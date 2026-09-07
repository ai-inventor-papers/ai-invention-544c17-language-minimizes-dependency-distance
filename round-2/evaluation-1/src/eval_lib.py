"""Helper functions for the register/tail-shape evaluation (eval.py).

Kept separate from eval.py to respect the repo's per-module line cap.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats

# ---------------------------------------------------------------------------
# Matched spoken/written pairs, as specified in the artifact plan.
# ---------------------------------------------------------------------------
MATCHED_PAIRS = {
    "slovenian": {"spoken": "sl_sst", "written": "sl_ssj", "family": "Indo-European (Slavic)"},
    "french": {"spoken": "fr_rhapsodie", "written": "fr_gsd", "family": "Indo-European (Romance)"},
    "english": {"spoken": "en_eslspok", "written": "en_ewt", "family": "Indo-European (Germanic)"},
    "turkish": {"spoken": "tr_atis", "written": "tr_imst", "family": "Turkic"},
}

FLAT_LIST_DEPRELS = {"flat", "list"}
MAJOR_DEPRELS = [
    "nsubj", "obj", "iobj", "obl", "nmod", "amod", "advmod",
    "acl", "advcl", "conj", "compound", "case", "mark", "det",
]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_examples(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    logger.info(f"Loading {path}")
    raw = json.loads(path.read_text())
    examples = raw["datasets"][0]["examples"]
    if limit is not None:
        examples = examples[:limit]
    logger.info(f"Loaded {len(examples)} examples")
    return examples


def build_frames(examples: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (sentence_df, arc_df) parsed from the raw example rows."""
    sent_rows = []
    arc_rows = []
    for i, ex in enumerate(examples):
        try:
            inp = json.loads(ex["input"])
            out = json.loads(ex["output"])
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"Skipping malformed example {i}")
            continue
        tb = ex["metadata_treebank_id"]
        reg = ex["metadata_register"]
        lang = ex["metadata_language"]
        fam = ex["metadata_language_family"]
        slen = ex["metadata_sentence_length"]
        norm_dists = out.get("normalized_distances", [])
        raw_dists = out.get("dependency_distances", [])
        deprels = out.get("deprel", [])
        upos = inp.get("upos", [])
        sent_rows.append(
            {
                "sent_id": i,
                "treebank_id": tb,
                "language": lang,
                "family": fam,
                "register": reg,
                "sentence_length": slen,
                "num_arcs": ex["metadata_num_arcs"],
                "mean_norm_dist": float(np.mean(norm_dists)) if norm_dists else np.nan,
                "has_intj": bool(set(upos) & {"INTJ"}),
                "norm_dists": norm_dists,
            }
        )
        n = min(len(norm_dists), len(deprels))
        has_intj_arc = "INTJ" in upos
        for k in range(n):
            arc_rows.append(
                {
                    "sent_id": i,
                    "treebank_id": tb,
                    "language": lang,
                    "family": fam,
                    "register": reg,
                    "sentence_length": slen,
                    "norm_dist": norm_dists[k],
                    "raw_dist": raw_dists[k] if k < len(raw_dists) else np.nan,
                    "deprel": deprels[k],
                    "sent_has_intj": has_intj_arc,
                }
            )
    sent_df = pd.DataFrame(sent_rows)
    arc_df = pd.DataFrame(arc_rows)
    logger.info(f"Built sentence_df={len(sent_df)} rows, arc_df={len(arc_df)} rows")
    return sent_df, arc_df


