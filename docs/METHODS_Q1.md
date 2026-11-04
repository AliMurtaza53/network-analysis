# Methods: Q1 Network Description and Model Formulation

## 1. Network topology

The primary network is Anaheim, California (38 zones, 416 nodes, 914 directed links), from the TNTP benchmark dataset (bstabler/TransportationNetworks). It is a planar directed graph. Nodes 1 to 38 are zone centroids (trip origins and destinations). Nodes 39 to 416 are physical intersections. The first-thru-node is 39: centroid nodes cannot serve as intermediate nodes in shortest paths, which prevents unrealistic routing shortcuts through centroid connectors.

Topology indices: beta index (links/nodes) = 2.197, gamma index = 0.736, cyclomatic number = 499. The cyclomatic number indicates 499 independent path cycles, reflecting a moderately redundant network with meaningful rerouting options.

## 2. OD demand

Demand is specified as a static origin-destination matrix of 1,406 non-zero pairs drawn from the TNTP Anaheim trips file. Total demand is 104,694 vehicles per hour. Demand is in units of vehicles per hour, consistent with the capacity data.

## 3. Link representation

Each link is defined by:
- **Tail** and **head** node identifiers
- **Capacity** (veh/h): the BPR softcap parameter
- **Length** (ft)
- **Free-flow time** (min): travel time at zero demand
- **BPR alpha** (B): congestion sensitivity, 0.15 for all Anaheim links
- **BPR beta** (Power): exponent, 4.0 for all Anaheim links

## 4. BPR cost function

Link travel time is computed by the Bureau of Public Roads (BPR) function:

    t_a(x_a) = t_a^0 * (1 + alpha_a * (x_a / c_a)^beta_a)

where x_a is flow, c_a is capacity, t_a^0 is free-flow time, and alpha_a and beta_a are BPR parameters. For Anaheim, alpha = 0.15 and beta = 4 uniformly. The cost function is strictly convex and separable across links.

## 5. User equilibrium model

The static user equilibrium (UE) is defined by Wardrop's first principle: at equilibrium, no traveler can reduce their travel time by unilaterally changing routes. This is equivalent to solving the Beckmann transformation:

    min  sum_a integral_0^{x_a} t_a(w) dw
    s.t. sum_p f_{prs} = d_{rs}  for all r, s
         f_{prs} >= 0
         x_a = sum_p sum_rs delta_{a,p}^{rs} * f_{prs}

where d_{rs} is demand between origin r and destination s, f_{prs} is flow on path p between r and s, and delta is the path-link incidence.

## 6. Solution algorithm

The Frank-Wolfe convex combinations method is used. At each iteration, the auxiliary all-or-nothing assignment is solved via Dijkstra shortest paths (heap implementation), and the step size is set by bisection on the derivative of the Beckmann function (the exact Frank-Wolfe step). Convergence is declared at relative gap < 1e-4 for the baseline; scenario sweeps use 1e-3 (validated against 1e-4 on a subset). Anaheim converges to gap < 1e-4 in 12 iterations and 6-8 seconds.

## 7. Performance metrics

All metrics are defined in resilience/metrics.py and computed as pure functions over the link-flow and OD-cost results of each scenario.

| Metric | Symbol | Definition |
|--------|--------|-----------|
| Total system travel time | TSTT | sum_a x_a * t_a(x_a) |
| Mean trip time | MTT | TSTT / served_demand |
| Delay | D | sum_a x_a * max(t_a - t_a^0, 0) |
| OD exposure (worst case) | delta_max | max_rs (t_rs^sc - t_rs^0) |
| OD exposure (p95) | delta_p95 | 95th percentile of OD time change |
| Congested links | N_vc | count of links with V/C > 1 |
| Unmet demand share | u | unmet trips / total demand |
| Hansen accessibility | A_i | sum_j O_j * exp(-beta * t_ij) |
| Latora efficiency | E | mean(1 / t_rs) over zone pairs |
| Truck delay | D_T | D * truck_share |
| Economic cost | C | (D/60) * VOT_pax + u * penalty |
| Resilience index | R | integral_0^H Q(t) dt / H |

Performance function Q(t) = served_share(t) * (MTT_baseline / MTT_scenario(t)), bounded in [0, 1].

## 8. Key assumptions

1. **Static assignment**: demand is instantaneous, steady-state. No dynamics, no queuing.
2. **Fixed demand**: OD demand does not respond to congestion (no elasticity).
3. **Deterministic**: no stochasticity in behavior, travel time, or demand.
4. **Perfect information**: all travelers know all link costs.
5. **Separable link costs**: t_a depends only on x_a, not on flows on other links.
6. **Single class**: all vehicles share the same cost function (freight is a synthetic post-hoc weight).
7. **Capacity is a soft BPR parameter**: there is no hard capacity constraint. Very high V/C ratios are possible in theory.
8. **No queue spillback**: the BPR function does not capture backward propagation of congestion.
9. **Centroid connectors**: zones connect to the network via connectors that are not routable as intermediates. This is a standard TNTP modeling convention.

## 9. Limitations

See LIMITATIONS.md for a full list. Key limitations for resilience analysis:
- **No recovery physics**: the recovery curves are parameterised functions, not physical repair models.
- **No demand response**: evacuation demand surges are simulated as fixed multipliers, not behaviour-responsive.
- **Static model**: the model cannot capture the time-varying buildup of congestion during a disruption.
- **Synthetic freight**: truck metrics are derived by applying a fixed share and PCE to the passenger flow, not from a separate freight demand matrix.
- **Schematic hazard**: the spatial footprint scenarios use a synthetic Pregnolato-style intensity function. No real hazard raster is used.
