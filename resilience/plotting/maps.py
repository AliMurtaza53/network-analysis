"""Map figures: baseline flow map (F1) and delta flow maps (F2)."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib
_get_cmap = matplotlib.colormaps.get_cmap if hasattr(matplotlib, 'colormaps') else cm.get_cmap
import geopandas as gpd
import pandas as pd
from resilience.plotting.style import (
    DIVERGING_CMAP, SEQUENTIAL_CMAP, scenario_color, add_footnote, save_figure
)

PLACEHOLDER_NOTE = "PLACEHOLDER: synthetic/model outputs — confirm parameters with Haider before publication"


def _add_north_arrow(ax, x=0.95, y=0.95):
    ax.annotate('N', xy=(x, y), xytext=(x, y - 0.07),
                arrowprops=dict(facecolor='black', width=2, headwidth=6),
                ha='center', fontsize=9, fontweight='bold',
                xycoords='axes fraction', textcoords='axes fraction')


def _add_scalebar(ax, gdf_metric, length_km=5):
    """Rough scale bar in metres assuming metric CRS."""
    bounds = gdf_metric.total_bounds  # minx miny maxx maxy
    xspan = bounds[2] - bounds[0]
    bar_len = length_km * 1000  # metres
    x0 = bounds[0] + 0.05 * xspan
    y0 = bounds[1] + 0.03 * (bounds[3] - bounds[1])
    ax.plot([x0, x0 + bar_len], [y0, y0], 'k-', lw=3, transform=ax.transData)
    ax.text(x0 + bar_len / 2, y0 + 200, f'{length_km} km', ha='center',
            fontsize=7, transform=ax.transData)


def plot_baseline_map(link_gdf: gpd.GeoDataFrame, crs_metric: str,
                      output_path: str):
    """F1: baseline map — line width = flow, color = V/C."""
    if link_gdf.crs is None or link_gdf.geometry.isna().all():
        print("F1: no geometry available, skipping map.")
        return

    gdf = link_gdf.to_crs(crs_metric).dropna(subset=['geometry'])
    flows = gdf['flow'].fillna(0)
    vc = gdf['vc'].fillna(0)

    # Normalise line widths to [0.3, 4] pixels
    fmax = flows.max()
    if fmax > 0:
        lw = 0.3 + 3.7 * flows / fmax
    else:
        lw = pd.Series([1.0] * len(gdf))

    fig, ax = plt.subplots(figsize=(8, 7))
    cmap = _get_cmap(SEQUENTIAL_CMAP)
    norm = plt.Normalize(vmin=0, vmax=min(vc.max(), 2.0))

    for idx, row in gdf.iterrows():
        color = cmap(norm(row['vc']))
        ax.plot(*row.geometry.xy, color=color, linewidth=float(lw[idx]), alpha=0.8)

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Volume/Capacity ratio')

    _add_north_arrow(ax)
    _add_scalebar(ax, gdf)
    ax.set_axis_off()
    ax.set_title('Anaheim baseline — link flows and V/C', fontsize=11)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F1: {output_path}.png")


def plot_delta_flow_maps(link_gdf: gpd.GeoDataFrame,
                         scenario_results: list,
                         scenario_labels: list,
                         baseline_flows: dict,
                         crs_metric: str,
                         output_path: str,
                         n_panels: int = 4):
    """F2: delta flow maps — four key scenarios in a 2x2 grid."""
    if link_gdf.crs is None or link_gdf.geometry.isna().all():
        print("F2: no geometry, skipping.")
        return

    gdf = link_gdf.to_crs(crs_metric).dropna(subset=['geometry'])
    link_ids = gdf['link_id'].tolist()

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    axes = axes.flatten()

    n = min(n_panels, len(scenario_results))
    for i in range(n):
        ax = axes[i]
        result = scenario_results[i]
        lr = result['link_results']

        deltas = []
        for lid in link_ids:
            base_flow = baseline_flows.get(lid, 0)
            scen_flow = lr[lid]['flow'] if lid in lr else 0
            deltas.append(scen_flow - base_flow)

        d_arr = np.array(deltas)
        vlim = max(abs(d_arr).max(), 1.0)
        norm = plt.Normalize(vmin=-vlim, vmax=vlim)
        cmap = _get_cmap(DIVERGING_CMAP)

        for j, (idx, row) in enumerate(gdf.iterrows()):
            lid = row['link_id']
            is_affected = lid in result.get('affected_links', [])
            color = cmap(norm(deltas[j]))
            lw = 2.5 if is_affected else 0.8
            ax.plot(*row.geometry.xy, color=color, linewidth=lw, alpha=0.85)

        sm = cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
        cbar.set_label('Δ flow (veh/h)')

        ax.set_axis_off()
        ax.set_title(scenario_labels[i], fontsize=9)
        _add_north_arrow(ax)

    for i in range(n, 4):
        axes[i].set_visible(False)

    fig.suptitle('Delta flow maps vs baseline', fontsize=12, fontweight='bold')
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved F2: {output_path}.png")


def plot_criticality_map(link_gdf: gpd.GeoDataFrame,
                         criticality_scores: dict,
                         top_links: list,
                         crs_metric: str,
                         output_path: str):
    """Part of F4: criticality map."""
    if link_gdf.crs is None or link_gdf.geometry.isna().all():
        print("F4 map: no geometry, skipping.")
        return

    gdf = link_gdf.to_crs(crs_metric).dropna(subset=['geometry'])

    scores = np.array([criticality_scores.get(lid, 0) for lid in gdf['link_id']])
    smax = scores.max() if scores.max() > 0 else 1.0
    cmap = _get_cmap('hot_r')
    norm = plt.Normalize(vmin=0, vmax=smax)

    fig, ax = plt.subplots(figsize=(8, 7))
    for idx, row in gdf.iterrows():
        lid = row['link_id']
        score = criticality_scores.get(lid, 0)
        is_top = lid in top_links
        color = cmap(norm(score))
        lw = 3.0 if is_top else 0.6
        ax.plot(*row.geometry.xy, color=color, linewidth=lw, alpha=0.9)

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('TSTT increase on closure')

    ax.set_axis_off()
    ax.set_title('Link criticality (top links highlighted)', fontsize=11)
    _add_north_arrow(ax)
    _add_scalebar(ax, gdf)
    add_footnote(fig, PLACEHOLDER_NOTE)
    save_figure(fig, output_path)
    plt.close(fig)
    print(f"Saved criticality map: {output_path}.png")
