# Testing Tools Decision Matrix

## Summary

**KEEP ALL** - Each tool serves a distinct, non-redundant purpose:

### Primary Tools (Keep)

1. **validate.py** (Root)
   - **Purpose**: Quick sanity checks for development
   - **Use Case**: Fast iteration during development, pre-commit validation
   - **Features**: Unit tests + UE solve + flow export
   - **Target User**: Developer making changes to network.py
   - **Keep**: ✅ YES - Primary validation tool

2. **tests/run_protocol.py**
   - **Purpose**: Comprehensive protocol-based testing with averaging
   - **Use Case**: Performance benchmarking, accuracy validation with statistical averaging
   - **Features**: Multiple test modes (auto, fwstep, shift, ue_solve), cProfile, averaged results
   - **Target User**: Performance testing, CI/CD, detailed validation
   - **Keep**: ✅ YES - Production testing framework

3. **tests/run_protocol_per_run.py**
   - **Purpose**: Per-run logging variant of run_protocol
   - **Use Case**: Analyzing run-to-run variance, debugging non-deterministic behavior
   - **Features**: Same as run_protocol but logs each run individually (not averaged)
   - **Target User**: Performance analysis, variance debugging
   - **Keep**: ✅ YES - Specialized analysis tool (distinct from run_protocol)

4. **tests/compare_networks.py**
   - **Purpose**: Side-by-side comparison of two network.py implementations
   - **Use Case**: A/B testing different implementations, regression detection
   - **Features**: Runs both implementations, generates comparison report
   - **Target User**: Evaluating implementation changes, merge decisions
   - **Keep**: ✅ YES - Essential for comparing implementations

5. **tests/compare_results.py**
   - **Purpose**: Post-hoc comparison of two CSV result files
   - **Use Case**: Comparing results from different runs/branches without re-running tests
   - **Features**: Reads existing CSVs, generates markdown/CSV comparison
   - **Target User**: Analysis of historical results, documentation
   - **Keep**: ✅ YES - Utility for result analysis

### Removed Tools

6. **tests/demo_protocol.py**
   - **Purpose**: Demo/tutorial showing how to use testing tools
   - **Use Case**: Learning workflow
   - **Decision**: ❌ REMOVE - README.md examples provide better documentation
   - **Reason**: README has comprehensive examples; demo adds no functionality

## Workflow Recommendations

### During Development
```bash
# Quick validation after changes
python validate.py

# Quick check with specific network
python validate.py --network archive/network_baseline.py
```

### Before Commit/PR
```bash
# Comprehensive accuracy + performance tests
python -m tests.run_protocol \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --mode ue_solve --runs 5 --output pre_commit.csv
```

### Comparing Implementations
```bash
# Option 1: Direct comparison (re-runs both)
python -m tests.compare_networks \
  --network-a archive/network_baseline.py \
  --network-b network.py \
  --tests tests/protocol/siouxfalls_10_aec.txt \
  --runs 5

# Option 2: Compare existing results
python -m tests.compare_results baseline.csv candidate.csv --format markdown
```

### Analyzing Variance
```bash
# Use per-run variant to see individual run data
python -m tests.run_protocol_per_run \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --runs 10 --output per_run_analysis.csv
```

## Tool Relationships

```
validate.py (fast, dev-focused)
    ↓
run_protocol.py (comprehensive, averaged)
    ↓
run_protocol_per_run.py (detailed, per-run)

compare_networks.py (runs 2× run_protocol)
    ↓
compare_results.py (post-analysis)
```

## Conclusion

All tools except `demo_protocol.py` serve distinct purposes and should be kept. The README.md provides sufficient documentation, making the demo script redundant.
