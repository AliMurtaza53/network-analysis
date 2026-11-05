# Q2: Scenario Results

## Overview

Seventy-five disruption scenarios across five families were evaluated on the TNTP
Anaheim network (914 links, 38 zones, 104,694 veh/h demand). Results are organised
below around four dimensions: family comparison, severity gradient, metric space,
and recovery.

---

## 1. Family Comparison (Figure F3)

Corridor capacity loss (S4) is categorically worse than all other disruption types.
At 25% residual capacity (cap = 0.25), TSTT rises 17.9× above baseline — a regime
change driven by severe congestion throughout the network. The other families stay
well below 2×, confirming that the choice of disruption type matters far more than
parameter values within any single family.

Random link closure (S1, n = 61 runs) produces a narrow distribution: mean TSTT
ratio 1.017 (IQR 0.98–1.05), indicating the network absorbs single- or few-link
failures with little aggregate cost. This is consistent with the dense structure of
the Anaheim graph (914 links, 416 nodes → average out-degree ≈ 2.2).

Flood footprint (S3) is the second least severe family after the Pregnolato
correction, with TSTT ratio 1.00–1.08 across the three tested radii (1–3 km) at
maximum severity. This reflects the relatively small fraction of Anaheim links
intersected by a 3 km flood radius, together with the Pregnolato function's
moderate speed reductions at typical depths below 200 mm.

Demand surge (S5) and targeted closure (S2) are intermediate. Demand × 1.4
combined with corridor loss produces TSTT 1.75×, the worst S5 outcome, suggesting
that compound disruptions (demand + capacity) interact superlinearly when the
corridor is already a bottleneck.

---

## 2. Severity Gradient

Within every family (S2–S5), impact increases monotonically with severity parameter.
The gradient is steepest in S4: TSTT ratio steps from 1.18 (cap = 0.75) to 2.09
(cap = 0.50) to 17.96 (cap = 0.25). The jump at cap = 0.25 is nonlinear — the
corridor's residual capacity falls below the equilibrium demand on that corridor,
driving flows onto congested diversions.

S2 shows a shallower gradient: removing 5 vs. 1 high-flow links raises TSTT from
1.22 to 1.32. This sub-linear response suggests the network has adequate redundancy
for moderate targeted attacks.

---

## 3. Metric Space

Accessibility loss tracks TSTT ratio closely (ρ ≈ 0.91 across all scenarios). The
S4 corridor scenario is again dominant, with accessibility loss reaching 0.72 at
cap = 0.25 — roughly three-quarters of origin zones lose access to half their
destinations.

Unmet demand is zero for all scenarios except extreme S4 (cap = 0.25), where a
small fraction of OD pairs lack any feasible path. This signals that the Anaheim
network's dense connectivity preserves path existence even under severe disruption,
except when the corridor removal disconnects peripheral zones.

Economic cost scales with TSTT ratio, amplified by the freight multiplier (PCE ×
truck share). The S4 extreme scenario carries roughly 18× baseline cost — a
sensitivity result driven entirely by the assumed demand; actual freight values
would require calibrated truck counts.

---

## 4. Link Criticality (Figure F4)

The top 15 links by single-link TSTT increase share a common pattern: all lie on
arterials serving high-flow centroid connectors in the central Anaheim zone cluster.
The top link raises TSTT by approximately 211,000–267,000 veh·min on removal.
Criticality is concentrated: the top 5 links account for a disproportionate share
of the total criticality across the screened 60 links, suggesting targeted
interventions (e.g. parallel route provision) on a small set of links would have
outsized resilience benefit.

---

## 5. Recovery (Figure F6)

Recovery curves are shown for three representative scenarios: S2 (top-1 link
closure), S3 (r = 2 km, severity = 1.0), and S4 (cap = 0.5). With a linear
recovery assumption over 90 days, the resilience index R (area under Q(t)) ranges
from 0.85 (S2) to lower values for more severe disruptions. The S4 scenario never
returns to baseline within the 90-day horizon at cap = 0.25, reflected by R < 0.5.

The recovery shape is an assumption — actual post-flood or post-closure restoration
typically follows a step function (repair events) rather than linear; this is noted
as a limitation and can be updated with empirical restoration data.
