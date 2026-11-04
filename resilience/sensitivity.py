"""Sensitivity analysis: OAT sweeps, 2D grids, Morris screening."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import copy
import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from resilience.engine import run_scenario, check_od_connectivity
from resilience.scenarios import Scenario, spatial_footprint
from resilience.metrics import compute_all


# ------------------------------------------------------------------
# Reference scenario for sensitivity sweeps (S3 r=2km, center Anaheim)
# ------------------------------------------------------------------

DEFAULT_REF_PARAMS = {
    'demand_factor': 1.0,
    'severity': 0.5,
    'radius_km': 2.0,
    'bpr_alpha': 0.15,
    'bpr_power': 4.0,
    'truck_share': 0.08,
    'pce': 2.0,
    'vot_pax_factor': 1.0,
    'vot_truck_factor': 1.0,
    'recovery_duration': 60.0,
    'recovery_shape': 'linear',
    'gap_tolerance': 1e-3,
}

ANAHEIM_CENTER = (-117.9, 33.84)


def _make_scenario(ref_params: dict, overrides: dict, link_gdf=None) -> dict:
    """Build a modified config + scenario from ref_params with overrides applied."""
    p = {**ref_params, **overrides}
    # Spatial footprint scenario with current severity/radius
    sc = spatial_footprint(ANAHEIM_CENTER[0], ANAHEIM_CENTER[1],
                           p['radius_km'], p['severity'])
    return p, sc


def _run_with_params(config: dict, params: dict, scenario: Scenario,
                     baseline_net, baseline_flows, link_gdf,
                     criticality_ranking=None) -> dict:
    """Run scenario with parameter overrides applied to a network copy."""
    import network as net_module

    cfg = dict(config)
    cfg['solver_gap'] = params.get('gap_tolerance', config.get('solver_gap', 1e-4))
    cfg['truck_share'] = params.get('truck_share', config.get('truck_share', 0.08))
    cfg['pce'] = params.get('pce', config.get('pce', 2.0))
    cfg['vot_passenger'] = (params.get('vot_pax_factor', 1.0) *
                            config.get('vot_passenger', 18.0))
    cfg['vot_truck'] = (params.get('vot_truck_factor', 1.0) *
                        config.get('vot_truck', 60.0))

    # Network copy with BPR overrides
    net = copy.deepcopy(baseline_net)
    alpha = params.get('bpr_alpha', 0.15)
    power = params.get('bpr_power', 4.0)
    for lk in net.link.values():
        lk.alpha = alpha
        lk.beta = power
        lk.updateCost()

    # Scale demand
    df = params.get('demand_factor', 1.0)
    if df != 1.0:
        for od in net.ODpair.values():
            od.demand *= df

    # Apply scenario (physical disruption only, demand already applied)
    from resilience.engine import apply_scenario
    apply_scenario(net, scenario, baseline_flows, criticality_ranking, link_gdf,
                   demand_factor=None)

    # Connectivity and solve
    reachable, unreachable = check_od_connectivity(net)
    removed = {}
    for od_id in unreachable:
        if od_id in net.ODpair:
            removed[od_id] = net.ODpair.pop(od_id)

    import io as _io
    _old = sys.stdout; sys.stdout = _io.StringIO()
    try:
        net.userEquilibrium(
            stepSizeRule=cfg.get('solver_step_rule', 'FW'),
            maxIterations=int(cfg.get('solver_max_iter', 1_000_000)),
            targetGap=float(cfg['solver_gap']),
        )
    finally:
        sys.stdout = _old

    for od_id, od in removed.items():
        net.ODpair[od_id] = od

    lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
          for lid, lk in net.link.items()}
    od_costs = {}
    for od_id in reachable:
        od = net.ODpair.get(od_id)
        if od:
            _, costs = net.shortestPath(od.origin)
            od_costs[od_id] = costs.get(od.destination, float('inf'))

    result = {
        'link_results': lr, 'od_costs': od_costs,
        'unmet_demand': sum(od.demand for od in removed.values()),
        'unreachable_ods': unreachable, 'reachable_ods': reachable,
        'net': net,
    }

    return compute_all(result, _make_baseline_result(baseline_net, cfg, config), cfg)


def _make_baseline_result(baseline_net, cfg, orig_config):
    """Lightweight baseline result dict for metric computation."""
    lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
          for lid, lk in baseline_net.link.items()}
    od_costs = {}
    for od_id, od in baseline_net.ODpair.items():
        _, costs = baseline_net.shortestPath(od.origin)
        od_costs[od_id] = costs.get(od.destination, float('inf'))
    return {
        'link_results': lr, 'od_costs': od_costs,
        'unmet_demand': 0.0,
        'unreachable_ods': [], 'reachable_ods': list(baseline_net.ODpair.keys()),
        'net': baseline_net,
    }


# ------------------------------------------------------------------
# OAT sweep
# ------------------------------------------------------------------

OAT_RANGES = {
    'demand_factor':   [0.8, 1.0, 1.2, 1.4],
    'severity':        [0.25, 0.50, 0.75, 1.0],
    'radius_km':       [1.0, 2.0, 3.0],
    'bpr_alpha':       [0.15, 0.25, 0.5],
    'bpr_power':       [2.0, 4.0, 6.0],
    'truck_share':     [0.0, 0.05, 0.10, 0.15],
    'pce':             [1.5, 2.0, 3.0],
    'vot_pax_factor':  [0.5, 1.0, 1.5],
    'vot_truck_factor':[0.5, 1.0, 1.5],
    'recovery_duration': [30.0, 60.0, 90.0],
    'gap_tolerance':   [1e-2, 1e-3, 1e-4],
}

KEY_OUTPUTS = ['tstt_ratio', 'mean_trip_time_ratio', 'unmet_share',
               'od_exposure_p95', 'accessibility_loss', 'total_economic_cost']


def run_oat(config: dict, baseline_net, baseline_flows, link_gdf,
            ref_params: dict = None, criticality_ranking=None) -> pd.DataFrame:
    """One-at-a-time sweep. Returns tidy DataFrame."""
    if ref_params is None:
        ref_params = dict(DEFAULT_REF_PARAMS)

    rows = []
    for param_name, values in OAT_RANGES.items():
        for val in values:
            overrides = {param_name: val}
            params, sc = _make_scenario(ref_params, overrides)
            try:
                m = _run_with_params(config, params, sc, baseline_net,
                                     baseline_flows, link_gdf, criticality_ranking)
                for out in KEY_OUTPUTS:
                    rows.append({
                        'param': param_name,
                        'value': val,
                        'output': out,
                        'metric_value': m.get(out, float('nan')),
                        'params_json': str(overrides),
                    })
            except Exception as e:
                print(f"OAT warning: {param_name}={val}: {e}")

    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# 2D grid: demand × severity
# ------------------------------------------------------------------

def run_2d_grid(config: dict, baseline_net, baseline_flows, link_gdf,
                demand_values=None, severity_values=None,
                criticality_ranking=None) -> pd.DataFrame:
    if demand_values is None:
        demand_values = [0.8, 1.0, 1.2, 1.4]
    if severity_values is None:
        severity_values = [0.25, 0.50, 0.75, 1.0]

    rows = []
    ref = dict(DEFAULT_REF_PARAMS)
    for df, sev in itertools.product(demand_values, severity_values):
        overrides = {'demand_factor': df, 'severity': sev}
        params, sc = _make_scenario(ref, overrides)
        try:
            m = _run_with_params(config, params, sc, baseline_net,
                                 baseline_flows, link_gdf, criticality_ranking)
            rows.append({
                'demand_factor': df, 'severity': sev,
                'tstt_ratio': m.get('tstt_ratio'),
                'unmet_share': m.get('unmet_share'),
                'accessibility_loss': m.get('accessibility_loss'),
                'total_economic_cost': m.get('total_economic_cost'),
            })
        except Exception as e:
            print(f"2D grid warning: demand={df}, sev={sev}: {e}")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# Morris screening via SALib
# ------------------------------------------------------------------

MORRIS_PARAMS = {
    'names': ['demand_factor', 'severity', 'radius_km', 'bpr_alpha', 'bpr_power',
              'truck_share', 'pce', 'vot_pax_factor'],
    'bounds': [[0.8, 1.4], [0.25, 1.0], [1.0, 3.0], [0.15, 0.5], [2.0, 6.0],
               [0.0, 0.15], [1.5, 3.0], [0.5, 1.5]],
}


def run_morris(config: dict, baseline_net, baseline_flows, link_gdf,
               n_trajectories: int = 10, criticality_ranking=None,
               seed: int = 42) -> dict:
    """Morris screening. Returns dict with SALib analyze results per output."""
    from SALib.sample.morris import sample as morris_sample
    from SALib.analyze import morris as morris_analyze

    problem = {
        'num_vars': len(MORRIS_PARAMS['names']),
        'names': MORRIS_PARAMS['names'],
        'bounds': MORRIS_PARAMS['bounds'],
    }

    X = morris_sample(problem, N=n_trajectories, seed=seed)
    print(f"Morris: {len(X)} runs")

    ref = dict(DEFAULT_REF_PARAMS)
    Y: Dict[str, List] = {out: [] for out in KEY_OUTPUTS}

    for i, x in enumerate(X):
        overrides = dict(zip(problem['names'], x))
        params = {**ref, **overrides}
        _, sc = _make_scenario(params, {})
        try:
            m = _run_with_params(config, params, sc, baseline_net,
                                 baseline_flows, link_gdf, criticality_ranking)
            for out in KEY_OUTPUTS:
                Y[out].append(m.get(out, float('nan')))
        except Exception as e:
            print(f"Morris run {i} failed: {e}")
            for out in KEY_OUTPUTS:
                Y[out].append(float('nan'))

    results = {}
    for out in KEY_OUTPUTS:
        y_arr = np.array(Y[out])
        valid = np.isfinite(y_arr)
        if valid.sum() < 2:
            continue
        try:
            si = morris_analyze.analyze(problem, X, y_arr, print_to_console=False, seed=seed)
            results[out] = {
                'names': problem['names'],
                'mu_star': si['mu_star'].tolist(),
                'sigma': si['sigma'].tolist(),
                'mu_star_conf': si.get('mu_star_conf', np.zeros(len(problem['names']))).tolist(),
            }
        except Exception as e:
            print(f"Morris analyze failed for {out}: {e}")

    return results


# ------------------------------------------------------------------
# Rank stability
# ------------------------------------------------------------------

def rank_stability(metric_values: Dict[str, List[float]]) -> dict:
    """Kendall tau of scenario ranking across parameter perturbations."""
    from scipy.stats import kendalltau
    keys = list(metric_values.keys())
    if len(keys) < 2:
        return {}
    taus = {}
    ref_ranks = np.argsort(np.argsort(metric_values[keys[0]]))
    for k in keys[1:]:
        alt_ranks = np.argsort(np.argsort(metric_values[k]))
        tau, _ = kendalltau(ref_ranks, alt_ranks)
        taus[k] = float(tau)
    return taus
