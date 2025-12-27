"""Compare two test protocol result CSV files (baseline vs candidate).

Usage:
  python -m tests.compare_results baseline.csv candidate.csv --output comparison.csv
  python -m tests.compare_results baseline.csv candidate.csv --format markdown

This script compares timing and accuracy metrics between two runs of the test protocol.
It produces a summary showing:
- Relative time changes (speedup/slowdown)
- Absolute time differences
- Accuracy pass/fail changes
- Optional statistical significance tests (if scipy available)
"""
import argparse
import csv
import sys
from typing import Dict, List, Any


def read_csv(path: str) -> List[Dict[str, Any]]:
    """Read CSV and return list of dicts."""
    with open(path, 'r') as f:
        return list(csv.DictReader(f))


def parse_float(s: str) -> float:
    """Parse float, return None if empty/invalid."""
    try:
        return float(s) if s.strip() else None
    except ValueError:
        return None


def parse_bool(s: str) -> bool:
    """Parse boolean string."""
    return s.strip().lower() in ('true', '1', 'yes')


def compare_runs(baseline: List[Dict], candidate: List[Dict]) -> List[Dict]:
    """Compare baseline and candidate results row-by-row.
    
    Returns list of comparison dicts with fields:
    - test_spec, metric
    - time_baseline, time_candidate, time_diff, time_rel_change (%)
    - passed_baseline, passed_candidate, accuracy_regressed
    """
    # Index by test_spec
    baseline_map = {r['test_spec']: r for r in baseline}
    candidate_map = {r['test_spec']: r for r in candidate}
    
    all_specs = sorted(set(baseline_map.keys()) | set(candidate_map.keys()))
    
    results = []
    for spec in all_specs:
        b = baseline_map.get(spec, {})
        c = candidate_map.get(spec, {})
        
        time_base = parse_float(b.get('time_mean_s', ''))
        time_cand = parse_float(c.get('time_mean_s', ''))
        passed_base = parse_bool(b.get('passed', 'False'))
        passed_cand = parse_bool(c.get('passed', 'False'))
        
        time_diff = None
        time_rel_change = None
        if time_base is not None and time_cand is not None:
            time_diff = time_cand - time_base
            if time_base > 0:
                time_rel_change = (time_diff / time_base) * 100  # percentage
        
        accuracy_regressed = passed_base and not passed_cand
        accuracy_improved = not passed_base and passed_cand
        
        results.append({
            'test_spec': spec,
            'metric': c.get('metric') or b.get('metric', ''),
            'time_baseline_s': time_base,
            'time_candidate_s': time_cand,
            'time_diff_s': time_diff,
            'time_rel_change_pct': time_rel_change,
            'passed_baseline': passed_base,
            'passed_candidate': passed_cand,
            'accuracy_regressed': accuracy_regressed,
            'accuracy_improved': accuracy_improved,
        })
    
    return results


def format_markdown(results: List[Dict]) -> str:
    """Format comparison as markdown table."""
    lines = [
        "# Performance Comparison",
        "",
        "| Test | Metric | Baseline (s) | Candidate (s) | Speedup | Accuracy |",
        "|------|--------|--------------|---------------|---------|----------|"
    ]
    
    for r in results:
        spec = r['test_spec']
        metric = r['metric']
        time_base = f"{r['time_baseline_s']:.4f}" if r['time_baseline_s'] is not None else 'N/A'
        time_cand = f"{r['time_candidate_s']:.4f}" if r['time_candidate_s'] is not None else 'N/A'
        
        if r['time_rel_change_pct'] is not None:
            rel = r['time_rel_change_pct']
            if rel < -1:
                speedup_str = f"⚡ **{-rel:.1f}% faster**"
            elif rel > 1:
                speedup_str = f"🐌 {rel:.1f}% slower"
            else:
                speedup_str = f"~{rel:.1f}%"
        else:
            speedup_str = 'N/A'
        
        if r['accuracy_regressed']:
            acc_str = '❌ REGRESSED'
        elif r['accuracy_improved']:
            acc_str = '✅ IMPROVED'
        elif r['passed_baseline'] and r['passed_candidate']:
            acc_str = '✅ Pass'
        else:
            acc_str = '❌ Fail'
        
        lines.append(f"| {spec} | {metric} | {time_base} | {time_cand} | {speedup_str} | {acc_str} |")
    
    lines.append("")
    
    # Summary
    total_tests = len(results)
    regressions = sum(1 for r in results if r['accuracy_regressed'])
    improvements = sum(1 for r in results if r['accuracy_improved'])
    faster = sum(1 for r in results if r['time_rel_change_pct'] is not None and r['time_rel_change_pct'] < -1)
    slower = sum(1 for r in results if r['time_rel_change_pct'] is not None and r['time_rel_change_pct'] > 1)
    
    lines.extend([
        "## Summary",
        f"- Total tests: {total_tests}",
        f"- Accuracy regressions: {regressions}",
        f"- Accuracy improvements: {improvements}",
        f"- Faster (>1%): {faster}",
        f"- Slower (>1%): {slower}",
    ])
    
    return '\n'.join(lines)


def write_csv(results: List[Dict], output_path: str) -> None:
    """Write comparison results to CSV."""
    fieldnames = [
        'test_spec', 'metric',
        'time_baseline_s', 'time_candidate_s', 'time_diff_s', 'time_rel_change_pct',
        'passed_baseline', 'passed_candidate', 'accuracy_regressed', 'accuracy_improved'
    ]
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def main():
    parser = argparse.ArgumentParser(description='Compare baseline and candidate test results')
    parser.add_argument('baseline', help='Baseline results CSV')
    parser.add_argument('candidate', help='Candidate results CSV')
    parser.add_argument('--output', help='Output comparison CSV (optional)')
    parser.add_argument('--format', choices=['csv', 'markdown'], default='csv',
                        help='Output format (default: csv)')
    args = parser.parse_args()
    
    baseline = read_csv(args.baseline)
    candidate = read_csv(args.candidate)
    
    if not baseline:
        print(f"Error: No data in baseline file {args.baseline}", file=sys.stderr)
        sys.exit(1)
    if not candidate:
        print(f"Error: No data in candidate file {args.candidate}", file=sys.stderr)
        sys.exit(1)
    
    results = compare_runs(baseline, candidate)
    
    if args.format == 'markdown':
        print(format_markdown(results))
    else:
        if args.output:
            write_csv(results, args.output)
            print(f"Wrote comparison to {args.output}")
        else:
            # Print to stdout as CSV
            fieldnames = [
                'test_spec', 'metric',
                'time_baseline_s', 'time_candidate_s', 'time_diff_s', 'time_rel_change_pct',
                'passed_baseline', 'passed_candidate', 'accuracy_regressed', 'accuracy_improved'
            ]
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
    
    # Exit with error if regressions detected
    regressions = sum(1 for r in results if r['accuracy_regressed'])
    if regressions > 0:
        print(f"\n⚠️  {regressions} accuracy regression(s) detected!", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
