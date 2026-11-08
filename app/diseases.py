"""Disease-name registry, kept separate from the advisory knowledge base."""
from dataclasses import dataclass
import re
from rapidfuzz import fuzz


@dataclass(frozen=True)
class Disease:
    id: str
    crop: str
    name_kn: str
    name_en: str
    aliases: tuple[str, ...]
    symptom_ids: tuple[str, ...]
    has_advisory: bool = False
    pest: bool = False
    confirmation_aliases: tuple[str, ...] = ()


# Recognition data only. This file deliberately contains no diagnosis guidance,
# treatment, chemical, or dosage content.
DISEASES = (
    Disease("paddy_blast", "paddy", "ಬೆಂಕಿ ರೋಗ", "Rice blast",
            ("ಬೆಂಕಿ ರೋಗ", "ಬೆಂಕಿರೋಗ", "ಬ್ಲಾಸ್ಟ್ ರೋಗ", "ಬ್ಲಾಸ್ಟ್",
             "benki roga", "benkiroga", "blast", "rice blast"),
            ("leaf_spots", "drying")),
    Disease("paddy_brown_spot", "paddy", "ಕಂದು ಚುಕ್ಕೆ ರೋಗ", "Brown spot",
            ("ಕಂದು ಚುಕ್ಕೆ ರೋಗ", "ಕಂದು ಚುಕ್ಕೆ", "kandu chukke", "brown spot", "rice brown spot"),
            ("leaf_spots", "grain_damage")),
    Disease("paddy_sheath_blight", "paddy", "ಕವಚ ಅಂಗಮಾರಿ ರೋಗ", "Sheath blight",
            ("ಕವಚ ಅಂಗಮಾರಿ ರೋಗ", "ಅಂಗಮಾರಿ", "angamari", "sheath blight"),
            ("rotting", "drying")),
    Disease("paddy_bacterial_blight", "paddy", "ಬ್ಯಾಕ್ಟೀರಿಯಾ ಎಲೆ ಸುಡು ರೋಗ", "Bacterial leaf blight",
            ("ಬ್ಯಾಕ್ಟೀರಿಯಾ ಎಲೆ ಸುಡು ರೋಗ", "ಎಲೆ ಸುಡು ರೋಗ", "bacterial blight", "bacterial leaf blight"),
            ("yellowing", "drying")),
    Disease("paddy_false_smut", "paddy", "ಸುಳ್ಳು ಕಾಡಿಗೆ ರೋಗ", "False smut",
            ("ಸುಳ್ಳು ಕಾಡಿಗೆ ರೋಗ", "ಕಾಡಿಗೆ ರೋಗ", "false smut"),
            ("grain_damage",)),
    Disease("paddy_tungro", "paddy", "ತುಂಗ್ರೋ ರೋಗ", "Tungro",
            ("ತುಂಗ್ರೋ ರೋಗ", "ತುಂಗ್ರೋ", "tungro"),
            ("yellowing", "stunted")),
    Disease("paddy_sheath_rot", "paddy", "ಕವಚ ಕೊಳೆ ರೋಗ", "Sheath rot",
            ("ಕವಚ ಕೊಳೆ ರೋಗ", "ಕವಚ ಕೊಳೆ", "sheath rot"),
            ("rotting",)),
    Disease("paddy_leaf_folder", "paddy", "ಎಲೆ ಸುತ್ತುವ ಹುಳು", "Leaf folder",
            ("ಎಲೆ ಸುತ್ತ", "ಎಲೆ ಮಡಚ", "ಸುತ್ತಿಕೊಂಡ", "ಸುತ್ತಿಕೊಳ್ಳ", "leaf folder", "leaf roll", "leaf fold"),
            ("leaf_spots", "drying"), pest=True),

    Disease("coconut_bud_rot", "coconut", "ತೆಂಗಿನ ಸುಳಿ ಕೊಳೆ", "Bud rot",
            ("ಮೊಗ್ಗು ಕೊಳೆ ರೋಗ", "ಮೊಗ್ಗು ಕೊಳೆ", "ಮೊಗ್ಗುಕೊಳೆ", "ಕುಡಿ ಕೊಳೆ", "ಸುಳಿ ಕೊಳೆ",
             "moggu kole roga", "moggu kole", "bud rot"),
            ("rotting", "crown")),
    Disease("coconut_basal_stem_rot", "coconut", "ಬುಡ ಕಾಂಡ ಕೊಳೆ ರೋಗ", "Basal stem rot",
            ("ಬುಡ ಕಾಂಡ ಕೊಳೆ ರೋಗ", "ಗ್ಯಾನೋಡರ್ಮಾ ಸೊರಗು ರೋಗ", "ganoderma", "basal stem rot"),
            ("yellowing", "oozing", "wilting", "rotting")),
    Disease("coconut_root_wilt", "coconut", "ಬೇರು ಸೊರಗು ರೋಗ", "Root wilt",
            ("ಬೇರು ಸೊರಗು ರೋಗ", "ಬೇರು ಸೊರಗು", "beru soragu", "root wilt"),
            ("yellowing", "wilting")),
    Disease("coconut_leaf_spot", "coconut", "ಎಲೆ ಚುಕ್ಕೆ ರೋಗ", "Leaf spot / leaf blight",
            ("ಎಲೆ ಚುಕ್ಕೆ ರೋಗ", "ಎಲೆ ಚುಕ್ಕೆ", "ele chukke", "leaf spot", "leaf blight"),
            ("leaf_spots", "drying")),
    Disease("coconut_stem_bleeding", "coconut", "ಕಾಂಡ ರಸ ಸೋರುವ ರೋಗ", "Stem bleeding",
            ("ಕಾಂಡ ರಸ ಸೋರುವ ರೋಗ", "ರಸ ಸೋರುವ", "stem bleeding"),
            ("oozing",)),
    Disease("coconut_button_shedding", "coconut", "ಎಳೆ ಕಾಯಿ ಉದುರುವಿಕೆ", "Button shedding",
            ("ಎಳೆ ಕಾಯಿ ಉದುರುವಿಕೆ", "button shedding"),
            ("nut_fall",), confirmation_aliases=("nut fall", "nuts falling")),
    Disease("coconut_rhino_beetle", "coconut", "ಕೊಂಬಿನ ದುಂಬಿ", "Rhinoceros beetle",
            ("ಕೊಂಬಿನ ದುಂಬಿ", "rhinoceros beetle", "rhino beetle"),
            ("crown",), pest=True, confirmation_aliases=("ದುಂಬಿ", "beetle")),

    Disease("arecanut_koleroga", "arecanut", "ಅಡಿಕೆ ಕೊಳೆ ರೋಗ", "Fruit rot (Koleroga / Mahali)",
            ("ಮಹಾಲಿ ರೋಗ", "ಮಹಾಲಿ", "ಮಹಾಳಿ ರೋಗ", "ಮಹಾಳಿ",
             "koleroga", "kole roga", "mahali", "fruit rot"),
            ("rotting", "nut_fall"),
            confirmation_aliases=("ಕಾಯಿ ಕೊಳೆ", "ಕಾಯಿ ಕೊಳೆತ", "ಕೊಳೆ ರೋಗ", "ಕೊಳೆರೋಗ")),
    Disease("arecanut_yld", "arecanut", "ಹಳದಿ ಎಲೆ ರೋಗ", "Yellow leaf disease",
            ("ಹಳದಿ ಎಲೆ ರೋಗ", "ಹಳದಿ ಎಲೆ", "haladi ele roga", "yellow leaf disease"),
            ("yellowing", "stunted")),
    Disease("arecanut_foot_rot", "arecanut", "ಬುಡ ಕೊಳೆ ರೋಗ", "Foot rot (Anabe roga)",
            ("ಬುಡ ಕೊಳೆ ರೋಗ", "ಅನಾಬೆ ರೋಗ", "ಅನಾಬೆ", "anabe roga", "foot rot"),
            ("rotting", "oozing", "wilting")),
    Disease("arecanut_inflorescence_dieback", "arecanut", "ಹೂಗೊಂಚಲು ಒಣಗುವ ರೋಗ", "Inflorescence dieback",
            ("ಹೂಗೊಂಚಲು ಒಣಗುವ ರೋಗ", "ಹೂಗೊಂಚಲು", "inflorescence dieback"),
            ("flower", "drying")),
    Disease("arecanut_bud_rot", "arecanut", "ಅಡಿಕೆ ಮೊಗ್ಗು ಕೊಳೆ ರೋಗ", "Bud rot",
            ("ಮೊಗ್ಗು ಕೊಳೆ ರೋಗ", "ಮೊಗ್ಗು ಕೊಳೆ", "ಮೊಗ್ಗುಕೊಳೆ", "ಕುಡಿ ಕೊಳೆ", "moggu kole roga", "moggu kole", "bud rot"),
            ("rotting", "crown")),
    Disease("arecanut_leaf_spot", "arecanut", "ಎಲೆ ಚುಕ್ಕೆ ರೋಗ", "Leaf spot",
            ("ಎಲೆ ಚುಕ್ಕೆ ರೋಗ", "ಎಲೆ ಚುಕ್ಕೆ", "ele chukke", "leaf spot"),
            ("leaf_spots", "drying")),
)


