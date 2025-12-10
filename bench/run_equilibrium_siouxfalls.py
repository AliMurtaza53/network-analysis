"""Run a long user-equilibrium on the SiouxFalls network and save iteration results.

This script will overwrite `bench_results_siouxfalls.csv` in the project root's
`bench/` folder with the iteration number, cumulative time (s), and relative gap.

Run: python bench\run_equilibrium_siouxfalls.py
"""
import os
import sys
import time

# Ensure project root on path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from network import Network

NET_FILE = os.path.join(project_root, 'SiouxFalls_net.tntp')
TRIPS_FILE = os.path.join(project_root, 'SiouxFalls_trips.tntp')
OUT_CSV = os.path.join(project_root, 'bench_results_siouxfalls.csv')

MAX_ITER = 10000


def main():
    print('Loading network...')
    net = Network(NET_FILE, TRIPS_FILE)

    print(f'Running user equilibrium for {MAX_ITER} iterations (MSA step)...')
    start_all = time.perf_counter()
    # Run with MSA and targetGap=0 to force full iterations unless gap == 0
    net.userEquilibrium(stepSizeRule='MSA', maxIterations=MAX_ITER, targetGap=0)
    end_all = time.perf_counter()

    # The network.userEquilibrium populates global lists `iteration_times` and `relative_gaps`.
    try:
        from network import iteration_times, relative_gaps
    except Exception:
        iteration_times = []
        relative_gaps = []

    total_time = end_all - start_all
    final_gap = relative_gaps[-1] if relative_gaps else None

    # Overwrite CSV with iteration,time,gap (time is cumulative duration recorded per iteration by the algorithm)
    print(f'Writing results to {OUT_CSV} (will overwrite)')
    with open(OUT_CSV, 'w') as f:
        f.write('iteration,cumulative_seconds,relative_gap\n')
        for i, (t, g) in enumerate(zip(iteration_times, relative_gaps), 1):
            f.write(f'{i},{t:.6f},{g:.12f}\n')
        # If iteration_times shorter than MAX_ITER (due to early stop), note final summary
        f.write(f'# total_runtime,{total_time:.6f},final_gap,{final_gap}\n')

    print('Done.')
    print(f'Total runtime: {total_time:.3f} s')
    print(f'Final relative gap: {final_gap}')
    print(f'CSV overwritten: {OUT_CSV}')


if __name__ == '__main__':
    main()
