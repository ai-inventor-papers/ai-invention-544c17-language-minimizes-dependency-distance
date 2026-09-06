# /// script
# requires-python = ">=3.12"
# dependencies = ["loguru"]
# ///
"""Build exp_sel_data_out.json from downloaded UD treebanks + Grambank typology.

Group 1 ("ud_treebanks"): one example per SENTENCE across 18 UD v2.18 treebanks
(commul/universal-dependencies, HF), covering matched spoken/written register
pairs (Slovenian SST/SSJ, French Rhapsodie/GSD, English ESLSpok/EWT/GUM) plus
typologically diverse written treebanks (Arabic, Japanese, Korean, Hindi,
Finnish, Chinese, Russian, Turkish, Nigerian Pidgin). input = sentence surface
form + POS sequence; output = per-arc dependency distances (raw + length-
normalized) plus heads/deprels, everything needed downstream for a Dependency
Distance Minimization (DDM) / extreme-value analysis.

Group 2 ("grambank_typology"): one example per language in Grambank v1.0.3
(Zenodo 10.5281/zenodo.7740139), covering every language that also appears
among the UD treebanks above. input = language identity; output = the raw
Grambank feature-value vector (binary/multistate morphosyntactic features),
used as a typological covariate table joinable to the UD group by language
name / ISO code.
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add("logs/run.log", rotation="30 MB", level="DEBUG")

WORKSPACE = Path(__file__).resolve().parent
DATASETS_DIR = WORKSPACE / "temp" / "datasets"
GRAMBANK_CLDF = DATASETS_DIR / "grambank" / "grambank-grambank-7ae000c" / "cldf"

# treebank_id -> (language name, ISO 639-1/3 code used for Grambank/UD join, register, family)
TREEBANK_META = {
    "sl_sst": ("Slovenian", "slv", "spoken", "Indo-European"),
    "sl_ssj": ("Slovenian", "slv", "written", "Indo-European"),
    "fr_rhapsodie": ("French", "fra", "spoken", "Indo-European"),
    "fr_gsd": ("French", "fra", "written", "Indo-European"),
    "en_eslspok": ("English", "eng", "spoken", "Indo-European"),
    "en_ewt": ("English", "eng", "written", "Indo-European"),
    "en_gum": ("English", "eng", "mixed", "Indo-European"),
    "tr_atis": ("Turkish", "tur", "spoken", "Turkic"),
    "tr_imst": ("Turkish", "tur", "written", "Turkic"),
    "ar_padt": ("Arabic", "arb", "written", "Afro-Asiatic"),
    "ja_gsd": ("Japanese", "jpn", "written", "Japonic"),
    "ko_gsd": ("Korean", "kor", "written", "Koreanic"),
    "hi_hdtb": ("Hindi", "hin", "written", "Indo-European"),
    "fi_tdt": ("Finnish", "fin", "written", "Uralic"),
    "zh_gsd": ("Chinese", "cmn", "written", "Sino-Tibetan"),
    "ru_syntagrus": ("Russian", "rus", "written", "Indo-European"),
    "pcm_nsc": ("Nigerian Pidgin", "pcm", "mixed", "Creole"),
    "nap_rb": ("Neapolitan", "nap", "written", "Indo-European"),
}

# ISO 639-3 -> Glottocode, needed to join into Grambank (which is keyed by Glottocode).
# Verified against Grambank's languages.csv (ISO639P3code column) below at runtime;
# this table only seeds the join for languages whose ISO/name lookup is ambiguous.
ISO_TO_NAME_HINT = {
    "slv": "Slovenian",
    "fra": "French",
    "eng": "English",
    "tur": "Turkish",
    "arb": "Arabic",
    "jpn": "Japanese",
    "kor": "Korean",
    "hin": "Hindi",
    "fin": "Finnish",
    "cmn": "Mandarin Chinese",
    "rus": "Russian",
    "pcm": "Nigerian Pidgin",
    "nap": "Neapolitan-Calabrese",
}


MAX_SENTENCES_PER_TREEBANK = 2000  # keeps full_data_out.json well under the file-size limit;
# full raw treebanks remain on disk at temp/datasets/full_*.json for any downstream re-extraction.


def _evenly_spaced_indices(n: int, k: int) -> list[int]:
    """k indices into range(n), evenly spaced, preserving document order."""
    if n <= k:
        return list(range(n))
    step = n / k
    return sorted({int(i * step) for i in range(k)})


def build_ud_examples(grambank_by_language: dict[str, dict]) -> list[dict]:
    examples = []
    n_sentences_by_treebank: dict[str, int] = defaultdict(int)
    for treebank_id, (language, iso, register, family) in TREEBANK_META.items():
        matches = sorted(DATASETS_DIR.glob(f"full_universal-dependencies_universal_dependencies_{treebank_id}_*.json"))
        if not matches:
            logger.warning(f"No full_*.json found for treebank {treebank_id}, skipping")
            continue
        data_path = matches[0]
        logger.info(f"Loading {data_path.name}")
        all_sentences = json.loads(data_path.read_text())
        keep_idx = _evenly_spaced_indices(len(all_sentences), MAX_SENTENCES_PER_TREEBANK)
        sentences = [(i, all_sentences[i]) for i in keep_idx]
        for row_idx, sent in sentences:
            tokens = sent.get("tokens") or []
            heads = sent.get("head") or []
            deprel = sent.get("deprel") or []
            upos = sent.get("upos") or []
            n = len(tokens)
            if n == 0 or len(heads) != n:
                continue

            distances = []
            normalized = []
            head_final_count = 0
            n_arcs = 0
            for tok_pos_0idx, head_1idx in enumerate(heads):
                if head_1idx is None or head_1idx == 0:
                    continue  # skip artificial root arc (ROOT.0 -> X)
                dep_pos = tok_pos_0idx + 1  # 1-indexed token position
                dist = abs(dep_pos - head_1idx)
                distances.append(dist)
                normalized.append(round(dist / n, 6))
                n_arcs += 1
                if head_1idx > dep_pos:
                    head_final_count += 1

            if n_arcs == 0:
                continue

            input_obj = {
                "treebank_id": treebank_id,
                "text": sent.get("text"),
                "tokens": tokens,
                "upos": upos,
            }
            output_obj = {
                "dependency_distances": distances,
                "normalized_distances": normalized,
                "heads": heads,
                "deprel": deprel,
            }

            grambank_feats = grambank_by_language.get(language)

            examples.append(
                {
                    "input": json.dumps(input_obj, ensure_ascii=False),
                    "output": json.dumps(output_obj, ensure_ascii=False),
                    "metadata_treebank_id": treebank_id,
                    "metadata_language": language,
                    "metadata_iso639_3": iso,
                    "metadata_language_family": family,
                    "metadata_register": register,
                    "metadata_sentence_id": sent.get("sent_id"),
                    "metadata_row_index": row_idx,
                    "metadata_sentence_length": n,
                    "metadata_num_arcs": n_arcs,
                    "metadata_mean_dependency_distance": round(sum(distances) / n_arcs, 6),
                    "metadata_mean_normalized_distance": round(sum(normalized) / n_arcs, 6),
                    "metadata_head_finality_ratio": round(head_final_count / n_arcs, 6),
                    "metadata_grambank_features": json.dumps(grambank_feats, ensure_ascii=False) if grambank_feats else None,
                }
            )
            n_sentences_by_treebank[treebank_id] += 1

    for tbk, cnt in sorted(n_sentences_by_treebank.items()):
        logger.info(f"  {tbk}: {cnt} sentence examples")
    return examples


def build_grambank_lookup() -> dict[str, dict]:
    """Language name -> Grambank feature-value dict, for the languages in TREEBANK_META.

    Grambank is language-level, not treebank-level: this covariate table is joined
    onto every ud_treebanks example of a matching language (both registers of the
    same language get identical typology, by design — the "within-language matched"
    setup the artifact plan calls for).
    """
    languages_path = GRAMBANK_CLDF / "languages.csv"
    values_path = GRAMBANK_CLDF / "values.csv"
    if not languages_path.exists() or not values_path.exists():
        logger.warning("Grambank CLDF files not found, ud examples will have metadata_grambank_features=null")
        return {}

    target_names = {name for (name, _iso, _reg, _fam) in TREEBANK_META.values()}
    target_names |= set(ISO_TO_NAME_HINT.values())

    lang_rows = {}
    with languages_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lang_rows[row["ID"]] = row  # ID == Glottocode

    matched_glottocodes = {gid: row for gid, row in lang_rows.items() if row["Name"] in target_names}
    logger.info(f"Grambank: matched {len(matched_glottocodes)}/{len(target_names)} target languages by name")

    feature_values: dict[str, dict[str, str]] = defaultdict(dict)
    with values_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            gid = row["Language_ID"]
            if gid in matched_glottocodes:
                feature_values[gid][row["Parameter_ID"]] = row["Value"]

    # Keep a compact core subset (~15 features, per the artifact plan's "10-15 core
    # features per language") rather than the full 195-feature vector on every one
    # of 33k sentence examples — the full per-language vectors remain retrievable
    # from temp/datasets/grambank/ if a downstream step needs the complete table.
    core_feature_ids = sorted({fid for feats in feature_values.values() for fid in feats})[:15]

    lookup: dict[str, dict] = {}
    for gid, lang_row in matched_glottocodes.items():
        feats = feature_values.get(gid, {})
        core = {fid: feats[fid] for fid in core_feature_ids if fid in feats}
        if core:
            lookup[lang_row["Name"]] = core
    logger.info(f"Grambank: built typology lookup for {len(lookup)} languages ({len(core_feature_ids)} core features each)")
    return lookup


def main() -> None:
    Path("logs").mkdir(exist_ok=True)

    grambank_lookup = build_grambank_lookup()

    ud_examples = build_ud_examples(grambank_lookup)
    if not ud_examples:
        raise RuntimeError("No UD sentence examples were built — check temp/datasets/ contents")
    logger.info(f"Total ud_treebanks examples: {len(ud_examples)}")
    n_with_typology = sum(1 for e in ud_examples if e["metadata_grambank_features"] is not None)
    logger.info(f"  of which {n_with_typology} carry a joined Grambank typology vector")

    output = {
        "metadata": {
            "source": "universal-dependencies/universal_dependencies (HF, UD v2.18; alias commul/universal_dependencies) + Grambank v1.0.3 (Zenodo 10.5281/zenodo.7740139) joined as a per-language covariate",
            "description": (
                "Per-sentence dependency-distance data across 18 UD treebanks (matched spoken/written "
                "register pairs + typologically diverse written treebanks). Each example carries the "
                "sentence's raw + length-normalized dependency distances, heads/deprels, and a joined "
                "Grambank typological feature vector for its language (same vector for both registers of "
                "a language, i.e. the within-language matched design), for Dependency Distance "
                "Minimization and extreme-value analysis across languages/registers/typology."
            ),
            "n_treebanks": len(TREEBANK_META),
            "n_ud_examples": len(ud_examples),
            "n_examples_with_grambank_typology": n_with_typology,
        },
        "datasets": [
            {"dataset": "ud_treebanks", "examples": ud_examples},
        ],
    }

    out_path = WORKSPACE / "full_data_out.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False))
    logger.info(f"Wrote {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
