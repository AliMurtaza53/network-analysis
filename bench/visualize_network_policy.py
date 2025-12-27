"""Visualize network with policy impact: flow/cost changes on links.

Reads the policy comparison CSV output from run_netanalysis_on.py and renders 
the network graph, coloring/sizing links by flow or cost changes between 
baseline and policy scenarios.

Run from project root:
    python bench\visualize_network_policy.py CITY_NAME
    
Example:
    python bench\visualize_network_policy.py SiouxFalls
"""
import os
import sys
import csv
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

if len(sys.argv) < 2:
    print("Usage: python bench/visualize_network_policy.py CITY_NAME")
    sys.exit(1)

city = sys.argv[1]
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
outdir = os.path.join(project_root, 'outputs')

policy_csv = os.path.join(outdir, f'{city}_policy_comparison.csv')

if not os.path.exists(policy_csv):
    print(f"Error: {policy_csv} not found. Run run_netanalysis_on.py first.")
    sys.exit(1)

# Read policy comparison data from run_netanalysis_on.py output
# Expected columns: links, cap, newcap, fft, newfft, costs, newcosts, flows, newflows
links_data = {}
with open(policy_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        link = row['links']
        baseline_flow = float(row['flows'])
        policy_flow = float(row['newflows'])
        baseline_cost = float(row['costs'])
        policy_cost = float(row['newcosts'])
        baseline_cap = float(row['cap'])
        policy_cap = float(row['newcap'])
        
        links_data[link] = {
            'baseline_flow': baseline_flow,
            'policy_flow': policy_flow,
            'baseline_cost': baseline_cost,
            'policy_cost': policy_cost,
            'baseline_cap': baseline_cap,
            'policy_cap': policy_cap,
            'flow_change': policy_flow - baseline_flow,
            'cost_change': policy_cost - baseline_cost,
        }

# Build directed graph from links
G = nx.DiGraph()
for link_str in links_data.keys():
    # Parse link format: "(tail,head)"
    link_str = link_str.strip()
    if link_str.startswith('(') and link_str.endswith(')'):
        inner = link_str[1:-1].split(',')
        if len(inner) == 2:
            tail, head = int(inner[0].strip()), int(inner[1].strip())
            G.add_edge(tail, head, link=link_str)

print(f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} links")

# Use spring layout for visualization
print("Computing layout...")
pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

# Create two subplots: flow change and cost change
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

for ax, metric in [(ax1, 'flow_change'), (ax2, 'cost_change')]:
    ax.set_title(f'Network: {metric.replace("_", " ").title()}', fontsize=14, fontweight='bold')
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=300, ax=ax)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, font_size=8, ax=ax)
    
    # Color and width edges by metric
    edge_values = []
    edge_colors = []
    edge_widths = []
    
    for u, v in G.edges():
        edge_data = G[u][v]
        link = edge_data['link']
        value = links_data[link][metric]
        edge_values.append(value)
        
        # Color: red for increase, blue for decrease
        if value > 0:
            edge_colors.append('red')
        elif value < 0:
            edge_colors.append('blue')
        else:
            edge_colors.append('gray')
        
        # Width proportional to absolute change
        edge_widths.append(0.5 + 3.0 * abs(value) / (max([abs(v) for v in edge_values]) + 1e-6))
    
    # Draw edges
    for (u, v), color, width in zip(G.edges(), edge_colors, edge_widths):
        nx.draw_networkx_edges(G, pos, [(u, v)], edge_color=color, width=width, ax=ax, 
                               arrowsize=15, arrowstyle='-|>', connectionstyle='arc3,rad=0.1')
    
    ax.axis('off')
    
    # Add legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', lw=2, label='Increase'),
        Line2D([0], [0], color='blue', lw=2, label='Decrease'),
        Line2D([0], [0], color='gray', lw=1, label='No change'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

plt.tight_layout()
out_png = os.path.join(outdir, f'{city}_network_policy_visualization.png')
os.makedirs(outdir, exist_ok=True)
plt.savefig(out_png, dpi=150, bbox_inches='tight')
plt.close()

print(f"Network visualization saved to {out_png}")

# Generate a separate plot focusing on top-flow links
fig, ax = plt.subplots(figsize=(12, 9))

# Subgraph of top links by baseline flow
top_n = 20
top_links = sorted(links_data.items(), key=lambda x: x[1]['baseline_flow'], reverse=True)[:top_n]
top_link_ids = [l[0] for l in top_links]

# Build subgraph
G_top = nx.DiGraph()
for link in top_link_ids:
    link_str = link.strip()
    if link_str.startswith('(') and link_str.endswith(')'):
        inner = link_str[1:-1].split(',')
        if len(inner) == 2:
            tail, head = int(inner[0].strip()), int(inner[1].strip())
            G_top.add_edge(tail, head, link=link_str)

if G_top.number_of_nodes() > 0:
    pos_top = nx.spring_layout(G_top, k=2, iterations=50, seed=42)
    
    ax.set_title(f'Top {top_n} Links by Baseline Flow: Flow Change', fontsize=14, fontweight='bold')
    
    # Draw nodes
    nx.draw_networkx_nodes(G_top, pos_top, node_color='lightgreen', node_size=500, ax=ax)
    nx.draw_networkx_labels(G_top, pos_top, font_size=9, ax=ax)
    
    # Color edges by flow change, width by absolute value
    edge_colors_top = []
    edge_widths_top = []
    max_change = max([abs(links_data[link_id]['flow_change']) for link_id in top_link_ids] + [1e-6])
    
    for u, v in G_top.edges():
        link = G_top[u][v]['link']
        flow_change = links_data[link]['flow_change']
        
        if flow_change > 0:
            edge_colors_top.append('red')
        elif flow_change < 0:
            edge_colors_top.append('blue')
        else:
            edge_colors_top.append('gray')
        
        edge_widths_top.append(0.5 + 4.0 * abs(flow_change) / max_change)
    
    for (u, v), color, width in zip(G_top.edges(), edge_colors_top, edge_widths_top):
        nx.draw_networkx_edges(G_top, pos_top, [(u, v)], edge_color=color, width=width, ax=ax,
                               arrowsize=20, arrowstyle='-|>', connectionstyle='arc3,rad=0.1')
    
    ax.axis('off')
    
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', lw=2, label='Flow increase'),
        Line2D([0], [0], color='blue', lw=2, label='Flow decrease'),
        Line2D([0], [0], color='gray', lw=1, label='No change'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

plt.tight_layout()
out_top_png = os.path.join(outdir, f'{city}_network_top_links.png')
plt.savefig(out_top_png, dpi=150, bbox_inches='tight')
plt.close()

print(f"Top links visualization saved to {out_top_png}")
