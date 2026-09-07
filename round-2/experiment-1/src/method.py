#!/usr/bin/env python3
"""Power-law (alpha) vs Generalized-Pareto (xi) tail indices for UD dependency
distances across 18 treebanks: EVT threshold selection, bootstrap CIs, matched
spoken/written pairs, and mixed-effects models predicting register / typology.
"""

from __future__ import annotations

import gc
import json
import multiprocessing as mp
import resource
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from loguru import logger
from scipy import stats
import statsmodels.formula.api as smf
import statsmodels.api as sm

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add("logs/run.log", rotation="30 MB", level="DEBUG")

WORKDIR = Path(__file__).parent
RAM_BUDGET = 10 * 1024**3  # 10GB of ~29GB container limit
resource.setrlimit(resource.RLIMIT_AS, (RAM_BUDGET * 3, RAM_BUDGET * 3))
resource.setrlimit(resource.RLIMIT_CPU, (3 * 3600, 3 * 3600))

NUM_CPUS = 4
SEED = 20260907
B_BOOTSTRAP = 300  # reduced from 1000 per fallback-8 (compute-time budget)
MIN_ARCS_PRIMARY = 1000
THRESHOLDS = [0.75, 0.80, 0.90]
PRIMARY_THRESHOLD = 0.75

MATCHED_PAIRS = [
    {"language": "Slovenian", "spoken": "sl_sst", "written": "sl_ssj"},
    {"language": "French", "spoken": "fr_rhapsodie", "written": "fr_gsd"},
    {"language": "English", "spoken": "en_eslspok", "written": "en_ewt"},
    {"language": "Turkish", "spoken": "tr_atis", "written": "tr_imst",
     "caveat": "ATIS is task-oriented dialogue, not spontaneous conversational speech"},
]


# ------------------------- data loading -------------------------

def load_examples(path: Path) -> list[dict]:
    logger.info(f"Loading {path}")
    data = json.loads(path.read_text())
    examples = data["datasets"][0]["examples"]
    logger.info(f"Loaded {len(examples)} sentence-level examples")
    return examples


def examples_to_frame(examples: list[dict]) -> pd.DataFrame:
    rows = []
    for ex in examples:
        try:
            out = json.loads(ex["output"])
        except (json.JSONDecodeError, KeyError):
            continue
        norm = out.get("normalized_distances", [])
        gb_raw = ex.get("metadata_grambank_features")
        gb_composite = np.nan
        if gb_raw:
            try:
                gb = json.loads(gb_raw)
                vals = [float(v) for v in gb.values() if v not in (None, "?", "")]
                if vals:
                    gb_composite = float(np.mean(vals))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        rows.append({
            "treebank_id": ex.get("metadata_treebank_id"),
            "language": ex.get("metadata_language"),
            "family": ex.get("metadata_language_family"),
            "register": ex.get("metadata_register"),
            "sentence_length": ex.get("metadata_sentence_length"),
            "head_finality_ratio": ex.get("metadata_head_finality_ratio"),
            "grambank_composite": gb_composite,
            "normalized_distances": norm,
            "n_arcs": len(norm),
        })
    df = pd.DataFrame(rows)
    logger.info(f"Built frame: {len(df)} sentences, {df['treebank_id'].nunique()} treebanks")
    return df


# ------------------------- EVT fitting -------------------------

def mrl_plot_points(distances: np.ndarray, quantiles: np.ndarray) -> list[dict]:
    pts = []
    for q in quantiles:
        t = float(np.quantile(distances, q))
        exceed = distances[distances > t] - t
        pts.append({
            "quantile": float(q),
            "threshold": t,
            "n_exceedances": int(exceed.size),
            "mean_excess": float(exceed.mean()) if exceed.size > 0 else None,
        })
    return pts


def fit_gpd_point(exceedances: np.ndarray) -> tuple[float, float, float]:
    """Fit Generalized Pareto (loc=0) via MLE, return (xi, sigma, loglik)."""
    mean_ex = exceedances.mean()
    var_ex = exceedances.var()
    xi0 = 0.5 * (1 - mean_ex**2 / var_ex) if var_ex > 0 else 0.1
    xi0 = float(np.clip(xi0, -0.4, 0.9))
    sigma0 = max(mean_ex * (1 - xi0), 1e-6)
    try:
        c, loc, scale = stats.genpareto.fit(exceedances, xi0, floc=0)
        ll = float(np.sum(stats.genpareto.logpdf(exceedances, c, loc=0, scale=scale)))
        return float(c), float(scale), ll
    except Exception as e:  # noqa: BLE001
        logger.warning(f"GPD MLE failed ({e}); falling back to method-of-moments")
        return xi0, sigma0, float("nan")


