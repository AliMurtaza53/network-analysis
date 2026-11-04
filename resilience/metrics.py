"""Performance metrics — pure functions over scenario result dicts."""
import numpy as np
import math
from typing import Dict, List, Optional, Any


# ------------------------------------------------------------------
# Travel cost metrics
# ------------------------------------------------------------------

def tstt(link_results: dict) -> float:
    """Total system travel time: sum of flow * cost over all links."""
    return sum(r['flow'] * r['cost'] for r in link_results.values())


def mean_trip_time(link_results: dict, served_demand: float) -> float:
    """TSTT / served demand."""
    if served_demand <= 0:
        return float('inf')
    return tstt(link_results) / served_demand


def delay_hours(link_results: dict) -> float:
    """Total delay: sum of flow * (cost - fft). In units of cost (minutes for Anaheim)."""
    return sum(r['flow'] * max(r['cost'] - r['fft'], 0) for r in link_results.values())


def worst_case_od_exposure(od_costs: dict, baseline_od_costs: dict) -> dict:
    """Change in OD shortest-path time vs baseline.

    Returns max, 95th percentile, and demand-weighted mean change.
    od_costs and baseline_od_costs keyed by od_id -> cost.
    """
    deltas = []
    for od_id, cost in od_costs.items():
        base = baseline_od_costs.get(od_id)
        if base is not None and base > 0:
            deltas.append(cost - base)

    if not deltas:
        return {'max': 0.0, 'p95': 0.0, 'mean': 0.0}

    arr = np.array(deltas)
    return {
        'max': float(np.max(arr)),
        'p95': float(np.percentile(arr, 95)),
        'mean': float(np.mean(arr)),
    }


def od_time_changes(od_costs: dict, baseline_od_costs: dict) -> List[float]:
    """List of delta OD times (for ECDF plotting)."""
    deltas = []
    for od_id, cost in od_costs.items():
        base = baseline_od_costs.get(od_id)
        if base is not None and base > 0:
            deltas.append(cost - base)
    return deltas


# ------------------------------------------------------------------
# Congestion metrics
# ------------------------------------------------------------------

def congested_link_count(link_results: dict, threshold: float = 1.0) -> int:
    return sum(1 for r in link_results.values() if r['vc'] > threshold)


def max_vc(link_results: dict) -> float:
    if not link_results:
        return 0.0
    return max(r['vc'] for r in link_results.values())


def vmt_weighted_vc(link_results: dict) -> float:
    """Flow-weighted mean V/C (VMT-weighted proxy)."""
    total_flow = sum(r['flow'] for r in link_results.values())
    if total_flow <= 0:
        return 0.0
    return sum(r['flow'] * r['vc'] for r in link_results.values()) / total_flow


# ------------------------------------------------------------------
# Unmet demand metrics
# ------------------------------------------------------------------

def unmet_share(unmet_demand: float, total_demand: float) -> float:
    if total_demand <= 0:
        return 0.0
    return unmet_demand / total_demand


def disconnected_od_count(unreachable_ods: list) -> int:
    return len(unreachable_ods)


def isolated_zone_count(unreachable_ods: list, num_zones: int) -> int:
    """Zones that appear in unreachable OD pairs as origin or destination."""
    nodes = set()
    for od_id in unreachable_ods:
        parts = od_id.split('->')
        if len(parts) == 2:
            nodes.add(parts[0])
            nodes.add(parts[1])
    return len(nodes)


# ------------------------------------------------------------------
# Accessibility (Hansen index)
# ------------------------------------------------------------------

def hansen_accessibility(od_costs: dict, attraction: Dict[str, float],
                          beta: float) -> Dict[str, float]:
    """Hansen index A_i = sum_j O_j * exp(-beta * t_ij) for each origin zone i.

    od_costs: {od_id -> travel time}, od_id = 'i->j'
    attraction: {zone_id_str -> O_j} (trips attracted)
    beta: decay parameter (1/min)
    Returns: {zone_id_str -> accessibility}
    """
    access: Dict[str, float] = {}
    # Group by origin
    from collections import defaultdict
    by_origin: Dict[str, List] = defaultdict(list)
    for od_id, cost in od_costs.items():
        parts = od_id.split('->')
        if len(parts) == 2:
            by_origin[parts[0]].append((parts[1], cost))

    for orig, pairs in by_origin.items():
        a = 0.0
        for dest, cost in pairs:
            oj = attraction.get(dest, 0.0)
            a += oj * math.exp(-beta * cost)
        access[orig] = a
    return access


