"""Revised figures F3, F4, F6, F8, F10, F13 (6.5 in wide, serif 11 pt, wrapped notes)."""
import sys, os, json, textwrap
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import LinearSegmentedColormap, Normalize

R, FIG, W = 'outputs/revised', 'outputs/revised/figures', 6.5
os.makedirs(FIG, exist_ok=True)
PAL = {'S1': '#2a78d6', 'S2': '#eb6834', 'S3': '#1baf7a', 'S4': '#eda100', 'S5': '#e34948', 'S0': '#898781'}
SURFACE, GRID, BASE, NOTE = '#fcfcfb', '#e1e0d9', '#b8b7ae', '#444444'
EDGE = dict(markeredgecolor=SURFACE, markeredgewidth=0.6)
VAL = 9.5  # in-plot value labels


def style():
    plt.rcParams.update({
        'font.family': 'serif', 'font.serif': ['Times New Roman', 'Liberation Serif', 'Tinos', 'DejaVu Serif'],
        'mathtext.fontset': 'stix', 'font.size': 11, 'axes.titlesize': 11, 'axes.labelsize': 11,
        'xtick.labelsize': 11, 'ytick.labelsize': 11, 'legend.fontsize': 11, 'text.color': 'black',
        'axes.labelcolor': 'black', 'xtick.color': 'black', 'ytick.color': 'black', 'axes.edgecolor': BASE,
        'axes.facecolor': SURFACE, 'figure.facecolor': SURFACE, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.linewidth': 0.6, 'grid.color': GRID, 'grid.linewidth': 0.6, 'xtick.major.width': 0.6,
        'ytick.major.width': 0.6, 'xtick.major.size': 3, 'ytick.major.size': 3, 'legend.frameon': False,
        'axes.titlelocation': 'left', 'axes.titleweight': 'bold', 'pdf.fonttype': 42, 'savefig.facecolor': SURFACE,
        'savefig.bbox': 'standard'})


def wrap(text, width=122):
    t = '\n'.join(textwrap.fill(p, width) for p in text.split('\n'))
    return t, t.count('\n') + 1


def make(rows, ncols=1, wr=None, note='', legend_rows=0, extra=0.95, **gskw):
    """rows: axes heights in inches. Notes/legend are figure-level so they span the full 6.5 in."""
    style()
    t, n = wrap(note)
    note_h = n * 8 * 1.2 / 72 + 0.06
    leg_h = 0.26 * legend_rows + 0.06 if legend_rows else 0
    H = sum(rows) + extra + note_h + leg_h
    fig = plt.figure(figsize=(W, H), layout='constrained')
    low = (note_h + leg_h) / H
    fig.get_layout_engine().set(w_pad=0.05, h_pad=0.05, wspace=0.03, hspace=0.03, rect=(0, low, 1, 1 - low))
    gs = fig.add_gridspec(len(rows), ncols, height_ratios=list(rows), width_ratios=wr, **gskw)
    fig.text(0.008, 0.004, t, fontsize=8, color=NOTE, va='bottom', ha='left', linespacing=1.15)

    def add_legend(handles, ncol):
        fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(0.5, note_h / H), ncol=ncol, borderaxespad=0,
                   handletextpad=0.4, columnspacing=1.2)
    return fig, gs, add_legend


def save(fig, name):
    fig.savefig(f'{FIG}/{name}.png', dpi=300); fig.savefig(f'{FIG}/{name}.pdf')
    print('saved', name, fig.get_size_inches())


def load_q2():
    d = pd.read_parquet(f'{R}/q2_metrics.parquet')
    b = d[d.label == 'Baseline'].iloc[0]
    acc0 = 1 - d.accessibility_weighted_mean / b.accessibility_weighted_mean
    m = d.family.isin(['S5', 'check'])
    served = d.served_share * d.total_demand
    d.loc[m, 'accessibility_loss'] = acc0[m]
    d.loc[m, 'tstt_ratio'] = (d.tstt / b.tstt)[m]
    d.loc[m, 'tt_served_ratio'] = ((d.tstt / served) / (b.tstt / b.total_demand))[m]
    assert (acc0 - d.accessibility_loss)[~m].abs().max() < 1e-3
    return d