# ---------------------------------------------------------------------------
# Metric 1: decile-level paired Wilcoxon / t-test (corrects pseudo-replication)
# ---------------------------------------------------------------------------
def decile_paired_test(sent_df: pd.DataFrame, spoken_id: str, written_id: str) -> dict[str, Any]:
    sub = sent_df[sent_df["treebank_id"].isin([spoken_id, written_id])].copy()
    sub = sub.dropna(subset=["mean_norm_dist", "sentence_length"])
    if len(sub) < 20:
        return {"status": "insufficient_data", "n_sentences": int(len(sub))}
    try:
        sub["decile"] = pd.qcut(sub["sentence_length"], 10, labels=False, duplicates="drop")
    except ValueError:
        return {"status": "insufficient_length_variation", "n_sentences": int(len(sub))}
    n_deciles_available = sub["decile"].nunique()

    agg = sub.groupby(["decile", "register"])["mean_norm_dist"].mean().unstack("register")
    spoken_reg = sub.loc[sub.treebank_id == spoken_id, "register"].iloc[0]
    written_reg = sub.loc[sub.treebank_id == written_id, "register"].iloc[0]
    agg = agg.dropna(subset=[spoken_reg, written_reg]) if (spoken_reg in agg.columns and written_reg in agg.columns) else pd.DataFrame()
    if len(agg) < 4:
        return {"status": "insufficient_paired_deciles", "n_deciles_available": int(n_deciles_available)}

    x_spoken = agg[spoken_reg].to_numpy()
    y_written = agg[written_reg].to_numpy()
    n_pairs = len(agg)

    diffs = x_spoken - y_written
    try:
        wil = stats.wilcoxon(x_spoken, y_written, zero_method="wilcox", correction=False, method="approx")
        z = wil.zstatistic if hasattr(wil, "zstatistic") else np.nan
        p_wil = float(wil.pvalue)
    except ValueError:
        z, p_wil = np.nan, 1.0
    effect_r = float(z / math.sqrt(n_pairs)) if z is not None and not np.isnan(z) else np.nan

    tt = stats.ttest_rel(x_spoken, y_written)
    mean_diff = float(np.mean(diffs))
    se_diff = float(np.std(diffs, ddof=1) / math.sqrt(n_pairs)) if n_pairs > 1 else np.nan
    tcrit = stats.t.ppf(0.975, df=n_pairs - 1) if n_pairs > 1 else np.nan
    ci_lo = mean_diff - tcrit * se_diff if not np.isnan(se_diff) else np.nan
    ci_hi = mean_diff + tcrit * se_diff if not np.isnan(se_diff) else np.nan

    return {
        "status": "ok",
        "n_deciles": int(n_pairs),
        "spoken_treebank": spoken_id,
        "written_treebank": written_id,
        "wilcoxon_Z": float(z) if z is not None else float("nan"),
        "wilcoxon_p_raw": p_wil,
        "wilcoxon_effect_r": effect_r,
        "paired_t_stat": float(tt.statistic),
        "paired_t_p": float(tt.pvalue),
        "mean_diff_spoken_minus_written": mean_diff,
        "diff_95ci_lo": float(ci_lo),
        "diff_95ci_hi": float(ci_hi),
        "direction": "spoken>written (heavier)" if mean_diff > 0 else "spoken<written (lighter)",
        "decile_means_spoken": [float(v) for v in x_spoken],
        "decile_means_written": [float(v) for v in y_written],
    }


