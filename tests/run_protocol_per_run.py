"""Variant of run_protocol.py that logs each run individually (not averaged).

Usage:
  python -m tests.run_protocol_per_run --tests protocol/siouxfalls_ue_fw.txt --mode ue_solve --network-path network_baseline.py --runs 5 --output baseline_per_run.csv
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import time
import importlib.util
import sys
from typing import Dict, Tuple, List, Callable

import network
import utils


def load_network_override(path: str):
    """Dynamically load a network.py alternative and install as the network module."""
    spec = importlib.util.spec_from_file_location("network", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load network module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['network'] = module
    globals()['network'] = module


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
            passed = abs(float(final_gap) / expected_iters - 1) <= 0.01
    
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
    
    return actual_iters, expected_iters if expected_iters else actual_iters, passed, details


def main():
    parser = argparse.ArgumentParser(description='Run UE protocol tests and log each run individually')
    parser.add_argument('--tests', nargs='+', required=True, help='Test spec files to run')
    parser.add_argument('--mode', choices=['auto','fwstep','shift','ue_solve'], default='ue_solve', help='Test mode')
    parser.add_argument('--network-path', default=None, help='Optional path to an alternative network.py implementation')
    parser.add_argument('--runs', type=int, default=3, help='Number of runs (default 3)')
    parser.add_argument('--output', default='test_protocol_per_run.csv', help='CSV summary output')
    args = parser.parse_args()

    if args.network_path:
        load_network_override(os.path.normpath(args.network_path))

    rows = []
    for spec in args.tests:
        spec = os.path.normpath(spec)
        try:
            if args.mode != 'ue_solve':
                raise ValueError("run_protocol_per_run only supports ue_solve mode")
            
            netf, tripsf, step_rule, max_iters, target_gap, gap_func_name, expected_iters = parse_ue_spec(spec)
            
            # Run N times and log each separately
            for run_num in range(1, args.runs + 1):
                t0 = time.perf_counter()
                actual_iters, expected, passed, details = run_ue_test(spec)
                t1 = time.perf_counter()
                elapsed_s = t1 - t0
                
                row = {
                    'test_spec': spec,
                    'run_number': run_num,
                    'gap_function': gap_func_name,
                    'actual_iterations': actual_iters,
                    'final_gap': details.get('final_gap', ''),
                    'time_s': elapsed_s,
                    'passed': bool(passed),
                }
                rows.append(row)
        except Exception as e:
            print(f"Error running {spec}: {e}")
            import traceback
            traceback.print_exc()

    # Write CSV with per-run details
    fieldnames = ['test_spec', 'run_number', 'gap_function', 'actual_iterations', 'final_gap', 'time_s', 'passed']
    with open(args.output, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, '') for k in fieldnames})

    print(f"Wrote per-run results to {args.output}")


if __name__ == '__main__':
    main()
