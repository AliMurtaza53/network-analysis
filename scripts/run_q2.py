"""Run Q2: disruption scenarios, metrics, criticality, recovery, and all figures.

Usage:
    python scripts/run_q2.py [--config config/anaheim.yaml] [--jobs N]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import copy
import json
import pandas as pd
import numpy as np
import time

from resilience.data import load_config, load_network, build_link_geodataframe
from resilience.engine import run_scenario, check_od_connectivity
from resilience.scenarios import (
    baseline, random_closure, targeted_closure, spatial_footprint,
    corridor_closure, demand_surge, default_q2_scenarios
)
from resilience.metrics import (
    compute_all, tstt, mean_trip_time, od_time_changes,
    topology_indices
)
from resilience.recovery import run_recovery_curve


ANAHEIM_CENTER = (-117.9, 33.84)
SEED = 42


def compute_criticality(config, baseline_net, baseline_result, baseline_flows,
                        link_gdf, top_n: int = 60):
    """Single-link removal criticality for top N links by baseline flow."""
    print(f"\nComputing criticality for top {top_n} links by flow...")
    link_flows = {lid: lk.flow for lid, lk in baseline_net.link.items()}
    # Proxy: sort by baseline flow
    proxy_ranked = sorted(link_flows.keys(), key=lambda x: link_flows[x], reverse=True)
    screen_links = proxy_ranked[:top_n]

    b_tstt = tstt(baseline_result['link_results'])
    criticality_ue = {}

    for i, lid in enumerate(screen_links):
        try:
            sc = type('Sc', (), {'scenario_id': f'crit_{lid}', 'family': '_crit',
                                  'params': {}, 'params_json': lambda s: '{}'})()
            net = copy.deepcopy(baseline_net)
            # Remove the link
            from resilience.engine import _remove_link
            _remove_link(net, lid)

            # Warm start
            for l2, lk in net.link.items():
                if l2 in baseline_flows:
                    lk.flow = baseline_flows[l2]
                    lk.updateCost()

            reachable, unreachable = check_od_connectivity(net)
            removed = {}
            for od_id in unreachable:
                if od_id in net.ODpair:
                    removed[od_id] = net.ODpair.pop(od_id)

            import io
            _old = sys.stdout; sys.stdout = io.StringIO()
            try:
                net.userEquilibrium(
                    stepSizeRule=config.get('solver_step_rule', 'FW'),
                    maxIterations=int(config.get('solver_max_iter', 1_000_000)),
                    targetGap=1e-3,  # relax for criticality screening
                )
            finally:
                sys.stdout = _old
            for od_id, od in removed.items():
                net.ODpair[od_id] = od

            lr = {l: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                      'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
                  for l, lk in net.link.items()}
            s_tstt = tstt(lr)
            criticality_ue[lid] = s_tstt - b_tstt

        except Exception as e:
            criticality_ue[lid] = 0.0
            print(f"  Criticality {lid}: {e}")

        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(screen_links)} done")

    proxy_scores = {lid: link_flows[lid] for lid in screen_links}
    return criticality_ue, proxy_scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/anaheim.yaml')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--skip-criticality', action='store_true')
    parser.add_argument('--skip-recovery', action='store_true')
    args = parser.parse_args()

    os.makedirs('outputs/q2', exist_ok=True)
    config = load_config(args.config)

    print("Loading network...")
    t0 = time.time()
    baseline_net = load_network(config)

    # Build link GeoDataFrame
    link_gdf = build_link_geodataframe(baseline_net, config)

    # Solve baseline UE (keep 1e-4 for baseline accuracy)
    print("Solving baseline UE...")
    t_bl = time.time()
    import io as _io_bl
    _old_bl = sys.stdout; sys.stdout = _io_bl.StringIO()
    try:
        convergence = baseline_net.userEquilibrium(
            stepSizeRule=config.get('solver_step_rule', 'FW'),
            maxIterations=int(config.get('solver_max_iter', 1_000_000)),
            targetGap=float(config.get('solver_gap', 1e-4)),
        )
    finally:
        sys.stdout = _old_bl
    print(f"  baseline UE: {time.time()-t_bl:.1f}s, gap={convergence['relative_gaps'][-1]:.2e}")
    baseline_flows = {lid: lk.flow for lid, lk in baseline_net.link.items()}
    baseline_od_costs = {}
    for od_id, od in baseline_net.ODpair.items():
        _, costs = baseline_net.shortestPath(od.origin)
        baseline_od_costs[od_id] = costs.get(od.destination, float('inf'))

    baseline_lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                          'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
                   for lid, lk in baseline_net.link.items()}
    baseline_result = {
        'link_results': baseline_lr,
        'od_costs': baseline_od_costs,
        'unmet_demand': 0.0,
        'unreachable_ods': [],
        'reachable_ods': list(baseline_net.ODpair.keys()),
        'net': baseline_net,
    }

    print(f"Baseline solved in {time.time()-t0:.1f}s, gap={convergence['relative_gaps'][-1]:.2e}")

    # Topology info (Q1 context)
    topo = topology_indices(baseline_net.numNodes, baseline_net.numLinks, baseline_net.numZones)
    print(f"Topology: {topo}")

    # Save baseline link table
    link_df = link_gdf[['link_id', 'tail', 'head', 'capacity', 'length', 'fft',
                          'alpha', 'beta']].copy()
    link_df['flow'] = link_df['link_id'].map(baseline_flows)
    link_df['vc'] = link_df.apply(
        lambda r: r['flow'] / r['capacity'] if r['capacity'] > 0 else 0, axis=1)
    link_df.to_parquet('outputs/q2/baseline_links.parquet', index=False)

    # F1: baseline map
    if link_gdf.crs is not None:
        from resilience.plotting.maps import plot_baseline_map
        plot_baseline_map(link_gdf, config.get('crs_metric', 'EPSG:26911'),
                          'outputs/q2/F1_baseline_map')

    # Criticality
    criticality_ue, proxy_scores = {}, {}
    criticality_ranking = []
    if not args.skip_criticality:
        top_n = config.get('criticality_top_n', 60)
        criticality_ue, proxy_scores = compute_criticality(
            config, baseline_net, baseline_result, baseline_flows, link_gdf, top_n)
        criticality_ranking = sorted(criticality_ue.keys(),
                                     key=lambda x: criticality_ue[x], reverse=True)
        # Save
        crit_df = pd.DataFrame({'link_id': list(criticality_ue.keys()),
                                 'ue_tstt_increase': list(criticality_ue.values()),
                                 'proxy_flow': [proxy_scores.get(k, 0) for k in criticality_ue]})
        crit_df.to_parquet('outputs/q2/criticality.parquet', index=False)
        print(f"Top critical links: {criticality_ranking[:5]}")

    # Use relaxed gap for scenario sweep (1e-3); validates against 1e-4 on baseline
    config_sweep = dict(config)
    config_sweep['solver_gap'] = 1e-3

    # Build full scenario list
    scenarios = default_q2_scenarios(criticality_ranking, ANAHEIM_CENTER)
    print(f"\nRunning {len(scenarios)} scenarios...")

    # Run scenarios
    all_metrics_rows = []
    all_link_rows = []
    od_delta_data = {}  # for F5

    for i, sc in enumerate(scenarios):
        try:
            result = run_scenario(config_sweep, sc, baseline_net, baseline_flows,
                                  criticality_ranking, link_gdf)
            m = compute_all(result, baseline_result, config)
            m['scenario_id'] = sc.scenario_id
            m['family'] = sc.family
            m['params_json'] = sc.params_json()
            all_metrics_rows.append(m)

            # Link level
            for lid, lr in result['link_results'].items():
                all_link_rows.append({
                    'scenario_id': sc.scenario_id,
                    'link_id': lid,
                    'flow': lr['flow'],
                    'cost': lr['cost'],
                    'vc': lr['vc'],
                    'closed': lid in result.get('affected_links', []),
                })

            # OD deltas for F5
            deltas = od_time_changes(result['od_costs'], baseline_od_costs)
            od_delta_data[sc.scenario_id] = (sc.family, deltas)

            if (i + 1) % 10 == 0:
                print(f"  {i+1}/{len(scenarios)} scenarios done")

        except Exception as e:
            print(f"  Scenario {sc.scenario_id} failed: {e}")

    # Save tidy tables
    metrics_df = pd.DataFrame(all_metrics_rows)
    metrics_df.to_parquet('outputs/q2/metrics.parquet', index=False)

    # Melt for panel plots
    id_cols = ['scenario_id', 'family', 'params_json']
    metric_cols = [c for c in metrics_df.columns if c not in id_cols]
    metrics_long = metrics_df.melt(id_vars=id_cols, value_vars=metric_cols,
                                   var_name='metric', value_name='value')
    metrics_long.to_parquet('outputs/q2/metrics_long.parquet', index=False)

    link_df_all = pd.DataFrame(all_link_rows)
    link_df_all.to_parquet('outputs/q2/link_results.parquet', index=False)

    print(f"\nSaved {len(metrics_df)} scenario metric rows, {len(link_df_all)} link rows")

    # Figures
    from resilience.plotting.panels import (
        plot_q2_panel, plot_criticality_panel, plot_ecdf_od_time, plot_metric_correlation
    )

    plot_q2_panel(metrics_long, 'outputs/q2/F3_q2_panel')
    plot_ecdf_od_time(od_delta_data, 'outputs/q2/F5_ecdf_od_time')
    plot_metric_correlation(metrics_long, 'outputs/q2/F7_metric_correlation')

    if criticality_ue:
        from resilience.plotting.panels import plot_criticality_panel
        from resilience.plotting.maps import plot_criticality_map
        top_links = criticality_ranking[:20]
        plot_criticality_panel(criticality_ue, proxy_scores, 'outputs/q2/F4_criticality_panel')
        if link_gdf.crs is not None:
            plot_criticality_map(link_gdf, criticality_ue, top_links,
                                 config.get('crs_metric', 'EPSG:26911'),
                                 'outputs/q2/F4_criticality_map')

    # F2: delta flow maps for 4 key scenarios
    key_families = ['S2', 'S3', 'S4', 'S5']
    key_results = []
    key_labels = []
    for sc in scenarios:
        if sc.family in key_families and len(key_results) < 4:
            for m_row in all_metrics_rows:
                if m_row['scenario_id'] == sc.scenario_id:
                    # Rebuild link_results from stored data
                    # (use metrics_df to find result rows from link table)
                    break
    # Simpler: re-run 4 key scenarios for maps
    if link_gdf.crs is not None:
        from resilience.plotting.maps import plot_delta_flow_maps
        key_scenarios = [sc for sc in scenarios if sc.family in key_families][:4]
        key_results_full = []
        for sc in key_scenarios:
            try:
                r = run_scenario(config_sweep, sc, baseline_net, baseline_flows,
                                 criticality_ranking, link_gdf)
                key_results_full.append(r)
                key_labels.append(sc.scenario_id)
            except Exception as e:
                print(f"Map re-run {sc.scenario_id}: {e}")
        if key_results_full:
            plot_delta_flow_maps(link_gdf, key_results_full, key_labels,
                                 baseline_flows,
                                 config.get('crs_metric', 'EPSG:26911'),
                                 'outputs/q2/F2_delta_flow_maps')

    # F6: recovery curves
    if not args.skip_recovery:
        print("\nRunning recovery curves...")
        recovery_results = {}
        rec_scenarios = [sc for sc in scenarios if sc.family in ['S2', 'S3', 'S4']][:4]
        for sc in rec_scenarios:
            try:
                rec = run_recovery_curve(config_sweep, sc, baseline_net, baseline_result,
                                         baseline_flows, horizon=90.0, shape='linear',
                                         link_gdf=link_gdf,
                                         criticality_ranking=criticality_ranking)
                recovery_results[sc.scenario_id] = (sc.family, rec)
            except Exception as e:
                print(f"Recovery {sc.scenario_id}: {e}")

        if recovery_results:
            from resilience.plotting.panels import plot_recovery_curves
            plot_recovery_curves(recovery_results, 'outputs/q2/F6_recovery_curves')
            # Save recovery table
            rec_rows = []
            for sc_id, (fam, rec) in recovery_results.items():
                for d, q in zip(rec['days'], rec['q_values']):
                    rec_rows.append({'scenario_id': sc_id, 'family': fam,
                                     'day': d, 'q': q,
                                     'resilience_index': rec['resilience_index'],
                                     'resilience_loss': rec['resilience_loss'],
                                     'time_to_95pct': rec['time_to_95pct']})
            pd.DataFrame(rec_rows).to_parquet('outputs/q2/recovery.parquet', index=False)

    total_time = time.time() - t0
    print(f"\nQ2 complete in {total_time:.0f}s")
    print("Outputs in outputs/q2/")


if __name__ == '__main__':
    main()
