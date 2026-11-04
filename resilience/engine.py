"""Scenario engine: copy network, apply scenario, check connectivity, solve UE."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import copy
import random
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

import network as net_module
import utils as utils_module
from resilience.scenarios import Scenario
import geopandas as gpd


CAPACITY_FLOOR = 1.0  # avoid div-by-zero in BPR when capacity is near zero


# ------------------------------------------------------------------
# Network modification helpers
# ------------------------------------------------------------------

def _remove_link(net, link_id: str):
    """Remove a link from the network in-place."""
    if link_id not in net.link:
        return
    lk = net.link[link_id]
    net.node[lk.tail].forwardStar.remove(link_id)
    net.node[lk.head].reverseStar.remove(link_id)
    del net.link[link_id]
    net.numLinks -= 1


def _reduce_capacity(net, link_id: str, severity: float, speed_reduction: bool = False):
    """Reduce link capacity by severity fraction; keep FFT unchanged by default.

    severity: fraction of capacity to remove (0.0 = no change, 1.0 = full closure).
    speed_reduction: if True, also scale FFT by (1 - severity) to model speed drop.
    """
    if link_id not in net.link:
        return
    lk = net.link[link_id]
    new_cap = max(lk.capacity * (1.0 - severity), CAPACITY_FLOOR)
    lk.capacity = new_cap
    if speed_reduction:
        lk.freeFlowTime *= (1.0 / max(1.0 - severity, 0.1))
    lk.updateCost()


# ------------------------------------------------------------------
# Reachability check (BFS respecting firstThroughNode)
# ------------------------------------------------------------------

def _reachable_set(net, origin: int) -> set:
    """BFS from origin; respects firstThroughNode constraint."""
    visited = {origin}
    queue = [origin]
    while queue:
        u = queue.pop()
        for ij in net.node[u].forwardStar:
            v = net.link[ij].head
            if v not in visited:
                # Can we pass through v? (Zone centroids blocked unless destination)
                visited.add(v)
                if v >= net.firstThroughNode or v == origin:
                    queue.append(v)
                else:
                    # v is a centroid — it's reachable as a destination but
                    # we don't expand from it (it's a sink in this BFS)
                    pass
    return visited


def check_od_connectivity(net) -> Tuple[List[str], List[str]]:
    """Return (reachable_od_ids, unreachable_od_ids)."""
    # Cache reachability per origin
    reach_cache: Dict[int, set] = {}
    reachable, unreachable = [], []
    for od_id, od in net.ODpair.items():
        orig = od.origin
        if orig not in reach_cache:
            reach_cache[orig] = _reachable_set(net, orig)
        if od.destination in reach_cache[orig]:
            reachable.append(od_id)
        else:
            unreachable.append(od_id)
    return reachable, unreachable


# ------------------------------------------------------------------
# Spatial footprint application (S3)
# ------------------------------------------------------------------

def _apply_spatial_footprint(net, params: dict, link_gdf: Optional[gpd.GeoDataFrame],
                              speed_reduction: bool = False):
    """Apply intensity-driven capacity reduction based on distance from footprint center."""
    if link_gdf is None or link_gdf.empty:
        return

    from shapely.geometry import Point
    import pyproj
    from shapely.ops import transform
    import functools

    cx = params['center_lon']
    cy = params['center_lat']
    radius_km = params['radius_km']
    severity_max = params.get('severity', 1.0)

    # Reproject center to UTM for distance in meters
    crs_metric = 'EPSG:26911'
    proj_wgs = pyproj.CRS('EPSG:4326')
    proj_utm = pyproj.CRS(crs_metric)
    transformer = pyproj.Transformer.from_crs(proj_wgs, proj_utm, always_xy=True)
    cx_m, cy_m = transformer.transform(cx, cy)

    gdf_m = link_gdf.to_crs(crs_metric) if link_gdf.crs else link_gdf

    for idx, row in gdf_m.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        centroid = geom.centroid
        dist_m = centroid.distance(Point(cx_m, cy_m))
        dist_km = dist_m / 1000.0
        if dist_km >= radius_km:
            continue
        # Pregnolato-style linear intensity decay
        intensity = 1.0 - (dist_km / radius_km)
        effective_severity = intensity * severity_max
        link_id = row['link_id']
        _reduce_capacity(net, link_id, effective_severity, speed_reduction)


# ------------------------------------------------------------------
# Main scenario application
# ------------------------------------------------------------------

def apply_scenario(net, scenario: Scenario, baseline_flows: Optional[Dict] = None,
                   criticality_ranking: Optional[List[str]] = None,
                   link_gdf: Optional[gpd.GeoDataFrame] = None,
                   demand_factor: Optional[float] = None):
    """Mutate net in-place according to scenario. Returns list of affected link_ids."""
    p = scenario.params
    affected = []

    # Demand scaling (applied regardless of family, as a combined modifier)
    df = demand_factor if demand_factor is not None else p.get('demand_factor', 1.0)
    if df != 1.0:
        for od in net.ODpair.values():
            od.demand *= df

    if scenario.family == 'S0':
        pass

    elif scenario.family == 'S1':
        # Random closure of k links
        k = p['k']
        seed = p['seed']
        rng = random.Random(seed)
        link_ids = list(net.link.keys())
        chosen = rng.sample(link_ids, min(k, len(link_ids)))
        for lid in chosen:
            _remove_link(net, lid)
            affected.append(lid)

    elif scenario.family == 'S2':
        # Targeted closure of top-k critical links
        k = p['k']
        if criticality_ranking:
            for lid in criticality_ranking[:k]:
                _remove_link(net, lid)
                affected.append(lid)

    elif scenario.family == 'S3':
        # Spatial footprint
        _apply_spatial_footprint(net, p, link_gdf)
        # Record all links affected (capacity changed)
        affected = list(net.link.keys())  # approximate

    elif scenario.family == 'S4':
        # Corridor/uniform capacity loss
        cap_frac = p.get('capacity_fraction', 0.0)
        link_type = p.get('link_type')
        severity = 1.0 - cap_frac  # capacity_fraction remaining → severity = lost fraction
        for lid, lk in list(net.link.items()):
            if link_type is None or int(lk.linkType) == link_type:
                if cap_frac == 0.0:
                    _remove_link(net, lid)
                else:
                    _reduce_capacity(net, lid, severity)
                affected.append(lid)

    elif scenario.family == 'S5':
        # Demand surge (demand already applied above)
        # If combined with another scenario, apply that scenario's physical disruption
        if 'combined_params' in p:
            combined_scenario = Scenario(
                p['combined_with'],
                p['combined_with'].split('_')[0],  # infer family from id
                p['combined_params']
            )
            # Map family from scenario id prefix
            for fam in ['S0', 'S1', 'S2', 'S3', 'S4']:
                if p['combined_with'].startswith(fam):
                    combined_scenario.family = fam
                    break
            affected += apply_scenario(net, combined_scenario, baseline_flows,
                                       criticality_ranking, link_gdf, demand_factor=None)

    # Warm start from baseline flows only for capacity-reduction scenarios.
    # For link-removal scenarios (S1, S2), baseline flows are misleading because
    # removed-link demand must redistribute; zero initialization converges faster.
    if baseline_flows is not None and scenario.family not in ('S1', 'S2', '_crit'):
        for lid in net.link:
            if lid in baseline_flows:
                net.link[lid].flow = baseline_flows[lid]
                net.link[lid].updateCost()

    return affected


# ------------------------------------------------------------------
# Run a single scenario
# ------------------------------------------------------------------

def run_scenario(config: dict, scenario: Scenario,
                 baseline_net=None,
                 baseline_flows: Optional[Dict] = None,
                 criticality_ranking: Optional[List[str]] = None,
                 link_gdf: Optional[gpd.GeoDataFrame] = None,
                 demand_factor: Optional[float] = None,
                 ) -> dict:
    """Deep-copy baseline network, apply scenario, solve UE, return results dict."""
    # Deep copy so baseline is untouched
    if baseline_net is not None:
        net = copy.deepcopy(baseline_net)
    else:
        net = net_module.Network(config['network'], config['trips'])

    affected_links = apply_scenario(net, scenario, baseline_flows, criticality_ranking,
                                    link_gdf, demand_factor)

    # Check OD connectivity
    reachable_ods, unreachable_ods = check_od_connectivity(net)
    unmet_demand = sum(net.ODpair[od_id].demand for od_id in unreachable_ods
                       if od_id in net.ODpair)

    # Remove unreachable OD pairs from solver entirely.
    # Setting demand=0 is NOT sufficient: allOrNothing traces paths for every OD pair
    # regardless of demand, and would crash on NO_PATH_EXISTS backlinks.
    removed_ods = {}
    for od_id in unreachable_ods:
        if od_id in net.ODpair:
            removed_ods[od_id] = net.ODpair.pop(od_id)

    convergence = {'relative_gaps': [], 'iteration_times': []}
    if net.ODpair and net.link:
        # Solve UE (suppress per-iteration prints)
        import io
        _old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            convergence = net.userEquilibrium(
                stepSizeRule=config.get('solver_step_rule', 'FW'),
                maxIterations=int(config.get('solver_max_iter', 1_000_000)),
                targetGap=float(config.get('solver_gap', 1e-4)),
                gapFunction=net.relativeGap,
            )
        finally:
            sys.stdout = _old_stdout

    # Restore removed OD pairs for metric computation
    for od_id, od in removed_ods.items():
        net.ODpair[od_id] = od

    # Collect OD shortest-path costs for reachable pairs
    od_costs: Dict[str, float] = {}
    for od_id in reachable_ods:
        if od_id not in net.ODpair:
            continue
        od = net.ODpair[od_id]
        _, costs = net.shortestPath(od.origin)
        od_costs[od_id] = costs.get(od.destination, float('inf'))

    # Link-level results
    link_results = {}
    for lid, lk in net.link.items():
        link_results[lid] = {
            'flow': lk.flow,
            'cost': lk.cost,
            'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0.0,
            'fft': lk.freeFlowTime,
            'capacity': lk.capacity,
            'closed': lid in affected_links and lid not in net.link,
        }

    final_gap = convergence['relative_gaps'][-1] if convergence['relative_gaps'] else float('nan')

    return {
        'scenario': scenario,
        'link_results': link_results,
        'od_costs': od_costs,
        'unmet_demand': unmet_demand,
        'unreachable_ods': unreachable_ods,
        'reachable_ods': reachable_ods,
        'affected_links': affected_links,
        'convergence': convergence,
        'final_gap': final_gap,
        'net': net,  # keep for metric computation
    }


# ------------------------------------------------------------------
# Parallelized scenario sweep
# ------------------------------------------------------------------

def run_scenarios(config: dict, scenarios: list,
                  baseline_net=None,
                  baseline_flows: Optional[Dict] = None,
                  criticality_ranking: Optional[List[str]] = None,
                  link_gdf: Optional[gpd.GeoDataFrame] = None,
                  n_jobs: int = -1) -> List[dict]:
    """Run multiple scenarios in parallel using joblib."""
    from joblib import Parallel, delayed

    def _run(sc):
        return run_scenario(config, sc, baseline_net, baseline_flows,
                            criticality_ranking, link_gdf)

    results = Parallel(n_jobs=n_jobs, prefer='threads')(
        delayed(_run)(sc) for sc in scenarios
    )
    return results
