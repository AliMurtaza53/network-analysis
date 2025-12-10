"""Benchmark script to compare label-setting vs heap-based shortest path
on the SiouxFalls network. Produces average runtime for `allOrNothing`.

Run from project root:
    python bench\benchmark_siouxfalls.py
"""
import time
import os
import sys
# Ensure project root (parent of this bench folder) is on sys.path so imports like
# `from network import Network` work when running the script directly.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from network import Network

NET_FILE = os.path.join(os.path.dirname(__file__), '..', 'SiouxFalls_net.tntp')
TRIPS_FILE = os.path.join(os.path.dirname(__file__), '..', 'SiouxFalls_trips.tntp')

TRIALS = 3


def time_all_or_nothing(net, use_heap=True):
    # Warm-up
    net.allOrNothing(use_heap=use_heap)
    start = time.perf_counter()
    for _ in range(1):
        net.allOrNothing(use_heap=use_heap)
    end = time.perf_counter()
    return end - start


def main():
    net_path = os.path.abspath(NET_FILE)
    trips_path = os.path.abspath(TRIPS_FILE)
    print('Loading network from: ', net_path)
    net = Network(net_path, trips_path)

    times_label = []
    times_heap = []

    for i in range(TRIALS):
        t = time_all_or_nothing(net, use_heap=False)
        times_label.append(t)
        print(f'Trial {i+1} label-setting: {t:.6f} s')

    for i in range(TRIALS):
        t = time_all_or_nothing(net, use_heap=True)
        times_heap.append(t)
        print(f'Trial {i+1} heap Dijkstra: {t:.6f} s')

    avg_label = sum(times_label) / len(times_label)
    avg_heap = sum(times_heap) / len(times_heap)

    print('\nResults (average over {} trials):'.format(TRIALS))
    print(f'  Label-setting all-or-nothing: {avg_label:.6f} s')
    print(f'  Heap Dijkstra all-or-nothing: {avg_heap:.6f} s')
    if avg_heap > 0:
        print(f'  Speedup (label / heap): {avg_label/avg_heap:.2f}x')

    # Optional CSV output
    outcsv = os.path.join(os.path.dirname(__file__), '..', 'bench_results_siouxfalls.csv')
    with open(outcsv, 'w') as f:
        f.write('method,trial,seconds\n')
        for i, t in enumerate(times_label, 1):
            f.write(f'label,{i},{t:.6f}\n')
        for i, t in enumerate(times_heap, 1):
            f.write(f'heap,{i},{t:.6f}\n')
    print('CSV written to', outcsv)


if __name__ == '__main__':
    main()
