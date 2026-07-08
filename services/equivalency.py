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

# STOP-CONDITION RESOLVED (Phase 7, 2026-07-08): peer card contents were
# escalated as a real privacy decision rather than assumed. Answer: full
# `name`, and social handles only as the contact path (no email fallback,
# no anonymized handle) — matches spec §8 literally.


def find_peer_matches(student_id):
    """Cross-campus peer discovery (spec §8), built entirely on the Phase 5
    equivalency engine — no Gemini involvement.

    For each of the student's enrollments, finds other students at a
    DIFFERENT campus enrolled in an equivalent course, where the
    equivalency clears both gates: confidence >= SURFACE_MIN_CONFIDENCE
    and is_surfaceable() (the denials-outweigh-confirmations cutoff from
    §7.4). Excludes: the student themself, hidden-visibility peers, and
    peers whose account isn't fully verified (edu + personal) yet — an
    account that can't log in shouldn't be discoverable either.

    Returns a list grouped by the student's own course:
      [{"my_course": Course, "matches": [
          {"peer": Student, "matched_course": Course,
           "confidence": float, "equivalency_id": str}, ...
      ]}, ...]
    Groups with zero matches are omitted.
    """
    my_enrollments = repository.get_enrollments_for_student(student_id)

    grouped = []
    for enrollment in my_enrollments:
        my_course = enrollment.course
        equivalencies = repository.get_equivalencies_for_course(
            my_course.id, min_confidence=SURFACE_MIN_CONFIDENCE
        )

        matches = []
        for eq in equivalencies:
            if not is_surfaceable(eq):
                continue

            other_course_id = (
                eq.course_b_id if eq.course_a_id == my_course.id else eq.course_a_id
            )
            other_course = repository.get_course_by_id(other_course_id)
            if not other_course or other_course.campus == my_course.campus:
                # Peer discovery is explicitly cross-campus (spec §8);
                # same-campus equivalency rows (if any ever exist) don't
                # produce peer matches here.
                continue

            for other_enrollment in repository.get_enrollments_for_course(other_course.id):
                peer = other_enrollment.student
                if peer.id == student_id:
                    continue
                if peer.course_visibility == "hidden":
                    continue
                if not peer.is_fully_active:
                    continue
                matches.append({
                    "peer": peer,
                    "matched_course": other_course,
                    "confidence": eq.confidence,
                    "equivalency_id": eq.id,
                })

        if matches:
            grouped.append({"my_course": my_course, "matches": matches})

    return grouped
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