def registry_for_kb(kb: dict) -> tuple[Disease, ...]:
    """Mark advice available only when a matching KB entry has usable text advice.

    Chemical review remains a separate gate in dialogue.py; these flags preserve
    the existing non-chemical advice for the five shipped records.
    """
    result = []
    for disease in DISEASES:
        entry = kb.get(disease.id)
        has_advisory = bool(
            entry
            and any(
                isinstance(sentences, list) and any(str(s).strip() for s in sentences)
                for sentences in entry.get("advice_kn", {}).values()
            )
        )
        result.append(Disease(**{**disease.__dict__, "has_advisory": has_advisory}))
    return tuple(result)


@dataclass(frozen=True)
class DiseaseMatch:
    ids: tuple[str, ...]
    method: str | None
    score: float
    crops_involved: tuple[str, ...]

    @property
    def single_id(self):
        return self.ids[0] if len(self.ids) == 1 else None

    @property
    def ambiguous(self):
        return len(self.ids) > 1

    @property
    def needs_confirm(self):
        return self.method in ("fuzzy", "weak") or self.ambiguous


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _is_kannada(text: str) -> bool:
    return any("\u0c80" <= ch <= "\u0cff" for ch in text)


def _ascii_alias_match(text: str, alias: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(alias)}(?![A-Za-z0-9_])"
    if re.search(pattern, text, flags=re.IGNORECASE):
        return True
    compact_alias = _compact(alias)
    return len(compact_alias) >= 7 and compact_alias in _compact(text)


