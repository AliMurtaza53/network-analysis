# Q1: Methodological Formulation

## Network Representation

The transport network is modelled as a directed graph G = (N, A) where N is the
set of nodes and A the set of directed links. Each link a ∈ A has free-flow travel
time t_a⁰ (min), capacity u_a (veh/h), and flow f_a (veh/h). The Anaheim TNTP
benchmark provides |N| = 416 nodes, |A| = 914 links, and 38 origin–destination
(OD) zones with total demand q = 104,694 veh/h.

## Link Performance Function (BPR)

Travel time on link a is given by the Bureau of Public Roads (BPR) function:

    t_a(f_a) = t_a⁰ · [1 + α · (f_a / u_a)^β]

with α = 0.15, β = 4 (TNTP Anaheim standard). This is a strictly increasing,
convex function of flow, ensuring a unique User Equilibrium solution. See
`docs/LIMITATIONS.md` for a note on alternative BPR calibrations used in
practice.

## User Equilibrium (Wardrop's First Principle)

A flow pattern {f_a} satisfies User Equilibrium (UE) if, for every OD pair rs
and every used path p:

    c_p = t_rs*     (used paths carry minimum cost)
    c_p ≥ t_rs*     (unused paths are no cheaper)

where c_p = Σ_{a∈p} t_a(f_a) and t_rs* is the equilibrium minimum cost.

Equivalently, UE is the unique minimiser of the Beckmann objective:

    Z(f) = Σ_a ∫₀^{f_a} t_a(x) dx

subject to flow conservation constraints and f_a ≥ 0.

## Solution Algorithm (Frank–Wolfe)

The Frank–Wolfe (linearised decomposition) method solves UE iteratively:

1. **Initialisation**: load all demand by All-or-Nothing (AON) assignment on
   free-flow shortest paths.
2. **AON direction**: find shortest paths under current costs; compute auxiliary
   flows y_a.
3. **Line search**: find λ* = argmin Z(f + λ(y − f)) over λ ∈ [0, 1] via
   bisection.
4. **Update**: f_a ← f_a + λ*(y_a − f_a).
5. **Convergence test**: relative gap < ε (default ε = 10⁻⁴).

The relative gap is:

    RG = [Σ_a t_a(f_a)(f_a − y_a)] / [Σ_a t_a(f_a) · f_a]

Validation against published TNTP Anaheim flows: R² = 0.9998, RMSE = 32 veh/h
(1.6% of mean flow, n = 914 links).

## Disruption Modelling

Each disruption scenario modifies {t_a⁰, u_a} for a subset of links and re-solves
UE from the perturbed network:

| Family | Mechanism |
|--------|-----------|
| S1 – Random closure | Remove k links uniformly at random (k ~ Uniform{1,5}) |
| S2 – Targeted closure | Remove top-k links by baseline flow (k = 1, 3, 5) |
| S3 – Flood footprint | Pregnolato et al. (2017) depth–speed function applied to links within radius r of a flood centre; speed reduction increases FFT and reduces capacity proportionally |
| S4 – Corridor loss | Reduce capacity of all links in a designated corridor by factor c (c = 0.25, 0.50, 0.75) |
| S5 – Demand surge | Scale all OD demands by factor d (d = 1.2, 1.4); two variants combined with S2 or S4 |

**Pregnolato depth–speed function** (S3):

    v(w) = 0.0009·w² − 0.5529·w + 86.9448    [km/h, w in mm, R² = 0.95]

Speed ratio: ρ(w) = v(w) / v(0). Complete closure at w ≥ 300 mm. Applied as:
t_a⁰ ← t_a⁰ / ρ,  u_a ← u_a · ρ.

## Performance Metrics

**Total System Travel Time** (primary):

    TSTT = Σ_a f_a · t_a(f_a)    [veh·min]

TSTT ratio: TSTT_disrupted / TSTT_baseline.

**Accessibility** (Hansen 1959):

    A_i = Σ_j O_j · exp(−β · t_ij*)    with β = 0.1 (assumed)

Accessibility loss: (A_baseline − A_disrupted) / A_baseline.

**Network efficiency** (Latora & Marchiori 2001):

    E = (1/n(n−1)) · Σ_{i≠j} 1/t_ij*

**Unmet demand**: fraction of OD pairs for which no path exists in the disrupted
network.

**Resilience index** (Bruneau et al. 2003):

    R = (1/T) · ∫₀ᵀ Q(t) dt

where Q(t) ∈ [0,1] is normalised system performance and T = 90 days (recovery
horizon). Linear recovery shape assumed.

**Economic cost** (assumed parameters):

    Cost = delay_hours · VOT_pax + unmet_trips · penalty · VOT_pax
    + truck_share · PCE · delay_hours · VOT_truck

with VOT_pax = $20/h, VOT_truck = $60/h, truck_share = 0.08, PCE = 2.0,
penalty = 1.5. All economic parameters are assumed; cost figures are illustrative.
