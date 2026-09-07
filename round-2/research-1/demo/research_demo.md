# Power-Law vs GPD Tail Models for Dependency Distance

## Summary

Comprehensive research establishing prior literature on power-law characterization of dependency-length distributions (Ferrer-i-Cancho 2003-2022) and clarifying the mathematical and methodological relationship between power-law exponents (α) and Generalized Pareto Distribution shape parameters (ξ). Key findings: (1) Power laws have been observed in dependency distances for 20+ years; (2) Petrini & Ferrer-i-Cancho 2022 show a two-regime model with a 4-5 word breakpoint fits 20 languages optimally; (3) Mathematically, α = 1/ξ—the two models are reciprocal parameterizations of identical tail behavior; (4) Standard methodology for power-law fitting (Clauset et al. 2009) uses MLE + KS threshold selection + likelihood-ratio model comparison; (5) GPD fitting uses similar MLE but focuses on peaks-over-threshold with stability-plot threshold selection; (6) No prior study directly compared α and ξ on dependency distances; (7) The hypothesis's novelty depends on demonstrating ξ has better statistical properties, greater discriminative power for register/typology, or superior interpretability—not just different parameterization. Experimental design specified for testing across 18 UD treebanks.

## Research Findings

## Literature on Power Laws in Dependency Distance

**Foundational Work (2003-2006).** Ferrer-i-Cancho's work established that syntactic dependency distances follow an exponentially decaying probability distribution [1, 2]. Specifically, the probability of observing a dependency at distance d decays approximately as exp(-λd) for sentences of fixed length [2]. However, Ferrer-i-Cancho made a critical empirical observation: the rate of decay slows down around 4-5 words, suggesting the distribution does not obey a simple exponential for all distances [1].

**Power-Law Claims (2007-2015).** Liu proposed that dependency distances in Chinese treebanks follow a power-law distribution p(d) ∝ d^(-α) [3]. A 2016 cross-linguistic study covering 30 languages identified power-law behavior for long sentences and exponential trends in short ones, suggesting the model depends on sentence length [3]. Futrell et al. (2015) provided large-scale evidence across 37 languages that syntactic structure minimizes dependency lengths, consistent with cognitive economy principles [4].

**Resolution via Two-Regime Model (2022-2025).** The most recent comprehensive study (Petrini & Ferrer-i-Cancho 2022, published 2025 in Glottometrics) tested both exponential and power-law models on 20 languages with unified annotation standards [5]. They found that a two-regime model—where the probability decay follows either exponential or power-law behavior up to a breakpoint, then switches to a second regime—provides the best fit across all 20 languages [5]. The breakpoint exhibits low variation across languages (mean 4-5 words), suggesting a universal cognitive chunking mechanism [5]. Crucially, Petrini and Ferrer-i-Cancho controlled for sentence-length effects by analyzing both fixed-length and mixed-length sentences, addressing confounds that plagued earlier comparisons [5].

## Mathematical Relationship Between Power-Law Exponent (α) and GPD Shape Parameter (ξ)

**Tail Equivalence.** For a power-law distribution p(x) ∝ x^(-α) (α > 1), the survival function (1 - cumulative distribution) decays as F̄(x) ~ x^(-α) [6]. For a Generalized Pareto Distribution with shape parameter ξ > 0, the survival function decays as F̄(x) ~ x^(-1/ξ) [7, 8]. Therefore, **α and 1/ξ are mathematically identical in the tail regime**: when α = 2.5, this is equivalent to ξ = 0.4 [7, 8]. The relationship α = 1/ξ means the two models are not independent competing hypotheses—they are simply different parameterizations of the same tail behavior [7].

**Interpretation Differences.** Despite mathematical equivalence in the tail, the two parameterizations offer different interpretations [7, 8]:
- Power-law exponent α directly describes rank-ordered scaling. Typical values range 1 < α < 3 [6].
- GPD shape parameter ξ characterizes tail risk: ξ > 0 indicates heavy tail, ξ = 0 indicates exponential, ξ < 0 indicates bounded tail [8]. Values typically range -0.5 < ξ < 0.5 [8].

## Standard Methodology for Power-Law Fitting

