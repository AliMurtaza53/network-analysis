"""Panel figures: F3 Q2 main panel, F4 criticality, F5 ECDF, F6 recovery, F7 correlation."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import pandas as pd
from resilience.plotting.style import (
    scenario_color, FAMILY_LABELS, add_panel_labels, add_footnote, save_figure,
    SEQUENTIAL_CMAP
)
from scipy.stats import spearmanr

PLACEHOLDER_NOTE = "PLACEHOLDER: synthetic/model outputs — confirm parameters with Haider before publication"


# ------------------------------------------------------------------
# F3: main Q2 panel
# ------------------------------------------------------------------

def plot_q2_panel(metrics_df: pd.DataFrame, output_path: str):
    """3×3 grid: one panel per metric, scenarios on x-axis, baseline reference line.

    metrics_df columns: scenario_id, family, metric, value
    """
    PANEL_METRICS = [
        ('tstt_ratio', 'TSTT ratio (vs baseline)'),
        ('mean_trip_time_ratio', 'Mean trip time ratio'),
        ('delay_hours_delta', 'Extra delay (hours)'),
        ('unmet_share', 'Unmet demand share'),
        ('accessibility_loss', 'Accessibility loss'),
        ('od_exposure_p95', '95th pct OD time increase (min)'),
        ('total_economic_cost', 'Economic cost (USD)'),
        ('truck_delay_hours', 'Truck delay (hours)'),
        ('max_vc', 'Max V/C ratio'),
    ]

    fig, axes = plt.subplots(3, 3, figsize=(14, 11))
    axes = axes.flatten()

    pivot = metrics_df.pivot_table(index='scenario_id', columns='metric',
                                   values='value', aggfunc='mean')

    # Sort scenarios by family then id
    scenario_meta = metrics_df[['scenario_id', 'family']].drop_duplicates()
    scenario_order = scenario_meta.sort_values(['family', 'scenario_id'])['scenario_id'].tolist()

    for i, (metric, label) in enumerate(PANEL_METRICS):
        ax = axes[i]
        if metric not in pivot.columns:
            ax.set_visible(False)
            continue

        y_vals = []
        x_labels = []
        colors = []

        for sc_id in scenario_order:
            if sc_id not in pivot.index:
                continue
            val = pivot.loc[sc_id, metric]
            if pd.isna(val):
                continue
            family = scenario_meta[scenario_meta.scenario_id == sc_id]['family'].values[0]
            y_vals.append(val)
            x_labels.append(sc_id)
            colors.append(scenario_color(family))

        x_pos = np.arange(len(y_vals))
        ax.bar(x_pos, y_vals, color=colors, alpha=0.8, edgecolor='none')

        # Baseline reference line
        if metric in ['tstt_ratio', 'mean_trip_time_ratio']:
            ax.axhline(1.0, color='black', linestyle='--', linewidth=0.8, alpha=0.6)
        elif metric in ['unmet_share', 'accessibility_loss', 'delay_hours_delta',
                        'total_economic_cost', 'truck_delay_hours', 'od_exposure_p95']:
            ax.axhline(0.0, color='black', linestyle='--', linewidth=0.8, alpha=0.6)

        ax.set_ylabel(label, fontsize=8)
        ax.set_xticks([])
        ax.set_title(label, fontsize=9)

    # Legend
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=c, label=FAMILY_LABELS.get(f, f))
               for f, c in [('S0', scenario_color('S0')), ('S1', scenario_color('S1')),
                             ('S2', scenario_color('S2')), ('S3', scenario_color('S3')),
                             ('S4', scenario_color('S4')), ('S5', scenario_color('S5'))]]
    fig.legend(handles=handles, loc='lower center', ncol=6, fontsize=8,
               bbox_to_anchor=(0.5, -0.02))

    add_panel_labels(axes)
    fig.suptitle('Q2: Network performance across disruption scenarios', fontsize=12,
                 fontweight='bold')
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F3: {output_path}.png")


# ------------------------------------------------------------------
# F4: criticality bar chart + proxy scatter
# ------------------------------------------------------------------

def plot_criticality_panel(criticality_ue: dict, proxy_scores: dict,
                           output_path: str):
    """Bar chart of top critical links + UE vs proxy scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Sort by UE TSTT increase
    sorted_links = sorted(criticality_ue.keys(),
                          key=lambda x: criticality_ue[x], reverse=True)[:20]

    # Bar chart
    ax = axes[0]
    scores = [criticality_ue[lid] for lid in sorted_links]
    y_pos = np.arange(len(sorted_links))
    ax.barh(y_pos, scores, color='#E69F00', alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([lid for lid in sorted_links], fontsize=7)
    ax.set_xlabel('TSTT increase on closure')
    ax.set_title('Top critical links (UE)', fontsize=10)
    ax.invert_yaxis()

    # Scatter: UE vs proxy
    ax = axes[1]
    common = [lid for lid in sorted_links if lid in proxy_scores]
    if common:
        x = [proxy_scores[lid] for lid in common]
        y = [criticality_ue[lid] for lid in common]
        ax.scatter(x, y, color='#56B4E9', alpha=0.7, s=50)
        # Spearman
        from scipy.stats import spearmanr
        rho, pval = spearmanr(x, y)
        ax.set_title(f'UE vs proxy (Spearman r={rho:.2f}, p={pval:.3f})', fontsize=9)
        ax.set_xlabel('Proxy score (baseline flow)')
        ax.set_ylabel('UE TSTT increase')

    add_panel_labels(axes)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F4: {output_path}.png")


# ------------------------------------------------------------------
# F5: ECDF of OD time change
# ------------------------------------------------------------------

def plot_ecdf_od_time(od_delta_data: dict, output_path: str):
    """ECDF of OD shortest-path time change, one curve per scenario family."""
    fig, ax = plt.subplots(figsize=(8, 5))

    for sc_id, (family, deltas) in od_delta_data.items():
        if not deltas:
            continue
        d = np.sort(deltas)
        ecdf = np.arange(1, len(d) + 1) / len(d)
        ax.step(d, ecdf, where='post', color=scenario_color(family),
                alpha=0.6, linewidth=1.2, label=sc_id)

    ax.axvline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    ax.set_xlabel('OD travel time change vs baseline (min)', fontsize=9)
    ax.set_ylabel('ECDF', fontsize=9)
    ax.set_title('Distribution of OD time changes', fontsize=10)
    ax.set_ylim(0, 1.05)

    # Dedupe legend by family
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=scenario_color(f), linewidth=2,
                      label=FAMILY_LABELS.get(f, f))
               for f in ['S1', 'S2', 'S3', 'S4', 'S5']]
    ax.legend(handles=handles, fontsize=8)

    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F5: {output_path}.png")


