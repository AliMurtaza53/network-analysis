# Testing Protocol for Network Analysis

This directory contains tools for testing performance and accuracy of network analysis implementations to support merge decisions.

## Files

- **run_protocol.py** - Main test runner that measures performance and accuracy
- **compare_results.py** - Compares baseline vs candidate test results
- **protocol/** - Test specification files (simplified format without grading)

## Quick Start

### 1. Run performance tests (auto mode: numeric + flows)

```bash
python -m tests.run_protocol \
  --tests tests/protocol/siouxfalls_10_aec.txt tests/protocol/siouxfalls_eqm_aec.txt \
  --func averageExcessCost \
  --runs 5 \
  --output results.csv \
  --json results.json
```

### 2. Run Frank-Wolfe step size (fwstep mode)

```bash
python -m tests.run_protocol \
  --mode fwstep \
  --tests tests/protocol/fw_siouxfalls.txt \
  --runs 3 \
  --output fw_results.csv
```

### 3. Run convex-combo flow shift (shift mode)

```bash
python -m tests.run_protocol \
  --mode shift \
  --tests tests/protocol/shift_siouxfalls_10.txt \
  --runs 3 \
  --output shift_results.csv
```

### 4. Compare implementations

Run tests on baseline:
```bash
git checkout main
python -m tests.run_protocol --tests tests/protocol/siouxfalls_10_aec.txt --func averageExcessCost --runs 5 --output baseline.csv
```

Run tests on feature branch:
```bash
git checkout feature/your-branch
python -m tests.run_protocol --tests tests/protocol/siouxfalls_10_aec.txt --func averageExcessCost --runs 5 --output candidate.csv
```

Compare results:
```bash
python -m tests.compare_results baseline.csv candidate.csv --format markdown
```

### 5. One-shot baseline vs candidate (side-by-side)

Use two network implementations in one command and compare outputs:
```bash
python -m tests.compare_networks \
  --mode auto \
  --func averageExcessCost \
  --tests tests/protocol/siouxfalls_10_aec.txt tests/protocol/siouxfalls_eqm_aec.txt \
  --runs 5 \
  --network-a path/to/network_baseline.py \
  --network-b path/to/network_candidate.py \
  --out-a baseline.csv \
  --out-b candidate.csv \
  --comparison comparison.csv \
  --format markdown
```

### 3. Profile for hotspots

```bash
python -m tests.run_protocol \
  --tests tests/protocol/siouxfalls_10_aec.txt \
  --func averageExcessCost \
  --runs 3 \
  --profile cprofile \
  --profile-dir profiler_output \
  --output results.csv
```

Check `profiler_output/*.prof.txt` for function-level timing details.

## Test Spec File Format

Test spec files use a simple format (comments allowed, non-comment lines):
```
Line 1: network file path
Line 2: trips file path
Line 3: flows file path (used to set link flows before measuring)
Line 4: expected numeric answer (float) [optional]
Line 5: answer flows file path [optional]
```

Rules:
- Numeric-only: provide line 4 only.
- Flows-only: skip numeric, provide line 4 as flows answer path.
- Both: provide numeric on line 4 and flows answer on line 5. The test passes only if **both** checks pass.

Combined numeric + flow example:
```
tests/SiouxFalls_net.txt
tests/SiouxFalls_trips.txt
tests/convexcombo/SiouxFalls_10_flows.txt
0.7192345440359187
tests/convexcombo/SiouxFalls_10_flows_answer.txt
```

Frank-Wolfe step size example (fwstep mode):
```
tests/SiouxFalls_net.txt
tests/SiouxFalls_trips.txt
tests/fwstepsize/SiouxFalls_current.txt
tests/fwstepsize/SiouxFalls_target.txt
0.21156509296270087
```

Convex-combo shift example (shift mode):
```
tests/SiouxFalls_net.txt
tests/SiouxFalls_trips.txt
tests/convexcombo/SiouxFalls_10_flows.txt
tests/convexcombo/SiouxFalls_eqm_flows.txt
0.1
tests/convexcombo/SiouxFalls_10_flows_answer.txt
```

## GitHub Actions Integration

The workflow `.github/workflows/perf-test.yml` automatically:
- Runs on PRs to main when core network files change
- Tests both baseline (main) and candidate (PR branch)
- Posts comparison table as PR comment
- Uploads detailed CSV/JSON artifacts

## Options

### run_protocol.py

- `--tests` - Test spec files to run (required)
- `--func` - Network method to call (e.g., averageExcessCost, relativeGap)
- `--runs` - Number of timing repetitions (default: 3)
- `--profile` - Collect cProfile data (choices: none, cprofile)
- `--profile-dir` - Directory for profile outputs (default: profiler_output)
- `--output` - CSV summary output (default: test_protocol_results.csv)
- `--json` - Optional JSON details output

### compare_results.py

- `baseline.csv` - Baseline results file (required)
- `candidate.csv` - Candidate results file (required)
- `--output` - Output comparison CSV (optional)
- `--format` - Output format: csv or markdown (default: csv)

## Best Practices

1. **Timing**: Use 5-30 runs for stable measurements; close heavy processes
2. **Profiling**: Use cProfile to find hotspots before optimizing
3. **Comparison**: Focus on relative changes >5% and accuracy regressions
4. **Documentation**: Record environment details (Python version, CPU, commit) in outputs