def bpr_ranges(d):
    """Min/max of each metric across the 4 BPR corner runs plus the base case."""
    u = pd.read_parquet(f'{R}/uncert.parquet')
    th = u.theta.map(json.loads)
    u['a'], u['b'] = th.map(lambda t: t['bpr_alpha']), th.map(lambda t: t['bpr_power'])
    s0 = u[u.label == 'Baseline'].set_index(['a', 'b'])
    key = list(zip(u.a, u.b))
    b = d[d.label == 'Baseline'].iloc[0]
    u['b_tstt'] = [s0.loc[k].tstt for k in key]
    u['b_acc'] = [s0.loc[k].accessibility_weighted_mean for k in key]
    served = u.served_share * u.total_demand
    u['tstt_ratio'] = u.tstt / u.b_tstt
    u['tt_served_ratio'] = (u.tstt / served) / (u.b_tstt / u.total_demand)
    u['accessibility_loss'] = np.where(u.family == 'S5', np.nan, 1 - u.accessibility_weighted_mean / u.b_acc)
    base = d.set_index('label')
    out = {}
    for lab, g in u[u.label != 'Baseline'].groupby('label'):
        for m in ('tstt_ratio', 'tt_served_ratio', 'accessibility_loss'):
            vals = list(g[m].dropna()) + [base.loc[lab, m]]
            out[(lab, m)] = (min(vals), max(vals))
    return out


