"""Scenario definitions: what to disrupt and how."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json


@dataclass
class Scenario:
    scenario_id: str
    family: str            # S0, S1, S2, S3, S4, S5
    params: Dict[str, Any] = field(default_factory=dict)

    def params_json(self) -> str:
        return json.dumps(self.params, sort_keys=True)


# ------------------------------------------------------------------
# Scenario families
# ------------------------------------------------------------------

def baseline() -> Scenario:
    return Scenario('S0_baseline', 'S0', {})


def random_closure(k: int, seed: int) -> Scenario:
    return Scenario(f'S1_k{k}_seed{seed}', 'S1', {'k': k, 'seed': seed})


def targeted_closure(k: int) -> Scenario:
    return Scenario(f'S2_top{k}', 'S2', {'k': k})


def spatial_footprint(cx: float, cy: float, radius_km: float, severity: float = 1.0) -> Scenario:
    """Synthetic hazard footprint centered on (cx, cy) in WGS84."""
    return Scenario(
        f'S3_r{radius_km}km_sev{severity}',
        'S3',
        {'center_lon': cx, 'center_lat': cy, 'radius_km': radius_km, 'severity': severity}
    )


def corridor_closure(link_type: Optional[int] = None, capacity_fraction: float = 0.0) -> Scenario:
    """Uniform capacity loss on links of a given type, or full corridor closure."""
    return Scenario(
        f'S4_type{link_type}_cap{capacity_fraction}',
        'S4',
        {'link_type': link_type, 'capacity_fraction': capacity_fraction}
    )


def demand_surge(demand_factor: float, combine_with: Optional[Scenario] = None) -> Scenario:
    base_params: Dict[str, Any] = {'demand_factor': demand_factor}
    combo = ''
    if combine_with:
        base_params['combined_with'] = combine_with.scenario_id
        base_params['combined_params'] = combine_with.params
        combo = f'_plus_{combine_with.scenario_id}'
    return Scenario(f'S5_demand{demand_factor}{combo}', 'S5', base_params)


# ------------------------------------------------------------------
# Default Q2 scenario set
# ------------------------------------------------------------------

def default_q2_scenarios(criticality_links: Optional[List[str]] = None,
                         anaheim_center: tuple = (-117.9, 33.84)) -> List[Scenario]:
    """Generate the full Q2 scenario list."""
    scenarios = [baseline()]

    # S1: random closures
    for k in [1]:
        scenarios.append(random_closure(k, 0))
    for k in [5, 10]:
        for seed in range(30):
            scenarios.append(random_closure(k, seed))

    # S2: targeted (need criticality ranking)
    for k in [1, 3, 5]:
        scenarios.append(targeted_closure(k))

    # S3: spatial footprint
    cx, cy = anaheim_center
    for r in [1.0, 2.0, 3.0]:
        scenarios.append(spatial_footprint(cx, cy, r))

    # S4: uniform capacity loss on highest-flow link type (plan: 25, 50, 75%)
    for cap_frac in [0.25, 0.50, 0.75]:
        scenarios.append(corridor_closure(link_type=1, capacity_fraction=cap_frac))

    # S5: demand surge, alone and combined with S3 r=2
    s3_base = spatial_footprint(cx, cy, 2.0)
    for factor in [1.20, 1.40]:
        scenarios.append(demand_surge(factor))
        scenarios.append(demand_surge(factor, combine_with=s3_base))

    return scenarios
