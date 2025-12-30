"""Quick validation script for candidate network.py changes.

Checks:
  1. Basic unit tests (tests.py + grader.py pass/fail)
  2. UE solve performance (timing, convergence)
  3. Final equilibrium flows (saved to CSV for inspection)

Usage:
  python validate.py                    # Run all checks with defaults (SiouxFalls, FW, 3 runs)
  python validate.py --skip-tests       # Skip unit tests, just do UE solve + flows
  python validate.py --network ../my_network.py --step-rule MSA --runs 5

Outputs:
  - Console: test pass/fail summary + UE metrics
  - CSV: final_flows_<timestamp>.csv with equilibrium flows
"""
from __future__ import annotations
import sys
import traceback
from datetime import datetime
import csv
import statistics
import time
import gc
from typing import Dict, Tuple, Callable

# ============================================================================
# SECTION 1: Unit test runner (from grader.py + tests.py)
# ============================================================================

def run_unit_tests() -> Tuple[bool, Dict[str, Tuple[int, int]]]:
    """Run basic unit tests from tests/ directory.
    
    Returns: (all_passed, scores_dict)
      all_passed: True if all tests passed
      scores_dict: {category: (score, possible), ...}
    """
    print("\n" + "="*70)
    print("SECTION 1: Unit Tests")
    print("="*70)
    
    try:
        # Import tests module from root (bypass tests/ package)
        import importlib.util
        spec = importlib.util.spec_from_file_location("tests_module", "tests.py")
        if spec is None or spec.loader is None:
            raise ImportError("Could not load tests.py")
        tests_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tests_module)
        
        # Import grader normally
        import grader
    except (ImportError, AttributeError) as e:
        print(f"ERROR: Could not import tests module: {e}")
        print("(Skipping unit tests. Use --skip-tests to suppress this message.)")
        return True, {}  # Don't fail if tests module not available
    
    scores = {}
    
    # Run relative gap tests
    print("\n[1/4] Relative gap tests...", end=' ', flush=True)
    score, possible = grader.runTests(tests_module.relativeGap, "tests/relativegap/")
    scores['Relative gap'] = (score, possible)
    print(f"{score}/{possible}")
    
    # Run average excess cost tests
    print("[2/4] Average excess cost tests...", end=' ', flush=True)
    score, possible = grader.runTests(tests_module.averageExcessCost, "tests/aec/")
    scores['Average excess cost'] = (score, possible)
    print(f"{score}/{possible}")
    
    # Run convex combination tests
    print("[3/4] Convex combination tests...", end=' ', flush=True)
    score, possible = grader.runTests(tests_module.convexCombination, "tests/convexcombo/")
    scores['Convex combination'] = (score, possible)
    print(f"{score}/{possible}")
    
    # Run Frank-Wolfe step size tests
    print("[4/4] Frank-Wolfe step size tests...", end=' ', flush=True)
    score, possible = grader.runTests(tests_module.frankWolfe, "tests/fwstepsize/")
    scores['Frank-Wolfe step size'] = (score, possible)
    print(f"{score}/{possible}")
    
    # Summary
    total_score = sum(s[0] for s in scores.values())
    total_possible = sum(s[1] for s in scores.values())
    all_passed = (total_score == total_possible)
    
    print("\n" + "-"*70)
    print(f"UNIT TESTS: {total_score}/{total_possible}", end='')
    print(" PASS" if all_passed else " FAIL")
    print("-"*70)
    
    return all_passed, scores


# ============================================================================
# SECTION 2: UE solver with flow export
# ============================================================================

