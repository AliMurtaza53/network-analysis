"""Polished figures for Q2 and Q3 — dataviz skill palette, paper-ready."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.patches import FancyArrowPatch
import json

# ── Style ─────────────────────────────────────────────────────────────────────
PALETTE = {          # dataviz skill categorical slots, ordered for adjacency CVD
    'S1': '#2a78d6', # blue   – random closure
    'S2': '#eb6834', # orange – targeted closure
    'S3': '#1baf7a', # aqua   – flood footprint
    'S4': '#eda100', # yellow – corridor loss
    'S5': '#e34948', # red    – demand surge
    'S0': '#898781', # muted  – baseline reference
}
FAMILY_LABELS = {
    'S1': 'Random closure',
    'S2': 'Targeted closure',
    'S3': 'Flood footprint',
    'S4': 'Corridor loss',
    'S5': 'Demand surge',
}
SURFACE   = '#fcfcfb'
INK       = '#0b0b0b'
INK2      = '#52514e'
MUTED     = '#898781'
GRID      = '#e1e0d9'
BASELINE  = '#c3c2b7'

RC = {
    'font.family': 'DejaVu Sans',
    'font.size': 7,
    'axes.titlesize': 8,
    'axes.labelsize': 7,
    'xtick.labelsize': 6.5,
    'ytick.labelsize': 6.5,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': True,
    'axes.spines.bottom': True,
    'axes.linewidth': 0.5,
    'axes.edgecolor': BASELINE,
    'axes.facecolor': SURFACE,
    'figure.facecolor': SURFACE,
    'grid.linewidth': 0.5,
    'grid.color': GRID,
    'grid.alpha': 1.0,
    'xtick.major.width': 0.5,
    'ytick.major.width': 0.5,
    'xtick.major.size': 2.5,
    'ytick.major.size': 2.5,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'axes.labelcolor': INK2,
    'text.color': INK,
    'legend.frameon': False,
    'legend.fontsize': 6.5,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': SURFACE,
}

def apply_style():
    plt.rcParams.update(RC)

def panel_label(ax, letter, x=-0.18, y=1.05):
    ax.text(x, y, letter, transform=ax.transAxes,
            fontsize=9, fontweight='bold', color=INK, va='top', ha='left')

def footnote(fig, text):
    fig.text(0.01, -0.02, text, fontsize=5.5, color=MUTED,
             ha='left', va='top', wrap=True)

def save(fig, path):
    fig.savefig(path + '.png', dpi=300, bbox_inches='tight')
    fig.savefig(path + '.pdf', bbox_inches='tight')
    print(f'Saved {path}.png')


# ── F3: Family comparison ──────────────────────────────────────────────────────

def plot_f3(df, outpath):
    """Strip + box by scenario family. 3 metrics. S4 extreme annotated."""
    apply_style()

    metrics = [
        ('tstt_ratio',         'TSTT ratio (disrupted / baseline)', 1.0, True),
        ('accessibility_loss', 'Accessibility loss (fraction)',     0.0, False),
        ('delay_hours_delta',  'Additional delay (h)',              0.0, False),
    ]
    families = ['S1', 'S2', 'S3', 'S4', 'S5']

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
    fig.subplots_adjust(wspace=0.38)

    for col, (metric, ylabel, ref, log_y) in enumerate(metrics):
        ax = axes[col]
        ax.set_facecolor(SURFACE)
        ax.yaxis.grid(True, zorder=0)
        ax.set_axisbelow(True)

        for xi, fam in enumerate(families):
            sub = df[df.family == fam][metric].dropna().values
            color = PALETTE[fam]

            if fam == 'S1':
                # Compact box: median, IQR, whiskers to 5-95th pct
                q5, q25, q50, q75, q95 = np.percentile(sub, [5, 25, 50, 75, 95])
                # whisker lines
                ax.plot([xi, xi], [q5, q25], color=color, lw=1.2, solid_capstyle='round', zorder=3)
                ax.plot([xi, xi], [q75, q95], color=color, lw=1.2, solid_capstyle='round', zorder=3)
                # IQR box
                box = plt.Rectangle((xi - 0.18, q25), 0.36, q75 - q25,
                                     facecolor=color, alpha=0.25, edgecolor=color,
                                     linewidth=0.8, zorder=4)
                ax.add_patch(box)
                # median
                ax.plot([xi - 0.18, xi + 0.18], [q50, q50],
                        color=color, lw=1.5, zorder=5)
            else:
                # Individual dots + connecting line (severity progression)
                ax.plot([xi] * len(sub), sub, 'o', color=color,
                        ms=4, mew=0, zorder=5, clip_on=True)
                if len(sub) > 1:
                    sub_sorted = np.sort(sub)
                    ax.plot([xi] * len(sub_sorted), sub_sorted, '-',
                            color=color, lw=0.8, alpha=0.5, zorder=4)

                # Annotate S4 outlier on TSTT ratio
                if fam == 'S4' and metric == 'tstt_ratio' and sub.max() > 5:
                    ax.annotate(f'{sub.max():.1f}×',
                                xy=(xi, min(sub[sub > 5])), xytext=(xi + 0.35, 3.0),
                                fontsize=5.5, color=PALETTE['S4'],
                                arrowprops=dict(arrowstyle='->', color=PALETTE['S4'],
                                                lw=0.6, connectionstyle='arc3,rad=-0.2'),
                                ha='left', va='center')

        # Reference line
        ax.axhline(ref, color=BASELINE, lw=0.8, ls='--', zorder=2)

        # Clip y-axis for TSTT ratio to show detail (annotate extreme)
        if metric == 'tstt_ratio':
            ax.set_ylim(0.7, 3.2)

        ax.set_xticks(range(len(families)))
        ax.set_xticklabels([FAMILY_LABELS[f].replace(' ', '\n') for f in families],
                           fontsize=6, color=INK2)
        ax.set_ylabel(ylabel, fontsize=7, color=INK2)
        panel_label(ax, 'ABC'[col])

    # Legend for S1 box
    s1_patch = mpatches.Patch(facecolor=PALETTE['S1'], alpha=0.25,
                               edgecolor=PALETTE['S1'], linewidth=0.8,
                               label='S1 IQR (n=61)')
    s1_line = mlines.Line2D([], [], color=PALETTE['S1'], lw=1.5, label='S1 median')
    dot = mlines.Line2D([], [], marker='o', color='none', markerfacecolor=INK2,
                        ms=4, label='Single scenario')
    fig.legend(handles=[s1_patch, s1_line, dot],
               loc='lower center', ncol=3, fontsize=6,
               bbox_to_anchor=(0.5, -0.12), frameon=False)

    fig.suptitle('Q2: Disruption impact by scenario family', fontsize=9,
                 fontweight='bold', color=INK, y=1.01)
    footnote(fig, 'Network: TNTP Anaheim (914 links, 38 zones). S4 extreme (cap=0.25): TSTT×17.9, clipped; annotated.')
    save(fig, outpath)
    plt.close(fig)


# ── F4: Criticality ranking ────────────────────────────────────────────────────

def plot_f4(crit_df, outpath):
    """Top-N links by TSTT increase — clean horizontal bar."""
    apply_style()
    sort_col = 'ue_tstt_increase' if 'ue_tstt_increase' in crit_df.columns else 'tstt_increase'
    top = crit_df.nlargest(15, sort_col).sort_values(sort_col)

    fig, ax = plt.subplots(figsize=(4.5, 3.8))
    ax.set_facecolor(SURFACE)

    sort_col2 = 'ue_tstt_increase' if 'ue_tstt_increase' in top.columns else 'tstt_increase'
    bars = ax.barh(range(len(top)), top[sort_col2].values,
                   color=PALETTE['S2'], height=0.55, linewidth=0)
    # value label at bar tip
    for bar, val in zip(bars, top[sort_col2].values):
        ax.text(val + top[sort_col2].max() * 0.01, bar.get_y() + bar.get_height() / 2,
                f'{val:,.0f}', va='center', ha='left', fontsize=5.5, color=INK2)

    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top['link_id'].values, fontsize=6)
    ax.set_xlabel('TSTT increase on single-link closure (veh·min)', fontsize=7, color=INK2)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title('F4: Link criticality — top 15 by TSTT impact', fontsize=8,
                 fontweight='bold', color=INK)

    footnote(fig, 'Criticality = additional TSTT when link removed individually (baseline UE flows, top 60 links screened).')
    save(fig, outpath)
    plt.close(fig)


# ── F6: Recovery curves ────────────────────────────────────────────────────────

def plot_f6(rec_df, outpath):
    """Q(t) recovery curves with shaded area and R annotated."""
    apply_style()
    scenarios = rec_df['scenario_id'].unique()
    colors = [PALETTE['S2'], PALETTE['S3'], PALETTE['S4']]

    fig, (ax_main, ax_bar) = plt.subplots(1, 2, figsize=(6.5, 2.8),
                                           gridspec_kw={'width_ratios': [2.5, 1]})
    fig.subplots_adjust(wspace=0.35)

    for sc, color in zip(scenarios, colors):
        sub = rec_df[rec_df['scenario_id'] == sc].sort_values('day')
        days = sub['day'].values
        q    = sub['q'].values
        R    = sub['resilience_index'].iloc[0]
        label = f'{sc}  (R={R:.3f})'

        ax_main.plot(days, q, 'o-', color=color, lw=1.5, ms=4, mew=0,
                     label=label, zorder=4)
        ax_main.fill_between(days, 0, q, color=color, alpha=0.08, zorder=2)

    ax_main.axhline(1.0, color=BASELINE, lw=0.8, ls='--', zorder=1)
    ax_main.set_xlabel('Days after disruption', fontsize=7, color=INK2)
    ax_main.set_ylabel('System performance Q(t)', fontsize=7, color=INK2)
    ax_main.set_ylim(0, 1.12)
    ax_main.yaxis.grid(True, zorder=0)
    ax_main.set_axisbelow(True)
    ax_main.legend(fontsize=6, loc='lower right')
    panel_label(ax_main, 'A')

    # Bar: resilience index R per scenario
    r_vals = [rec_df[rec_df['scenario_id'] == sc]['resilience_index'].iloc[0]
              for sc in scenarios]
    short  = [sc.replace('S3_r2.0km_sev1.0', 'S3').replace('S4_type1_cap0.5', 'S4')
                .replace('S2_top1', 'S2') for sc in scenarios]

    ax_bar.barh(range(len(scenarios)), r_vals, color=colors, height=0.5, linewidth=0)
    for i, (val, sc) in enumerate(zip(r_vals, short)):
        ax_bar.text(val - 0.01, i, f'{val:.3f}', va='center', ha='right',
                    fontsize=6, color='white' if val > 0.5 else INK2)
    ax_bar.set_yticks(range(len(scenarios)))
    ax_bar.set_yticklabels(short, fontsize=6.5)
    ax_bar.set_xlabel('Resilience index R', fontsize=7, color=INK2)
    ax_bar.set_xlim(0, 1.05)
    ax_bar.axvline(1.0, color=BASELINE, lw=0.8, ls='--')
    panel_label(ax_bar, 'B', x=-0.28)

    fig.suptitle('F6: Recovery curves and resilience index (90-day horizon)', fontsize=9,
                 fontweight='bold', color=INK, y=1.02)
    footnote(fig, 'R = ∫Q(t)dt / horizon. Linear recovery shape. Q(t) = served-share × baseline-mean-tt / disrupted-mean-tt.')
    save(fig, outpath)
    plt.close(fig)


# ── F8: Tornado (OAT) ─────────────────────────────────────────────────────────

def plot_f8(oat_df, outpath):
    """Tornado: swing range per parameter, 2 key outputs side by side."""
    apply_style()
    outputs = ['tstt_ratio', 'accessibility_loss']
    out_labels = {'tstt_ratio': 'TSTT ratio', 'accessibility_loss': 'Accessibility loss'}
    param_labels = {
        'demand_factor': 'Demand multiplier',
        'severity': 'Disruption severity',
        'radius_km': 'Flood radius (km)',
        'bpr_power': 'BPR power (β)',
        'bpr_alpha': 'BPR alpha (α)',
        'vot_pax_factor': 'VOT passenger (×)',
        'vot_truck_factor': 'VOT truck (×)',
        'truck_share': 'Truck share',
        'pce': 'PCE',
        'recovery_duration': 'Recovery duration (d)',
        'gap_tolerance': 'Solver gap',
    }

    # Compute swings for primary output (tstt_ratio) to set shared order
    primary = oat_df[oat_df['output'] == 'tstt_ratio']
    swings_all = primary.groupby('param')['metric_value'].agg(lambda x: x.max() - x.min())
    param_order = swings_all.sort_values(ascending=True).index.tolist()

    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.0), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    for col, out in enumerate(outputs):
        ax = axes[col]
        ax.set_facecolor(SURFACE)
        sub = oat_df[oat_df['output'] == out]
        swings = sub.groupby('param')['metric_value'].agg(lambda x: x.max() - x.min())
        swings = swings.reindex(param_order).fillna(0)

        colors = [PALETTE['S1'] if v > swings.quantile(0.6) else '#c3d9f0'
                  for v in swings.values]
        ax.barh(range(len(swings)), swings.values, color=colors, height=0.6, linewidth=0)
        ax.set_yticks(range(len(swings)))
        if col == 0:
            ax.set_yticklabels([param_labels.get(p, p) for p in swings.index], fontsize=6.5)
        else:
            ax.set_yticklabels([])
        ax.set_xlabel('Swing (max − min)', fontsize=7, color=INK2)
        ax.set_title(out_labels[out], fontsize=8, color=INK)
        ax.xaxis.grid(True, zorder=0)
        ax.set_axisbelow(True)
        panel_label(ax, 'AB'[col])

    # highlight top 2 with annotation on left panel
    top2 = swings_all.nlargest(2)
    for p in top2.index:
        idx = param_order.index(p)
        axes[0].get_children()  # just reference
        axes[0].text(swings_all[p] * 1.02, idx, '★', fontsize=7,
                     color=PALETTE['S1'], va='center')

    fig.suptitle('F8: OAT sensitivity — parameter swing', fontsize=9,
                 fontweight='bold', color=INK, y=1.02)
    footnote(fig, 'OAT: one-at-a-time sweep. Swing = range across parameter values. ★ = top 2 influential parameters.')
    save(fig, outpath)
    plt.close(fig)


# ── F10: Morris ───────────────────────────────────────────────────────────────

def plot_f10(morris_results, outpath):
    """μ* vs σ scatter for key outputs. Diagonal = σ/μ*=1 (pure interaction)."""
    apply_style()
    param_labels = {
        'demand_factor': 'Demand mult.',
        'severity': 'Severity',
        'radius_km': 'Radius (km)',
        'bpr_power': 'BPR β',
        'bpr_alpha': 'BPR α',
        'truck_share': 'Truck share',
        'pce': 'PCE',
        'gap_tolerance': 'Solver gap',
    }
    outputs = list(morris_results.keys())[:4]  # keep ≤4
    out_labels = {
        'tstt_ratio': 'TSTT ratio', 'accessibility_loss': 'Accessibility loss',
        'unmet_share': 'Unmet share', 'total_economic_cost': 'Economic cost',
        'od_exposure_p95': 'OD p95 exposure', 'mean_trip_time_ratio': 'Mean trip time',
    }

    ncols = min(len(outputs), 2)
    nrows = (len(outputs) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.4 * ncols, 3.0 * nrows))
    if len(outputs) == 1:
        axes = [[axes]]
    elif nrows == 1:
        axes = [list(axes)]
    else:
        axes = [list(row) for row in axes]
    axes_flat = [ax for row in axes for ax in row]

    for i, out in enumerate(outputs):
        ax = axes_flat[i]
        ax.set_facecolor(SURFACE)
        si = morris_results[out]
        names = si['names']
        mu  = np.array(si['mu_star'])
        sig = np.array(si['sigma'])

        ax.scatter(mu, sig, s=28, color=PALETTE['S1'], alpha=0.9,
                   edgecolors='none', zorder=4)
        for j, name in enumerate(names):
            ax.annotate(param_labels.get(name, name), (mu[j], sig[j]),
                        textcoords='offset points', xytext=(4, 2),
                        fontsize=5.5, color=INK2)

        lim = max(mu.max(), sig.max()) * 1.15 + 1e-9
        ax.plot([0, lim], [0, lim], color=BASELINE, lw=0.8, ls='--', zorder=1)
        ax.set_xlim(left=0); ax.set_ylim(bottom=0)
        ax.set_xlabel('μ* (mean absolute effect)', fontsize=7, color=INK2)
        ax.set_ylabel('σ (std — interactions)', fontsize=7, color=INK2)
        ax.set_title(out_labels.get(out, out), fontsize=8, color=INK)
        ax.yaxis.grid(True, zorder=0); ax.xaxis.grid(True, zorder=0)
        ax.set_axisbelow(True)
        panel_label(ax, 'ABCD'[i])

    for i in range(len(outputs), len(axes_flat)):
        axes_flat[i].set_visible(False)

    fig.suptitle('F10: Morris screening — importance vs interaction', fontsize=9,
                 fontweight='bold', color=INK, y=1.02)
    footnote(fig, 'Morris (1991). μ* = mean |EE|, σ = std EE. Dashed diagonal: σ = μ* (strong interaction region). n=5 trajectories, 8 params.')
    save(fig, outpath)
    plt.close(fig)


# ── F13: Numerical sensitivity ────────────────────────────────────────────────

def plot_f13(num_df, outpath):
    """Gap tolerance convergence + UE vs AON, 2 panels."""
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(6.0, 2.6))
    fig.subplots_adjust(wspace=0.4)

    # Panel A: gap sweep
    gap_df = num_df[num_df['type'] == 'gap']
    ax = axes[0]
    ax.set_facecolor(SURFACE)
    for mi, metric in enumerate(gap_df['metric'].unique()):
        sub = gap_df[gap_df['metric'] == metric].sort_values('gap')
        color = [PALETTE['S1'], PALETTE['S2'], PALETTE['S3']][mi % 3]
        ax.plot(sub['gap'].astype(float), sub['value'],
                'o-', color=color, lw=1.5, ms=4, mew=0, label=metric)
    ax.set_xscale('log')
    ax.invert_xaxis()
    ax.set_xlabel('Solver gap tolerance (tighter →)', fontsize=7, color=INK2)
    ax.set_ylabel('Metric value', fontsize=7, color=INK2)
    ax.set_title('Gap tolerance sensitivity', fontsize=8, color=INK)
    ax.yaxis.grid(True, zorder=0); ax.set_axisbelow(True)
    ax.legend(fontsize=6)
    panel_label(axes[0], 'A')

    # Panel B: UE vs AON bar
    model_df = num_df[num_df['type'] == 'model']
    ax2 = axes[1]
    ax2.set_facecolor(SURFACE)
    if not model_df.empty:
        pivot = model_df.pivot_table(index='metric', columns='model', values='value')
        x = np.arange(len(pivot))
        w = 0.35
        cols = [PALETTE['S1'], PALETTE['S2']]
        for j, (col_name, color) in enumerate(zip(pivot.columns, cols)):
            ax2.bar(x + j * w, pivot[col_name], width=w, color=color,
                    alpha=0.9, linewidth=0, label=col_name)
        ax2.set_xticks(x + w / 2)
        ax2.set_xticklabels(pivot.index, rotation=35, ha='right', fontsize=6)
        ax2.set_ylabel('Metric value', fontsize=7, color=INK2)
        ax2.set_title('UE vs AON', fontsize=8, color=INK)
        ax2.yaxis.grid(True, zorder=0); ax2.set_axisbelow(True)
        ax2.legend(fontsize=6)
    else:
        ax2.set_visible(False)
    panel_label(axes[1], 'B')

    fig.suptitle('F13: Numerical and model-form sensitivity', fontsize=9,
                 fontweight='bold', color=INK, y=1.02)
    footnote(fig, 'Gap sweep on baseline Anaheim UE. AON = all-or-nothing (1 iteration). Metric values normalized to reference.')
    save(fig, outpath)
    plt.close(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    base = os.path.dirname(os.path.dirname(__file__))
    q2 = os.path.join(base, 'outputs', 'q2')
    q3 = os.path.join(base, 'outputs', 'q3')

    print('Loading data...')
    metrics   = pd.read_parquet(os.path.join(q2, 'metrics.parquet'))
    crit      = pd.read_parquet(os.path.join(q2, 'criticality.parquet'))
    recovery  = pd.read_parquet(os.path.join(q2, 'recovery.parquet'))
    oat       = pd.read_parquet(os.path.join(q3, 'oat_results.parquet'))
    num_sens  = pd.read_parquet(os.path.join(q3, 'numerical_sensitivity.parquet'))
    with open(os.path.join(q3, 'morris_results.json')) as f:
        morris = json.load(f)

    print('F3...')
    plot_f3(metrics, os.path.join(q2, 'F3_family_comparison'))

    print('F4...')
    plot_f4(crit, os.path.join(q2, 'F4_criticality'))

    print('F6...')
    plot_f6(recovery, os.path.join(q2, 'F6_recovery'))

    print('F8...')
    plot_f8(oat, os.path.join(q3, 'F8_tornado'))

    print('F10...')
    plot_f10(morris, os.path.join(q3, 'F10_morris'))

    print('F13...')
    plot_f13(num_sens, os.path.join(q3, 'F13_numerical'))

    print('Done.')

if __name__ == '__main__':
    main()
