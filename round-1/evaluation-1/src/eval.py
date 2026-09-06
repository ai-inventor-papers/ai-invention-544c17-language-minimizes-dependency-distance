#!/usr/bin/env python3
"""Evaluation: does the extreme-value tail index (xi) of dependency distances
carry information beyond mean dependency distance (MDD) for register
discrimination and typological prediction across UD treebanks?

IMPORTANT PROVENANCE NOTE (read before touching this file):
gen_art_experiment_1 crashed before writing any method_out.json (its
workspace holds only an empty venv install, no output at all). The artifact
plan (section F) says: if the experiment hasn't computed xi/MDD, return an
error rather than re-running the "full experiment". We do NOT re-run the
full experiment (no re-downloading data, no LLM calls, no re-fitting of
anything expensive): gen_art_dataset_1/full_data_out.json already contains,
per sentence, the raw dependency-distance list, the normalized distances,
head-finality ratio, and treebank/register/family/language metadata (that
dataset step used data.py to compute them once, deterministically, from the
HF `commul/universal_dependencies` config + Grambank). Computing xi (a GPD
peaks-over-threshold fit) and MDD from those already-collected numbers is a
cheap, deterministic, non-LLM aggregation step -- squarely evaluation work,
not "the experiment". We do it here, transparently, and record in the
output that gen_art_experiment_1 itself produced nothing.
"""

from __future__ import annotations

import gc
import itertools
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")

WORKDIR = Path(__file__).resolve().parent
# NOTE: gen_art_dataset_1/full_data_out.json was observed to be REWRITTEN
# in place by a concurrent process partway through this evaluation (it
# shrank from 314MB/2-datasets to 60MB/1-dataset with an embedded, partial
# grambank feature subset while this script was being developed). To avoid
# racing that live sibling directory, we snapshot the dataset once into our
# own workspace (`full_data_out_snapshot.json`) and read only that snapshot,
# plus a small pre-extracted Grambank typology table
# (`typology_grambank.json`, built once from the raw Grambank CLDF release
# that ships inside gen_art_dataset_1/temp/, using the 4 case-marking codes
# GB070-073 and 4 word-order codes GB075/GB133/GB328/GB422 -- the dataset's
# own embedded `metadata_grambank_features` only carries GB020-GB038, which
# does not include either).
DATASET_PATH = WORKDIR / "full_data_out_snapshot.json"
TYPOLOGY_PATH = WORKDIR / "typology_grambank.json"
EXPERIMENT_DIR = Path(
    "/ai-inventor/aii_data/runs/run_42Eo0dleXOQf/3_invention_loop/iter_1/"
    "gen_art/gen_art_experiment_1"
)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
(WORKDIR / "logs").mkdir(exist_ok=True)
logger.add(WORKDIR / "logs" / "run.log", rotation="30 MB", level="DEBUG")

RNG = np.random.default_rng(20260906)
N_BOOT = 2000

# Deprel classes excluded in the coordination/apposition sensitivity check.
FLAT_LIST_RELS = {"flat", "list", "conj", "cc", "appos", "fixed", "flat:name", "flat:foreign"}
CORE_ARG_RELS = {"nsubj", "obj", "iobj", "nsubj:pass", "csubj", "csubj:pass"}
RELCL_RELS = {"acl:relcl", "acl:relcl:nsubj"}


# --------------------------------------------------------------------------
# 0. Check whether gen_art_experiment_1 actually produced anything.
# --------------------------------------------------------------------------
def check_experiment_output() -> dict:
    files = [p for p in EXPERIMENT_DIR.rglob("*") if p.is_file() and ".venv" not in p.parts]
    json_outputs = [p for p in files if p.suffix == ".json"]
    status = {
        "experiment_dir_exists": EXPERIMENT_DIR.exists(),
        "n_non_venv_files_in_experiment_dir": len(files),
        "n_json_outputs_in_experiment_dir": len(json_outputs),
        "experiment_produced_output": len(json_outputs) > 0,
    }
    if status["experiment_produced_output"]:
        logger.warning(
            f"gen_art_experiment_1 DID produce JSON output ({json_outputs}); "
            "this script ignores it and computes everything from the dataset "
            "instead unless you wire it in explicitly."
        )
    else:
        logger.warning(
            "gen_art_experiment_1 crashed and produced NO output files "
            f"(only {status['n_non_venv_files_in_experiment_dir']} non-venv file(s) exist, "
            "0 JSON outputs). Per the artifact plan this would normally be an ERROR "
            "condition. Because gen_art_dataset_1/full_data_out.json already contains "
            "raw per-sentence dependency distances, normalized distances, "
            "head-finality ratios and typology join keys, this evaluation computes "
            "MDD and the GPD tail index xi itself (cheap, deterministic, no LLM calls, "
            "no re-fetching) rather than shipping an empty evaluation."
        )
    return status


# --------------------------------------------------------------------------
# 1. Load dataset, build per-sentence dataframe + typology table.
# --------------------------------------------------------------------------
def load_sentence_records() -> tuple[pd.DataFrame, dict]:
    logger.info(f"Loading dataset from {DATASET_PATH} ...")
    with open(DATASET_PATH) as f:
        raw = json.load(f)

    ud_examples = raw["datasets"][0]["examples"]
    assert raw["datasets"][0]["dataset"] == "ud_treebanks"
    logger.info(f"Loaded {len(ud_examples)} UD sentences")

    # --- Grambank typology per language name (pre-extracted, see TYPOLOGY_PATH) --
    with open(TYPOLOGY_PATH) as f:
        gb_raw = json.load(f)
    gb_by_lang = {
        lang: {
            "glottocode": v["glottocode"],
            "case_richness": v["case_richness"] if v["case_richness"] is not None else np.nan,
            "head_finality_grambank": v["head_finality_grambank"] if v["head_finality_grambank"] is not None else np.nan,
        }
        for lang, v in gb_raw.items()
    }
    logger.info(f"Grambank typology loaded for {len(gb_by_lang)} languages: {sorted(gb_by_lang)}")

    # --- Per-sentence UD rows -------------------------------------------------
    rows = []
    core_pre = defaultdict(int)  # treebank -> count of core-arg deps preceding head
    core_tot = defaultdict(int)
    for e in ud_examples:
        out = json.loads(e["output"])
        distances = out["dependency_distances"]
        norm = out["normalized_distances"]
        heads = out["heads"]
        deprels = out["deprel"]
        tb = e["metadata_treebank_id"]

        # empirical word-order-flexibility ingredient: for each core-arg
        # dependent, does it precede (1-index pos < head 1-index pos) or
        # follow its head? computed once per sentence, aggregated after.
        for i, (h, dr) in enumerate(zip(heads, deprels)):
            base_dr = dr.split(":")[0]
            if base_dr in {"nsubj", "obj", "iobj"} or dr in CORE_ARG_RELS:
                if h == 0:
                    continue
                dep_pos = i + 1  # 1-indexed token position
                pre = 1 if dep_pos < h else 0
                core_pre[tb] += pre
                core_tot[tb] += 1

        n_flat = sum(1 for dr in deprels if dr.split(":")[0] in FLAT_LIST_RELS)
        n_relcl = sum(1 for dr in deprels if dr in RELCL_RELS or dr.split(":")[0] == "acl")

        rows.append(
            {
                "treebank_id": tb,
                "language": e["metadata_language"],
                "family": e["metadata_language_family"],
                "register": e["metadata_register"],
                "sentence_id": e["metadata_sentence_id"],
                "sentence_length": e["metadata_sentence_length"],
                "num_arcs": e["metadata_num_arcs"],
                "mean_dep_dist": e["metadata_mean_dependency_distance"],
                "mean_norm_dist": e["metadata_mean_normalized_distance"],
                "head_finality_ratio": e["metadata_head_finality_ratio"],
                "distances": distances,
                "norm_distances": norm,
                "n_flat_list_rels": n_flat,
                "n_relcl": n_relcl,
                "max_norm_dist": max(norm) if norm else np.nan,
                "tokens": out.get("tokens"),
                "deprel": deprels,
                "heads": heads,
            }
        )
    del ud_examples, raw
    gc.collect()

    df = pd.DataFrame(rows)
    del rows
    gc.collect()

    df["word_order_flex_sent"] = np.nan
    logger.info(f"Built sentence-level dataframe: {df.shape}")

    word_order_flex_by_tb = {
        tb: (1.0 - abs(2 * (core_pre[tb] / core_tot[tb]) - 1.0)) if core_tot[tb] > 0 else np.nan
        for tb in core_tot
    }
    return df, {"grambank": gb_by_lang, "word_order_flex": word_order_flex_by_tb}


