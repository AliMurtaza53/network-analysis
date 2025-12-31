# Advanced Network Analysis Workflows

This guide documents how to conduct advanced network analyses using the current setup: link removal, OD demand modification, and alternative objective functions (emissions, system equilibrium).

**Table of Contents:**
1. [Link Removal Analysis](#1-link-removal-analysis)
2. [OD Demand Modification](#2-od-demand-modification)
3. [Emissions-Based Optimization](#3-emissions-based-optimization)
4. [System Equilibrium (SO) Analysis](#4-system-equilibrium-so-analysis)
5. [Spatial Analysis & Mapping](#5-spatial-analysis--mapping)
6. [Implementation Patterns](#implementation-patterns)

---

## 1. Link Removal Analysis

**Purpose:** Analyze network resilience by studying impacts when critical segments are disabled or removed.

**Use Cases:**
- Infrastructure failure/disaster analysis
- Evacuation planning (closing certain routes)
- Identifying critical network segments
- Bottleneck identification

### Implementation

Add to `policies/modifiers.py`:

```python
def remove_links(net: Network, link_ids: List[str]) -> None:
    """Disable specified links by setting capacity to zero.
    
    Args:
        net: Network object
        link_ids: List of link identifiers as strings, e.g., ['(5,9)', '(9,10)']
    
    Example:
        >>> remove_links(net, ['(5,9)', '(9,10)'])  # Block highway corridor
    """
    for link_id in link_ids:
        if link_id in net.link:
            net.link[link_id].capacity = 0
            net.link[link_id].updateCost()
        else:
            print(f"Warning: Link {link_id} not found in network")
```

### Example Experiment

Create `experiments/link_removal_siouxfalls.py`:

```python
from network import Network
from policies.modifiers import remove_links, reset_flows
import csv, os

# Define critical links to test
CRITICAL_LINKS = [
    '(5,9)', '(9,10)',      # Highway corridor north
    '(10,15)', '(15,22)'    # Highway corridor south
]

# Baseline
print('Baseline...')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
baseline_tstt = sum(l.flow * l.cost for l in net.link.values())
baseline_gap = net.relativeGap()

# Scenario: Remove critical links
print('\nRemoving critical links...')
reset_flows(net)
remove_links(net, CRITICAL_LINKS)
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
removal_tstt = sum(l.flow * l.cost for l in net.link.values())
removal_gap = net.relativeGap()

# Results
print(f'\nBaseline TSTT: {baseline_tstt:,.0f}')
print(f'After removal: {removal_tstt:,.0f}')
print(f'Impact:        +{((removal_tstt - baseline_tstt) / baseline_tstt)*100:.1f}%')

# Save detailed comparison
os.makedirs('results', exist_ok=True)
with open('results/link_removal.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['scenario', 'tstt', 'gap', 'impact_pct'])
    w.writeheader()
    w.writerow({'scenario': 'baseline', 'tstt': baseline_tstt, 'gap': baseline_gap, 
                'impact_pct': 0})
    w.writerow({'scenario': 'links_removed', 'tstt': removal_tstt, 'gap': removal_gap,
                'impact_pct': ((removal_tstt - baseline_tstt) / baseline_tstt)*100})
```

### Key Considerations

- **Capacity = 0** forces traffic to alternate routes; much stronger than modest capacity reduction
- **Convergence may be slower** if alternate routes become heavily congested
- **Identify critical OD pairs** most affected by examining flow redistribution
- Can test individual link removal vs. multiple simultaneous removals
- Results show network vulnerability and redundancy

---

## 2. OD Demand Modification

**Purpose:** Analyze network response to demand changes (growth, shifts, or targeted changes).

**Use Cases:**
- Growth scenario analysis (e.g., 20% increase over 10 years)
- Demand management studies (peak vs. off-peak)
- Targeted incentives (reduce demand on certain corridors)
- Equity analysis (impacts on different OD pairs)

### Implementation

Functions already exist in `policies/modifiers.py`:

```python
# Uniform scaling (all OD pairs grow by factor)
from policies.modifiers import scale_demand
scale_demand(net, factor=1.2)  # 20% uniform growth

# Specific OD pair modification
from policies.modifiers import scale_specific_demand
scale_specific_demand(net, [('1', '5'), ('2', '6')], factor=0.5)  # 50% reduction

# Direct modification
net.ODpair['1']['5'].demand *= 2.0  # Double specific pair
```

### Example Experiment

Create `experiments/demand_growth_siouxfalls.py`:

```python
from network import Network
from policies.modifiers import scale_demand, reset_flows
import csv, os

# Test different growth scenarios
GROWTH_RATES = [1.0, 1.1, 1.2, 1.5]  # 0%, 10%, 20%, 50% growth

os.makedirs('results', exist_ok=True)

with open('results/demand_growth.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['growth_factor', 'pct_growth', 'tstt', 'gap'])
    w.writeheader()
    
    for growth in GROWTH_RATES:
        print(f'\nGrowth factor: {growth} ({(growth-1)*100:.0f}% increase)')
        
        net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
        
        # Apply growth
        if growth > 1.0:
            scale_demand(net, factor=growth)
        
        # Solve
        net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
        tstt = sum(l.flow * l.cost for l in net.link.values())
        gap = net.relativeGap()
        
        print(f'TSTT: {tstt:,.0f}, Gap: {gap:.6f}')
        
        w.writerow({'growth_factor': growth, 'pct_growth': (growth-1)*100,
                   'tstt': tstt, 'gap': gap})

print('\nSaved: results/demand_growth.csv')
```

### Advanced: Targeted Demand Change

```python
# Target high-income commuters on specific corridors
high_value_pairs = [('1', '5'), ('5', '1'), ('10', '15'), ('15', '10')]
scale_specific_demand(net, high_value_pairs, factor=0.7)  # 30% reduction

# Simulate local population growth
local_growth = [('12', '13'), ('13', '12'), ('3', '4'), ('4', '3')]
scale_specific_demand(net, local_growth, factor=1.3)  # 30% increase
```

### Key Considerations

- **Elastic vs. inelastic demand:** Model assumes fixed demand (inelastic)
- **Non-linear growth:** TSTT doesn't grow linearly with demand (accelerates at high loads)
- **OD-specific elasticity:** Some pairs have better alternates than others
- **Can combine with capacity policies** for growth + infrastructure scenarios
- Compare convergence speeds at different demand levels (higher demand = slower)

---

## 3. Emissions-Based Optimization

**Purpose:** Incorporate environmental objectives alongside travel time minimization.

**Use Cases:**
- Green transportation planning
- Emissions pricing/carbon taxes
- Environmental impact assessment
- Policy design (which tolls best reduce emissions?)

### Implementation

Add to `policies/modifiers.py`:

```python
def apply_emission_cost(net: Network, emission_weight: float = 0.1, 
                        emission_per_flow: float = 0.001) -> None:
    """Add emissions-based cost component to link costs.
    
    Emissions typically increase with congestion. This function adds a 
    congestion-weighted term to link costs to represent environmental impact.
    
    Args:
        net: Network object
        emission_weight: Weight in [0,1] - controls importance vs. travel time
                        0.1 = emissions are 10% as important as travel time
        emission_per_flow: Emissions per unit flow per unit congestion
    
    Example:
        >>> apply_emission_cost(net, emission_weight=0.15)
        >>> net.userEquilibrium(...)  # Users now route considering emissions
    """
    for link in net.link.values():
        # Base cost is travel time
        base_cost = link.cost
        
        # Emissions cost: increases with congestion
        # congestion_level = current_flow / capacity (proxy for emissions)
        congestion_level = max(0, link.flow / link.capacity if link.capacity > 0 else 0)
        emissions_cost = congestion_level * emission_per_flow
        
        # Combined cost: time + weighted emissions
        link.cost = base_cost + emission_weight * emissions_cost
```

### Example Experiment

Create `experiments/emissions_optimization_siouxfalls.py`:

```python
from network import Network
from policies.modifiers import apply_emission_cost, reset_flows
import csv, os

# Test different emission weights
EMISSION_WEIGHTS = [0.0, 0.05, 0.1, 0.2]  # 0% to 20% of travel time importance

os.makedirs('results', exist_ok=True)

with open('results/emissions_optimization.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['emission_weight', 'tstt', 'gap', 
                                       'total_emissions_proxy'])
    w.writeheader()
    
    for weight in EMISSION_WEIGHTS:
        print(f'\nEmission weight: {weight} ({weight*100:.0f}% of travel time)')
        
        net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
        
        # Store baseline for comparison
        if weight == 0.0:
            net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
        else:
            apply_emission_cost(net, emission_weight=weight)
            net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
        
        tstt = sum(l.flow * l.cost for l in net.link.values())
        gap = net.relativeGap()
        
        # Proxy for total emissions: sum of (flow * congestion_level)
        total_emissions = 0
        for link in net.link.values():
            congestion = link.flow / link.capacity if link.capacity > 0 else 0
            total_emissions += link.flow * congestion
        
        print(f'TSTT: {tstt:,.0f}, Gap: {gap:.6f}, Emissions proxy: {total_emissions:,.0f}')
        
        w.writerow({'emission_weight': weight, 'tstt': tstt, 'gap': gap,
                   'total_emissions_proxy': total_emissions})

print('\nSaved: results/emissions_optimization.csv')
```

### Key Considerations

- **Emissions assumption:** Model assumes emissions ∝ congestion (reasonable for real networks)
- **Weight tuning critical:** 0.1 vs. 0.2 can shift routing significantly
- **Trade-off analysis:** Does reducing emissions cost in TSTT increase?
- **Iterative tuning:** Start with low weights, increase to see impacts
- **Real emissions models:** Current version is proxy; could integrate detailed vehicle emission models
- **Toll equivalent:** Emission weight roughly translates to implicit carbon tax per vehicle

---

## 4. System Equilibrium (SO) Analysis

**Purpose:** Optimize total system performance instead of individual user optimization.

**Current Challenge:** The codebase solves User Equilibrium (UE) where each driver minimizes own travel time. System Optimal (SO) minimizes total TSTT—requires different algorithm.

### Why SO Matters

- **UE is selfish:** Drivers don't account for congestion they cause others
- **SO is socially optimal:** Minimizes total system cost
- **Gap quantifies inefficiency:** UE TSTT vs. SO TSTT = Price of Anarchy
- **Tolling closes gap:** Optimal tolls can push UE toward SO

### Option 1: Iterative Toll Approximation (Practical)

Add to `policies/modifiers.py`:

```python
def iterate_toward_system_optimal(net: Network, iterations: int = 5, 
                                   toll_step: float = 0.5, 
                                   congestion_threshold: float = 1.0) -> dict:
    """Iteratively adjust tolls to approximate system optimal routing.
    
    Uses marginal cost tolling: makes drivers pay for congestion they impose.
    By increasing tolls on congested links, pushes UE solution toward SO.
    
    Args:
        net: Network object
        iterations: Number of toll adjustment iterations
        toll_step: Size of toll increment for congested links
        congestion_threshold: Ratio above which links incur toll (default 1.0 = at capacity)
    
    Returns:
        Dictionary with TSTT and congestion metrics over iterations
    """
    history = {'iteration': [], 'tstt': [], 'avg_toll': []}
    
    for i in range(iterations):
        # Solve current UE with existing tolls
        net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=2000)
        
        tstt = sum(l.flow * l.cost for l in net.link.values())
        history['iteration'].append(i)
        history['tstt'].append(tstt)
        
        # Update tolls based on congestion
        total_toll = 0
        for link in net.link.values():
            congestion_level = link.flow / link.capacity if link.capacity > 0 else 0
            
            if congestion_level > congestion_threshold:
                # Toll = marginal congestion cost
                toll_increase = toll_step * (congestion_level - congestion_threshold)
                link.toll = max(0, link.toll + toll_increase)
                link.updateCost()
                total_toll += link.toll
        
        avg_toll = total_toll / len(net.link) if len(net.link) > 0 else 0
        history['avg_toll'].append(avg_toll)
        
        print(f'Iteration {i}: TSTT={tstt:,.0f}, Avg toll={avg_toll:.2f}')
    
    return history
```

### Example Experiment

Create `experiments/system_optimal_siouxfalls.py`:

```python
from network import Network
from policies.modifiers import iterate_toward_system_optimal
import csv, os

print('Computing System Optimal via iterative tolling...')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')

history = iterate_toward_system_optimal(net, iterations=10, toll_step=1.0)

# Results
os.makedirs('results', exist_ok=True)
with open('results/system_optimal.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['iteration', 'tstt', 'avg_toll'])
    w.writeheader()
    for i in range(len(history['iteration'])):
        w.writerow({'iteration': history['iteration'][i],
                   'tstt': history['tstt'][i],
                   'avg_toll': history['avg_toll'][i]})

print('\nTSTT progression:')
for i, tstt in enumerate(history['tstt']):
    print(f'  Iteration {i}: {tstt:,.0f}')

print(f'\nTSST improvement: {((history["tstt"][0] - history["tstt"][-1]) / history["tstt"][0])*100:.1f}%')
print('Saved: results/system_optimal.csv')
```

### Option 2: Full SO Solver (Advanced)

For exact SO solution, would need convex optimization:

```python
# Pseudocode - requires external solver (scipy, CVXPY, Gurobi, etc.)
from scipy.optimize import minimize

def solve_system_optimal_exact(net: Network) -> dict:
    """Solve exact system optimal problem using convex optimization.
    
    Minimize: Σ(flow_e * cost_e(flow_e)) for all edges e
    Subject to: flow conservation constraints on all OD pairs
    
    This is a complex problem; simplified version shown here.
    """
    # Extract problem structure
    num_links = len(net.link)
    link_ids = list(net.link.keys())
    
    def objective(flows):
        """Objective: total system cost"""
        total_cost = 0
        for i, link_id in enumerate(link_ids):
            link = net.link[link_id]
            flow = flows[i]
            cost = flow * link.compute_cost(flow)  # Needs to be differentiable
            total_cost += cost
        return total_cost
    
    # This is where you'd call scipy.optimize.minimize or similar
    # Requires: flow conservation constraints, non-negativity bounds
    # Complex implementation deferred to full SO module if needed
    pass
```

### Key Considerations

- **Toll-based approach:** Practical, interpretable, matches real-world policy
- **Convergence:** Takes several iterations; may oscillate if step size too large
- **Exact SO:** Requires specialized solvers, significantly more complex
- **Marginal cost pricing theory:** Tolls represent cost drivers impose on others
- **Realism:** Most real networks use tolling imperfectly; approximate SO is practical target

---

## 5. Spatial Analysis & Mapping

**Purpose:** Add geographic awareness to network analysis—visualize results on maps, overlay hazard layers, and perform spatial disruption analysis.

**Current Limitation:** The network representation is **topological** (nodes/links with IDs) but **not spatial** (no lat/lon coordinates). To enable mapping and spatial analysis, you need to add coordinate data.

### Use Cases
- **Hazard overlay:** Identify vulnerable links in flood zones, earthquake risk areas, wildfire zones
- **Disruption analysis:** Which links fail in a 100-year flood? How does network reroute?
- **Equity mapping:** Visualize which neighborhoods experience congestion impacts
- **Visual communication:** Show policymakers where interventions have most impact
- **Evacuation planning:** Map optimal escape routes, identify bottlenecks spatially

---

### 5.1 Adding Spatial Data to Networks

#### Option A: Add Coordinates to Existing TNTP Files

The TNTP format supports optional node coordinate fields. Modify your network file to include `X_COORD` and `Y_COORD`:

**Example: `tests/SiouxFalls_net_spatial.txt`**
```
<NUMBER OF NODES> 24
<NUMBER OF LINKS> 76
<NUMBER OF ZONES> 24
<FIRST THRU NODE> 1
<END OF METADATA>

~ Node data (ID, X_COORD, Y_COORD)
1  96.662  25.376
2  96.662  41.876
3  86.662  25.376
4  76.662  25.376
...

~ Link data
~   ID    init_node  term_node  capacity  length  free_flow_time  B  power  speed_limit  toll  link_type
    1     (1,2)      1          2          25900.20064  6  6  0.15  4  1  0  ;
...
```

If coordinates don't exist, you can:
- **Find them online:** Some TNTP networks have coordinate files
- **Assign synthetic coordinates:** Place nodes on a grid for topology visualization
- **Digitize from maps:** Use QGIS to click nodes and extract lat/lon

#### Option B: Create Coordinate Mapping Separately

Store coordinates in a separate CSV file:

**`tests/SiouxFalls_coordinates.csv`**
```csv
node_id,x,y,lon,lat
1,96.662,25.376,-96.729,43.544
2,96.662,41.876,-96.729,43.554
3,86.662,25.376,-96.739,43.544
...
```

Load alongside network:
```python
import pandas as pd

coords = pd.read_csv('tests/SiouxFalls_coordinates.csv', index_col='node_id')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')

# Attach to nodes
for node_id in net.node.keys():
    if node_id in coords.index:
        net.node[node_id].x = coords.loc[node_id, 'x']
        net.node[node_id].y = coords.loc[node_id, 'y']
```

---

### 5.2 Visualization Approaches

#### Approach 1: Matplotlib (Static, Simple)

**Best for:** Quick visualizations, research papers, simple network topology

```python
import matplotlib.pyplot as plt
import pandas as pd

# Load coordinates
coords = pd.read_csv('tests/SiouxFalls_coordinates.csv', index_col='node_id')

# Load network and solve
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=2000)

# Plot network
fig, ax = plt.subplots(figsize=(12, 10))

# Draw links colored by flow
for link_id, link in net.link.items():
    # Extract origin and destination node IDs
    origin, dest = link_id.strip('()').split(',')
    
    if origin in coords.index and dest in coords.index:
        x_coords = [coords.loc[origin, 'x'], coords.loc[dest, 'x']]
        y_coords = [coords.loc[origin, 'y'], coords.loc[dest, 'y']]
        
        # Color by congestion level
        congestion = link.flow / link.capacity if link.capacity > 0 else 0
        color = plt.cm.RdYlGn_r(min(congestion, 1.0))  # Red = congested
        
        ax.plot(x_coords, y_coords, color=color, linewidth=2, alpha=0.7)

# Draw nodes
ax.scatter(coords['x'], coords['y'], c='black', s=50, zorder=5)

# Annotations
for node_id in coords.index[:5]:  # Label first 5 nodes
    ax.annotate(str(node_id), (coords.loc[node_id, 'x'], coords.loc[node_id, 'y']),
                fontsize=8, ha='right')

ax.set_title('Network Flow - Congestion Level')
ax.set_xlabel('X Coordinate')
ax.set_ylabel('Y Coordinate')
plt.colorbar(plt.cm.ScalarMappable(cmap='RdYlGn_r'), ax=ax, label='Congestion')
plt.savefig('results/network_map.png', dpi=300)
plt.show()
```

#### Approach 2: Folium (Interactive Web Maps)

**Best for:** Real geographic coordinates (lat/lon), interactive exploration, presentations

```bash
pip install folium
```

```python
import folium
import pandas as pd

coords = pd.read_csv('tests/SiouxFalls_coordinates.csv')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=2000)

# Create base map (centered on network)
center_lat = coords['lat'].mean()
center_lon = coords['lon'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

# Add links as lines
for link_id, link in net.link.items():
    origin, dest = link_id.strip('()').split(',')
    
    if origin in coords['node_id'].values and dest in coords['node_id'].values:
        origin_coords = coords[coords['node_id'] == origin].iloc[0]
        dest_coords = coords[coords['node_id'] == dest].iloc[0]
        
        # Line color by congestion
        congestion = link.flow / link.capacity if link.capacity > 0 else 0
        if congestion > 1.2:
            color = 'red'
        elif congestion > 0.8:
            color = 'orange'
        else:
            color = 'green'
        
        # Create line
        folium.PolyLine(
            locations=[
                [origin_coords['lat'], origin_coords['lon']],
                [dest_coords['lat'], dest_coords['lon']]
            ],
            color=color,
            weight=3,
            opacity=0.7,
            popup=f"Link {link_id}<br>Flow: {link.flow:.0f}<br>Capacity: {link.capacity:.0f}"
        ).add_to(m)

# Add nodes as circles
for _, row in coords.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=5,
        color='black',
        fill=True,
        popup=f"Node {row['node_id']}"
    ).add_to(m)

# Save
m.save('results/network_map_interactive.html')
print('Saved: results/network_map_interactive.html')
```

#### Approach 3: GeoPandas (GIS Integration)

**Best for:** Professional GIS workflows, shapefile export, spatial operations

```bash
pip install geopandas shapely
```

```python
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd

coords = pd.read_csv('tests/SiouxFalls_coordinates.csv')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=2000)

# Create GeoDataFrame for links
link_data = []
for link_id, link in net.link.items():
    origin, dest = link_id.strip('()').split(',')
    
    if origin in coords['node_id'].values and dest in coords['node_id'].values:
        origin_coords = coords[coords['node_id'] == origin].iloc[0]
        dest_coords = coords[coords['node_id'] == dest].iloc[0]
        
        geometry = LineString([
            (origin_coords['lon'], origin_coords['lat']),
            (dest_coords['lon'], dest_coords['lat'])
        ])
        
        link_data.append({
            'link_id': link_id,
            'flow': link.flow,
            'capacity': link.capacity,
            'congestion': link.flow / link.capacity if link.capacity > 0 else 0,
            'geometry': geometry
        })

links_gdf = gpd.GeoDataFrame(link_data, crs='EPSG:4326')

# Export to shapefile (readable by QGIS, ArcGIS)
links_gdf.to_file('results/network_links.shp')
print('Saved: results/network_links.shp')

# Quick plot
fig, ax = plt.subplots(figsize=(12, 10))
links_gdf.plot(ax=ax, column='congestion', cmap='RdYlGn_r', linewidth=2, legend=True)
ax.set_title('Network Congestion')
plt.savefig('results/network_geopandas.png', dpi=300)
```

#### Approach 4: Kepler.gl (Advanced, Beautiful)

**Best for:** Stunning visualizations, animated flows, presentations to executives

```bash
pip install keplergl
```

```python
from keplergl import KeplerGl
import pandas as pd

coords = pd.read_csv('tests/SiouxFalls_coordinates.csv')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=2000)

# Prepare data
link_data = []
for link_id, link in net.link.items():
    origin, dest = link_id.strip('()').split(',')
    
    if origin in coords['node_id'].values and dest in coords['node_id'].values:
        origin_coords = coords[coords['node_id'] == origin].iloc[0]
        dest_coords = coords[coords['node_id'] == dest].iloc[0]
        
        link_data.append({
            'origin_lat': origin_coords['lat'],
            'origin_lon': origin_coords['lon'],
            'dest_lat': dest_coords['lat'],
            'dest_lon': dest_coords['lon'],
            'flow': link.flow,
            'congestion': link.flow / link.capacity if link.capacity > 0 else 0
        })

links_df = pd.DataFrame(link_data)

# Create map
map_1 = KeplerGl(height=600)
map_1.add_data(data=links_df, name='network_flows')
map_1.save_to_html(file_name='results/network_kepler.html')
print('Saved: results/network_kepler.html')
```

---

### 5.3 Hazard Layer Overlay

#### Example: Flood Zone Analysis

**Scenario:** Identify which links are vulnerable to 100-year flood events.

**Step 1: Obtain Hazard Data**

Download flood zone shapefile from FEMA (or other source):
```bash
# Example for Sioux Falls, SD
# Download from: https://msc.fema.gov/portal/home
# File: FEMA_FloodZones_SiouxFalls.shp
```

**Step 2: Spatial Intersection**

```python
import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd

# Load network
coords = pd.read_csv('tests/SiouxFalls_coordinates.csv')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')

# Create links GeoDataFrame (same as before)
link_data = []
for link_id, link in net.link.items():
    origin, dest = link_id.strip('()').split(',')
    
    if origin in coords['node_id'].values and dest in coords['node_id'].values:
        origin_coords = coords[coords['node_id'] == origin].iloc[0]
        dest_coords = coords[coords['node_id'] == dest].iloc[0]
        
        geometry = LineString([
            (origin_coords['lon'], origin_coords['lat']),
            (dest_coords['lon'], dest_coords['lat'])
        ])
        
        link_data.append({
            'link_id': link_id,
            'geometry': geometry
        })

links_gdf = gpd.GeoDataFrame(link_data, crs='EPSG:4326')

# Load flood zones
flood_zones = gpd.read_file('data/FEMA_FloodZones_SiouxFalls.shp')

# Ensure same CRS
flood_zones = flood_zones.to_crs('EPSG:4326')

# Spatial join: which links intersect flood zones?
vulnerable_links = gpd.sjoin(links_gdf, flood_zones, how='inner', predicate='intersects')

print(f'Total links: {len(links_gdf)}')
print(f'Flood-vulnerable links: {len(vulnerable_links)}')
print(f'Vulnerable link IDs: {vulnerable_links["link_id"].tolist()}')

# Export for visualization
vulnerable_links.to_file('results/flood_vulnerable_links.shp')
```

**Step 3: Run Disruption Analysis**

```python
from policies.modifiers import remove_links, reset_flows

# Baseline
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
baseline_tstt = sum(l.flow * l.cost for l in net.link.values())

# Flood scenario: remove vulnerable links
print(f'\nRemoving {len(vulnerable_links)} flood-vulnerable links...')
reset_flows(net)
remove_links(net, vulnerable_links['link_id'].tolist())
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
flood_tstt = sum(l.flow * l.cost for l in net.link.values())

print(f'Baseline TSTT: {baseline_tstt:,.0f}')
print(f'Flood TSTT:    {flood_tstt:,.0f}')
print(f'Impact:        +{((flood_tstt - baseline_tstt) / baseline_tstt)*100:.1f}%')
```

---

### 5.4 Advanced Spatial Analysis

#### Buffer Zone Analysis

**Question:** Which links are within 500m of critical infrastructure?

```python
import geopandas as gpd
from shapely.geometry import Point

# Critical infrastructure (hospitals, emergency services)
critical_points = gpd.GeoDataFrame({
    'name': ['Hospital A', 'Fire Station B'],
    'geometry': [Point(-96.729, 43.544), Point(-96.735, 43.550)]
}, crs='EPSG:4326')

# Create 500m buffer (convert to UTM for meters)
critical_points_utm = critical_points.to_crs('EPSG:32614')  # UTM Zone 14N
buffers = critical_points_utm.buffer(500)  # 500 meters
buffers_gdf = gpd.GeoDataFrame({'geometry': buffers}, crs='EPSG:32614').to_crs('EPSG:4326')

# Find links within buffer
links_gdf_utm = links_gdf.to_crs('EPSG:32614')
critical_access_links = gpd.sjoin(links_gdf_utm, buffers_gdf.to_crs('EPSG:32614'), 
                                   how='inner', predicate='intersects')

print(f'Links providing critical access: {len(critical_access_links)}')
```

#### Proximity Analysis

**Question:** How far is each OD pair from the nearest hospital?

```python
from shapely.ops import nearest_points

# For each zone centroid
zone_coords = coords.set_index('node_id')

for zone_id in net.zones:
    if zone_id in zone_coords.index:
        zone_point = Point(zone_coords.loc[zone_id, 'lon'], 
                          zone_coords.loc[zone_id, 'y'])
        
        # Find nearest hospital
        nearest_geom = nearest_points(zone_point, critical_points.unary_union)[1]
        distance_km = zone_point.distance(nearest_geom) * 111  # rough lat/lon to km
        
        print(f'Zone {zone_id}: {distance_km:.2f} km to nearest hospital')
```

#### Multi-Hazard Overlay

**Scenario:** Combine flood zones, earthquake risk, and wildfire zones.

```python
# Load multiple hazard layers
floods = gpd.read_file('data/flood_zones.shp')
quakes = gpd.read_file('data/earthquake_risk.shp')
fires = gpd.read_file('data/wildfire_zones.shp')

# Intersect each with network links
flood_links = gpd.sjoin(links_gdf, floods, predicate='intersects')
quake_links = gpd.sjoin(links_gdf, quakes, predicate='intersects')
fire_links = gpd.sjoin(links_gdf, fires, predicate='intersects')

# Count hazard exposure per link
hazard_counts = {}
for link_id in links_gdf['link_id']:
    count = 0
    if link_id in flood_links['link_id'].values: count += 1
    if link_id in quake_links['link_id'].values: count += 1
    if link_id in fire_links['link_id'].values: count += 1
    hazard_counts[link_id] = count

# Prioritize multi-hazard links for resilience investments
high_risk = [k for k, v in hazard_counts.items() if v >= 2]
print(f'Links exposed to 2+ hazards: {high_risk}')
```

---

### 5.5 Complete Spatial Disruption Workflow

Create `experiments/spatial_flood_disruption.py`:

```python
"""Spatial flood disruption analysis for Sioux Falls network."""
import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd
import folium
from network import Network
from policies.modifiers import remove_links, reset_flows
import csv, os

# Load network and coordinates
coords = pd.read_csv('tests/SiouxFalls_coordinates.csv')
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')

# Build spatial network
link_geometries = []
for link_id, link in net.link.items():
    origin, dest = link_id.strip('()').split(',')
    if origin in coords['node_id'].values and dest in coords['node_id'].values:
        origin_row = coords[coords['node_id'] == origin].iloc[0]
        dest_row = coords[coords['node_id'] == dest].iloc[0]
        geom = LineString([
            (origin_row['lon'], origin_row['lat']),
            (dest_row['lon'], dest_row['lat'])
        ])
        link_geometries.append({'link_id': link_id, 'geometry': geom})

links_gdf = gpd.GeoDataFrame(link_geometries, crs='EPSG:4326')

# Load flood zones
flood_zones = gpd.read_file('data/flood_zones_100yr.shp').to_crs('EPSG:4326')

# Identify vulnerable links
vulnerable = gpd.sjoin(links_gdf, flood_zones, predicate='intersects')
vulnerable_ids = vulnerable['link_id'].unique().tolist()

print(f'Vulnerable links: {len(vulnerable_ids)}/{len(links_gdf)}')

# Baseline scenario
print('\nBaseline (no flooding)...')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
baseline_tstt = sum(l.flow * l.cost for l in net.link.values())
baseline_gap = net.relativeGap()

# Flood scenario
print('Flood scenario (vulnerable links disabled)...')
reset_flows(net)
remove_links(net, vulnerable_ids)
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
flood_tstt = sum(l.flow * l.cost for l in net.link.values())
flood_gap = net.relativeGap()

# Results
impact_pct = ((flood_tstt - baseline_tstt) / baseline_tstt) * 100
print(f'\nImpact: +{impact_pct:.1f}% increase in TSTT')

# Save results
os.makedirs('results', exist_ok=True)
with open('results/flood_disruption.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['scenario', 'tstt', 'gap', 'vulnerable_links'])
    w.writeheader()
    w.writerow({'scenario': 'baseline', 'tstt': baseline_tstt, 'gap': baseline_gap, 
                'vulnerable_links': 0})
    w.writerow({'scenario': 'flood', 'tstt': flood_tstt, 'gap': flood_gap,
                'vulnerable_links': len(vulnerable_ids)})

# Create interactive map
m = folium.Map(location=[coords['lat'].mean(), coords['lon'].mean()], zoom_start=12)

# Add flood zones (semi-transparent)
folium.GeoJson(
    flood_zones,
    style_function=lambda x: {'fillColor': 'blue', 'color': 'blue', 
                              'weight': 1, 'fillOpacity': 0.3},
    name='100-Year Flood Zone'
).add_to(m)

# Add vulnerable links (red)
for link_id in vulnerable_ids:
    geom = links_gdf[links_gdf['link_id'] == link_id].iloc[0].geometry
    coords_list = [[c[1], c[0]] for c in geom.coords]  # lat, lon order for folium
    folium.PolyLine(coords_list, color='red', weight=4, 
                    popup=f'Vulnerable: {link_id}').add_to(m)

# Add safe links (green)
safe_ids = set(links_gdf['link_id']) - set(vulnerable_ids)
for link_id in safe_ids:
    geom = links_gdf[links_gdf['link_id'] == link_id].iloc[0].geometry
    coords_list = [[c[1], c[0]] for c in geom.coords]
    folium.PolyLine(coords_list, color='green', weight=2, opacity=0.5,
                    popup=f'Safe: {link_id}').add_to(m)

folium.LayerControl().add_to(m)
m.save('results/flood_disruption_map.html')

print('\nSaved: results/flood_disruption.csv')
print('Saved: results/flood_disruption_map.html')
```

---

### 5.6 Tools & Packages Summary

| Tool | Best For | Installation |
|------|----------|-------------|
| **matplotlib** | Static plots, research papers | `pip install matplotlib` |
| **folium** | Interactive web maps | `pip install folium` |
| **geopandas** | GIS operations, shapefiles | `pip install geopandas` |
| **keplergl** | Beautiful visualizations | `pip install keplergl` |
| **contextily** | Add basemaps to plots | `pip install contextily` |
| **plotly** | Interactive 3D visualizations | `pip install plotly` |

For GIS professionals:
- **QGIS** (free, open source): Import shapefiles, manual editing
- **ArcGIS**: Enterprise GIS with advanced spatial analytics

---

### 5.7 Key Considerations

**Coordinate Systems:**
- **WGS84 (EPSG:4326)**: Standard lat/lon, use for web maps (folium, kepler)
- **UTM**: Projected coordinates in meters, use for distance calculations
- Always check and convert CRS when combining datasets

**Data Sources:**
- **Network coordinates**: TNTP website, academic papers, digitize from maps
- **Hazard layers**: FEMA (floods), USGS (earthquakes), state agencies (wildfires)
- **Basemaps**: OpenStreetMap, Google Maps API, Mapbox

**Performance:**
- Large networks (>1000 links) may be slow to render
- Simplify geometries for web maps: `gdf.simplify(tolerance=0.001)`
- Use tile-based rendering for huge datasets

**Validation:**
- Always visually inspect: do links connect correct nodes?
- Check coordinate system: does network align with basemap?
- Verify hazard overlay: do flood zones cover expected areas?

---

## Implementation Patterns

### Standard Experiment Template

All workflow experiments follow this pattern:

```python
from network import Network
from policies.modifiers import [YOUR_FUNCTION]
import csv, os

# 1. SETUP
PARAM_VALUE = 2.0  # Your parameter
net = Network('tests/SiouxFalls_net.txt', 'tests/SiouxFalls_trips.txt')

# 2. BASELINE
print('Baseline...')
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
baseline_metrics = {
    'tstt': sum(l.flow * l.cost for l in net.link.values()),
    'gap': net.relativeGap(),
    'avg_speed': compute_avg_speed(net)  # Custom metrics
}

# 3. APPLY POLICY
print('Applying policy...')
reset_flows(net)  # Important: clear flows before re-solving
[YOUR_FUNCTION](net, PARAM_VALUE)

# 4. RE-SOLVE
net.userEquilibrium(stepSizeRule='FW', targetGap=1e-4, maxIterations=3000)
policy_metrics = {
    'tstt': sum(l.flow * l.cost for l in net.link.values()),
    'gap': net.relativeGap(),
    'avg_speed': compute_avg_speed(net)
}

# 5. COMPARE
print(f'TSTT change: {((policy_metrics["tstt"] - baseline_metrics["tstt"]) / baseline_metrics["tstt"])*100:.1f}%')

# 6. SAVE
os.makedirs('results', exist_ok=True)
with open('results/experiment_name.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['scenario', 'tstt', 'gap'])
    w.writeheader()
    w.writerow({'scenario': 'baseline', **baseline_metrics})
    w.writerow({'scenario': 'policy', **policy_metrics})
```

### Debugging Tips

- **Gap not converging?** Check if policy creates extreme congestion; increase `maxIterations`
- **Unexpected results?** Verify network loaded correctly: `print(len(net.link), len(net.ODpair))`
- **Link modifications not working?** Ensure link IDs match network format (usually strings like `'(1,2)'`)
- **Always reset flows** between scenarios with `reset_flows(net)` to avoid cascading effects
- **Slow performance?** Use smaller networks first (3parallel, braess) before SiouxFalls (24 nodes, 76 links)

---

## Running Experiments

```bash
# Single experiment
python experiments/link_removal_siouxfalls.py

# All demand growth scenarios
python experiments/demand_growth_siouxfalls.py

# Emission sensitivity analysis
python experiments/emissions_optimization_siouxfalls.py

# System optimal approximation
python experiments/system_optimal_siouxfalls.py
```

Results saved to `results/` as CSV files, ready for analysis in Excel, Python, or R.

---

## Next Steps

- **Combine workflows:** e.g., "Demand growth + capacity expansion" (growth scenario planning)
- **Add uncertainty:** Run each scenario with perturbations to understand robustness
- **Equity analysis:** Compute impacts by OD pair origin/destination zone
- **Visualization:** Plot TSTT vs. congestion level, toll distribution, flow changes
- **Validation:** Compare to real data when available; calibrate emission models