def holm_bonferroni(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    corrected = {}
    running_max = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running_max = max(running_max, adj)
        corrected[name] = float(running_max)
    return corrected


# ---------------------------------------------------------------------------
# Metric 2: GPD shape parameter xi via MRL-informed threshold + MLE + bootstrap
# ---------------------------------------------------------------------------
def mean_residual_life(x: np.ndarray, quantiles: np.ndarray) -> list[dict[str, float]]:
    out = []
    for q in quantiles:
        u = float(np.quantile(x, q))
        excess = x[x > u] - u
        if len(excess) < 5:
            continue
        out.append({"quantile": float(q), "threshold": u, "mean_excess": float(np.mean(excess)), "n_exceed": int(len(excess))})
    return out


def choose_threshold_from_mrl(mrl: list[dict[str, float]]) -> float:
    """Pick the lowest quantile beyond which the MRL curve is roughly linear
    (slope of mean-excess changes by <20% over the next 3 candidate points)."""
    if len(mrl) < 4:
        return mrl[0]["quantile"] if mrl else 0.90
    means = [m["mean_excess"] for m in mrl]
    for i in range(len(means) - 3):
        window = means[i : i + 4]
        slopes = np.diff(window)
        if np.all(np.abs(slopes) < 0.5 * (abs(window[0]) + 1e-9)):
            return mrl[i]["quantile"]
    return mrl[len(mrl) // 2]["quantile"]


def fit_gpd(x: np.ndarray, threshold_q: float, n_boot: int = 300, rng: np.random.Generator | None = None) -> dict[str, Any]:
    rng = rng or np.random.default_rng(0)
    u = float(np.quantile(x, threshold_q))
    excess = x[x > u] - u
    excess = excess[excess > 0]
    if len(excess) < 15:
        return {"status": "insufficient_exceedances", "n_exceed": int(len(excess)), "threshold": u}
    try:
        xi, _loc, sigma = stats.genpareto.fit(excess, floc=0)
    except (RuntimeError, ValueError) as e:
        return {"status": f"fit_failed: {e}", "n_exceed": int(len(excess)), "threshold": u}
    loglik = float(np.sum(stats.genpareto.logpdf(excess, xi, loc=0, scale=sigma)))
    aic = 2 * 2 - 2 * loglik

    n = len(excess)
    boot_xi = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(excess, size=n, replace=True)
        try:
            bxi, _, _ = stats.genpareto.fit(sample, floc=0)
        except (RuntimeError, ValueError):
            bxi = np.nan
        boot_xi[b] = bxi
    boot_xi = boot_xi[~np.isnan(boot_xi)]
    ci_lo, ci_hi = (float(np.percentile(boot_xi, 2.5)), float(np.percentile(boot_xi, 97.5))) if len(boot_xi) > 20 else (float("nan"), float("nan"))

    return {
        "status": "ok",
        "threshold_quantile": float(threshold_q),
        "threshold": u,
        "n_exceed": int(n),
        "xi": float(xi),
        "sigma": float(sigma),
        "loglik": loglik,
        "aic": float(aic),
        "xi_ci95_lo": ci_lo,
        "xi_ci95_hi": ci_hi,
    }


# ---------------------------------------------------------------------------
# Metric 6: power-law tail (Clauset-Shalizi-Newman-style continuous MLE)
# ---------------------------------------------------------------------------
def fit_powerlaw(x: np.ndarray, threshold_q: float) -> dict[str, Any]:
    xmin = float(np.quantile(x, threshold_q))
    tail = x[x >= xmin]
    tail = tail[tail > 0]
    n = len(tail)
    if n < 15 or xmin <= 0:
        return {"status": "insufficient_data", "n_tail": int(n)}
    logs = np.log(tail / xmin)
    alpha = 1.0 + n / np.sum(logs)
    loglik = float(n * np.log(alpha - 1) - n * np.log(xmin) - alpha * np.sum(np.log(tail / xmin)))
    # AIC for a single-parameter continuous power law fit on the same tail sample
    aic = 2 * 1 - 2 * loglik
    # KS statistic between empirical tail CDF and fitted power-law CDF
    sorted_tail = np.sort(tail)
    ecdf = np.arange(1, n + 1) / n
    fitted_cdf = 1 - (sorted_tail / xmin) ** (1 - alpha)
    ks = float(np.max(np.abs(ecdf - fitted_cdf)))
    return {
        "status": "ok",
        "xmin_quantile": float(threshold_q),
        "xmin": xmin,
        "n_tail": int(n),
        "alpha": float(alpha),
        "loglik": loglik,
        "aic": float(aic),
        "ks_stat": ks,
    }


def akaike_weights(aic_gpd: float, aic_pl: float) -> dict[str, float]:
    aics = np.array([aic_gpd, aic_pl])
    delta = aics - np.min(aics)
    w = np.exp(-0.5 * delta)
    w = w / np.sum(w)
    return {"w_gpd": float(w[0]), "w_powerlaw": float(w[1]), "winner": "GPD" if w[0] > w[1] else "power-law"}


# ---------------------------------------------------------------------------
# Metric 8: qualitative categorisation of long-distance arcs by deprel heuristic
# ---------------------------------------------------------------------------
def categorize_arc(deprel: str, has_intj: bool) -> str:
    if has_intj:
        return "disfluency/filler"
    if deprel in {"acl", "acl:relcl"}:
        return "long-distance relative clause"
    if deprel in {"flat", "list", "conj", "appos"}:
        return "coordination/apposition"
    if deprel in {"advcl", "obl", "obl:agent"}:
        return "extraposition"
    if deprel in {"nsubj", "csubj", "obj"}:
        return "topicalization/scrambling"
    return "other"