# ------------------------------------------------------------------------- F3
def f3():
    d = load_q2(); d = d[d.family != 'check']
    rng = bpr_ranges(d)
    d['k'] = d.spec.map(lambda s: json.loads(s)[1] if json.loads(s)[0] == 'S1' else np.nan)
    rows = [('S1 random,\n5 links (n = 30)', 'S1', (d.family == 'S1') & (d.k == 5), 'o'),
            ('S1 random,\n10 links (n = 30)', 'S1', (d.family == 'S1') & (d.k == 10), 'o'),
            ('S2 targeted,\ntop 1, 3, 5 links', 'S2', d.family == 'S2', 'o'),
            ('S3 flood,\nr = 1, 2, 3 km', 'S3', d.family == 'S3', 'o'),
            ('S4a capacity loss,\nall links', 'S4', d.label.str.startswith('S4a'), 's'),
            ('S4b capacity loss,\nbusiest 10% of links', 'S4', d.label.str.startswith('S4b'), 'o'),
            ('S5 demand surge,\n×1.2 and ×1.4', 'S5', d.family == 'S5', 'o')]
    mets = [('tstt_ratio', '(A) Total travel time', 'Ratio to baseline (log scale)', True),
            ('tt_served_ratio', '(B) Time per served trip', 'Ratio to baseline (log scale)', True),
            ('accessibility_loss', '(C) Accessibility', 'Loss (% of baseline)', False)]
    note = ('Anaheim network (914 links, 38 zones). Every ratio is paired with a baseline solved the same way (solver noise about 0.05%). '
            'Lines through points: S2 to S5, range across BPR parameters (alpha 0.15 to 0.50, beta 3 to 5), with an arrow where the range runs off the axis; S1, 95% bootstrap interval of the median. '
            'Total travel time falls when demand goes unserved and rises when demand grows, so panel B is the like-for-like measure. '
            'The S1 run closing a single link (ratio 1.00) is omitted.')
    fig, gs, axl = make([3.75], 3, [1.25, 1.0, 0.72], note, legend_rows=1, extra=0.75)
    axes = [fig.add_subplot(gs[0, 0])] + [fig.add_subplot(gs[0, i], sharey=None) for i in (1, 2)]
    n, rn = len(rows), np.random.default_rng(1)
    for ci, (m, ttl, xl, lg) in enumerate(mets):
        ax = axes[ci]; ax.set_axisbelow(True); ax.xaxis.grid(True)
        if lg:
            ax.set_xscale('log'); ax.axvline(1, color=BASE, lw=0.9, zorder=1)
            ax.set_xticks([1, 3, 10, 30]); ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlim(0.8, 45)
        else:
            ax.axvline(0, color=BASE, lw=0.9, zorder=1); ax.set_xlim(-3, 100); ax.set_xticks([0, 50, 100])
        for ri, (lab, fam, mask, mk) in enumerate(rows):
            y0 = n - 1 - ri; s = d[mask]; sc = 100 if m == 'accessibility_loss' else 1
            x = s[m].values * sc; col = PAL[fam]
            if ci == 2 and fam == 'S5':
                ax.text(2, y0, 'n/a: weights\nscale with\ndemand', fontsize=VAL, va='center', color=NOTE); continue
            if fam == 'S1':
                yy = y0 + rn.uniform(-0.3, 0.3, len(x)); hol = s.unmet_share.values > 0
                ax.scatter(x[~hol], yy[~hol], s=16, color=col, edgecolor=SURFACE, linewidth=0.4, zorder=3)
                ax.scatter(x[hol], yy[hol], s=16, facecolor=SURFACE, edgecolor=col, linewidth=1.0, zorder=3)
                bs = [np.median(rn.choice(x, len(x))) for _ in range(2000)]
                lo, hi = np.percentile(bs, [2.5, 97.5]); med = np.median(x)
                ax.errorbar(med, y0, xerr=[[med - lo], [hi - med]], fmt='D', ms=4, color='black', elinewidth=1.3, capsize=3, zorder=5)
            else:
                ax.scatter(x, [y0] * len(x), s=26, marker=mk, color=col, edgecolor=SURFACE, linewidth=0.5, zorder=4)
                top = ax.get_xlim()[1]
                for xi, lb in zip(x, s.label):
                    lo, hi = rng[(lb, m)]
                    ax.plot([max(lo * sc, ax.get_xlim()[0]), min(hi * sc, top)], [y0, y0], color=col, lw=1.3, alpha=0.55, zorder=3, solid_capstyle='butt')
                    if hi * sc > top:
                        ax.plot(top, y0, marker='>', ms=5, color=col, clip_on=False, zorder=4)
            if ci < 2 and fam != 'S1':
                hi = max(rng[(lb, m)][1] for lb in s.label)
                ax.text(ax.get_xlim()[1], y0 + 0.32, f'upper bound {hi:.1f}×' if hi < 100 else f'upper bound {hi:.0f}×', fontsize=VAL, va='bottom', ha='right')
        ax.set_xlabel(xl); ax.set_title(ttl, pad=4); ax.set_ylim(-0.6, n - 0.4)
        ax.set_yticks(range(n)); ax.tick_params(axis='y', length=0)
        ax.set_yticklabels([r[0] for r in reversed(rows)] if ci == 0 else [])
    axl([Line2D([], [], marker='o', ls='', color='#777', markersize=5, label='All zones connected'),
                 Line2D([], [], marker='o', ls='', markerfacecolor=SURFACE, markeredgecolor='#777', markersize=5, label='Some zones cut off'),
                 Line2D([], [], marker='D', color='black', markersize=4, label='S1 median ± 95% interval')], 3)
    save(fig, 'F3_family_comparison')


