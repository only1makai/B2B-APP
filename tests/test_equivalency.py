"""Equivalency engine tests (spec §7.2 cache-first flow, §7.4 confidence math).

Nudge magnitude (+/-0.05) and confidence floor (0.01) were ambiguous in the
spec and resolved with the project owner 2026-07-03 rather than guessed.
"""
import pytest

import repository as repo
from services import equivalency as eq_engine


def _two_courses():
    a = repo.create_course("UCSC", "CSE 101", "Data Structures")
    b = repo.create_course("UCLA", "CS 32", "Data Structures II")
    return a, b


def test_known_pair_returns_cached_confidence(app):
    with app.app_context():
        a, b = _two_courses()
        repo.create_equivalency(a.id, b.id, 0.87, "gemini_flash")

        result = eq_engine.check_equivalency(a.id, b.id)
        assert result["status"] == "known"
        assert result["confidence"] == 0.87
        assert result["method"] == "gemini_flash"
        assert result["confirmations"] == 0 and result["denials"] == 0
        assert result["surfaceable"] is True

        # Order independence — canonical pairing (spec §5).
        reverse = eq_engine.check_equivalency(b.id, a.id)
        assert reverse["equivalency_id"] == result["equivalency_id"]


def test_unknown_pair_returns_pending_status(app):
    with app.app_context():
        a = repo.create_course("UCSD", "CSE 100", "Advanced Data Structures")
        b = repo.create_course("Berkeley", "CS 170", "Algorithms")
        assert eq_engine.check_equivalency(a.id, b.id) == {"status": "unknown"}


def test_gemini_fallback_seam_is_stubbed_not_wired(app):
    with app.app_context():
        a, b = _two_courses()
        with pytest.raises(NotImplementedError):
            eq_engine.resolve_unknown_pair(a.id, b.id)


def test_confirm_increments_and_nudges_confidence_up(app):
    with app.app_context():
        a, b = _two_courses()
        created = repo.create_equivalency(a.id, b.id, 0.80, "gemini_flash")

        updated = eq_engine.confirm_equivalency(created.id)
        assert updated.confirmations == 1
        assert updated.confidence == pytest.approx(0.85)

        updated = eq_engine.confirm_equivalency(created.id)
        assert updated.confirmations == 2
        assert updated.confidence == pytest.approx(0.90)


def test_confirm_caps_at_point_99(app):
    with app.app_context():
        a, b = _two_courses()
        created = repo.create_equivalency(a.id, b.id, 0.97, "gemini_flash")

        eq_engine.confirm_equivalency(created.id)  # would be 1.02 uncapped
        updated = eq_engine.confirm_equivalency(created.id)
        assert updated.confidence == pytest.approx(0.99)


def test_deny_increments_and_nudges_confidence_down(app):
    with app.app_context():
        a, b = _two_courses()
        created = repo.create_equivalency(a.id, b.id, 0.80, "gemini_flash")

        updated = eq_engine.deny_equivalency(created.id)
        assert updated.denials == 1
        assert updated.confidence == pytest.approx(0.75)


def test_deny_floors_at_point_01(app):
    with app.app_context():
        a, b = _two_courses()
        created = repo.create_equivalency(a.id, b.id, 0.03, "gemini_flash")

        eq_engine.deny_equivalency(created.id)  # would be -0.02 uncapped
        updated = eq_engine.deny_equivalency(created.id)
        assert updated.confidence == pytest.approx(0.01)


def test_surfaceable_stops_when_denials_exceed_confirmations_and_confidence_low(app):
    with app.app_context():
        a, b = _two_courses()
        created = repo.create_equivalency(a.id, b.id, 0.55, "gemini_flash")

        eq_engine.deny_equivalency(created.id)  # denials=1, confidence=0.50
        eq_engine.deny_equivalency(created.id)  # denials=2, confidence=0.45

        result = eq_engine.check_equivalency(a.id, b.id)
        assert result["denials"] == 2 and result["confirmations"] == 0
        assert result["confidence"] < 0.5
        assert result["surfaceable"] is False

        # Stops surfacing but stays in the table as data (spec §7.4).
        assert repo.get_equivalency_by_id(created.id) is not None


def test_confirmations_outweighing_denials_keeps_it_surfaceable_even_if_low(app):
    with app.app_context():
        a, b = _two_courses()
        # Low confidence but confirmations >= denials -> still surfaceable
        # per the spec's exact condition (denials > confirmations AND < 0.5).
        created = repo.create_equivalency(a.id, b.id, 0.40, "gemini_flash")
        eq_engine.confirm_equivalency(created.id)  # confirmations=1, denials=0

        result = eq_engine.check_equivalency(a.id, b.id)
        assert result["confidence"] < 0.5
        assert result["confirmations"] >= result["denials"]
        assert result["surfaceable"] is True
