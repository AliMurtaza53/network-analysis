"""Lightweight test protocol runner for accuracy + performance.

Usage examples (run from repo root):
  python -m tests.run_protocol --tests protocol/siouxfalls_10_aec.txt --func averageExcessCost --runs 5 --output results.csv
  python -m tests.run_protocol --tests protocol/siouxfalls_10_aec.txt protocol/siouxfalls_eqm_aec.txt --func averageExcessCost --profile cprofile --profile-dir profs
  python -m tests.run_protocol --tests protocol/siouxfalls_ue_fw.txt --mode ue_solve --runs 3 --output ue_timing.csv
  python -m tests.run_protocol --tests protocol/siouxfalls_10_aec.txt --func averageExcessCost --network-path network_baseline.py --output baseline_results.csv
  python -m tests.run_protocol --tests protocol/siouxfalls_ue_fw.txt --mode ue_solve --network-path network_baseline.py --runs 3 --output baseline_ue_timing.csv

Test spec file format (non-comment lines):
    Line 1: network file path
    Line 2: trips file path
    Line 3: flows file path (used to set link flows before measuring)
    Line 4: expected numeric answer (float) *if present*
    Line 5: path to an answer flows file for per-link comparison *if present*

UE solve spec format (--mode ue_solve):
    Line 1: network file path
    Line 2: trips file path
    Line 3: step rule (FW or MSA)
    Line 4: max iterations (int)
    Line 5: target gap (float)
    Line 6: gap function name (relativeGap or averageExcessCost)
    Line 7 (optional): expected iterations (int) or expected final gap (float) for pass/fail

Notes:
- You can provide numeric only, flows only, or both (numeric on the first remaining line, flows answer on the next).
- When both are provided, the test passes only if both numeric and flow checks pass.

This script:
- parses test spec files and constructs `network.Network`, loads flows, computes the requested metric,
- measures execution time across repeated runs (mean/std),
- optionally collects a cProfile for a single run and writes `.prof` files,
- writes a CSV summary and optional JSON details.

Used to compare baseline vs candidate implementations for merge decisions.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import time
import statistics
import cProfile
import pstats
import io
import importlib.util
import sys
from typing import Dict, Tuple, List, Callable

import network
import utils


def approxEqual(value, target, tolerance):
    """Check if value is approximately equal to target within tolerance."""
    if (abs(target) <= tolerance): 
        return abs(value) <= tolerance
    return abs(float(value) / target - 1) <= tolerance


def load_network_override(path: str):
    """Dynamically load a network.py alternative and install as the network module."""
    spec = importlib.util.spec_from_file_location("network", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load network module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['network'] = module
    globals()['network'] = module


def write_flow_diff_file(out_path: str, computed: Dict[str, float], expected: Dict[str, float], tolerance: float = 0.01) -> None:
    """Write per-link flow comparison CSV: link_id, computed, expected, abs_error, match."""
    fieldnames = ['link_id', 'computed_flow', 'expected_flow', 'abs_error', 'match']
    with open(out_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        # Use union of keys to surface missing links on either side
        all_links = set(computed.keys()) | set(expected.keys())
        for ij in sorted(all_links):
            c = computed.get(ij, 0.0)
            e = expected.get(ij, 0.0)
            err = abs(c - e)
            match = approxEqual(c, e, tolerance)
            writer.writerow({
                'link_id': ij,
                'computed_flow': c,
                'expected_flow': e,
                'abs_error': err,
                'match': match,
            })


def parse_spec(path: str):
    """Parse a protocol test spec.

    Returns: (networkFile, tripsFile, flowsFile, numeric_answer_or_none, flow_answer_or_none)
    The parser accepts:
    - numeric-only: numeric_answer set, flow_answer None
    - flow-only: numeric_answer None, flow_answer set (path)
    - both: numeric_answer set on first remaining line, flow_answer set on next
    """
    networkFile = None
    tripsFile = None
    flowsFile = None
    numeric_answer = None
    flow_answer = None
    with open(path, "r") as f:
        for line in f.read().splitlines():
            if len(line.strip()) == 0 or line.lstrip().startswith('#'):
                continue
            if networkFile is None:
                networkFile = os.path.normpath(line.strip())
                continue
            if tripsFile is None:
                tripsFile = os.path.normpath(line.strip())
                continue
            if flowsFile is None:
                flowsFile = os.path.normpath(line.strip())
                continue
            if numeric_answer is None:
                raw = line.strip()
                try:
                    numeric_answer = float(raw)
                    continue
                except ValueError:
                    pass
            if flow_answer is None:
                flow_answer = os.path.normpath(line.strip())
                continue
    return networkFile, tripsFile, flowsFile, numeric_answer, flow_answer


def parse_fw_spec(path: str):
    """Parse Frank-Wolfe step size spec: net, trips, base flows, target flows, expected step size."""
    networkFile = None
    tripsFile = None
    baseFlows = None
    targetFlows = None
    step_answer = None
    with open(path, "r") as f:
        for line in f.read().splitlines():
            if len(line.strip()) == 0 or line.lstrip().startswith('#'):
                continue
            if networkFile is None:
                networkFile = os.path.normpath(line.strip())
                continue
            if tripsFile is None:
                tripsFile = os.path.normpath(line.strip())
                continue
            if baseFlows is None:
                baseFlows = os.path.normpath(line.strip())
                continue
            if targetFlows is None:
                targetFlows = os.path.normpath(line.strip())
                continue
            if step_answer is None:
                step_answer = float(line.strip())
                continue
    return networkFile, tripsFile, baseFlows, targetFlows, step_answer


def parse_shift_spec(path: str):
    """Parse convex-combo shift spec: net, trips, base flows, target flows, step size, answer flows."""
    networkFile = None
    tripsFile = None
    baseFlows = None
    targetFlows = None
    step_size = None
    answerFlows = None
    with open(path, "r") as f:
        for line in f.read().splitlines():
            if len(line.strip()) == 0 or line.lstrip().startswith('#'):
                continue
            if networkFile is None:
                networkFile = os.path.normpath(line.strip())
                continue
            if tripsFile is None:
                tripsFile = os.path.normpath(line.strip())
                continue
            if baseFlows is None:
                baseFlows = os.path.normpath(line.strip())
                continue
            if targetFlows is None:
                targetFlows = os.path.normpath(line.strip())
                continue
            if step_size is None:
                step_size = float(line.strip())
                continue
            if answerFlows is None:
                answerFlows = os.path.normpath(line.strip())
                continue
    return networkFile, tripsFile, baseFlows, targetFlows, step_size, answerFlows


def parse_ue_spec(path: str):
    """Parse UE solve spec: net, trips, step_rule, max_iters, target_gap, gap_func, optional expected_iterations."""
    networkFile = None
    tripsFile = None
    step_rule = None
    max_iters = None
    target_gap = None
    gap_func = None
    expected_iters = None
    with open(path, "r") as f:
        for line in f.read().splitlines():
            if len(line.strip()) == 0 or line.lstrip().startswith('#'):
                continue
            if networkFile is None:
                networkFile = os.path.normpath(line.strip())
                continue
            if tripsFile is None:
                tripsFile = os.path.normpath(line.strip())
                continue
            if step_rule is None:
                step_rule = line.strip()
                continue
            if max_iters is None:
                max_iters = int(line.strip())
                continue
            if target_gap is None:
                target_gap = float(line.strip())
                continue
            if gap_func is None:
                gap_func = line.strip()
                continue
            if expected_iters is None:
                try:
                    expected_iters = int(line.strip())
                except ValueError:
                    expected_iters = float(line.strip())
                continue
    return networkFile, tripsFile, step_rule, max_iters, target_gap, gap_func, expected_iters


def read_flows_file(flowsFileName: str) -> Dict[str, float]:
    flows = {}
    with open(flowsFileName, "r") as f:
        for line in f.read().splitlines():
            if len(line.strip()) == 0 or line.lstrip().startswith('#'):
                continue
            parts = line.split()
            flows[parts[0]] = float(parts[1])
    return flows


def run_single_test(spec_path: str, func_name: str) -> Tuple[float, float, bool, Dict]:
    """Run the specified metric once and return (value, expected, pass, details).

    Supports both numeric and flow comparisons (one or both). Overall pass requires all provided checks to pass.
    details includes comparison metadata for downstream reporting.
    """
    netf, tripsf, flowsf, numeric_answer, flow_answer = parse_spec(spec_path)
    net = network.Network(netf, tripsf)
    flows = read_flows_file(flowsf)
    for ij in net.link:
        net.link[ij].flow = flows[ij]
        net.link[ij].updateCost()

    numeric_value = None
    numeric_pass = True if numeric_answer is None else False
    if numeric_answer is not None:
        if not hasattr(net, func_name):
            raise AttributeError(f"Network has no attribute {func_name}")
        metric_func = getattr(net, func_name)
        numeric_value = metric_func()
        numeric_pass = approxEqual(numeric_value, numeric_answer, 0.01)

    flow_mismatches = None
    flow_max_abs_err = None
    flow_pass = True if flow_answer is None else False
    if flow_answer is not None:
        answer_flows = read_flows_file(flow_answer)
        mismatches = 0
        max_abs_err = 0.0
        for ij in net.link:
            computed = net.link[ij].flow
            expected = answer_flows.get(ij, None)
            if expected is None:
                mismatches += 1
                max_abs_err = max(max_abs_err, abs(computed))
                continue
            diff = abs(computed - expected)
            max_abs_err = max(max_abs_err, diff)
            if not approxEqual(computed, expected, 0.01):
                mismatches += 1
        flow_mismatches = mismatches
        flow_max_abs_err = max_abs_err
        flow_pass = (mismatches == 0)

    overall_pass = True
    if numeric_answer is not None:
        overall_pass = overall_pass and numeric_pass
    if flow_answer is not None:
        overall_pass = overall_pass and flow_pass

    details = {
        "networkFile": netf,
        "tripsFile": tripsf,
        "flowsFile": flowsf,
        "numeric_expected": numeric_answer,
        "numeric_value": numeric_value,
        "numeric_pass": numeric_pass,
        "answerFlowsFile": flow_answer,
        "flow_mismatches": flow_mismatches,
        "flow_max_abs_err": flow_max_abs_err,
        "flow_pass": flow_pass,
    }

    # For backward compatibility, return numeric_value and numeric_expected when present; otherwise flow_max_abs_err and 0.0.
    value_out = numeric_value if numeric_value is not None else (flow_max_abs_err if flow_max_abs_err is not None else 0.0)
    expected_out = numeric_answer if numeric_answer is not None else 0.0
    return value_out, expected_out, overall_pass, details


def run_fw_test(spec_path: str) -> Tuple[float, float, bool, Dict]:
    """Run a Frank-Wolfe step size test (numeric only)."""
    netf, tripsf, basef, targetf, step_answer = parse_fw_spec(spec_path)
    net = network.Network(netf, tripsf)
    base_flows = read_flows_file(basef)
    target_flows = read_flows_file(targetf)
    for ij in net.link:
        net.link[ij].flow = base_flows[ij]
    step = net.FrankWolfeStepSize(target_flows, 1e-10)
    passed = approxEqual(step, step_answer, 0.01)
    details = {
        "networkFile": netf,
        "tripsFile": tripsf,
        "baseFlows": basef,
        "targetFlows": targetf,
        "expected_step": step_answer,
        "value_step": step,
        "numeric_pass": passed,
    }
    return step, step_answer, passed, details


def run_shift_test(spec_path: str) -> Tuple[float, float, bool, Dict]:
    """Run a convex-combo shift test comparing per-link flows after shiftFlows."""
    netf, tripsf, basef, targetf, step_size, answerFlows = parse_shift_spec(spec_path)
    net = network.Network(netf, tripsf)
    base_flows = read_flows_file(basef)
    target_flows = read_flows_file(targetf)
    for ij in net.link:
        net.link[ij].flow = base_flows[ij]
    net.shiftFlows(target_flows, step_size)

    answer_flows = read_flows_file(answerFlows)
    mismatches = 0
    max_abs_err = 0.0
    for ij in net.link:
        computed = net.link[ij].flow
        expected = answer_flows.get(ij, None)
        if expected is None:
            mismatches += 1
            max_abs_err = max(max_abs_err, abs(computed))
            continue
        diff = abs(computed - expected)
        max_abs_err = max(max_abs_err, diff)
        if not approxEqual(computed, expected, 0.01):
            mismatches += 1
    passed = mismatches == 0
    details = {
        "networkFile": netf,
        "tripsFile": tripsf,
        "baseFlows": basef,
        "targetFlows": targetf,
        "step_size": step_size,
        "answerFlowsFile": answerFlows,
        "flow_mismatches": mismatches,
        "flow_max_abs_err": max_abs_err,
        "flow_pass": passed,
    }
    return max_abs_err, 0.0, passed, details


def run_ue_test(spec_path: str) -> Tuple[float, float, bool, Dict]:
    """Run a full UE solve and return iterations, final gap, pass status."""
    netf, tripsf, step_rule, max_iters, target_gap, gap_func_name, expected_iters = parse_ue_spec(spec_path)
    net = network.Network(netf, tripsf)
    
    # Get gap function reference
    if not hasattr(net, gap_func_name):
        raise AttributeError(f"Network has no attribute {gap_func_name}")
    gap_func = getattr(net, gap_func_name)
    
    # Solve UE
    net.userEquilibrium(step_rule, max_iters, target_gap, gap_func)
    
    # Extract results from network module's globals (where userEquilibrium sets them)
    rg = network.__dict__.get('relative_gaps', None)
    if rg is not None and len(rg) > 0:
        actual_iters = len(rg)
        final_gap = rg[-1]
    else:
        actual_iters = 0
        final_gap = gap_func()
    
    # Pass/fail based on expected iterations or final gap if provided
    passed = True
    if expected_iters is not None:
        if isinstance(expected_iters, int):
            # Expected iterations
            passed = (actual_iters == expected_iters)
        else:
            # Expected final gap
            passed = approxEqual(final_gap, expected_iters, 0.01)
    
    details = {
        "networkFile": netf,
        "tripsFile": tripsf,
        "step_rule": step_rule,
        "max_iterations": max_iters,
        "target_gap": target_gap,
        "gap_function": gap_func_name,
        "actual_iterations": actual_iters,
        "final_gap": final_gap,
        "expected": expected_iters,
    }
    
    # Return actual_iters as value, expected_iters as expected
    return actual_iters, expected_iters if expected_iters else actual_iters, passed, details


def time_test(spec_path: str, runner: Callable[[], Tuple[float, float, bool, Dict]], runs: int) -> Tuple[float, float, float, float, float, float, Dict]:
    """Time the test over `runs` executions. Returns (time_mean, time_std, value_mean, value_std, final_gap_mean, final_gap_std, details)."""
    times: List[float] = []
    values: List[float] = []
    final_gaps: List[float] = []
    details = None
    for _ in range(runs):
        t0 = time.perf_counter()
        value, answer, passed, details = runner()
        t1 = time.perf_counter()
        times.append(t1 - t0)
        values.append(value)
        final_gap = details.get('final_gap', None)
        if final_gap is not None:
            try:
                final_gaps.append(float(final_gap))
            except (ValueError, TypeError):
                pass
    
    time_mean = statistics.mean(times)
    time_std = statistics.pstdev(times) if len(times) > 1 else 0.0
    
    value_mean = statistics.mean(values) if values else None
    value_std = statistics.pstdev(values) if len(values) > 1 else 0.0
    
    final_gap_mean = statistics.mean(final_gaps) if final_gaps else None
    final_gap_std = statistics.pstdev(final_gaps) if len(final_gaps) > 1 else 0.0
    
    return time_mean, time_std, value_mean, value_std, final_gap_mean, final_gap_std, details


def collect_profile(spec_path: str, runner: Callable[[], Tuple[float, float, bool, Dict]], out_path: str) -> None:
    """Run one invocation under cProfile and write a stats file to out_path."""
    profiler = cProfile.Profile()
    profiler.runcall(runner)
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
    ps.print_stats(80)
    with open(out_path, 'w') as f:
        f.write(s.getvalue())


def main():
    parser = argparse.ArgumentParser(description='Run accuracy + performance protocol for network tests')
    parser.add_argument('--tests', nargs='+', required=True, help='Test spec files to run')
    parser.add_argument('--func', required=False, help='Network method to call (e.g. averageExcessCost, relativeGap). Used for numeric comparisons in auto mode.')
    parser.add_argument('--mode', choices=['auto','fwstep','shift','ue_solve'], default='auto', help='Select test mode: auto (numeric/flow combined), fwstep (Frank-Wolfe step size), shift (convex-combo flow shift), ue_solve (full UE solve timing).')
    parser.add_argument('--network-path', default=None, help='Optional path to an alternative network.py implementation for side-by-side performance/accuracy comparisons.')
    parser.add_argument('--runs', type=int, default=3, help='Number of timing repetitions (default 3)')
    parser.add_argument('--profile', choices=['none','cprofile'], default='none', help='Collect profile for each test')
    parser.add_argument('--profile-dir', default='profiler_output', help='Directory to write profile outputs')
    parser.add_argument('--output', default='test_protocol_results.csv', help='CSV summary output')
    parser.add_argument('--flow-diff-dir', default='flow_diffs', help='Directory to write per-link flow comparison CSVs when flow answers are provided')
    parser.add_argument('--json', default=None, help='Optional JSON details output')
    args = parser.parse_args()

    if args.network_path:
        load_network_override(os.path.normpath(args.network_path))

    os.makedirs(args.profile_dir, exist_ok=True)
    os.makedirs(args.flow_diff_dir, exist_ok=True)

    rows = []
    details_out = {}
    for spec in args.tests:
        spec = os.path.normpath(spec)
        try:
            if args.mode == 'auto':
                runner = lambda sp=spec: run_single_test(sp, args.func)
            elif args.mode == 'fwstep':
                runner = lambda sp=spec: run_fw_test(sp)
            elif args.mode == 'shift':
                runner = lambda sp=spec: run_shift_test(sp)
            elif args.mode == 'ue_solve':
                runner = lambda sp=spec: run_ue_test(sp)
            else:
                raise ValueError(f"Unknown mode {args.mode}")

            time_mean, time_std, value_mean, value_std, final_gap_mean, final_gap_std, _ = time_test(spec, runner, args.runs)
            # Run once more to capture canonical details and pass/fail from the runner
            actual_val, expected, passed, details = runner()

            profile_file = None
            if args.profile == 'cprofile':
                base = os.path.splitext(os.path.basename(spec))[0]
                profile_file = os.path.join(args.profile_dir, f"{base}.prof.txt")
                collect_profile(spec, runner, profile_file)

            # Optional per-link flow diff output when a flow answer is provided (auto/shift modes)
            flow_diff_file = None
            answer_flows_file = details.get('answerFlowsFile','')
            if answer_flows_file:
                base = os.path.splitext(os.path.basename(spec))[0]
                flow_diff_file = os.path.join(args.flow_diff_dir, f"{base}.flows.compare.csv")
                # For auto mode, computed flows come from the flows file specified in the spec
                if args.mode == 'auto':
                    computed_flows = read_flows_file(details['flowsFile'])
                    expected_flows = read_flows_file(answer_flows_file)
                    write_flow_diff_file(flow_diff_file, computed_flows, expected_flows)
                elif args.mode == 'shift':
                    # Reconstruct flows after shift to produce a detailed diff
                    netf, tripsf, basef, targetf, step_size, answerFlows = parse_shift_spec(spec)
                    net = network.Network(netf, tripsf)
                    base_flows = read_flows_file(basef)
                    target_flows = read_flows_file(targetf)
                    for ij in net.link:
                        net.link[ij].flow = base_flows[ij]
                    net.shiftFlows(target_flows, step_size)
                    computed_flows = {ij: net.link[ij].flow for ij in net.link}
                    expected_flows = read_flows_file(answerFlows)
                    write_flow_diff_file(flow_diff_file, computed_flows, expected_flows)

            # For ue_solve mode, use actual_iterations as the primary metric
            if args.mode == 'ue_solve':
                metric_name = 'ue_iterations'
                expected_val = details.get('expected', '')
                actual_val = details.get('actual_iterations', '')
            else:
                metric_name = args.func if args.mode=='auto' else args.mode
                expected_val = details.get('numeric_expected','') or details.get('expected_step','')
                actual_val = details.get('numeric_value','') or details.get('value_step','')

            row = {
                'test_spec': spec,
                'metric': metric_name,
                'expected': expected_val,
                'value_mean': value_mean if value_mean is not None else actual_val,
                'value_std': value_std,
                'numeric_pass': details.get('numeric_pass',''),
                'passed': bool(passed),
                'answer_flows': details.get('answerFlowsFile',''),
                'flow_mismatches': details.get('flow_mismatches',''),
                'flow_max_abs_err': details.get('flow_max_abs_err',''),
                'flow_pass': details.get('flow_pass',''),
                'final_gap_mean': final_gap_mean,
                'final_gap_std': final_gap_std,
                'time_mean_s': time_mean,
                'time_std_s': time_std,
                'runs': args.runs,
                'profile_file': profile_file,
                'flow_diff_file': flow_diff_file,
            }
            rows.append(row)
            details_out[spec] = details
        except utils.NotYetAttemptedException:
            rows.append({'test_spec': spec, 'metric': args.func if args.mode=='auto' else args.mode, 'error': 'NotYetAttempted'})
        except Exception as e:
            rows.append({'test_spec': spec, 'metric': args.func if args.mode=='auto' else args.mode, 'error': str(e)})

    # write CSV
    fieldnames = ['test_spec','metric','expected','value_mean','value_std','numeric_pass','passed','answer_flows','flow_mismatches','flow_max_abs_err','flow_pass','final_gap_mean','final_gap_std','time_mean_s','time_std_s','runs','profile_file','flow_diff_file','error']
    with open(args.output, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    if args.json:
        with open(args.json, 'w') as jf:
            json.dump({'rows': rows, 'details': details_out}, jf, indent=2)

    print(f"Wrote CSV results to {args.output}")
    if args.json:
        print(f"Wrote JSON details to {args.json}")


if __name__ == '__main__':
    main()