def hansen_summary(access: Dict[str, float]) -> dict:
    """Demand-weighted mean, minimum, and Gini across zones."""
    vals = list(access.values())
    if not vals:
        return {'weighted_mean': 0.0, 'min': 0.0, 'gini': 0.0}
    arr = np.array(vals)
    gini = _gini(arr)
    return {
        'weighted_mean': float(np.mean(arr)),
        'min': float(np.min(arr)),
        'gini': gini,
    }


def _gini(arr: np.ndarray) -> float:
    if arr.sum() == 0:
        return 0.0
    arr = np.sort(arr)
    n = len(arr)
    idx = np.arange(1, n + 1)
    return float((2 * np.dot(idx, arr)) / (n * arr.sum()) - (n + 1) / n)


# ------------------------------------------------------------------
# Network efficiency (Latora)
# ------------------------------------------------------------------

def latora_efficiency(od_costs: dict, num_zones: int) -> float:
    """Mean of 1/t_ij over zone pairs with finite path."""
    vals = []
    for od_id, cost in od_costs.items():
        if cost > 0 and not math.isinf(cost):
            vals.append(1.0 / cost)
    if not vals:
        return 0.0
    return float(np.mean(vals))


# ------------------------------------------------------------------
# Freight proxy
# ------------------------------------------------------------------

def freight_metrics(link_results: dict, od_costs: dict, net_od_pairs: dict,
                    truck_share: float, pce: float,
                    vot_truck: float) -> dict:
    """Synthetic freight proxy metrics.

    truck_share: fraction of passenger demand that is truck (by count)
    pce: passenger car equivalents per truck
    vot_truck: USD per hour (time unit = minutes, so /60)
    """
    # Truck delay hours on links
    total_truck_delay_min = sum(
        r['flow'] * truck_share * max(r['cost'] - r['fft'], 0)
        for r in link_results.values()
    )
    truck_delay_hours = total_truck_delay_min / 60.0

    truck_cost_usd = truck_delay_hours * vot_truck

    # Truck throughput: served truck trips * shortest path cost (proxy for distance-time)
    truck_throughput = 0.0
    for od_id, cost in od_costs.items():
        if od_id in net_od_pairs:
            truck_demand = net_od_pairs[od_id].demand * truck_share
            truck_throughput += truck_demand * cost  # veh*min

    return {
        'truck_delay_hours': truck_delay_hours,
        'truck_cost_usd': truck_cost_usd,
        'truck_throughput': truck_throughput,
    }


# ------------------------------------------------------------------
# Economic cost
# ------------------------------------------------------------------

def total_economic_cost(link_results: dict, unmet_demand: float,
                        total_demand: float,
                        vot_passenger: float,
                        unmet_penalty_hours: float) -> float:
    """Monetized delay (USD) + unmet trip penalty."""
    delay_min = delay_hours(link_results)  # actually minutes for Anaheim
    delay_h = delay_min / 60.0
    delay_cost = delay_h * vot_passenger
    penalty_cost = unmet_demand * unmet_penalty_hours * vot_passenger
    return delay_cost + penalty_cost


# ------------------------------------------------------------------
# Topology (context only)
# ------------------------------------------------------------------

def topology_indices(num_nodes: int, num_links: int, num_zones: int) -> dict:
    """Beta, gamma, cyclomatic number for the METHODS_Q1 description."""
    beta = num_links / num_nodes if num_nodes > 0 else 0
    gamma = num_links / (3 * (num_nodes - 2)) if num_nodes > 2 else 0
    cyclomatic = num_links - num_nodes + 1
    return {'beta': beta, 'gamma': gamma, 'cyclomatic': cyclomatic}