**Parameter Estimation.** The canonical approach (Clauset, Shalizi, Newman 2009, cited 6797 times [9]) uses maximum-likelihood estimation rather than least-squares fitting [9]. For a power law with minimum value x_min, the MLE for the exponent is [9]:

α̂ = 1 + n / Σ(ln(x_i / x_min))

where n is the number of observations and x_i are the observed values ≥ x_min [9]. Statistical uncertainty in α̂ is calculated from bootstrapping [9].

**Threshold Selection.** The critical step is choosing x_min. Clauset et al. (2009) recommend the **Kolmogorov-Smirnov (KS) test**: for each candidate x_min, fit a power law and compute the KS distance between empirical and theoretical cumulative distributions [9]. Choose the x_min that minimizes this distance [9]. This guards against claiming a power law when none exists and is far superior to visual log-log inspection [9].

**Goodness-of-Fit Testing.** After fitting, test whether data are consistent with the power-law hypothesis via bootstrap: (1) generate synthetic data from the fitted model, (2) compute KS statistics on each synthetic sample, (3) compare to the original data's KS statistic to obtain a p-value [9]. If p > 0.1, the power-law hypothesis is plausible; if p ≤ 0.1, reject it [9].

**Model Comparison.** Compare power laws to competing models (lognormal, exponential, Weibull) using **likelihood-ratio tests** [9]. The test statistic LR = -2·ln(L_power-law / L_alternative) approximately follows a χ² distribution [9]. Positive LR favors the power law; negative LR favors the alternative [9].

## Threshold Selection for Generalized Pareto Distribution (GPD)

**Peaks-Over-Threshold Framework.** GPD fitting targets the upper tail of a distribution [7, 8, 10]. The standard approach selects a threshold u, extracts all exceedances X > u, and fits a GPD to shifted exceedances Y = X - u [7, 10]. MLE for GPD shape parameter ξ and scale parameter σ are computed on the exceedances [8].

**Threshold Selection Methods.** The mean-residual-life (MRL) plot—plotting E[X - u | X > u] against u—should become approximately linear above the "true" threshold [10]. Practitioners use multiple approaches: (1) MRL plots to identify candidate thresholds, (2) **stability plots** showing how ξ changes with threshold, with ideal threshold where ξ stabilizes [10], and (3) Bayesian or likelihood-based joint optimization [10].

**Critical Consideration.** Unlike power-law fitting which identifies x_min (minimum value where power-law begins), GPD fitting **requires choosing u in the tail** [7, 10]. This is fundamentally different and may yield different tail inferences [7].

## Sentence-Length Normalization and Confounding

**The Problem.** Petrini and Ferrer-i-Cancho (2022) documented that dependency distances are confounded by sentence length: longer sentences have more opportunities for long dependencies [5]. Earlier studies disagreed on power-law vs. exponential models, likely due to differential sentence-length control [5].

**Standard Solutions.** (1) Fixed-length analysis: fit separate models to sentences of lengths 10-20, 20-30, etc., then pool parameter estimates [5]. (2) Sentence-length normalization: divide distance by sentence length d_norm = d / L [5]. (3) Mixed-length analysis with correction: include sentence length as a predictor in a mixed-effects model [5]. Petrini and Ferrer-i-Cancho employ both fixed-length and mixed-length analyses on parallel corpora, making findings robust to this confound [5].

## Existing Prior Comparisons of Power-Law and GPD Models

**Gap in the Literature.** Despite 20+ years of power-law research in linguistics and 30+ years of GPD methodology in extreme-value theory, **no prior study has directly compared power-law exponents (α) to GPD shape parameters (ξ) on the same dependency-distance data** [1, 2, 3, 5]. The closest work compares power-law to exponential models [1, 5], but does not test whether GPD fitting yields different conclusions about register or typological variation [5].

**Model Comparison in Other Domains.** In hydrology and finance, practitioners routinely compare power-law and GPD models on the same tail data [10], typically using AIC/BIC for model selection [10]. However, they ask which model predicts extreme events better, not whether α and 1/ξ yield different inferences [10].

## Register and Typology Effects: Current State of Knowledge

