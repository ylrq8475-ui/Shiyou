# Error history read-only audit for the 2026-10-22 bounded study

Role: internal support to account B. This is not an A2/Codex independent acceptance or training authorization. Model fits: 0. Preprocessor fits: 0. Raw competition files read: 0. Model weights loaded: 0. No previous files changed. Only completed aggregate JSON, plans and source text were inspected.

## Ridge branch can already be recomputed without training

Source: `D:/codex/A2B035_LIGHT_DUAL_20261021_v1/execution/RESULT_LIGHT_DUAL.json`, `results[*].temporal_only_descriptive`. Every split includes five fold scores, worst fold, fold population standard deviation and prefix weighted losses. Fold validation sizes are 17,16,16,16,16; weighting the stored fold scores by those counts reproduces the total to floating precision.

| Split | B0 | Ridge only | Ridge minus B0 | Full residual dual minus Ridge |
|---|---:|---:|---:|---:|
| Fixed | 73.71410733861434 | 73.23622758682410 | -0.47787975179024 | -1.26873215181146 |
| Repeat 1 | 72.72544757191915 | 73.43633737794123 | +0.71088980602208 | +0.15563747705005 |
| Repeat 2 | 72.82149914955260 | 73.90697908510760 | +1.08547993555500 | -0.66371300578443 |
| Repeat 3 | 72.09785488289351 | 73.84069193109107 | +1.74283704819756 | -0.49834382911091 |
| Repeat 4 | 72.30838983776125 | 73.22355473759830 | +0.91516489983705 | -1.37249785218488 |
| Repeat 5 | 72.42917858211703 | 73.61196750306182 | +1.18278892094479 | -1.03520836666532 |

Ridge repeated mean 73.60390612696; mean gain +1.1274321221112955; 5/5 repeat gains positive. Full dual repeated mean is worse than Ridge by 0.6828251153390965. Ridge still loses on the fixed split and has only 2–4 positive paired folds per repeat. It is not demonstrated stable on all partitions. The prior plan explicitly treated Ridge as a descriptive ablation, not a newly retained candidate. Its subgroup errors were not persisted: the existing ERROR_GROUPS describes B0 versus the full dual model, not Ridge alone. Do not relabel those groups as Ridge results.

## Repeated common error patterns and counterexamples

Sources: the LIGHT_DUAL and FEATURE_FRESHNESS_v2 `execution/ERROR_GROUPS.json`; freshness `GROUP_CONFOUNDING_CHECK.json`. The numbers below average five repeated splits of the same 81 wells, not five independent datasets. Groups overlap across dimensions; contributions cannot be summed across dimensions.

| Pre-prediction state | Wells | B0 mean loss | Full dual mean loss | Dual contribution to total score | Positive repeat contributions |
|---|---:|---:|---:|---:|---:|
| Raw scale fallback | 14 | 0.30654644 | 0.23166639 | +1.29422307 | 5/5 |
| Positive scale | 67 | 0.26869263 | 0.27896410 | -0.84961606 | 0/5 |
| Operating fraction below 0.8 | 32 | 0.34229016 | 0.31247257 | +1.17797894 | 5/5 |
| Other operating fraction | 49 | 0.23144431 | 0.24356739 | -0.73337193 | 1/5 |
| Recent oil ratio below 0.5 | 8 | 0.25011722 | 0.19352118 | +0.55897328 | 5/5 |
| Recent oil ratio 0.5–2 | 63 | 0.26676121 | 0.27689336 | -0.78805562 | 0/5 |
| Recent ratio unavailable | 10 | 0.34871618 | 0.29414735 | +0.67368934 | 5/5 |
| Chemical concentration/viscosity observed now | 53 | 0.24668424 | 0.26195119 | -0.99894805 | 0/5 |
| Chemical values missing one month | 18 | 0.31847941 | 0.28383545 | +0.76986572 | 5/5 |
| Chemical values missing two or more months | 10 | 0.34871618 | 0.29414735 | +0.67368934 | 5/5 |

The two chemical missingness dimensions have the same members. Their ten long-missing wells exactly equal the ten recent-production-ratio-unavailable wells in the completed no-fit overlap check. Thus chemical missingness and production state are confounded. The observations support examining production state and robustness; they do not prove missing chemical measurements cause the errors.

Counterexamples matter: five wells with latest BX outside 0–100 have B0 mean loss 0.21126689, lower than the within-range group 0.27071448. Their flag does not justify clipping values or dropping rows. The B0 recent oil-drop group is not intrinsically the highest-error group. Prior B0-prime diagnostics used the M-month ratio, a different cutoff and group definition; do not transfer that claim to B0 M−1.

The freshness candidate changed the long-missing chemical group's contribution by only +0.01530381 and the low-operating-fraction group's by +0.02389352 on average. Overall gain was +0.04498896, insufficient for the registered retention rule. Missing-memory alone has already been tested and is not an untried remedy.

