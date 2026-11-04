"""Global style: palette, rcParams, and helpers. One edit changes everything."""
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

# ------------------------------------------------------------------
# Palette — one color per scenario family, colorblind-safe (Okabe-Ito)
# ------------------------------------------------------------------
FAMILY_COLORS = {
    'S0': '#999999',  # grey — baseline
    'S1': '#56B4E9',  # sky blue — random closures
    'S2': '#E69F00',  # orange — targeted
    'S3': '#009E73',  # teal — spatial footprint
    'S4': '#CC79A7',  # pink — corridor
    'S5': '#D55E00',  # vermillion — demand surge
}

FAMILY_LABELS = {
    'S0': 'Baseline',
    'S1': 'Random closure',
    'S2': 'Targeted closure',
    'S3': 'Spatial footprint',
    'S4': 'Corridor loss',
    'S5': 'Demand surge',
}

# Diverging colormap for delta flow maps
DIVERGING_CMAP = 'RdBu_r'
# Sequential colormap for V/C
SEQUENTIAL_CMAP = 'YlOrRd'


def scenario_color(family: str) -> str:
    return FAMILY_COLORS.get(family, '#333333')


# ------------------------------------------------------------------
# rcParams — applied once at import
# ------------------------------------------------------------------

def apply_style():
    mpl.rcParams.update({
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'font.family': 'sans-serif',
        'font.size': 9,
        'axes.titlesize': 10,
        'axes.labelsize': 9,
        'legend.fontsize': 8,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'axes.axisbelow': True,
        'figure.constrained_layout.use': True,
    })


apply_style()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def add_panel_labels(axes, start='a'):
    """Add (a), (b), ... labels to a list of axes."""
    for i, ax in enumerate(axes):
        label = chr(ord(start) + i)
        ax.text(-0.12, 1.05, f'({label})', transform=ax.transAxes,
                fontsize=10, fontweight='bold', va='top')


def add_footnote(fig, text: str):
    fig.text(0.01, 0.01, text, fontsize=7, color='#555555',
             transform=fig.transFigure, va='bottom')


def save_figure(fig, path_stem: str):
    """Save as both PNG (300 dpi) and PDF."""
    fig.savefig(path_stem + '.png', dpi=300, bbox_inches='tight')
    fig.savefig(path_stem + '.pdf', bbox_inches='tight')
