"""Entry point: run Q2 and Q3 in sequence.

Usage:
    python run_all.py [--config config/anaheim.yaml] [--morris-n 10] [--skip-recovery]
"""
import subprocess
import sys
import argparse
import time

def run(cmd, label):
    t0 = time.time()
    print(f"\n{'='*60}")
    print(f"Starting {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, check=True)
    print(f"{label} done in {time.time()-t0:.0f}s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/anaheim.yaml')
    parser.add_argument('--morris-n', type=int, default=10)
    parser.add_argument('--skip-recovery', action='store_true')
    args = parser.parse_args()

    q2_cmd = [sys.executable, 'scripts/run_q2.py', '--config', args.config]
    if args.skip_recovery:
        q2_cmd.append('--skip-recovery')

    q3_cmd = [sys.executable, 'scripts/run_q3.py', '--config', args.config,
              '--morris-n', str(args.morris_n)]

    run(q2_cmd, 'Q2: disruption scenarios')
    run(q3_cmd, 'Q3: sensitivity analysis')

    print("\nAll done. Outputs in outputs/q2/ and outputs/q3/")


if __name__ == '__main__':
    main()