# ------------------------------------------------------------------
# F6: Recovery curves Q(t)
# ------------------------------------------------------------------

def plot_recovery_curves(recovery_results: dict, output_path: str):
    """Q(t) curves per scenario with loss area shaded + resilience index bar."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ax = axes[0]
    for sc_id, (family, rec) in recovery_results.items():
        days = rec['days']
        q = rec['q_values']
        color = scenario_color(family)
        ax.plot(days, q, color=color, linewidth=2, label=sc_id)
        ax.fill_between(days, q, 1.0, alpha=0.08, color=color)

    ax.axhline(1.0, color='black', linestyle='--', linewidth=0.8, alpha=0.5, label='Baseline')
    ax.set_xlabel('Days after disruption', fontsize=9)
    ax.set_ylabel('Performance Q(t)', fontsize=9)
    ax.set_title('Recovery curves', fontsize=10)
    ax.set_ylim(0, 1.1)

    # Bar of resilience index R
    ax2 = axes[1]
    sc_ids = list(recovery_results.keys())
    R_vals = [recovery_results[sc_id][1]['resilience_index'] for sc_id in sc_ids]
    colors = [scenario_color(recovery_results[sc_id][0]) for sc_id in sc_ids]
    y_pos = np.arange(len(sc_ids))
    ax2.barh(y_pos, R_vals, color=colors, alpha=0.85)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(sc_ids, fontsize=8)
    ax2.axvline(1.0, color='black', linestyle='--', linewidth=0.8)
    ax2.set_xlabel('Resilience index R', fontsize=9)
    ax2.set_title('Resilience index by scenario', fontsize=10)
    ax2.invert_yaxis()

    add_panel_labels(axes)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F6: {output_path}.png")


# ------------------------------------------------------------------
# F7: Metric correlation heatmap
# ------------------------------------------------------------------

def plot_metric_correlation(metrics_df: pd.DataFrame, output_path: str):
    """Spearman correlation heatmap of metrics across scenarios."""
    pivot = metrics_df.pivot_table(index='scenario_id', columns='metric',
                                   values='value', aggfunc='mean')
    pivot = pivot.dropna(axis=1, thresh=max(2, len(pivot) // 2))

    corr = pivot.corr(method='spearman')

    fig, ax = plt.subplots(figsize=(9, 8))
    im = ax.imshow(corr.values, cmap='RdBu_r', vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04).set_label('Spearman r')
    ax.set_title('Metric correlation (Spearman) across scenarios', fontsize=10)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F7: {output_path}.png")
