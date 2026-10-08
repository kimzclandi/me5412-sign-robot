"""Finite-catalog selectors, not arbitrary English-to-ASL translation.

Embedding uses a real local SentenceTransformer when explicitly installed.
The shared guards are conservative heuristics, not a semantic safety proof.
The selected action's ASL review and playback policy are handled downstream.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
import time
import unicodedata

from .contracts import ROOT, load_catalog

_METHODS = {"exact", "embedding", "llm"}


def normalize(text: str) -> str:
    """Normalize case/spacing and terminal punctuation; preserve internal syntax."""
    text = unicodedata.normalize("NFKC", text).replace("’", "'").casefold()
    return " ".join(text.split()).strip(" .!?，。！")


def _guard(text: str) -> tuple[str, str] | None:
    """Reject obvious scope changes; deliberately incomplete natural-language rules."""
    if not text:
        return "clarify", "empty_input"
    if len(text) > 240:
        return "unsupported", "input_too_long"
    if any(c.isalpha() and not ("a" <= c <= "z") for c in text):
        return "unsupported", "english_only"
    if re.search(r"\b(no|not|never|neither|nothing|without|cannot|stop|cancel|refuse)\b|\b\w+n't\b", text):
        return "unsupported", "negated_or_declining"
    if re.search(r"\b(dose|dosage|medicine|medication|pill\w*|tablet\w*|insulin|diagnos\w*|consent|surgery|allerg\w*|pain|emergency|prescri\w*)\b", text):
        return "unsupported", "clinical_content_out_of_scope"
    if re.search(r'["“”]|\b(say|said|says|told|tell|asked|ask|translate|translation|means|meaning|quote|quoted|who|what|why|how)\b', text):
        return "unsupported", "reported_or_metalinguistic"
    intents = [
        bool(re.search(r"\b(hello|hi|greetings|greeting|hey)\b", text)),
        bool(re.search(r"\b(thanks|thank|grateful|appreciate|gratitude)\b", text)),
        bool(re.search(r"\b(wait|waiting|hold|pause)\b", text)),
    ]
    if sum(intents) > 1 or re.search(r"\b(and|then|also|but|instead)\b|[;\n.!?]", text):
        return "clarify", "multiple_or_compound_intents"
    if re.search(r"\b(if|unless|although|whether)\b", text):
        return "unsupported", "conditional_input"
    if intents[2]:
        if re.search(r"\b(i|we|he|she|they|my|our|his|her|their)\b", text):
            return "unsupported", "waiting_role_mismatch"
        if re.search(r"\d|\b(one|two|three|four|five|ten|hour\w*|minute\w*|second\w*|until|for|outside|inside|here|there|room|desk|when|while)\b", text):
            return "unsupported", "qualified_wait_out_of_scope"
    if intents[1] and re.search(r"\b(him|her|them|mother|father|doctor|nurse)\b", text):
        return "unsupported", "gratitude_recipient_out_of_scope"
    return None


def _exact(text: str, catalog: list[dict]) -> tuple[str, str | None, str]:
    matches = [a["action_id"] for a in catalog if text in {normalize(s) for s in a["aliases"]}]
    if len(matches) == 1:
        return "execute", matches[0], "exact_alias"
    if matches:
        return "clarify", None, "ambiguous_catalog_alias"
    return "unsupported", None, "no_exact_alias"


@lru_cache(maxsize=1)
def _load_encoder(model_path: str):
    # No remote resolution at inference, remote code, token lookup, or downloads.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_path, device="cpu", local_files_only=True,
                               trust_remote_code=False, token=False)


@lru_cache(maxsize=4)
def _embedding_index(model_path: str, documents: tuple[str, ...]):
    encoder = _load_encoder(model_path)
    return encoder.encode(list(documents), normalize_embeddings=True, convert_to_numpy=True,
                          show_progress_bar=False)


def _embedding(text: str, catalog: list[dict]) -> tuple[str, str | None, str]:
    import numpy as np

    try:
        config = json.loads((ROOT / "config/embedding.json").read_text())
        path = (ROOT / config["model_path"]).resolve()
        if not (path / "model.safetensors").is_file():
            return "error", None, "embedding_unavailable"
        if not catalog:
            return "error", None, "empty_catalog"
        # A sentence is compared with descriptions and accepted paraphrases.
        # Taking the best phrase within each action avoids treating two aliases
        # for the same action as competing classes when computing the margin.
        documents, owners = [], []
        for action in catalog:
            for document in [action["meaning_en"], *action["aliases"]]:
                documents.append(document)
                owners.append(action["action_id"])
        matrix = _embedding_index(str(path), tuple(documents))  # [N, 384]
        query = _load_encoder(str(path)).encode([text], normalize_embeddings=True,
                                               convert_to_numpy=True,
                                               show_progress_bar=False)  # [1, 384]
        scores = np.asarray(matrix @ query[0], dtype=float)  # cosine scores [N]
        if scores.shape != (len(documents),) or not np.isfinite(scores).all():
            return "error", None, "embedding_invalid_scores"
        action_scores = {a["action_id"]: -float("inf") for a in catalog}
        for owner, score in zip(owners, scores):
            action_scores[owner] = max(action_scores[owner], float(score))
        ranked = sorted(action_scores.items(), key=lambda item: (-item[1], item[0]))
        if ranked[0][1] < float(config["min_similarity"]):
            return "unsupported", None, "embedding_below_threshold"
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < float(config["min_margin"]):
            return "clarify", None, "embedding_ambiguous"
        return "execute", ranked[0][0], "embedding_match"
    except (ImportError, OSError):
        return "error", None, "embedding_unavailable"
    except Exception:
        # Model/config/runtime problems must never execute an unverified fallback.
        return "error", None, "embedding_runtime_error"


def select_action(text, method: str = "exact", catalog: list[dict] | None = None) -> dict:
    """Return a legal action ID or a non-executing status, always with timing.

    latency_ms includes the shared guard and any cold model loading for this call.
    No method silently uses another method when its backend is unavailable.
    """
    started = time.perf_counter()

    def result(status, action_id, reason):
        return {"status": status, "action_id": action_id, "reason_code": reason,
                "method": method, "latency_ms": round((time.perf_counter() - started) * 1000, 3)}

    if not isinstance(method, str) or method not in _METHODS:
        return result("error", None, "unknown_method")
    if not isinstance(text, str):
        return result("error", None, "invalid_input_type")
    if "\n" in text.strip():
        return result("clarify", None, "multiple_or_compound_intents")
    normalized = normalize(text)
    guard = _guard(normalized)
    if guard:
        return result(guard[0], None, guard[1])
    try:
        actions = load_catalog() if catalog is None else catalog
        if not isinstance(actions, list) or not actions:
            return result("error", None, "empty_catalog")
        ids = [a["action_id"] for a in actions]
        if len(ids) != len(set(ids)):
            return result("error", None, "invalid_catalog")
        for action in actions:
            if not isinstance(action["action_id"], str) or not isinstance(action["meaning_en"], str):
                return result("error", None, "invalid_catalog")
            if not isinstance(action["aliases"], list) or not all(isinstance(s, str) for s in action["aliases"]):
                return result("error", None, "invalid_catalog")
        if method == "exact":
            return result(*_exact(normalized, actions))
        if method == "embedding":
            return result(*_embedding(normalized, actions))
        from .llm import choose_local
        metadata = {}
        decision = result(*choose_local(text, actions, metadata=metadata))
        if metadata:
            decision["metadata"] = metadata
        return decision
    except (OSError, ValueError, KeyError, TypeError):
        return result("error", None, "invalid_catalog")