# ------------------------------------------------------------------------- F4
def f4():
    from resilience.data import load_config, load_network, build_link_geodataframe
    cfg = load_config('config/anaheim.yaml'); gdf = build_link_geodataframe(load_network(cfg), cfg).set_index('link_id')
    ends_of = lambda s: tuple(int(x) for x in s.strip('()').split(','))
    c = pd.read_parquet('outputs/q2/criticality.parquet').sort_values('ue_tstt_increase', ascending=False).reset_index(drop=True)
    base = pd.read_parquet(f'{R}/q2_metrics.parquet').query("label=='Baseline'").base_tstt.iloc[0]
    N = 15
    top = c.head(N).copy(); top['rank'] = np.arange(1, N + 1); top['pct'] = 100 * top.ue_tstt_increase / base
    cmap = LinearSegmentedColormap.from_list('o', ['#f8d2bd', '#eb6834', '#8a2c04']); norm = Normalize(0, 25)
    note = ('Closing one link at a time and re-solving to equilibrium, for the 60 links with the highest baseline flow (a screen, not exhaustive). '
            'Both directions of a road share one geometry, so ranks 1 to 5 sit on one corridor (as do ranks 6 and 7, and 8 to 10). '
            'Ranks 1 and 2 are adjacent segments of one arterial and have identical effect. Zone-centroid connectors are not drawn. '
            '100% = 1.42 million vehicle-minutes per peak hour. Solver noise is about 0.05%.')
    fig, gs, _ = make([3.2], 2, [1.6, 1.0], note, extra=0.75)
    axm, axb = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    is_conn = lambda lid: min(ends_of(lid)) <= 38
    for lid, geo in gdf.geometry.items():
        if not is_conn(lid):
            xs, ys = geo.xy; axm.plot(xs, ys, color='#c9c8be', lw=0.5, zorder=1)
    cents = []
    for _, r in top.sort_values('pct').iterrows():
        geo = gdf.loc[r.link_id].geometry; xs, ys = geo.xy
        axm.plot(xs, ys, color=cmap(norm(r.pct)), lw=3.0, zorder=3, solid_capstyle='round')
        cents.append((r['rank'], geo.centroid.x, geo.centroid.y))
    cl = []
    for rk, x, y in sorted(cents):
        for g in cl:
            if any(np.hypot(x - a, y - b) < 0.008 for _, a, b in g):
                g.append((rk, x, y)); break
        else:
            cl.append([(rk, x, y)])
    for g in cl:
        rk = sorted(p[0] for p in g)
        runs, st = [], rk[0]
        for u, v in zip(rk, rk[1:] + [None]):
            if v != u + 1:
                runs.append(str(st) if st == u else f'{st}–{u}'); st = v
        lab = ', '.join(runs)
        axm.annotate(lab, (np.mean([p[1] for p in g]), np.mean([p[2] for p in g])), xytext=(0, 6), textcoords='offset points',
                     fontsize=11, ha='center', fontweight='bold', zorder=6, bbox=dict(boxstyle='round,pad=0.1', fc=SURFACE, ec='none', alpha=0.9))
    axm.set_aspect(1 / np.cos(np.radians(33.84))); axm.axis('off'); axm.set_title('(A) Location', pad=4)
    axm.set_anchor('N')
    cax = axm.inset_axes([0.1, -0.16, 0.8, 0.045])
    cb = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation='horizontal')
    cb.set_label('Rise in travel time if closed (%)'); cb.outline.set_linewidth(0.4)
    yy = np.arange(N)[::-1]
    axb.barh(yy, top.pct, height=0.68, color=[cmap(norm(p)) for p in top.pct], zorder=3)
    axb.set_yticks(yy); axb.set_yticklabels([f'{r}  ({ends_of(l)[0]}→{ends_of(l)[1]})' for r, l in zip(top['rank'], top.link_id)])
    axb.tick_params(axis='y', length=0)
    for y, p in zip(yy, top.pct):
        axb.text(p + 0.4, y, f'{p:.1f}', va='center', fontsize=VAL)
    axb.set_xlim(0, 27); axb.set_ylim(-0.7, N - 0.3); axb.xaxis.grid(True); axb.set_axisbelow(True)
    axb.set_xticks([0, 5, 10, 15, 20, 25]); axb.set_xlabel('Rise in travel time (% of baseline)')
    axb.set_title('(B) Impact of each closure', pad=4)
    save(fig, 'F4_criticality')