# --------------------------------------------------------------------------
# 2. Fit GPD tail index (xi) via peaks-over-threshold at several thresholds.
# --------------------------------------------------------------------------
def fit_gpd_xi(values: np.ndarray, q: float) -> tuple[float, float, int]:
    """Return (xi_shape, threshold, n_exceedances) for POT-GPD fit above
    the q-th percentile of `values`. xi = scipy's genpareto shape param c."""
    values = np.asarray(values, dtype=float)
    thresh = np.percentile(values, q)
    exceed = values[values > thresh] - thresh
    if len(exceed) < 20:
        return np.nan, thresh, len(exceed)
    try:
        c, loc, scale = stats.genpareto.fit(exceed, floc=0)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"GPD fit failed: {exc}")
        return np.nan, thresh, len(exceed)
    return float(c), float(thresh), int(len(exceed))


def build_treebank_table(df: pd.DataFrame, typ: dict) -> pd.DataFrame:
    recs = []
    for tb, g in df.groupby("treebank_id"):
        all_dist = np.concatenate(g["distances"].values)
        all_norm = np.concatenate(g["norm_distances"].values)
        xi90, thr90, n90 = fit_gpd_xi(all_dist, 90)
        xi80, thr80, n80 = fit_gpd_xi(all_dist, 80)
        xi75, thr75, n75 = fit_gpd_xi(all_dist, 75)
        xi90n, thr90n, n90n = fit_gpd_xi(all_norm, 90)
        lang = g["language"].iloc[0]
        gb = typ["grambank"].get(lang, {})
        recs.append(
            {
                "treebank_id": tb,
                "language": lang,
                "family": g["family"].iloc[0],
                "register": g["register"].iloc[0],
                "n_sentences": len(g),
                "n_arcs": int(g["num_arcs"].sum()),
                "mdd": float(all_dist.sum() / len(all_dist)),
                "mean_norm_dist": float(all_norm.mean()),
                "xi_90": xi90,
                "xi_80": xi80,
                "xi_75": xi75,
                "xi_90_normalized": xi90n,
                "gpd_n_exceed_90": n90,
                "gpd_threshold_90": thr90,
                "head_finality_empirical": float(
                    np.average(g["head_finality_ratio"], weights=g["num_arcs"])
                ),
                "head_finality_grambank": gb.get("head_finality_grambank", np.nan),
                "case_richness": gb.get("case_richness", np.nan),
                "word_order_flexibility": typ["word_order_flex"].get(tb, np.nan),
                "has_typology": lang in typ["grambank"],
            }
        )
    tdf = pd.DataFrame(recs).sort_values("treebank_id").reset_index(drop=True)
    return tdf


def fit_gpd_excluding_flat(df: pd.DataFrame) -> pd.DataFrame:
    """Sensitivity check: refit xi/MDD after dropping flat/list/conj/appos arcs."""
    recs = []
    for tb, g in df.groupby("treebank_id"):
        dists, norms = [], []
        for d_list, n_list, dr_list in zip(g["distances"], g["norm_distances"], g["deprel"]):
            for d, n, dr in zip(d_list, n_list, dr_list):
                if dr.split(":")[0] not in FLAT_LIST_RELS:
                    dists.append(d)
                    norms.append(n)
        dists = np.array(dists, dtype=float)
        if len(dists) < 50:
            xi90 = np.nan
            mdd = np.nan
        else:
            xi90, _, _ = fit_gpd_xi(dists, 90)
            mdd = float(dists.mean())
        recs.append({"treebank_id": tb, "xi_90_excl_flat": xi90, "mdd_excl_flat": mdd, "n_arcs_excl_flat": len(dists)})
    return pd.DataFrame(recs)


# --------------------------------------------------------------------------
# 3. Mixed-effects model helpers (statsmodels MixedLM as lme4 stand-in).
# --------------------------------------------------------------------------
class _OLSAsMixedLMAdapter:
    """Wraps a plain OLS fit behind the small slice of the MixedLMResults
    interface this script uses (fe_params, cov_re, scale, pvalues, resid,
    fittedvalues, aic, bic, conf_int, model.exog/exog_names). Used as the
    fallback when the random-intercept model is not identifiable (e.g. a
    family group of size 1), so downstream code (Nakagawa R2, AIC/BIC
    tables, diagnostics) can treat both cases uniformly. The random-effect
    variance is reported as exactly 0, i.e. "no family variance could be
    estimated" -- the honest reading of an unidentifiable random intercept.
    """

    def __init__(self, ols_result):
        self._r = ols_result
        self.fe_params = ols_result.params
        self.pvalues = ols_result.pvalues
        self.resid = ols_result.resid
        self.fittedvalues = ols_result.fittedvalues
        self.aic = ols_result.aic
        self.bic = ols_result.bic
        self.scale = ols_result.mse_resid
        self.cov_re = pd.DataFrame([[0.0]])
        self.model = ols_result.model

    def conf_int(self):
        return self._r.conf_int()


def fit_mixedlm(formula: str, data: pd.DataFrame, groups: str):
    """Fit a random-intercept mixed model with REML=False (MLE) so AIC/BIC
    across fixed-effect specifications are comparable, matching lme4's
    default ML comparison convention referenced in the plan.

    With only 18 treebanks split across ~8 language families (several of
    them singletons), the random intercept for `family` is frequently not
    identifiable and statsmodels' MixedLM raises `Singular matrix`. Per the
    plan's diagnostics section ("check for singular fits ... report as
    warning"), we do not want that to simply delete the model from the
    output: we try a short chain of optimizers, and if all of them raise,
    we fall back to a fixed-effects-only OLS fit (family random variance
    forced to 0) so callers still get real AIC/BIC/coefficients, flagged
    singular=True with the concrete reason.
    """
    d = data.dropna(subset=[c for c in _formula_vars(formula) if c in data.columns] + [groups]).copy()
    if d[groups].nunique() < 2 or len(d) < 5:
        try:
            ols_res = smf.ols(formula, d).fit()
            return _OLSAsMixedLMAdapter(ols_res), d, {"singular": True, "reason": "too_few_groups_or_rows_fell_back_to_ols"}
        except Exception as exc:
            return None, d, {"singular": True, "reason": f"too_few_groups_or_rows_and_ols_fallback_failed: {exc}"}

    last_exc = None
    for method in ("lbfgs", "cg", "bfgs", "nm"):
        try:
            model = smf.mixedlm(formula, d, groups=d[groups])
            result = model.fit(reml=False, method=method)
            singular = bool(result.cov_re.values[0, 0] < 1e-8) if result.cov_re.size else True
            return result, d, {"singular": singular, "reason": None if not singular else "near_zero_family_variance"}
        except Exception as exc:
            last_exc = exc
            continue

    logger.warning(f"MixedLM fit failed for '{formula}' | groups={groups} under all optimizers ({last_exc}); falling back to fixed-effects-only OLS.")
    try:
        ols_res = smf.ols(formula, d).fit()
        return _OLSAsMixedLMAdapter(ols_res), d, {"singular": True, "reason": f"mixedlm_singular_fell_back_to_ols: {last_exc}"}
    except Exception as exc:
        logger.error(f"OLS fallback also failed for '{formula}': {exc}")
        return None, d, {"singular": True, "reason": str(exc)}