def match_disease(text: str, crop: str | None, registry: tuple[Disease, ...],
                  crop_explicit: bool | None = None) -> DiseaseMatch:
    """Match disease names conservatively; fuzzy matches always require confirmation."""
    if crop_explicit is None:
        crop_explicit = crop is not None
    normalized = _normalize(text)
    compact_text = _compact(normalized)
    eligible = [d for d in registry if crop is None or d.crop == crop]

    # The shipped "ಎಲೆ ಮಡಚ" alias covers this inflected predicate when the
    # crop context already identifies paddy; keep morphology in matching code
    # rather than expanding the disease alias list.
    if crop == "paddy" and re.search(r"(?:^|\s)ಮಡಚಿಕೊಂಡಿದೆ(?=\s|$)", normalized):
        if any(d.id == "paddy_leaf_folder" for d in eligible):
            return DiseaseMatch(("paddy_leaf_folder",), "exact", 1.0, ("paddy",))

    exact_scores = {}

    for disease in eligible:
        best_score = 0
        best_is_weak = False
        for alias in disease.aliases + disease.confirmation_aliases:
            normalized_alias = _normalize(alias)
            compact_alias = _compact(normalized_alias)
            if not compact_alias:
                continue
            if _is_kannada(normalized_alias):
                matched = len(compact_alias) >= 3 and compact_alias in compact_text
            else:
                matched = _ascii_alias_match(normalized, normalized_alias)
            if matched:
                weak_alias = alias in disease.confirmation_aliases
                alias_needs_confirm = weak_alias and (
                    disease.id == "coconut_rhino_beetle" or not crop_explicit
                )
                if len(compact_alias) > best_score or (
                    len(compact_alias) == best_score and best_is_weak and not alias_needs_confirm
                ):
                    best_score = len(compact_alias)
                    best_is_weak = alias_needs_confirm
        if best_score:
            exact_scores[disease.id] = (best_score, best_is_weak)

    if exact_scores:
        best = max(score for score, _ in exact_scores.values())
        ids = tuple(d.id for d in eligible if exact_scores.get(d.id, (0, False))[0] == best)
        weak = any(exact_scores[disease_id][1] for disease_id in ids)
        method = "weak" if weak else "exact"
        return DiseaseMatch(ids, method, float(best), tuple(dict.fromkeys(d.crop for d in eligible if d.id in ids)))

    fuzzy_scores = {}
    if len(compact_text) >= 6:
        for disease in eligible:
            best_score = 0
            for alias in disease.aliases + disease.confirmation_aliases:
                compact_alias = _compact(_normalize(alias))
                if len(compact_alias) < 6 or len(compact_text) < len(compact_alias):
                    continue
                score = fuzz.partial_ratio(compact_alias, compact_text)
                if score >= 85:
                    best_score = max(best_score, score)
            if best_score:
                fuzzy_scores[disease.id] = best_score

    if fuzzy_scores:
        best = max(fuzzy_scores.values())
        ids = tuple(d.id for d in eligible
                    if fuzzy_scores.get(d.id, 0) >= 85 and best - fuzzy_scores.get(d.id, 0) <= 2)
        return DiseaseMatch(ids, "fuzzy", float(best), tuple(dict.fromkeys(d.crop for d in eligible if d.id in ids)))

    return DiseaseMatch((), None, 0.0, ())