# ------------------------------------------------------------------------- F6
def f6():
    r = pd.read_parquet(f'{R}/recovery.parquet')
    sty = [('S2 top-1', 'S2 top-1 closure', 'S2', '-'), ('S2 top-5', 'S2 top-5 closure', 'S2', '--'),
           ('S3 flood r=3 km', 'S3 flood, r = 3 km', 'S3', '-'), ('S4b arterial cap 0.5', 'S4b busiest links, cap 0.5', 'S4', '-'),
           ('S4b arterial cap 0.25', 'S4b busiest links, cap 0.25', 'S4', '--')]
    note = ('Capacity is restored linearly over 90 days and equilibrium is re-solved every 5 days. Q = (share of demand served) × '
            '(baseline mean trip time ÷ disrupted mean trip time). R is the average of Q over the 90-day horizon. '
            'S2 top-k closes the k greedily chosen links; S4b cuts capacity on the busiest 10% of links.')
    fig, gs, _ = make([2.35, 1.75], 1, None, note, extra=1.25)
    a, b = fig.add_subplot(gs[0]), fig.add_subplot(gs[1])
    stats = []
    for key, nm, fam, ls in sty:
        s = r[r.label == key].sort_values('day'); d, q = s.day.values, s.q.values
        stats.append((nm, fam, ls, np.trapezoid(q, d) / 90, q[0]))
        a.plot(d, q, color=PAL[fam], ls=ls, lw=1.8, zorder=3)
    a.set_ylim(0, 1.04); a.set_xlim(0, 90); a.yaxis.grid(True); a.set_axisbelow(True); a.set_xticks(range(0, 91, 15))
    a.axhline(0.95, color=BASE, lw=0.8, ls=':')
    a.set_xlabel('Days since disruption'); a.set_ylabel('System performance Q'); a.set_title('(A) Recovery curves', pad=4)
    a.legend(handles=[Line2D([], [], color=PAL[f], ls=l, lw=1.8, label=nm) for nm, f, l, _, _ in stats], loc='lower right', ncol=1)
    order = sorted(stats, key=lambda t: t[3]); ys = np.arange(len(order))
    for y, (nm, fam, ls, Rv, q0) in zip(ys, order):
        b.hlines(y, q0, Rv, color=PAL[fam], lw=1.4, alpha=0.5, zorder=2)
        b.plot(q0, y, marker='o', ms=6, color=SURFACE, markeredgecolor=PAL[fam], markeredgewidth=1.3, ls='', zorder=3)
        b.plot(Rv, y, marker='o', ms=7, color=PAL[fam], ls='', zorder=4, **EDGE)
        b.text(Rv + 0.02, y, f'R = {Rv:.2f}', va='center', fontsize=VAL)
    b.set_yticks(ys); b.set_yticklabels([t[0] for t in order]); b.tick_params(axis='y', length=0)
    b.set_xlim(0, 1.13); b.set_ylim(-0.6, len(order) - 0.4); b.xaxis.grid(True); b.set_axisbelow(True)
    b.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0]); b.set_xlabel('Q at day 0 (open marker) and resilience index R (filled marker)')
    b.set_title('(B) Resilience index', pad=4)
    save(fig, 'F6_recovery')


# ------------------------------------------------------------------------- F8
LAB = {'demand_factor': 'Demand multiplier (0.8–1.4)', 'bpr_alpha': 'BPR α (0.15–0.50)', 'bpr_power': 'BPR β (2–6)',
       'radius_km': 'Flood radius (1–5 km)', 'severity': 'Flood depth (25–100%)', 'gap': 'Solver gap (1e-4–1e-2)'}


def f8():
    o = pd.read_parquet(f'{R}/oat.parquet')
    sw = lambda m, sc: o[o.scenario == sc].groupby('param')[m].agg(lambda s: s.max() - s.min())
    order = sw('tstt_ratio', 'flood').sort_values().index.tolist()
    note = ('One-at-a-time sweep; every run is compared with a baseline solved at the same parameter value. Flood radius and depth do not '
            'apply to the closure scenario. Value of time, truck share and passenger-car equivalents enter only the linear economic-cost '
            'formula and cannot change these physical outputs, so they are omitted.')
    fig, gs, axl = make([2.6], 2, [1.25, 1.0], note, legend_rows=1, extra=0.75)
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])]
    for ci, (m, ttl, xl) in enumerate([('tstt_ratio', '(A) Total travel time', 'Swing (log scale)'),
                                       ('accessibility_loss', '(B) Accessibility loss', 'Swing (log scale)')]):
        ax = axes[ci]; f, cl = sw(m, 'flood'), sw(m, 'closure'); ys = np.arange(len(order))
        ax.set_xscale('log'); ax.set_xlim(1e-4, 60)
        for y, p in zip(ys, order):
            xs = [f[p]] + ([cl[p]] if p in cl.index else [])
            ax.hlines(y, min(xs), max(xs), color=BASE, lw=0.9, zorder=1)
            lo_first = p in cl.index and cl[p] < f[p]
            ax.plot(f[p], y, marker='o', ms=7, color=PAL['S3'], ls='', zorder=4, **EDGE)
            ax.text(f[p] * (1.6 if lo_first else 0.65), y, f'{f[p]:.3f}', fontsize=VAL, va='center', ha='left' if lo_first else 'right')
            if p in cl.index:
                ax.plot(cl[p], y, marker='D', ms=6, color=PAL['S2'], ls='', zorder=5, **EDGE)
                ax.text(cl[p] * (0.65 if lo_first else 1.6), y, f'{cl[p]:.3f}', fontsize=VAL, va='center', ha='right' if lo_first else 'left')
        ax.xaxis.grid(True); ax.set_axisbelow(True); ax.set_xlabel(xl); ax.set_title(ttl, pad=4)
        ax.set_xticks([1e-3, 1e-1, 10]); ax.set_xticklabels(['0.001', '0.1', '10'])
        ax.set_ylim(-0.6, len(order) - 0.4); ax.set_yticks(ys); ax.tick_params(axis='y', length=0)
        ax.set_yticklabels([LAB[p] for p in order] if ci == 0 else [])
    axl([Line2D([], [], marker='o', ls='', color=PAL['S3'], markersize=6, label='Flood, r = 3 km'),
                 Line2D([], [], marker='D', ls='', color=PAL['S2'], markersize=5.5, label='Top-3 link closure')], 2)
    save(fig, 'F8_tornado')


