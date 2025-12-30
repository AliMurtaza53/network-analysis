"""Example experiment: Capacity expansion analysis on SiouxFalls network.

Compares baseline equilibrium vs expanded capacity scenario.
"""
import sys
import csv
from network import Network
from policies.modifiers import expand_capacity, scale_capacity_systematic, reset_flows, get_metrics


def run_baseline_experiment():
    """Run baseline SiouxFalls equilibrium."""
    print("\n" + "="*70)
    print("BASELINE: SiouxFalls Network - Current Capacity")
    print("="*70)
    
    net = Network("tests/SiouxFalls_net.txt", "tests/SiouxFalls_trips.txt")
    
    print("Solving baseline equilibrium...")
    convergence = net.userEquilibrium(
        stepSizeRule="FW",
        maxIterations=int(1e6),
        targetGap=1e-4,
        gapFunction=net.relativeGap
    )
    
    metrics = get_metrics(net)
    print(f"\nBaseline Results:")
    print(f"  Iterations: {len(convergence['relative_gaps'])}")
    print(f"  TSTT: {metrics['tstt']:.0f}")
    print(f"  Avg Cost: {metrics['avg_cost']:.4f}")
    print(f"  Max Utilization: {metrics['max_utilization']:.1%}")
    print(f"  Congested Links: {metrics['congested_links']}")
    print(f"  Relative Gap: {metrics['relative_gap']:.6e}")
    
    # Save baseline flows
    baseline_flows = {link_id: link.flow for link_id, link in net.link.items()}
    with open("results/baseline_siouxfalls.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['link_id', 'flow', 'cost', 'capacity', 'utilization'])
        for link_id, link in net.link.items():
            util = link.flow / link.capacity if link.capacity > 0 else 0
            writer.writerow([f"{link_id}", link.flow, link.cost, link.capacity, util])
    
    print(f"\n✓ Baseline flows saved to results/baseline_siouxfalls.csv")
    
    return net, metrics, baseline_flows


def run_capacity_expansion_experiment(baseline_net, baseline_metrics, baseline_flows):
    """Run capacity expansion scenario."""
    print("\n" + "="*70)
    print("POLICY: Capacity Expansion (+10% all links)")
    print("="*70)
    
    # Load fresh network
    net = Network("tests/SiouxFalls_net.txt", "tests/SiouxFalls_trips.txt")
    
    # Apply policy: uniform 10% capacity increase
    print("Applying policy: expanding all link capacities by 10%...")
    scale_capacity_systematic(net, factor=1.10)
    
    # Solve
    print("Solving policy equilibrium...")
    convergence = net.userEquilibrium(
        stepSizeRule="FW",
        maxIterations=int(1e6),
        targetGap=1e-4,
        gapFunction=net.relativeGap
    )
    
    metrics = get_metrics(net)
    print(f"\nPolicy Results:")
    print(f"  Iterations: {len(convergence['relative_gaps'])}")
    print(f"  TSTT: {metrics['tstt']:.0f}")
    print(f"  Avg Cost: {metrics['avg_cost']:.4f}")
    print(f"  Max Utilization: {metrics['max_utilization']:.1%}")
    print(f"  Congested Links: {metrics['congested_links']}")
    print(f"  Relative Gap: {metrics['relative_gap']:.6e}")
    
    # Compare with baseline
    print(f"\nComparison with Baseline:")
    tstt_change = metrics['tstt'] - baseline_metrics['tstt']
    tstt_pct = (tstt_change / baseline_metrics['tstt']) * 100
    util_change = metrics['max_utilization'] - baseline_metrics['max_utilization']
    congestion_change = metrics['congested_links'] - baseline_metrics['congested_links']
    
    print(f"  TSTT Change: {tstt_change:+.0f} ({tstt_pct:+.1f}%)")
    print(f"  Max Util Change: {util_change:+.1%}")
    print(f"  Congested Links Change: {congestion_change:+d}")
    
    # Save policy flows
    with open("results/policy_expansion_10pct.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['link_id', 'flow_baseline', 'flow_policy', 'flow_change', 
                        'capacity_baseline', 'capacity_policy', 'util_baseline', 'util_policy'])
        for link_id, link in net.link.items():
            baseline_flow = baseline_flows[link_id]
            baseline_cap = baseline_net.link[link_id].capacity
            baseline_util = baseline_flow / baseline_cap if baseline_cap > 0 else 0
            policy_util = link.flow / link.capacity if link.capacity > 0 else 0
            writer.writerow([
                f"{link_id}",
                baseline_flow,
                link.flow,
                link.flow - baseline_flow,
                baseline_cap,
                link.capacity,
                baseline_util,
                policy_util
            ])
    
    print(f"\n✓ Policy flows saved to results/policy_expansion_10pct.csv")
    
    return net, metrics


