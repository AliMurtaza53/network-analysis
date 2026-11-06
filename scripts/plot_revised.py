"""Revised figures F3, F4, F6, F8, F10, F13 from outputs/revised/ (paired baselines)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from plot_polished import PALETTE, SURFACE, INK, INK2, MUTED, GRID, BASELINE, apply_style, panel_label, save

R = 'outputs/revised'
FIG = 'outputs/revised/figures'
os.makedirs(FIG, exist_ok=True)
EDGE = dict(markeredgecolor=SURFACE, markeredgewidth=0.6)


def thousands(ax, axis='x'):
    f = matplotlib.ticker.FuncFormatter(lambda v, _: f'{v:,.0f}')
    (ax.xaxis if axis == 'x' else ax.yaxis).set_major_formatter(f)


def note(fig, text, y=-0.01):
    fig.text(0.01, y, text, fontsize=5.8, color=MUTED, ha='left', va='top')



def load_q2():
    d = pd.read_parquet(f'{R}/q2_metrics.parquet')
    b = d[d.label == 'Baseline'].iloc[0]
    acc0 = 1 - d.accessibility_weighted_mean / b.accessibility_weighted_mean
    m = d.family.isin(['S5', 'check'])
    served = d.served_share * d.total_demand
    d.loc[m, 'accessibility_loss'] = acc0[m]
    d.loc[m, 'tstt_ratio'] = (d.tstt / b.tstt)[m]
    d.loc[m, 'tt_served_ratio'] = ((d.tstt / served) / (b.tstt / b.total_demand))[m]
    chk = (acc0 - d.accessibility_loss)[~m].abs().max()
    assert chk < 1e-3, chk
    return d

# ------------------------------------------------------------------------- F3
def f3():
    apply_style()
    d = load_q2()
    d = d[d.family != 'check']
    k_of = lambda s: json.loads(s)[1] if s.startswith('["S1"') else None
    d['k'] = d.spec.map(lambda s: json.loads(s)[1] if json.loads(s)[0] == 'S1' else np.nan)
    rows = [  # (label, family, mask, marker)
        ('S1  Random closure, 5 links (n=30)', 'S1', (d.family == 'S1') & (d.k == 5), 'o'),
        ('S1  Random closure, 10 links (n=30)', 'S1', (d.family == 'S1') & (d.k == 10), 'o'),
        ('S2  Targeted closure (top-1/3/5 links)', 'S2', d.family == 'S2', 'o'),
        ('S3  Flood footprint (r = 1/2/3 km)', 'S3', d.family == 'S3', 'o'),
        ('S4a  Capacity loss, all links', 'S4', d.label.str.startswith('S4a'), 's'),
        ('S4b  Capacity loss, 10% busiest links', 'S4', d.label.str.startswith('S4b'), 'o'),
        ('S5  Demand surge (x1.2, x1.4, +disruption)', 'S5', d.family == 'S5', 'o'),
    ]
    mets = [('tstt_ratio', 'Total travel time\n(ratio to baseline, log)', True),
            ('tt_served_ratio', 'Time per served trip\n(ratio to baseline, log)', True),
            ('accessibility_loss', 'Accessibility loss\n(% of baseline)', False)]
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 3.3), sharey=True, gridspec_kw=dict(wspace=0.08, width_ratios=[1.15, 1.15, 0.8]))
    fig.subplots_adjust(left=0.30, right=0.985, top=0.94, bottom=0.30)
    n = len(rows)
    rng = np.random.default_rng(1)
    for ci, (m, xl, lg) in enumerate(mets):
        ax = axes[ci]
        ax.set_axisbelow(True); ax.xaxis.grid(True)
        if lg:
            ax.set_xscale('log'); ax.axvline(1, color=BASELINE, lw=0.8, zorder=1)
            ax.set_xticks([1, 2, 5, 10, 20]); ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlim(0.8, 45)
        else:
            ax.axvline(0, color=BASELINE, lw=0.8, zorder=1); ax.set_xlim(-3, 95)
        for ri, (lab, fam, mask, mk) in enumerate(rows):
            y0 = n - 1 - ri
            s = d[mask]
            x = s[m].values * (100 if m == 'accessibility_loss' else 1)
            c = PALETTE[fam]
            if ci == 2 and fam == 'S5':
                ax.text(3, y0, 'n/a: demand-weighted measure\nrises with demand itself', fontsize=5.6, color=MUTED, va='center'); continue
            if fam == 'S1':
                yy = y0 + rng.uniform(-0.28, 0.28, len(x))
                hollow = (s.unmet_share.values > 0)
                ax.scatter(x[~hollow], yy[~hollow], s=14, color=c, edgecolor=SURFACE, linewidth=0.4, zorder=3)
                ax.scatter(x[hollow], yy[hollow], s=14, facecolor=SURFACE, edgecolor=c, linewidth=0.9, zorder=3)
                ax.plot([np.median(x)] * 2, [y0 - 0.38, y0 + 0.38], color=INK, lw=1.1, zorder=4)
            else:
                ax.scatter(x, [y0] * len(x), s=22, marker=mk, color=c, edgecolor=SURFACE, linewidth=0.5, zorder=3)
                if len(x) > 1:
                    ax.plot([x.min(), x.max()], [y0, y0], color=c, lw=1, alpha=0.5, zorder=2)
            if ci < 2 and fam != 'S1':
                hi = x.max()
                ax.text(hi * (1.12 if lg else 1), y0 + 0.2, f'{hi:.2f}x' if hi < 10 else f'{hi:.1f}x', fontsize=6, color=INK2, va='bottom', ha='left')
            if ci == 2:
                ax.text(x.max() + 2, y0, f'{x.max():.0f}%' if x.max() >= 10 else f'{x.max():.1f}%', fontsize=6, color=INK2, va='center')
        ax.set_xlabel(xl, fontsize=6.8)
        ax.set_ylim(-0.7, n - 0.3)
        panel_label(ax, 'ABC'[ci], x=-0.02 if ci else -0.02, y=1.08)
    axes[0].set_yticks(range(n)); axes[0].set_yticklabels([r[0] for r in reversed(rows)], fontsize=6.5, color=INK2)
    axes[0].tick_params(axis='y', length=0)
    leg = [Line2D([], [], marker='o', ls='', color=MUTED, markersize=4, label='all zones still connected'),
           Line2D([], [], marker='o', ls='', markerfacecolor=SURFACE, markeredgecolor=MUTED, markersize=4, label='some zones cut off (their demand unserved)'),
           Line2D([], [], color=INK, lw=1.1, label='S1 median')]
    fig.legend(handles=leg, loc='lower center', ncol=3, bbox_to_anchor=(0.6, 0.075), fontsize=6.3)
    note(fig, 'Anaheim network, 914 links, 38 zones. Each ratio is paired with the baseline solved the same way (noise floor about 0.05%).  '
              'S1 k=1 run omitted (ratio 1.00).\nTotal travel time falls when demand goes unserved or rises because demand grows, so panel B (per served trip) is the like-for-like measure.',
         y=0.065)
    save(fig, f'{FIG}/F3_family_comparison')


# ------------------------------------------------------------------------- F4
def f4():
    apply_style()
    from resilience.data import load_config, load_network, build_link_geodataframe
    cfg = load_config('config/anaheim.yaml'); gdf = build_link_geodataframe(load_network(cfg), cfg).set_index('link_id')
    c = pd.read_parquet('outputs/q2/criticality.parquet').sort_values('ue_tstt_increase', ascending=False).reset_index(drop=True)
    bl = pd.read_parquet('outputs/q2/baseline_links.parquet').set_index('link_id')
    base = pd.read_parquet(f'{R}/q2_metrics.parquet').query("label=='Baseline'").base_tstt.iloc[0]
    N = 12
    top = c.head(N).copy(); top['rank'] = np.arange(1, N + 1)
    top['pct'] = 100 * top.ue_tstt_increase / base
    top['vc'] = top.link_id.map(bl.vc)
    ends = [tuple(s.strip('()').split(',')) for s in top.link_id]
    grp = list(range(N))
    for i in range(N):
        for j in range(i):
            if set(ends[i]) & set(ends[j]):
                grp[i] = grp[j]
    fig = plt.figure(figsize=(6.9, 3.6))
    axm = fig.add_axes([0.0, 0.12, 0.44, 0.76]); axb = fig.add_axes([0.575, 0.2, 0.27, 0.68])
    for geom in gdf.geometry:
        xs, ys = geom.xy; axm.plot(xs, ys, color='#cfcec4', lw=0.4, zorder=1)
    cent = {}
    for i, r in top.iterrows():
        g = gdf.loc[r.link_id].geometry; xs, ys = g.xy
        axm.plot(xs, ys, color=PALETTE['S2'], lw=2.2, zorder=3, solid_capstyle='round')
        cent.setdefault(grp[i], []).append((g.centroid.x, g.centroid.y, r['rank']))
    for k, pts in cent.items():
        rk = sorted(p[2] for p in pts); lab = f'{rk[0]}' if len(rk) == 1 else f'{rk[0]}\u2013{rk[-1]}'
        x = np.mean([p[0] for p in pts]); y = np.mean([p[1] for p in pts])
        axm.annotate(lab, (x, y), xytext=(0, 7), textcoords='offset points', fontsize=6.5, color=INK, ha='center', zorder=5,
                     fontweight='bold', bbox=dict(boxstyle='round,pad=0.12', fc=SURFACE, ec='none', alpha=0.9))
    axm.set_aspect(1 / np.cos(np.radians(33.84))); axm.axis('off')
    axm.set_title('Where the 12 most critical links sit (orange)', fontsize=7, loc='left', color=INK2, pad=12, x=0.07)
    yy = np.arange(N)[::-1]
    axb.barh(yy, top.pct, height=0.62, color=PALETTE['S2'], zorder=3)
    axb.set_yticks(yy); axb.set_yticklabels([f"{r}  ({a}\u2192{b})" for r, (a, b) in zip(top['rank'], ends)], fontsize=6.3, color=INK2)
    axb.tick_params(axis='y', length=0)
    tr = matplotlib.transforms.blended_transform_factory(axb.transAxes, axb.transData)
    for y, r in zip(yy, top.itertuples()):
        axb.text(r.pct + 0.4, y, f'{r.pct:.1f}%', va='center', fontsize=6, color=INK2)
        axb.text(1.2, y, f'{r.proxy_flow:,.0f}', va='center', ha='right', fontsize=6, color=MUTED, transform=tr)
        axb.text(1.4, y, f'{r.vc:.2f}', va='center', ha='right', fontsize=6, color=MUTED, transform=tr)
    axb.text(1.2, N - 0.35, 'flow\n(veh/h)', fontsize=5.8, color=MUTED, ha='right', va='bottom', transform=tr)
    axb.text(1.4, N - 0.35, 'v/c', fontsize=5.8, color=MUTED, ha='right', va='bottom', transform=tr)
    axb.set_xlim(0, 28); axb.set_ylim(-0.7, N - 0.3); axb.xaxis.grid(True); axb.set_axisbelow(True)
    axb.set_xticks([0, 5, 10, 15, 20, 25]); axb.spines['bottom'].set_bounds(0, 25)
    axb.set_xlabel('Rise in total travel time when this link alone is closed\n(% of baseline; 100% = 1.42 million veh\u00b7min per peak hour)', fontsize=6.6)
    axb.set_title('Impact of closing each link (rank, from\u2192to node)', fontsize=7, loc='left', color=INK2, x=-0.33)
    panel_label(axm, 'A', x=0.0, y=1.14); panel_label(axb, 'B', x=-0.5, y=1.12)
    note(fig, 'Single-link closures re-solved to equilibrium for the 60 links with the highest baseline flow (a screen, not exhaustive). Ranks 1\u20132 are adjacent segments of one arterial (equal effect); ranks 1\u20133 are consecutive\n'
              'links of one corridor. v/c = baseline volume-to-capacity ratio. Equilibrium noise is about 0.05% of baseline.', y=0.05)
    save(fig, f'{FIG}/F4_criticality')


# ------------------------------------------------------------------------- F6
def f6():
    apply_style()
    r = pd.read_parquet(f'{R}/recovery.parquet')
    sty = {'S2 top-1': ('S2', '-'), 'S2 top-5': ('S2', '--'), 'S3 flood r=3 km': ('S3', '-'),
           'S4b arterial cap 0.5': ('S4', '-'), 'S4b arterial cap 0.25': ('S4', '--')}
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.9, 2.9), gridspec_kw=dict(width_ratios=[1.5, 1], wspace=0.55))
    stats = []
    for lab, (fam, ls) in sty.items():
        s = r[r.label == lab].sort_values('day')
        Rv = np.trapezoid(s.q, s.day) / 90
        q = s.q.values; d = s.day.values
        t95 = next((float(np.interp(0.95, [q[i - 1], q[i]], [d[i - 1], d[i]])) for i in range(1, len(q)) if q[i] >= 0.95 > q[i - 1]), 0.0 if q[0] >= 0.95 else np.nan)
        stats.append((lab, fam, ls, Rv, q[0], t95))
        a.plot(d, q, color=PALETTE[fam], ls=ls, lw=1.6, zorder=3)
    a.set_ylim(0, 1.05); a.set_xlim(0, 90); a.yaxis.grid(True); a.set_axisbelow(True)
    a.axhline(0.95, color=BASELINE, lw=0.7, ls=':'); a.text(90, 0.955, '95%', fontsize=5.8, color=MUTED, ha='right', va='bottom')
    a.set_xlabel('Days since disruption (capacity restored linearly to day 90)'); a.set_ylabel('System performance Q(t)\n(1 = baseline)')
    a.set_xticks(range(0, 91, 15))
    a.legend(handles=[Line2D([], [], color=PALETTE[f], ls=l, lw=1.6, label=f'{lab}  (Q at day 0 = {q0:.2f})') for lab, f, l, Rv, q0, t in stats],
             loc='lower right', fontsize=6.1, handlelength=2.6)
    panel_label(a, 'A', x=-0.14, y=1.08)
    ys = np.arange(len(stats))[::-1]
    for y, (lab, fam, ls, Rv, q0, t95) in zip(ys, sorted(stats, key=lambda t: t[3])):
        b.hlines(y, q0, 1.0, color=PALETTE[fam], lw=1, alpha=0.4, zorder=2)
        b.plot(q0, y, marker='o', ms=4.5, color=SURFACE, markeredgecolor=PALETTE[fam], markeredgewidth=1.1, zorder=3, ls='')
        b.plot(Rv, y, marker='o', ms=5.5, color=PALETTE[fam], zorder=4, ls='', **EDGE)
        b.text(1.015, y, f'R={Rv:.2f}', fontsize=6, color=INK2, va='center')
    b.set_yticks(ys); b.set_yticklabels([t[0] for t in sorted(stats, key=lambda t: t[3])], fontsize=6.3, color=INK2)
    b.tick_params(axis='y', length=0)
    b.set_xlim(0, 1.14); b.set_ylim(-0.6, len(stats) - 0.4); b.xaxis.grid(True); b.set_axisbelow(True)
    b.set_xlabel('Resilience index R (filled) and Q at day 0 (open)'); b.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    panel_label(b, 'B', x=-0.62, y=1.08)
    note(fig, 'R = average of Q(t) over the 90-day horizon. Q = (share of demand served) x (baseline / disrupted mean trip time), re-solved to equilibrium every 5 days. '
              'S2 top-k: k greedily chosen links closed; S4b: all links in the busiest 10% lose capacity.', y=-0.07)
    save(fig, f'{FIG}/F6_recovery')


# ------------------------------------------------------------------------- F8
LAB = {'demand_factor': 'Demand multiplier (0.8–1.4)', 'bpr_alpha': 'BPR α (0.15–0.50)', 'bpr_power': 'BPR β (2–6)',
       'radius_km': 'Flood radius (1–5 km)', 'severity': 'Flood depth (25–100% of 300 mm)', 'gap': 'Solver gap ε (1e-4–1e-2)'}


def f8():
    apply_style()
    o = pd.read_parquet(f'{R}/oat.parquet')
    sw = lambda m, sc: o[o.scenario == sc].groupby('param')[m].agg(lambda s: s.max() - s.min())
    mets = [('tstt_ratio', 'Swing in total-travel-time impact\n(change in ratio to paired baseline, log scale)'),
            ('accessibility_loss', 'Swing in accessibility loss\n(change in fraction of baseline, log scale)')]
    order = sw('tstt_ratio', 'flood').sort_values().index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.0), sharey=True, gridspec_kw=dict(wspace=0.08))
    fig.subplots_adjust(bottom=0.33, top=0.93)
    for ci, (m, xl) in enumerate(mets):
        ax = axes[ci]; f, cl = sw(m, 'flood'), sw(m, 'closure')
        ys = np.arange(len(order)); ax.set_xscale('log'); ax.set_xlim(3e-4, 30)
        for y, p in zip(ys, order):
            xs = [f[p]] + ([cl[p]] if p in cl.index else [])
            ax.hlines(y, min(xs), max(xs), color=BASELINE, lw=0.8, zorder=1)
            ax.plot(f[p], y, marker='o', ms=6, color=PALETTE['S3'], ls='', zorder=4, **EDGE)
            lo_first = p in cl.index and cl[p] < f[p]
            ax.text(f[p] * (1.25 if lo_first else 0.8), y, f'{f[p]:.3f}', fontsize=5.8, color=INK2, va='center', ha='left' if lo_first else 'right')
            if p in cl.index:
                ax.plot(cl[p], y, marker='D', ms=5, color=PALETTE['S2'], ls='', zorder=5, **EDGE)
                ax.text(cl[p] * (0.8 if lo_first else 1.25), y, f'{cl[p]:.3f}', fontsize=5.8, color=INK2, va='center', ha='right' if lo_first else 'left')
        ax.xaxis.grid(True); ax.set_axisbelow(True); ax.set_xlabel(xl, fontsize=6.6)
        ax.set_xticks([1e-3, 1e-2, 1e-1, 1, 10]); ax.set_xticklabels(['0.001', '0.01', '0.1', '1', '10'])
        panel_label(ax, 'AB'[ci], x=-0.02, y=1.08)
    axes[0].set_yticks(ys); axes[0].set_yticklabels([LAB[p] for p in order], fontsize=6.4, color=INK2); axes[0].tick_params(axis='y', length=0)
    leg = [Line2D([], [], marker='o', ls='', color=PALETTE['S3'], markersize=5, label='reference disruption: flood, r = 3 km'),
           Line2D([], [], marker='D', ls='', color=PALETTE['S2'], markersize=4.5, label='reference disruption: top-3 link closure')]
    fig.legend(handles=leg, loc='lower center', ncol=2, bbox_to_anchor=(0.55, 0.075), fontsize=6.3)
    note(fig, 'One-at-a-time sweep; each run is compared with a baseline solved under the same parameter value. Flood radius and depth do not apply to the closure scenario.\n'
              'Value-of-time, truck share and PCE enter only the economic-cost formula (linear), so they cannot change these physical outputs and are omitted.', y=0.06)
    save(fig, f'{FIG}/F8_tornado')


# ------------------------------------------------------------------------ F10
def f10():
    apply_style()
    j = json.load(open(f'{R}/morris.json'))
    pretty = {'demand_factor': 'Demand', 'bpr_alpha': 'BPR α', 'bpr_power': 'BPR β', 'radius_km': 'Flood radius', 'severity': 'Flood depth', 'log10_gap': 'Solver gap'}
    mets = [('tstt_ratio', 'Total-travel-time impact'), ('accessibility_loss', 'Accessibility loss')]
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.9), gridspec_kw=dict(wspace=0.28))
    for ci, (m, ttl) in enumerate(mets):
        ax = axes[ci]; v = j[m]; mu, sg, cf = map(np.array, (v['mu_star'], v['sigma'], v['mu_star_conf']))
        lim = max((mu + cf).max(), sg.max()) * 1.12
        ax.plot([0, lim], [0, lim], color=BASELINE, lw=0.8, ls='--', zorder=1)
        ax.plot([0, lim], [0, 0.5 * lim], color=BASELINE, lw=0.8, ls=':', zorder=1)
        ax.text(lim * 0.98, lim * 0.93, 'σ = μ*', fontsize=5.8, color=MUTED, ha='right', rotation=0)
        ax.text(lim * 0.5, lim * 0.25 - lim * 0.07, 'σ = μ*/2', fontsize=5.8, color=MUTED, ha='center')
        small = []
        for i, nme in enumerate(v['names']):
            if mu[i] < 0.12 * lim:
                small.append(pretty[nme]); continue
            ax.errorbar(mu[i], sg[i], xerr=cf[i], fmt='o', ms=5, color=PALETTE['S1'], ecolor=PALETTE['S1'], elinewidth=0.7, capsize=1.5, markeredgecolor=SURFACE, zorder=3)
            ax.annotate(pretty[nme], (mu[i], sg[i]), xytext=(5, 4), textcoords='offset points', fontsize=6.3, color=INK2)
        if small:
            ax.text(0.03 * lim, 0.3 * lim, 'Small effect (μ* < 12% of axis):\n' + ', '.join(small), fontsize=6, color=INK2, va='top')
        ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.set_aspect('equal', 'box'); ax.grid(True); ax.set_axisbelow(True)
        ax.set_xlabel('μ*  importance (mean |elementary effect|)'); ax.set_ylabel('σ  nonlinearity / interaction')
        ax.set_title(ttl, fontsize=7, loc='left', color=INK2)
        panel_label(ax, 'AB'[ci], x=-0.2, y=1.12)
    note(fig, 'Morris screening: 16 trajectories, 4 levels, 112 model runs, each paired with its own baseline; bars are 95% bootstrap intervals on μ*. Points near σ = μ* behave nonlinearly or interact\n'
              'with other inputs; points far below it act roughly additively. Reference disruption: flood footprint, radius 1–5 km.', y=-0.02)
    save(fig, f'{FIG}/F10_morris')


# ------------------------------------------------------------------------ F13
def f13():
    apply_style()
    n = pd.read_parquet(f'{R}/numerical.parquet')
    n['gap'] = n.theta.map(lambda s: json.loads(s)['gap'])
    g = n[(n.rule == 'FW') & (n.iters > 1)].copy()
    sweep = g.drop_duplicates(['label', 'gap'])
    cols = {'S3 flood r=3 km': PALETTE['S3'], 'S2 top-3 closure': PALETTE['S2'], 'S4b arterial cap 0.5': PALETTE['S4'], 'baseline (no disruption)': MUTED}
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.7), gridspec_kw=dict(wspace=0.5, width_ratios=[1, 1, 1.05]))
    a, b, c = axes
    for lab, col in cols.items():
        s = sweep[sweep.label == lab].sort_values('gap')
        ref = s[s.gap == s.gap.min()]
        if lab == 'baseline (no disruption)':
            y = 100 * (s.tstt.values / ref.tstt.values[0] - 1)
        else:
            y = 100 * (s.tstt_ratio.values / ref.tstt_ratio.values[0] - 1)
        a.plot(s.gap, y, marker='o', ms=4, color=col, lw=1.2, label=lab, **EDGE)
        b.plot(s.gap, s.iters, marker='o', ms=4, color=col, lw=1.2, **EDGE)
    for ax in (a, b):
        ax.set_xscale('log'); ax.invert_xaxis(); ax.set_xlabel('Solver gap ε (tighter →)'); ax.grid(True); ax.set_axisbelow(True)
    a.axhline(0, color=BASELINE, lw=0.8); a.set_ylabel('Error vs ε = 1e-5 solution (%)')
    b.set_yscale('log'); b.set_ylabel('Frank–Wolfe iterations')
    a.legend(fontsize=5.6, loc='upper right', bbox_to_anchor=(1.03, 1.0))
    panel_label(a, 'A', x=-0.3, y=1.1); panel_label(b, 'B', x=-0.3, y=1.1)
    m = n[(n.iters > 1) | (n.rule == 'MSA')].copy()
    sc = ['S3 flood r=3 km', 'S2 top-3 closure', 'S4b arterial cap 0.5']
    ue = [n[(n.label == s) & (n.rule == 'FW') & (n.gap == 1e-4)].tstt_ratio.iloc[0] for s in sc]
    ao = [n[(n.label == s) & (n.rule == 'MSA')].tstt_ratio.iloc[0] for s in sc]
    x = np.arange(len(sc)); w = 0.36
    c.bar(x - w / 2, ue, w, color=[cols[s] for s in sc], zorder=3)
    c.bar(x + w / 2, ao, w, color=[cols[s] for s in sc], alpha=0.38, hatch='////', edgecolor=SURFACE, linewidth=0, zorder=3)
    for xi, u, o in zip(x, ue, ao):
        c.text(xi - w / 2 - 0.02, u + 0.015, f'{u:.2f}', ha='center', fontsize=5.6, color=INK2)
        c.text(xi + w / 2 + 0.02, o + 0.015, f'{o:.2f}', ha='center', fontsize=5.6, color=INK2)
    c.set_xticks(x); c.set_xticklabels(['Flood\nr=3 km', 'Top-3\nclosure', 'Arterial\ncap 0.5'], fontsize=6.3)
    c.axhline(1, color=BASELINE, lw=0.8); c.set_ylim(0.9, max(max(ue), max(ao)) * 1.3); c.yaxis.grid(True); c.set_axisbelow(True)
    c.set_ylabel('Impact: total travel time\n(ratio to baseline)')
    c.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=MUTED, label='full equilibrium (ε = 1e-4)'),
                      plt.Rectangle((0, 0), 1, 1, color=MUTED, alpha=0.38, hatch='////', label='single iteration (no equilibrium)')],
             fontsize=5.6, loc='upper left')
    panel_label(c, 'C', x=-0.3, y=1.1)
    note(fig, 'Impact ratios are paired with a baseline solved at the same ε (panel A, B) or the same method (panel C). Panel A baseline curve is the absolute travel time of the undisrupted network.', y=-0.1)
    save(fig, f'{FIG}/F13_numerical')


if __name__ == '__main__':
    for s in (sys.argv[1:] or ['f3', 'f4', 'f6', 'f8', 'f10', 'f13']):
        globals()[s]()
