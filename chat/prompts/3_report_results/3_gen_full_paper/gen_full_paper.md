# gen_full_paper — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `run_42Eo0dleXOQf` — Tail Risk in Dependency Distance: A Generalized Pareto Analysis Across 18 Language Treebanks
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_full_paper` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-07 08:02:27 UTC

````
<research_methodology>
Write like an experienced academic. Reviewers judge both the science and the writing.

- Claims must be proportional to evidence. Choose verbs carefully — "demonstrate," "observe," and "hypothesize" mean different things.
- Every result needs: what was measured, on what data, the numbers, and what they mean.
- Methodology must be specific enough to reproduce. Related work must be organized by theme, not a literature dump.
- State limitations honestly. Avoid both overclaiming and excessive hedging.
</research_methodology>

<system_reminder>
Do not ask follow up questions and do not ask the user anything. Execute all steps independently.
You must follow the todo list provided in each prompt exactly as written.
No placeholders, stubs, or incomplete code — all code must be complete and functional.
</system_reminder>

<process_isolation>
CRITICAL: Multiple pipeline runs may execute simultaneously on this machine. `ps aux | grep method.py` matches ALL runs, not just yours.
- NEVER kill processes by name (`killall`, `pkill -f`, `ps aux | grep ... | xargs kill`). This kills OTHER runs' processes.
- NEVER monitor processes by name (`ps aux | grep method.py`). You will see other runs' processes and get confused.
- ALWAYS use PID-based process management:
  Run: `uv run method.py & PID=$!` or `timeout <seconds> uv run method.py & PID=$!`
  Check: `kill -0 $PID 2>/dev/null && echo "Running" || echo "Ended"`
  Stop: `kill $PID`
  Wait: `wait $PID; echo "Exit code: $?"`
  Monitor: `tail -f logs/run.log & TAIL_PID=$!` then `kill $TAIL_PID` when done
</process_isolation>

<workspace>
Your workspace: `/ai-inventor/aii_data/runs/run_42Eo0dleXOQf/4_gen_paper_repo/_4_assemble_paper/paper/workspace`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_42Eo0dleXOQf/4_gen_paper_repo/_4_assemble_paper/paper/workspace/`:
GOOD: `/ai-inventor/aii_data/runs/run_42Eo0dleXOQf/4_gen_paper_repo/_4_assemble_paper/paper/workspace/file.py`, `/ai-inventor/aii_data/runs/run_42Eo0dleXOQf/4_gen_paper_repo/_4_assemble_paper/paper/workspace/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>

<task>
Create a publication-ready top-conference LaTeX paper with BibTeX from <paper_text> and <available_figures>, compile to PDF.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<paper_text>
title: >-
  Tail Risk in Dependency Distance: A Generalized Pareto Analysis Across 18 Language Treebanks
abstract: >-
  Dependency distance minimization (DDM) is the observation that speakers arrange words to keep syntactic dependencies short;
  it has been documented across 37+ languages using mean dependency distance (MDD) as the summary statistic. This work investigates
  whether the linguistically consequential measure is instead the tail of the dependency-length distribution, characterized
  via extreme value theory. Fitting Generalized Pareto Distributions to sentence-length-normalized dependency distances in
  18 Universal Dependencies treebanks (558,144 arcs across 33,030 sentences, 8 language families), we extract a tail-risk
  shape parameter ξ. We find that ξ carries information about typology independent of MDD: ξ correlates with head-finality
  syntax more strongly than MDD does (partial ρ = −0.55 vs −0.29), and generalizes across families in leave-one-family-out
  cross-validation (RMSE 0.067 vs MDD's 0.51). Register (spoken vs. written) shows directionally consistent effects on ξ at
  the matched-pair level (3 of 4 language pairs, Wilcoxon p < 0.01 after Holm correction), but does not reach significance
  in population-level univariate correlation (ρ = −0.52, p_Holm = 0.27), and the effect reverses at higher percentile thresholds,
  suggesting threshold sensitivity. Comparison to power-law tail exponents (α) shows ξ and α are reciprocal parameterizations
  (r = −0.73) yet ξ predicts register better in mixed-effects models (AICc 26.7 vs 63.4). The results establish ξ as a new,
  robust typological statistic for characterizing dependency distributions, though register effects remain mixed and require
  further investigation with larger matched-pair samples.
paper_text: "# Tail Risk in Dependency Distance: A Generalized Pareto Analysis Across 18 Language Treebanks\n\n## Abstract\n\
  \nDependency distance minimization (DDM) is the observation that speakers arrange words to keep syntactic dependencies short;\
  \ it has been documented across 37+ languages using mean dependency distance (MDD) as the summary statistic. This work investigates\
  \ whether the linguistically consequential measure is instead the tail of the dependency-length distribution, characterized\
  \ via extreme value theory. Fitting Generalized Pareto Distributions to sentence-length-normalized dependency distances\
  \ in 18 Universal Dependencies treebanks (558,144 arcs across 33,030 sentences, 8 language families), we extract a tail-risk\
  \ shape parameter ξ. We find that ξ carries information about typology independent of MDD: ξ correlates with head-finality\
  \ syntax more strongly than MDD does (partial ρ = −0.55 vs −0.29), and generalizes across families in leave-one-family-out\
  \ cross-validation (RMSE 0.067 vs MDD's 0.51). Register (spoken vs. written) shows directionally consistent effects on ξ\
  \ at the matched-pair level (3 of 4 language pairs, Wilcoxon p < 0.01 after Holm correction), but does not reach significance\
  \ in population-level univariate correlation (ρ = −0.52, p_Holm = 0.27), and the effect reverses at higher percentile thresholds,\
  \ suggesting threshold sensitivity. Comparison to power-law tail exponents (α) shows ξ and α are reciprocal parameterizations\
  \ (r = −0.73) yet ξ predicts register better in mixed-effects models (AICc 26.7 vs 63.4). The results establish ξ as a new,\
  \ robust typological statistic for characterizing dependency distributions, though register effects remain mixed and require\
  \ further investigation with larger matched-pair samples.\n\n## 1. Introduction\n\nDependency distance is the linear distance\
  \ between a word and its syntactic head. This measure plays a central role in theories of language comprehension, production,\
  \ and evolution. Futrell, Mahowald, and Gibson's landmark 2015 study documented dependency distance minimization (DDM) across\
  \ 37 languages: actual sentences have shorter mean dependency distances than random word orders, a pattern interpreted as\
  \ evidence that speakers minimize cognitive load during production and comprehension [1]. This finding motivated theories\
  \ linking syntactic structure to working memory constraints [2], and has been applied to typological prediction, historical\
  \ language change, and the emergence of linguistic universals [3].\n\nYet nearly all DDM research, including the most recent\
  \ large-scale UD-based studies, summarizes dependency-length distributions using their mean or median. This central-tendency\
  \ focus assumes that speakers optimize typical sentences. An alternative hypothesis emerges from cognitive theory: working\
  \ memory failures are threshold phenomena. Once a dependency's integration cost exceeds an individual's capacity or a neurocognitive\
  \ decay window closes, comprehension breaks down. It is not gradual, but abrupt. If this is true, speakers should prioritize\
  \ suppressing catastrophic long dependencies even when doing so conflicts with minimizing mean distance. Under this logic,\
  \ the linguistically consequential quantity is not the average dependency length, but how fast the probability of an extreme\
  \ dependency decays.\n\n**The Theoretical Prediction.** If spoken language production is more constrained by real-time cognitive\
  \ resources than written language, we predict that spoken registers will exhibit lighter, more bounded tails in their dependency-length\
  \ distributions. This means fewer catastrophic-length dependencies even when mean distances are similar. This would manifest\
  \ as a more negative shape parameter in an extreme-value-theory tail model, indicating that the upper bound on feasible\
  \ dependencies is tighter in speech.\n\nExtreme value theory (EVT) was developed precisely to quantify this tail behavior.\
  \ The Generalized Pareto Distribution (GPD), fitted via peaks-over-threshold (POT) methods, parameterizes the tail's weight\
  \ via a shape parameter ξ. Values are interpreted as follows: ξ > 0 indicates heavy (power-law-like) tails with unbounded\
  \ maximum dependencies; ξ = 0 indicates exponential decay; ξ < 0 indicates a bounded tail with a hard upper limit. This\
  \ framework has been standard in finance, hydrology, and reliability engineering for 30+ years but has been largely absent\
  \ from linguistics.\n\nA related set of findings motivates the empirical work. Ferrer-i-Cancho and colleagues established\
  \ over two decades that dependency distances in many languages follow power-law or exponential distributions [4], not uniform\
  \ or normal distributions [5]. However, this prior work characterized whole-distribution shapes (power law vs. lognormal)\
  \ and did not examine how tail heaviness (parameterized via power-law exponent α or GPD shape ξ) varies by register or typology.\
  \ Additionally, power-law exponent α and GPD shape parameter ξ are mathematically reciprocal for the same tail data (α ≈\
  \ 1/ξ), raising the question of whether ξ offers genuinely new information or merely reparameterizes existing findings [6].\n\
  \n**This Study's Contributions.** (1) We introduce ξ, the Generalized Pareto tail-risk shape parameter, as an orthogonal\
  \ descriptor of dependency distributions, with strong typological correlates (head-finality effects 1.9× stronger than for\
  \ MDD). (2) We test the hypothesis that spoken language exhibits lighter tails, finding directional consistency at the matched-pair\
  \ level (3 of 4 pairs significant after Holm correction) but population-level insignificance and threshold sensitivity.\
  \ (3) We directly compare ξ to power-law α, establishing that ξ predicts register better in regression models despite high\
  \ mathematical correlation. (4) We adapt EVT machinery to linguistics in close collaboration with established methods (mixed-effects\
  \ models, permutation baselines), rather than introducing an entirely new framework.\n\n[FIGURE:fig_evt_illustration]\n\n\
  ## 2. Methods\n\n### 2.1 Data and Sample\n\nWe analyze Universal Dependencies version 2.18 treebanks from the HuggingFace\
  \ repository (commul/universal_dependencies). Selection criteria: (a) minimum 500 sentences to support stable arc-length\
  \ distributions; (b) publicly available in UD format; (c) documented register labels where possible. The final dataset comprises\
  \ 18 treebanks spanning 18 languages in 8 language families (Indo-European, Afro-Asiatic, Japonic, Sino-Tibetan, Koreanic,\
  \ Uralic, Turkic, creoles), covering 33,030 sentences and 558,144 dependency arcs. Four treebanks are matched spoken/written\
  \ pairs within the same language: Slovenian (SST spoken / SSJ written, n=1829 + 1904 sentences), French (Rhapsodie spoken\
  \ / GSD written, n=2059 + 1998 sentences), English (ESLSpok non-native learner speech / EWT written web, n=1856 + 1913 sentences),\
  \ and Turkish (ATIS task-oriented speech / IMST written news, n=8640 + 2800 sentences). The remaining 14 treebanks are typologically\
  \ diverse written or mixed-register samples (Arabic PADT, Japanese GSD, Korean GSD, Hindi HDTB, Finnish TDT, Chinese GSD,\
  \ Russian SynTagRus, Nigerian Pidgin, Neapolitan). This design allows isolation of register effects from cross-language\
  \ confounds while scaling typological coverage.\n\n### 2.2 Dependency Distance and Normalization\n\nFor each sentence, we\
  \ extracted all arcs from the CoNLL-U head column, computing dependency distance as the absolute linear position difference\
  \ (|head_position − dependent_position|), 1-indexed, excluding the artificial ROOT arc. To control for sentence length (longer\
  \ sentences mechanically permit longer arcs), we normalized each distance by sentence length: DD_norm = DD / sentence_length.\
  \ This approach follows standard practice in DDM research and matches the normalization used in recent typological studies\
  \ [7].\n\n### 2.3 Extreme Value Estimation: Peaks-Over-Threshold\n\nFor each treebank, we fitted a Generalized Pareto Distribution\
  \ to the upper tail of normalized dependency distances via the peaks-over-threshold method [8]:\n\n1. **Threshold Selection:**\
  \ We used mean-residual-life (MRL) plots to identify where the empirical mean excess becomes approximately linear. We then\
  \ evaluated thresholds at the 75th, 80th, and 90th percentiles of the normalized distance distribution and report results\
  \ primarily at the 75th percentile with sensitivity analysis for the others.\n\n2. **Parameter Estimation:** For all exceedances\
  \ above the threshold, we estimated the scale (σ) and shape (ξ) parameters via maximum likelihood using scipy.stats.genpareto\
  \ [9]. Interpretation of ξ: values ξ < 0 indicate a bounded distribution with maximum dependency distance; ξ = 0 indicates\
  \ exponential decay (no power law); ξ > 0 indicate heavy, unbounded tails. Formally, the probability of exceeding a distance\
  \ x above threshold u is P(X > x | X > u) ∝ (1 + ξ · x/σ)^{−1/ξ} [9].\n\n3. **Confidence Intervals:** We generated 1000\
  \ bootstrap resamples (seed=20260907) to compute 95% confidence intervals on ξ.\n\n### 2.4 Power-Law Baseline: Comparison\
  \ to Power-Law Exponent\n\nTo establish the novelty of ξ over existing tail-risk measures from the linguistics literature,\
  \ we also fitted a power-law tail model to each treebank [4]. Following Clauset et al. (2009), we identified the x_min threshold\
  \ that minimizes the Kolmogorov-Smirnov distance between the empirical and fitted cumulative distributions, then estimated\
  \ the exponent α via MLE: α̂ = 1 + n / Σ(ln(x_i / x_min)). Mathematically, power-law exponent α and GPD shape parameter\
  \ ξ satisfy α ≈ 1/ξ when both are fitted to the same tail data [6, 8], making them reciprocal parameterizations rather than\
  \ independent descriptors. We therefore computed both for direct comparison.\n\n### 2.5 Within-Language Register Comparisons\n\
  \nFor the four language pairs with both spoken and written treebanks, we performed two paired analyses:\n\n1. **Decile-Level\
  \ Wilcoxon Test (Corrected for Pseudo-Replication):** We partitioned sentences into 10 length-matched deciles within each\
  \ register, then paired deciles across registers. For each paired decile, we computed the mean normalized dependency distance,\
  \ yielding n=10 paired observations per language pair. We ran a Wilcoxon signed-rank test on these 10 pairs, with Holm-Bonferroni\
  \ correction across the 4 language pairs (α_corrected = 0.0125). This avoids the pseudo-replication error of treating 209k\
  \ non-independent arcs as 39 independent observations.\n\n2. **Treebank-Level ξ Comparison:** We fitted ξ separately for\
  \ each register and computed a paired t-test across the 4 matched pairs (n=4 language pairs, not individual sentences).\n\
  \n### 2.6 Mixed-Effects Models\n\nWe fitted linear mixed-effects models with treebank-level ξ as the outcome, register and\
  \ typological features as fixed effects, and language family as a random intercept. Given that 8 families span only 18 treebanks,\
  \ most random-intercept models exhibit singular fits. We report models that converge with a non-zero family variance; others\
  \ are presented as fixed-effects-only OLS with family variance forced to zero and flagged as such. This follows best practice\
  \ for small random-effects structures [10].\n\nPrimary models:\n- Model 1: ξ ~ MDD + (1 | family)\n- Model 2: ξ ~ MDD +\
  \ register + (1 | family)  \n- Model 3: MDD ~ register + (1 | family)\n\nWe also fitted univariate models predicting register\
  \ (binary: spoken=1, written=0) from ξ and α separately, and jointly, comparing via AICc and Akaike weights.\n\n### 2.7\
  \ Typological Features and Predictors\n\nTypological features included: (1) empirical head-finality ratio (fraction of arcs\
  \ where the head word follows the dependent, computed directly from each treebank); (2) word-order flexibility (entropy-based\
  \ measure of positional variation); (3) Grambank v1.0.3 morphosyntactic features (case richness, tense availability, agreement\
  \ marking), matched by language. Grambank values are language-level (not treebank-level) and thus shared across both registers\
  \ of the same language.\n\n### 2.8 Cross-Validation\n\nLeave-One-Family-Out cross-validation (LOFO): We trained mixed-effects\
  \ models on data from 7 families, predicted ξ and MDD for the held-out family (1–3 treebanks), and computed macro RMSE and\
  \ MAPE. We report the 95% bootstrap confidence interval on these metrics.\n\n### 2.9 Sensitivity and Robustness\n\nSensitivity\
  \ analyses included: (1) excluding flat/list/conj/appos arc types and re-fitting ξ to test annotation-choice robustness;\
  \ (2) excluding treebanks with <1000 arcs (Nigerian Pidgin: 20 sentences); (3) fitting ξ at 75th, 80th, and 90th percentile\
  \ thresholds and reporting correlations between estimates and directions of register effects across thresholds.\n\n## 3.\
  \ Results\n\n### 3.1 Register Effects on Tail Index: Matched-Pair Analysis\n\nApplying the corrected decile-level Wilcoxon\
  \ test across four languages:\n\n- **Slovenian (SST/SSJ)**: Wilcoxon Z = −2.60, p_raw = 0.0093, p_Holm = 0.028, effect size\
  \ r = −0.82. Spoken language shows lighter tails (lower normalized distance). Mean difference: Δ = −0.013.\n- **French (Rhapsodie/GSD)**:\
  \ Wilcoxon Z = −2.80, p_raw = 0.0051, p_Holm = 0.020, r = −0.89. Spoken lighter. Δ = −0.017.\n- **English (ESLSpok/EWT)**:\
  \ Wilcoxon Z = −1.27, p_raw = 0.203, p_Holm = 0.405 (NOT significant). r = −0.40. Mean Δ = +0.008 (opposite direction).\n\
  - **Turkish (ATIS/IMST)**: Wilcoxon Z = −0.78, p_raw = 0.441, p_Holm = 0.441 (NOT significant). r = −0.26. Mean Δ = −0.001.\n\
  \n**Paired t-test on ξ across all four languages (treating each language pair as one observation):** t(3) = −1.885, p =\
  \ 0.156. The effect is not significant at the language level despite directional consistency in 3 of 4 pairs.\n\n[FIGURE:fig_register_paired_wilcoxon]\n\
  \n### 3.2 Register Effects: Population-Level Correlation\n\nAmong the 15 treebanks where both registers are present (4 matched\
  \ pairs + 7 additional language families with only one register per language represented), we computed Spearman correlations\
  \ between register and ξ. Result: ρ = −0.523, p = 0.045. After Holm-Bonferroni correction for multiple testing across 6\
  \ typological correlations, p_Holm = 0.272 (NOT significant). The same analysis on MDD (controlling for register) shows\
  \ register is NOT a significant univariate predictor of MDD (ρ = 0.104, p = 0.677), establishing that ξ and MDD respond\
  \ differently to register but neither univariately dominates.\n\n### 3.3 Comparison of ξ to Power-Law Exponent α\n\nWe fitted\
  \ power-law tails to the same threshold-exceeding data, obtaining exponent α for each treebank. The mathematical expectation\
  \ is α ≈ 1/ξ [6].\n\n**Empirical Correlation:** ξ and α are strongly negatively correlated (Spearman ρ = −0.728, p = 0.0009,\
  \ 95% CI [−0.895, −0.380]). The Pearson r² = 0.49, indicating substantial shared variance but not complete redundancy.\n\
  \n**Model Comparison for Register Prediction:** \n- Model (ξ-only): AICc = 26.73, Akaike weight = 1.000 (massively dominant)\n\
  - Model (α-only): AICc = 63.44, Akaike weight = 1.06 × 10^−8  \n- Model (ξ + α jointly): AICc = 81.55, Akaike weight < 10^−12\n\
  \nξ alone predicts register far better than α, and adding α to ξ worsens the fit. However, this superiority may reflect\
  \ ξ's greater flexibility (continuous values spanning −0.5 to +0.8 across treebanks, vs. α's narrower range), not genuine\
  \ independence from α.\n\n**Power-Law Fit Comparison:** Across 18 treebanks, we compared the goodness-of-fit (via AIC) between\
  \ GPD and power-law models. Result: power-law fitting achieved better fit in 12 of 18 treebanks (67%), GPD in 6 of 18. This\
  \ suggests the two-regime model recently proposed by Petrini & Ferrer-i-Cancho (2022), which switches between exponential\
  \ and power-law regimes around a 4–5 word breakpoint, may be more appropriate [4].\n\n### 3.4 Typological Correlations and\
  \ Generalization\n\nHead-finality (empirical, computed from each treebank): \n- Marginal correlation with ξ: ρ = −0.512,\
  \ p = 0.036\n- Partial correlation (controlling for register and word-order flexibility): ρ = −0.547, p = 0.023\n\nHead-finality\
  \ correlation with MDD: \n- Marginal: ρ = −0.278, p = 0.267\n- Partial: ρ = −0.294, p = 0.236\n\n**ξ's head-finality effect\
  \ is 1.9× stronger than MDD's.** Head-final languages (OV word order, heads follow dependents) show lower ξ, indicating\
  \ heavier tails and longer upper-tail dependencies, consistent with the hypothesis that rigid canonical order trades off\
  \ against long-distance movement when necessary [11].\n\nLeave-One-Family-Out cross-validation (n=8 family-level folds):\n\
  - **ξ generalization:** Macro RMSE = 0.067 (95% CI [0.043, 0.091]), MAPE = 77.1%\n- **MDD generalization:** Macro RMSE =\
  \ 0.510 (95% CI [0.330, 0.688]), MAPE = 18.4%\n\nξ generalizes better than MDD in absolute error but has higher percentage\
  \ error (reflecting ξ's smaller scale). Per-family RMSE for ξ ranges from 0.024 (Japonic, n=1 treebank) to 0.120 (Turkic,\
  \ n=3 treebanks).\n\n[FIGURE:fig_lofo_validation]\n\n### 3.5 Threshold Sensitivity and Effect Reversals\n\nThe register\
  \ effect on ξ is sensitive to the POT threshold:\n\n| Percentile Threshold | ρ(ξ, register) | p-value | Direction |\n|---|---|---|---|\n\
  | 75th (primary) | −0.523 | 0.045 | Spoken lower ξ |\n| 80th | −0.384 | 0.137 | Spoken lower ξ |\n| 90th | +0.035 | 0.895\
  \ | Spoken higher ξ |\n\nAt the 90th percentile (deepest tail), the register effect reverses sign and becomes negligible.\
  \ This suggests that the phenomenon driving register differences (if any) operates in the moderate-to-high tail, not the\
  \ extreme tail. For α, the effect sign also shifts across thresholds but remains non-significant throughout (Holm-corrected).\n\
  \n### 3.6 Robustness Checks\n\nExcluding flat/list/conj/appos arc types: ξ estimates change by mean ±15.3% compared to the\
  \ full dataset, while MDD changes by ±2.0%. This indicates that annotation-segmentation choices affect tail estimates more\
  \ than central-tendency statistics, a limitation acknowledged below.\n\nExcluding treebanks with <1000 arcs (N=1: Nigerian\
  \ Pidgin): Register correlations strengthen slightly (ρ_ξ = 0.078 → 0.433), suggesting that small-sample tail estimates\
  \ introduce noise.\n\n## 4. Discussion\n\n### 4.1 ξ as a New Typological Statistic\n\nThe Generalized Pareto shape parameter\
  \ ξ proves to be a linguistically meaningful, typologically structured descriptor of dependency-length distributions, orthogonal\
  \ to mean dependency distance. The stronger head-finality correlation for ξ versus MDD (1.9× effect-size difference) suggests\
  \ that tail shape and central tendency are shaped by distinct mechanisms. One possibility: speakers allocate resources to\
  \ minimize frequent, typical dependencies (affecting the mean), while separately suppressing rare catastrophic dependencies\
  \ through information-structural and syntactic constraints specific to each language's canonical order [11]. Head-final\
  \ languages, which rigidly place heads after dependents, may rely on selective long-distance movement to preserve informational\
  \ flow, thus exhibiting heavier, longer-range tails [12].\n\n### 4.2 Register Effects: Directional Consistency but Population\
  \ Insignificance\n\nThe matched-pair analysis reveals directional consistency at the language level: 3 of 4 pairs show spoken\
  \ language with lower tail indices (lighter tails). Slovenian and French reach significance even after multiple-comparison\
  \ correction (p_Holm < 0.03), suggesting a genuine effect. However, this effect does not emerge robustly at the population\
  \ level. The univariate correlation (ρ = −0.52, p_Holm = 0.27) remains non-significant, and the paired t-test across the\
  \ four languages is far from significance (p = 0.156, 95% CI includes zero).\n\nThis discrepancy likely reflects two confounds:\
  \ (1) **Sample heterogeneity.** The four matched pairs span vastly different genres and annotation schemes (task-oriented\
  \ dialogue, conversational interviews, learner speech, news writing), making them not truly exchangeable. Turkish ATIS contains\
  \ highly structured task-specific utterances, while Slovenian SST contains naturalistic conversation; these genre effects\
  \ may overwhelm register effects. (2) **Register label coarseness.** UD metadata often conflates several types of speech:\
  \ read transcriptions, interviews, and spontaneous speech may all fall under \"spoken,\" yet the cognitive constraints differ.\n\
  \nThe register effect's reversal at the 90th percentile is a critical caveat. If the effect were robust, it should strengthen\
  \ in the deepest tail (where memory constraints bite hardest). Instead, the effect disappears, suggesting that spoken vs.\
  \ written differences operate in the moderate tail, not in extreme outliers. This partially disconfirms the memory-load\
  \ hypothesis in its simplest form.\n\n### 4.3 Comparison to Power-Law Models\n\nξ and power-law exponent α are reciprocal\
  \ parameterizations (α ≈ 1/ξ) with high empirical correlation (ρ = −0.728), meaning they capture mathematically equivalent\
  \ tail behavior. Despite this near-equivalence, ξ predicts register better in regression models (AICc 26.7 vs 63.4). Why?\
  \ ξ likely has lower variance in estimation or greater flexibility in the regression framework, but this does not establish\
  \ it as a genuinely novel linguistic statistic, merely as a superior parameterization for the same underlying phenomenon.\n\
  \nA more sobering finding: power-law fitting actually achieved better goodness-of-fit than GPD in 12 of 18 treebanks (67%).\
  \ This suggests the two-regime model by Petrini & Ferrer-i-Cancho (2022), which switches between exponential and power-law\
  \ regimes around a 4–5 word breakpoint, may be more appropriate. If true, focusing on either pure power law or pure GPD\
  \ misses the mechanism. Future work should test whether the register effect manifests differently in the exponential versus\
  \ power-law regimes.\n\n### 4.4 Limitations\n\n**Annotation heterogeneity.** Flat/list/conj/appos arc handling varies significantly\
  \ across UD treebanks [13]. Our sensitivity analysis shows ξ estimates are 7.5× more sensitive to these choices than MDD\
  \ (±15% vs ±2%). This raises the possibility that some register-level ξ differences reflect annotator choices rather than\
  \ true linguistic variation. A partial solution: future work should standardize segmentation or re-annotate using a unified\
  \ scheme.\n\n**Small matched-pair sample.** Only 4 language pairs with both registers have sufficient annotations. Languages\
  \ differ in language family (two Indo-European, one Turkic), genre (task-oriented vs. conversational), and register definition.\
  \ Generalizing to a universal \"spoken lighter-tail\" effect requires larger, more homogeneous samples.\n\n**Treebank size\
  \ confound.** Smallest treebanks (Nigerian Pidgin, 20 sentences) cannot support stable tail estimates. Although we report\
  \ sensitivity checks excluding them, the primary analysis includes them. LOFO results show per-family RMSE varies more than\
  \ 5-fold, suggesting that treebank-level variation in sample size and annotation quality dominates family-level effects.\n\
  \n**Threshold selection.** The choice of 75th percentile threshold is somewhat arbitrary. Our sensitivity analysis shows\
  \ ξ and its register effect are threshold-dependent, reversing sign at the 90th percentile. This fragility suggests that\
  \ the POT approach, while mathematically elegant, may be sensitive to implementation choices in applied linguistic settings.\n\
  \n**Correlational, not causal inference.** All results are observational. We cannot infer whether head-finality causes tail\
  \ shape, whether register differences reflect production constraints vs. genre conventions, or whether cognitive memory\
  \ limitations drive the patterns. Experimental manipulation or computational modeling (e.g., simulating language production\
  \ under memory constraints) would strengthen causal claims.\n\n### 4.5 Contribution to Theory and Practice\n\n**For Cognitive\
  \ Theory.** Our work reframes DDM from a central-tendency optimization (\"minimize mean distance to reduce load\") to a\
  \ risk-management framework (\"suppress catastrophic dependencies\"). The evidence is partially supportive: spoken registers\
  \ do show lighter tails in 3 of 4 pairs, and typology predicts tail shape. However, the effects are modest, threshold-sensitive,\
  \ and do not hold at population scale, suggesting memory constraints are one among several pressures on dependency syntax.\n\
  \n**For Quantitative Typology.** The tail-risk shape parameter ξ is a new, measurable dimension of language design. Its\
  \ stronger typological correlates (especially head-finality) position it as a useful tool for characterizing linguistic\
  \ diversity. Future work should apply ξ to other syntactic phenomena (argument-structure distributions, anaphora-resolution\
  \ distance) and typological questions (morphological complexity, information-structural rigidity).\n\n**For Extreme-Value\
  \ Theory in Linguistics.** We demonstrate that EVT machinery, developed for finance and hydrology, can be transplanted to\
  \ linguistics. However, the mathematical reciprocal relationship between α and ξ, combined with power-law models outfitting\
  \ GPD models in 67% of cases, suggests that existing power-law frameworks may already capture the essential information.\
  \ The value of EVT may lie not in ξ per se, but in the conceptual reframing of syntax as optimizing edge cases rather than\
  \ averages.\n\n## 5. Conclusion\n\nWe demonstrate that the Generalized Pareto shape parameter ξ is a new, theoretically\
  \ motivated, and empirically robust descriptor of dependency-length distributions. It correlates with head-finality more\
  \ strongly than mean dependency distance and generalizes across language families (LOFO RMSE 0.067). Register effects are\
  \ directionally consistent at the matched-pair level (3 of 4 pairs significant, p < 0.03 after Holm correction) but do not\
  \ reach significance at the population level (p_Holm = 0.27) and reverse at extreme-tail quantiles, suggesting threshold\
  \ sensitivity and genre confounds.\n\nThe tail-risk framework reorients DDM research toward questions about edge cases and\
  \ risk management, offering new perspectives on language typology. However, the finding that power-law models fit better\
  \ than GPD in most treebanks suggests that the Petrini & Ferrer-i-Cancho two-regime model may be more appropriate for future\
  \ work.\n\n**Future Directions:** (1) Expand register sampling to include matched-pair treebanks in more language families,\
  \ with controlled genres (e.g., conversational speech and formal news writing in the same languages). (2) Test whether ξ\
  \ differences at the matched-pair level reflect production constraints (real-time memory) or genre conventions (formal writing\
  \ norms), via psycholinguistic experiments (e.g., reading-time studies of sentences with various tail-risk profiles). (3)\
  \ Examine whether the two-regime exponential/power-law model accounts for register-by-family interactions better than single-regime\
  \ GPD or power-law fits. (4) Apply the tail-risk framework to other syntactic phenomena (argument structure, coordination\
  \ scope, anaphora distance) to test whether the risk-management hypothesis generalizes beyond dependency distance.\n\n##\
  \ Acknowledgments\n\nWe thank the Universal Dependencies maintainers for curating and releasing the UD v2.18 treebanks,\
  \ and the Grambank and WALS projects for making typological features freely available. We acknowledge helpful feedback from\
  \ Kaja Dobrovoljc (Ljubljana) on Slovenian and spoken language annotation practices. Computational resources were provided\
  \ by [institution]. All code and analysis artifacts are available at [repository].\n\n## References\n\n[1] Futrell, R.,\
  \ Mahowald, K., & Gibson, E. (2015). Large-scale evidence of dependency length minimization in 37 languages. *Proceedings\
  \ of the National Academy of Sciences*, 112(33), 10336–10341.\n\n[2] Lewis, R. L., & Vasishth, S. (2005). An activation-based\
  \ model of sentence processing as skilled memory retrieval. *Cognitive Science*, 29(3), 375–419.\n\n[3] Liu, H., Xu, C.,\
  \ & Liang, J. (2017). Dependency distance: A new perspective on syntactic patterns in natural languages. *Physics of Life\
  \ Reviews*, 21, 171–193.\n\n[4] Petrini, K., & Ferrer-i-Cancho, R. (2025). Distribution of syntactic dependency distances\
  \ across 20 languages. *Glottometrics*, [volume/issue], [pages]. arXiv:2211.14620.\n\n[5] Ferrer-i-Cancho, R. (2004). Patterns\
  \ in syntactic dependency networks. *Physical Review E*, 69(5), 051915.\n\n[6] Clauset, A., Shalizi, C. R., & Newman, M.\
  \ E. (2009). Power-law distributions in empirical data. *SIAM Review*, 51(4), 661–703.\n\n[7] Temperley, D., & Gildea, D.\
  \ (2018). Minimizing syntactic dependency lengths: Typological/cognitive universal? *Annual Review of Linguistics*, 4, 1–15.\n\
  \n[8] Beirlant, J., Goegebeur, Y., Segers, J., & Teugels, J. L. (2004). *Statistics of extremes: Theory and applications*.\
  \ John Wiley & Sons.\n\n[9] SciPy Documentation: scipy.stats.genpareto. Retrieved from https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html\n\
  \n[10] Bates, D., Kliegl, R., Vasishth, S., & Baayen, H. (2018). Parsimonious mixed models. *arXiv*, 1506.04967.\n\n[11]\
  \ Hawkins, J. A. (1994). *A performance theory of order and constituency*. Cambridge University Press.\n\n[12] Gildea, D.,\
  \ & Temperley, D. (2010). Do grammars minimize dependency length? *Cognitive Science*, 34(2), 286–310.\n\n[13] de Marneffe,\
  \ M. C., & Nivre, J. (2019). Dependency grammar. *Annual Review of Linguistics*, 5, 1–16.\n\n[14] Dryer, M. S., & Haspelmath,\
  \ M. (Eds.). (2013). *The world atlas of language structures online*. Max Planck Institute for Evolutionary Anthropology.\
  \ https://wals.info/\n\n[15] Dobrovoljc, K., Erjavec, T., & Krek, S. (2017). The Universal Dependencies Treebank for Slovenian.\
  \ In *Proceedings of the Sixth Workshop on Balto-Slavic Natural Language Processing* (pp. 33–38). Association for Computational\
  \ Linguistics."
summary: >-
  This paper establishes the Generalized Pareto shape parameter ξ as a new, robust typological statistic for characterizing
  dependency-length distributions across 18 UD treebanks. ξ carries orthogonal information to mean dependency distance, correlates
  with head-finality typology 1.9× more strongly, and generalizes well across language families (LOFO RMSE 0.067). Register
  (spoken vs. written) effects are directionally consistent at the matched-pair level (3 of 4 pairs significant after Holm
  correction) but do not reach population-level significance (p=0.27 Holm-corrected) and reverse at higher percentile thresholds,
  indicating threshold sensitivity and genre confounds. Comparison to power-law exponents shows ξ predicts register better
  in regression models despite high mathematical correlation (α ≈ 1/ξ). However, power-law models actually fit the data better
  in 12 of 18 treebanks, suggesting that two-regime models may be more appropriate. The work reframes dependency-distance
  minimization as both a central-tendency and risk-management phenomenon, with honest acknowledgment of limitations and caveats.
</paper_text>

<available_figures>
--- Item 1 ---
id: fig_evt_illustration
figure_type: concept
title: 'Extreme Value Theory: Bounded vs Unbounded Tails'
caption: >-
  Illustration of the Generalized Pareto Distribution shape parameter ξ and its interpretation. Left: ξ < 0 (bounded tail,
  hard maximum on dependency distance, typical of tightly structured languages). Center: ξ = 0 (exponential decay, no power-law
  behavior). Right: ξ > 0 (unbounded power-law tail, possibility of very long dependencies, typical of flexible-order languages).
  The shape parameter directly captures tail heaviness independent of mean distance.
image_gen_detailed_description: >-
  Three side-by-side probability-density curves showing dependency distance on the x-axis (0 to 1.2 on normalized scale) and
  probability density on y-axis. Left panel labeled 'ξ < 0 (Bounded)' shows a curve that rises sharply then cuts off abruptly
  at x=0.6, with vertical line marking hard ceiling. Center panel labeled 'ξ = 0 (Exponential)' shows smooth exponential decay
  from 1.0 to near-zero over the range. Right panel labeled 'ξ > 0 (Power Law)' shows a curve that decays slowly, maintaining
  non-zero probability far out the tail (x>1.0). Use distinct colors: blue for bounded, green for exponential, red for power-law.
  Add legend explaining ξ parameter values and linguistic interpretation (memory constraints vs flexibility).
aspect_ratio: '16:9'
summary: >-
  Conceptual diagram showing how the GPD shape parameter ξ characterizes tail behavior from bounded (memory-constrained) to
  unbounded (flexible) extremes.
figure_path: figures/fig_evt_illustration_v0.jpg

--- Item 2 ---
id: fig_register_paired_wilcoxon
figure_type: data
title: 'Register Effects on Tail Index: Corrected Paired Analysis'
caption: >-
  Decile-level Wilcoxon signed-rank test results across four matched spoken/written language pairs. Shown are raw p-values,
  Holm-corrected significance thresholds, and effect sizes (Spearman r). Slovenian and French reach significance after multiple-comparison
  correction (p_Holm < 0.03); English and Turkish are non-significant. Error bars show 95% confidence intervals on the mean
  normalized dependency distance difference (spoken minus written). The paired t-test across all four languages yields p=0.156
  (not significant), indicating the effect does not generalize to the population level.
image_gen_detailed_description: >-
  Four-panel horizontal layout, one per language (Slovenian, French, English, Turkish). Each panel shows: (1) A bar centered
  at 0, extending left/right to show mean normalized distance difference (spoken - written), with 95% CI error bars; (2) Horizontal
  line at y=0 as reference; (3) Point on bar labeled with p_raw and p_Holm values above/below; (4) Significance asterisk or
  'ns' label. Use green bars for p_Holm < 0.05 (Slovenian, French), red/grey for non-significant (English, Turkish). Y-axis
  label 'Mean normalized distance (spoken - written)' from -0.025 to +0.015. X-axis categorical. Add text box at bottom stating
  'Paired t-test (n=4 pairs): t=-1.885, p=0.156'.
aspect_ratio: '16:9'
summary: >-
  Decile-matched paired comparison of spoken and written registers across four languages, showing directional consistency
  but non-significant population-level effect.
figure_path: figures/fig_register_paired_wilcoxon_v0.pdf

--- Item 3 ---
id: fig_lofo_validation
figure_type: data
title: 'Cross-Family Generalization: Leave-One-Family-Out RMSE'
caption: >-
  Leave-one-family-out cross-validation performance for tail-index ξ versus mean dependency distance (MDD). Each of 8 family-level
  folds is shown as a point; error bars reflect 95% bootstrap confidence intervals on macro RMSE. ξ achieves substantially
  lower absolute error (RMSE 0.067) than MDD (0.510), demonstrating better cross-family generalization. Per-family RMSE for
  ξ ranges 0.024–0.120, indicating variable stability within smaller families.
image_gen_detailed_description: >-
  Scatter plot with x-axis 'ξ (Generalized Pareto)' ranging 0 to 0.15, y-axis 'MDD (Mean Dependency Distance)' ranging 0 to
  0.7. Two clouds of points: one cluster (red, low x, low y) representing ξ estimates with RMSE values (points labeled 'Japonic
  0.024', 'Sinitic 0.045', 'Uralic 0.055', 'Romance 0.068', 'Germanic 0.078', 'Slavic 0.085', 'Afroasiatic 0.095', 'Turkic
  0.120'); second cluster (blue, high x, high y) for MDD with similarly labeled RMSE values. Add horizontal band at y=0.51
  labeled 'MDD median RMSE' and vertical band at x=0.067 labeled 'ξ median RMSE'. Include inset text: 'ξ RMSE=0.067 [0.043-0.091],
  MDD RMSE=0.51 [0.33-0.69]'. Draw diagonal reference line (slope ~1) for reference.
aspect_ratio: '1:1'
summary: >-
  Cross-family generalization performance showing ξ's superior absolute-error RMSE compared to MDD across 8 language families.
figure_path: figures/fig_lofo_validation_v0.pdf
</available_figures>

<figure_requirements>
CRITICAL: Include ALL figures from <available_figures>. No exceptions.

- Every figure MUST use \includegraphics{figures/<the filename from its own `figure_path` above>} — INCLUDING the extension it actually has. Data figures are delivered as `.pdf` (vector, so their axis labels stay sharp) and concept figures as `.jpg`. Writing `.jpg` for a `.pdf` figure names a file that is not in figures/ and the build fails on it
- Do NOT skip, convert to tables, or describe without inserting
- Each needs: \begin{figure}[placement], \includegraphics, \caption, \label, \end{figure} — one placement for every figure, see FLOAT PLACEMENT below. Constrain every \includegraphics with `width=\linewidth,height=0.85\textheight,keepaspectratio`. The height is a LAST RESORT, not the usual limit: it exists so a very tall figure cannot overrun the page, and at 0.4 it bound almost everything instead — a 1:1 confusion matrix printed at 50.9% and its 11 pt axis labels reached the page at 5.6 pt, below what any venue accepts. At 0.85 every ratio the paper prompt prescribes (21:9, 16:9, 4:3, 1:1) is limited by WIDTH, prints at 93% and keeps its text above 10 pt. Use exactly these option keys — `max height=` is NOT valid LaTeX
- Use the `caption` field from each figure for \caption{...} — do NOT invent new captions
- Place figures where their [FIGURE:fig_id] markers appear in paper_text
- VERIFICATION: paper.tex MUST have exact same number of \includegraphics as <available_figures>
- Do NOT generate new figure images (no matplotlib, no PIL, no image generation). Use ONLY the pre-generated figures from <available_figures>. They were already created by a previous pipeline step.

FLOAT PLACEMENT: every figure gets \begin{figure}[!htbp]. Measured, not chosen:
the document the aii-paper-to-latex skill sets up is ONE column, so `figure*` is
exactly as wide as `figure` (469.76pt either way) and gains nothing; and any
placement asking for a page TOP — `[!t]`, `[!tbp]` — floated the hero diagram above
the paper's own title on page 1, while `[!htbp]` did not. `[!htbp]` also gives LaTeX
four options, so a float can never be deferred to the end of the document, which one
option alone risks. Where the hero ENDS UP is decided by its [FIGURE:] marker in
paper_text, which is already placed near the end of the Introduction — preserve it.
</figure_requirements>

<artifact_links>
The paper_text contains \footnote{Code: \url{...}} references linking to artifact source code
on GitHub. Include \usepackage{hyperref} and \usepackage{url}.
Preserve these exactly as-is — do not remove, rewrite, or convert them to plain text.
The URLs will not resolve yet (the repo is deployed after compilation) — do NOT try to verify or fix them.
</artifact_links>

<headings>
NEVER use inline math (``$...$``) inside ``\section{...}`` / ``\subsection{...}`` / ``\subsubsection{...}`` arguments — hyperref's bookmark builder errors out (``Token not allowed in a PDF string``) and the PDF outline breaks. If a section heading needs a math-looking term, use the text equivalent (``d star`` not ``$d^*$``, ``alpha-equivalent`` not ``$\alpha$-equivalent``) or wrap it in ``\texorpdfstring{$math$}{plain}``. Inline math inside body paragraphs is fine.
</headings>

<writing_register>
Write in the register of the field's best papers (the style exemplars block below, when the writing step saved any), not in the register of a language
model. Four things are measured on the finished draft, and a draft outside them is sent back with
the numbers:
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also. These are 10 to 30 times more frequent in machine-written abstracts than in
  human ones, and reviewers read them as such.
- Em dashes: at most 3 per 1,000 words. Use a comma, a colon or a full stop.
- Sentence rhythm: mix short and long sentences. An interquartile range of sentence length under
  8 words reads as machine-written.
- Hedging: at most 15 hedges (may, likely, suggests, appears) per 1,000
  words. State what the evidence supports plainly; hedge where it is thin, not everywhere.
Style never changes substance: numbers, claims, citations and figure markers stay exactly as the
evidence gives them. The user's original request (delivered as a separate message) overrides all
of this wherever the two conflict.
</writing_register>


FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-paper-to-latex, aii-semscholar-bib.
TODO 2. Review <paper_text> and <available_figures>. Copy all figure images into ./figures/ in your workspace. Count figures — MUST include every one. Plan placements per section. Build `./references.bib` via aii_semscholar_bib__fetch — collect DOIs/ArXiv IDs from <paper_text> and batch-fetch all BibTeX in one call. Do NOT fabricate entries.
TODO 3. Create `./paper.tex` per aii-paper-to-latex skill's setup, write ALL sections, insert ALL figures from <available_figures>, include `./references.bib` via \bibliography. Compile to PDF per skill's process. Fix errors.
TODO 4. CRITICAL VERIFICATION: Run `grep -c 'includegraphics' paper.tex`, confirm count equals figures in <available_figures>. If not, add missing figures. Verify `./paper.pdf` was created.
TODO 5. VISUAL REVIEW: Write Python script to convert EVERY page of paper.pdf to PNG at 150 DPI (use pdf2image or pymupdf). Then read ALL page screenshots — each page image costs ~1,600 tokens so a 15-page paper is only ~24K tokens. You MUST read every page. The ONLY exception is if all page images would not fit in your remaining context — in that case, read as many as fit and state which pages you are skipping and why. Check every page for layout issues, overlapping figures, cut-off text, bad spacing, formatting problems. Fix issues and recompile.
TODO 6. FINAL READ: Check page count (`pdfinfo paper.pdf` or pymupdf). Read entire paper.pdf — check for missing sections, unclear explanations, inconsistencies, typos. Fix and recompile. The ONLY exception is if all pages would not fit in your remaining context — in that case, read as many pages as fit and state which pages you are skipping and why.
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "FullPaperExpectedFiles": {
      "description": "All expected output files from full paper generation.",
      "properties": {
        "paper_tex_path": {
          "description": "Path to LaTeX source file. Example: 'paper.tex'",
          "title": "Paper Tex Path",
          "type": "string"
        },
        "paper_pdf_path": {
          "description": "Path to compiled PDF. Example: 'paper.pdf'",
          "title": "Paper Pdf Path",
          "type": "string"
        },
        "references_bib_path": {
          "description": "Path to BibTeX bibliography file. Example: 'references.bib'",
          "title": "References Bib Path",
          "type": "string"
        },
        "figure_paths": {
          "description": "Paths to all figure image files. Example: ['figures/fig1_v0.jpg', 'figures/fig2_v0.jpg']",
          "items": {
            "type": "string"
          },
          "title": "Figure Paths",
          "type": "array"
        }
      },
      "required": [
        "paper_tex_path",
        "paper_pdf_path",
        "references_bib_path",
        "figure_paths"
      ],
      "title": "FullPaperExpectedFiles",
      "type": "object"
    }
  },
  "description": "Full paper \u2014 structured output from paper generation.",
  "properties": {
    "title": {
      "description": "Paper title in plain, everyday language \u2014 short and jargon-free so a non-expert grasps it at a glance. Aim for about 4-8 words (~40 characters).",
      "maxLength": 90,
      "minLength": 12,
      "title": "Title",
      "type": "string"
    },
    "summary": {
      "description": "Brief summary of the generated paper: sections written, figures included, compilation status",
      "maxLength": 5000,
      "minLength": 500,
      "title": "Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/FullPaperExpectedFiles",
      "description": "All output files you created. Must include paper.tex, paper.pdf, references.bib, and paths to all figure files."
    }
  },
  "required": [
    "title",
    "summary",
    "out_expected_files"
  ],
  "title": "FullPaper",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.
````

### [2] HUMAN-USER prompt · 2026-09-07 08:02:27 UTC

```
Direction: Computational Linguistics — Dependency Distance Minimization Across UD Treebanks. Something genuinely novel and groundbreaking that measures dependency-distance distributions across UD treebanks, investigates whether spoken language minimizes more than written, characterizes how typology interacts with the pattern, and identifies families that deviate. MUST use commul/universal_dependencies on HuggingFace.

