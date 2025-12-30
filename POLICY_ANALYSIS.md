# Policy Analysis Branch

This branch is for implementing and testing network policy changes and analyzing their impacts.

## Purpose

Explore how modifications to network infrastructure and demand affect user equilibrium outcomes.

## Policy Types

### 1. Capacity Modifications
- Expand capacity on selected links (e.g., add lanes)
- Reduce capacity (bottleneck studies)
- Systematic capacity scaling (e.g., all links +10%)

### 2. Demand Modifications
- Increase/decrease OD demand systematically
- Shift demand between origin-destination pairs
- Create new origins/destinations
- Time-of-day variations

### 3. Infrastructure Changes
- Add new links
- Remove/close links
- Toll pricing on specific links

## Suggested Structure

```
policy-analysis/
├── policies/                           # Policy definition files
│   ├── capacity_expansion_10pct.py     # Modify link capacities
│   ├── demand_growth_scenario.py       # Demand projections
│   └── toll_pricing_scheme.py          # Pricing policies
│
├── experiments/                        # Experiment runners
│   ├── run_capacity_study.py           # Test capacity changes
│   ├── run_demand_scenario.py          # Test demand changes
│   └── run_comparative_analysis.py     # Compare baseline vs policy
│
├── results/                            # Results storage
│   ├── baseline_siouxfalls.csv         # Baseline equilibrium flows
│   ├── policy_siouxfalls_expanded.csv  # Policy scenario flows
│   └── comparison_report.md            # Analysis summary
│
└── POLICY_ANALYSIS.md                  # This branch documentation
```

## Workflow Example

```python
from network import Network
import copy

# Load baseline
net = Network("tests/SiouxFalls_net.txt", "tests/SiouxFalls_trips.txt")

# Solve baseline
net.userEquilibrium(stepSizeRule="FW", targetGap=1e-4, gapFunction=net.relativeGap)
baseline_tstt = sum(link.flow * link.cost for link in net.link.values())
baseline_flows = {link_id: link.flow for link_id, link in net.link.items()}

# Save baseline
print(f"Baseline TSTT: {baseline_tstt:.0f}")

# Apply policy: expand capacity on key links
for link_id, link in net.link.items():
    if link_id in [("1", "2"), ("10", "11")]:  # Expand specific links
        link.capacity *= 1.25  # 25% increase
        link.updateCost()

# Reset flows and re-solve
for link in net.link.values():
    link.flow = 0

net.userEquilibrium(stepSizeRule="FW", targetGap=1e-4, gapFunction=net.relativeGap)
policy_tstt = sum(link.flow * link.cost for link in net.link.values())
policy_flows = {link_id: link.flow for link_id, link in net.link.items()}

# Compare
print(f"Policy TSTT: {policy_tstt:.0f}")
print(f"Improvement: {(1 - policy_tstt/baseline_tstt)*100:.1f}%")

# Identify most impacted links
flow_changes = {}
for link_id in baseline_flows:
    change = policy_flows[link_id] - baseline_flows[link_id]
    if abs(change) > 0.1:
        flow_changes[link_id] = change

print("\nMost impacted links:")
for link_id, change in sorted(flow_changes.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
    print(f"  {link_id}: {change:+.2f} vehicles")
```

## Key Metrics to Track

- **TSTT** (Total System Travel Time): Sum of (flow × cost)
- **Relative Gap**: Convergence metric
- **Link utilization**: flow / capacity
- **Congestion**: Links with flow > capacity
- **Mode shift**: Changes in route choice
- **Equity**: Impacts on different OD pairs

## Tools to Use

```bash
# Quick validation of policy changes
python validate.py --skip-tests

# Compare baseline vs policy
python -m tests.compare_results baseline_siouxfalls.csv policy_siouxfalls.csv --format markdown

# Detailed per-link flow comparison
python -m tests.run_protocol \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --mode ue_solve \
  --runs 3 \
  --output policy_results.csv \
  --flow-diff-dir policy_flow_diffs
```

## Documentation Requirements

For each policy analysis, create a summary including:
1. **Policy Description**: What changed and why
2. **Baseline Results**: Initial equilibrium metrics
3. **Policy Results**: Equilibrium after changes
4. **Comparison**: Impact analysis with key metrics
5. **Visualization**: Plots of congestion, flow changes, etc.
6. **Conclusions**: Effectiveness of the policy

Example report template:
```markdown
# Policy Analysis: Capacity Expansion on Links 1-2, 10-11

## Policy Description
Expand capacity on critical links by 25% to reduce congestion.

## Results

| Metric | Baseline | Policy | Change |
|--------|----------|--------|--------|
| TSTT | 123,456 | 118,234 | -3.9% |
| Avg Gap | 0.0001 | 0.00009 | -7.5% |
| Max Utilization | 98% | 84% | -14% |

## Conclusion
Capacity expansion on links 1-2 and 10-11 reduces TSTT by 3.9%...
```

## Getting Started

1. Create policy modifier script in `policies/`
2. Create experiment runner in `experiments/`
3. Run baseline equilibrium and save results
4. Apply policy and re-solve
5. Compare and document findings
6. Commit results to this branch

## See Also

- [README.md](../README.md) - Main documentation
- [VALIDATE.md](../VALIDATE.md) - Validation tool docs
- [bench/visualize_network_policy.py](../bench/visualize_network_policy.py) - Policy visualization tools
