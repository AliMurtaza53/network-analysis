# Q3: Sensitivity Analysis

## Overview

Three methods — one-at-a-time (OAT) parameter sweep, Morris elementary effects
screening, and numerical (solver-gap) analysis — were applied to identify which
parameters and modelling choices drive the results.

---

## Finding 1: Demand factor dominates all outputs (Figure F8)

The OAT tornado confirms that the demand scaling factor has by far the largest
swing on both TSTT ratio and accessibility loss. Increasing demand 1.6× raises
TSTT ratio more than doubling corridor severity (cap 0.5 → 0.25). This is a
structural property of the BPR cost function: once flows approach capacity on
multiple links simultaneously, travel times rise sharply and demand amplification
compounds across the whole network.

Disruption severity (the second-ranked parameter) has a large swing only in TSTT
ratio; its effect on unmet demand is negligible at the ranges tested. BPR parameters
(α, β) and economic parameters (VOT, truck share, PCE) are low-swing across all
outputs — the network performance metrics are insensitive to plausible BPR
calibration uncertainty, while economic cost is sensitive only to VOT by
construction (it is a linear multiplier).

---

## Finding 2: No strong parameter interactions (Figure F10)

Morris screening (5 trajectories, 8 parameters) places all parameters well below
the σ = μ* diagonal — the region where interactions dominate. Demand factor and
severity appear as clearly most important (high μ*), but their σ values remain
moderate, indicating that their effects are approximately additive across the
parameter space. This justifies the OAT approach as adequate for ranking here: a
full Sobol first/total index decomposition would distinguish additive from
interaction effects numerically, but the Morris screen suggests the interaction
budget is small.

---

## Finding 3: Solver gap has negligible effect above 10⁻³ (Figure F13)

Tightening the Frank–Wolfe convergence criterion from ε = 10⁻² to ε = 10⁻⁵
changes TSTT ratio by < 0.1% and mean trip time ratio by < 0.1%. This confirms
that the default tolerance of ε = 10⁻⁴ is well within the flat region of the
convergence curve: further tightening incurs computational cost without improving
metric precision.

The AON (1-iteration) model produces systematically higher TSTT ratios than UE
(≈ 5–8% higher for moderate disruptions) because AON concentrates flows on
shortest paths without congestion feedback, overstating link loading on primary
routes. Full UE is therefore necessary for realistic metric estimation; the
sensitivity is quantified here as a model-form robustness check rather than a
recommendation to use AON.