Ambition: level 3 of 5 — phenomenological science: surface and rigorously characterize a new empirical regularity or anomaly in the data, even before a full theoretical explanation exists.

Reviewer: I am Kaja Dobrovoljc (JSI / University of Ljubljana). Calibrate from my existing papers. Cross-domain methods (information theory, mixed-effects models, sequence models) welcome — but keep them close to what I already know, not too far from my background.

Submission/Goal: a paper for ACL, EMNLP, or the Computational Linguistics journal. Audience: computational linguists and quantitative typologists. Tone: empirically rigorous, careful with linguistic detail, reproducible on public UD.
```

### [3] SKILL-INPUT — aii-paper-to-latex · 2026-09-07 08:02:29 UTC

The agent loaded the **aii-paper-to-latex** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-to-latex
description: "Assembles and compiles a LaTeX paper into paper.pdf: documentclass and package preamble, figure floats that includegraphics pre-generated vector .pdf and .jpg files, float-placement and width rules, and the required pdflatex, bibtex, pdflatex, pdflatex run sequence. Use whenever pre-written text and pre-generated figures must become a compiled PDF, and whenever a build misbehaves — citations printing as question marks, figures drifting to the end or above the title, shrunken axis labels, undefined references. Triggers: latex, tex, pdflatex, bibtex, natbib, includegraphics, figure float, htbp, compile or build the paper, paper.tex, paper.pdf. NOT for: writing the paper's text or deciding its structure (use aii-paper-writing), creating the figure images (aii-data-fig-gen, aii-concept-fig-gen), or fetching bibliography entries (use aii-semscholar-bib); NOT for reshaping a PDF that already exists — merging, splitting, form filling, table extraction (use anthropic-pdf)."
---

## LaTeX Paper Assembly

Assembles a research paper from paper text, pre-generated figures (vector `.pdf` for data figures, `.jpg` for concept figures) and a bibliography into a compiled PDF.

### Document Setup

```latex
\documentclass[11pt,letterpaper]{article}
\usepackage{graphicx, geometry, amsmath, hyperref, url, natbib, booktabs, xcolor, listings}
\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=black, citecolor=black, urlcolor=black}
```

### Figure Inclusion

CRITICAL: Include ALL figures. Every figure MUST appear in the paper.

```latex
\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\linewidth,height=0.85\textheight,keepaspectratio]{figures/filename.pdf}
  \caption{Descriptive caption.}
  \label{fig:label}
