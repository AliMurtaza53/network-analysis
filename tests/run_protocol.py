"""Lightweight test protocol runner for accuracy + performance.

Usage examples (run from repo root):
  python -m tests.run_protocol --tests tests/aec/4-SiouxFalls_10.txt --func averageExcessCost --runs 5 --output results.csv
  python -m tests.run_protocol --tests tests/aec/4-SiouxFalls_10.txt tests/aec/5-SiouxFalls_eqm.txt --func averageExcessCost --profile cprofile --profile-dir profs

Test spec file format (non-comment lines):
  Line 1: network file path
  Line 2: trips file path
  Line 3: flows file path
  Line 4: expected answer (float)

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
from typing import Dict, Tuple, List

import network
import utils


def approxEqual(value, target, tolerance):
    """Check if value is approximately equal to target within tolerance."""
    if (abs(target) <= tolerance): 
        return abs(value) <= tolerance
    return abs(float(value) / target - 1) <= tolerance


def parse_aec_or_relativegap_spec(path: str) -> Tuple[str, str, str, float]:
    """Parse a simple spec file used by `aec` and `relativegap` tests.

    Returns: (networkFile, tripsFile, flowsFile, answer)
    """
    networkFile = None
    tripsFile = None
    flowsFile = None
    answer = None
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
            if answer is None:
                answer = float(line.strip())
                continue
    return networkFile, tripsFile, flowsFile, answer


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

    details contains: networkFile, tripsFile, flowsFile.
    """
    netf, tripsf, flowsf, answer = parse_aec_or_relativegap_spec(spec_path)
    net = network.Network(netf, tripsf)
    flows = read_flows_file(flowsf)
    for ij in net.link:
        net.link[ij].flow = flows[ij]
        net.link[ij].updateCost()
    # call the requested function / metric on network
    if not hasattr(net, func_name):
        raise AttributeError(f"Network has no attribute {func_name}")
    metric_func = getattr(net, func_name)
    value = metric_func()
    passed = approxEqual(value, answer, 0.01)
    details = {
        "networkFile": netf,
        "tripsFile": tripsf,
        "flowsFile": flowsf,
        "expected": answer,
    }
    return value, answer, passed, details


def time_test(spec_path: str, func_name: str, runs: int) -> Tuple[float, float, float, Dict]:
    """Time the test over `runs` executions. Returns (mean, std, last_value, details)

    details are the same as run_single_test details.
    """
    times: List[float] = []
    last_value = None
    details = None
    for i in range(runs):
        t0 = time.perf_counter()
        value, answer, passed, details = run_single_test(spec_path, func_name)
        t1 = time.perf_counter()
        times.append(t1 - t0)
        last_value = value
    mean = statistics.mean(times)
    std = statistics.pstdev(times) if len(times) > 1 else 0.0
    return mean, std, last_value, details


def collect_profile(spec_path: str, func_name: str, out_path: str) -> None:
    """Run one invocation under cProfile and write a stats file to out_path."""
    profiler = cProfile.Profile()
    def target():
        run_single_test(spec_path, func_name)
    profiler.runcall(target)
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
    ps.print_stats(80)
    with open(out_path, 'w') as f:
        f.write(s.getvalue())


def main():
    parser = argparse.ArgumentParser(description='Run accuracy + performance protocol for network tests')
    parser.add_argument('--tests', nargs='+', required=True, help='Test spec files to run')
    parser.add_argument('--func', required=True, help='Network method to call (e.g. averageExcessCost, relativeGap)')
    parser.add_argument('--runs', type=int, default=3, help='Number of timing repetitions (default 3)')
    parser.add_argument('--profile', choices=['none','cprofile'], default='none', help='Collect profile for each test')
    parser.add_argument('--profile-dir', default='profiler_output', help='Directory to write profile outputs')
    parser.add_argument('--output', default='test_protocol_results.csv', help='CSV summary output')
    parser.add_argument('--json', default=None, help='Optional JSON details output')
    args = parser.parse_args()

    os.makedirs(args.profile_dir, exist_ok=True)

    rows = []
    details_out = {}
    for spec in args.tests:
        spec = os.path.normpath(spec)
        try:
            mean, std, last_value, details = time_test(spec, args.func, args.runs)
            value, expected, passed, _ = run_single_test(spec, args.func)
            profile_file = None
            if args.profile == 'cprofile':
                base = os.path.splitext(os.path.basename(spec))[0]
                profile_file = os.path.join(args.profile_dir, f"{base}.prof.txt")
                collect_profile(spec, args.func, profile_file)
            row = {
                'test_spec': spec,
                'metric': args.func,
                'expected': expected,
                'value': value,
                'passed': bool(passed),
                'time_mean_s': mean,
                'time_std_s': std,
                'runs': args.runs,
                'profile_file': profile_file,
            }
            rows.append(row)
            details_out[spec] = details
        except utils.NotYetAttemptedException:
            rows.append({'test_spec': spec, 'metric': args.func, 'error': 'NotYetAttempted'})
        except Exception as e:
            rows.append({'test_spec': spec, 'metric': args.func, 'error': str(e)})

    # write CSV
    fieldnames = ['test_spec','metric','expected','value','passed','time_mean_s','time_std_s','runs','profile_file','error']
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
