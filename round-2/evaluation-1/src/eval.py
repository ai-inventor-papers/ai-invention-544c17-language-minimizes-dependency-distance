#!/usr/bin/env python3
"""Register-effect evaluation with the pseudo-replication error fixed.

Computes decile-level paired tests, GPD tail-shape (xi) vs power-law (alpha)
model comparison, family/size/deprel/sentence-length/annotation-reliability
stratifications, robustness checks, and a deprel-based qualitative sample of
long-distance arcs. Output follows the exp_eval_sol_out schema.
"""

import argparse
import json
import resource
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
from loguru import logger
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
import eval_lib as L  # noqa: E402

WORKDIR = Path(__file__).parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(WORKDIR / "logs" / "eval.log", rotation="30 MB", level="DEBUG")

RNG = np.random.default_rng(42)
THRESHOLD_Q = 0.90  # base tail threshold quantile, refined per-treebank via MRL


def set_memory_limit(gb: float) -> None:
    avail = psutil.virtual_memory().available
    budget = gb * 1024**3
    if budget >= avail:
        budget = avail * 0.8
    resource.setrlimit(resource.RLIMIT_AS, (int(budget * 3), int(budget * 3)))
    logger.info(f"RAM budget set to ~{budget / 1e9:.1f} GB (available {avail / 1e9:.1f} GB)")


def treebank_tail_models(x: np.ndarray, threshold_q: float = THRESHOLD_Q, n_boot: int = 300) -> dict:
    mrl = L.mean_residual_life(x, np.linspace(0.5, 0.97, 20))
    chosen_q = L.choose_threshold_from_mrl(mrl) if mrl else threshold_q
    gpd = L.fit_gpd(x, chosen_q, n_boot=n_boot, rng=RNG)
    pl = L.fit_powerlaw(x, chosen_q)
    result = {"mrl_chosen_quantile": chosen_q, "gpd": gpd, "powerlaw": pl}
    if gpd.get("status") == "ok" and pl.get("status") == "ok":
        result["akaike"] = L.akaike_weights(gpd["aic"], pl["aic"])
    # threshold-sensitivity robustness check: +-20% of chosen quantile
    sens = {}
    for label, q in [("minus20pct", max(0.5, chosen_q * 0.8)), ("plus20pct", min(0.98, chosen_q * 1.2))]:
        sens[label] = L.fit_gpd(x, q, n_boot=150, rng=RNG)
    result["threshold_sensitivity"] = sens
    return result


