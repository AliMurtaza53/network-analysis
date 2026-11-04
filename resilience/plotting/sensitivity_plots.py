"""Sensitivity figures: F8 tornado, F9 2D heatmaps, F10 Morris, F11 rank stability, F12 violin, F13 numerical."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
from resilience.plotting.style import add_panel_labels, add_footnote, save_figure

PLACEHOLDER_NOTE = "PLACEHOLDER: synthetic/model outputs — confirm parameters with Haider before publication"
PARAM_LABELS = {
    'demand_factor': 'Demand multiplier',
    'severity': 'Disruption severity',
    'radius_km': 'Footprint radius (km)',
    'bpr_alpha': 'BPR alpha (B)',
    'bpr_power': 'BPR power',
    'truck_share': 'Truck share',
    'pce': 'PCE',
    'vot_pax_factor': 'VOT passenger (×)',
    'vot_truck_factor': 'VOT truck (×)',
    'recovery_duration': 'Recovery duration (days)',
    'gap_tolerance': 'Solver gap tolerance',
}
OUTPUT_LABELS = {
    'tstt_ratio': 'TSTT ratio',
    'mean_trip_time_ratio': 'Mean trip time ratio',
    'unmet_share': 'Unmet share',
    'od_exposure_p95': 'OD p95 exposure',
    'accessibility_loss': 'Accessibility loss',
    'total_economic_cost': 'Economic cost (USD)',
}


# ------------------------------------------------------------------
# F8: Tornado plot (OAT swing)
# ------------------------------------------------------------------

def plot_tornado(oat_df: pd.DataFrame, output_path: str):
    """Tornado: swing range per parameter per output metric."""
    outputs = oat_df['output'].unique()
    n = len(outputs)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 6))
    if n == 1:
        axes = [axes]

    for ax, out in zip(axes, outputs):
        sub = oat_df[oat_df['output'] == out]
        swings = sub.groupby('param')['metric_value'].agg(lambda x: x.max() - x.min())
        swings = swings.sort_values(ascending=True)

        ax.barh(range(len(swings)), swings.values, color='#56B4E9', alpha=0.85)
        ax.set_yticks(range(len(swings)))
        ax.set_yticklabels([PARAM_LABELS.get(p, p) for p in swings.index], fontsize=8)
        ax.set_xlabel('Swing (max - min)', fontsize=8)
        ax.set_title(OUTPUT_LABELS.get(out, out), fontsize=9)

    add_panel_labels(axes)
    fig.suptitle('F8: OAT sensitivity — parameter swing', fontsize=11, fontweight='bold')
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F8: {output_path}.png")


# ------------------------------------------------------------------
# F9: 2D heatmaps (demand × severity)
# ------------------------------------------------------------------

def plot_2d_heatmaps(grid_df: pd.DataFrame, output_path: str):
    """2D heatmaps: demand factor vs severity for TSTT ratio and unmet share."""
    metrics_to_plot = [
        ('tstt_ratio', 'TSTT ratio'),
        ('unmet_share', 'Unmet demand share'),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    for ax, (metric, label) in zip(axes, metrics_to_plot):
        pivot = grid_df.pivot_table(index='demand_factor', columns='severity',
                                    values=metric, aggfunc='mean')
        im = ax.imshow(pivot.values, cmap='YlOrRd', aspect='auto',
                       extent=[pivot.columns.min(), pivot.columns.max(),
                                pivot.index.min(), pivot.index.max()],
                       origin='lower')
        ax.set_xlabel('Disruption severity', fontsize=9)
        ax.set_ylabel('Demand factor', fontsize=9)
        ax.set_title(label, fontsize=10)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        # Contour labels
        try:
            cs = ax.contour(pivot.columns, pivot.index, pivot.values,
                            colors='white', linewidths=0.6, alpha=0.5)
            ax.clabel(cs, fontsize=7, fmt='%.2f')
        except Exception:
            pass

    add_panel_labels(axes)
    fig.suptitle('F9: Demand × severity interaction', fontsize=11, fontweight='bold')
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F9: {output_path}.png")


# ------------------------------------------------------------------
# F10: Morris mu* vs sigma scatter
# ------------------------------------------------------------------

def plot_morris_scatter(morris_results: dict, output_path: str):
    """Scatter of mu_star vs sigma for each output."""
    outputs = list(morris_results.keys())
    n = len(outputs)
    if n == 0:
        print("F10: no Morris results to plot.")
        return

    ncols = min(n, 3)
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows))
    if n == 1:
        axes = [[axes]]
    axes_flat = np.array(axes).flatten() if n > 1 else [axes]

    for i, out in enumerate(outputs):
        ax = axes_flat[i]
        si = morris_results[out]
        names = si['names']
        mu = np.array(si['mu_star'])
        sigma = np.array(si['sigma'])

        ax.scatter(mu, sigma, s=60, color='#009E73', alpha=0.8)
        for j, name in enumerate(names):
            ax.annotate(PARAM_LABELS.get(name, name), (mu[j], sigma[j]),
                        textcoords='offset points', xytext=(4, 4), fontsize=7)

        # Reference lines: mu*=sigma (interaction indicator)
        lim = max(mu.max(), sigma.max()) * 1.1 if len(mu) > 0 else 1.0
        ax.plot([0, lim], [0, lim], 'k--', linewidth=0.6, alpha=0.4)
        ax.set_xlabel('μ* (importance)', fontsize=8)
        ax.set_ylabel('σ (interactions)', fontsize=8)
        ax.set_title(OUTPUT_LABELS.get(out, out), fontsize=9)

    for i in range(len(outputs), len(axes_flat)):
        axes_flat[i].set_visible(False)

    fig.suptitle('F10: Morris sensitivity — μ* vs σ', fontsize=11, fontweight='bold')
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F10: {output_path}.png")


# ------------------------------------------------------------------
# F11: Rank stability heatmap
# ------------------------------------------------------------------

def plot_rank_stability(rank_tau_df: pd.DataFrame, output_path: str):
    """Heatmap of Kendall tau of scenario ranking across parameter perturbations."""
    if rank_tau_df.empty:
        print("F11: no rank stability data.")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    if 'output' in rank_tau_df.columns:
        pivot = rank_tau_df.set_index('output')
    elif 'param' in rank_tau_df.columns:
        pivot = rank_tau_df.set_index('param').T
    else:
        pivot = rank_tau_df
    vals = pivot.select_dtypes(include='number').values.astype(float)
    pivot = pivot.select_dtypes(include='number')
    im = ax.imshow(vals, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(vals.shape[1]))
    ax.set_yticks(range(vals.shape[0]))
    ax.set_xticklabels(pivot.columns, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(pivot.index, fontsize=8)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label('Swing (max-min)')
    ax.set_title('F11: Parameter swing by output', fontsize=10)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F11: {output_path}.png")


# ------------------------------------------------------------------
# F12: Violin of output range across sweep
# ------------------------------------------------------------------

def plot_output_range(oat_df: pd.DataFrame, output_path: str):
    """Violin/box plot of metric value range per scenario family across OAT sweep."""
    fig, axes = plt.subplots(1, len(oat_df['output'].unique()),
                             figsize=(4 * len(oat_df['output'].unique()), 5))
    if len(oat_df['output'].unique()) == 1:
        axes = [axes]

    for ax, out in zip(axes, oat_df['output'].unique()):
        sub = oat_df[oat_df['output'] == out]
        data_by_param = [sub[sub.param == p]['metric_value'].dropna().values
                         for p in sub['param'].unique()]
        labels = [PARAM_LABELS.get(p, p) for p in sub['param'].unique()]

        parts = ax.violinplot(data_by_param, showmedians=True)
        for pc in parts['bodies']:
            pc.set_alpha(0.7)
        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
        ax.set_ylabel(OUTPUT_LABELS.get(out, out), fontsize=8)
        ax.set_title(OUTPUT_LABELS.get(out, out), fontsize=9)

    fig.suptitle('F12: Output range across OAT parameter sweep', fontsize=11)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F12: {output_path}.png")


# ------------------------------------------------------------------
# F13: Numerical sensitivity (gap tolerance + UE vs AON)
# ------------------------------------------------------------------

def plot_numerical_sensitivity(numerical_df: pd.DataFrame, output_path: str):
    """Bar chart: metric value at different gap tolerances and UE vs AON."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    # Gap tolerance panel
    gap_df = numerical_df[numerical_df['type'] == 'gap'] if 'type' in numerical_df.columns else pd.DataFrame()
    if not gap_df.empty:
        ax = axes[0]
        for metric in gap_df['metric'].unique():
            sub = gap_df[gap_df['metric'] == metric]
            ax.plot(sub['gap'].astype(float), sub['value'], marker='o', label=metric)
        ax.set_xscale('log')
        ax.set_xlabel('Solver gap tolerance')
        ax.set_ylabel('Metric value')
        ax.set_title('Numerical sensitivity (gap tolerance)', fontsize=10)
        ax.legend(fontsize=7)
    else:
        axes[0].set_visible(False)

    # UE vs AON panel
    model_df = numerical_df[numerical_df['type'] == 'model'] if 'type' in numerical_df.columns else pd.DataFrame()
    if not model_df.empty:
        ax = axes[1]
        pivot = model_df.pivot_table(index='metric', columns='model', values='value')
        x = np.arange(len(pivot))
        w = 0.35
        for j, col in enumerate(pivot.columns):
            ax.bar(x + j * w, pivot[col], width=w, label=col, alpha=0.8)
        ax.set_xticks(x + w / 2)
        ax.set_xticklabels(pivot.index, rotation=45, ha='right', fontsize=8)
        ax.set_title('Model form: UE vs AON', fontsize=10)
        ax.legend(fontsize=8)
    else:
        axes[1].set_visible(False)

    add_panel_labels(axes)
    fig.suptitle('F13: Numerical and model form sensitivity', fontsize=11)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F13: {output_path}.png")
