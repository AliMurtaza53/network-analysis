# Limitations

## Model limitations

**Static user equilibrium.** The model assigns all demand simultaneously to equilibrium routes. It cannot represent the buildup or clearance of congestion over time, nor the dynamic rerouting that occurs as a disruption unfolds. Dynamic traffic assignment would be required for time-of-day analysis.

**Fixed demand.** OD demand is a fixed matrix. The model does not capture elastic demand: travelers do not cancel trips, shift mode, change destination, or depart at a different time in response to congestion or service loss. This means disruption impacts are likely underestimated (some travelers in reality would not make the trip), while also underestimating access loss (the model assumes all demand is served if a path exists, however congested).

**No queue spillback.** The BPR cost function is smooth and allows arbitrarily high V/C ratios without hard capacity enforcement. Real-world networks develop queues that propagate upstream and block intersections. BPR overestimates travel times at V/C > ~1.5 relative to queuing models, while underestimating spatial extent of congestion.

**Single vehicle class.** All demand is treated as passenger cars. Freight is a synthetic overlay (a fixed share of total flow multiplied by PCE). A proper multiclass assignment with separate freight OD matrices would be needed for freight-specific resilience conclusions.

**Separable link costs.** The BPR function depends only on the flow on that link. Interactions between turning movements at intersections, or between arterials and the motorway ramp it feeds, are not modelled.

## Scenario limitations

**Spatial footprint hazard model (S3).** S3 implements the Pregnolato et al. (2017, TRD) depth-disruption function v(w) = 0.0009w² − 0.5529w + 86.9448 (km/h, w in mm), which reduces free-flow speed as a quadratic function of flood depth. Flood depth decays linearly from a maximum at the flood centre (severity × 300 mm) to zero at radius_km. No real flood inundation map is used; centre, radius and severity are parameterised assumptions, not physically derived from a hydrological model.

**BPR parameters.** The TNTP Anaheim benchmark network specifies α = 0.15, β = 4 uniformly on all links (original BPR 1964 values). California regional travel demand models (e.g. SCAG) use higher exponents (α = 0.80–1.00, β = 5–8) differentiated by facility type and area type. These produce steeper cost curves at high V/C ratios and would yield significantly larger TSTT impacts under disruption. We retain TNTP parameters for benchmark reproducibility (validated R² = 0.9998 against published flows); results are not directly comparable to SCAG-calibrated models.

**Instant disruption.** All scenario families apply disruption instantaneously to the full network state. Staged or progressive failure (e.g., a flood that incrementally inundates roads) is not modelled.

**No interdependencies.** Power grid, communication, or fuel supply dependencies are not modelled. The model assumes traffic signals are operational (or that the network topology is otherwise unaffected by infrastructure co-failures).

**Corridor definition by link_type.** S4 corridor scenarios use the TNTP link_type attribute (1 = major arterial in Anaheim data). This is a coarse classification not aligned to any specific named corridor.

**Demand surge is a uniform multiplier.** S5 demand surge scales all OD pairs equally. In reality, emergency demand surges are directional (evacuation outbound from an affected zone). A directional pattern would require zone-specific demand scaling.

## Recovery curve limitations

**Parameterised, not physical.** Recovery curves (linear, exponential, step) are mathematical shapes, not outputs of a repair scheduling model or resource allocation optimisation. The recovery duration parameter is an assumption, not a prediction.

**No resource constraints.** The model does not limit the rate of repair by crew availability, material supply, or access to damaged infrastructure.

**Snap-shot solving.** Each recovery day is a fresh static UE solve with an interpolated capacity fraction. This ignores within-day dynamics and the memory effects of queues from previous days.

## Sensitivity analysis limitations

**OAT is not global.** One-at-a-time sensitivity does not capture parameter interactions. The Morris screening provides a first-order estimate of interaction but is not a full variance-based Sobol analysis.

**BPR parameters are uniform.** The sensitivity analysis varies alpha and beta globally. In practice, different link types would have different BPR parameters, and their joint distribution is unknown for the Anaheim network.

**Value of time is a placeholder.** VOT parameters (18 $/h passenger, 60 $/h truck) and PCE (2.0) are taken from generic US DOT guidance. No local calibration was performed.

## Data limitations

**Network is a planning-level schematic.** The Anaheim TNTP network is a simplified representation used for algorithm benchmarking. It has 914 links for a network that in reality has tens of thousands of lane-segments. Centroid connectors are artificial and their capacities do not represent real access restrictions.

**Coordinates are schematic.** The geojson for the Anaheim network is derived from the TNTP repository, which provides approximate coordinates for visualisation. Node positions may not align with actual Anaheim street intersections.

**No validation against observed data.** The base model has not been calibrated or validated against observed link counts, journey time surveys, or loop detector data. Absolute metric values (TSTT, travel times) carry unknown bias. Relative comparisons between scenarios are more reliable than absolute values.

**Freight share and PCE are assumed.** The 8% truck share and PCE of 2.0 are placeholder values. Actual Anaheim freight patterns are unknown and not in the TNTP dataset.

## Computational limitations

**Convergence gap.** Scenario sweeps use a relaxed gap criterion of 1e-3 (versus 1e-4 for the baseline). This introduces a small numerical uncertainty in TSTT comparisons between scenarios, estimated at <0.1% based on the baseline sensitivity check (gap=7e-5 at 1e-4 target).

**Parallelism not exploited.** The scenario sweep is sequential (joblib threads with n_jobs=1 for reproducibility). Parallel execution would reduce wall time substantially for the 75-scenario Q2 sweep.

**Deep copy cost.** Each scenario deep-copies the full network object. For very large networks (>10,000 links) this would become a bottleneck. For the 914-link Anaheim network it is acceptable.