def fit_powerlaw_alpha(exceedances_from_xmin: np.ndarray, xmin: float) -> tuple[float, float]:
    """Clauset et al. (2009) discrete-continuous MLE for continuous power law.
    exceedances_from_xmin are the RAW values (>= xmin), not offsets."""
    x = exceedances_from_xmin[exceedances_from_xmin > 0]
    n = x.size
    if n < 2 or xmin <= 0:
        return float("nan"), float("nan")
    s = np.sum(np.log(x / xmin))
    if s <= 0:
        return float("nan"), float("nan")
    alpha = 1.0 + n / s
    se = (alpha - 1.0) / np.sqrt(n)
    return float(alpha), float(se)


def bootstrap_ci(values: np.ndarray, xmin: float, rng: np.random.Generator, b: int):
    """Return (xi_boot, alpha_boot) arrays from B resamples of raw values > xmin."""
    n = values.size
    xi_boot = np.empty(b)
    alpha_boot = np.empty(b)
    for i in range(b):
        idx = rng.integers(0, n, size=n)
        resample = values[idx]
        exc = resample - xmin
        xi_b, _, _ = fit_gpd_point(exc)
        xi_boot[i] = xi_b
        a_b, _ = fit_powerlaw_alpha(resample, xmin)
        alpha_boot[i] = a_b
    return xi_boot, alpha_boot


def analyze_treebank_threshold(args) -> dict:
    treebank_id, distances, quantile, do_bootstrap, seed = args
    distances = np.asarray(distances, dtype=float)
    distances = distances[distances > 0]
    t = float(np.quantile(distances, quantile))
    above = distances[distances > t]
    exceed = above - t
    n_exc = exceed.size
    if n_exc < 20:
        return {
            "treebank_id": treebank_id, "quantile": quantile, "threshold": t,
            "n_exceedances": n_exc, "insufficient_exceedances": True,
        }
    xi, sigma, ll = fit_gpd_point(exceed)
    alpha, alpha_se = fit_powerlaw_alpha(above, t)
    result = {
        "treebank_id": treebank_id, "quantile": quantile, "threshold": t,
        "n_exceedances": n_exc, "insufficient_exceedances": False,
        "xi_point": xi, "sigma_point": sigma, "gpd_loglik": ll,
        "alpha_point": alpha, "alpha_se": alpha_se,
    }
    if do_bootstrap:
        rng = np.random.default_rng(seed)
        xi_boot, alpha_boot = bootstrap_ci(above, t, rng, B_BOOTSTRAP)
        xi_boot_clean = xi_boot[np.isfinite(xi_boot)]
        alpha_boot_clean = alpha_boot[np.isfinite(alpha_boot)]
        if xi_boot_clean.size > 10:
            result["xi_ci_lower"] = float(np.percentile(xi_boot_clean, 2.5))
            result["xi_ci_upper"] = float(np.percentile(xi_boot_clean, 97.5))
        else:
            result["xi_ci_lower"] = result["xi_ci_upper"] = None
        if alpha_boot_clean.size > 10:
            result["alpha_ci_lower"] = float(np.percentile(alpha_boot_clean, 2.5))
            result["alpha_ci_upper"] = float(np.percentile(alpha_boot_clean, 97.5))
        else:
            result["alpha_ci_lower"] = result["alpha_ci_upper"] = None
        result["xi_boot"] = xi_boot_clean.tolist()
        result["alpha_boot"] = alpha_boot_clean.tolist()
    return result


# ------------------------- model helpers -------------------------

def aicc(loglik: float, k: int, n: int) -> float:
    aic = 2 * k - 2 * loglik
    denom = n - k - 1
    if denom <= 0:
        return float("inf")
    return aic + (2 * k * (k + 1)) / denom


def akaike_weights(aiccs: list[float]) -> list[float]:
    m = min(a for a in aiccs if np.isfinite(a))
    deltas = [a - m if np.isfinite(a) else np.inf for a in aiccs]
    exps = [np.exp(-d / 2) for d in deltas]
    total = sum(exps)
    return [e / total if total > 0 else float("nan") for e in exps]


def nakagawa_r2(model_result, re_var: float, resid_var: float, fixed_var: float) -> tuple[float, float]:
    total = fixed_var + re_var + resid_var
    if total <= 0:
        return float("nan"), float("nan")
    r2_marg = fixed_var / total
    r2_cond = (fixed_var + re_var) / total
    return float(r2_marg), float(r2_cond)


