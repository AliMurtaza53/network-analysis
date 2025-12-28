"""Run run_protocol twice with two network implementations and compare results.

Usage:
  python -m tests.compare_networks \
    --tests tests/protocol/siouxfalls_10_aec.txt tests/protocol/siouxfalls_eqm_aec.txt \
    --mode auto \
    --func averageExcessCost \
    --network-a path/to/network_baseline.py \
    --network-b path/to/network_candidate.py \
    --runs 5 \
    --out-a baseline.csv \
    --out-b candidate.csv \
    --comparison comparison.csv \
    --format markdown

Notes:
- network-a/b are optional; if omitted, uses current network.py for both (useful for deterministic smoke).
- mode can be auto|fwstep|shift; func is required for auto.
- Comparison exits with non-zero if accuracy regressions are detected (via compare_results).
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import os
from typing import List


def run_cmd(cmd: List[str]):
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description='Compare two network implementations using run_protocol outputs')
    parser.add_argument('--tests', nargs='+', required=True, help='Spec files')
    parser.add_argument('--mode', choices=['auto','fwstep','shift'], default='auto')
    parser.add_argument('--func', required=False, help='Network method (required for auto)')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--network-a', default=None, help='network.py path for baseline')
    parser.add_argument('--network-b', default=None, help='network.py path for candidate')
    parser.add_argument('--out-a', default='baseline.csv')
    parser.add_argument('--out-b', default='candidate.csv')
    parser.add_argument('--comparison', default='comparison.csv')
    parser.add_argument('--format', choices=['csv','markdown'], default='csv')
    parser.add_argument('--profile', choices=['none','cprofile'], default='none')
    args = parser.parse_args()

    if args.mode == 'auto' and not args.func:
        parser.error('--func is required in auto mode')

    base_cmd = [sys.executable, '-m', 'tests.run_protocol', '--mode', args.mode, '--runs', str(args.runs), '--profile', args.profile]
    if args.func:
        base_cmd += ['--func', args.func]
    base_cmd += ['--tests'] + args.tests

    cmd_a = base_cmd + ['--output', args.out_a]
    if args.network_a:
        cmd_a += ['--network-path', os.path.normpath(args.network_a)]

    cmd_b = base_cmd + ['--output', args.out_b]
    if args.network_b:
        cmd_b += ['--network-path', os.path.normpath(args.network_b)]

    run_cmd(cmd_a)
    run_cmd(cmd_b)

    compare_cmd = [sys.executable, '-m', 'tests.compare_results', args.out_a, args.out_b]
    if args.format == 'markdown':
        compare_cmd += ['--format', 'markdown']
    else:
        compare_cmd += ['--output', args.comparison]
    run_cmd(compare_cmd)


if __name__ == '__main__':
    main()
