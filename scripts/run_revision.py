"""Revision run: paired baselines, greedy targeted closure, arterial capacity loss,
working recovery restoration, and rebuilt sensitivity analysis.

Usage: python scripts/run_revision.py [q2] [recovery] [q3] [numerical] [smoke]
Outputs go to outputs/revised/ (old outputs are left untouched).
"""
import sys, os, io, copy, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from multiprocessing import Pool

from resilience.data import load_config, load_network, build_link_geodataframe
from resilience.engine import apply_scenario, check_od_connectivity, _remove_link, _reduce_capacity
from resilience.scenarios import Scenario, spatial_footprint
from resilience.metrics import compute_all
from resilience.sensitivity import _make_baseline_result

OUT = 'outputs/revised'
CENTER = (-117.9, 33.84)
G = {}
DEFAULT = dict(demand_factor=1.0, bpr_alpha=0.15, bpr_power=4.0, gap=1e-4)


def _init():
    cfg = load_config('config/anaheim.yaml')
    G['cfg'] = cfg
    G['net'] = load_network(cfg)
    G['gdf'] = build_link_geodataframe(G['net'], cfg)
    G['cache'] = {}


def _prep(theta):
    net = copy.deepcopy(G['net'])
    a, b = theta.get('bpr_alpha', 0.15), theta.get('bpr_power', 4.0)
    for lk in net.link.values():
        lk.alpha, lk.beta = a, b
        lk.updateCost()
    df = theta.get('demand_factor', 1.0)
    if df != 1.0:
        for od in net.ODpair.values():
            od.demand *= df
    return net


