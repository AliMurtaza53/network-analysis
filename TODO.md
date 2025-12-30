# Network Analysis Project - TODO List

## Overview
This document tracks development tasks, improvements, and known issues for the transportation network analysis project.

## Completed Functions
- ✅ `relativeGap()` - Calculate relative gap for convergence assessment
- ✅ `averageExcessCost()` - Calculate AEC for convergence assessment
- ✅ `shiftFlows()` - Update link flows via convex combinations
- ✅ `FrankWolfeStepSize()` - Compute optimal step size using binary search
- ✅ `userEquilibrium()` - Solve for user equilibrium via convex combinations (REFACTORED)
- ✅ `acyclicShortestPath()` - Find shortest paths using topological order
- ✅ `shortestPath_label()` - Label-setting shortest path algorithm
- ✅ `shortestPath_heap()` - Dijkstra heap-based shortest path (default)
- ✅ `allOrNothing()` - All-or-nothing traffic assignment
- ✅ `findLeastEnteringLinks()` - Support for topological ordering
- ✅ `findTopologicalOrder()` - Compute topological ordering for acyclic networks
- ✅ `createTopologicalList()` - Build list from topological order
- ✅ `formAdjacencyMatrix()` - Build adjacency matrix representation
- ✅ `loadPaths()` - Load path flows to link and update costs
- ✅ File I/O - Read TNTP format network and demand files
- ✅ Validation & Finalization - Network data validation and initialization

## Recently Fixed Issues
### userEquilibrium() Refactoring (Dec 30, 2025)
- **Issue**: Used global variables `iteration_times` and `relative_gaps`
- **Fix**: Refactored to use local variables and return convergence history as dictionary
- **Return value**: `{'iteration_times': [...], 'relative_gaps': [...]}`
- **Improved**: Function parameter `gapFunction` now defaults to None with self.relativeGap as default
- **Benefit**: Function is now reusable and thread-safe; convergence history is captured per call

## Functions Needing Updates or Refinement

### High Priority
1. **Convergence Criteria Enhancement**
   - Current: `userEquilibrium()` supports relativeGap and averageExcessCost
   - TODO: Consider adding Beckmann function or other convergence measures
   - TODO: Better documentation of convergence behavior with different step size rules
   - TODO: Add convergence diagnostics/warnings

2. **Step Size Rule Variants**
   - Current: MSA supports 'natural' (1/(k+1)), 'squares' (1/(k^2+1)), exponential
   - TODO: Evaluate performance trade-offs for each variant
   - TODO: Add adaptive step size rules
   - TODO: Document recommended settings for different network types

3. **Shortest Path Algorithm Selection**
   - Current: Two implementations available (label-setting and heap-based Dijkstra)
   - TODO: Document performance characteristics for different network types
   - TODO: Consolidate or provide clear guidance on which to use
   - TODO: Consider profile-guided optimization

### Medium Priority
4. **Path-Based Assignment**
   - Current: Path data structures exist; `loadPaths()` implemented
   - TODO: Develop or refine path-based user equilibrium solver
   - TODO: Add path enumeration strategies
   - TODO: Path cost calculation and update mechanisms

5. **Link Cost Function**
   - Current: Uses BPR (Bureau of Public Roads) cost function
   - TODO: Document cost function clearly
   - TODO: Consider support for alternative cost functions
   - TODO: Add toll and distance cost factors

### Low Priority
6. **Data Structure Optimization**
   - Adjacency matrix uses dict of dicts (could be sparse matrix for large networks)
   - TODO: Evaluate performance on large networks (>10K nodes)
   - TODO: Consider numpy/scipy sparse matrices if scaling needed

7. **Testing & Validation**
   - TODO: Add unit tests for all core algorithms
   - TODO: Add network benchmark suite
   - TODO: Validate against known test cases (e.g., Sioux Falls)

8. **Documentation**
   - TODO: Add comprehensive algorithm documentation
   - TODO: Parameter sensitivity analysis
   - TODO: Usage examples and case studies

## Known Issues
- Topological ordering temporarily modifies reverse star lists (restored at end)
- Limited error handling for degenerate cases
- No support for asymmetric costs (one-way restrictions, tolls with direction)

## Architecture Notes
- **Files**: network.py (core), link.py, node.py, od.py, path.py (data structures)
- **Data Format**: TNTP (Transportation Network Test Problem)
- **Primary Algorithm**: Link-based convex combinations (MSA/Frank-Wolfe)
- **Shortest Path**: Default uses Dijkstra with binary heap (label-setting available)
- **Test Networks**: 3-parallel, Braess, SiouxFalls, Anaheim, Barcelona

## Testing
- Run validation: `python validate.py --network <file> --demand <file>`
- Run tests: `python tests.py`
- Benchmarking available in `bench/` directory

## Notes for Future Developers
- When modifying path-related code, ensure `path.cost` is updated
- Always call `link.updateCost()` after changing `link.flow`
- Respect `firstThroughNode` to prevent centroid shortcuts
- TNTP format: nodes numbered 1..numNodes (Python uses 0-based indexing internally)
- userEquilibrium() now returns convergence history - check return value for analysis

