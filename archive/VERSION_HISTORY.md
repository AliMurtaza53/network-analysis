# Network.py Evolution History

This archive contains historical versions of `network.py` showing the evolution of the implementation. The current production version is `../network.py`.

## Version Timeline

### 1. network_baseline.py (Initial Implementation)
**Purpose**: Original homework/assignment version with basic UE solving functionality.

**Key Features**:
- Basic Frank-Wolfe and MSA algorithms
- Initial implementation of user equilibrium solver
- `run_demo()` function for testing on sample networks
- Basic shortest path algorithms

**Known Issues**:
- Used global variables for convergence tracking
- Less optimized performance
- Limited error handling

### 2. network_5.3final.py (Intermediate Refinement)
**Purpose**: Improved version with performance optimizations and bug fixes.

**Changes from baseline**:
- Performance improvements in shortest path algorithms
- Better convergence tracking
- Refined gap function calculations
- Improved code organization

**Status**: Intermediate development version

### 3. network_base.py (Refined Version)
**Purpose**: Further refinements and cleanup before final version.

**Changes**:
- Additional performance tuning
- Better documentation
- Code cleanup and refactoring
- Preparation for production release

### 4. network.py (Current Production Version)
**Location**: `../network.py`

**Final Improvements**:
- ✅ Removed global variables - `userEquilibrium()` now returns convergence data
- ✅ Fixed `run_demo()` to use correct gap function (`relativeGap` instead of `averageExcessCost`)
- ✅ Cleaned up homework instruction comments
- ✅ Consistent use of named parameters
- ✅ Better memory management
- ✅ Comprehensive docstrings
- ✅ Full validation test coverage

**Changes Log**:
- Refactored `userEquilibrium()` to return `{'iteration_times': [...], 'relative_gaps': [...]}`
- Changed default `gapFunction` parameter from `relativeGap` to `None` with runtime fallback
- Fixed convergence issues in `run_demo()` by using `relativeGap` consistently
- Removed global `iteration_times` and `relative_gaps` variables

## Migration Notes

When comparing implementations or debugging:
1. All versions follow the same TNTP file format
2. Core algorithms (Frank-Wolfe, MSA) are functionally equivalent
3. Main differences are in code organization, performance, and convergence tracking
4. Current version (`../network.py`) is the validated production code

## Usage

To test with archived versions (for comparison/debugging):
```bash
# Run validation with baseline
python validate.py --network archive/network_baseline.py

# Run validation with current
python validate.py --network network.py

# Compare performance
python -m tests.compare_networks \
  --network-a archive/network_baseline.py \
  --network-b network.py \
  --tests tests/protocol/siouxfalls_ue_fw.txt \
  --mode ue_solve --runs 3
```

## Recommendation

**Use `../network.py`** for all new work. The archived versions are kept for:
- Historical reference
- Performance comparison benchmarks
- Debugging regression issues
- Understanding implementation evolution