# ------------------------------------------------------------------------ F10
def f10():
    j = json.load(open(f'{R}/morris.json'))
    pretty = {'demand_factor': 'Demand', 'bpr_alpha': 'BPR α', 'bpr_power': 'BPR β', 'radius_km': 'Flood radius',
              'severity': 'Flood depth', 'log10_gap': 'Solver gap'}
    note = ('Morris screening: 16 trajectories, 4 levels, 112 model runs, each paired with a baseline solved at the same parameter values; '
            'error bars are 95% bootstrap intervals on μ*. Points near σ = μ* are nonlinear or interact with other inputs; points far '
            'below it act roughly additively. Reference disruption: flood footprint with radius 1 to 5 km.')
    fig, gs, _ = make([2.55], 2, None, note, extra=0.75)
    for ci, (m, ttl) in enumerate([('tstt_ratio', '(A) Total travel time impact'), ('accessibility_loss', '(B) Accessibility loss')]):
        ax = fig.add_subplot(gs[0, ci]); v = j[m]; mu, sg, cf = map(np.array, (v['mu_star'], v['sigma'], v['mu_star_conf']))
        lim = max((mu + cf).max(), sg.max()) * 1.1
        ax.plot([0, lim], [0, lim], color=BASE, lw=0.9, ls='--', zorder=1); ax.plot([0, lim], [0, lim / 2], color=BASE, lw=0.9, ls=':', zorder=1)
        ax.text(lim * 0.97, lim * 0.97, 'σ = μ*', fontsize=VAL, ha='right', va='top', rotation=0)
        ax.text(lim * 0.97, lim * 0.485 + lim * 0.02, 'σ = μ*/2', fontsize=VAL, ha='right', va='bottom')
        small = []
        for i, nme in enumerate(v['names']):
            if mu[i] < 0.12 * lim:
                small.append(pretty[nme]); continue
            ax.errorbar(mu[i], sg[i], xerr=cf[i], fmt='o', ms=6, color=PAL['S1'], ecolor=PAL['S1'], elinewidth=0.9, capsize=2.5,
                        markeredgecolor=SURFACE, zorder=3)
            ax.annotate(pretty[nme], (mu[i], sg[i]), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=11)
        ax.text(0.98 * lim, 0.03 * lim, 'Small effect (μ* < 12% of axis):\n' + ', '.join(small[:2]) + ',\n' + ', '.join(small[2:]),
                fontsize=VAL, va='bottom', ha='right', color=NOTE)
        ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.set_aspect('equal', 'box'); ax.grid(True); ax.set_axisbelow(True)
        ax.set_xlabel('μ* (mean absolute elementary effect)'); ax.set_ylabel('σ (nonlinearity and interaction)'); ax.set_title(ttl, pad=4)
    save(fig, 'F10_morris')


