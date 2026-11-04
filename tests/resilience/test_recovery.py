"""Tests for recovery module."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import pytest
import numpy as np
from resilience.recovery import (
    recovery_linear, recovery_exponential, recovery_step,
    performance_q
)


def test_linear_boundary():
    assert recovery_linear(0, 90) == 0.0
    assert recovery_linear(90, 90) == 1.0
    assert abs(recovery_linear(45, 90) - 0.5) < 1e-9


def test_exponential_boundary():
    assert recovery_exponential(0, 90) == 0.0
    # At t=horizon should be close to 1
    assert recovery_exponential(90, 90) > 0.95


def test_step_boundary():
    assert recovery_step(0, 90) == 0.0
    assert recovery_step(89, 90) == 0.0
    assert recovery_step(90, 90) == 1.0


def test_linear_monotone():
    horizon = 90
    vals = [recovery_linear(t, horizon) for t in range(0, 91, 10)]
    assert all(vals[i] <= vals[i+1] for i in range(len(vals)-1))


def test_performance_q_baseline_is_one():
    """Q(t) should equal 1 for a no-disruption case (identical to baseline)."""
    import network as net_module
    net_b = net_module.Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
    net_b.userEquilibrium(stepSizeRule='FW', maxIterations=10000, targetGap=1e-4)

    lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0}
          for lid, lk in net_b.link.items()}
    base_result = {'link_results': lr, 'unmet_demand': 0.0, 'net': net_b,
                   'unreachable_ods': [], 'reachable_ods': list(net_b.ODpair.keys())}

    q = performance_q(base_result, base_result)
    assert abs(q - 1.0) < 0.01, f"Q(baseline) should be 1.0, got {q}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