def _solve(net, gap, rule='FW', maxit=1_000_000):
    reach, unreach = check_od_connectivity(net)
    removed = {o: net.ODpair.pop(o) for o in unreach if o in net.ODpair}
    t0, old = time.time(), sys.stdout
    sys.stdout = io.StringIO()
    try:
        conv = net.userEquilibrium(stepSizeRule=rule, maxIterations=maxit, targetGap=gap)
    finally:
        sys.stdout = old
    secs = time.time() - t0
    for o, od in removed.items():
        net.ODpair[o] = od
    lr = {lid: {'flow': lk.flow, 'cost': lk.cost, 'fft': lk.freeFlowTime,
                'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0} for lid, lk in net.link.items()}
    od_costs = {}
    for o in reach:
        od = net.ODpair.get(o)
        if od:
            _, c = net.shortestPath(od.origin)
            od_costs[o] = c.get(od.destination, float('inf'))
    res = {'link_results': lr, 'od_costs': od_costs, 'unmet_demand': sum(od.demand for od in removed.values()),
           'unreachable_ods': unreach, 'reachable_ods': reach, 'net': net}
    return res, secs, len(conv['relative_gaps'])


def _tstt(res):
    return sum(v['flow'] * v['cost'] for v in res['link_results'].values())


def _baseline(theta, rule, maxit):
    key = (theta.get('demand_factor', 1.0), theta.get('bpr_alpha', 0.15), theta.get('bpr_power', 4.0),
           theta.get('gap', 1e-4), rule, maxit)
    if key not in G['cache']:
        net = _prep(theta)
        res, secs, it = _solve(net, theta.get('gap', 1e-4), rule, maxit)
        G['cache'][key] = (res, _make_baseline_result(res['net'], G['cfg'], G['cfg']), secs, it)
    return G['cache'][key]


def disrupt(net, spec):
    k = spec[0]
    if k == 'S0':
        return
    if k == 'S1':
        apply_scenario(net, Scenario('S1', 'S1', {'k': spec[1], 'seed': spec[2]}), None, None, None, demand_factor=None)
    elif k == 'REM':
        for lid in spec[1]:
            _remove_link(net, lid)
    elif k == 'CAP':
        for lid in spec[1]:
            _reduce_capacity(net, lid, 1.0 - spec[2])
    elif k == 'S3':
        apply_scenario(net, spatial_footprint(CENTER[0], CENTER[1], spec[1], spec[2]), None, None,
                       G['gdf'], demand_factor=None)
    elif k == 'S4a':
        for lid in list(net.link):
            _reduce_capacity(net, lid, 1.0 - spec[1])
    elif k == 'MULTI':
        for s in spec[1]:
            disrupt(net, s)
    else:
        raise ValueError(spec)


def run_case(a):
    theta = {**DEFAULT, **a.get('theta', {})}
    spec, rule, maxit = a['spec'], a.get('rule', 'FW'), a.get('maxit', 1_000_000)
    bres, bbase, bsecs, bit = _baseline(theta, rule, maxit)
    net = _prep(theta)
    disrupt(net, spec)
    res, secs, it = _solve(net, theta['gap'], rule, maxit)
    m = {k: v for k, v in compute_all(res, bbase, G['cfg']).items() if isinstance(v, (int, float, np.floating))}
    total = sum(od.demand for od in bres['net'].ODpair.values())
    served = total - res['unmet_demand']
    b_tstt, s_tstt = _tstt(bres), _tstt(res)
    m.update(label=a.get('label', ''), family=a.get('family', ''), spec=json.dumps(spec), theta=json.dumps(theta),
             rule=rule, base_tstt=b_tstt, tstt=s_tstt, total_demand=total, served_share=served / total,
             tt_served_ratio=(s_tstt / served) / (b_tstt / total) if served > 0 else np.nan,
             tstt_ratio=s_tstt / b_tstt, iters=it, secs=secs, base_iters=bit, base_secs=bsecs)
    return m


def run_recovery(a):
    theta = dict(DEFAULT)
    bres, bbase, _, _ = _baseline(theta, 'FW', 1_000_000)
    total = sum(od.demand for od in bres['net'].ODpair.values())
    b_mean = _tstt(bres) / total
    rows = []
    for day in a['days']:
        f = min(day / a['horizon'], 1.0)
        kind = a['kind']
        if f >= 1.0:
            spec = ('S0',)
        elif kind == 'REM':
            spec = ('REM', a['ids']) if f == 0 else ('CAP', a['ids'], f)
        elif kind == 'S3':
            spec = ('S3', a['radius'], a['sev'] * (1 - f))
        elif kind == 'S4b':
            spec = ('CAP', a['ids'], a['cap'] + (1 - a['cap']) * f)
        net = _prep(theta)
        disrupt(net, spec)
        res, _, _ = _solve(net, theta['gap'])
        served = total - res['unmet_demand']
        s_mean = _tstt(res) / served
        q = (served / total) * min(b_mean / s_mean, 1.0)
        rows.append(dict(label=a['label'], family=a['family'], day=day, q=q, tstt_ratio=_tstt(res) / _tstt(bres),
                         unmet_share=res['unmet_demand'] / total))
    return rows


def _pool():
    return Pool(4, initializer=_init)


# --------------------------------------------------------------------------- Q2
def stage_q2():
    os.makedirs(OUT, exist_ok=True)
    crit = pd.read_parquet('outputs/q2/criticality.parquet').sort_values('ue_tstt_increase', ascending=False)
    cand_all = crit.link_id.tolist()[:30]
    with _pool() as pool:
        chosen = [cand_all[0]]
        greedy_log = [dict(step=1, link=cand_all[0], tstt_ratio=float(crit.ue_tstt_increase.iloc[0]), note='single-link rank 1')]
        base = pool.map(run_case, [dict(spec=('S0',), label='baseline')])[0]
        for step in range(2, 6):
            cands = [c for c in cand_all if c not in chosen]
            rs = pool.map(run_case, [dict(spec=('REM', chosen + [c]), label=c) for c in cands])
            ok = [(r['tstt_ratio'], r['label']) for r in rs if r['unmet_share'] == 0]
            best = max(ok)
            chosen.append(best[1])
            greedy_log.append(dict(step=step, link=best[1], tstt_ratio=best[0], note='greedy, connectivity-preserving'))
            print('greedy step', step, best, flush=True)
        json.dump(dict(chosen=chosen, log=greedy_log), open(f'{OUT}/s2_greedy.json', 'w'), indent=1)

        arterial = pd.read_parquet('outputs/q2/baseline_links.parquet').sort_values('flow', ascending=False)
        art_ids = arterial.link_id.tolist()[:int(0.10 * len(arterial))]
        json.dump(art_ids, open(f'{OUT}/arterial_ids.json', 'w'))

        old = pd.read_parquet('outputs/q2/metrics.parquet')
        s1 = old[old.family == 'S1']
        cases = [dict(spec=('S0',), family='S0', label='Baseline')]
        for pj in s1.params_json:
            p = json.loads(pj)
            cases.append(dict(spec=('S1', p['k'], p['seed']), family='S1', label=f"S1_k{p['k']}_seed{p['seed']}"))
        for k in (1, 3, 5):
            cases.append(dict(spec=('REM', chosen[:k]), family='S2', label=f'S2 greedy top-{k}'))
        for r in (1.0, 2.0, 3.0):
            cases.append(dict(spec=('S3', r, 1.0), family='S3', label=f'S3 flood r={r:g} km'))
        for c in (0.75, 0.5, 0.25):
            cases.append(dict(spec=('S4a', c), family='S4', label=f'S4a network-wide cap {c}'))
            cases.append(dict(spec=('CAP', art_ids, c), family='S4', label=f'S4b arterial cap {c}'))
        for df in (1.2, 1.4):
            cases.append(dict(theta=dict(demand_factor=df), spec=('S0',), family='S5', label=f'S5 demand x{df}'))
            cases.append(dict(theta=dict(demand_factor=df), spec=('S3', 2.0, 1.0), family='S5',
                              label=f'S5 demand x{df} + flood r=2 km'))
            cases.append(dict(theta=dict(demand_factor=df), spec=('REM', chosen[:3]), family='S5',
                              label=f'S5 demand x{df} + S2 top-3'))
        cases.append(dict(theta=dict(demand_factor=4.0), spec=('S0',), family='check', label='check: demand x4'))
        df_ = pd.DataFrame(pool.map(run_case, cases))
    df_.to_parquet(f'{OUT}/q2_metrics.parquet', index=False)
    print(df_.groupby('family')[['tstt_ratio', 'tt_served_ratio', 'unmet_share', 'accessibility_loss']].describe().T.to_string()[:3000])


# ---------------------------------------------------------------------- recovery
def stage_recovery():
    g = json.load(open(f'{OUT}/s2_greedy.json'))['chosen']
    art = json.load(open(f'{OUT}/arterial_ids.json'))
    days = list(range(0, 91, 5))
    jobs = [dict(kind='REM', ids=g[:1], label='S2 top-1', family='S2', days=days, horizon=90),
            dict(kind='REM', ids=g[:5], label='S2 top-5', family='S2', days=days, horizon=90),
            dict(kind='S3', radius=3.0, sev=1.0, label='S3 flood r=3 km', family='S3', days=days, horizon=90),
            dict(kind='S4b', ids=art, cap=0.5, label='S4b arterial cap 0.5', family='S4', days=days, horizon=90),
            dict(kind='S4b', ids=art, cap=0.25, label='S4b arterial cap 0.25', family='S4', days=days, horizon=90)]
    with _pool() as pool:
        rows = [r for rs in pool.map(run_recovery, jobs) for r in rs]
    df = pd.DataFrame(rows)
    df.to_parquet(f'{OUT}/recovery.parquet', index=False)
    for lab, s in df.groupby('label'):
        s = s.sort_values('day')
        R = np.trapezoid(s.q, s.day) / 90
        print(lab, 'R=%.3f' % R, 'Q0=%.3f' % s.q.iloc[0])


# --------------------------------------------------------------------------- Q3
OAT = {'demand_factor': [0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4], 'bpr_alpha': [0.15, 0.25, 0.35, 0.5],
       'bpr_power': [2.0, 3.0, 4.0, 5.0, 6.0], 'radius_km': [1.0, 2.0, 3.0, 4.0, 5.0],
       'severity': [0.25, 0.5, 0.75, 1.0], 'gap': [1e-4, 1e-3, 1e-2]}
REF = dict(demand_factor=1.0, bpr_alpha=0.15, bpr_power=4.0, radius_km=3.0, severity=1.0, gap=1e-4)


def _case_from(p, scenario, g3):
    theta = dict(demand_factor=p['demand_factor'], bpr_alpha=p['bpr_alpha'], bpr_power=p['bpr_power'], gap=p['gap'])
    spec = ('S3', p['radius_km'], p['severity']) if scenario == 'flood' else ('REM', g3)
    return dict(theta=theta, spec=spec, label=scenario)


def stage_q3():
    g3 = json.load(open(f'{OUT}/s2_greedy.json'))['chosen'][:3]
    jobs, meta = [], []
    for pname, vals in OAT.items():
        for v in vals:
            p = {**REF, pname: v}
            for sc in ('flood', 'closure'):
                if sc == 'closure' and pname in ('radius_km', 'severity'):
                    continue
                jobs.append(_case_from(p, sc, g3)); meta.append(dict(param=pname, value=v, scenario=sc))
    from SALib.sample.morris import sample as msample
    from SALib.analyze.morris import analyze as manalyze
    names = ['demand_factor', 'bpr_alpha', 'bpr_power', 'radius_km', 'severity', 'log10_gap']
    problem = dict(num_vars=6, names=names, bounds=[[0.8, 1.4], [0.15, 0.5], [2, 6], [1, 5], [0.25, 1.0], [-4, -2]])
    X = msample(problem, N=16, num_levels=4, seed=7)
    n_oat = len(jobs)
    for x in X:
        p = dict(demand_factor=x[0], bpr_alpha=x[1], bpr_power=x[2], radius_km=x[3], severity=x[4], gap=10 ** x[5])
        jobs.append(_case_from(p, 'flood', g3))
    with _pool() as pool:
        res = pool.map(run_case, jobs, chunksize=2)
    oat = pd.DataFrame([{**m, **r} for m, r in zip(meta, res[:n_oat])])
    oat.to_parquet(f'{OUT}/oat.parquet', index=False)
    out = {}
    for metric in ('tstt_ratio', 'accessibility_loss', 'tt_served_ratio'):
        Y = np.array([r[metric] for r in res[n_oat:]])
        a = manalyze(problem, X, Y, num_levels=4, num_resamples=500, seed=3)
        out[metric] = dict(names=names, mu_star=list(map(float, a['mu_star'])), sigma=list(map(float, a['sigma'])),
                           mu_star_conf=list(map(float, a['mu_star_conf'])))
    json.dump(out, open(f'{OUT}/morris.json', 'w'), indent=1)
    pd.DataFrame([{**dict(zip(names, x)), **{k: r[k] for k in ('tstt_ratio', 'accessibility_loss', 'tt_served_ratio')}}
                  for x, r in zip(X, res[n_oat:])]).to_parquet(f'{OUT}/morris_runs.parquet', index=False)
    print(json.dumps({k: dict(zip(v['names'], np.round(v['mu_star'], 4))) for k, v in out.items()}, indent=1))


# ------------------------------------------------------------------- numerical
def stage_numerical():
    g = json.load(open(f'{OUT}/s2_greedy.json'))['chosen']
    art = json.load(open(f'{OUT}/arterial_ids.json'))
    scen = {'baseline (no disruption)': ('S0',), 'S3 flood r=3 km': ('S3', 3.0, 1.0),
            'S2 top-3 closure': ('REM', g[:3]), 'S4b arterial cap 0.5': ('CAP', art, 0.5)}
    jobs = [dict(spec=s, label=n, theta=dict(gap=gp)) for n, s in scen.items() for gp in (1e-2, 1e-3, 1e-4, 1e-5)]
    for n, s in list(scen.items())[1:]:
        jobs.append(dict(spec=s, label=n, rule='MSA', maxit=1))
        jobs.append(dict(spec=s, label=n, rule='FW', maxit=1_000_000))
    with _pool() as pool:
        res = pool.map(run_case, jobs, chunksize=1)
    pd.DataFrame(res).to_parquet(f'{OUT}/numerical.parquet', index=False)
    print(pd.DataFrame(res)[['label', 'theta', 'rule', 'tstt', 'tstt_ratio', 'iters', 'secs']].to_string())


# ------------------------------------------------------------ BPR uncertainty
def stage_uncert():
    g = json.load(open(f'{OUT}/s2_greedy.json'))['chosen']
    art = json.load(open(f'{OUT}/arterial_ids.json'))
    cases = []
    for a, b in ((0.15, 3.0), (0.15, 5.0), (0.50, 3.0), (0.50, 5.0)):
        th = dict(bpr_alpha=a, bpr_power=b)
        cases.append(dict(theta=th, spec=('S0',), family='S0', label='Baseline'))
        for k in (1, 3, 5):
            cases.append(dict(theta=th, spec=('REM', g[:k]), family='S2', label=f'S2 greedy top-{k}'))
        for r in (1.0, 2.0, 3.0):
            cases.append(dict(theta=th, spec=('S3', r, 1.0), family='S3', label=f'S3 flood r={r:g} km'))
        for c in (0.75, 0.5, 0.25):
            cases.append(dict(theta=th, spec=('S4a', c), family='S4', label=f'S4a network-wide cap {c}'))
            cases.append(dict(theta=th, spec=('CAP', art, c), family='S4', label=f'S4b arterial cap {c}'))
        for df in (1.2, 1.4):
            for lab, sp in ((f'S5 demand x{df}', ('S0',)), (f'S5 demand x{df} + flood r=2 km', ('S3', 2.0, 1.0)),
                            (f'S5 demand x{df} + S2 top-3', ('REM', g[:3]))):
                cases.append(dict(theta={**th, 'demand_factor': df}, spec=sp, family='S5', label=lab))
    cases.sort(key=lambda c: -(c['spec'][0] in ('S4a', 'CAP')))
    with _pool() as pool:
        res = pool.map(run_case, cases, chunksize=1)
    pd.DataFrame(res).to_parquet(f'{OUT}/uncert.parquet', index=False)
    print(pd.DataFrame(res)[['label', 'theta', 'tstt', 'iters', 'secs']].head(8).to_string())


def stage_smoke():
    _init()
    for spec in (('S0',), ('S3', 3.0, 1.0), ('REM', ['(92,91)'])):
        t = time.time()
        r = run_case(dict(spec=spec, label='smoke'))
        print(spec, round(r['tstt_ratio'], 4), round(r['tt_served_ratio'], 4), r['unmet_share'], r['iters'], round(time.time() - t, 1), flush=True)
    print('link id sample:', list(G['net'].link)[:3])


if __name__ == '__main__':
    for s in sys.argv[1:] or ['smoke']:
        t = time.time(); globals()['stage_' + s](); print(f'[{s}] {time.time() - t:.0f}s', flush=True)