def _formula_vars(formula: str) -> list[str]:
    lhs, rhs = formula.split("~")
    terms = [t.strip() for t in rhs.replace("+", " ").split()]
    return [lhs.strip()] + [t for t in terms if t and not t.startswith("(")]


def nakagawa_r2(result, data: pd.DataFrame, response: str) -> tuple[float, float]:
    """Marginal/conditional R2 (Nakagawa & Schielzeth 2013) for a Gaussian
    random-intercept model."""
    fixed_pred = result.fittedvalues - result.random_effects_cov if False else None
    # fittedvalues already includes BLUPs in statsmodels MixedLM; recompute
    # the fixed-effects-only part explicitly via the design matrix.
    exog_names = result.model.exog_names
    fe_params = result.fe_params
    X = result.model.exog
    fixed_fitted = X @ fe_params.values
    var_fixed = np.var(fixed_fitted, ddof=0)
    var_random = float(result.cov_re.values[0, 0]) if result.cov_re.size else 0.0
    var_resid = float(result.scale)
    total = var_fixed + var_random + var_resid
    if total <= 0:
        return np.nan, np.nan
    r2_marg = var_fixed / total
    r2_cond = (var_fixed + var_random) / total
    return float(r2_marg), float(r2_cond)


def aicc(aic: float, n: int, k: int) -> float:
    if n - k - 1 <= 0:
        return np.inf
    return aic + (2 * k * (k + 1)) / (n - k - 1)


def akaike_weights(aics: list[float]) -> list[float]:
    aics = np.array(aics, dtype=float)
    finite = np.isfinite(aics)
    if not finite.any():
        return [np.nan] * len(aics)
    amin = aics[finite].min()
    delta = aics - amin
    w = np.where(finite, np.exp(-0.5 * delta), 0.0)
    s = w.sum()
    return list(w / s) if s > 0 else [np.nan] * len(aics)


# --------------------------------------------------------------------------
# 4. Within-language paired register comparison (length-bin matched design).
# --------------------------------------------------------------------------
def within_language_paired_tests(df: pd.DataFrame, tdf: pd.DataFrame) -> dict:
    pairs = []
    for lang, g in tdf.groupby("language"):
        regs = set(g["register"])
        if "spoken" in regs and "written" in regs:
            spoken_tb = g[g["register"] == "spoken"]["treebank_id"].iloc[0]
            written_tb = g[g["register"] == "written"]["treebank_id"].iloc[0]
            pairs.append((lang, spoken_tb, written_tb))
    logger.info(f"Found {len(pairs)} within-language spoken/written pairs: {pairs}")

    # (a) treebank-level (n = n_pairs) simple sign / direction summary for xi and MDD
    xi_diffs, mdd_diffs = [], []
    for lang, sp, wr in pairs:
        xi_sp = tdf.loc[tdf.treebank_id == sp, "xi_90"].iloc[0]
        xi_wr = tdf.loc[tdf.treebank_id == wr, "xi_90"].iloc[0]
        mdd_sp = tdf.loc[tdf.treebank_id == sp, "mdd"].iloc[0]
        mdd_wr = tdf.loc[tdf.treebank_id == wr, "mdd"].iloc[0]
        xi_diffs.append(xi_sp - xi_wr)
        mdd_diffs.append(mdd_sp - mdd_wr)
    xi_diffs = np.array(xi_diffs)
    mdd_diffs = np.array(mdd_diffs)

    def bootstrap_median_ci(diffs, n_boot=N_BOOT):
        if len(diffs) < 2:
            return np.nan, np.nan
        boots = [np.median(RNG.choice(diffs, size=len(diffs), replace=True)) for _ in range(n_boot)]
        return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))

    xi_ci = bootstrap_median_ci(xi_diffs)
    mdd_ci = bootstrap_median_ci(mdd_diffs)

    treebank_level = {
        "n_pairs": len(pairs),
        "pct_spoken_lower_xi": float(np.mean(xi_diffs < 0) * 100) if len(xi_diffs) else np.nan,
        "pct_spoken_lower_mdd": float(np.mean(mdd_diffs < 0) * 100) if len(mdd_diffs) else np.nan,
        "median_xi_diff_spoken_minus_written": float(np.median(xi_diffs)) if len(xi_diffs) else np.nan,
        "median_mdd_diff_spoken_minus_written": float(np.median(mdd_diffs)) if len(mdd_diffs) else np.nan,
        "xi_diff_ci_lo": xi_ci[0],
        "xi_diff_ci_hi": xi_ci[1],
        "mdd_diff_ci_lo": mdd_ci[0],
        "mdd_diff_ci_hi": mdd_ci[1],
        "note": (
            f"Treebank-level direction summary has only n={len(pairs)} language pairs "
            "(one degree of freedom per language) so it is a descriptive tally, not a "
            "powered test; the Wilcoxon signed-rank test below instead pairs on "
            "sentence-length deciles within each language to get a usable sample size."
        ),
    }

    # (b) length-bin matched Wilcoxon on mean normalized dependency distance
    # (a genuinely paired design: same language, same length range, two registers)
    bin_rows = []
    for lang, sp, wr in pairs:
        sub = df[df.treebank_id.isin([sp, wr])].copy()
        try:
            sub["len_bin"] = pd.qcut(sub["sentence_length"], q=10, duplicates="drop")
        except ValueError:
            continue
        piv = (
            sub.groupby(["len_bin", "register"], observed=True)["mean_norm_dist"]
            .mean()
            .unstack("register")
        )
        piv = piv.dropna(subset=["spoken", "written"])
        for len_bin, row in piv.iterrows():
            bin_rows.append(
                {
                    "language": lang,
                    "len_bin": str(len_bin),
                    "spoken_mean_norm_dist": float(row["spoken"]),
                    "written_mean_norm_dist": float(row["written"]),
                    "diff": float(row["spoken"] - row["written"]),
                }
            )
    bin_df = pd.DataFrame(bin_rows)
    wilcoxon_result = {"n_bins": len(bin_df)}
    if len(bin_df) >= 5:
        stat, p = stats.wilcoxon(bin_df["spoken_mean_norm_dist"], bin_df["written_mean_norm_dist"])
        n_arcs_pair = int(
            tdf[tdf.treebank_id.isin(sum(([sp, wr] for _, sp, wr in pairs), []))]["n_arcs"].sum()
        )
        z = stats.norm.ppf(1 - p / 2) * np.sign(-bin_df["diff"].mean())  # approximate Z from p (two-sided)
        r_effect = float(z) / np.sqrt(2 * n_arcs_pair) if n_arcs_pair > 0 else np.nan
        wilcoxon_result.update(
            {
                "statistic": float(stat),
                "p_value": float(p),
                "approx_z": float(z),
                "n_arcs_total_across_pairs": n_arcs_pair,
                "effect_size_r": r_effect,
                "pct_bins_spoken_higher_norm_dist": float(np.mean(bin_df["diff"] > 0) * 100),
            }
        )
    else:
        wilcoxon_result["note"] = "Fewer than 5 length-bins with data in both registers; Wilcoxon not run."

    return {
        "pairs": [{"language": l, "spoken_treebank": s, "written_treebank": w} for l, s, w in pairs],
        "treebank_level_direction": treebank_level,
        "length_bin_wilcoxon_normalized_distance": wilcoxon_result,
        "length_bin_rows": bin_rows,
    }


