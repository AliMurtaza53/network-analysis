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
    """Calculate key performance metrics."""
    tstt = sum(link.flow * link.cost for link in net.link.values())
    total_demand = sum(od.demand for origin_dict in net.ODpair.values() 
                      for od in origin_dict.values())
    
    return {
        'tstt': tstt,
        'total_demand': total_demand,
        'relative_gap': net.relativeGap(),
        'avg_excess_cost': net.averageExcessCost()
    }


def scale_capacity(net: Network, link_ids: List[Tuple], 
                   capacity_factor: float = 2.0, 
                   fft_factor: float = None) -> None:
    """Scale capacity and free flow time on selected links.
    
    Can model capacity expansion (factor > 1.0) or reduction (factor < 1.0).
    By default, free flow time adjusts inversely to capacity:
    - Double capacity (2.0x) → halve FFT (0.5x)
    - Halve capacity (0.5x) → double FFT (2.0x)
    
    Args:
        net: Network object
        link_ids: List of (i, j) tuples for links to modify
        capacity_factor: Capacity multiplication factor (default: 2.0 = doubling)
        fft_factor: Free flow time multiplication factor 
                   (default: None = auto-compute as 1/capacity_factor)
    
    Example:
        >>> # Expand highway: double capacity, auto-adjust FFT to 0.5x
        >>> scale_capacity(net, [("5","9"), ("9","10")])
        
        >>> # Custom: 50% capacity increase, manual FFT adjustment
        >>> scale_capacity(net, links, capacity_factor=1.5, fft_factor=0.8)
        
        >>> # Bottleneck study: reduce capacity, FFT increases automatically
        >>> scale_capacity(net, links, capacity_factor=0.5)  # FFT becomes 2.0x
    """
    # Auto-compute FFT factor if not provided: inverse of capacity factor
    if fft_factor is None:
        fft_factor = 1.0 / capacity_factor
    
    for link_id in link_ids:
        if link_id in net.link:
            net.link[link_id].capacity *= capacity_factor
            net.link[link_id].freeFlowTime *= fft_factor
            net.link[link_id].updateCost()
        else:
            # Silently skip missing links (they may not exist in all networks)
            pass
