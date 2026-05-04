from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

from harness_benchmark.challenges.base import (
    ActionDescriptor,
    ActionResult,
    BaseChallenge,
    CostConfig,
    EventDescriptor,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN = 4
TOKENS_PER_PAGE = 1_000
PAGES_PER_FRAGMENT = 3
TOKENS_PER_FRAGMENT = PAGES_PER_FRAGMENT * TOKENS_PER_PAGE
CHARS_PER_FRAGMENT = TOKENS_PER_FRAGMENT * CHARS_PER_TOKEN
CHARS_PER_PAGE = TOKENS_PER_PAGE * CHARS_PER_TOKEN

DIFFICULTY_CONFIGS: dict[str, dict[str, Any]] = {
    "easy":   {"num_glyphs": 10, "num_fragments": 5,  "num_decoys": 5},
    "medium": {"num_glyphs": 30, "num_fragments": 150, "num_decoys": 25},
    "hard":   {"num_glyphs": 50, "num_fragments": 250, "num_decoys": 50},
}

# ---------------------------------------------------------------------------
# Glyph pool — 60 distinct Unicode symbols
# ---------------------------------------------------------------------------

GLYPH_POOL: list[str] = [
    "◊", "◈", "◉", "◌", "◍", "◎", "●", "◐", "◑", "◒",
    "◓", "◔", "◕", "◖", "◗", "◘", "◙", "◚", "◛", "◜",
    "◝", "◞", "◟", "◠", "◡", "◢", "◣", "◤", "◥", "◦",
    "◧", "◨", "◩", "◪", "◫", "◬", "◭", "◮", "◯", "★",
    "☆", "♠", "♡", "♢", "♣", "♤", "♥", "♦", "♧", "✦",
    "✧", "✩", "✪", "✫", "✬", "✭", "✮", "✯", "✰", "✱",
]

# Encodable units: 26 single letters + 24 common English digraphs = 50 total
_SINGLE_LETTERS: list[str] = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_DIGRAPHS: list[str] = [
    "TH", "HE", "IN", "ER", "AN", "RE", "ON", "AT", "EN", "ND",
    "TI", "ES", "OR", "TE", "OF", "ED", "IS", "IT", "AL", "AR",
    "ST", "TO", "NT", "NG",
]

# ---------------------------------------------------------------------------
# Prose generation
# ---------------------------------------------------------------------------

_PARA_TEMPLATES: list[str] = [
    (
        "The study of {topic} has attracted significant scholarly attention over recent decades. "
        "Early investigators documented that {observation}, a finding which prompted revision of "
        "several foundational assumptions. Subsequent work by practitioners in the {region} tradition "
        "confirmed the pattern across a wider range of {subject} instances, establishing a basis for "
        "the comparative framework that now dominates the field. The implications for adjacent "
        "disciplines were not immediately apparent, though {implication} proved particularly "
        "consequential for subsequent research programs. Questions regarding {open_question} remain "
        "unresolved, and the current literature reflects this uncertainty in its treatment of boundary "
        "cases and transitional examples. Further investigation along these lines is expected to "
        "yield results of broad theoretical importance within the next several years."
    ),
    (
        "Archival research conducted at the {location} repository yielded a substantial body of "
        "documentary evidence bearing on the {subject} question. Materials dating from the {era} "
        "period were examined systematically, revealing {result_count} previously uncatalogued items "
        "of potential significance. The documents exhibit consistent internal evidence that {claim}, "
        "a conclusion that aligns with but does not depend upon the physical evidence recovered from "
        "associated contexts. Counterarguments to the effect that {counterargument} have been "
        "considered and found unconvincing in light of the cumulative record. Further archival "
        "research at comparable institutions would likely strengthen these conclusions considerably."
    ),
    (
        "Methodological developments in {topic} have significantly altered the questions that "
        "investigators can address empirically. The introduction of {method} as an analytical "
        "tool opened access to data previously inaccessible to direct examination, enabling "
        "researchers to assess competing hypotheses with greater precision. Early applications "
        "of this approach yielded results consistent with the {position_a} interpretation, "
        "prompting a degree of theoretical consolidation that subsequent work has tested "
        "unevenly. The {anomaly} remains resistant to explanation under the dominant framework, "
        "however, and several research groups have proposed theoretical modifications intended "
        "to accommodate it. Whether these modifications preserve the explanatory power of the "
        "original model is a matter of ongoing discussion among specialists in the field."
    ),
    (
        "Field investigations at site {site_id} were conducted over {duration} under varied "
        "conditions. The recovered assemblage comprises {artifact_count} items distributed across "
        "several distinct depositional contexts. Stratigraphic analysis indicates a complex "
        "formation history, with evidence of both primary deposition and secondary disturbance in "
        "different areas of the site. The {period} horizon is most clearly defined in the northern "
        "sector, where {fraction} of all recovered materials are attributed to this phase. "
        "Comparative analysis with {comparison_site} suggests connections to broader exchange "
        "networks that extended across a wide geographic area during this period of sustained contact."
    ),
    (
        "The theoretical debate between the {position_a} and competing frameworks has generated "
        "a substantial secondary literature that now threatens to obscure the original empirical "
        "questions at issue. Proponents of each position have tended to emphasize evidence "
        "favorable to their own interpretation while finding methodological fault with studies "
        "that yield less supportive results. Several meta-analyses have attempted to aggregate "
        "available evidence, with mixed outcomes: {result} in approximately {fraction} of cases "
        "examined. The field would benefit from pre-registered studies designed to test "
        "diagnostic predictions derived from each framework, though institutional incentives "
        "do not currently favor this more rigorous approach to adjudicating the dispute."
    ),
    (
        "Comparative analysis of {item_a} and {item_b} reveals both structural similarities and "
        "significant differences that inform ongoing debates in the field. The similarities, "
        "documented by {person_a} and others working in the same tradition, suggest a common "
        "origin or prolonged contact between the producing groups. The differences, by contrast, "
        "point toward divergent developmental trajectories once the initial period of contact ended. "
        "Quantitative analysis of {variable_a} and {variable_b} shows a pattern consistent with "
        "gradual divergence over the course of the {era} period, though the rate of change varies "
        "across different dimensions of the material and documentary record available for study."
    ),
    (
        "Statistical analysis of the available data reveals a correlation between {variable_a} "
        "and {variable_b} with a coefficient of {coefficient}. The relationship holds across "
        "{trial_count} independent replications and remains significant after controlling for "
        "{confound}. These findings provide empirical support for the theoretical model proposed "
        "by {theorist}, though several aspects of that model require modification in light of "
        "the present results. The direction of the causal relationship remains uncertain, "
        "as the available data are consistent with multiple causal structures. Experimental "
        "designs that could resolve this ambiguity have been proposed but not yet fully implemented."
    ),
    (
        "The correspondence between {person_a} and {person_b}, spanning the period from {year} "
        "to approximately a decade later, documents the development of ideas that would later "
        "prove central to the field. Early letters express uncertainty about {claim}, which "
        "the participants regarded as {qualifier} in the absence of stronger supporting evidence. "
        "Later exchanges show increasing confidence as additional data became available, "
        "culminating in a joint publication that is now considered foundational. The {count} "
        "surviving letters represent only a portion of the total exchange; the remainder were "
        "either lost or remain in private hands and have not been made available for examination."
    ),
    (
        "Recent excavations have extended the known distribution of the {subject} tradition "
        "considerably beyond the boundaries established by earlier surveys. The new sites, "
        "identified through {method}, exhibit assemblage compositions consistent with {claim} "
        "but also display certain distinctive features not previously documented in the literature. "
        "Chronometric dating of organic samples from sealed contexts indicates that the relevant "
        "activity spanned approximately {duration}, somewhat longer than earlier estimates suggested. "
        "This expanded time range has implications for models of how the tradition developed and "
        "how it related to other contemporary phenomena documented in adjacent geographic areas."
    ),
    (
        "Longitudinal monitoring of the {subject} phenomenon over a period of {duration} has "
        "produced a dataset of sufficient depth to evaluate several competing models. The {position_a} "
        "model correctly predicts the overall trajectory but systematically underestimates variance "
        "in the middle portion of the record. Alternative models that incorporate {variable_a} as "
        "an additional parameter perform better on this dimension but introduce additional complexity "
        "that is not warranted by the marginal improvement in fit. The preferred approach at this "
        "stage is to retain the simpler model while flagging its known limitations for practical "
        "applications that depend on accurate variance estimates across the full temporal range."
    ),
]

_FILLERS: dict[str, list[str]] = {
    "topic": [
        "comparative linguistics", "archival historiography", "stratigraphic analysis",
        "institutional economics", "computational philology", "settlement archaeology",
        "climate reconstruction", "manuscript studies", "material culture analysis",
        "network cartography", "historical demography", "numismatic research",
    ],
    "observation": [
        "certain anomalies recurred under controlled conditions",
        "the expected correlation failed to materialize in several important cases",
        "variance increased systematically with sample size",
        "boundary cases produced outcomes inconsistent with the dominant model",
        "the observed distribution differed significantly from theoretical expectations",
        "two distinct populations could be identified within the previously unified category",
    ],
    "region": ["northern", "eastern", "coastal", "highland", "central", "western", "continental", "insular", "southern"],
    "subject": [
        "the practice", "the phenomenon", "the artifact class", "the technique",
        "the institutional form", "the textual corpus", "the material tradition", "the exchange network",
    ],
    "implication": [
        "the revision of standard chronologies",
        "a reassessment of causal relationships",
        "methodological innovation in adjacent subfields",
        "a narrowing of theoretical consensus",
        "the identification of previously overlooked patterns",
        "the integration of formerly distinct research programs",
    ],
    "open_question": [
        "the precise boundary conditions",
        "the role of environmental factors",
        "long-term stability across contexts",
        "cross-regional variation in rates of change",
        "the direction of causation",
        "the mechanisms of transmission across generations",
    ],
    "location": [
        "northern archive", "eastern repository", "coastal collection", "highland depot",
        "central registry", "western reading room", "institutional library", "regional depot",
    ],
    "era": [
        "early classical", "late archaic", "transitional", "middle period",
        "terminal phase", "pre-modern", "formative", "consolidation",
    ],
    "result_count": ["fourteen", "several dozen", "over three hundred", "forty-seven", "more than a thousand", "sixty-two"],
    "claim": [
        "the technique predated the commonly accepted origin by several generations",
        "the distribution was far wider than previous surveys had indicated",
        "the primary function was ceremonial rather than utilitarian",
        "the materials were imported rather than locally produced",
        "the chronological framework required substantial revision",
        "a previously unsuspected connection existed between the two traditions",
    ],
    "counterargument": [
        "the source material is too fragmentary to support such conclusions",
        "the author had evident reasons to misrepresent the situation",
        "later interpolations cannot be ruled out",
        "the comparison cases are not strictly analogous",
        "the methods applied were insufficiently precise for this application",
        "the sample size was too small to sustain generalizations of this scope",
    ],
    "result": [
        "the anomaly persisted across independent replications",
        "no simple explanation could account for all observations",
        "the predicted relationship proved nonlinear",
        "the effect disappeared when confounds were controlled",
        "both mechanisms appeared to operate simultaneously",
    ],
    "method": [
        "isotopic analysis", "morphometric comparison", "network analysis",
        "stratigraphic sequencing", "computational modeling", "spectroscopic examination",
        "systematic surface survey", "targeted subsurface investigation",
    ],
    "position_a": ["unified mechanism", "gradualist", "discontinuity", "materialist", "functionalist", "structuralist"],
    "anomaly": [
        "a persistent class of exceptions",
        "the transitional examples",
        "a geographically restricted variant",
        "the earliest documented instances",
        "certain large-scale assemblages",
        "the anomalous late occurrences",
    ],
    "site_id": [f"GR-{n:04d}" for n in range(100, 9999, 137)],
    "duration": ["three field seasons", "nearly a decade", "an intensive two-year program", "several years", "four consecutive seasons"],
    "artifact_count": ["over two hundred", "forty-seven", "more than a thousand", "several hundred", "sixty-three"],
    "period": ["late archaic", "transitional", "early classical", "middle", "terminal"],
    "fraction": ["approximately a third", "more than half", "a small minority", "the majority", "roughly a quarter"],
    "comparison_site": [
        "analogous deposits in the region",
        "a well-documented reference collection",
        "sites of comparable date and character",
        "the nearest well-studied parallel assemblage",
    ],
    "item_a": ["the common form", "type A specimens", "the early examples", "the larger variants"],
    "item_b": ["the rare variant", "type B specimens", "the later examples", "the smaller variants"],
    "person_a": ["the senior investigator", "the project director", "the lead analyst", "the primary author"],
    "person_b": ["a junior colleague", "an external reviewer", "a skeptical correspondent", "the committee chair"],
    "variable_a": ["ambient conditions", "population density", "material composition", "elapsed time", "spatial proximity"],
    "variable_b": ["observed frequency", "structural integrity", "adoption rate", "error incidence", "documented occurrence"],
    "coefficient": ["0.74", "0.83", "0.61", "0.91", "0.55", "0.68"],
    "trial_count": ["seven", "twelve", "over twenty", "four independent sets of", "nine consecutive"],
    "confound": ["seasonal variation", "observer bias", "sampling irregularities", "instrument drift", "definitional inconsistencies"],
    "theorist": ["the framework's original proponent", "a leading authority in the subfield", "a prominent cross-disciplinary contributor"],
    "year": [str(y) for y in range(800, 1950, 13)],
    "qualifier": ["inconclusive", "suggestive at best", "premature", "circumstantial", "preliminary"],
    "count": ["forty-three", "over sixty", "twenty-seven", "more than a hundred", "thirty-eight"],
}

_MAPPING_SENTENCES: list[str] = [
    "Scholars of the notation system have confirmed that the symbol {glyph} corresponds to the unit {unit} in the standard transliteration table.",
    "According to the recovered codex, {glyph} is the conventional representation for {unit}.",
    "The cipher committee established that {glyph} encodes the character {unit}, a convention that persisted throughout the archival period.",
    "Cross-referencing three independent manuscripts confirms: the mark {glyph} should be read as {unit}.",
    "In the relevant notational system, the glyph {glyph} is unambiguously assigned to the unit {unit}.",
    "The transcription key, partially reconstructed from marginal annotations, lists {glyph} as the symbol for {unit}.",
    "Examination of consistent usage patterns across the corpus establishes that {glyph} decodes to {unit} in all documented contexts.",
    "The senior archivist's notes state clearly that {glyph} represents the character {unit} in the standard cipher.",
]

_DECOY_SENTENCES: list[str] = [
    "Some manuscripts employ the glyph {glyph} in a decorative capacity, though its precise meaning in that context remains disputed.",
    "The symbol {glyph} appears frequently in documents from the {era} period, though scholars disagree about its specific function.",
    "Several annotators have proposed that {glyph} may be related to the broader family of notation marks, but no definitive assignment has been established.",
    "The mark {glyph} is sometimes confused with similar symbols, particularly in poorly preserved documents where ink degradation obscures fine details.",
    "References to the symbol {glyph} appear in the secondary literature, though these discussions remain largely conjectural and uncorroborated.",
]

_PLAINTEXT_TEMPLATES: list[str] = [
    "The expedition recovered {item} from the {location} site after {duration} of careful excavation and all specimens were catalogued by the research team. The materials were subsequently transferred to the {institution} for further analysis and long-term preservation.",
    "Research conducted at the {location} facility demonstrated that {finding} under carefully controlled laboratory conditions. The results were subsequently verified by an independent team working at a separate {institution} confirming the reliability of the original findings.",
    "The archive holds {count} documents relating to the {subject} controversy that emerged during the {era} period of institutional reorganization. Scholars have yet to reach definitive consensus on the interpretation of the most critical materials in the collection.",
    "Investigators traced the origin of the recovered {artifact} to a workshop in the {location} district which was active during the {era} period of widespread production. The identification relied on distinctive stylistic features combined with isotopic analysis of the raw materials.",
    "The review committee examined all available evidence and concluded that the proposed {subject} interpretation could not be sustained on the basis of the current data alone. Further systematic fieldwork was strongly recommended before any definitive scholarly position could responsibly be adopted.",
]

_PLAINTEXT_FILLERS: dict[str, list[str]] = {
    "item": [
        "a collection of inscribed tablets",
        "several intact ceramic vessels",
        "a set of metal instruments",
        "an extensive documentary record",
        "a series of carefully carved markers",
    ],
    "location": ["northern highland", "coastal lowland", "central valley", "eastern frontier", "western plateau"],
    "duration": ["three field seasons", "nearly a decade", "an intensive two-year campaign", "several preliminary surveys"],
    "institution": ["regional museum", "national archive", "university collection", "research institute", "conservation laboratory"],
    "finding": [
        "reaction rates varied systematically with ambient conditions",
        "the predicted correlation held across all sampled groups",
        "variance was lower than baseline models had assumed",
        "the reported anomaly reproduced reliably under controlled conditions",
        "no significant difference was detected between the two study populations",
    ],
    "count": ["over three hundred", "forty-seven", "more than a thousand", "sixty-two", "several hundred"],
    "subject": ["attribution", "dating", "provenance", "functional interpretation", "classification"],
    "era": ["early classical", "late archaic", "transitional", "middle period", "terminal phase"],
    "artifact": ["inscribed panel", "composite tool", "decorated vessel", "carved figurine", "sealed container"],
}


def _fill(rng: random.Random, template: str, fillers: dict[str, list[str]]) -> str:
    result = template
    for key, options in fillers.items():
        ph = "{" + key + "}"
        while ph in result:
            result = result.replace(ph, rng.choice(options), 1)
    return result


def _generate_prose(rng: random.Random, target_chars: int) -> str:
    parts: list[str] = []
    total = 0
    while total < target_chars:
        tmpl = rng.choice(_PARA_TEMPLATES)
        para = _fill(rng, tmpl, _FILLERS)
        parts.append(para)
        total += len(para) + 2  # +2 for \n\n separator
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Codebook & encoding
# ---------------------------------------------------------------------------

def _build_codebook(num_glyphs: int, rng: random.Random) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Returns (codebook: glyph->unit, encoder: unit->list[glyph])."""
    if num_glyphs <= 26:
        units = list(_SINGLE_LETTERS)
        rng.shuffle(units)
        units = units[:num_glyphs]
    else:
        extra = num_glyphs - 26
        units = list(_SINGLE_LETTERS) + list(_DIGRAPHS[:extra])

    glyphs = list(GLYPH_POOL)
    rng.shuffle(glyphs)
    selected = glyphs[:num_glyphs]

    codebook: dict[str, str] = {selected[i]: units[i] for i in range(num_glyphs)}
    encoder: dict[str, list[str]] = {}
    for g, u in codebook.items():
        encoder.setdefault(u, []).append(g)
    return codebook, encoder


def _encode_text(text: str, encoder: dict[str, list[str]], rng: random.Random) -> str:
    """Encode plaintext — try digraphs first, then single letters; leave others as-is."""
    text = text.upper()
    result: list[str] = []
    i = 0
    while i < len(text):
        if i + 1 < len(text):
            pair = text[i] + text[i + 1]
            if pair in encoder:
                result.append(rng.choice(encoder[pair]))
                i += 2
                continue
        ch = text[i]
        if ch in encoder:
            result.append(rng.choice(encoder[ch]))
        else:
            result.append(ch)
        i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Fragment metadata & lazy text generation
# ---------------------------------------------------------------------------

@dataclass
class _FragmentMeta:
    id: str
    sub_seed: int
    # page index (0-based, within this fragment) -> (glyph, unit)
    page_mappings: dict[int, tuple[str, str]] = field(default_factory=dict)
    # page index (0-based, within this fragment) -> decoy glyph
    page_decoys: dict[int, str] = field(default_factory=dict)


def _load_page_mappings(f: dict[str, Any]) -> dict[int, tuple[str, str]]:
    # New format: {"page_mappings": {"0": [glyph, unit], ...}}
    if "page_mappings" in f:
        return {int(p): tuple(m) for p, m in f["page_mappings"].items()}
    # Legacy format: {"mappings": [[glyph, unit], ...]} — pin each to a distinct page.
    legacy = [tuple(m) for m in f.get("mappings", [])]
    return {i: m for i, m in enumerate(legacy) if i < PAGES_PER_FRAGMENT}


def _load_page_decoys(f: dict[str, Any]) -> dict[int, str]:
    if "page_decoys" in f:
        return {int(p): g for p, g in f["page_decoys"].items()}
    # Legacy format: {"decoy_glyphs": [glyph, ...]} — place on pages after any mappings.
    legacy = list(f.get("decoy_glyphs", []))
    start = min(len(f.get("mappings", [])), PAGES_PER_FRAGMENT)
    return {start + i: g for i, g in enumerate(legacy) if start + i < PAGES_PER_FRAGMENT}


def _fragment_page(meta: _FragmentMeta, page_idx: int) -> str:
    """Generate one page of a fragment deterministically from (sub_seed, page_idx)."""
    rng = random.Random(f"{meta.sub_seed}:{page_idx}")
    prose = _generate_prose(rng, CHARS_PER_PAGE)
    paras = prose.split("\n\n")

    mapping = meta.page_mappings.get(page_idx)
    if mapping is not None:
        glyph, unit = mapping
        sentence = rng.choice(_MAPPING_SENTENCES).format(glyph=glyph, unit=unit)
        idx = rng.randint(0, len(paras) - 1)
        paras[idx] += " " + sentence

    decoy = meta.page_decoys.get(page_idx)
    if decoy is not None:
        sentence = rng.choice(_DECOY_SENTENCES).format(glyph=decoy, era=rng.choice(_FILLERS["era"]))
        idx = rng.randint(0, len(paras) - 1)
        paras[idx] += " " + sentence

    return "\n\n".join(paras)


def _build_fragments(
    rng: random.Random,
    num_fragments: int,
    num_decoys: int,
    codebook: dict[str, str],
) -> list[_FragmentMeta]:
    pairs = list(codebook.items())
    rng.shuffle(pairs)
    num_glyphs = len(pairs)

    total_pages = num_fragments * PAGES_PER_FRAGMENT
    if num_glyphs + num_decoys > total_pages:
        raise ValueError(
            f"num_fragments*PAGES_PER_FRAGMENT ({total_pages}) must be >= "
            f"num_glyphs ({num_glyphs}) + num_decoys ({num_decoys}) so each mapping "
            f"and decoy can occupy a distinct page."
        )
    if num_decoys > num_glyphs:
        raise ValueError(
            f"num_decoys ({num_decoys}) cannot exceed num_glyphs ({num_glyphs}); "
            f"each decoy glyph must be distinct."
        )

    # Spread mappings evenly across all pages (global page index: 0 .. total_pages-1).
    mapping_stride = total_pages / num_glyphs
    mapping_pages = [int(i * mapping_stride) for i in range(num_glyphs)]

    # Spread decoys evenly across the pages not used by mappings.
    used = set(mapping_pages)
    remaining_pages = [p for p in range(total_pages) if p not in used]
    decoy_pages: list[int] = []
    if num_decoys > 0:
        decoy_stride = len(remaining_pages) / num_decoys
        decoy_pages = [remaining_pages[int(i * decoy_stride)] for i in range(num_decoys)]

    # Each decoy glyph appears at most once across the archive.
    decoy_glyph_pool = list(codebook.keys())
    rng.shuffle(decoy_glyph_pool)

    page_mappings_by_frag: dict[int, dict[int, tuple[str, str]]] = {
        i: {} for i in range(num_fragments)
    }
    for i, global_page in enumerate(mapping_pages):
        frag_idx, page_in_frag = divmod(global_page, PAGES_PER_FRAGMENT)
        page_mappings_by_frag[frag_idx][page_in_frag] = pairs[i]

    page_decoys_by_frag: dict[int, dict[int, str]] = {i: {} for i in range(num_fragments)}
    for i, global_page in enumerate(decoy_pages):
        frag_idx, page_in_frag = divmod(global_page, PAGES_PER_FRAGMENT)
        page_decoys_by_frag[frag_idx][page_in_frag] = decoy_glyph_pool[i]

    fragments: list[_FragmentMeta] = []
    for frag_idx in range(num_fragments):
        meta = _FragmentMeta(
            id=f"frag-{frag_idx:05d}",
            sub_seed=rng.randint(0, 2**31 - 1),
            page_mappings=page_mappings_by_frag[frag_idx],
            page_decoys=page_decoys_by_frag[frag_idx],
        )
        fragments.append(meta)

    return fragments


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ca in a:
        curr = [prev[0] + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def _score_submission(
    submitted_mapping: dict[str, str],
    submitted_plaintext: str,
    codebook: dict[str, str],
    plaintext: str,
) -> dict[str, Any]:
    total_mappings = len(codebook)
    correct = sum(1 for g, u in codebook.items() if submitted_mapping.get(g) == u)
    mapping_score = round(70.0 * correct / total_mappings, 1) if total_mappings else 0.0

    a = submitted_plaintext.upper().strip()
    b = plaintext.upper().strip()
    dist = _levenshtein(a, b)
    max_len = max(len(a), len(b), 1)
    similarity = max(0.0, 1.0 - dist / max_len)
    plaintext_score = round(30.0 * similarity, 1)

    return {
        "mapping_correct": correct,
        "mapping_total": total_mappings,
        "mapping_score": mapping_score,
        "plaintext_score": plaintext_score,
        "total": round(mapping_score + plaintext_score, 1),
        "max": 100,
    }


# ---------------------------------------------------------------------------
# Generation entry point
# ---------------------------------------------------------------------------

@dataclass
class _CipherState:
    codebook: dict[str, str]
    plaintext: str
    ciphertext: str
    fragments: list[_FragmentMeta]
    difficulty: str
    seed: int | None


def _generate(seed: int | None, difficulty: str) -> _CipherState:
    rng = random.Random(seed)
    cfg = DIFFICULTY_CONFIGS.get(difficulty, DIFFICULTY_CONFIGS["medium"])
    num_glyphs: int = cfg["num_glyphs"]
    num_fragments: int = cfg["num_fragments"]
    num_decoys: int = cfg["num_decoys"]

    codebook, encoder = _build_codebook(num_glyphs, rng)
    plaintext = _fill(rng, rng.choice(_PLAINTEXT_TEMPLATES), _PLAINTEXT_FILLERS)
    ciphertext = _encode_text(plaintext, encoder, rng)
    fragments = _build_fragments(rng, num_fragments, num_decoys, codebook)

    logger.info(
        "[cipher_decoder] Generated — difficulty=%s glyphs=%d fragments=%d decoys=%d",
        difficulty, num_glyphs, num_fragments, num_decoys,
    )
    return _CipherState(
        codebook=codebook,
        plaintext=plaintext,
        ciphertext=ciphertext,
        fragments=fragments,
        difficulty=difficulty,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Challenge class
# ---------------------------------------------------------------------------

class CipherDecoderChallenge(BaseChallenge):
    slug = "cipher_decoder"
    name = "Cipher Decoder"
    description = (
        "Reconstruct a glyph-to-character codebook by reading a large archive of fragments, "
        "then decode the ciphered message."
    )
    version = "1.0"
    tags = ["context_management", "compaction", "search", "reasoning"]
    difficulty = "medium"

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionDescriptor]:
        return [
            ActionDescriptor(
                type="cipher_decoder.list_fragments",
                description="List all fragment IDs in the archive.",
                base_cost=0.5,
                params={},
                response_schema={"fragment_ids": "array<string>"},
            ),
            ActionDescriptor(
                type="cipher_decoder.read_fragment",
                description=(
                    "Read one page of a fragment's text. Each fragment is approximately 10,000 tokens "
                    "split into 10 pages of ~1,000 tokens each. page is 1-indexed."
                ),
                base_cost=2.0,
                params={
                    "fragment_id": {"type": "string", "required": True},
                    "page": {"type": "int", "required": False, "default": 1, "description": "1-indexed page number"},
                },
                response_schema={
                    "fragment_id": "string",
                    "page": "int",
                    "total_pages": "int",
                    "text": "string",
                },
            ),
            ActionDescriptor(
                type="cipher_decoder.submit_decoding",
                description=(
                    "Submit the recovered codebook and decoded plaintext. "
                    "Scored: glyph_mapping correctness 70 pts (proportional), "
                    "plaintext similarity 30 pts (edit-distance scaled). "
                    "Challenge ends after submission."
                ),
                base_cost=3.0,
                params={
                    "glyph_mapping": {
                        "type": "object",
                        "required": True,
                        "description": "Dict mapping each glyph symbol to its decoded character or digraph",
                    },
                    "plaintext": {
                        "type": "string",
                        "required": True,
                        "description": "Your decoded version of the ciphered message",
                    },
                },
                response_schema={
                    "score": "object",
                    "total_points": "float",
                    "max_points": "float",
                    "completed": "bool",
                },
            ),
        ]

    @classmethod
    def events(cls) -> list[EventDescriptor]:
        return [
            EventDescriptor(
                type="cipher_decoder.completed",
                description="Decoding submission received.",
                payload_schema={
                    "message": "string",
                    "score": "object",
                    "actions_taken": "int",
                    "total_cost": "float",
                },
            ),
        ]

    @classmethod
    def cost_config(cls) -> CostConfig:
        return CostConfig(
            invalid_action_multiplier=2.0,
            time_rate_per_second=0.02,
            length_rate_per_message=0.15,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self, options: dict[str, Any]) -> None:
        super().__init__(options)
        self._seed: int | None = options.get("seed", None)
        self._difficulty: str = options.get("difficulty", "medium")
        self._action_count = 0
        self._total_cost = 0.0
        self.completed = False
        self._submission: dict[str, Any] | None = None
        self._score_result: dict[str, Any] | None = None

        state = _generate(self._seed, self._difficulty)
        self._codebook = state.codebook
        self._plaintext = state.plaintext
        self._ciphertext = state.ciphertext
        self._fragments = state.fragments
        self._fragment_index: dict[str, _FragmentMeta] = {f.id: f for f in self._fragments}

    # ------------------------------------------------------------------
    # State / objective
    # ------------------------------------------------------------------

    def initial_state(self) -> dict[str, Any]:
        return {
            "difficulty": self._difficulty,
            "num_fragments": len(self._fragments),
            "num_glyphs_to_find": len(self._codebook),
            "ciphered_message": self._ciphertext,
            "note": (
                "The ciphered message encodes characters as Unicode glyphs. "
                "Each glyph maps to a single letter (A-Z) or a common two-letter digraph (e.g. TH, ER). "
                "Characters without a glyph assignment appear as-is. "
                "Read archive fragments to discover the glyph-to-character mappings, then submit your decoding."
            ),
        }

    def objective(self) -> dict[str, Any]:
        return {
            "objective": (
                "Reconstruct the complete glyph codebook by reading archive fragments, "
                "then decode the ciphered message and submit your findings."
            ),
            "hints": [
                "Call list_fragments to get all fragment IDs.",
                f"There are {len(self._codebook)} glyph-to-character mappings to find.",
                "Each fragment spans 10 pages (~1,000 tokens per page) — a mapping can appear on any page.",
                "Mappings appear naturally in prose, e.g. 'the symbol X corresponds to the unit Y'.",
                "Some fragments are decoys that mention glyphs without assigning them — read carefully.",
                "Non-encoded characters (spaces, punctuation, unmapped letters) appear as-is in the ciphertext.",
            ],
            "success_condition": "submit_decoding with the correct glyph_mapping and decoded plaintext",
            "failure_condition": None,
            "scoring": {
                "glyph_mapping": "70 pts — proportional to fraction of correct glyph→character mappings",
                "plaintext": "30 pts — scaled by edit-distance similarity to the true plaintext",
            },
        }

    def end_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "actions_taken": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "difficulty": self._difficulty,
            "num_fragments": len(self._fragments),
            "num_glyphs": len(self._codebook),
        }
        if self._score_result:
            summary["score"] = self._score_result
        return summary

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "codebook": self._codebook,
            "plaintext": self._plaintext,
            "ciphertext": self._ciphertext,
            "fragments": [
                {
                    "id": f.id,
                    "sub_seed": f.sub_seed,
                    "page_mappings": {str(p): list(m) for p, m in f.page_mappings.items()},
                    "page_decoys": {str(p): g for p, g in f.page_decoys.items()},
                }
                for f in self._fragments
            ],
            "difficulty": self._difficulty,
            "seed": self._seed,
            "action_count": self._action_count,
            "total_cost": self._total_cost,
            "completed": self.completed,
            "submission": self._submission,
            "score_result": self._score_result,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], options: dict[str, Any]) -> "CipherDecoderChallenge":
        instance = cls.__new__(cls)
        super(CipherDecoderChallenge, instance).__init__(options)
        instance.options = data.get("options", options)
        instance._codebook = data["codebook"]
        instance._plaintext = data["plaintext"]
        instance._ciphertext = data["ciphertext"]
        instance._fragments = [
            _FragmentMeta(
                id=f["id"],
                sub_seed=f["sub_seed"],
                page_mappings=_load_page_mappings(f),
                page_decoys=_load_page_decoys(f),
            )
            for f in data["fragments"]
        ]
        instance._fragment_index = {f.id: f for f in instance._fragments}
        instance._difficulty = data["difficulty"]
        instance._seed = data["seed"]
        instance._action_count = data["action_count"]
        instance._total_cost = data["total_cost"]
        instance.completed = data["completed"]
        instance._submission = data.get("submission")
        instance._score_result = data.get("score_result")
        logger.info(
            "[cipher_decoder] Session resumed — difficulty=%s fragments=%d actions=%d",
            instance._difficulty, len(instance._fragments), instance._action_count,
        )
        return instance

    # ------------------------------------------------------------------
    # Available actions
    # ------------------------------------------------------------------

    def available_actions(self) -> list[dict[str, Any]]:
        fragment_ids = [f.id for f in self._fragments]
        return [
            {
                "type": "cipher_decoder.list_fragments",
                "base_cost": 0.5,
                "params": {},
                "available": True,
            },
            {
                "type": "cipher_decoder.read_fragment",
                "base_cost": 2.0,
                "params": {
                    "fragment_id": {"type": "string", "enum": fragment_ids},
                    "page": {"type": "int", "default": 1, "min": 1},
                },
                "available": True,
                "note": "Each fragment has 10 pages of ~1,000 tokens each.",
            },
            {
                "type": "cipher_decoder.submit_decoding",
                "base_cost": 3.0,
                "params": {
                    "glyph_mapping": {"type": "object"},
                    "plaintext": {"type": "string"},
                },
                "available": not self.completed,
                "note": "Challenge ends after submission." if not self.completed else "Already submitted.",
            },
        ]

    # ------------------------------------------------------------------
    # Action dispatch
    # ------------------------------------------------------------------

    async def handle(self, verb: str, payload: dict[str, Any]) -> ActionResult:
        if verb == "list_fragments":
            return self._handle_list_fragments()
        if verb == "read_fragment":
            return self._handle_read_fragment(payload)
        if verb == "submit_decoding":
            return self._handle_submit_decoding(payload)
        raise KeyError(verb)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _handle_list_fragments(self) -> ActionResult:
        self._action_count += 1
        cost = 0.5
        self._total_cost += cost
        ids = [f.id for f in self._fragments]
        logger.info("[cipher_decoder] list_fragments — %d fragments", len(ids))
        return ActionResult(payload={"fragment_ids": ids}, base_cost=cost)

    def _handle_read_fragment(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 2.0
        self._total_cost += cost

        frag_id = payload.get("fragment_id", "")
        if frag_id not in self._fragment_index:
            return ActionResult(
                payload={
                    "error": {
                        "code": "UNKNOWN_FRAGMENT",
                        "message": f"Fragment {frag_id!r} not found. Use list_fragments to see available IDs.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="unknown_fragment",
            )

        meta = self._fragment_index[frag_id]
        total_pages = PAGES_PER_FRAGMENT

        page = max(1, int(payload.get("page", 1)))
        if page > total_pages:
            return ActionResult(
                payload={
                    "error": {
                        "code": "PAGE_OUT_OF_RANGE",
                        "message": f"Page {page} out of range for {frag_id!r} (1–{total_pages}).",
                        "detail": {"total_pages": total_pages},
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="page_out_of_range",
            )

        text = _fragment_page(meta, page - 1)

        logger.info("[cipher_decoder] read_fragment %s page=%d/%d", frag_id, page, total_pages)
        return ActionResult(
            payload={
                "fragment_id": frag_id,
                "page": page,
                "total_pages": total_pages,
                "text": text,
            },
            base_cost=cost,
        )

    def _handle_submit_decoding(self, payload: dict[str, Any]) -> ActionResult:
        self._action_count += 1
        cost = 3.0
        self._total_cost += cost

        if self.completed:
            return ActionResult(
                payload={
                    "error": {
                        "code": "ALREADY_SUBMITTED",
                        "message": "A decoding has already been submitted. The challenge is over.",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="already_submitted",
            )

        missing = [f for f in ("glyph_mapping", "plaintext") if not payload.get(f)]
        if missing:
            return ActionResult(
                payload={
                    "error": {
                        "code": "MISSING_FIELDS",
                        "message": f"Missing required fields: {missing}",
                    }
                },
                base_cost=cost,
                invalid=True,
                invalid_reason="missing_fields",
            )

        self._submission = payload
        self._score_result = _score_submission(
            payload.get("glyph_mapping", {}),
            payload.get("plaintext", ""),
            self._codebook,
            self._plaintext,
        )
        self.completed = True

        logger.info(
            "[cipher_decoder] Submitted — score=%.1f/%d actions=%d cost=%.1f",
            self._score_result["total"], self._score_result["max"],
            self._action_count, self._total_cost,
        )

        self._push(
            "cipher_decoder.completed",
            {
                "message": "Decoding submission received.",
                "score": self._score_result,
                "actions_taken": self._action_count,
                "total_cost": self._total_cost,
            },
        )

        return ActionResult(
            payload={
                "score": self._score_result,
                "total_points": self._score_result["total"],
                "max_points": self._score_result["max"],
                "completed": True,
            },
            base_cost=cost,
            completed=True,
        )