SYMPTOM_ALIASES = {
    "yellowing": ("ಹಳದಿ", "ಹಳದಿಯಾಗುತ್ತಿದೆ", "ಹಳದಿಯಾಗುತ್ತಿವೆ", "haladi", "yellow"),
    "leaf_spots": ("ಚುಕ್ಕೆ", "ಕಲೆ", "chukke", "spot", "spots"),
    "rotting": ("ಕೊಳೆ", "ಕೊಳೆತ", "kole", "rot", "rotting"),
    "nut_fall": ("ಉದುರು", "ಉದುರ", "udur", "fall", "falls", "falling", "drop"),
    "drying": ("ಒಣಗ", "ಸುಡು", "onaga", "dry", "drying"),
    "oozing": ("ಸೋರು", "ರಸ ಸೋರು", "soru", "ooze", "oozing", "bleeding"),
    "wilting": ("ಸೊರಗು", "ಬಾಡಿದ", "ಬಾಡುತ್ತ", "ಬಾಡಿಹೋ", "soragu", "wilt", "wilting", "droop", "drooping"),
    "grain_damage": ("ಕಾಳು", "ಕಾಳಿನ", "ಧಾನ್ಯ", "ಧಾನ್ಯ ಹಾನಿ", "kaalu", "grain", "grains"),
    "stunted": ("ಕುಂಠಿತ", "ಕುಂಠಿತ ಬೆಳವಣಿಗೆ", "kuntita", "stunted", "stunted growth"),
    "flower": ("ಹೂವು", "ಹೂಗೊಂಚಲು", "flower", "flowers"),
    "crown": ("ಮೊಗ್ಗು", "crown", "bud"),
}


@dataclass(frozen=True)
class SymptomCandidate:
    id: str
    score: int
    matched_symptoms: tuple[str, ...]


def match_symptoms(text: str) -> frozenset[str]:
    """Return symptom groups found using Kannada compact-substrings/ASCII words."""
    normalized = _normalize(text)
    compact_text = _compact(normalized)
    found = set()
    for symptom_id, aliases in SYMPTOM_ALIASES.items():
        for alias in aliases:
            alias = _normalize(alias)
            compact_alias = _compact(alias)
            if _is_kannada(alias):
                # Keep short meaningful symptom words but ignore one-character fragments.
                matched = len(compact_alias) >= 2 and compact_alias in compact_text
            else:
                matched = _ascii_alias_match(normalized, alias)
            if matched:
                found.add(symptom_id)
                break
    return frozenset(found)


def rank_disease_candidates(symptoms: set[str] | frozenset[str], crop: str | None,
                            registry: tuple[Disease, ...]) -> tuple[SymptomCandidate, ...]:
    """Rank same-crop diseases by shared symptom IDs; registry order breaks ties."""
    if not crop or not symptoms:
        return ()
    ranked = []
    for disease in registry:
        if disease.crop != crop:
            continue
        overlap = tuple(s for s in disease.symptom_ids if s in symptoms)
        if overlap:
            ranked.append(SymptomCandidate(disease.id, len(overlap), overlap))
    ranked.sort(key=lambda c: -c.score)  # stable sort preserves registry order for ties
    return tuple(ranked)


def _normalize(text: str) -> str:
    """Local normalization matching dialogue.normalize without a circular import."""
    import unicodedata
    text = unicodedata.normalize("NFC", text or "").replace("\u200c", "").replace("\u200d", "")
    text = re.sub(r"[.,!?;:'()\"-]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()