The residual layer's harm to the full dual score is observed. Inferring that in-sample residual fitting caused overfitting requires a new controlled comparison; the aggregate evidence does not establish that causal explanation.

## Completed mechanisms that should not be repeated unchanged

| Prior experiment | Actual completed mechanism | Relevant result / limitation |
|---|---|---|
| A2B-022 | Exact duplicate feature removal | Fixed −0.459497; repeated mean −0.140818; 0/5 gains. Completed stop. |
| A2B-023 | Absolute log1p(RCYL) versus log1p(RCYL/scale), same B0 conditions | Fixed −0.970672286; repeated mean −0.513785843; 0/5 gains. Completed stop. |
| A2B-024 R2 | Whole-well fixed route: positive raw last oil uses scaled B0, fallback uses absolute-log arm | Research repeats +0.478484, but confirmation +0.04603297 and first-two-month −0.01198886; failed confirmation. Do not resurrect unchanged or call a new seed independent data. |
| A2B-035 R13 search | T0−1 ET/MultiOutput ET grids, 400/800 trees, leaf 2/4/6/10, feature fractions; target scales; response features R1–R5; fixed/inner fusion | Completed broad search. Its response features are related to proposed state features but use different cutoff/definitions. |
| R15 HX | History duration, count of measures/types, time since measure, conditionally cumulative oil | Not equivalent to the proposed 3/6-month production-state block. Fixed B0_HX 73.802319595, repeated mean approximately 72.35594 versus B0 72.47647. |
| R16 native | LightGBM/CatBoost, both cutoffs, weighted/unweighted | Completed; no compact ET200/depth8 found in this inspected matrix. |
| R17 | Fixed B0/B0-prime raw prediction fusions 70/30 and 50/50 | Completed and separately reviewed; local gain is not a platform-score guarantee. |
| Freshness v2 | Original325 plus ten legal missing-memory fields, unchanged ET400 | Completed; fixed −0.05222396; repeated mean +0.04498896; failed retention. |
| Light dual | Ridge alpha100 on 195 temporal columns plus HGB120 residual correction | Completed; fixed −1.74661190; repeated +0.44460701; failed stability. Ridge-only aggregates already available above. |

Key historical source locations:

- `D:/codex/A2B023_20261010_v1/delivery_v2/REPORT_B.md`
- `D:/codex/A2B024_20261012_v1/post_run/upload/REPORT_B.md`
- `D:/codex/A2B035_SEARCH_20261019_v1/PLAN_DAILY_SEARCH.json`
- `D:/codex/A2B035_SEARCH_20261019_v1/execution/RESULT_DAILY_SEARCH.json`
- `D:/codex/A2B035_R15_20261020_v1/source/routes15.py` (`hx_values`)
- `D:/codex/A2B035_R15_20261020_v1/source/base/guard035.py` (`response_features`)
- `D:/codex/A2B035_R15_20261020_v1/execution/FINAL_RESEARCH.json`
- `D:/codex/A2B035_R16_20261020_v2/execution/NATIVE_MATRIX_COMPLETE.json`

This is a scoped history check, not proof that no unprovided experiment exists. Prior R13 response features specifically used end-event month versus earlier months, pre-segment means, oil/liquid response, concentration response and month-normalized SCTS. They belong to the same mechanism family as production-state features, so novelty should be defined narrowly.

## At most three useful controlled mechanisms for the new batch

1. **Capacity control:** bounded-depth ET200 with the original325, contrasted against same-run B0. Keep target, cutoff, preprocessing, seed and split identities. This is a joint model-capacity policy (tree count and depth), not a claim isolating depth alone. No equivalent ET200/max_depth8 completed configuration was found in the inspected R13–R17 materials.
2. **Production-state representation:** exactly the same compact tree with a predeclared M−1-only state block. Compare it to the compact original325 tree, not just B0, so added-feature effect is identifiable. SCTS/calendar days, zero-production frequency and robust 3/6-month changes are supported as hypotheses by the observed state associations. Oil/liquid ratios are empirical ratios; do not assert physical water cut or correct daily oil by operating fraction without validated unit semantics. Require finite positive denominators, explicit missing indicators and no test-based thresholds.
3. **Temporal regularization and complementarity:** retain the existing 195 temporal-column definition, change only Ridge alpha100→1000, and report its own score beside the already available alpha100 ablation. A prespecified 75% state-tree +25% Ridge blend tests global complementarity without using validation labels to route or tune weights. The blend is an additional composition result, not a pure single-factor causal comparison. Do not revive HGB residual correction in the same batch.

Select and lock all definitions before new candidate scores. A new confirmation split on the same81 wells is another split, not independent new data. Stability needs both fixed/repeated performance and state-specific regressions; aggregate gain should not conceal systematic damage to the common positive-scale/operating group. Persist only anonymized grouped counts and contributions; per-well predictions and identities remain memory-only.
