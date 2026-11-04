"""Recovery curves, snapshot solves, and resilience index."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import copy
import numpy as np
from typing import Dict, List, Callable, Optional
from resilience.engine import run_scenario
from resilience.scenarios import Scenario
from resilience.metrics import tstt, mean_trip_time


SNAPSHOT_DAYS = [0, 7, 14, 30, 60, 90]


# ------------------------------------------------------------------
# Capacity recovery functions  t in [0, horizon]
# ------------------------------------------------------------------

def recovery_linear(t: float, horizon: float) -> float:
    """Fraction of capacity restored by day t (linear)."""
    return min(t / horizon, 1.0)


def recovery_exponential(t: float, horizon: float) -> float:
    """Exponential recovery: 1 - exp(-3t/horizon) normalised to reach ~1 at t=horizon."""
    if horizon <= 0:
        return 1.0
    return 1.0 - np.exp(-3.0 * t / horizon)


def recovery_step(t: float, horizon: float) -> float:
    """Step recovery: nothing until t >= horizon, then full restoration."""
    return 1.0 if t >= horizon else 0.0


RECOVERY_SHAPES: Dict[str, Callable] = {
    'linear': recovery_linear,
    'exponential': recovery_exponential,
    'step': recovery_step,
}


# ------------------------------------------------------------------
# Performance function Q(t) in [0,1]
# ------------------------------------------------------------------

def performance_q(snapshot_result: dict, baseline_result: dict) -> float:
    """Q(t) = served_share * (baseline_mean_tt / snapshot_mean_tt).

    Returns value in [0, 1].
    """
    b_net = baseline_result['net']
    s_net = snapshot_result['net']

    b_total = sum(od.demand for od in b_net.ODpair.values())
    s_total = sum(od.demand for od in s_net.ODpair.values())
    s_unmet = snapshot_result['unmet_demand']
    s_served = max(s_total - s_unmet, 0.0)
    served_share = s_served / b_total if b_total > 0 else 0.0

    b_tstt = tstt(baseline_result['link_results'])
    s_tstt = tstt(snapshot_result['link_results'])

    b_mean_tt = b_tstt / b_total if b_total > 0 else 1.0
    s_mean_tt = s_tstt / s_served if s_served > 0 else float('inf')

    if s_mean_tt <= 0 or not np.isfinite(s_mean_tt):
        tt_ratio = 0.0
    else:
        tt_ratio = min(b_mean_tt / s_mean_tt, 1.0)

    return float(served_share * tt_ratio)


# ------------------------------------------------------------------
# Recovery sweep
# ------------------------------------------------------------------

def run_recovery_curve(config: dict, disruption_scenario: Scenario,
                       baseline_net, baseline_result: dict,
                       baseline_flows: Dict,
                       horizon: float = 90.0,
                       shape: str = 'linear',
                       snapshot_days: List[float] = SNAPSHOT_DAYS,
                       criticality_ranking=None,
                       link_gdf=None) -> dict:
    """Solve UE at each snapshot day, tracking Q(t).

    At each snapshot, the disrupted links have their capacity partially restored
    according to the recovery shape.
    Returns dict with keys: days, q_values, resilience_index, resilience_loss,
    time_to_95pct.
    """
    rec_fn = RECOVERY_SHAPES[shape]
    q_values = []

    for day in snapshot_days:
        frac_restored = rec_fn(day, horizon)

        # Build a snapshot scenario: same disruption but partial restoration
        snap_net = copy.deepcopy(baseline_net)

        # Apply scenario to get disrupted state
        from resilience.engine import apply_scenario, check_od_connectivity
        affected = apply_scenario(snap_net, disruption_scenario, None, criticality_ranking, link_gdf)

        # Partially restore capacity on affected links
        if frac_restored > 0 and frac_restored < 1.0:
            orig_net = copy.deepcopy(baseline_net)
            for lid in affected:
                if lid in snap_net.link and lid in orig_net.link:
                    orig_cap = orig_net.link[lid].capacity
                    disrupted_cap = snap_net.link[lid].capacity
                    # Restore fraction of lost capacity
                    lost = orig_cap - disrupted_cap
                    snap_net.link[lid].capacity = disrupted_cap + frac_restored * lost
                    snap_net.link[lid].updateCost()
        elif frac_restored >= 1.0:
            # Full restoration — re-add removed links from baseline
            # Re-run from clean baseline
            snap_net = copy.deepcopy(baseline_net)

        # Warm start
        for lid in snap_net.link:
            if lid in baseline_flows:
                snap_net.link[lid].flow = baseline_flows[lid]
                snap_net.link[lid].updateCost()

        # Connectivity check and solve
        reachable, unreachable = check_od_connectivity(snap_net)
        removed = {}
        for od_id in unreachable:
            if od_id in snap_net.ODpair:
                removed[od_id] = snap_net.ODpair.pop(od_id)

        import io, sys as _sys
        _old = _sys.stdout; _sys.stdout = io.StringIO()
        try:
            snap_net.userEquilibrium(
                stepSizeRule=config.get('solver_step_rule', 'FW'),
                maxIterations=int(config.get('solver_max_iter', 1_000_000)),
                targetGap=float(config.get('solver_gap', 1e-4)),
            )
        finally:
            _sys.stdout = _old

        for od_id, od in removed.items():
            snap_net.ODpair[od_id] = od

        lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                    'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
              for lid, lk in snap_net.link.items()}

        unmet = sum(od.demand for od in removed.values())
        snap_result = {
            'link_results': lr,
            'unmet_demand': unmet,
            'unreachable_ods': unreachable,
            'reachable_ods': reachable,
            'net': snap_net,
        }

        q = performance_q(snap_result, baseline_result)
        q_values.append(q)

    # Resilience index: trapezoidal integral / horizon
    days_arr = np.array(snapshot_days, dtype=float)
    q_arr = np.array(q_values, dtype=float)
    _trapz = getattr(np, 'trapezoid', np.trapz)
    R = float(_trapz(q_arr, days_arr) / horizon) if horizon > 0 else 0.0
    resilience_loss = 1.0 - R

    # Time to 95% recovery
    t95 = None
    for i, q in enumerate(q_values):
        if q >= 0.95:
            t95 = float(snapshot_days[i])
            break
    if t95 is None:
        t95 = float(horizon)  # did not recover

    return {
        'days': list(snapshot_days),
        'q_values': q_values,
        'resilience_index': R,
        'resilience_loss': resilience_loss,
        'time_to_95pct': t95,
    }