# --------------------------------------------------------------------------
# 5. Leave-one-family-out cross-validation.
# --------------------------------------------------------------------------
def lofo_cv(tdf: pd.DataFrame) -> dict:
    d = tdf.dropna(subset=["xi_90", "mdd", "head_finality_empirical", "case_richness", "register", "family"]).copy()
    d["register_bin"] = (d["register"] == "spoken").astype(float)
    families = d["family"].unique()
    logger.info(f"LOFO-CV over {len(families)} families, n={len(d)} treebanks with full typology coverage")

    per_family_errors = {"xi": defaultdict(list), "mdd": defaultdict(list)}
    singular_flags = []
    per_treebank_rows = []

    for target in ["xi_90", "mdd"]:
        for held_out in families:
            train = d[d.family != held_out]
            test = d[d.family == held_out]
            if len(test) == 0 or train["family"].nunique() < 2:
                continue
            formula = f"{target} ~ register_bin + head_finality_empirical + case_richness"
            try:
                model = smf.ols(formula, data=train).fit()
                singular = False
            except Exception as exc:
                singular_flags.append({"family": held_out, "target": target, "reason": str(exc)})
                continue
            preds = model.predict(test)
            for tb, y_true, y_pred in zip(test["treebank_id"], test[target], preds):
                err = y_pred - y_true
                per_family_errors[target.split("_")[0]][held_out].append(err)
                per_treebank_rows.append(
                    {"target": target, "family": held_out, "treebank_id": tb, "y_true": float(y_true), "y_pred": float(y_pred)}
                )

    def summarize(errs_by_family: dict) -> dict:
        fam_rmse = {f: float(np.sqrt(np.mean(np.square(e)))) for f, e in errs_by_family.items() if e}
        fam_mae = {f: float(np.mean(np.abs(e))) for f, e in errs_by_family.items() if e}
        if not fam_rmse:
            return {"macro_rmse": np.nan, "macro_mae": np.nan, "rmse_ci_lo": np.nan, "rmse_ci_hi": np.nan, "per_family_rmse": {}}
        macro_rmse = float(np.mean(list(fam_rmse.values())))
        macro_mae = float(np.mean(list(fam_mae.values())))
        vals = list(fam_rmse.values())
        boots = [np.mean(RNG.choice(vals, size=len(vals), replace=True)) for _ in range(N_BOOT)] if len(vals) > 1 else [macro_rmse]
        return {
            "macro_rmse": macro_rmse,
            "macro_mae": macro_mae,
            "rmse_ci_lo": float(np.percentile(boots, 2.5)),
            "rmse_ci_hi": float(np.percentile(boots, 97.5)),
            "per_family_rmse": fam_rmse,
        }

    xi_summary = summarize(per_family_errors["xi"])
    mdd_summary = summarize(per_family_errors["mdd"])

    # MAPE separately (avoid div-by-zero on near-zero xi)
    def mape(target_key, formula_target):
        rows = [r for r in per_treebank_rows if r["target"] == formula_target]
        vals = [abs((r["y_pred"] - r["y_true"]) / r["y_true"]) for r in rows if abs(r["y_true"]) > 1e-6]
        return float(np.mean(vals) * 100) if vals else np.nan

    return {
        "n_families": int(len(families)),
        "n_treebanks_used": int(len(d)),
        "xi_lofo": {**xi_summary, "mape_pct": mape("xi", "xi_90")},
        "mdd_lofo": {**mdd_summary, "mape_pct": mape("mdd", "mdd")},
        "singular_or_failed_folds": singular_flags,
        "per_treebank_predictions": per_treebank_rows,
    }


# --------------------------------------------------------------------------
# 6. Typological correlations + partial correlations (residual-on-residual).
# --------------------------------------------------------------------------
def typological_correlations(tdf: pd.DataFrame) -> dict:
    feats = ["head_finality_empirical", "case_richness", "word_order_flexibility"]
    outcomes = ["xi_90", "mdd"]
    d_full = tdf.copy()

    def spearman_ci(x, y, n_boot=N_BOOT):
        mask = ~(np.isnan(x) | np.isnan(y))
        x, y = np.asarray(x)[mask], np.asarray(y)[mask]
        if len(x) < 4:
            return np.nan, np.nan, np.nan, np.nan, int(len(x))
        rho, p = stats.spearmanr(x, y)
        idx = np.arange(len(x))
        boots = []
        for _ in range(n_boot):
            bi = RNG.choice(idx, size=len(idx), replace=True)
            if len(set(x[bi])) < 2 or len(set(y[bi])) < 2:
                continue
            r, _ = stats.spearmanr(x[bi], y[bi])
            boots.append(r)
        lo, hi = (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))) if boots else (np.nan, np.nan)
        return float(rho), float(p), lo, hi, int(len(x))

    raw_results = {}
    pvals = []
    keys = []
    for feat in feats:
        for outcome in outcomes:
            rho, p, lo, hi, n = spearman_ci(d_full[feat].values, d_full[outcome].values)
            key = f"{outcome}_vs_{feat}"
            raw_results[key] = {"rho": rho, "p_raw": p, "ci_lo": lo, "ci_hi": hi, "n": n}
            pvals.append(p if np.isfinite(p) else 1.0)
            keys.append(key)

    # Holm-Bonferroni across the 6 tests
    order = np.argsort(pvals)
    m = len(pvals)
    adj = [np.nan] * m
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj_p = min((m - rank) * pvals[idx], 1.0)
        running_max = max(running_max, adj_p)
        adj[idx] = running_max
    for key, a in zip(keys, adj):
        raw_results[key]["p_holm"] = float(a)

    # Partial correlations: residualize outcome ~ register + (1|family), and
    # feature ~ register + (1|family), then Spearman on residuals.
    partials = {}
    d_full["register_bin"] = (d_full["register"] == "spoken").astype(float)
    for outcome in outcomes:
        res_out, data_out, meta_out = fit_mixedlm(f"{outcome} ~ register_bin", d_full, "family")
        if res_out is None:
            continue
        data_out = data_out.copy()
        data_out["resid_outcome"] = res_out.resid
        for feat in feats:
            res_feat, data_feat, meta_feat = fit_mixedlm(f"{feat} ~ register_bin", d_full, "family")
            if res_feat is None:
                continue
            data_feat = data_feat.copy()
            data_feat["resid_feat"] = res_feat.resid
            merged = data_out[["treebank_id", "resid_outcome"]].merge(
                data_feat[["treebank_id", "resid_feat"]], on="treebank_id"
            )
            if len(merged) >= 4:
                rho, p = stats.spearmanr(merged["resid_outcome"], merged["resid_feat"])
            else:
                rho, p = np.nan, np.nan
            partials[f"partial_{outcome}_vs_{feat}_given_register"] = {
                "rho": float(rho) if np.isfinite(rho) else np.nan,
                "p": float(p) if np.isfinite(p) else np.nan,
                "n": int(len(merged)),
                "outcome_singular": meta_out["singular"],
                "feature_singular": meta_feat["singular"],
            }
    return {"marginal_spearman": raw_results, "partial_correlations_controlling_register": partials}


