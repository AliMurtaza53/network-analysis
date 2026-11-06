"""Unit tests for disruption mechanics. Run from repo root: pytest tests/test_resilience.py -q"""
import copy, os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
os.chdir(ROOT)

from resilience.data import load_config, load_network, build_link_geodataframe
from resilience.engine import (_remove_link, _reduce_capacity, _pregnolato_speed_ratio, _apply_spatial_footprint,
                               check_od_connectivity, CAPACITY_FLOOR)


def solve(net, gap=1e-6):
    net.userEquilibrium(stepSizeRule='FW', maxIterations=200000, targetGap=gap)


def tstt(net):
    return sum(l.flow * l.cost for l in net.link.values())


@pytest.fixture(scope='module')
def sf():
    return load_network(load_config('config/siouxfalls.yaml'))


@pytest.fixture(scope='module')
def anaheim():
    cfg = load_config('config/anaheim.yaml')
    net = load_network(cfg)
    return net, build_link_geodataframe(net, cfg)


def test_remove_link_updates_graph(sf):
    net = copy.deepcopy(sf)
    lid = next(iter(net.link)); lk = net.link[lid]; n0 = net.numLinks
    _remove_link(net, lid)
    assert lid not in net.link and net.numLinks == n0 - 1
    assert lid not in net.node[lk.tail].forwardStar and lid not in net.node[lk.head].reverseStar


def test_reduce_capacity_scales_and_floors(sf):
    net = copy.deepcopy(sf)
    lid = next(iter(net.link)); c0 = net.link[lid].capacity
    _reduce_capacity(net, lid, 0.25)
    assert net.link[lid].capacity == pytest.approx(0.75 * c0)
    _reduce_capacity(net, lid, 1.0)
    assert net.link[lid].capacity == CAPACITY_FLOOR


def test_pregnolato_depth_function():
    assert _pregnolato_speed_ratio(0.0) == pytest.approx(1.0)
    assert _pregnolato_speed_ratio(300.0) == 0.0
    r = [_pregnolato_speed_ratio(w) for w in range(0, 300, 10)]
    assert all(a >= b for a, b in zip(r, r[1:]))
    w = 150.0
    assert _pregnolato_speed_ratio(w) == pytest.approx((0.0009 * w * w - 0.5529 * w + 86.9448) / 86.9448)


def test_equilibrium_conserves_flow_and_reaches_gap(sf):
    net = copy.deepcopy(sf); solve(net, 1e-5)
    assert net.relativeGap() < 1e-5
    supply = {n: 0.0 for n in net.node}
    for od in net.ODpair.values():
        supply[od.origin] += od.demand; supply[od.destination] -= od.demand
    total = sum(od.demand for od in net.ODpair.values())
    for n in net.node:
        out = sum(net.link[l].flow for l in net.node[n].forwardStar)
        inn = sum(net.link[l].flow for l in net.node[n].reverseStar)
        assert out - inn == pytest.approx(supply[n], abs=1e-6 * total)


def test_uniform_capacity_cut_equals_demand_growth(sf):
    # Cutting every capacity to c is equivalent to demand x 1/c for time per trip.
    a = copy.deepcopy(sf)
    for lid in list(a.link):
        _reduce_capacity(a, lid, 0.5)
    b = copy.deepcopy(sf)
    for od in b.ODpair.values():
        od.demand *= 2.0
    solve(a, 1e-4); solve(b, 1e-4)
    d_a = sum(od.demand for od in a.ODpair.values()); d_b = sum(od.demand for od in b.ODpair.values())
    assert (tstt(a) / d_a) == pytest.approx(tstt(b) / d_b, rel=5e-3)


def test_single_link_removal_keeps_demand_and_connectivity(sf):
    net = copy.deepcopy(sf); total0 = sum(od.demand for od in net.ODpair.values())
    _remove_link(net, next(iter(net.link)))
    _, unreachable = check_od_connectivity(net)
    assert unreachable == [] and sum(od.demand for od in net.ODpair.values()) == pytest.approx(total0)


def test_flood_footprint_grows_with_radius_and_vanishes_at_zero_depth(anaheim):
    net0, gdf = anaheim
    def changed(radius, sev):
        n = copy.deepcopy(net0)
        _apply_spatial_footprint(n, dict(center_lon=-117.9, center_lat=33.84, radius_km=radius, severity=sev), gdf)
        return sum(1 for k, l in n.link.items() if l.capacity != net0.link[k].capacity)
    counts = [changed(r, 1.0) for r in (0.1, 1.0, 2.0, 3.0)]
    assert counts == sorted(counts) and counts[-1] > counts[0]
    assert changed(3.0, 0.0) == 0


def test_random_closure_without_connectors_never_picks_connectors(anaheim):
    from run_revision import disrupt
    net0, _ = anaheim
    for seed in range(25):
        n = copy.deepcopy(net0)
        disrupt(n, ('S1x', 10, seed))
        gone = set(net0.link) - set(n.link)
        assert len(gone) == 10
        assert all(min(int(x) for x in g.strip('()').split(',')) > 38 for g in gone)


def test_paired_baseline_ratio_is_one():
    import run_revision as rr
    rr._init()
    r = rr.run_case(dict(spec=('S0',), label='t'))
    assert r['tstt_ratio'] == pytest.approx(1.0, abs=1e-9) and r['unmet_share'] == 0
