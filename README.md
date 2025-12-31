# Network Analysis

A Python-based transportation network analysis framework for solving user equilibrium (UE) problems using Frank-Wolfe or Method of Successive Averages (MSA) algorithms. Includes comprehensive testing, validation, and performance benchmarking tools. 

# Acknowledgement

This project builds on skeleton code provided as part of homework assignments in **Dr. Stephen Boyles' CE 392C** (Fall 2023, UT Austin). 

**Class-provided skeleton:**
- `od.py` - Origin-Destination pair representation
- `node.py` - Network node class
- `link.py` - Link class with BPR cost functions
- `path.py` - Path-based representation
- `utils.py` - File I/O and TNTP format utilities

**Course assignment:**
We were tasked with implementing `network.py` to solve user equilibrium problems using Frank-Wolfe and MSA algorithms.

**Additional work (beyond course requirements):**
- `validate.py` - Fast validation tool for development
- Comprehensive testing suite (`tests/run_protocol.py`, etc.)
- Performance benchmarking and comparison tools
- Documentation (README, VALIDATE.md, etc.)
- Code refinements, memory optimization, and cleanup
- Archive organization and versioning

## Overview

This project solves traffic assignment problems where travelers choose routes to minimize their individual travel time, leading to user equilibrium. The implementation supports:

- **User Equilibrium Solving**: Frank-Wolfe and MSA algorithms with configurable convergence criteria
- **Quick Validation**: Fast development workflow with `validate.py`
- **Comprehensive Testing**: Protocol-based accuracy and performance testing
- **Implementation Comparison**: Side-by-side benchmarking of algorithm variants
- **Standard Format**: TNTP (Transportation Network Test Problem) format support

## Quick Start

### Development Workflow

**Fast iteration during development:**
```bash
# Quick validation: unit tests + UE solve + flow export
python validate.py

# Skip unit tests for faster iteration
python validate.py --skip-tests

# Test on different network
python validate.py --net-file tests/Anaheim_net.txt --trips-file tests/Anaheim_trips.txt

# Multiple runs for performance timing
python validate.py --skip-tests --runs 5
```

See [VALIDATE.md](VALIDATE.md) for complete `validate.py` documentation.

### Basic Usage

```python
from network import Network

# Load network and demand
net = Network("tests/SiouxFalls_net.txt", "tests/SiouxFalls_trips.txt")

# Solve user equilibrium
convergence = net.userEquilibrium(
    stepSizeRule="FW",           # Frank-Wolfe or MSA
    maxIterations=1000000,
    targetGap=1e-4,
    gapFunction=net.relativeGap
)

# Check convergence
print(f"Converged in {len(convergence['relative_gaps'])} iterations")
print(f"Final gap: {net.relativeGap():.6e}")
print(f"Avg excess cost: {net.averageExcessCost():.6e}")

# Access results
for link_id, link in net.link.items():
    print(f"Link {link_id}: flow={link.flow:.2f}, cost={link.cost:.2f}")
```

### Policy Analysis

Analyze transportation policies by modifying network capacity, demand, or costs:

```python
from policies.modifiers import scale_capacity, scale_demand, remove_links, reset_flows

# Capacity expansion: double capacity on highway corridor
highway_links = ['(5,9)', '(9,10)', '(10,15)', '(15,22)']
scale_capacity(net, highway_links, capacity_factor=2.0)  # FFT auto-adjusts to 0.5x
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)

# Demand growth scenario: 20% increase across all OD pairs
scale_demand(net, factor=1.2)

# Network resilience: remove links (e.g., for disaster analysis)
remove_links(net, ['(5,9)', '(9,10)'])

# Compare metrics before/after
reset_flows(net)  # Clear flows before re-solving with policy
from policies.modifiers import get_metrics
metrics = get_metrics(net)
print(f"TSTT: {metrics['tstt']:.0f}, Gap: {metrics['relative_gap']:.6e}")
```

See [ANALYSIS_WORKFLOWS.md](ANALYSIS_WORKFLOWS.md) for link removal, OD modification, and system equilibrium analysis patterns.

## Core Files

### Network Implementation

- **[network.py](network.py)** - Main Network class (PRODUCTION VERSION)
  - User equilibrium solving (Frank-Wolfe, MSA)
  - Shortest path algorithms (Dijkstra, label-setting, acyclic)
  - All-or-nothing assignment
  - Gap functions (relative gap, average excess cost)
  - Flow shifting and convergence tracking

