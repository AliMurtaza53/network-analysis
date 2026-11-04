"""Run Q3: sensitivity analysis sweeps and figures.

Usage:
    python scripts/run_q3.py [--config config/anaheim.yaml]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import pandas as pd
import numpy as np
import time

from resilience.data import load_config, load_network, build_link_geodataframe
from resilience.sensitivity import run_oat, run_2d_grid, run_morris
from resilience.plotting.sensitivity_plots import (
    plot_tornado, plot_2d_heatmaps, plot_morris_scatter,
    plot_rank_stability, plot_output_range, plot_numerical_sensitivity
)


def numerical_sensitivity(config, baseline_net, baseline_flows, link_gdf, criticality_ranking):
    """Run UE at different gap tolerances and compare AON vs UE."""
    from resilience.sensitivity import _run_with_params, _make_scenario, DEFAULT_REF_PARAMS
    from resilience.engine import check_od_connectivity
    import copy, network as net_module
    from resilience.metrics import tstt, mean_trip_time

    rows = []
    ref = dict(DEFAULT_REF_PARAMS)
    params, sc = _make_scenario(ref, {})

    # Gap tolerance sweep
    for gap in [1e-2, 1e-3, 1e-4]:
        p_copy = dict(params)
        p_copy['gap_tolerance'] = gap
        try:
            m = _run_with_params(config, p_copy, sc, baseline_net, baseline_flows,
                                 link_gdf, criticality_ranking)
            for metric in ['tstt_ratio', 'mean_trip_time_ratio', 'unmet_share']:
                rows.append({'type': 'gap', 'gap': gap, 'model': 'UE',
                             'metric': metric, 'value': m.get(metric)})
        except Exception as e:
            print(f"Num sensitivity gap={gap}: {e}")

    # AON (all-or-nothing, 1 iteration of UE with max 1 iteration)
    try:
        cfg_aon = dict(config)
        cfg_aon['solver_max_iter'] = 1
        cfg_aon['solver_step_rule'] = 'MSA'
        net = copy.deepcopy(baseline_net)
        from resilience.engine import apply_scenario
        apply_scenario(net, sc, baseline_flows, criticality_ranking, link_gdf)
        reachable, unreachable = check_od_connectivity(net)
        saved = {}
        for od_id in unreachable:
            if od_id in net.ODpair:
                saved[od_id] = net.ODpair[od_id].demand
                net.ODpair[od_id].demand = 0.0
        import io as _io2; _o2 = sys.stdout; sys.stdout = _io2.StringIO()
        try:
            net.userEquilibrium(stepSizeRule='MSA', maxIterations=1, targetGap=1e-4)
        finally:
            sys.stdout = _o2
        for od_id, dem in saved.items():
            if od_id in net.ODpair:
                net.ODpair[od_id].demand = dem

        lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                    'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
              for lid, lk in net.link.items()}
        b_total = sum(od.demand for od in baseline_net.ODpair.values())
        s_served = b_total - sum(saved.values())
        b_tstt_val = tstt({lid: {'flow': lk.flow, 'cost': lk.cost}
                           for lid, lk in baseline_net.link.items()})
        s_tstt = tstt(lr)
        for metric, val in [('tstt_ratio', s_tstt / b_tstt_val if b_tstt_val > 0 else 1),
                             ('mean_trip_time_ratio', (s_tstt / s_served) / (b_tstt_val / b_total)
                              if s_served > 0 and b_total > 0 else 1),
                             ('unmet_share', sum(saved.values()) / b_total if b_total > 0 else 0)]:
            rows.append({'type': 'model', 'gap': None, 'model': 'AON',
                         'metric': metric, 'value': val})
        # Also UE row for comparison
        for metric in ['tstt_ratio', 'mean_trip_time_ratio', 'unmet_share']:
            m = _run_with_params(config, params, sc, baseline_net, baseline_flows,
                                 link_gdf, criticality_ranking)
            rows.append({'type': 'model', 'gap': None, 'model': 'UE',
                         'metric': metric, 'value': m.get(metric)})
    except Exception as e:
        print(f"AON comparison failed: {e}")

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/anaheim.yaml')
    parser.add_argument('--morris-n', type=int, default=10)
    args = parser.parse_args()

    os.makedirs('outputs/q3', exist_ok=True)
    config = load_config(args.config)

    print("Loading network and solving baseline...")
    t0 = time.time()
    baseline_net = load_network(config)
    link_gdf = build_link_geodataframe(baseline_net, config)

    import io as _io
    _old = sys.stdout; sys.stdout = _io.StringIO()
    try:
        convergence = baseline_net.userEquilibrium(
            stepSizeRule=config.get('solver_step_rule', 'FW'),
            maxIterations=int(config.get('solver_max_iter', 1_000_000)),
            targetGap=float(config.get('solver_gap', 1e-4)),
        )
    finally:
        sys.stdout = _old
    baseline_flows = {lid: lk.flow for lid, lk in baseline_net.link.items()}

    # Try to load criticality ranking from Q2 outputs
    criticality_ranking = []
    crit_path = 'outputs/q2/criticality.parquet'
    if os.path.exists(crit_path):
        crit_df = pd.read_parquet(crit_path)
        criticality_ranking = crit_df.sort_values('ue_tstt_increase', ascending=False)['link_id'].tolist()
        print(f"Loaded {len(criticality_ranking)} critical links from Q2")

    print(f"Baseline ready in {time.time()-t0:.1f}s")

    # 1. OAT sweep
    print("\nRunning OAT sweep...")
    oat_df = run_oat(config, baseline_net, baseline_flows, link_gdf, criticality_ranking=criticality_ranking)
    oat_df.to_parquet('outputs/q3/oat_results.parquet', index=False)
    print(f"OAT done: {len(oat_df)} rows")

    # 2. 2D grid
    print("\nRunning 2D grid (demand × severity)...")
    grid_df = run_2d_grid(config, baseline_net, baseline_flows, link_gdf, criticality_ranking=criticality_ranking)
    grid_df.to_parquet('outputs/q3/grid_results.parquet', index=False)
    print(f"2D grid done: {len(grid_df)} rows")

    # 3. Morris
    print(f"\nRunning Morris screening ({args.morris_n} trajectories)...")
    morris_results = run_morris(config, baseline_net, baseline_flows, link_gdf,
                                n_trajectories=args.morris_n, criticality_ranking=criticality_ranking)
    import json
    with open('outputs/q3/morris_results.json', 'w') as f:
        json.dump(morris_results, f, indent=2)
    print("Morris done")

    # 4. Numerical sensitivity
    print("\nRunning numerical sensitivity...")
    num_df = numerical_sensitivity(config, baseline_net, baseline_flows, link_gdf, criticality_ranking)
    num_df.to_parquet('outputs/q3/numerical_sensitivity.parquet', index=False)

    # Figures
    print("\nGenerating figures...")
    plot_tornado(oat_df, 'outputs/q3/F8_tornado')
    plot_2d_heatmaps(grid_df, 'outputs/q3/F9_2d_heatmaps')
    plot_morris_scatter(morris_results, 'outputs/q3/F10_morris')
    plot_output_range(oat_df, 'outputs/q3/F12_output_range')
    plot_numerical_sensitivity(num_df, 'outputs/q3/F13_numerical_sensitivity')

    # Rank stability
    outputs_key = ['tstt_ratio', 'unmet_share', 'accessibility_loss']
    rank_rows = []
    for param in oat_df['param'].unique():
        for out in outputs_key:
            sub = oat_df[(oat_df['param'] == param) & (oat_df['output'] == out)]
            if len(sub) >= 2:
                rank_rows.append({'param': param, 'output': out,
                                  'swing': sub['metric_value'].max() - sub['metric_value'].min()})
    rank_df = pd.DataFrame(rank_rows)
    if not rank_df.empty:
        pivot = rank_df.pivot_table(index='output', columns='param', values='swing')
        plot_rank_stability(pivot.reset_index(), 'outputs/q3/F11_rank_stability')

    total_time = time.time() - t0
    print(f"\nQ3 complete in {total_time:.0f}s")
    print("Outputs in outputs/q3/")

    # Print summary ranking
    if oat_df is not None and not oat_df.empty:
        print("\nTop influential parameters (by mean swing across outputs):")
        summary = oat_df.groupby('param')['metric_value'].agg(lambda x: x.max() - x.min())
        print(summary.sort_values(ascending=False).head(10))


if __name__ == '__main__':
    main()