# ------------------------------------------------------------------------ F13
def f13():
    n = pd.read_parquet(f'{R}/numerical.parquet'); n['gap'] = n.theta.map(lambda s: json.loads(s)['gap'])
    sweep = n[(n.rule == 'FW') & (n.iters > 1)].drop_duplicates(['label', 'gap'])
    cols = {'S3 flood r=3 km': (PAL['S3'], 'Flood, r = 3 km'), 'S2 top-3 closure': (PAL['S2'], 'Top-3 link closure'),
            'S4b arterial cap 0.5': (PAL['S4'], 'S4b busiest links, cap 0.5'), 'baseline (no disruption)': (PAL['S0'], 'Baseline, absolute travel time')}
    note = ('Panels A and B: Frank–Wolfe solver gap ε swept from 1e-2 to 1e-5; errors are relative to the ε = 1e-5 solution, and impact ratios are '
            'paired with a baseline solved at the same ε. Panel C: impact ratio at ε = 1e-4 against a single assignment iteration with no '
            'equilibrium, each paired with a baseline from the same method; the printed value is the single-iteration ratio relative to full equilibrium.')
    fig, gs, axl = make([2.35], 3, [1, 1, 1.0], note, legend_rows=2, extra=0.8)
    a, b, c = [fig.add_subplot(gs[0, i]) for i in range(3)]
    for lab, (col, _) in cols.items():
        s = sweep[sweep.label == lab].sort_values('gap'); ref = s.iloc[0]
        y = 100 * (s.tstt.values / ref.tstt - 1) if lab.startswith('baseline') else 100 * (s.tstt_ratio.values / ref.tstt_ratio - 1)
        a.plot(s.gap, y, marker='o', ms=5, color=col, lw=1.4, **EDGE); b.plot(s.gap, s.iters, marker='o', ms=5, color=col, lw=1.4, **EDGE)
    for ax in (a, b):
        ax.set_xscale('log'); ax.invert_xaxis(); ax.set_xlabel('Solver gap ε'); ax.grid(True); ax.set_axisbelow(True)
        ax.set_xticks([1e-2, 1e-3, 1e-4, 1e-5])
    a.axhline(0, color=BASE, lw=0.8); a.set_ylabel('Error versus ε = 1e-5 (%)'); b.set_yscale('log'); b.set_ylabel('Solver iterations')
    a.set_title('(A) Accuracy', pad=4); b.set_title('(B) Cost', pad=4)
    sc = ['S3 flood r=3 km', 'S2 top-3 closure', 'S4b arterial cap 0.5']
    ue = [n[(n.label == s) & (n.rule == 'FW') & (n.gap == 1e-4)].tstt_ratio.iloc[0] for s in sc]
    ao = [n[(n.label == s) & (n.rule == 'MSA')].tstt_ratio.iloc[0] for s in sc]
    x = np.arange(3); w = 0.38
    c.bar(x - w / 2, ue, w, color=[cols[s][0] for s in sc], zorder=3)
    c.bar(x + w / 2, ao, w, color=[cols[s][0] for s in sc], alpha=0.4, hatch='////', edgecolor=SURFACE, linewidth=0, zorder=3)
    for xi, u, o_ in zip(x, ue, ao):
        c.text(xi, max(u, o_) + 0.04, f'{(o_ / u - 1) * 100:+.1f}%', ha='center', fontsize=VAL)
    c.set_xticks(x); c.set_xticklabels(['Flood', 'Closure', 'S4b']); c.axhline(1, color=BASE, lw=0.8)
    c.set_ylim(0.9, 2.3); c.yaxis.grid(True); c.set_axisbelow(True); c.set_ylabel('Impact ratio'); c.set_title('(C) Model form', pad=4)
    h = [Line2D([], [], color=v[0], marker='o', lw=1.4, markersize=5, label=v[1]) for v in cols.values()]
    h += [Patch(facecolor=PAL['S0'], label='Full equilibrium, ε = 1e-4'), Patch(facecolor=PAL['S0'], alpha=0.4, hatch='////', edgecolor=SURFACE, label='Single iteration')]
    axl(h, 3)
    save(fig, 'F13_numerical')


if __name__ == '__main__':
    for s in (sys.argv[1:] or ['f3', 'f4', 'f6', 'f8', 'f10', 'f13']):
        globals()[s]()
