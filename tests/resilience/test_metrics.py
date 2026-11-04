"""Unit tests for metrics.py — hand-checkable outcomes on simple networks."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import pytest
import math
from resilience.metrics import (
    tstt, mean_trip_time, delay_hours, worst_case_od_exposure,
    congested_link_count, max_vc, unmet_share, hansen_accessibility,
    hansen_summary, latora_efficiency, topology_indices, _gini
)


def _lr(flow, cost, fft, capacity):
    vc = flow / capacity if capacity > 0 else 0
    return {'flow': flow, 'cost': cost, 'fft': fft, 'capacity': capacity, 'vc': vc}


# ------------------------------------------------------------------
# Travel cost
# ------------------------------------------------------------------

def test_tstt_simple():
    lr = {'a': _lr(100, 2.0, 1.0, 200), 'b': _lr(50, 3.0, 1.5, 200)}
    assert abs(tstt(lr) - (100 * 2.0 + 50 * 3.0)) < 1e-9


def test_mean_trip_time():
    lr = {'a': _lr(100, 2.0, 1.0, 200)}
    assert abs(mean_trip_time(lr, 100) - 2.0) < 1e-9


def test_delay_hours_no_negative():
    # Flow below capacity: fft should equal cost, so delay = 0
    lr = {'a': _lr(0, 1.0, 1.0, 200)}
    assert delay_hours(lr) == 0.0


def test_delay_hours_positive():
    lr = {'a': _lr(100, 2.5, 1.0, 200)}
    expected = 100 * (2.5 - 1.0)
    assert abs(delay_hours(lr) - expected) < 1e-9


def test_od_exposure_max():
    od = {'1->2': 5.0, '1->3': 3.0}
    base = {'1->2': 2.0, '1->3': 2.0}
    exp = worst_case_od_exposure(od, base)
    assert abs(exp['max'] - 3.0) < 1e-9
    assert abs(exp['p95'] - 3.0) < 0.5  # may differ due to percentile rounding


# ------------------------------------------------------------------
# Congestion
# ------------------------------------------------------------------

def test_congested_link_count():
    lr = {
        'a': _lr(200, 2.0, 1.0, 100),  # vc=2.0 > 1.0 → congested
        'b': _lr(50, 1.2, 1.0, 100),   # vc=0.5 → not congested
    }
    assert congested_link_count(lr) == 1


def test_max_vc():
    lr = {'a': _lr(200, 2.0, 1.0, 100), 'b': _lr(50, 1.2, 1.0, 100)}
    assert abs(max_vc(lr) - 2.0) < 1e-9


# ------------------------------------------------------------------
# Unmet demand
# ------------------------------------------------------------------

def test_unmet_share_zero():
    assert unmet_share(0.0, 1000.0) == 0.0


def test_unmet_share_half():
    assert abs(unmet_share(500.0, 1000.0) - 0.5) < 1e-9


# ------------------------------------------------------------------
# Accessibility
# ------------------------------------------------------------------

def test_hansen_no_negative_attraction():
    od = {'1->2': 10.0, '1->3': 5.0}
    att = {'2': 100.0, '3': 50.0}
    access = hansen_accessibility(od, att, beta=0.1)
    assert '1' in access
    assert access['1'] > 0


def test_hansen_summary_gini_uniform():
    # All zones equal → Gini = 0
    access = {'1': 1.0, '2': 1.0, '3': 1.0}
    s = hansen_summary(access)
    assert abs(s['gini']) < 1e-9


def test_gini_sorted():
    import numpy as np
    arr = np.array([1.0, 2.0, 3.0, 4.0])
    g = _gini(arr)
    assert 0 <= g <= 1


# ------------------------------------------------------------------
# Efficiency
# ------------------------------------------------------------------

def test_latora_efficiency_simple():
    od = {'1->2': 2.0, '1->3': 4.0}
    eff = latora_efficiency(od, num_zones=3)
    expected = (1/2.0 + 1/4.0) / 2
    assert abs(eff - expected) < 1e-9


# ------------------------------------------------------------------
# Topology
# ------------------------------------------------------------------

def test_topology_sioux_falls_approx():
    t = topology_indices(416, 914, 38)
    assert abs(t['beta'] - 914/416) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
