"""Run and compare user equilibrium (MSA) using label-setting vs heap Dijkstra.

This script runs two full equilibrium experiments on SiouxFalls with
`maxIterations=10000` and writes two CSVs:
 - `bench_results_siouxfalls_label.csv`
 - `bench_results_siouxfalls_heap.csv`

It also writes `bench_results_siouxfalls_compare.csv` with a short summary.

Run from project root:
    python bench\run_compare_equilibrium_siouxfalls.py
"""
import os
import sys
import time
import importlib

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from network import Network
import network as network_module

NET_FILE = os.path.join(project_root, 'SiouxFalls_net.tntp')
TRIPS_FILE = os.path.join(project_root, 'SiouxFalls_trips.tntp')
OUT_LABEL = os.path.join(project_root, 'bench_results_siouxfalls_label.csv')
OUT_HEAP = os.path.join(project_root, 'bench_results_siouxfalls_heap.csv')
OUT_SUMMARY = os.path.join(project_root, 'bench_results_siouxfalls_compare.csv')

MAX_ITER = 10000


def run_mode(mode_name, patch_label=False):
    """Run userEquilibrium for mode_name. If patch_label is True, force label-setting.

    Returns (elapsed_seconds, iteration_times_list, relative_gaps_list)
    """
    # reload module to clear any leftover globals/state
    importlib.reload(network_module)
    NetworkClass = network_module.Network

    orig_all = NetworkClass.allOrNothing

    if patch_label:
        # wrap original to call with use_heap=False
        def allornothing_label(self):
            return orig_all(self, use_heap=False)
        NetworkClass.allOrNothing = allornothing_label
    else:
        # ensure default calls use heap (explicit wrapper calling use_heap=True)
        def allornothing_heap(self):
            return orig_all(self, use_heap=True)
        NetworkClass.allOrNothing = allornothing_heap

    # instantiate fresh network
    net = NetworkClass(NET_FILE, TRIPS_FILE)

    # clear recording lists if present
    network_module.iteration_times = []
    network_module.relative_gaps = []

    print(f"Starting {mode_name} run (max {MAX_ITER} iterations)...")
    t0 = time.perf_counter()
    net.userEquilibrium(stepSizeRule='MSA', maxIterations=MAX_ITER, targetGap=0)
    t1 = time.perf_counter()

    it_times = getattr(network_module, 'iteration_times', [])
    gaps = getattr(network_module, 'relative_gaps', [])

    # restore original method
    NetworkClass.allOrNothing = orig_all

    elapsed = t1 - t0
    return elapsed, it_times, gaps


def write_csv(path, it_times, gaps):
    with open(path, 'w') as f:
        f.write('iteration,cumulative_seconds,relative_gap\n')
        for i, (t, g) in enumerate(zip(it_times, gaps), 1):
            f.write(f'{i},{t:.10f},{g:.12e}\n')


def main():
    # Run label-setting (patch)
    elapsed_label, it_times_label, gaps_label = run_mode('label-setting', patch_label=True)
    print(f'label-setting done: {elapsed_label:.1f}s, iterations={len(it_times_label)}')
    write_csv(OUT_LABEL, it_times_label, gaps_label)

    # Run heap (default)
    elapsed_heap, it_times_heap, gaps_heap = run_mode('heap-dijkstra', patch_label=False)
    print(f'heap-dijkstra done: {elapsed_heap:.1f}s, iterations={len(it_times_heap)}')
    write_csv(OUT_HEAP, it_times_heap, gaps_heap)

    # Write comparison summary
    with open(OUT_SUMMARY, 'w') as f:
        f.write('mode,total_seconds,iterations,final_gap\n')
        f.write(f'label,{elapsed_label:.6f},{len(it_times_label)},{gaps_label[-1] if gaps_label else ''}\n')
        f.write(f'heap,{elapsed_heap:.6f},{len(it_times_heap)},{gaps_heap[-1] if gaps_heap else ''}\n')

    print('CSV outputs:')
    print(' ', OUT_LABEL)
    print(' ', OUT_HEAP)
    print(' ', OUT_SUMMARY)


if __name__ == '__main__':
    main()
