# Validation Script

**Purpose**: Quick sanity checks for `network.py` changes before committing.

**What it does**:
1. **Unit tests** (optional): Runs all basic tests from `tests.py` + `grader.py` (relativegap, AEC, convex combo, FW step size)
2. **UE solve**: Runs user equilibrium solver on a network, reports metrics averaged over N runs
3. **Flow export**: Saves final equilibrium flows to CSV for inspection/comparison

## Quick Start

```bash
# Default: all checks with SiouxFalls network (FW, 3 runs)
python validate.py

# Skip tests, just UE solve
python validate.py --skip-tests

# Different network
python validate.py --net-file tests/Anaheim_net.txt --trips-file tests/Anaheim_trips.txt

# MSA instead of FW, 5 runs
python validate.py --step-rule MSA --runs 5

# Custom network.py
python validate.py --network network_candidate.py

# No flow export
python validate.py --no-flows
```

## Output

**Console**:
- Pass/fail for each unit test category (40 tests total)
- UE metrics: gap ± std, solve time ± std

**CSV file**:
- `final_flows_<timestamp>.csv` with columns: `link_id`, `flow`
- Use for flow-based comparisons or visualization

## Options

```
--skip-tests           Skip unit tests, only run UE solve
--network PATH         Override network.py (default: network.py)
--net-file PATH        Network file for UE solve (default: tests/SiouxFalls_net.txt)
--trips-file PATH      Trips file for UE solve (default: tests/SiouxFalls_trips.txt)
--step-rule {FW|MSA}   Step size rule (default: FW)
--runs N               Runs to average (default: 3)
--no-flows             Skip flow CSV export
```

## Examples

```bash
# Before making changes: baseline
python validate.py --runs 3

# After changes: quick check
python validate.py --skip-tests --runs 3

# Detailed test on large network
python validate.py --net-file tests/Barcelona_net.txt --trips-file tests/Barcelona_trips.txt --runs 5

# Compare two implementations
python validate.py --network network.py --skip-tests --runs 1
# Then swap network.py with candidate and run again
```

## Exit Code

- `0` = All checks passed
- `1` = At least one check failed