def fit_mixed_or_fallback(formula: str, data: pd.DataFrame, group_col: str, label: str) -> dict:
    """Fit MixedLM with random intercept on group_col; fall back to OLS+fixed group if singular."""
    out = {"label": label, "formula": formula, "group_col": group_col}
    try:
        n_groups = data[group_col].nunique()
        if n_groups < 2 or n_groups >= len(data) - 1:
            raise ValueError("degenerate grouping for random effects")
        md = smf.mixedlm(formula, data=data, groups=data[group_col])
        mdf = md.fit(reml=False, method=["lbfgs", "cg", "powell"])
        re_var = float(mdf.cov_re.iloc[0, 0]) if mdf.cov_re.size else 0.0
        resid_var = float(mdf.scale)
        fitted_fixed = mdf.model.exog @ mdf.fe_params.values
        fixed_var = float(np.var(fitted_fixed))
        if re_var < 1e-8 or not np.isfinite(mdf.llf):
            raise ValueError("singular random-effects variance")
        n = len(data)
        k = len(mdf.fe_params) + 2  # fixed effects + resid var + re var
        out.update({
            "method": "mixedlm_random_intercept",
            "converged": bool(mdf.converged),
            "loglik": float(mdf.llf),
            "n_params": k,
            "n_obs": n,
            "aicc": aicc(float(mdf.llf), k, n),
            "re_var_group": re_var,
            "resid_var": resid_var,
            "fixed_effects": {
                name: {"coef": float(mdf.fe_params[name]), "se": float(mdf.bse_fe[name]),
                       "t": float(mdf.tvalues[name]), "p": float(mdf.pvalues[name])}
                for name in mdf.fe_params.index
            },
        })
        r2m, r2c = nakagawa_r2(mdf, re_var, resid_var, fixed_var)
        out["r2_marginal"] = r2m
        out["r2_conditional"] = r2c
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[{label}] MixedLM failed/singular ({e}); falling back to OLS with fixed group")
        try:
            fixed_formula = formula + f" + C({group_col})"
            ols = smf.ols(fixed_formula, data=data).fit()
            n = len(data)
            k = int(ols.df_model) + 2
            out.update({
                "method": "ols_fixed_group_fallback",
                "converged": True,
                "loglik": float(ols.llf),
                "n_params": k,
                "n_obs": n,
                "aicc": aicc(float(ols.llf), k, n),
                "re_var_group": None,
                "resid_var": float(ols.scale),
                "fixed_effects": {
                    name: {"coef": float(ols.params[name]), "se": float(ols.bse[name]),
                           "t": float(ols.tvalues[name]), "p": float(ols.pvalues[name])}
                    for name in ols.params.index if not name.startswith("C(")
                },
                "r2_marginal": float(ols.rsquared),
                "r2_conditional": float(ols.rsquared),
            })
        except Exception as e2:  # noqa: BLE001
            logger.error(f"[{label}] OLS fallback also failed: {e2}")
            out.update({"method": "failed", "error": str(e2)})
        return out


def holm_bonferroni(pvals: list[float]) -> list[float]:
    n = len(pvals)
    order = np.argsort(pvals)
    adjusted = np.empty(n)
    running_max = 0.0
    for rank, idx in enumerate(order):
        adj = (n - rank) * pvals[idx]
        running_max = max(running_max, adj)
        adjusted[idx] = min(running_max, 1.0)
    return adjusted.tolist()


def spearman_ci(x: np.ndarray, y: np.ndarray) -> dict:
    if len(x) < 4:
        return {"rho": None, "p": None, "ci_lower": None, "ci_upper": None, "n": len(x)}
    rho, p = stats.spearmanr(x, y)
    n = len(x)
    if not np.isfinite(rho) or abs(rho) >= 1.0:
        return {"rho": float(rho), "p": float(p), "ci_lower": None, "ci_upper": None, "n": n}
    z = np.arctanh(rho)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return {"rho": float(rho), "p": float(p), "ci_lower": float(np.tanh(lo)),
            "ci_upper": float(np.tanh(hi)), "n": n}


# ------------------------- main pipeline -------------------------