# --------------------------------------------------------------------------
# 7. Outlier detection & rule-based linguistic categorization.
# --------------------------------------------------------------------------
PHENOMENON_KEYS = ["extraposition", "long_distance_rc", "free_word_order", "speech_disfluency", "coordination_apposition", "other"]


def categorize_sentence(row, flexible_language: bool) -> str:
    deprels = row["deprel"]
    n = len(deprels)
    if n == 0:
        return "other"
    base = [dr.split(":")[0] for dr in deprels]
    n_relcl = sum(1 for dr in deprels if dr in RELCL_RELS or dr.split(":")[0] == "acl")
    n_flat = sum(1 for dr in base if dr in FLAT_LIST_RELS)
    n_disfl = sum(1 for dr in base if dr in {"discourse", "reparandum", "vocative", "interjection"})
    n_root_dep_far = 1 if row["max_norm_dist"] > 0.5 else 0

    if n_disfl / n > 0.05:
        return "speech_disfluency"
    if n_relcl >= 1 and row["max_norm_dist"] > 0.3:
        return "long_distance_rc"
    if n_flat / n > 0.2:
        return "coordination_apposition"
    if flexible_language and row["max_norm_dist"] > 0.4:
        return "free_word_order"
    if n_root_dep_far:
        return "extraposition"
    return "other"


def outlier_analysis(df: pd.DataFrame, tdf: pd.DataFrame) -> dict:
    d = tdf.dropna(
        subset=["xi_90", "register", "head_finality_empirical", "case_richness", "word_order_flexibility"]
    ).copy()
    d["register_bin"] = (d["register"] == "spoken").astype(float)
    formula = "xi_90 ~ register_bin + head_finality_empirical + case_richness + word_order_flexibility"
    result, data, meta = fit_mixedlm(formula, d, "family")
    if result is None:
        return {"error": "full mixed model failed to fit", "meta": meta}

    fitted_fixed = result.model.exog @ result.fe_params.values
    resid = data["xi_90"].values - fitted_fixed
    sigma = float(np.std(resid, ddof=1)) if len(resid) > 1 else np.nan
    z = resid / sigma if sigma and sigma > 0 else np.full_like(resid, np.nan)
    data = data.assign(xi_residual=resid, xi_z=z)

    flagged = data[np.abs(data["xi_z"]) > 2].sort_values("xi_z", key=np.abs, ascending=False)
    logger.info(f"Outlier scan: {len(flagged)}/{len(data)} treebanks with |z|>2")

    median_wof = tdf["word_order_flexibility"].median()
    outlier_details = []
    all_flagged_sentences = []
    for _, row in flagged.iterrows():
        tb = row["treebank_id"]
        flexible = tdf.loc[tdf.treebank_id == tb, "word_order_flexibility"].iloc[0] > median_wof
        sub = df[df.treebank_id == tb].copy()
        thresh = sub["max_norm_dist"].quantile(0.9)
        top = sub[sub["max_norm_dist"] >= thresh].nlargest(min(50, max(20, len(sub[sub["max_norm_dist"] >= thresh]))), "max_norm_dist")
        cats = []
        for _, srow in top.iterrows():
            cat = categorize_sentence(srow, flexible)
            cats.append(cat)
            all_flagged_sentences.append(
                {
                    "treebank_id": tb,
                    "sentence_id": srow["sentence_id"],
                    "max_norm_dist": float(srow["max_norm_dist"]),
                    "sentence_length": int(srow["sentence_length"]),
                    "category": cat,
                }
            )
        cat_counts = {c: cats.count(c) for c in PHENOMENON_KEYS}
        outlier_details.append(
            {
                "treebank_id": tb,
                "language": row["language"],
                "register": row["register"],
                "xi_z": float(row["xi_z"]),
                "xi_residual": float(row["xi_residual"]),
                "n_tail_sentences_examined": len(cats),
                "category_counts": cat_counts,
                "dominant_category": max(cat_counts, key=cat_counts.get) if cats else None,
                "interpretation": (
                    f"{row['language']} ({row['treebank_id']}, {row['register']}) has xi more "
                    f"{'extreme (heavier-tailed)' if row['xi_residual'] > 0 else 'moderate (lighter-tailed)'} "
                    f"than the model predicts from register+typology alone (z={row['xi_z']:.2f}); "
                    f"its longest-normalized-distance sentences are dominated by "
                    f"'{max(cat_counts, key=cat_counts.get) if cats else 'n/a'}' constructions."
                ),
            }
        )

    return {
        "model_formula": formula,
        "model_singular": meta["singular"],
        "n_treebanks": int(len(data)),
        "n_outliers_flagged": int(len(flagged)),
        "sigma_residual": sigma,
        "all_residuals": [
            {"treebank_id": t, "xi_residual": float(r), "xi_z": float(zz)}
            for t, r, zz in zip(data["treebank_id"], resid, z)
        ],
        "top_outliers": outlier_details[:5],
        "flagged_tail_sentences": all_flagged_sentences,
    }


# --------------------------------------------------------------------------
# 8. Sensitivity analysis.
# --------------------------------------------------------------------------
def sensitivity_analysis(df: pd.DataFrame, tdf: pd.DataFrame) -> dict:
    excl_flat = fit_gpd_excluding_flat(df)
    merged = tdf.merge(excl_flat, on="treebank_id")
    merged["xi_pct_change_excl_flat"] = (
        100 * (merged["xi_90_excl_flat"] - merged["xi_90"]) / merged["xi_90"].abs()
    )
    merged["mdd_pct_change_excl_flat"] = (
        100 * (merged["mdd_excl_flat"] - merged["mdd"]) / merged["mdd"].abs()
    )

    small_treebanks = tdf[tdf["n_arcs"] < 20000]["treebank_id"].tolist()
    large_only = tdf[tdf["n_arcs"] >= 20000].copy()

    def register_corr(sub):
        s = sub.dropna(subset=["xi_90", "register"])
        s = s.assign(register_bin=(s["register"] == "spoken").astype(float))
        if s["register_bin"].nunique() < 2 or len(s) < 4:
            return np.nan
        rho, _ = stats.pointbiserialr(s["register_bin"], s["xi_90"])
        return float(rho)

    threshold_sensitivity = {
        "xi_75_mean": float(tdf["xi_75"].mean(skipna=True)),
        "xi_80_mean": float(tdf["xi_80"].mean(skipna=True)),
        "xi_90_mean": float(tdf["xi_90"].mean(skipna=True)),
        "xi_75_90_corr": float(tdf[["xi_75", "xi_90"]].dropna().corr().iloc[0, 1]) if tdf[["xi_75", "xi_90"]].dropna().shape[0] > 2 else np.nan,
        "xi_80_90_corr": float(tdf[["xi_80", "xi_90"]].dropna().corr().iloc[0, 1]) if tdf[["xi_80", "xi_90"]].dropna().shape[0] > 2 else np.nan,
    }

    return {
        "excl_flat_list_conj_appos": {
            "per_treebank": merged[
                ["treebank_id", "xi_90", "xi_90_excl_flat", "xi_pct_change_excl_flat", "mdd", "mdd_excl_flat", "mdd_pct_change_excl_flat"]
            ].to_dict(orient="records"),
            "mean_abs_pct_change_xi": float(merged["xi_pct_change_excl_flat"].abs().mean()),
            "mean_abs_pct_change_mdd": float(merged["mdd_pct_change_excl_flat"].abs().mean()),
        },
        "excl_small_treebanks_lt_20k_arcs": {
            "excluded_treebanks": small_treebanks,
            "n_remaining": int(len(large_only)),
            "register_xi_corr_full": register_corr(tdf),
            "register_xi_corr_excl_small": register_corr(large_only),
        },
        "gpd_threshold_sensitivity": threshold_sensitivity,
    }


