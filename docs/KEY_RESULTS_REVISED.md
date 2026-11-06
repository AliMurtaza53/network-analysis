# Revised key results (supersedes docs/Q2_results.md and docs/Q3_sensitivity.md and the first Word draft)

Everything below is from `scripts/run_revision.py` (data in `outputs/revised/`) and `scripts/plot_revised.py`
(figures in `outputs/revised/figures/`). Every impact ratio is paired: the disrupted network is compared with a baseline
solved under the same parameters and solver settings. Solver noise floor is about 0.05% of baseline.

## 1. What was wrong with the first draft

| First-draft claim | Status | What the data say |
|---|---|---|
| S4 is a "corridor" loss | Wrong | Every Anaheim link has `linkType == 1`, so S4 cut capacity on all 914 links. Rebuilt as S4a (network-wide) and S4b (the 10% busiest links, 92 links). |
| S4 at 25% capacity gives 17.9x | Right, but it is an identity | Uniform capacity x0.25 is the same as demand x4: per-trip time ratio is 17.943 in both runs. Max v/c reaches 7.56, far outside the range BPR was calibrated for. |
| S1 ratios below 1 are a Braess effect (15% of runs, min 0.829) | Wrong | 14 of 61 runs (23%) are below 1; 12 of those cut zones off and drop their demand from total travel time. Per served trip the minimum is 0.98. |
| S2 top-1, top-3, top-5 | Flawed design | Top-3 gave exactly the same result as top-1: the top-3 links are consecutive segments of one arterial. Replaced by greedy selection. |
| S5 combined with "corridor loss" | Wrong | S5 combos were with a 2 km flood. Rebuilt with flood and with S2 top-3. |
| S5 TSTT is comparable with other families | Wrong | TSTT rises with demand itself. Use time per served trip (1.10 and 1.24 for x1.2 and x1.4 alone). |
| Criticality: "top 5 links are 60% of criticality", "all >90% v/c" | Unsupported | 17 of 60 screened links have negative "criticality" (closing them lowers TSTT, min -267,116 veh-min), so a share of the total is undefined. Top-5 are 47% of the summed positive effects (43 links); baseline v/c of top-5 is 1.06-1.18. |
| Recovery: R = 0.80-0.85, "never reaches 95%" | Artifact | Closed links were deleted from the graph, so partial restoration did nothing: Q(t) was a step at day 90 and R came from interpolating 6 samples. Fixed. |
| Accessibility tracks TSTT, rho = 0.91 | Unsupported | Spearman 0.74 against time per served trip (non-S5 scenarios). |
| Q3: demand dominates (mu* = 0.93), no interactions | Reversed | Old ratios compared against one fixed baseline, so changing demand/alpha/beta mostly moved the baseline. Paired, the ranking depends on the disruption (section 4). |
| Q3: AON overstates impact by 5-8% | Mostly unsupported | +1.0%, +0.1%, +5.3% for three scenarios (section 4). |
| California BPR parameters alpha 0.8-1.0, beta 5-8 | Unsourced | Dropped. |

## 2. Q2 results (Fig. F3, F4, F6)

Scenario set: baseline + 61 random (k=1: 1 run; k=5: 30; k=10: 30) + 3 targeted + 3 flood + 6 capacity + 6 demand = 80 runs
(plus one demand x4 identity check).

Family comparison, impact on total travel time (TSTT) and time per served trip (TT), ratio to baseline:

| Family | Scenario | TSTT | TT | Accessibility loss |
|---|---|---|---|---|
| S1 random, 5 links | median / max | 1.013 / 1.221 | same | up to 8.2% |
| S1 random, 10 links | median / max | 1.021 / 1.148 | 1.024 / 1.148 | up to 12% |
| S2 greedy top-1 / 3 / 5 | | 1.218 / 1.394 / 1.532 | same | 7.8 / 11.7 / 21.0% |
| S3 flood r = 1 / 2 / 3 km | | 1.001 / 1.016 / 1.079 | same | 0.1 / 1.6 / 7.9% |
| S4a all links, cap 0.75 / 0.5 / 0.25 | | 1.182 / 2.092 / 17.943 | same | 12 / 36 / 71% |
| S4b busiest 10%, cap 0.75 / 0.5 / 0.25 | | 1.160 / 1.940 / 15.459 | same | 10 / 29 / 49% |
| S5 demand x1.2 / x1.4 | | 1.316 / 1.731 | 1.097 / 1.237 | n/a |
| S5 x1.2 / x1.4 + flood r=2 km | | 1.334 / 1.754 | 1.111 / 1.253 | n/a |
| S5 x1.2 / x1.4 + S2 top-3 | | 2.240 / 3.686 | 1.867 / 2.633 | n/a |

- S1: 25 of 61 runs cut at least one zone off (23% of k=5 runs, 60% of k=10); mean unserved demand 1.5%, max 16%.
  Among the 36 runs that keep every zone connected, median TSTT ratio is 1.024 (range 1.000-1.221).
- Greedy top-5 closure list: (92,91), (115,114), (211,210), (169,168), (192,191). Marginal TSTT ratios 1.218, 1.318, 1.394, 1.465, 1.532.
- S5 compound effect: demand x1.4 alone is 1.24 per trip and top-3 closure alone is 1.39; together they are 2.63, versus 1.72 if effects multiplied.
- Accessibility loss is not shown for S5: the demand-weighted measure rises with demand itself.
- Criticality (single-link closure, 60 highest-flow links screened, baseline TSTT 1.420 million veh-min per peak hour):
  (92,91) and (91,90) each +21.8% (308,978 veh-min), (90,89) +21.2%, (114,113) and (115,114) +9.8%. Ranks 1-3 are consecutive links of one corridor.
  Top-3 are 36%, top-5 47%, top-12 70% of the summed positive effects. Caveat: closures that cut zones off lower TSTT (17 negative values), so TSTT-based criticality should be paired with unserved demand.