- **[link.py](link.py)** - Link class with BPR cost functions
- **[node.py](node.py)** - Node class for network topology
- **[od.py](od.py)** - Origin-Destination demand representation
- **[path.py](path.py)** - Path-based representation (if needed)
- **[utils.py](utils.py)** - File I/O and TNTP format parsing

### Testing & Validation

- **[validate.py](validate.py)** - Primary validation tool for development
  - Quick unit tests + UE solve + flow export
  - Statistical averaging over multiple runs
  - Memory-efficient (garbage collection between runs)
  - See [VALIDATE.md](VALIDATE.md) for details

- **[tests.py](tests.py)** - Unit test suite
  - Relative gap calculation tests
  - Average excess cost tests
  - Convex combination tests
  - Frank-Wolfe step size tests

- **[grader.py](grader.py)** - Test runner and grading logic

### Advanced Testing (tests/ directory)

- **[tests/run_protocol.py](tests/run_protocol.py)** - Comprehensive protocol-based testing
  - Multiple test modes: `auto`, `fwstep`, `shift`, `ue_solve`
  - Statistical averaging across runs
  - cProfile integration
  - JSON/CSV output with detailed metrics
  - Per-link flow comparison

- **[tests/run_protocol_per_run.py](tests/run_protocol_per_run.py)** - Per-run variant
  - Logs individual runs (no averaging)
  - Useful for analyzing run-to-run variance
  - Debugging non-deterministic behavior

- **[tests/compare_networks.py](tests/compare_networks.py)** - Implementation comparison
  - Side-by-side testing of two network.py versions
  - A/B performance benchmarking
  - Automated comparison reports

- **[tests/compare_results.py](tests/compare_results.py)** - Result file comparison
  - Post-hoc analysis of CSV results
  - Markdown or CSV output
  - No re-execution needed

## Test Datasets

Located in `tests/` directory (TNTP format):

- **SiouxFalls** - Small network (24 nodes, 76 links) - good for quick testing
- **Anaheim** - Medium network for realistic testing
- **Barcelona** - Large network for performance testing
- **Braess** - Paradox demonstration network
- **3-parallel** - Simple test case for debugging

## Project Structure

```
network-analysis/
├── network.py              # Main implementation (USE THIS)
├── validate.py             # Quick validation tool
├── VALIDATE.md             # validate.py documentation
├── README.md               # This file
├── ANALYSIS_WORKFLOWS.md   # Policy analysis and advanced workflows
├── link.py, node.py, od.py, path.py, utils.py
├── tests.py, grader.py     # Unit tests
│
├── policies/               # Policy modification functions
│   └── modifiers.py        # Scale capacity/demand, remove links, etc.
│
├── experiments/            # Policy analysis experiments
│   └── highway_expansion_siouxfalls.py  # Example: capacity expansion
│
├── tests/                  # Test data and advanced testing tools
│   ├── *_net.txt           # Network topology files (TNTP format)
│   ├── *_trips.txt         # OD demand files (TNTP format)
│   ├── run_protocol.py     # Comprehensive test protocol runner
│   ├── run_protocol_per_run.py  # Per-run variant
│   ├── compare_networks.py # Implementation comparison tool
│   ├── compare_results.py  # Result comparison tool
│   └── protocol/           # Test specification files
│       ├── siouxfalls_ue_fw.txt
│       ├── siouxfalls_ue_msa.txt
│       └── ...
│
├── archive/                # Historical versions (reference only)
│   ├── VERSION_HISTORY.md  # Evolution documentation
│   ├── TESTING_TOOLS_ANALYSIS.md
│   ├── network_baseline.py
│   ├── network_5.3final.py
│   └── network_base.py
│
├── bench/                  # Benchmarking scripts
│   └── ...
│
└── outputs/                # Generated files (gitignored)
    ├── *_ue_flows.txt
    ├── *.prof
    └── *.csv
```

## Workflows

### 1. During Development

```bash
# Quick check after code changes
python validate.py --skip-tests --runs 1

# Full validation before commit
python validate.py --runs 3
```

### 2. Comprehensive Testing

```bash
# Run accuracy + performance tests
python -m tests.run_protocol \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --mode ue_solve \
  --runs 5 \
  --output results.csv \
  --profile cprofile
```

### 3. Comparing Implementations

