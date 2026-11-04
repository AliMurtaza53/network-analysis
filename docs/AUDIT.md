# AUDIT.md — Phase 0 Findings

Date: 2026-11-04

## Unit tests and solver

- `python validate.py` on SiouxFalls: **40/40 unit tests pass**.
- SiouxFalls UE (FW, gap 1e-4): **13.7 s**, final gap 9.9e-5.
- Anaheim UE (FW, gap 1e-4): **6.2 s**, final gap 7.0e-5.
- Both converge well within budget. A full Morris sweep of ~90 Anaheim solves runs in roughly 10 minutes.

## Unverified items (from Section 3)

**1. Geojson filenames and join schema.**
Confirmed. `bstabler/TransportationNetworks/Anaheim/` ships `anaheim.geojson` (914 LineString features) and `anaheim_nodes.geojson` (416 Point features). Link join key: `init_node` and `term_node` properties map directly to the TNTP tail/head integers; link ID in `network.py` is the string `'(tail,head)'`. Count check: 914 links and 416 nodes match TNTP metadata exactly.

**2. `<FIRST THRU NODE>` handling.**
Confirmed correct. Anaheim metadata: `FIRST THRU NODE = 39`, meaning zones 1–38 (centroids) cannot serve as intermediate nodes. Both `shortestPath_heap` and `shortestPath_label` in `network.py` check `if u < self.firstThroughNode and u != origin: continue` before expanding a node. The first-thru-node constraint is correctly enforced.

**3. What `remove_links` does for disconnected OD pairs.**
`remove_links` does not exist in the codebase. The plan's `engine.run_scenario` will implement it. If a closure disconnects an OD pair, the existing `allOrNothing` will crash at `self.link[backlink[curnode]]` when `backlink[curnode] == NO_PATH_EXISTS`. The engine will perform a reachability check before calling the solver and drop unreachable OD pairs from the demand matrix, recording them as unmet demand.

**4. `scale_capacity` FFT auto-adjustment.**
Confirmed the bug described in the plan. `policies/modifiers.py:scale_capacity` defaults to `fft_factor = 1.0 / capacity_factor`, so halving capacity doubles FFT. This is correct for capacity expansion modelling (the existing experiments use it this way) but wrong for disruption scenarios where we want capacity reduced with FFT unchanged. The resilience engine will use its own capacity-reduction routine that keeps FFT fixed by default, with an optional speed-reduction mode. The existing `scale_capacity` default is not changed.

**5. BPR B and Power per link.**
Confirmed per-link. The TNTP reader stores `float(data[5])` as `alpha` (B) and `float(data[6])` as `beta` (Power) on each `Link` object. For Anaheim, all links have B=0.15 and Power=4 (uniform). These can be overridden for sensitivity runs by patching `link.alpha` and `link.beta` directly on a network copy before calling `userEquilibrium`.

**6. Runtime.**
SiouxFalls: 13.7 s. Anaheim: 6.2 s. Sweep budget: 90 Morris solves ≈ 9 min on Anaheim. This is within acceptable limits; warm starting from baseline flows will further reduce it. No need to relax gap for the main sweep.

**7. Python environment.**
`numpy` and `pandas` were pre-installed. `matplotlib`, `geopandas`, `shapely`, `scipy`, `SALib`, and `joblib` were installed in this session via pip. `pyproj` and `pyogrio` (geopandas backend) also installed.

## Bugs found in existing code

### `policies/modifiers.py`: `scale_demand` and `get_metrics` assume nested ODpair dict

`scale_demand` iterates `for origin_dict in net.ODpair.values(): for od in origin_dict.values()`. But `net.ODpair` is a flat dict keyed by strings like `'1->2'`; its values are `OD` objects, not nested dicts. These functions will raise `AttributeError` at runtime. `scale_specific_demand` has the same bug. The resilience package does not call these functions and implements its own demand scaling.

**Decision: do not modify `policies/modifiers.py`** until a failing test is written against it. The bugs are noted here. The resilience engine works directly on network copies.

## Open questions for Haider (Section 9)

1. **VOT, PCE, truck share, unmet penalty**: Using placeholder defaults (passenger VOT 18 USD/h, truck VOT 60 USD/h, PCE 2.0, truck share 8%, unmet penalty = 2 h × VOT). All labelled as placeholders in config and figures.

2. **Anaheim vs DMV network**: Proceeding with Anaheim as the primary network. A DMV network can be added later via config change only.

3. **Synthetic hazard footprint**: Proceeding with a synthetic Pregnolato-style depth-to-disruption function. Interface ready to accept a real raster.

## CRS note

Anaheim coordinates are in WGS84 (longitude/latitude). For distance-based work (footprint radius in km) the engine reprojects to EPSG:26911 (UTM 11N). All exports use WGS84.
