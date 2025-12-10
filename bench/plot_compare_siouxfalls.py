"""Plot comparison of label-setting vs heap Dijkstra equilibrium runs.
Reads CSVs produced by `run_compare_equilibrium_siouxfalls.py` and writes:
 - `bench/siouxfalls_gap_plot.png`
 - `bench/summary_siouxfalls.txt` (text summary)

Run from project root:
    python bench\plot_compare_siouxfalls.py
"""
import os
import sys
import csv
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
label_csv = os.path.join(project_root, 'bench_results_siouxfalls_label.csv')
heap_csv = os.path.join(project_root, 'bench_results_siouxfalls_heap.csv')
summary_csv = os.path.join(project_root, 'bench_results_siouxfalls_compare.csv')
out_png = os.path.join(project_root, 'bench', 'siouxfalls_gap_plot.png')
out_summary = os.path.join(project_root, 'bench', 'summary_siouxfalls.txt')

def read_gap_csv(path):
    iters = []
    gaps = []
    if not os.path.exists(path):
        return iters, gaps
    with open(path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            try:
                it = int(row[0])
                gap = float(row[2])
            except Exception:
                continue
            iters.append(it)
            gaps.append(gap)
    return iters, gaps

iters_label, gaps_label = read_gap_csv(label_csv)
iters_heap, gaps_heap = read_gap_csv(heap_csv)

# Basic plot: relative gap vs iteration (log scale) for both methods
plt.figure(figsize=(10,6))
if iters_label and gaps_label:
    plt.semilogy(iters_label, gaps_label, label='label-setting', alpha=0.8)
if iters_heap and gaps_heap:
    plt.semilogy(iters_heap, gaps_heap, label='heap-dijkstra', alpha=0.8)

plt.xlabel('Iteration')
plt.ylabel('Relative gap (log scale)')
plt.title('SiouxFalls: Relative gap vs iteration (label-setting vs heap)')
plt.grid(True, which='both', ls='--', lw=0.5)
plt.legend()
plt.tight_layout()

# Ensure output folder exists
os.makedirs(os.path.dirname(out_png), exist_ok=True)
plt.savefig(out_png, dpi=150)
plt.close()

# Compose a short text summary
final_label = gaps_label[-1] if gaps_label else None
final_heap = gaps_heap[-1] if gaps_heap else None

# Read compare CSV for runtimes if available
runtimes = {}
if os.path.exists(summary_csv):
    with open(summary_csv, 'r') as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row:
                continue
            if row[0].lower() in ('label', 'heap'):
                runtimes[row[0].lower()] = (row[1], row[2], row[3] if len(row) > 3 else '')

with open(out_summary, 'w') as f:
    f.write('SiouxFalls equilibrium comparison summary\n')
    f.write('========================================\n\n')
    if final_label is not None:
        f.write(f'Label-setting final relative gap: {final_label:.6e}\n')
    else:
        f.write('Label-setting data not available.\n')
    if final_heap is not None:
        f.write(f'Heap-Dijkstra final relative gap: {final_heap:.6e}\n')
    else:
        f.write('Heap data not available.\n')
    f.write('\n')
    if 'label' in runtimes:
        f.write(f"Label runtime (from compare CSV): {runtimes['label'][0]} s, iterations {runtimes['label'][1]}\n")
    if 'heap' in runtimes:
        f.write(f"Heap runtime (from compare CSV): {runtimes['heap'][0]} s, iterations {runtimes['heap'][1]}\n")
    f.write('\n')
    if final_label is not None and final_heap is not None:
        try:
            ratio = float(final_label) / float(final_heap) if final_heap > 0 else float('inf')
            f.write(f'Relative gap ratio (label / heap): {ratio:.3f}x\n')
        except Exception:
            pass
    f.write('\nNotes:\n- Both runs used MSA step-size (1/(k+1)).\n- CSVs used: ' + label_csv + ', ' + heap_csv + '\n')

print('Plot saved to:', out_png)
print('Summary saved to:', out_summary)