**Spoken vs Written Register.** Dobrovoljc and colleagues created Slovenian spoken and written treebanks (SST and SSJ) for register comparison [11]. A 2017 study found that spoken language exhibits different dependency distance properties than written language [12]. However, no study has tested whether spoken language has **lower power-law exponents or lower ξ** as a consequence of planning constraints [11, 12].

**Typological Patterns.** Futrell et al. (2015) documented that dependency-length minimization occurs across word-order typologies (SVO, SOV, VSO) [4]. However, typological variation in tail shape (α or ξ) has not been systematically characterized [4].

## Critical Appraisal: Is ξ a "Novel" Statistic?

**The Challenge.** Since α = 1/ξ, computing ξ is mathematically equivalent to reporting 1/α. For novelty, the hypothesis must demonstrate genuine advantages beyond reparameterization [6, 7]:

1. **Statistical Properties**: Does ξ estimation via GPD/MLE have lower bias or variance than α estimation via power-law MLE on dependency distances? This requires direct empirical comparison [9].

2. **Interpretability**: Is ξ more interpretable? The GPD parameterization (ξ > 0 = heavy tail, ξ = 0 = exponential, ξ < 0 = bounded tail) is arguably more explicit, but this is presentation choice [7, 8].

3. **Predictive Power for Linguistic Factors**: Does ξ better discriminate register or typological variation than α? This requires fitting both models across treebanks and comparing effect sizes [5]. If both yield identical discriminative power (as theory predicts), novelty collapses [6, 7].

4. **Theoretical Alignment with EVT**: GPD is the canonical extreme-value-theory model for tail inference. If the goal is to position dependency distances as an **extreme-value phenomenon**, then GPD is theoretically justified [10]. However, if power-law models fit well already, the motivation for EVT is unclear [9, 5].

## Experimental Design for Hypothesis Testing

**18 Treebanks.** The plan mentions "18-treebank, 4-matched-pair evidence (Slovenian SST/SSJ, French Rhapsodie/GSD, English, Turkish ATIS/IMST)." This requires:
1. Extract dependency distances from each treebank's Universal Dependencies format.
2. Identify spoken/written labels and typological metadata.
3. Ensure treebanks have ≥20,000 arcs for stable tail estimation [1, 5].

**Parallel Fitting Procedure.**
1. **Normalize distances** for sentence length using fixed-length and mixed-length analyses [5].
2. **Select thresholds** jointly for power-law (x_min via KS) and GPD (u via stability plot) at the same percentile range [9, 10].
3. **Estimate α and ξ** via MLE, compute bootstrap confidence intervals, conduct goodness-of-fit tests (KS for power law, Anderson-Darling for GPD) [9, 10].
4. **Compare models** using AIC/BIC and likelihood-ratio tests on the same tail subset [9].
5. **Test equivalence**: verify that α ≈ 1/ξ numerically across treebanks; if true, the models are just reparameterizations [6].

**Register and Typology Analysis.**
1. Fit α and ξ separately for spoken and written language within each language.
2. Compute effect sizes: Δα = α_spoken - α_written, Δξ = ξ_spoken - ξ_written.
3. Test hypothesis via mixed-effects models: outcome ~ register + typology + (1 | language family).
4. Compare whether α or ξ explains more variance in register/typology (R² comparison).

## Summary

Power-law distributions are well-established in dependency distances (Ferrer-i-Cancho 2004 onwards), with recent evidence favoring a two-regime model (Petrini & Ferrer-i-Cancho 2022). The GPD shape parameter ξ is mathematically identical to 1/α, meaning the two models parameterize the same tail behavior differently. No prior study compares α and ξ on dependency distances. The hypothesis's novelty requires demonstrating that ξ offers better statistical properties, greater discriminative power for linguistic factors, or superior interpretability—not just different parameterization. Experimental design for 18 UD treebanks with matched register pairs is well-established in methodology and feasible with standard tools (scipy, poweRlaw package).

## Sources