- Recovery (capacity restored linearly over 90 days, equilibrium re-solved every 5 days):

| Scenario | Q at day 0 | R (90-day mean of Q) | Days to Q >= 0.95 |
|---|---|---|---|
| S2 top-1 | 0.82 | 0.983 | 9 |
| S2 top-5 | 0.65 | 0.950 | 26 |
| S3 flood r = 3 km | 0.93 | 0.965 | 24 |
| S4b busiest 10%, cap 0.5 | 0.52 | 0.827 | 69 |
| S4b busiest 10%, cap 0.25 | 0.06 | 0.640 | 76 |

  Restoration is front-loaded: for the top-1 closure Q is back above 0.95 after 9 days (10% of capacity restored), because BPR delay is convex in flow/capacity.

## 3. Q1 corrections for the methods text

- Network: 416 nodes, 914 links, 38 zones, 104,694 veh/h; all links have type 1.
- S4 must be described as (a) network-wide capacity loss and (b) capacity loss on the busiest 10% of links.
- S2 must be described as greedy: each step closes the link that most increases TSTT given links already closed, among the 30 highest single-link-criticality candidates, restricted to choices that keep every zone connected.
- S5 is measured against the original-demand baseline; Q3 sensitivity is measured against the same-parameter baseline.
- Q(t) = (served share) x (baseline mean trip time / disrupted mean trip time), capped at 1.
- TSTT excludes unserved demand; report unserved share alongside it.

## 4. Q3 results (Fig. F8, F10, F13)

Reference disruptions: flood (r = 3 km, depth 100% of 300 mm) and top-3 greedy closure. Parameters: demand multiplier 0.8-1.4,
BPR alpha 0.15-0.50, BPR beta 2-6, flood radius 1-5 km, flood depth 25-100%, solver gap 1e-4 to 1e-2.
Value-of-time, truck share and PCE enter only the linear economic-cost formula and cannot change physical outputs.

Finding 1, what matters depends on the disruption (OAT swing in TSTT impact ratio):

| Parameter | Flood reference | Closure reference |
|---|---|---|
| Flood radius (1-5 km) | 0.651 | n/a |
| Flood depth | 0.062 | n/a |
| BPR beta | 0.009 | 6.005 |
| Demand multiplier | 0.009 | 0.928 |
| BPR alpha | 0.008 | 0.623 |
| Solver gap | 0.001 | 0.002 |

  For a flood, only the hazard's size and depth matter; flood impact is steeply nonlinear in radius (1.001, 1.016, 1.079, 1.271, 1.652 at 1-5 km).
  For a closure, the congestion function and demand dominate, because diverted flow pushes v/c to about 4.6 where the beta-th power amplifies delay.

Finding 2, effects are nonlinear and interacting (Morris, 16 trajectories, 112 runs, flood reference):

| Parameter | mu* (TSTT impact) | sigma | mu* (accessibility loss) | sigma |
|---|---|---|---|---|
| Flood radius | 0.534 | 0.857 | 0.260 | 0.157 |
| Flood depth | 0.378 | 0.729 | 0.145 | 0.119 |
| BPR beta | 0.174 | 0.478 | 0.013 | 0.016 |
| Demand | 0.036 | 0.065 | 0.022 | 0.025 |
| BPR alpha | 0.016 | 0.021 | 0.020 | 0.018 |
| Solver gap (log10) | 0.007 | 0.011 | 0.003 | 0.004 |

  sigma exceeds mu* for radius, depth and beta (TSTT impact): these act nonlinearly or through interactions, the opposite of the first draft.
  Caveat: 16 trajectories gives wide bootstrap intervals; the ranking is robust, exact mu* values are not.

Finding 3, solver tolerance and model form (baseline and three disruptions):

| Quantity | eps = 1e-2 | 1e-3 | 1e-4 | 1e-5 (reference) |
|---|---|---|---|---|
| Baseline TSTT error | +1.19% | +0.07% | -0.01% | 0 |
| Impact-ratio error (flood, closure, arterial) | up to 0.12% | up to 0.07% | up to 0.05% | 0 |
| Iterations (flood / closure / arterial / baseline) | 2-5 | 5-14 | 12-50 | 33-260 |

  Absolute TSTT needs eps <= 1e-3; impact ratios are already stable at 1e-2. The default 1e-4 is safe.
  Single-iteration assignment versus full equilibrium, impact ratio: flood 1.090 vs 1.079, top-3 closure 1.395 vs 1.394, arterial cap 0.5: 2.042 vs 1.940.
  The shortcut is adequate unless the network is heavily congested.

## 5. Limits to state in the report

- BPR with beta = 4 is applied far outside its calibration range in S4 (max v/c 7.56); S4 at cap 0.25 is a stress test, not a forecast.
- No demand elasticity, no queue spillback, no rerouting or departure-time response.
- Flood is a synthetic footprint centred on Anaheim; the Pregnolato depth-speed function is applied, but depths are assumed.
- Economic cost uses assumed values of time and truck parameters; illustrative only.
- Single-link criticality screens only the 60 highest-flow links.
- References in `docs/references.bib` were written from memory; DOIs need a spot check before submission.

## 6. Decisions needed before regenerating the draft

1. Keep S4a and S4b both, or report only S4b as the "corridor" scenario?
2. Add an unserved-demand-aware criticality ranking (closures that cut zones off currently look harmless in TSTT)?
3. Reference disruption for Q3: keep flood and top-3 closure, or add the arterial scenario?
4. Replace the old figures in `outputs/q2` and `outputs/q3`, or keep `outputs/revised` alongside them?