def run_full_analysis(sent_df, arc_df, n_boot: int) -> dict:
    metrics: dict = {}

    # ---- 1. corrected decile-level paired tests + 4. Holm-Bonferroni --------
    logger.info("Metric 1: decile-level paired Wilcoxon/t-test per matched pair")
    pair_decile = {}
    raw_pvals = {}
    for name, spec in L.MATCHED_PAIRS.items():
        res = L.decile_paired_test(sent_df, spec["spoken"], spec["written"])
        pair_decile[name] = res
        if res.get("status") == "ok":
            raw_pvals[name] = res["wilcoxon_p_raw"]
    corrected = L.holm_bonferroni(raw_pvals) if raw_pvals else {}
    for name in pair_decile:
        if name in corrected:
            pair_decile[name]["wilcoxon_p_holm"] = corrected[name]
    metrics["decile_paired_tests"] = pair_decile

    # ---- 2. GPD xi per treebank (all 18) + power-law (metric 6) -------------
    logger.info("Metric 2 & 6: per-treebank GPD xi and power-law alpha fits")
    treebank_models = {}
    for tb, grp in sent_df.groupby("treebank_id"):
        norm = np.concatenate([np.asarray(v, dtype=float) for v in grp["norm_dists"] if len(v) > 0])
        norm = norm[np.isfinite(norm) & (norm > 0)]
        n_boot_tb = n_boot if len(norm) > 200 else max(50, n_boot // 3)
        treebank_models[tb] = treebank_tail_models(norm, n_boot=n_boot_tb)
        treebank_models[tb]["n_normalized_distances"] = int(len(norm))
    metrics["treebank_tail_models"] = treebank_models

    xi_vals, alpha_vals = [], []
    for tb, m in treebank_models.items():
        if m["gpd"].get("status") == "ok" and m["powerlaw"].get("status") == "ok":
            xi_vals.append(m["gpd"]["xi"])
            alpha_vals.append(m["powerlaw"]["alpha"])
    if len(xi_vals) >= 3:
        corr = stats.pearsonr(xi_vals, alpha_vals)
        metrics["xi_alpha_correlation"] = {"r": float(corr.statistic), "p": float(corr.pvalue), "n_treebanks": len(xi_vals)}
    else:
        metrics["xi_alpha_correlation"] = {"status": "insufficient_treebanks"}

    # ---- pair-level xi comparison + language tally --------------------------
    logger.info("Pair-level GPD xi comparison + language tally")
    tally = {}
    xi_spoken_list, xi_written_list = [], []
    for name, spec in L.MATCHED_PAIRS.items():
        sp, wr = treebank_models.get(spec["spoken"], {}), treebank_models.get(spec["written"], {})
        sp_xi, wr_xi = sp.get("gpd", {}).get("xi"), wr.get("gpd", {}).get("xi")
        sp_mdd = float(sent_df.loc[sent_df.treebank_id == spec["spoken"], "mean_norm_dist"].mean())
        wr_mdd = float(sent_df.loc[sent_df.treebank_id == spec["written"], "mean_norm_dist"].mean())
        entry = {
            "family": spec["family"],
            "xi_spoken": sp_xi,
            "xi_written": wr_xi,
            "xi_direction": None,
            "mdd_spoken": sp_mdd,
            "mdd_written": wr_mdd,
            "mdd_direction": "spoken>written" if sp_mdd > wr_mdd else "spoken<written",
        }
        if sp_xi is not None and wr_xi is not None:
            entry["xi_direction"] = "spoken>written (heavier tail)" if sp_xi > wr_xi else "spoken<written (lighter tail)"
            xi_spoken_list.append(sp_xi)
            xi_written_list.append(wr_xi)
        tally[name] = entry
    metrics["language_level_tally"] = tally
    metrics["n_pairs_spoken_lighter_tail"] = int(sum(1 for e in tally.values() if e["xi_direction"] == "spoken<written (lighter tail)"))
    metrics["n_pairs_spoken_heavier_tail"] = int(sum(1 for e in tally.values() if e["xi_direction"] == "spoken>written (heavier tail)"))
    metrics["n_pairs_spoken_higher_mdd"] = int(sum(1 for e in tally.values() if e["mdd_direction"] == "spoken>written"))
    if len(xi_spoken_list) >= 2:
        tt = stats.ttest_rel(xi_spoken_list, xi_written_list)
        metrics["xi_paired_ttest_across_pairs"] = {"t": float(tt.statistic), "p": float(tt.pvalue), "n_pairs": len(xi_spoken_list)}

    # ---- 5a. by language family ---------------------------------------------
    metrics["stratified_by_family"] = {
        name: {"family": spec["family"], "mdd_direction": tally[name]["mdd_direction"], "xi_direction": tally[name]["xi_direction"]}
        for name, spec in L.MATCHED_PAIRS.items()
    }

    # ---- 5b. by treebank size quartile --------------------------------------
    logger.info("Metric 5b: stratify by treebank size (token count) quartile")
    size_by_tb = sent_df.groupby("treebank_id")["sentence_length"].sum()
    n_bins = min(4, size_by_tb.nunique())
    if n_bins >= 2:
        codes = pd.qcut(size_by_tb, n_bins, labels=False, duplicates="drop")
        names = ["Q1_smallest", "Q2", "Q3", "Q4_largest"]
        quartiles = codes.map(lambda c: names[min(int(c), 3)])
    else:
        quartiles = pd.Series("Q1_smallest", index=size_by_tb.index)
    size_strat = {}
    for tb, q in quartiles.items():
        reg = sent_df.loc[sent_df.treebank_id == tb, "register"].iloc[0]
        size_strat.setdefault(str(q), []).append({"treebank": tb, "register": reg, "n_tokens": int(size_by_tb[tb])})
    metrics["stratified_by_size_quartile"] = size_strat
    pair_sizes = [int(size_by_tb.get(spec["spoken"], 0) + size_by_tb.get(spec["written"], 0)) for spec in L.MATCHED_PAIRS.values()]
    pair_abs_mdd_diff = [abs(tally[n]["mdd_spoken"] - tally[n]["mdd_written"]) for n in L.MATCHED_PAIRS]
    if len(pair_sizes) >= 3:
        corr_size = stats.pearsonr(pair_sizes, pair_abs_mdd_diff)
        metrics["size_vs_effect_magnitude_correlation"] = {"r": float(corr_size.statistic), "p": float(corr_size.pvalue)}

    # ---- 5c. sentence-length distribution: KS test per pair -----------------
    logger.info("Metric 5c: KS test on sentence-length distributions per pair")
    ks_results = {}
    for name, spec in L.MATCHED_PAIRS.items():
        sp_len = sent_df.loc[sent_df.treebank_id == spec["spoken"], "sentence_length"].dropna().to_numpy()
        wr_len = sent_df.loc[sent_df.treebank_id == spec["written"], "sentence_length"].dropna().to_numpy()
        if len(sp_len) > 5 and len(wr_len) > 5:
            ks = stats.ks_2samp(sp_len, wr_len)
            ks_results[name] = {
                "ks_stat": float(ks.statistic),
                "ks_p": float(ks.pvalue),
                "spoken_mean_len": float(np.mean(sp_len)),
                "written_mean_len": float(np.mean(wr_len)),
                "spoken_shorter": bool(np.mean(sp_len) < np.mean(wr_len)),
            }
    metrics["sentence_length_distribution_ks"] = ks_results

    # ---- 5d. by deprel type ---------------------------------------------------
    logger.info("Metric 5d: register effect stratified by deprel type (arc-level, Mann-Whitney)")
    deprel_strat = {}
    for name, spec in L.MATCHED_PAIRS.items():
        per_deprel = {}
        for dep in L.MAJOR_DEPRELS:
            sp = arc_df.loc[(arc_df.treebank_id == spec["spoken"]) & (arc_df.deprel == dep), "norm_dist"].dropna().to_numpy()
            wr = arc_df.loc[(arc_df.treebank_id == spec["written"]) & (arc_df.deprel == dep), "norm_dist"].dropna().to_numpy()
            if len(sp) >= 10 and len(wr) >= 10:
                mw = stats.mannwhitneyu(sp, wr, alternative="two-sided")
                per_deprel[dep] = {
                    "n_spoken": int(len(sp)),
                    "n_written": int(len(wr)),
                    "mean_spoken": float(np.mean(sp)),
                    "mean_written": float(np.mean(wr)),
                    "mannwhitney_p": float(mw.pvalue),
                }
        deprel_strat[name] = per_deprel
    metrics["stratified_by_deprel"] = deprel_strat
    all_p = [(pair, dep, v["mannwhitney_p"]) for pair, d in deprel_strat.items() for dep, v in d.items()]
    strongest = sorted(all_p, key=lambda t: t[2])[:5]
    metrics["strongest_register_signal_deprels"] = [{"pair": p, "deprel": d, "p": pv} for p, d, pv in strongest]

    # ---- 5e. annotation reliability cross-check ------------------------------
    logger.info("Metric 5e: annotation-reliability heuristic cross-check")
    reliability = {}
    for name, spec in L.MATCHED_PAIRS.items():
        sp = sent_df[sent_df.treebank_id == spec["spoken"]]
        wr = sent_df[sent_df.treebank_id == spec["written"]]
        sp_len, wr_len = float(sp.sentence_length.mean()), float(wr.sentence_length.mean())
        sp_intj, wr_intj = float(sp.has_intj.mean()), float(wr.has_intj.mean())
        contradicts_length = sp_len > wr_len
        contradicts_intj = sp_intj <= wr_intj
        reliability[name] = {
            "spoken_mean_length": sp_len,
            "written_mean_length": wr_len,
            "spoken_intj_fraction": sp_intj,
            "written_intj_fraction": wr_intj,
            "contradicts_shorter_spoken_heuristic": bool(contradicts_length),
            "contradicts_more_disfluency_spoken_heuristic": bool(contradicts_intj),
            "flagged": bool(contradicts_length or contradicts_intj),
        }
    metrics["annotation_reliability_check"] = reliability

    # ---- 7a. robustness: exclude flat/list deprels ---------------------------
    logger.info("Metric 7a: robustness — exclude flat/list deprels, recompute xi")
    robust_excl = {}
    for name, spec in L.MATCHED_PAIRS.items():
        entry = {}
        for role, tb in [("spoken", spec["spoken"]), ("written", spec["written"])]:
            vals = arc_df.loc[(arc_df.treebank_id == tb) & (~arc_df.deprel.isin(L.FLAT_LIST_DEPRELS)), "norm_dist"].dropna().to_numpy()
            vals = vals[np.isfinite(vals) & (vals > 0)]
            gpd = L.fit_gpd(vals, THRESHOLD_Q, n_boot=100, rng=RNG) if len(vals) > 30 else {"status": "insufficient_data"}
            entry[role] = {"xi_excl_flat_list": gpd.get("xi"), "n": int(len(vals))}
        if entry["spoken"]["xi_excl_flat_list"] is not None and entry["written"]["xi_excl_flat_list"] is not None:
            orig = metrics["language_level_tally"][name]
            new_dir = "spoken>written" if entry["spoken"]["xi_excl_flat_list"] > entry["written"]["xi_excl_flat_list"] else "spoken<written"
            orig_dir = "spoken>written" if orig["xi_spoken"] is not None and orig["xi_spoken"] > orig["xi_written"] else "spoken<written"
            entry["direction_changed_vs_full"] = bool(new_dir != orig_dir)
        robust_excl[name] = entry
    metrics["robustness_exclude_flat_list"] = robust_excl

    # ---- 7b. minimum-arc threshold -------------------------------------------
    logger.info("Metric 7b: robustness — minimum-arc treebank exclusion")
    arc_counts = arc_df.groupby("treebank_id").size()
    small_treebanks = arc_counts[arc_counts < 1000].index.tolist()
    metrics["robustness_small_treebank_exclusion"] = {
        "small_treebanks_lt_1000_arcs": {tb: int(arc_counts[tb]) for tb in small_treebanks},
        "n_pairs_affected": int(sum(1 for spec in L.MATCHED_PAIRS.values() if spec["spoken"] in small_treebanks or spec["written"] in small_treebanks)),
    }

    # threshold-sensitivity summary (7c) pulled from per-treebank results already computed
    logger.info("Metric 7c: summarising threshold-sensitivity CI overlap")
    sens_summary = {}
    for tb, m in treebank_models.items():
        base = m["gpd"]
        sens = m.get("threshold_sensitivity", {})
        lo, hi = sens.get("minus20pct", {}), sens.get("plus20pct", {})
        if base.get("status") == "ok" and lo.get("status") == "ok" and hi.get("status") == "ok":
            base_ci = (base.get("xi_ci95_lo"), base.get("xi_ci95_hi"))
            overlaps = []
            for cand in (lo, hi):
                cci = (cand.get("xi_ci95_lo"), cand.get("xi_ci95_hi"))
                if all(v is not None and not np.isnan(v) for v in [*base_ci, *cci]):
                    overlaps.append(bool(base_ci[0] <= cci[1] and cci[0] <= base_ci[1]))
            sens_summary[tb] = {"base_xi": base["xi"], "minus20pct_xi": lo.get("xi"), "plus20pct_xi": hi.get("xi"), "ci_overlaps_base": overlaps}
    metrics["threshold_sensitivity_summary"] = sens_summary

    # ---- 8. qualitative inspection: English pair -----------------------------
    logger.info("Metric 8: qualitative longest-arc inspection (English ESLSpok vs EWT)")
    qual = {}
    for role, tb in [("spoken", "en_eslspok"), ("written", "en_ewt")]:
        sub = arc_df[arc_df.treebank_id == tb].dropna(subset=["norm_dist"])
        if len(sub) < 20:
            qual[role] = {"status": "insufficient_data"}
            continue
        thresh = float(sub["norm_dist"].quantile(0.95))
        longest = sub[sub["norm_dist"] > thresh].copy()
        sampled = longest.sample(n=min(20, len(longest)), random_state=42)
        sampled["category"] = sampled.apply(lambda r: L.categorize_arc(r["deprel"], bool(r["sent_has_intj"])), axis=1)
        counts = sampled["category"].value_counts().to_dict()
        qual[role] = {
            "p95_threshold": thresh,
            "n_sampled": int(len(sampled)),
            "category_counts": {k: int(v) for k, v in counts.items()},
            "examples": sampled[["sent_id", "deprel", "norm_dist"]].head(10).to_dict("records"),
        }
    metrics["qualitative_longest_arc_inspection"] = qual

    return metrics


def flatten_agg(metrics: dict) -> dict[str, float]:
    """Flatten the headline numeric results into metrics_agg (schema requires all-number)."""
    agg: dict[str, float] = {}
    for name, res in metrics["decile_paired_tests"].items():
        if res.get("status") == "ok":
            agg[f"{name}_wilcoxon_p_raw"] = res["wilcoxon_p_raw"]
            agg[f"{name}_wilcoxon_p_holm"] = res.get("wilcoxon_p_holm", float("nan"))
            agg[f"{name}_wilcoxon_effect_r"] = res["wilcoxon_effect_r"]
            agg[f"{name}_paired_t_p"] = res["paired_t_p"]
            agg[f"{name}_mean_diff"] = res["mean_diff_spoken_minus_written"]
    for name, e in metrics["language_level_tally"].items():
        if e["xi_spoken"] is not None:
            agg[f"{name}_xi_spoken"] = e["xi_spoken"]
            agg[f"{name}_xi_written"] = e["xi_written"]
        agg[f"{name}_mdd_spoken"] = e["mdd_spoken"]
        agg[f"{name}_mdd_written"] = e["mdd_written"]
    agg["n_pairs_spoken_lighter_tail"] = float(metrics["n_pairs_spoken_lighter_tail"])
    agg["n_pairs_spoken_heavier_tail"] = float(metrics["n_pairs_spoken_heavier_tail"])
    agg["n_pairs_spoken_higher_mdd"] = float(metrics["n_pairs_spoken_higher_mdd"])
    if "xi_alpha_correlation" in metrics and "r" in metrics["xi_alpha_correlation"]:
        agg["xi_alpha_correlation_r"] = metrics["xi_alpha_correlation"]["r"]
        agg["xi_alpha_correlation_p"] = metrics["xi_alpha_correlation"]["p"]
    if "xi_paired_ttest_across_pairs" in metrics:
        agg["xi_paired_ttest_t"] = metrics["xi_paired_ttest_across_pairs"]["t"]
        agg["xi_paired_ttest_p"] = metrics["xi_paired_ttest_across_pairs"]["p"]
    if "size_vs_effect_magnitude_correlation" in metrics:
        agg["size_vs_effect_magnitude_r"] = metrics["size_vs_effect_magnitude_correlation"]["r"]
    n_wins_gpd = sum(1 for m in metrics["treebank_tail_models"].values() if m.get("akaike", {}).get("winner") == "GPD")
    n_total_akaike = sum(1 for m in metrics["treebank_tail_models"].values() if "akaike" in m)
    agg["n_treebanks_gpd_wins"] = float(n_wins_gpd)
    agg["n_treebanks_with_model_comparison"] = float(n_total_akaike)
    for name, ks in metrics["sentence_length_distribution_ks"].items():
        agg[f"{name}_length_ks_stat"] = ks["ks_stat"]
        agg[f"{name}_length_ks_p"] = ks["ks_p"]
    n_flagged = sum(1 for v in metrics["annotation_reliability_check"].values() if v["flagged"])
    agg["n_pairs_flagged_annotation_reliability"] = float(n_flagged)
    n_dir_changed = sum(1 for v in metrics["robustness_exclude_flat_list"].values() if v.get("direction_changed_vs_full"))
    agg["n_pairs_direction_changed_excl_flat_list"] = float(n_dir_changed)
    agg["n_treebanks_below_1000_arcs"] = float(len(metrics["robustness_small_treebank_exclusion"]["small_treebanks_lt_1000_arcs"]))
    clean: dict[str, float] = {}
    for k, v in agg.items():
        if v is None:
            clean[k] = 0.0
        else:
            fv = float(v)
            clean[k] = 0.0 if np.isnan(fv) else fv
    return clean


def build_output_examples(metrics: dict) -> list[dict]:
    pair_examples = []
    for name, spec in L.MATCHED_PAIRS.items():
        pair_examples.append(
            {
                "input": f"Matched register pair: {name} ({spec['spoken']} spoken vs {spec['written']} written), family={spec['family']}",
                "output": json.dumps(
                    {
                        "decile_paired_test": metrics["decile_paired_tests"].get(name),
                        "language_level_tally": metrics["language_level_tally"].get(name),
                        "sentence_length_ks": metrics["sentence_length_distribution_ks"].get(name),
                        "stratified_by_deprel": metrics["stratified_by_deprel"].get(name),
                        "annotation_reliability": metrics["annotation_reliability_check"].get(name),
                        "robustness_exclude_flat_list": metrics["robustness_exclude_flat_list"].get(name),
                    }
                ),
                "metadata_pair_name": name,
                "metadata_family": spec["family"],
                "eval_wilcoxon_p_raw": metrics["decile_paired_tests"].get(name, {}).get("wilcoxon_p_raw", -1.0) or -1.0,
                "eval_wilcoxon_effect_r": metrics["decile_paired_tests"].get(name, {}).get("wilcoxon_effect_r", 0.0) or 0.0,
            }
        )
    treebank_examples = []
    for tb, m in metrics["treebank_tail_models"].items():
        treebank_examples.append(
            {
                "input": f"Tail-shape model comparison for treebank {tb}",
                "output": json.dumps(m),
                "metadata_treebank_id": tb,
                "eval_xi": m["gpd"].get("xi", 0.0) if m["gpd"].get("status") == "ok" else 0.0,
                "eval_alpha": m["powerlaw"].get("alpha", 0.0) if m["powerlaw"].get("status") == "ok" else 0.0,
                "eval_n_normalized_distances": float(m["n_normalized_distances"]),
            }
        )
    qual_examples = [
        {
            "input": "Qualitative inspection of the 20 longest-distance arcs (>p95) per register, English ESLSpok vs EWT",
            "output": json.dumps(metrics["qualitative_longest_arc_inspection"]),
            "metadata_pair_name": "english",
            "eval_n_categories_spoken": float(len(metrics["qualitative_longest_arc_inspection"].get("spoken", {}).get("category_counts", {}))),
        }
    ]
    return pair_examples, treebank_examples, qual_examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(WORKDIR / "full_data_out.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--n-boot", type=int, default=300)
    parser.add_argument("--out", default=str(WORKDIR / "eval_out.json"))
    args = parser.parse_args()

    set_memory_limit(gb=6.0)

    examples = L.load_examples(Path(args.data), limit=args.limit)
    sent_df, arc_df = L.build_frames(examples)
    metrics = run_full_analysis(sent_df, arc_df, n_boot=args.n_boot)
    agg = flatten_agg(metrics)
    pair_ex, tb_ex, qual_ex = build_output_examples(metrics)

    output = {
        "metadata": {
            "evaluation_name": "Register Effects on Tail Shape, Corrected Unit",
            "description": (
                "Corrected decile-level paired tests, GPD xi vs power-law alpha tail models, "
                "and stratified/robustness analyses of the spoken-vs-written dependency-distance register effect "
                "across 4 matched UD treebank pairs and 18 treebanks total."
            ),
            "n_sentences": int(len(sent_df)),
            "n_arcs": int(len(arc_df)),
            "n_treebanks": int(sent_df["treebank_id"].nunique()),
        },
        "metrics_agg": agg,
        "datasets": [
            {"dataset": "matched_register_pairs", "examples": pair_ex},
            {"dataset": "treebank_tail_models", "examples": tb_ex},
            {"dataset": "qualitative_longest_arc_inspection", "examples": qual_ex},
        ],
    }
    Path(args.out).write_text(json.dumps(output, indent=2, allow_nan=False))
    logger.info(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