[1] [Patterns in syntactic dependency networks (Ferrer-i-Cancho 2004)](https://doi.org/10.1103/physreve.69.051915) — Foundational work establishing exponential decay in dependency distances and identifying the anomalous slowing of decay around 4-5 words in Czech and Romanian.

[2] [Optimality of syntactic dependency distances (Ferrer-i-Cancho et al., 2022)](https://doi.org/10.1103/physreve.105.014308) — Recent work on optimality of dependency distances and mathematical foundations of dependency distance minimization.

[3] [The distribution of syntactic dependency distances (Petrini & Ferrer-i-Cancho 2022, published 2025)](https://doi.org/10.48550/arxiv.2211.14620) — Comprehensive study of 20 languages showing two-regime exponential/power-law model is optimal, with ~4-5 word breakpoint across languages, addressing sentence-length confounds via parallel corpora.

[4] [Large-scale evidence of dependency length minimization in 37 languages (Futrell et al. 2015)](https://doi.org/10.1073/pnas.1502134112) — PNAS paper providing large-scale cross-linguistic evidence that dependency-length minimization occurs across word-order typologies, supporting cognitive economy hypothesis.

[5] [Petrini & Ferrer-i-Cancho 2022 - Full PDF](https://arxiv.org/pdf/2211.14620) — Full text detailing two-regime model methodology, sentence-length normalization strategies, breakpoint findings across 20 languages, and connection to cognitive chunking theory.

[6] [Power-law distributions in empirical data (Clauset, Shalizi, Newman 2009)](https://doi.org/10.48550/arXiv.0706.1062) — Canonical methodology paper (6797 citations) for power-law fitting: maximum-likelihood estimation, Kolmogorov-Smirnov threshold selection, goodness-of-fit testing, and likelihood-ratio model comparison.

[7] [Pareto distribution (Wikipedia)](https://en.wikipedia.org/wiki/Pareto_distribution) — Mathematical definitions of Pareto and generalized Pareto distributions, including relationship to power laws and extreme value theory frameworks.

[8] [scipy.stats.genpareto documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html) — Technical reference for generalized Pareto distribution implementation in Python, including shape parameter ξ interpretation and MLE computation.

[9] [Clauset et al. 2009 - Full PDF (arXiv 0706.1062)](https://arxiv.org/pdf/0706.1062) — Complete methodology for power-law analysis: MLE formulas, KS test procedure for threshold selection, bootstrap goodness-of-fit, and Box 1 recipe for practitioners.

[10] [Estimating the Tails of Loss Severity Distributions Using Extreme Value Theory (Beirlant et al., 1997)](https://doi.org/10.2143/ast.27.1.563210) — Extreme-value-theory methodology for GPD fitting, threshold selection via mean-residual-life plots and stability plots, goodness-of-fit testing for tail models.

[11] [The Universal Dependencies Treebank of Spoken Slovenian (Dobrovoljc et al., 2016)](https://doi.org/10.63317/3xjypk7r6955) — Spoken Slovenian treebank providing matched-pair data (with written SSJ treebank) for register and cognitive-demand studies of dependency syntax.

[12] [Dependency Distance Differences across Interpreting Types: Implications for Cognitive Demand (Dragsted et al., 2017)](https://doi.org/10.3389/fpsyg.2017.02132) — Empirical evidence that dependency distances differ across spoken vs. written registers, with implications for cognitive load and processing constraints.

## Follow-up Questions

- When power-law exponents (α) and GPD shape parameters (ξ) are estimated on the same subset of dependency-distance data from 18 treebanks, do they yield numerically equivalent predictions of tail behavior (i.e., does α ≈ 1/ξ hold empirically), or are there systematic biases in one estimator relative to the other that could explain a claim of novelty for ξ?
- Across the matched-pair treebanks (Slovenian SST/SSJ, French Rhapsodie/GSD, English spoken/written, Turkish ATIS/IMST), does the GPD shape parameter ξ discriminate register (spoken vs. written) better than the power-law exponent α, or do both models show identical effect sizes and significance levels—meaning register effects on tail shape are robust to parameterization choice?
- If Petrini & Ferrer-i-Cancho's (2022) two-regime model is the true generating process for dependency distances, should both power-law and GPD fitting be restricted to the regime above the 4-5 word breakpoint, or applied to the full tail? How sensitive are α and ξ estimates to this methodological choice, and which regime choice best captures the linguistic phenomenon the hypothesis aims to explain?

---
*Generated by AI Inventor Pipeline*
