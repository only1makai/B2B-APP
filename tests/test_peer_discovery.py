"""Peer discovery (spec §8), built on the Phase 5 equivalency engine.

Privacy decision (escalated to and resolved by the project owner,
2026-07-08): peer cards show full name and social handles only — no email,
no anonymized handle. See services/equivalency.find_peer_matches().
"""
import re

import pytest

import repository as repo
from services import equivalency as eq_engine


def _student(name, edu_email, personal_email, campus, **extra):
    s = repo.create_student(
        name=name, edu_email=edu_email, password="testpass123", campus=campus,
        year="Junior", consent_given_at="2026-07-08T00:00:00+00:00", **extra,
    )
    repo.mark_edu_verified(s.id)
    repo.set_personal_email(s.id, personal_email)
    repo.mark_personal_verified(s.id)
    return s


def _csrf(client, path):
    html = client.get(path).data.decode()
    return re.search('name="csrf_token" value="([^"]+)"', html).group(1)


def _login(client, email, password="testpass123"):
    tok = _csrf(client, "/login")
    return client.post("/login", data=dict(csrf_token=tok, email=email, password=password))


def test_student_sees_peer_on_equivalent_course_at_another_campus(app):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        bob = _student("Bob", "bob@g.ucla.edu", "bob.p@gmail.com", "UCLA")
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        repo.create_enrollment(alice.id, c1.id, "Fall 2026")
        repo.create_enrollment(bob.id, c2.id, "Fall 2026")
        repo.create_equivalency(c1.id, c2.id, 0.87, "gemini_flash")

        groups = eq_engine.find_peer_matches(alice.id)
        assert len(groups) == 1
        assert groups[0]["my_course"].id == c1.id
        assert len(groups[0]["matches"]) == 1
        match = groups[0]["matches"][0]
        assert match["peer"].id == bob.id
        assert match["matched_course"].id == c2.id
        assert match["confidence"] == 0.87


def test_non_surfaceable_equivalency_produces_no_match(app):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        bob = _student("Bob", "bob@g.ucla.edu", "bob.p@gmail.com", "UCLA")
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        repo.create_enrollment(alice.id, c1.id, "Fall 2026")
        repo.create_enrollment(bob.id, c2.id, "Fall 2026")
        eq = repo.create_equivalency(c1.id, c2.id, 0.55, "gemini_flash")

        # Deny it into non-surfaceable territory: denials > confirmations
        # and confidence drops below 0.5 (spec §7.4).
        eq_engine.deny_equivalency(eq.id)  # denials=1, confidence=0.50
        eq_engine.deny_equivalency(eq.id)  # denials=2, confidence=0.45

        assert eq_engine.find_peer_matches(alice.id) == []


def test_hidden_visibility_peer_never_appears(app):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        priya = _student("Priya", "priya@ucsc.edu", "priya.p@gmail.com", "UCSC")
        bob = _student("Bob", "bob@g.ucla.edu", "bob.p@gmail.com", "UCLA")
        repo.set_course_visibility(priya.id, "hidden")

        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        c3 = repo.create_course("Berkeley", "CS 61B", "Data Structures III")
        repo.create_enrollment(alice.id, c1.id, "Fall 2026")
        repo.create_enrollment(bob.id, c2.id, "Fall 2026")
        repo.create_enrollment(priya.id, c3.id, "Fall 2026")
        repo.create_equivalency(c1.id, c2.id, 0.87, "gemini_flash")
        repo.create_equivalency(c1.id, c3.id, 0.90, "gemini_flash")

        groups = eq_engine.find_peer_matches(alice.id)
        all_peer_ids = {m["peer"].id for g in groups for m in g["matches"]}
        assert bob.id in all_peer_ids
        assert priya.id not in all_peer_ids


def test_student_never_appears_in_own_peer_results(app):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        # Alice enrolled in the equivalent course too (e.g. double-enrolled,
        # transfer credit) -- must never match herself.
        repo.create_enrollment(alice.id, c1.id, "Fall 2026")
        repo.create_enrollment(alice.id, c2.id, "Fall 2026")
        repo.create_equivalency(c1.id, c2.id, 0.87, "gemini_flash")

        groups = eq_engine.find_peer_matches(alice.id)
        all_peer_ids = {m["peer"].id for g in groups for m in g["matches"]}
        assert alice.id not in all_peer_ids


def test_confirm_and_deny_routes_require_auth(client, app):
    with app.app_context():
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        eq = repo.create_equivalency(c1.id, c2.id, 0.80, "gemini_flash")
        eq_id = eq.id

    # Valid CSRF token but no session -- isolates the auth gate from CSRF.
    tok = _csrf(client, "/login")
    r = client.post(f"/equivalencies/{eq_id}/confirm", data=dict(csrf_token=tok))
    assert r.status_code == 302 and "/login" in r.headers["Location"]

    tok = _csrf(client, "/login")
    r = client.post(f"/equivalencies/{eq_id}/deny", data=dict(csrf_token=tok))
    assert r.status_code == 302 and "/login" in r.headers["Location"]

    with app.app_context():
        unchanged = repo.get_equivalency_by_id(eq_id)
        assert unchanged.confidence == 0.80
        assert unchanged.confirmations == 0 and unchanged.denials == 0


def test_confirm_and_deny_routes_adjust_confidence_when_authenticated(app, client):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        eq = repo.create_equivalency(c1.id, c2.id, 0.80, "gemini_flash")
        eq_id = eq.id

    _login(client, "alice.p@gmail.com")

    tok = _csrf(client, "/login")
    r = client.post(f"/equivalencies/{eq_id}/confirm", data=dict(csrf_token=tok))
    assert r.status_code == 302
    with app.app_context():
        updated = repo.get_equivalency_by_id(eq_id)
        assert updated.confirmations == 1
        assert updated.confidence == pytest.approx(0.85)

    tok = _csrf(client, "/login")
    r = client.post(f"/equivalencies/{eq_id}/deny", data=dict(csrf_token=tok))
    assert r.status_code == 302
    with app.app_context():
        updated = repo.get_equivalency_by_id(eq_id)
        assert updated.denials == 1
        assert updated.confidence == pytest.approx(0.80)


def test_peers_page_renders_full_name_and_social_handles(app, client):
    with app.app_context():
        alice = _student("Alice", "alice@ucsc.edu", "alice.p@gmail.com", "UCSC")
        bob = _student(
            "Bob Chen", "bob@g.ucla.edu", "bob.p@gmail.com", "UCLA",
            social_handles={"github": "bobchen"},
        )
        c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
        c2 = repo.create_course("UCLA", "CS 32", "Data Structures II")
        repo.create_enrollment(alice.id, c1.id, "Fall 2026")
        repo.create_enrollment(bob.id, c2.id, "Fall 2026")
        repo.create_equivalency(c1.id, c2.id, 0.87, "gemini_flash")

    _login(client, "alice.p@gmail.com")
    html = client.get("/peers").data.decode()
    assert "Bob Chen" in html
    assert "bobchen" in html
    assert "bob.p@gmail.com" not in html  # never leak email to a peer