\end{figure}
```

Rules:
- ALWAYS `[!htbp]` — all four options, so a float can never be deferred to the end of the
  document, which `[t]` or `[h]` alone risks. Do not ask for a page TOP: `[!t]` and
  `[!tbp]` both floated a figure ABOVE the paper's own title on page 1, where `[!htbp]`
  on the same document did not. Where a figure lands is decided by where it is declared
  in the text
- Use `figure`, never `figure*`. This document class is ONE column, so `figure*` is exactly
  as wide as `figure` (469.76pt either way) and gains nothing, while restricting the float
  to a page top
- ALWAYS constrain with `width` and `keepaspectratio`. Add `height` only as a
  LAST RESORT against a very tall figure overrunning the page, and keep it
  generous — `0.85\textheight`. A tight height cap binds on ordinary figures
  and LaTeX then shrinks the TEXT with them: at `0.4\textheight` a square
  figure printed at 50.9%, putting 11 pt axis labels on the page at 5.6 pt.
  The figure generator measures legibility at the figure's OWN size, so it
  cannot see this happen
- Every figure needs `\caption`, `\label`, and a `\ref` in the text
- Do NOT convert figures to tables or describe them without inserting the image
- Do NOT skip any figures

### Compilation Process

Run each command separately (do NOT chain with `&&` — pdflatex often exits non-zero on warnings, which would skip bibtex and leave citations as `??`):

```bash
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

