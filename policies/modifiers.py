"""Policy modifiers for network capacity and demand changes.

Functions to systematically modify network.py Network objects for policy analysis.
"""
from typing import Dict, Tuple, List
from network import Network


def expand_capacity(net: Network, link_ids: List[Tuple], factor: float) -> None:
    """Expand capacity on specified links.
    
    Args:
        net: Network object
        link_ids: List of (i, j) tuples for links to expand
        factor: Multiplication factor (e.g., 1.25 for +25%)
    """
    for link_id in link_ids:
        if link_id in net.link:
            net.link[link_id].capacity *= factor
            net.link[link_id].updateCost()


def scale_capacity_systematic(net: Network, factor: float) -> None:
    """Scale all link capacities by a uniform factor.
    
    Args:
        net: Network object
        factor: Multiplication factor (e.g., 1.1 for +10% on all links)
    """
    for link in net.link.values():
        link.capacity *= factor
        link.updateCost()


def scale_demand(net: Network, factor: float) -> None:
    """Scale all OD demand by a uniform factor.
    
    Args:
        net: Network object
        factor: Multiplication factor (e.g., 1.2 for 20% demand growth)
    """
    for origin_dict in net.ODpair.values():
        for od in origin_dict.values():
            od.demand *= factor


def scale_specific_demand(net: Network, od_pairs: List[Tuple], factor: float) -> None:
    """Scale demand for specific OD pairs.
    
    Args:
        net: Network object
        od_pairs: List of (origin, destination) tuples
        factor: Multiplication factor
    """
    for origin, destination in od_pairs:
        if origin in net.ODpair and destination in net.ODpair[origin]:
            net.ODpair[origin][destination].demand *= factor


def add_toll(net: Network, link_ids: List[Tuple], toll_amount: float) -> None:
    """Add toll to specified links (modifies cost function).
    
    Args:
        net: Network object
        link_ids: List of (i, j) tuples for toll links
        toll_amount: Additional cost (time units or monetary)
    """
    for link_id in link_ids:
        if link_id in net.link:
            net.link[link_id].toll = toll_amount
            net.link[link_id].updateCost()


def remove_toll(net: Network, link_ids: List[Tuple]) -> None:
    """Remove toll from specified links.
    
    Args:
        net: Network object
        link_ids: List of (i, j) tuples
    """
    for link_id in link_ids:
        if link_id in net.link:
            net.link[link_id].toll = 0
            net.link[link_id].updateCost()


def reset_flows(net: Network) -> None:
    """Reset all link flows to zero.
    
    Args:
        net: Network object
    """
    for link in net.link.values():
        link.flow = 0


def get_metrics(net: Network) -> Dict:
    """Calculate key performance metrics.
    
    Args:
        net: Network object (solved)
    
    Returns:
        Dict with keys: tstt, avg_cost, max_utilization, congested_links, total_demand
    """
    tstt = sum(link.flow * link.cost for link in net.link.values())
    total_flow = sum(link.flow for link in net.link.values())
    avg_cost = tstt / total_flow if total_flow > 0 else 0
    
    utilizations = [link.flow / link.capacity for link in net.link.values() if link.capacity > 0]
    max_util = max(utilizations) if utilizations else 0
    
    congested = sum(1 for u in utilizations if u > 1.0)
    
    total_demand = sum(sum(od.demand for od in origin_dict.values()) 
                       for origin_dict in net.ODpair.values())
    
    return {
        'tstt': tstt,
        'avg_cost': avg_cost,
        'max_utilization': max_util,
        'congested_links': congested,
        'total_demand': total_demand,
        'relative_gap': net.relativeGap(),
        'avg_excess_cost': net.averageExcessCost()
    }
