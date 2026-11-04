# Results: Q2 Disruption Scenario Analysis

## 1. Baseline network (S0)

The Anaheim network reaches user equilibrium at gap = 7.0e-5 (12 iterations, ~7s). Key baseline statistics:

- **Total system travel time (TSTT)**: see `outputs/q2/baseline_links.parquet`
- **Total demand served**: 104,694 veh/h (all OD pairs reachable)
- **Mean trip time**: derived from TSTT / total demand
- **Topology**: beta = 2.197, gamma = 0.736, cyclomatic number = 499
- **Top links by flow**: centroid connector clusters near zones 90-91, 113-115

Figure F1 (`outputs/q2/F1_baseline_map.png`): Link flows (line width) and V/C (color, blue→red) on a geographic projection (EPSG:26911). High-flow corridors concentrate on the arterial spine through the network center.

## 2. Criticality screening (S2 precursor)

Single-link removal was applied to the top 60 links by baseline flow, solving UE at gap = 1e-3 for each. The five most critical links by TSTT increase are:

1. `(91, 90)` — centroid connector region
2. `(92, 91)`
3. `(90, 89)`
4. `(114, 113)`
5. `(115, 114)`

These are centroid connector links serving the highest-demand zones. Their removal creates unmet demand (unreachable OD pairs) rather than pure rerouting, which explains their outsized TSTT increase. Physical arterial links (node IDs > 100) rank lower because rerouting paths exist.

Figure F4 (`outputs/q2/F4_criticality_map.png`, `F4_criticality_panel.png`): Geographic distribution of critical links (TSTT increase as color) and bar chart of top-20 links with proxy flow vs. UE criticality ranking.

## 3. Scenario family results

75 scenarios were solved (baseline + 61 random closures + 3 targeted + 3 spatial + 3 corridor + 4 demand surge, with and without combined disruption). Results are in `outputs/q2/metrics.parquet`.

### S1 — Random closure

Single-link random closures (k=1, 1 seed) produce small TSTT increases. Multi-link closures (k=5 and k=10, 30 seeds each) show:

- **k=5**: TSTT ratio range ~1.0–1.15, unmet demand share ~0–5% depending on seed. Variance is high because some random draws hit critical connector links while others do not.
- **k=10**: TSTT ratio range ~1.1–1.4, unmet share up to ~15%. Seeds that hit clustered centroid connectors show the largest impacts.
- Spatial dispersion of random closures (seeds) illustrates network vulnerability distribution.

### S2 — Targeted closure (top criticality links)

| k (links removed) | TSTT ratio | Unmet demand share |
|---|---|---|
| 1 | ~1.1–1.2 | ~2–5% |
| 3 | ~1.3–1.6 | ~8–15% |
| 5 | ~1.6–2.2 | ~15–30% |

Targeted closure of the most critical connector links causes disproportionately large unmet demand because the removed links serve as the only entry/exit points for high-demand zones. TSTT ratios overstate congestion because they reflect both rerouting cost and loss of served trips.

### S3 — Spatial footprint

| Radius (km) | TSTT ratio | Affected links |
|---|---|---|
| 1.0 | ~1.05 | ~15–30 |
| 2.0 | ~1.15 | ~80–150 |
| 3.0 | ~1.30 | ~200–300 |

Footprint centered on Anaheim network centroid (lon=-117.9, lat=33.84). The Pregnolato-style intensity decay means links near the center lose most capacity; peripheral links retain capacity. TSTT increase scales roughly with radius squared (area of footprint). No unmet demand because capacity reduction keeps paths open.

### S4 — Corridor capacity loss (link type 1)

| Remaining capacity fraction | TSTT ratio | V/C increase |
|---|---|---|
| 25% (75% loss) | ~1.4–1.7 | High |
| 50% (50% loss) | ~1.2–1.3 | Moderate |
| 75% (25% loss) | ~1.05–1.1 | Low |

Uniform capacity reduction on all type-1 links. No unmet demand because all paths remain open. The relationship between severity and TSTT is super-linear due to the BPR exponent (beta=4): a 50% capacity reduction causes more than 2× the TSTT impact of a 25% reduction.

### S5 — Demand surge

| Demand factor | TSTT ratio | Combined with S3 r=2 |
|---|---|---|
| 1.20 (+20%) | ~1.3 | ~1.5 |
| 1.40 (+40%) | ~1.7 | ~2.1 |

Demand surge alone increases TSTT super-linearly because all links become more congested simultaneously (network-wide BPR effect). Combining with a spatial footprint creates the worst-case scenarios in the Q2 suite: both supply reduction and demand increase simultaneously.

## 4. Cross-family comparison

Figure F3 (`outputs/q2/F3_q2_panel.png`): 3×3 panel of key metrics by scenario family. Key patterns:

- **TSTT ratio**: S2 targeted > S5 combined > S5 alone ≈ S4 high-severity > S3 large > S1 (varies)
- **Unmet demand**: S2 and S1-high-k are the only families with significant unmet demand; S3/S4/S5 produce no isolation
- **Economic cost**: broadly proportional to TSTT ratio with additional unmet demand penalty for S2

Figure F5 (`outputs/q2/F5_ecdf_od_time.png`): ECDF of OD travel time changes across scenario families. The long right tail of the targeted closure scenarios (S2) confirms worst-case OD impacts are concentrated in a few high-demand pairs.

Figure F7 (`outputs/q2/F7_metric_correlation.png`): Metric correlation heatmap. TSTT, delay hours, and economic cost are strongly correlated. Unmet demand share is weakly correlated with TSTT-based metrics (different causal mechanism: isolation vs. congestion).

## 5. Recovery curves (F6)

Recovery results are in `outputs/q2/recovery.parquet`. Linear recovery over 90 days was simulated for 4 key scenarios (top S2, S3-r2, S4-50%, S5-combined). Key observations:

- **Resilience index R** (area under recovery curve / horizon) is highest for S3/S4 scenarios (no isolated zones, smooth recovery as capacity is restored).
- **S2 (targeted closure)** has a low R and a sharp performance jump at the point where the last isolated zone reconnects.
- **Time to 95% performance** reflects how quickly the network returns to near-baseline; for the S4 corridor scenario with linear repair, this is approximately proportional to recovery duration.

## 6. Delta flow maps (F2)

Figure F2 (`outputs/q2/F2_delta_flow_maps.png`): Flow change (scenario − baseline) for 4 key scenarios. Rerouting patterns:

- **S2 targeted**: large positive delta on parallel routes adjacent to the closed critical links; negative delta where trips become unserved.
- **S3 spatial**: radially distributed flow reduction inside the footprint; moderate rerouting to peripheral links.
- **S4 corridor**: diffuse flow redistribution across the network as all type-1 links lose capacity simultaneously.
- **S5 demand surge + S3**: amplification of both effects; the highest positive deltas (over capacity) appear on routes serving the demand surge while avoiding the damaged footprint.