All four commands are required. Skipping bibtex causes `??` in all citations.
Fix any errors between runs. Verify `./paper.pdf` was created.

### Output Files

- `./paper.tex` — LaTeX source
- `./references.bib` — bibliography file
- `./paper.pdf` — compiled PDF
- `./figures/` — all figure images (pre-generated, copied into workspace). Data
  figures are `.pdf` (vector — LaTeX renders their text at page resolution, which
  is what keeps axis labels sharp in print); concept figures are `.jpg`. Use each
  file's OWN extension in `\includegraphics`; there is no conversion step.
````

### [4] SKILL-INPUT — aii-semscholar-bib · 2026-09-07 08:02:29 UTC

The agent loaded the **aii-semscholar-bib** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-semscholar-bib
description: "Fetches real BibTeX entries in one batch from Semantic Scholar by DOI, ArXiv ID or title via aii_semscholar_bib__fetch, normalises citation keys to AuthorYYYY, injects DOIs, and writes the result into references.bib, with a mandatory web-search fallback for anything not found. ALWAYS use whenever a bibliography, reference list or .bib file is being built or extended, and whenever a citation needs a verified entry instead of an invented one — never hand-write BibTeX first. Triggers: bibliography, references.bib, bibtex, citation key, DOI, arXiv id, Semantic Scholar, reference list, cite these papers, natbib entries. NOT for: writing the text around the citations (use aii-paper-writing), running bibtex and compiling (use aii-paper-to-latex), judging whether cited work supports the claims (use amg-paper-verification), or open-ended literature search and PDF mining (use aii-web-tools)."
---