def build_treebank_frame(sent_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tb_id, grp in sent_df.groupby("treebank_id"):
        distances = np.concatenate([np.asarray(d, dtype=float) for d in grp["normalized_distances"]])
        rows.append({
            "treebank_id": tb_id,
            "language": grp["language"].iloc[0],
            "family": grp["family"].iloc[0],
            "register": grp["register"].iloc[0],
            "n_sentences": len(grp),
            "n_arcs": int(distances.size),
            "head_finality_ratio": float(grp["head_finality_ratio"].mean()),
            "grambank_composite": float(grp["grambank_composite"].mean()) if grp["grambank_composite"].notna().any() else np.nan,
            "_distances": distances,
        })
    return pd.DataFrame(rows)


def run_threshold_analysis(tb_df: pd.DataFrame, primary_ids: set[str]) -> dict:
    """Fit xi/alpha for every treebank x threshold. Full bootstrap only at
    primary threshold for primary treebanks (time budget); point estimates
    everywhere else."""
    tasks = []
    for _, row in tb_df.iterrows():
        for q in THRESHOLDS:
            do_boot = (q == PRIMARY_THRESHOLD) and (row["treebank_id"] in primary_ids)
            tasks.append((row["treebank_id"], row["_distances"], q, do_boot,
                          SEED + hash(row["treebank_id"]) % 10_000 + int(q * 100)))

    results = {}
    logger.info(f"Fitting EVT models for {len(tasks)} (treebank, threshold) cells")
    t0 = perf_counter()
    with ProcessPoolExecutor(max_workers=NUM_CPUS, mp_context=mp.get_context("spawn")) as pool:
        futs = {pool.submit(analyze_treebank_threshold, task): task for task in tasks}
        done_n = 0
        for fut in as_completed(futs):
            task = futs[fut]
            tb_id, q = task[0], task[2]
            try:
                res = fut.result()
                results[(tb_id, q)] = res
            except Exception as e:  # noqa: BLE001
                logger.error(f"Fit failed for {tb_id}@{q}: {e}")
                results[(tb_id, q)] = {"treebank_id": tb_id, "quantile": q, "error": str(e)}
            done_n += 1
            if done_n % 10 == 0:
                logger.info(f"  {done_n}/{len(tasks)} cells done ({perf_counter()-t0:.1f}s)")
    logger.info(f"EVT fitting done in {perf_counter()-t0:.1f}s")
    return results


@logger.catch(reraise=True)
def main():
    rng = np.random.default_rng(SEED)
    data_path = WORKDIR / "full_data_out.json"
    examples = load_examples(data_path)
    sent_df = examples_to_frame(examples)
    del examples
    gc.collect()

    tb_df = build_treebank_frame(sent_df)
    del sent_df
    gc.collect()

    excluded = tb_df[tb_df["n_arcs"] < MIN_ARCS_PRIMARY]["treebank_id"].tolist()
    included = tb_df[tb_df["n_arcs"] >= MIN_ARCS_PRIMARY]["treebank_id"].tolist()
    primary_ids = set(included)
    logger.info(f"Treebanks: {len(tb_df)} total; primary (>=1000 arcs): {len(included)}; "
                f"excluded (small-n robustness only): {excluded}")

    # ---- Phase 2: MRL plots for 4 representative treebanks ----
    mrl_quantiles = np.round(np.arange(0.50, 0.96, 0.05), 2)
    mrl_reps = tb_df.sort_values("n_arcs", ascending=False)["treebank_id"].head(4).tolist()
    mrl_plots = {}
    for tb_id in mrl_reps:
        dist = tb_df.loc[tb_df["treebank_id"] == tb_id, "_distances"].iloc[0]
        mrl_plots[tb_id] = mrl_plot_points(dist, mrl_quantiles)
    logger.info(f"Computed MRL plots for: {mrl_reps}")

    # ---- Phases 3-4: fit xi (GPD) and alpha (power law) per treebank x threshold ----
    fit_results = run_threshold_analysis(tb_df, primary_ids)

    # assemble per-treebank primary-threshold table + sensitivity thresholds
    treebank_table = []
    for _, row in tb_df.iterrows():
        tb_id = row["treebank_id"]
        entry = {
            "treebank_id": tb_id, "language": row["language"], "family": row["family"],
            "register": row["register"], "n_sentences": int(row["n_sentences"]),
            "n_arcs": int(row["n_arcs"]),
            "head_finality_ratio": row["head_finality_ratio"],
            "grambank_composite": None if pd.isna(row["grambank_composite"]) else row["grambank_composite"],
            "excluded_primary": tb_id not in primary_ids,
        }
        for q in THRESHOLDS:
            r = fit_results.get((tb_id, q), {})
            suffix = str(int(q * 100))
            entry[f"threshold_{suffix}"] = r.get("threshold")
            entry[f"n_exceedances_{suffix}"] = r.get("n_exceedances")
            entry[f"xi_{suffix}"] = r.get("xi_point")
            entry[f"alpha_{suffix}"] = r.get("alpha_point")
            if q == PRIMARY_THRESHOLD:
                entry["xi_ci_lower"] = r.get("xi_ci_lower")
                entry["xi_ci_upper"] = r.get("xi_ci_upper")
                entry["alpha_ci_lower"] = r.get("alpha_ci_lower")
                entry["alpha_ci_upper"] = r.get("alpha_ci_upper")
        treebank_table.append(entry)
    treebank_df = pd.DataFrame(treebank_table)
    logger.info(f"Treebank table assembled: {len(treebank_df)} rows")

    # ---- Fallback 1: instability check ----
    unstable = []
    for _, r in treebank_df.iterrows():
        if r["xi_ci_lower"] is not None and r["xi_ci_upper"] is not None and r["xi_75"] not in (None,):
            width = r["xi_ci_upper"] - r["xi_ci_lower"]
            if abs(r["xi_75"]) > 1e-9 and width > 2 * abs(r["xi_75"]):
                unstable.append(r["treebank_id"])
    logger.info(f"Unstable-CI treebanks (xi CI width > 2x point est): {unstable}")

    primary_df = treebank_df[~treebank_df["excluded_primary"]].copy()

    # ---- Phase 5: xi vs alpha relationship (cross-treebank, primary threshold) ----
    valid = primary_df.dropna(subset=["xi_75", "alpha_75"])
    xi_alpha_corr = spearman_ci(valid["xi_75"].to_numpy(), valid["alpha_75"].to_numpy())
    if len(valid) >= 3:
        slope, intercept, r_value, p_value, std_err = stats.linregress(valid["xi_75"], valid["alpha_75"])
        xi_alpha_regression = {"slope": float(slope), "intercept": float(intercept),
                                "r_squared": float(r_value**2), "p_value": float(p_value)}
    else:
        xi_alpha_regression = None
    logger.info(f"xi vs alpha Spearman rho={xi_alpha_corr['rho']}")

    # ---- Phase 6: typological covariates + register binary ----
    primary_df["register_binary"] = primary_df["register"].map({"written": 0, "spoken": 1})
    for col in ["xi_75", "alpha_75", "head_finality_ratio", "grambank_composite"]:
        vals = primary_df[col].astype(float)
        mu, sd = vals.mean(), vals.std(ddof=0)
        primary_df[col + "_z"] = (vals - mu) / sd if sd and np.isfinite(sd) and sd > 0 else np.nan

    # ---- Phase 7: univariate correlations with Holm-Bonferroni ----
    corr_tests = []
    reg_sub = primary_df.dropna(subset=["register_binary"])
    corr_tests.append(("xi_vs_register", spearman_ci(reg_sub["xi_75"].to_numpy(), reg_sub["register_binary"].to_numpy())))
    corr_tests.append(("alpha_vs_register", spearman_ci(reg_sub["alpha_75"].to_numpy(), reg_sub["register_binary"].to_numpy())))
    corr_tests.append(("xi_vs_head_finality", spearman_ci(primary_df["xi_75"].to_numpy(), primary_df["head_finality_ratio"].to_numpy())))
    corr_tests.append(("alpha_vs_head_finality", spearman_ci(primary_df["alpha_75"].to_numpy(), primary_df["head_finality_ratio"].to_numpy())))
    gb_sub = primary_df.dropna(subset=["grambank_composite"])
    if len(gb_sub) > 5:
        corr_tests.append(("xi_vs_grambank_composite", spearman_ci(gb_sub["xi_75"].to_numpy(), gb_sub["grambank_composite"].to_numpy())))
        corr_tests.append(("alpha_vs_grambank_composite", spearman_ci(gb_sub["alpha_75"].to_numpy(), gb_sub["grambank_composite"].to_numpy())))

    raw_p = [t[1]["p"] if t[1]["p"] is not None else 1.0 for t in corr_tests]
    adj_p = holm_bonferroni(raw_p)
    correlation_matrix = []
    for (name, res), padj in zip(corr_tests, adj_p):
        correlation_matrix.append({**res, "test": name, "p_holm_adjusted": float(padj),
                                    "significant_at_05": bool(padj < 0.05)})
    logger.info(f"Computed {len(correlation_matrix)} univariate correlations (Holm-adjusted)")

    # ---- Phase 8: matched-pair register analysis ----
    tb_index = {r["treebank_id"]: r for r in treebank_table}
    matched_pair_results = []
    delta_xi_signs, delta_alpha_signs = [], []
    for pair in MATCHED_PAIRS:
        sp_id, wr_id = pair["spoken"], pair["written"]
        sp, wr = tb_index.get(sp_id), tb_index.get(wr_id)
        if sp is None or wr is None or sp.get("xi_75") is None or wr.get("xi_75") is None:
            matched_pair_results.append({**pair, "status": "missing_data"})
            continue
        d_xi = sp["xi_75"] - wr["xi_75"]
        d_alpha = sp["alpha_75"] - wr["alpha_75"]
        sp_boot = fit_results.get((sp_id, PRIMARY_THRESHOLD), {}).get("xi_boot")
        wr_boot = fit_results.get((wr_id, PRIMARY_THRESHOLD), {}).get("xi_boot")
        sp_a_boot = fit_results.get((sp_id, PRIMARY_THRESHOLD), {}).get("alpha_boot")
        wr_a_boot = fit_results.get((wr_id, PRIMARY_THRESHOLD), {}).get("alpha_boot")
        ci_dxi = ci_dalpha = (None, None)
        if sp_boot and wr_boot:
            n = min(len(sp_boot), len(wr_boot))
            diffs = np.array(sp_boot[:n]) - np.array(wr_boot[:n])
            ci_dxi = (float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))
        if sp_a_boot and wr_a_boot:
            n = min(len(sp_a_boot), len(wr_a_boot))
            diffs = np.array(sp_a_boot[:n]) - np.array(wr_a_boot[:n])
            ci_dalpha = (float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)))
        matched_pair_results.append({
            "language": pair["language"], "spoken_treebank": sp_id, "written_treebank": wr_id,
            "caveat": pair.get("caveat"), "status": "ok",
            "xi_spoken": sp["xi_75"], "xi_written": wr["xi_75"], "delta_xi": d_xi,
            "delta_xi_ci_lower": ci_dxi[0], "delta_xi_ci_upper": ci_dxi[1],
            "alpha_spoken": sp["alpha_75"], "alpha_written": wr["alpha_75"], "delta_alpha": d_alpha,
            "delta_alpha_ci_lower": ci_dalpha[0], "delta_alpha_ci_upper": ci_dalpha[1],
            "spoken_lighter_tail_xi": bool(d_xi < 0),
            "spoken_lighter_tail_alpha": bool(d_alpha > 0),
        })
        delta_xi_signs.append(d_xi < 0)
        delta_alpha_signs.append(d_alpha > 0)
    n_spoken_lighter_xi = sum(delta_xi_signs)
    n_spoken_lighter_alpha = sum(delta_alpha_signs)
    logger.info(f"Matched pairs: {n_spoken_lighter_xi}/{len(delta_xi_signs)} show spoken-lighter (xi); "
                f"{n_spoken_lighter_alpha}/{len(delta_alpha_signs)} (alpha)")

    # ---- Phase 9: mixed-effects models (register ~ xi/alpha, family random intercept) ----
    mm_df = primary_df.dropna(subset=["register_binary", "xi_75", "alpha_75"]).copy()
    mm_df = mm_df.rename(columns={"xi_75": "xi", "alpha_75": "alpha"})
    model_specs = [
        ("Model1_xi_only", "register_binary ~ xi"),
        ("Model2_alpha_only", "register_binary ~ alpha"),
        ("Model3_xi_plus_alpha", "register_binary ~ xi + alpha"),
    ]
    model_fits = {}
    if len(mm_df) >= 6 and mm_df["family"].nunique() >= 2:
        for label, formula in model_specs:
            model_fits[label] = fit_mixed_or_fallback(formula, mm_df, "family", label)
    else:
        logger.warning(f"Insufficient data for mixed-effects models (n={len(mm_df)}); skipping Phase 9")

    model_comparison = None
    if model_fits and all(m.get("aicc") is not None for m in model_fits.values()):
        labels = list(model_fits.keys())
        aiccs = [model_fits[l]["aicc"] for l in labels]
        weights = akaike_weights(aiccs)
        min_aicc = min(a for a in aiccs if np.isfinite(a))
        model_comparison = [
            {"model": l, "aicc": model_fits[l]["aicc"], "delta_aicc": model_fits[l]["aicc"] - min_aicc,
             "akaike_weight": w, "r2_marginal": model_fits[l].get("r2_marginal"),
             "r2_conditional": model_fits[l].get("r2_conditional"), "method": model_fits[l].get("method")}
            for l, w in zip(labels, weights)
        ]
        logger.info(f"Model comparison: {[(m['model'], round(m['akaike_weight'], 3)) for m in model_comparison]}")

    # ---- Phase 10: typology-controlled models ----
    typo_df = mm_df.dropna(subset=["head_finality_ratio"]).copy()
    typo_models = {}
    if len(typo_df) >= 6:
        typo_models["typology_only"] = fit_mixed_or_fallback(
            "register_binary ~ head_finality_ratio", typo_df, "family", "typology_only")
        typo_models["typology_plus_xi"] = fit_mixed_or_fallback(
            "register_binary ~ head_finality_ratio + xi", typo_df, "family", "typology_plus_xi")
        typo_models["typology_plus_alpha"] = fit_mixed_or_fallback(
            "register_binary ~ head_finality_ratio + alpha", typo_df, "family", "typology_plus_alpha")
        r2_base = typo_models["typology_only"].get("r2_conditional")
        r2_xi = typo_models["typology_plus_xi"].get("r2_conditional")
        r2_alpha = typo_models["typology_plus_alpha"].get("r2_conditional")
        typo_r2_deltas = {
            "delta_r2_from_xi": (r2_xi - r2_base) if (r2_xi is not None and r2_base is not None) else None,
            "delta_r2_from_alpha": (r2_alpha - r2_base) if (r2_alpha is not None and r2_base is not None) else None,
        }
    else:
        typo_r2_deltas = None
        logger.warning("Insufficient data with head_finality for Phase 10 typology-controlled models")

    # ---- Phase 11: sensitivity across thresholds ----
    sensitivity = []
    for q in THRESHOLDS:
        suffix = str(int(q * 100))
        sub = primary_df.dropna(subset=[f"xi_{suffix}", f"alpha_{suffix}"])
        reg_sub_q = sub.dropna(subset=["register_binary"])
        xi_reg_corr = spearman_ci(reg_sub_q[f"xi_{suffix}"].to_numpy(), reg_sub_q["register_binary"].to_numpy()) if len(reg_sub_q) >= 4 else None
        alpha_reg_corr = spearman_ci(reg_sub_q[f"alpha_{suffix}"].to_numpy(), reg_sub_q["register_binary"].to_numpy()) if len(reg_sub_q) >= 4 else None
        xi_alpha_c = spearman_ci(sub[f"xi_{suffix}"].to_numpy(), sub[f"alpha_{suffix}"].to_numpy()) if len(sub) >= 4 else None
        sensitivity.append({
            "threshold_quantile": q, "n_treebanks": len(sub),
            "xi_vs_register_rho": xi_reg_corr["rho"] if xi_reg_corr else None,
            "alpha_vs_register_rho": alpha_reg_corr["rho"] if alpha_reg_corr else None,
            "xi_vs_alpha_rho": xi_alpha_c["rho"] if xi_alpha_c else None,
        })
    reg_direction_flip = False
    rhos = [s["xi_vs_register_rho"] for s in sensitivity if s["xi_vs_register_rho"] is not None]
    if len(rhos) >= 2 and (max(rhos) > 0) and (min(rhos) < 0):
        reg_direction_flip = True
    logger.info(f"Sensitivity across thresholds computed; register-effect sign flip across thresholds: {reg_direction_flip}")

    # ---- Phase 12: outlier detection ----
    outliers = []
    for family, grp in primary_df.groupby("family"):
        if grp["language"].nunique() < 2:
            continue
        for col, resid_name in [("xi_75", "xi_residual"), ("alpha_75", "alpha_residual")]:
            mu, sd = grp[col].mean(), grp[col].std(ddof=0)
            if not sd or not np.isfinite(sd) or sd == 0:
                continue
            for _, r in grp.iterrows():
                z = (r[col] - mu) / sd
                if abs(z) > 2.0:
                    outliers.append({
                        "treebank_id": r["treebank_id"], "family": family, "metric": col,
                        "value": r[col], "standardized_residual": float(z),
                        "note": "flagged via within-family standardization; manual syntactic inspection not automated in this pipeline",
                    })
    logger.info(f"Outlier treebanks flagged: {len(outliers)}")

    # ---- Narrative + verdict ----
    xi_alpha_redundant = xi_alpha_corr["rho"] is not None and abs(xi_alpha_corr["rho"]) > 0.7
    xi_alpha_independent = xi_alpha_corr["rho"] is not None and abs(xi_alpha_corr["rho"]) < 0.5
    both_beat_either = False
    if model_comparison:
        w3 = next((m["akaike_weight"] for m in model_comparison if m["model"] == "Model3_xi_plus_alpha"), None)
        w1 = next((m["akaike_weight"] for m in model_comparison if m["model"] == "Model1_xi_only"), None)
        w2 = next((m["akaike_weight"] for m in model_comparison if m["model"] == "Model2_alpha_only"), None)
        both_beat_either = w3 is not None and w1 is not None and w2 is not None and w3 > w1 and w3 > w2
    register_confirmed = n_spoken_lighter_xi >= 3 or n_spoken_lighter_alpha >= 3

    if (not xi_alpha_redundant) and both_beat_either and register_confirmed:
        verdict = "CONFIRMS"
    elif (not xi_alpha_redundant) or register_confirmed:
        verdict = "PARTIALLY_CONFIRMS"
    else:
        verdict = "UNCONFIRMED"

    narrative = {
        "a_xi_alpha_relationship": (
            f"Spearman rho(xi, alpha) = {xi_alpha_corr['rho']}; "
            f"{'REDUNDANT (>0.7)' if xi_alpha_redundant else ('INDEPENDENT (<0.5)' if xi_alpha_independent else 'MODERATE overlap')}"
        ),
        "b_both_beat_either": f"Model3 (xi+alpha) has higher Akaike weight than both single-predictor models: {both_beat_either}",
        "c_register_effect": (
            f"{n_spoken_lighter_xi}/{len(delta_xi_signs)} matched pairs show spoken-lighter-tail via xi; "
            f"{n_spoken_lighter_alpha}/{len(delta_alpha_signs)} via alpha (majority threshold = 3/4)"
        ),
        "d_beyond_typology": typo_r2_deltas,
        "e_typology_dissociation": [c for c in correlation_matrix if "grambank" in c["test"] or "head_finality" in c["test"]],
        "f_threshold_robustness": f"Register-effect sign flip across 75/80/90th percentile thresholds: {reg_direction_flip}",
    }

    # ---- Assemble exp_gen_sol_out.json ----
    examples_out = []
    for entry in treebank_table:
        tb_id = entry["treebank_id"]
        input_payload = {
            "treebank_id": tb_id, "language": entry["language"], "family": entry["family"],
            "register": entry["register"], "n_sentences": entry["n_sentences"], "n_arcs": entry["n_arcs"],
            "primary_threshold_quantile": PRIMARY_THRESHOLD,
        }
        output_payload = {
            "xi_75": entry.get("xi_75"), "xi_ci_lower": entry.get("xi_ci_lower"), "xi_ci_upper": entry.get("xi_ci_upper"),
            "alpha_75": entry.get("alpha_75"), "alpha_ci_lower": entry.get("alpha_ci_lower"), "alpha_ci_upper": entry.get("alpha_ci_upper"),
            "xi_80": entry.get("xi_80"), "alpha_80": entry.get("alpha_80"),
            "xi_90": entry.get("xi_90"), "alpha_90": entry.get("alpha_90"),
            "threshold_75": entry.get("threshold_75"), "n_exceedances_75": entry.get("n_exceedances_75"),
            "head_finality_ratio": entry.get("head_finality_ratio"),
            "grambank_composite": entry.get("grambank_composite"),
            "excluded_from_primary_analysis": entry.get("excluded_primary"),
        }
        examples_out.append({
            "input": json.dumps(input_payload, allow_nan=False),
            "output": json.dumps(output_payload, allow_nan=False),
            "metadata_treebank_id": tb_id,
            "metadata_language": entry["language"],
            "metadata_family": entry["family"],
            "metadata_register": entry["register"],
            "predict_our_method": "" if entry.get("xi_75") is None else f"{entry['xi_75']:.6f}",
            "predict_baseline": "" if entry.get("alpha_75") is None else f"{entry['alpha_75']:.6f}",
        })

    def clean_nan(obj):
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_nan(v) for v in obj]
        if isinstance(obj, float) and not np.isfinite(obj):
            return None
        if isinstance(obj, (np.floating,)):
            return None if not np.isfinite(obj) else float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    output = {
        "metadata": {
            "method_name": "GPD-shape (xi) vs power-law-exponent (alpha) tail indices for UD dependency distances",
            "description": ("Peaks-over-threshold extreme value analysis (Generalized Pareto MLE, our method) compared "
                             "against a Clauset et al. (2009) power-law-exponent baseline, both fit to the same "
                             "exceedances above the 75th/80th/90th percentile of sentence-length-normalized dependency "
                             "distances, per UD treebank."),
            "n_treebanks_total": len(tb_df),
            "n_treebanks_primary": len(included),
            "excluded_treebanks_small_n": excluded,
            "bootstrap_resamples": B_BOOTSTRAP,
            "primary_threshold_quantile": PRIMARY_THRESHOLD,
            "sensitivity_thresholds": THRESHOLDS,
            "unstable_ci_treebanks": unstable,
            "mrl_plots_representative": mrl_plots,
            "xi_vs_alpha_correlation": xi_alpha_corr,
            "xi_vs_alpha_regression": xi_alpha_regression,
            "correlation_matrix": correlation_matrix,
            "matched_pair_register_analysis": matched_pair_results,
            "matched_pairs_spoken_lighter_xi": f"{n_spoken_lighter_xi}/{len(delta_xi_signs)}",
            "matched_pairs_spoken_lighter_alpha": f"{n_spoken_lighter_alpha}/{len(delta_alpha_signs)}",
            "mixed_effects_model_fits": model_fits,
            "mixed_effects_model_comparison": model_comparison,
            "typology_controlled_models": typo_models,
            "typology_controlled_r2_deltas": typo_r2_deltas,
            "threshold_sensitivity": sensitivity,
            "register_effect_sign_flip_across_thresholds": reg_direction_flip,
            "outlier_treebanks": outliers,
            "narrative_summary": narrative,
            "verdict": verdict,
            "seed": SEED,
        },
        "datasets": [{"dataset": "ud_treebanks", "examples": examples_out}],
    }
    output = clean_nan(output)

    out_path = WORKDIR / "method_out.json"
    out_path.write_text(json.dumps(output, indent=2))
    logger.info(f"Wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)")
    logger.info(f"VERDICT: {verdict}")


if __name__ == "__main__":
    main()