def run_ue_solve(network_file: str, trips_file: str, step_rule: str,
                 num_runs: int = 3) -> Tuple[Dict, Tuple[float, float], Tuple[float, float]]:
    """Run UE solve multiple times, return flows + metrics.
    
    Args:
        network_file: Path to TNTP network file
        trips_file: Path to TNTP trips file
        step_rule: "FW" or "MSA"
        num_runs: Number of runs to average over
    
    Returns:
        (final_flows, (gap_mean, gap_std), (time_mean, time_std))
    """
    print("\n" + "="*70)
    print("SECTION 2: UE Solve (Frank-Wolfe Algorithm)")
    print("="*70)
    print(f"\nNetwork: {network_file}")
    print(f"Trips: {trips_file}")
    print(f"Step rule: {step_rule}")
    print(f"Runs: {num_runs}\n")
    
    import network
    import os
    
    gaps = []
    times = []
    final_flows = None
    
    for run_num in range(1, num_runs + 1):
        print(f"  Run {run_num}/{num_runs}...", end=' ', flush=True)
        
        # Create fresh network instance
        net = network.Network(network_file, trips_file)
        
        # Suppress iteration printouts by redirecting to devnull
        # (Note: console output adds ~0-5% overhead, so we suppress it)
        old_stdout = sys.stdout
        devnull = open(os.devnull, 'w')
        sys.stdout = devnull
        
        # Solve UE
        t0 = time.time()
        net.userEquilibrium(
            stepSizeRule=step_rule,
            maxIterations=int(1e6),
            targetGap=1e-4,
            gapFunction=net.relativeGap
        )
        elapsed = time.time() - t0
        
        # Restore stdout
        sys.stdout = old_stdout
        devnull.close()
        
        gap = net.relativeGap()
        gaps.append(gap)
        times.append(elapsed)
        
        print(f"gap={gap:.6f}, time={elapsed:.1f}s")
        
        # Save flows from last run
        final_flows = {link_id: link.flow for link_id, link in net.link.items()}
        
        # Explicitly clean up network object to free memory
        del net
        gc.collect()
    
    # Compute statistics
    gap_mean = statistics.mean(gaps)
    gap_std = statistics.stdev(gaps) if num_runs > 1 else 0.0
    time_mean = statistics.mean(times)
    time_std = statistics.stdev(times) if num_runs > 1 else 0.0
    
    print("\n" + "-"*70)
    print(f"Final gap:    {gap_mean:.8f} ± {gap_std:.8f}")
    print(f"Solve time:   {time_mean:.2f}s ± {time_std:.2f}s")
    print("-"*70)
    
    return final_flows, (gap_mean, gap_std), (time_mean, time_std)


def save_flows(flows: Dict[str, float], output_file: str) -> None:
    """Save flows to CSV file."""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['link_id', 'flow'])
        for link_id in sorted(flows.keys()):
            writer.writerow([link_id, flows[link_id]])
    print(f"\nFlows saved to {output_file}")


# ============================================================================
# SECTION 3: Main entry point
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Quick validation of candidate network.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate.py                          # Full validation with defaults (SiouxFalls, FW, 3 runs)
  python validate.py --skip-tests             # UE solve only, no unit tests
  python validate.py --network network_candidate.py
  python validate.py --net-file Anaheim_net.txt --trips-file Anaheim_trips.txt
  python validate.py --step-rule MSA --runs 5
        """
    )
    parser.add_argument('--skip-tests', action='store_true',
                        help='Skip unit tests, only run UE solve')
    parser.add_argument('--network', default='network.py',
                        help='Path to network.py candidate (default: network.py)')
    parser.add_argument('--net-file', default='tests/SiouxFalls_net.txt',
                        help='Network file path (default: tests/SiouxFalls_net.txt)')
    parser.add_argument('--trips-file', default='tests/SiouxFalls_trips.txt',
                        help='Trips file path (default: tests/SiouxFalls_trips.txt)')
    parser.add_argument('--step-rule', choices=['FW', 'MSA'], default='FW',
                        help='Step size rule (default: FW)')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of UE runs to average (default: 3)')
    parser.add_argument('--no-flows', action='store_true',
                        help='Skip flow export')
    
    args = parser.parse_args()
    
    # Inject candidate network if not default
    if args.network != 'network.py':
        import importlib.util
        spec = importlib.util.spec_from_file_location("network", args.network)
        if spec is None or spec.loader is None:
            print(f"ERROR: Could not load {args.network}")
            sys.exit(1)
        module = importlib.util.module_from_spec(spec)
        sys.modules['network'] = module
        spec.loader.exec_module(module)
    
    exit_code = 0
    
    # Run unit tests unless skipped
    if not args.skip_tests:
        try:
            all_passed, scores = run_unit_tests()
            if not all_passed:
                exit_code = 1
        except Exception as e:
            print(f"\nERROR in unit tests: {e}")
            traceback.print_exc()
            exit_code = 1
    
    # Run UE solve
    try:
        final_flows, (gap_mean, gap_std), (time_mean, time_std) = run_ue_solve(
            network_file=args.net_file,
            trips_file=args.trips_file,
            step_rule=args.step_rule,
            num_runs=args.runs
        )
        
        # Save flows unless skipped
        if not args.no_flows:
            timestamp = datetime.now().strftime("%m%d_%H%M")
            # Extract network module name (e.g., "network_base" from "network_base.py")
            import os
            network_name = os.path.splitext(os.path.basename(args.network))[0]
            # Extract network file name (e.g., "SiouxFalls" from "tests/SiouxFalls_net.txt")
            net_basename = os.path.splitext(os.path.basename(args.net_file))[0]
            # Remove "_net" suffix if present
            net_basename = net_basename.replace("_net", "")
            output_file = f"ue_flows_{network_name}_{net_basename}_{timestamp}.csv"
            save_flows(final_flows, output_file)
    
    except Exception as e:
        print(f"\nERROR in UE solve: {e}")
        traceback.print_exc()
        exit_code = 1
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("PASS: Validation complete")
    else:
        print("FAIL: Validation failed (see above)")
    print("="*70 + "\n")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
