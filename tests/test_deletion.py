"""Deletion behavior per Makai's decision (2026-07-03): the student's own
data is fully deleted; their authored help requests survive anonymized so
other students' responses aren't destroyed with them."""
import repository as repo
from models import Enrollment, HelpRequest, HelpResponse, InteractionLog


def _make_two_students_with_activity():
    alice = repo.create_student(
        "Alice", "alice@ucsc.edu", "pw-alice", "UCSC", "Junior",
        consent_given_at="2026-07-03T00:00:00+00:00",
    )
    bob = repo.create_student(
        "Bob", "bob@ucla.edu", "pw-bob", "UCLA", "Senior",
        consent_given_at="2026-07-03T00:00:00+00:00",
    )
    c1 = repo.create_course("UCSC", "CSE 101", "Data Structures")
    c2 = repo.create_course("UCLA", "CS 32", "Data Structures")
    repo.create_enrollment(alice.id, c1.id, "Fall 2026")
    repo.create_enrollment(bob.id, c2.id, "Fall 2026")

    alices_request = repo.create_help_request(alice.id, c1.id, "AVL rotations", "How do I balance?")
    bobs_request = repo.create_help_request(bob.id, c2.id, "Pointers", "Segfault help")
    # Bob answers Alice's request; Alice answers Bob's.
    bobs_response_on_alices = repo.create_help_response(alices_request.id, bob.id, "Rotate twice.")
    alices_response_on_bobs = repo.create_help_response(bobs_request.id, alice.id, "Check null.")
    repo.create_interaction_log(alice.id, "equivalency_lookup", b"cipher")

    return alice, bob, alices_request, bobs_request, bobs_response_on_alices, alices_response_on_bobs


def test_deletion_anonymizes_requests_and_deletes_own_data(app):
    with app.app_context():
        alice, bob, alices_request, bobs_request, bobs_resp, alices_resp = (
            _make_two_students_with_activity()
        )
        alice_id, request_id = alice.id, alices_request.id
        bob_id, bobs_request_id = bob.id, bobs_request.id
        bobs_resp_id, alices_resp_id = bobs_resp.id, alices_resp.id

        assert repo.delete_student_and_data(alice_id) is True

        # Student row and wholly-owned data are gone.
        assert repo.get_student_by_id(alice_id) is None
        assert Enrollment.query.filter_by(student_id=alice_id).count() == 0
        assert InteractionLog.query.filter_by(student_id=alice_id).count() == 0
        # Alice's response on Bob's request is genuinely deleted.
        assert HelpResponse.query.filter_by(id=alices_resp_id).count() == 0

        # Her authored request survives, anonymized — no re-linkable identifier.
        surviving = HelpRequest.query.get(request_id)
        assert surviving is not None
        assert surviving.student_id is None
        # Bob's genuine response on it is intact.
        assert HelpResponse.query.filter_by(id=bobs_resp_id).count() == 1

        # Bob himself is untouched.
        assert repo.get_student_by_id(bob_id) is not None
        assert HelpRequest.query.get(bobs_request_id).student_id == bob_id


def test_deletion_returns_false_for_unknown_student(app):
    with app.app_context():
        assert repo.delete_student_and_data("no-such-uuid") is False
