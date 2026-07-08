"""Equivalency engine: cache-first lookup, confidence math, confirmations
(spec §7.2 cache-first flow, §7.4 confidence/confirmation math).

Nudge magnitude and confidence floor are not specified numerically in the
spec ("nudge confidence up/down, cap 0.99") — resolved with the project
owner 2026-07-03: fixed +/-0.05 per confirm/deny event, clamped to
[CONFIDENCE_FLOOR, CONFIDENCE_CAP].

Gemini fallback (spec §7.1, §7.3) is out of scope this phase — see the seam
at the bottom of this file.
"""
import repository

SURFACE_MIN_CONFIDENCE = 0.5  # spec §8 peer-discovery surfacing threshold
CONFIDENCE_STEP = 0.05
CONFIDENCE_FLOOR = 0.01
CONFIDENCE_CAP = 0.99


def check_equivalency(course_a_id, course_b_id):
    """Cache-first lookup (spec §7.2). Any equivalency lookup checks the
    equivalencies table first; only a genuine miss may go on to trigger a
    Gemini call (Phase 6 — see resolve_unknown_pair below).

    Returns either:
      {"status": "known", "equivalency_id", "course_a_id", "course_b_id",
       "confidence", "method", "confirmations", "denials", "surfaceable"}
    or:
      {"status": "unknown"}
    """
    eq = repository.get_equivalency(course_a_id, course_b_id)
    if eq is None:
        return {"status": "unknown"}
    return _serialize(eq)


def _serialize(eq):
    return {
        "status": "known",
        "equivalency_id": eq.id,
        "course_a_id": eq.course_a_id,
        "course_b_id": eq.course_b_id,
        "confidence": eq.confidence,
        "method": eq.method,
        "confirmations": eq.confirmations,
        "denials": eq.denials,
        "surfaceable": is_surfaceable(eq),
    }


def is_surfaceable(eq):
    """Spec §7.4: a pair with denials > confirmations AND confidence < 0.5
    stops surfacing in peer discovery but stays in the table as data."""
    if eq.denials > eq.confirmations and eq.confidence < SURFACE_MIN_CONFIDENCE:
        return False
    return True


def confirm_equivalency(equivalency_id):
    """A student confirms a surfaced equivalency (spec §7.4)."""
    eq = repository.get_equivalency_by_id(equivalency_id)
    if eq is None:
        return None
    new_confidence = min(CONFIDENCE_CAP, eq.confidence + CONFIDENCE_STEP)
    return repository.update_equivalency(
        equivalency_id,
        confidence=new_confidence,
        confirmations=eq.confirmations + 1,
    )


def deny_equivalency(equivalency_id):
    """A student denies a surfaced equivalency (spec §7.4)."""
    eq = repository.get_equivalency_by_id(equivalency_id)
    if eq is None:
        return None
    new_confidence = max(CONFIDENCE_FLOOR, eq.confidence - CONFIDENCE_STEP)
    return repository.update_equivalency(
        equivalency_id,
        confidence=new_confidence,
        denials=eq.denials + 1,
    )


# --- Phase 6 seam ------------------------------------------------------
# check_equivalency() already returns {"status": "unknown"} for an unmapped
# pair without making any external call. Phase 6 wires the Gemini Flash
# lookup in here: call the model, then repository.create_equivalency(
# course_a_id, course_b_id, confidence, method="gemini_flash") to persist
# the result, so the next check_equivalency() call for the same pair hits
# cache with zero API calls (spec §7.2).
def resolve_unknown_pair(course_a_id, course_b_id):
    raise NotImplementedError(
        "Gemini fallback is Phase 6 (spec §7.1/§7.3) — not wired yet. "
        "check_equivalency() already handles the cache-miss case."
    )