def write_summary_report(baseline_metrics, policy_metrics):
    """Write markdown summary report."""
    report = f"""# Policy Analysis Report: Capacity Expansion

## Policy Description
Uniform 10% increase in capacity on all links in SiouxFalls network.

## Objective
Test whether capacity expansion reduces congestion and improves network efficiency.

## Results Comparison

| Metric | Baseline | Policy | Change | % Change |
|--------|----------|--------|--------|----------|
| TSTT (veh-hrs) | {baseline_metrics['tstt']:.0f} | {policy_metrics['tstt']:.0f} | {policy_metrics['tstt']-baseline_metrics['tstt']:+.0f} | {((policy_metrics['tstt']-baseline_metrics['tstt'])/baseline_metrics['tstt'])*100:+.2f}% |
| Avg Cost | {baseline_metrics['avg_cost']:.4f} | {policy_metrics['avg_cost']:.4f} | {policy_metrics['avg_cost']-baseline_metrics['avg_cost']:+.4f} | N/A |
| Max Utilization | {baseline_metrics['max_utilization']:.1%} | {policy_metrics['max_utilization']:.1%} | {policy_metrics['max_utilization']-baseline_metrics['max_utilization']:+.1%} | N/A |
| Congested Links (>100%) | {baseline_metrics['congested_links']} | {policy_metrics['congested_links']} | {policy_metrics['congested_links']-baseline_metrics['congested_links']:+d} | N/A |
| Relative Gap | {baseline_metrics['relative_gap']:.6e} | {policy_metrics['relative_gap']:.6e} | N/A | N/A |

## Key Findings

1. **System Efficiency**: {
    f"Capacity expansion reduced TSTT by {abs((policy_metrics['tstt']-baseline_metrics['tstt'])/baseline_metrics['tstt'])*100:.1f}%"
    if policy_metrics['tstt'] < baseline_metrics['tstt']
    else f"Capacity expansion increased TSTT by {abs((policy_metrics['tstt']-baseline_metrics['tstt'])/baseline_metrics['tstt'])*100:.1f}%"
}

2. **Congestion**: {
    f"Reduced congested links from {baseline_metrics['congested_links']} to {policy_metrics['congested_links']}"
}

3. **Network Utilization**: Maximum link utilization decreased from {baseline_metrics['max_utilization']:.1%} to {policy_metrics['max_utilization']:.1%}

## Detailed Results

- Baseline flows: `results/baseline_siouxfalls.csv`
- Policy flows: `results/policy_expansion_10pct.csv`

## Conclusion

The 10% uniform capacity expansion shows {
    "promise for reducing system-wide travel time"
    if policy_metrics['tstt'] < baseline_metrics['tstt']
    else "limited benefit or potential negative effects"
} on the SiouxFalls network.

Further analysis should examine:
- Which specific links benefit most from expansion
- Optimal capacity allocation strategies
- Trade-offs between cost and performance
- Demand scenarios
"""
    
    with open("results/ANALYSIS_REPORT.md", "w") as f:
        f.write(report)
    
    print(f"\n✓ Analysis report saved to results/ANALYSIS_REPORT.md")


def main():
    """Run full capacity expansion analysis."""
    print("\n" + "="*70)
    print("SIOUXFALLS NETWORK POLICY ANALYSIS")
    print("Scenario: Uniform Capacity Expansion")
    print("="*70)
    
    # Baseline
    baseline_net, baseline_metrics, baseline_flows = run_baseline_experiment()
    
    # Policy
    policy_net, policy_metrics = run_capacity_expansion_experiment(baseline_net, baseline_metrics, baseline_flows)
    
    # Summary
    write_summary_report(baseline_metrics, policy_metrics)
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print("\nResults stored in results/")
    print("  - baseline_siouxfalls.csv")
    print("  - policy_expansion_10pct.csv")
    print("  - ANALYSIS_REPORT.md")


if __name__ == "__main__":
    main()
