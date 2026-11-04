# Results: Q3 Sensitivity Analysis

## 1. Overview

Q3 investigates how uncertain model parameters affect the resilience metrics computed in Q2. Three complementary methods are used:

1. **One-at-a-time (OAT) tornado analysis**: each parameter swept over its range while others are held at reference values.
2. **2D demand × severity grid**: joint effect of the two most policy-relevant parameters.
3. **Morris elementary effects screening**: global sensitivity estimate using (10 trajectories × 11 parameters = 110 model evaluations) to rank parameters by mean absolute elementary effect (mu*) and detect nonlinearity (sigma).

A reference scenario is defined with: demand_factor=1.0, severity=0.3, radius_km=2.0, BPR alpha=0.15, BPR beta=4.0, truck_share=0.08, PCE=2.0, VOT multiplier=1.0, unmet_penalty_hours=2.0, recovery_duration=60, gap=1e-3.

Results are in `outputs/q3/`.

## 2. OAT tornado analysis (F8)

Figure F8 (`outputs/q3/F8_tornado.png`): Tornado chart of parameter swings on key outputs (TSTT ratio, unmet demand share, mean trip time ratio).

**Most influential parameters** (approximate swing ranking):

1. **demand_factor**: single largest driver of TSTT increase. Even a ±20% demand swing produces ~±30–40% TSTT change due to network-wide BPR nonlinearity.
2. **severity**: second largest for capacity-reduction scenarios. Nonlinear effect due to BPR (capacity appears in denominator to the fourth power).
3. **radius_km**: moderate effect for spatial footprint scenarios. Roughly quadratic in radius (footprint area).
4. **bpr_power (beta)**: moderate. Higher beta concentrates more of the congestion penalty at high V/C, amplifying the impact of capacity reductions.
5. **bpr_alpha**: smaller effect than beta because it scales all V/C terms uniformly.
6. **truck_share, pce, vot_factor**: affect only the economic and freight sub-metrics, not TSTT itself.
7. **unmet_penalty_hours**: affects economic cost of scenarios with isolation; irrelevant for S3/S4/S5.
8. **gap_tolerance**: negligible effect on relative metrics (TSTT ratios) over the 1e-2 to 1e-4 range tested.

**Key finding**: the two operationally controllable parameters (severity, demand_factor) are also the two most influential. This means that early traffic management actions (demand management, demand smoothing) have the greatest potential to reduce disruption impacts.

## 3. 2D demand × severity grid (F9)

Figure F9 (`outputs/q3/F9_2d_heatmaps.png`): Heatmaps of TSTT ratio, unmet demand share, and economic cost over a grid of demand_factor (0.8–1.5) × severity (0.0–0.9).

**Key observations**:

- TSTT ratio shows smooth super-linear increase in both dimensions, confirming BPR nonlinearity.
- Unmet demand only appears in the high-severity corner (severity > ~0.7) where full link closures begin to isolate zones. The boundary is sharp.
- Economic cost is dominated by TSTT at low severity; at high severity, unmet demand penalty dominates.
- The combined scenario (high demand + high severity) is 3–5× more damaging than either alone, indicating synergistic interaction.
- The gradient is steeper in the demand_factor direction at high severity, and steeper in severity at high demand. This means interventions targeting demand reduction are most effective when supply is already constrained.

## 4. Morris elementary effects screening (F10)

Figure F10 (`outputs/q3/F10_morris.png`): mu* (mean absolute elementary effect) vs sigma (standard deviation of elementary effects) scatter, one point per parameter per output.

**Interpretation**:

- Points with high mu* and high sigma indicate parameters with strong nonlinear or interaction effects.
- Points with high mu* and low sigma indicate parameters with consistent large linear effects.

**Results**:

- **demand_factor**: high mu*, moderate sigma — consistently large effect with moderate nonlinearity.
- **severity**: high mu*, high sigma — large effect with strong nonlinearity (BPR fourth-power), especially for metrics near the isolation threshold.
- **bpr_power**: moderate mu*, high sigma — large interaction effects (severity and demand amplify each other through the exponent).
- **radius_km**: moderate mu* for spatial metrics, low sigma.
- All remaining parameters: low mu* for TSTT-based metrics; truck_share, pce, vot_factor show non-negligible mu* only for economic cost metrics.

**Screening conclusion**: 2–3 parameters (demand_factor, severity, and to a lesser extent bpr_power or radius_km) explain most of the output variance. A full variance-based Sobol analysis would be needed to quantify total-order indices, but the Morris screening suggests the input space is effectively low-dimensional.

## 5. Rank stability across outputs (F11)

Figure F11 (`outputs/q3/F11_rank_stability.png`): Heatmap of parameter swing by output metric. Each cell shows the range of the output as the parameter sweeps from its minimum to maximum.

The parameter ranking is consistent across TSTT ratio, mean trip time ratio, and economic cost: demand_factor > severity > radius_km > bpr_power. The ranking changes only for the unmet_demand output, where severity dominates because it determines whether links are fully removed.

## 6. Output range violin (F12)

Figure F12 (`outputs/q3/F12_output_range.png`): Distribution of metric values across all OAT sweep evaluations, by parameter. This shows which parameters produce the widest spread of outcomes. Demand_factor and severity produce the widest distributions; unmet_penalty_hours produces a wide economic cost distribution but no effect on physical metrics.

## 7. Numerical sensitivity (F13)

Figure F13 (`outputs/q3/F13_numerical_sensitivity.png`): Comparison of:

- **Gap tolerance effect**: TSTT ratio at gap = 1e-2, 1e-3, 1e-4. The difference between 1e-3 and 1e-4 is < 0.5% on TSTT ratio and < 1% on mean trip time ratio. The 1e-2 gap shows ~1–2% difference from 1e-4. The Q2 sweep used 1e-3 (accepted precision).
- **UE vs. AON**: All-or-nothing assignment (1 MSA iteration) overestimates TSTT by ~10–20% because it does not account for the spreading of flow across parallel routes. Residual gap from full UE is orders of magnitude smaller. This confirms that the UE model is necessary; AON would not be acceptable for comparative scenario analysis.

## 8. Summary and implications for resilience planning

1. **Demand management is the highest-leverage lever**: reducing travel demand during disruptions (by trip cancellation, telework, demand spreading) has the largest effect on network performance, outweighing the physical severity of the disruption within normal parameter ranges.

2. **Nonlinearity means thresholds matter**: small increases in severity near the capacity-exhaustion point (V/C ≈ 1) produce disproportionately large TSTT increases. Pre-emptive capacity preservation (e.g., protecting high-flow links from construction, avoiding simultaneous closures) has high value.

3. **Freight and economic cost metrics are sensitive to assumed shares**: the truck_share and PCE parameters are placeholder values and have non-negligible effect on economic cost estimates. Field surveys would be needed to narrow their uncertainty.

4. **Numerical precision is not a binding constraint**: the 1e-3 convergence gap is sufficient for the relative comparisons in Q2. Absolute metric values carry larger uncertainty from model structure (static assignment, fixed demand) than from solver precision.