## Tool: `aii_semscholar_bib__fetch`

Batch-fetch BibTeX entries from Semantic Scholar. Pass all references in a single call — the tool handles batching internally.

### How it works

1. **DOI/ArXiv refs** → batched into POST /paper/batch calls (up to 500 per API call, auto-chunked)
2. **Title-only refs** → individual GET /paper/search/match (1s delay between)
3. **Post-process** → fix entry type, fix citation key (AuthorYYYY), inject DOI

The ability server runs a single worker (`max_threads: 1`). Multiple concurrent tool calls are queued — each runs independently (no cross-request aggregation). Batching happens within each request.

### Input format

```json
{
  "references": [
    {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
    {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
    {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
  ]
}
```

Each reference object can have:
- `doi` — DOI string (ArXiv DOIs like `10.48550/arXiv.XXXX.XXXXX` auto-convert to ArXiv IDs)
- `arxiv` — ArXiv ID (e.g. `"2305.14325"`)
- `title` — Paper title (used for search/match when no DOI/ArXiv)
- `author` — First author last name (for cleaner citation key)
- `year` — Publication year (int, for citation key)

At least one of `doi`, `arxiv`, or `title` is required per reference.

### Output format

```json
{
  "success": true,
  "bib_text": "@inproceedings{Vaswani2017, ...}\n\n@article{Wei2022, ...}",
  "total": 3,
  "found": 3,
  "failed_count": 0,
  "entries": [{"citation_key": "Vaswani2017", "bibtex": "...", "title": "...", "doi": "...", "arxiv": ""}],
  "failed": []
}
```

### Workflow

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Call `aii_semscholar_bib__fetch` with the full list in **one call**
3. Save `bib_text` from the response to your `references.bib` file
4. Check `failed` — for any missed papers, follow the **fallback procedure** below

### Fallback for failed references (MANDATORY)

NEVER fabricate BibTeX. For each failed reference:
1. **WebSearch** for `"Title" author year` (try `site:arxiv.org` too)
2. **WebFetch** the paper page → extract title, authors, year, venue, DOI/ArXiv ID
3. If DOI/ArXiv found → retry `aii_semscholar_bib__fetch` with it
4. Last resort: write BibTeX by hand using **only verified info from the actual paper page**

---

### CLI (for manual use / debugging)

```bash
SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-semscholar-bib" && \
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py --refs '[
  {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
  {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
  {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
]'
```

`--json, -j` — output raw JSON instead of .bib text

**If the script fails** with a connection error (ability server not running): create a local `.venv`, install server deps from `server_requirements.txt` into it, then import the `@aii_ability` function from the script and call it directly — bypassing the server:
```bash
uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r "$SKILL_DIR/scripts/server_requirements.txt"
```
````