```bash
# Compare current vs archived baseline
python -m tests.compare_networks \
  --network-a archive/network_baseline.py \
  --network-b network.py \
  --tests tests/protocol/siouxfalls_10_aec.txt \
  --mode auto \
  --func averageExcessCost \
  --runs 5
```

### 4. Analyzing Variance

```bash
# Get per-run data to analyze consistency
python -m tests.run_protocol_per_run \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --mode ue_solve \
  --runs 10 \
  --output variance_analysis.csv
```

## Test Protocol Specifications

Test specs in `tests/protocol/` define test cases. Example formats:

**UE Solve Test:**
```
tests/SiouxFalls_net.txt
tests/SiouxFalls_trips.txt
FW
1000000
1e-4
relativeGap
```

**Metric Evaluation:**
```
tests/SiouxFalls_net.txt
tests/SiouxFalls_trips.txt
tests/aec/SiouxFalls_eqm_flows.txt
0.000123
tests/aec/SiouxFalls_eqm_flows.txt
```

See [tests/run_protocol.py](tests/run_protocol.py) docstring for complete specification format.

## Network Class API

### Primary Methods

```python
# Solve user equilibrium
convergence_data = net.userEquilibrium(
    stepSizeRule='FW',          # 'FW' or 'MSA'
    maxIterations=1000000,
    targetGap=1e-4,
    gapFunction=net.relativeGap,  # or net.averageExcessCost
    stepType='natural'           # for MSA: 'natural', 'squares'
)
# Returns: {'iteration_times': [...], 'relative_gaps': [...]}

# Gap metrics
gap = net.relativeGap()              # Relative gap measure
aec = net.averageExcessCost()        # Average excess cost

# Shortest paths
net.shortestPath(origin)             # Dijkstra's algorithm
net.acyclicShortestPath(origin)      # For DAGs only

# All-or-nothing assignment
net.allOrNothing(origin)             # Load shortest paths

# Flow shifting
net.shiftFlows(targetFlows, stepSize)  # Convex combination

# Frank-Wolfe step size
alpha = net.FrankWolfeStepSize(targetFlows)  # Bisection search
```

### File I/O

```python
# Load from TNTP files
net = Network(networkFile, demandFile)

# Or load after construction
net.readFromFiles(networkFile, demandFile)

# Access network components
for link_id, link in net.link.items():
    print(link.flow, link.cost, link.capacity)

for origin, destinations in net.ODpair.items():
    for dest, od in destinations.items():
        print(od.origin, od.destination, od.demand)
```

## Development Notes

### Convergence Tracking

`userEquilibrium()` returns convergence history:
```python
convergence = net.userEquilibrium(...)
print(f"Iterations: {len(convergence['relative_gaps'])}")
print(f"Final gap: {convergence['relative_gaps'][-1]:.6e}")

# Plot convergence
import matplotlib.pyplot as plt
plt.semilogy(convergence['relative_gaps'])
plt.xlabel('Iteration')
plt.ylabel('Relative Gap')
plt.show()
```

### Gap Functions

Two gap measures supported:

1. **Relative Gap** (recommended for convergence):
   - Normalized measure: gap / total system travel time
   - Better for comparing across different networks
   - Use as `gapFunction=net.relativeGap`

2. **Average Excess Cost**:
   - Average over-cost compared to shortest paths
   - Direct interpretation in time units
   - Use as `gapFunction=net.averageExcessCost`

### Memory Management

For large networks or multiple runs:
- `validate.py` includes garbage collection between runs
- Explicitly `del net` and call `gc.collect()` when done
- Use `--skip-tests` flag to reduce memory overhead

### Historical Versions

See `archive/VERSION_HISTORY.md` for evolution of the implementation. Use `archive/network_baseline.py` or other versions only for comparison/debugging.

## Performance Tips

1. **Use Frank-Wolfe for production**: Generally faster convergence than MSA
2. **Tune target gap**: `1e-4` is usually sufficient for practical purposes
3. **Profile bottlenecks**: Use `--profile cprofile` with protocol runners
4. **Batch testing**: Use `run_protocol.py` for multiple tests in one invocation

## Citation & Data Sources

Networks from [Transportation Networks for Research](https://github.com/bstabler/TransportationNetworks) repository.

TNTP format specification: https://github.com/bstabler/TransportationNetworks

## License

[Add appropriate license]