# ------------------------------------------------------------------
# Aggregate all metrics into a flat dict
# ------------------------------------------------------------------

def compute_all(result: dict, baseline_result: dict, config: dict) -> dict:
    """Compute all metrics for a scenario result, normalised against baseline."""
    lr = result['link_results']
    b_lr = baseline_result['link_results']
    od_c = result['od_costs']
    b_od_c = baseline_result['od_costs']
    net = result['net']

    # Served demand
    total_demand = sum(od.demand for od in net.ODpair.values())
    served_demand = total_demand - result['unmet_demand']
    b_total = sum(od.demand for od in baseline_result['net'].ODpair.values())

    # Attraction = trips produced at each zone (use total demand as proxy)
    attraction = {}
    for od_id, od in net.ODpair.items():
        dest_str = od_id.split('->')[1] if '->' in od_id else str(od.destination)
        attraction[dest_str] = attraction.get(dest_str, 0.0) + od.demand

    beta_access = config.get('accessibility_beta', 0.1)
    access = hansen_accessibility(od_c, attraction, beta_access)
    b_access = hansen_accessibility(b_od_c, attraction, beta_access)

    b_tstt = tstt(b_lr)
    s_tstt = tstt(lr)

    b_mean_tt = mean_trip_time(b_lr, b_total)
    s_mean_tt = mean_trip_time(lr, served_demand)

    od_exp = worst_case_od_exposure(od_c, b_od_c)
    access_sum = hansen_summary(access)
    b_access_sum = hansen_summary(b_access)

    truck_share = config.get('truck_share', 0.08)
    pce = config.get('pce', 2.0)
    vot_truck = config.get('vot_truck', 60.0)
    vot_pax = config.get('vot_passenger', 18.0)
    unmet_pen = config.get('unmet_penalty_hours', 2.0)

    freight = freight_metrics(lr, od_c, net.ODpair, truck_share, pce, vot_truck)
    b_freight = freight_metrics(b_lr, b_od_c, baseline_result['net'].ODpair,
                                truck_share, pce, vot_truck)

    return {
        # Travel cost
        'tstt': s_tstt,
        'tstt_ratio': s_tstt / b_tstt if b_tstt > 0 else 1.0,
        'mean_trip_time': s_mean_tt,
        'mean_trip_time_ratio': s_mean_tt / b_mean_tt if b_mean_tt > 0 else 1.0,
        'delay_hours': delay_hours(lr) / 60.0,
        'delay_hours_delta': (delay_hours(lr) - delay_hours(b_lr)) / 60.0,
        # OD exposure
        'od_exposure_max': od_exp['max'],
        'od_exposure_p95': od_exp['p95'],
        'od_exposure_mean': od_exp['mean'],
        # Congestion
        'congested_links': congested_link_count(lr),
        'max_vc': max_vc(lr),
        'weighted_vc': vmt_weighted_vc(lr),
        # Unmet demand
        'unmet_demand': result['unmet_demand'],
        'unmet_share': unmet_share(result['unmet_demand'], total_demand),
        'disconnected_ods': disconnected_od_count(result['unreachable_ods']),
        # Accessibility
        'accessibility_weighted_mean': access_sum['weighted_mean'],
        'accessibility_min': access_sum['min'],
        'accessibility_gini': access_sum['gini'],
        'accessibility_loss': (b_access_sum['weighted_mean'] - access_sum['weighted_mean'])
                              / b_access_sum['weighted_mean'] if b_access_sum['weighted_mean'] > 0 else 0.0,
        # Efficiency
        'latora_efficiency': latora_efficiency(od_c, net.numZones),
        # Freight
        'truck_delay_hours': freight['truck_delay_hours'],
        'truck_cost_usd': freight['truck_cost_usd'],
        'truck_throughput': freight['truck_throughput'],
        # Economic
        'total_economic_cost': total_economic_cost(lr, result['unmet_demand'],
                                                   total_demand, vot_pax, unmet_pen),
    }