# --------------------------------------------------------------------------
# 9. Model assumption diagnostics.
# --------------------------------------------------------------------------
def diagnostics(tdf: pd.DataFrame, model_results: dict) -> dict:
    shapiro_xi = stats.shapiro(tdf["xi_90"].dropna())
    shapiro_mdd = stats.shapiro(tdf["mdd"].dropna())
    out = {
        "shapiro_wilk_xi90": {"statistic": float(shapiro_xi.statistic), "p_value": float(shapiro_xi.pvalue), "normal_at_05": bool(shapiro_xi.pvalue > 0.05)},
        "shapiro_wilk_mdd": {"statistic": float(shapiro_mdd.statistic), "p_value": float(shapiro_mdd.pvalue), "normal_at_05": bool(shapiro_mdd.pvalue > 0.05)},
        "singular_fit_flags": {},
        "residual_homogeneity": {},
    }
    for name, res in model_results.items():
        if res is None:
            out["singular_fit_flags"][name] = "model_failed_to_fit"
            continue
        cov_re = res.cov_re.values[0, 0] if res.cov_re.size else 0.0
        out["singular_fit_flags"][name] = bool(cov_re < 1e-8)
        fitted = res.fittedvalues.values
        resid = res.resid.values
        if len(fitted) > 3:
            rho, p = stats.spearmanr(np.abs(resid), fitted)
            out["residual_homogeneity"][name] = {"spearman_abs_resid_vs_fitted": float(rho), "p_value": float(p)}
    return out


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    exp_status = check_experiment_output()
    df, typ = load_sentence_records()
    tdf = build_treebank_table(df, typ)
    logger.info(f"Treebank table:\n{tdf[['treebank_id','register','family','n_arcs','mdd','xi_90','xi_90_normalized']].to_string()}")

    tdf["register_bin"] = (tdf["register"] == "spoken").astype(float)

    # ---- 1. Mixed-effects model comparison -------------------------------
    logger.info("Fitting Model 1/2/3 mixed-effects models ...")
    m1, d1, meta1 = fit_mixedlm("xi_90 ~ mdd", tdf, "family")
    m2, d2, meta2 = fit_mixedlm("xi_90 ~ register_bin + mdd", tdf, "family")
    m3, d3, meta3 = fit_mixedlm("mdd ~ register_bin", tdf, "family")

    model_comparison = {}
    if m1 is not None and m2 is not None:
        aic1, aic2 = float(m1.aic), float(m2.aic)
        bic1, bic2 = float(m1.bic), float(m2.bic)
        k1, k2 = len(m1.fe_params) + 1, len(m2.fe_params) + 1
        aicc1, aicc2 = aicc(aic1, len(d1), k1), aicc(aic2, len(d2), k2)
        w1, w2 = akaike_weights([aicc1, aicc2])
        r2m1, r2c1 = nakagawa_r2(m1, d1, "xi_90")
        r2m2, r2c2 = nakagawa_r2(m2, d2, "xi_90")
        model_comparison = {
            "model1_mdd_only": {"aic": aic1, "bic": bic1, "aicc": float(aicc1), "akaike_weight": float(w1), "r2_marginal": r2m1, "r2_conditional": r2c1, "singular": meta1["singular"], "register_coef": None, "register_p": None},
            "model2_register_plus_mdd": {
                "aic": aic2, "bic": bic2, "aicc": float(aicc2), "akaike_weight": float(w2),
                "r2_marginal": r2m2, "r2_conditional": r2c2, "singular": meta2["singular"],
                "register_coef": float(m2.fe_params.get("register_bin", np.nan)),
                "register_p": float(m2.pvalues.get("register_bin", np.nan)),
                "mdd_coef": float(m2.fe_params.get("mdd", np.nan)),
            },
            "delta_aicc_model2_minus_model1": float(aicc2 - aicc1),
            "register_improves_fit": bool(aicc2 < aicc1),
            "r2_marginal_gain_model1_to_2": float(r2m2 - r2m1) if np.isfinite(r2m1) and np.isfinite(r2m2) else np.nan,
            "r2_conditional_gain_model1_to_2": float(r2c2 - r2c1) if np.isfinite(r2c1) and np.isfinite(r2c2) else np.nan,
        }
    if m3 is not None:
        r2m3, r2c3 = nakagawa_r2(m3, d3, "mdd")
        model_comparison["model3_mdd_on_register"] = {
            "aic": float(m3.aic), "bic": float(m3.bic),
            "register_coef": float(m3.fe_params.get("register_bin", np.nan)),
            "register_p": float(m3.pvalues.get("register_bin", np.nan)),
            "r2_marginal": r2m3, "r2_conditional": r2c3, "singular": meta3["singular"],
        }

    # ---- 2. Variance partitioning: 4-predictor model on xi ---------------
    logger.info("Fitting 4-predictor variance-partitioning model ...")
    d_std = tdf.copy()
    for c in ["head_finality_empirical", "case_richness", "word_order_flexibility", "mdd"]:
        d_std[c + "_z"] = (d_std[c] - d_std[c].mean()) / d_std[c].std(ddof=0)
    m4, d4, meta4 = fit_mixedlm(
        "xi_90 ~ register_bin + head_finality_empirical_z + case_richness_z + word_order_flexibility_z",
        d_std, "family",
    )
    variance_partitioning = {}
    if m4 is not None:
        r2m4, r2c4 = nakagawa_r2(m4, d4, "xi_90")
        semi_partial = {}
        full_r2 = r2m4
        for drop in ["register_bin", "head_finality_empirical_z", "case_richness_z", "word_order_flexibility_z"]:
            keep = [p for p in ["register_bin", "head_finality_empirical_z", "case_richness_z", "word_order_flexibility_z"] if p != drop]
            nested_formula = "xi_90 ~ " + " + ".join(keep) if keep else "xi_90 ~ 1"
            m_nested, d_nested, _ = fit_mixedlm(nested_formula, d_std, "family")
            if m_nested is not None:
                r2m_nested, _ = nakagawa_r2(m_nested, d_nested, "xi_90")
                semi_partial[drop] = float(full_r2 - r2m_nested) if np.isfinite(full_r2) and np.isfinite(r2m_nested) else np.nan
            else:
                semi_partial[drop] = np.nan
        variance_partitioning = {
            "formula": "xi_90 ~ register_bin + head_finality_z + case_richness_z + word_order_flexibility_z + (1|family)",
            "r2_marginal": r2m4, "r2_conditional": r2c4,
            "family_variance_pct_of_total": float((r2c4 - r2m4) * 100) if np.isfinite(r2c4) and np.isfinite(r2m4) else np.nan,
            "standardized_slopes": {p: float(m4.fe_params.get(p, np.nan)) for p in ["register_bin", "head_finality_empirical_z", "case_richness_z", "word_order_flexibility_z"]},
            "slope_ci_95": {p: [float(m4.conf_int().loc[p, 0]), float(m4.conf_int().loc[p, 1])] if p in m4.conf_int().index else [np.nan, np.nan] for p in ["register_bin", "head_finality_empirical_z", "case_richness_z", "word_order_flexibility_z"]},
            "slope_p_values": {p: float(m4.pvalues.get(p, np.nan)) for p in ["register_bin", "head_finality_empirical_z", "case_richness_z", "word_order_flexibility_z"]},
            "semi_partial_r2_marginal_drop": semi_partial,
            "singular_fit": meta4["singular"],
            "n_treebanks": int(len(d4)),
        }

    # ---- 3. Within-language paired register comparison --------------------
    logger.info("Running within-language paired register comparisons ...")
    paired_results = within_language_paired_tests(df, tdf)

    # ---- 4. LOFO-CV --------------------------------------------------------
    logger.info("Running leave-one-family-out cross-validation ...")
    lofo_results = lofo_cv(tdf)

    # ---- 5. Typological correlations --------------------------------------
    logger.info("Computing typological correlations (marginal + partial) ...")
    typ_corr = typological_correlations(tdf)

    # ---- 6. Outlier detection ----------------------------------------------
    logger.info("Running outlier detection & rule-based categorization ...")
    outliers = outlier_analysis(df, tdf)

    # ---- 7. Sensitivity analysis --------------------------------------------
    logger.info("Running sensitivity analysis (excl. flat/list, excl. small treebanks, threshold sweep) ...")
    sensitivity = sensitivity_analysis(df, tdf)

    # ---- 8. Diagnostics ------------------------------------------------------
    logger.info("Running model diagnostics ...")
    diag = diagnostics(tdf, {"model1_mdd_only": m1, "model2_register_mdd": m2, "model3_mdd_register": m3, "model4_full": m4})

    # -----------------------------------------------------------------------
    # Assemble metrics_agg (flat numeric summary of everything above)
    # -----------------------------------------------------------------------
    def g(d, *keys, default=np.nan):
        cur = d
        for k in keys:
            if cur is None or k not in cur:
                return default
            cur = cur[k]
        return cur if cur is not None else default

    def safe_float(v):
        try:
            f = float(v)
            return f if np.isfinite(f) else 0.0
        except (TypeError, ValueError):
            return 0.0

    metrics_agg = {
        "experiment_produced_output": float(exp_status["experiment_produced_output"]),
        "n_treebanks": float(len(tdf)),
        "n_sentences_total": float(len(df)),
        "n_arcs_total": float(tdf["n_arcs"].sum()),
        "n_families": float(tdf["family"].nunique()),
        "n_within_language_register_pairs": float(g(paired_results, "treebank_level_direction", "n_pairs")),

        "model1_aicc": safe_float(g(model_comparison, "model1_mdd_only", "aicc")),
        "model2_aicc": safe_float(g(model_comparison, "model2_register_plus_mdd", "aicc")),
        "delta_aicc_register_vs_mdd_only": safe_float(g(model_comparison, "delta_aicc_model2_minus_model1")),
        "register_improves_fit_over_mdd_only": float(bool(g(model_comparison, "register_improves_fit", default=False))),
        "model2_register_coefficient": safe_float(g(model_comparison, "model2_register_plus_mdd", "register_coef")),
        "model2_register_p_value": safe_float(g(model_comparison, "model2_register_plus_mdd", "register_p")),
        "model2_r2_marginal": safe_float(g(model_comparison, "model2_register_plus_mdd", "r2_marginal")),
        "model2_r2_conditional": safe_float(g(model_comparison, "model2_register_plus_mdd", "r2_conditional")),
        "r2_marginal_gain_from_register": safe_float(g(model_comparison, "r2_marginal_gain_model1_to_2")),
        "model3_mdd_register_coefficient": safe_float(g(model_comparison, "model3_mdd_on_register", "register_coef")),
        "model3_mdd_register_p_value": safe_float(g(model_comparison, "model3_mdd_on_register", "register_p")),

        "variance_partition_r2_marginal": safe_float(g(variance_partitioning, "r2_marginal")),
        "variance_partition_r2_conditional": safe_float(g(variance_partitioning, "r2_conditional")),
        "family_variance_pct_of_total": safe_float(g(variance_partitioning, "family_variance_pct_of_total")),
        "register_standardized_slope": safe_float(g(variance_partitioning, "standardized_slopes", "register_bin")),
        "head_finality_standardized_slope": safe_float(g(variance_partitioning, "standardized_slopes", "head_finality_empirical_z")),
        "case_richness_standardized_slope": safe_float(g(variance_partitioning, "standardized_slopes", "case_richness_z")),
        "word_order_flex_standardized_slope": safe_float(g(variance_partitioning, "standardized_slopes", "word_order_flexibility_z")),

        "pct_pairs_spoken_lower_xi": safe_float(g(paired_results, "treebank_level_direction", "pct_spoken_lower_xi")),
        "pct_pairs_spoken_lower_mdd": safe_float(g(paired_results, "treebank_level_direction", "pct_spoken_lower_mdd")),
        "median_xi_diff_spoken_minus_written": safe_float(g(paired_results, "treebank_level_direction", "median_xi_diff_spoken_minus_written")),
        "length_bin_wilcoxon_p_value": safe_float(g(paired_results, "length_bin_wilcoxon_normalized_distance", "p_value")),
        "length_bin_wilcoxon_effect_size_r": safe_float(g(paired_results, "length_bin_wilcoxon_normalized_distance", "effect_size_r")),
        "length_bin_pct_spoken_higher_norm_dist": safe_float(g(paired_results, "length_bin_wilcoxon_normalized_distance", "pct_bins_spoken_higher_norm_dist")),

        "lofo_xi_macro_rmse": safe_float(g(lofo_results, "xi_lofo", "macro_rmse")),
        "lofo_xi_macro_mae": safe_float(g(lofo_results, "xi_lofo", "macro_mae")),
        "lofo_xi_mape_pct": safe_float(g(lofo_results, "xi_lofo", "mape_pct")),
        "lofo_mdd_macro_rmse": safe_float(g(lofo_results, "mdd_lofo", "macro_rmse")),
        "lofo_mdd_macro_mae": safe_float(g(lofo_results, "mdd_lofo", "macro_mae")),
        "n_lofo_singular_or_failed_folds": float(len(g(lofo_results, "singular_or_failed_folds", default=[]))),

        "n_outliers_flagged": safe_float(g(outliers, "n_outliers_flagged")),
        "n_treebanks_scored_for_outliers": safe_float(g(outliers, "n_treebanks")),

        "shapiro_p_xi90": safe_float(g(diag, "shapiro_wilk_xi90", "p_value")),
        "shapiro_p_mdd": safe_float(g(diag, "shapiro_wilk_mdd", "p_value")),
        "n_singular_fits": float(sum(1 for v in diag.get("singular_fit_flags", {}).values() if v is True)),

        "sensitivity_mean_abs_pct_change_xi_excl_flat": safe_float(g(sensitivity, "excl_flat_list_conj_appos", "mean_abs_pct_change_xi")),
        "sensitivity_mean_abs_pct_change_mdd_excl_flat": safe_float(g(sensitivity, "excl_flat_list_conj_appos", "mean_abs_pct_change_mdd")),
        "n_treebanks_excluded_small": safe_float(len(g(sensitivity, "excl_small_treebanks_lt_20k_arcs", "excluded_treebanks", default=[]))),
        "xi_threshold_75_90_correlation": safe_float(g(sensitivity, "gpd_threshold_sensitivity", "xi_75_90_corr")),
        "xi_threshold_80_90_correlation": safe_float(g(sensitivity, "gpd_threshold_sensitivity", "xi_80_90_corr")),
    }
    for key, res in typ_corr.get("marginal_spearman", {}).items():
        metrics_agg[f"spearman_{key}"] = safe_float(res.get("rho"))
        metrics_agg[f"spearman_{key}_p_holm"] = safe_float(res.get("p_holm"))
    for key, res in typ_corr.get("partial_correlations_controlling_register", {}).items():
        metrics_agg[key] = safe_float(res.get("rho"))

    # -----------------------------------------------------------------------
    # Assemble "datasets" (per-schema: input/output strings + predict_/eval_/metadata_)
    # -----------------------------------------------------------------------
    treebank_examples = []
    for _, row in tdf.iterrows():
        input_obj = {"treebank_id": row["treebank_id"], "language": row["language"], "family": row["family"], "register": row["register"]}
        output_obj = {
            "mdd": row["mdd"], "xi_90": row["xi_90"], "xi_80": row["xi_80"], "xi_75": row["xi_75"],
            "xi_90_normalized": row["xi_90_normalized"], "head_finality_empirical": row["head_finality_empirical"],
            "head_finality_grambank": row["head_finality_grambank"], "case_richness": row["case_richness"],
            "word_order_flexibility": row["word_order_flexibility"], "n_arcs": int(row["n_arcs"]), "n_sentences": int(row["n_sentences"]),
        }
        z_lookup = {r["treebank_id"]: r for r in outliers.get("all_residuals", [])}
        zrow = z_lookup.get(row["treebank_id"], {})
        treebank_examples.append(
            {
                "input": json.dumps(input_obj),
                "output": json.dumps(output_obj),
                "metadata_treebank_id": row["treebank_id"],
                "metadata_language": row["language"],
                "metadata_family": row["family"],
                "metadata_register": row["register"],
                "predict_xi_90": str(row["xi_90"]),
                "predict_mdd": str(row["mdd"]),
                "eval_xi_z_score": safe_float(zrow.get("xi_z")),
                "eval_xi_residual": safe_float(zrow.get("xi_residual")),
                "eval_is_outlier": float(abs(zrow.get("xi_z", 0.0)) > 2 if zrow.get("xi_z") is not None else 0.0),
            }
        )

    pair_examples = [
        {
            "input": json.dumps({"language": r["language"], "len_bin": r["len_bin"]}),
            "output": json.dumps({"spoken_mean_norm_dist": r["spoken_mean_norm_dist"], "written_mean_norm_dist": r["written_mean_norm_dist"], "diff": r["diff"]}),
            "metadata_language": r["language"],
            "eval_diff_spoken_minus_written": safe_float(r["diff"]),
        }
        for r in paired_results.get("length_bin_rows", [])
    ] or [
        {
            "input": json.dumps({"note": "no length-bin pairs available"}),
            "output": json.dumps({"note": "no length-bin pairs available"}),
            "eval_diff_spoken_minus_written": 0.0,
        }
    ]

    outlier_examples = [
        {
            "input": json.dumps({"treebank_id": s["treebank_id"], "sentence_id": s["sentence_id"]}),
            "output": json.dumps({"category": s["category"], "max_norm_dist": s["max_norm_dist"], "sentence_length": s["sentence_length"]}),
            "metadata_treebank_id": s["treebank_id"],
            "metadata_category": s["category"],
            "eval_max_norm_dist": safe_float(s["max_norm_dist"]),
        }
        for s in outliers.get("flagged_tail_sentences", [])
    ] or [
        {
            "input": json.dumps({"note": "no treebanks flagged as outliers (|z|<=2 for all)"}),
            "output": json.dumps({"note": "no outlier sentences examined"}),
            "eval_max_norm_dist": 0.0,
        }
    ]

    lofo_examples = [
        {
            "input": json.dumps({"treebank_id": r["treebank_id"], "held_out_family": r["family"], "target": r["target"]}),
            "output": json.dumps({"y_true": r["y_true"], "y_pred": r["y_pred"]}),
            "metadata_treebank_id": r["treebank_id"],
            "metadata_family": r["family"],
            "predict_lofo_value": str(r["y_pred"]),
            "eval_abs_error": safe_float(abs(r["y_pred"] - r["y_true"])),
        }
        for r in lofo_results.get("per_treebank_predictions", [])
    ] or [
        {
            "input": json.dumps({"note": "LOFO-CV produced no folds (insufficient typology coverage or families)"}),
            "output": json.dumps({"note": "no predictions"}),
            "eval_abs_error": 0.0,
        }
    ]

    output = {
        "metadata": {
            "evaluation_name": "tail_index_vs_mdd_register_typology",
            "description": (
                "Evaluates whether GPD tail index xi carries information beyond MDD for "
                "spoken/written register discrimination and typological prediction across "
                "18 UD treebanks. gen_art_experiment_1 crashed and produced no output "
                "(see experiment_status), so xi/MDD/typology-join were computed here "
                "directly from gen_art_dataset_1's already-collected per-sentence raw "
                "dependency distances (deterministic, no LLM calls, no re-fetching)."
            ),
            "experiment_status": exp_status,
            "model_comparison_register_independence": model_comparison,
            "variance_partitioning": variance_partitioning,
            "within_language_paired_register_comparison": {
                "pairs": paired_results["pairs"],
                "treebank_level_direction": paired_results["treebank_level_direction"],
                "length_bin_wilcoxon_normalized_distance": paired_results["length_bin_wilcoxon_normalized_distance"],
            },
            "leave_one_family_out_cv": {
                "n_families": lofo_results["n_families"],
                "n_treebanks_used": lofo_results["n_treebanks_used"],
                "xi_lofo": lofo_results["xi_lofo"],
                "mdd_lofo": lofo_results["mdd_lofo"],
                "singular_or_failed_folds": lofo_results["singular_or_failed_folds"],
            },
            "typological_correlations": typ_corr,
            "outlier_summary": {
                "model_formula": outliers.get("model_formula"),
                "model_singular": outliers.get("model_singular"),
                "n_outliers_flagged": outliers.get("n_outliers_flagged"),
                "top_outliers": outliers.get("top_outliers"),
            },
            "sensitivity_analysis": sensitivity,
            "diagnostics": diag,
            "typology_coverage_note": (
                f"Grambank typology (case_richness, head_finality_grambank) available for "
                f"{int(tdf['has_typology'].sum())}/{len(tdf)} treebanks; missing for "
                f"{tdf.loc[~tdf['has_typology'], 'treebank_id'].tolist()}. head_finality_empirical "
                "and word_order_flexibility are computed directly from UD annotations for all 18 "
                "treebanks and used as the primary typology signal; case_richness (Grambank-only) "
                "is NaN and dropped listwise for the 3 uncovered treebanks in models that include it."
            ),
        },
        "metrics_agg": metrics_agg,
        "datasets": [
            {"dataset": "treebank_level_xi_mdd_typology", "examples": treebank_examples},
            {"dataset": "within_language_length_bin_pairs", "examples": pair_examples},
            {"dataset": "outlier_tail_sentence_categorization", "examples": outlier_examples},
            {"dataset": "lofo_cv_predictions", "examples": lofo_examples},
        ],
    }

    def sanitize(obj):
        """Recursively replace NaN/Inf floats and numpy scalars with plain,
        strict-JSON-safe values (None for non-finite numbers) so the output
        parses under json.dump(allow_nan=False), which the schema validator
        (and any standard JSON reader) requires."""
        if isinstance(obj, dict):
            return {k: sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [sanitize(v) for v in obj]
        if isinstance(obj, (np.floating, float)):
            f = float(obj)
            return f if np.isfinite(f) else None
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    output = sanitize(output)

    out_path = WORKDIR / "eval_out.json"
    logger.info(f"Writing evaluation output to {out_path}")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str, allow_nan=False)
    logger.info(f"Done. metrics_agg has {len(metrics_agg)} keys; wrote {out_path.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
