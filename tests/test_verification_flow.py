"""Two-email identity flow (Makai, 2026-07-03): edu_email is verification-only
proof of UC affiliation; personal_email + password is the login; account is
fully active only when both are independently verified."""
import re

from itsdangerous import URLSafeTimedSerializer

import repository as repo


def _csrf(client, path):
    html = client.get(path).data.decode()
    return re.search('name="csrf_token" value="([^"]+)"', html).group(1)


def _register(client, edu_email="maya@ucsc.edu", **overrides):
    data = dict(
        name="Maya", edu_email=edu_email, password="longenough",
        campus="UCSC", year="Junior", ferpa_consent="yes",
    )
    data.update(overrides)
    data["csrf_token"] = _csrf(client, "/register")
    return client.post("/register", data=data)


def _token(app, salt, payload):
    return URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=salt).dumps(payload)


def test_allowlist_applies_to_edu_email_only(app, client):
    # gmail rejected as edu address...
    r = _register(client, edu_email="maya@gmail.com")
    assert r.status_code == 400 and b"not a UC campus domain" in r.data
    # ...g.ucla.edu (UCLA student domain) accepted
    r = _register(client, edu_email="diego@g.ucla.edu", campus="UCLA")
    assert r.status_code == 200 and b"Check your inbox" in r.data


def test_full_two_email_flow(app, client):
    assert _register(client).status_code == 200
    with app.app_context():
        student = repo.get_student_by_edu_email("maya@ucsc.edu")
        assert student.edu_verified is False and not student.is_fully_active
        sid = student.id

    # Cannot log in at any point with the edu address.
    tok = _csrf(client, "/login")
    r = client.post("/login", data=dict(csrf_token=tok, email="maya@ucsc.edu", password="longenough"))
    assert r.status_code == 401

    # Step 1: edu magic link -> onboarding step 2, still not logged in.
    r = client.get(f"/verify/edu/{_token(app, 'edu-verify', sid)}", follow_redirects=False)
    assert "/onboarding/personal-email" in r.headers["Location"]
    assert client.get("/dashboard").status_code == 302  # not authenticated

    # Step 2: personal email must differ from edu, then accepts any domain.
    tok = _csrf(client, "/onboarding/personal-email")
    r = client.post("/onboarding/personal-email",
                    data=dict(csrf_token=tok, personal_email="maya@ucsc.edu"))
    assert r.status_code == 400
    tok = _csrf(client, "/onboarding/personal-email")
    r = client.post("/onboarding/personal-email",
                    data=dict(csrf_token=tok, personal_email="maya.codes@gmail.com"))
    assert r.status_code == 200 and b"Check your inbox" in r.data

    # Login still blocked: personal not yet verified.
    tok = _csrf(client, "/login")
    r = client.post("/login", data=dict(csrf_token=tok, email="maya.codes@gmail.com", password="longenough"))
    assert r.status_code == 403

    # Personal magic link is bound to the exact address.
    bad = _token(app, "personal-verify", {"sid": sid, "email": "attacker@evil.com"})
    client.get(f"/verify/personal/{bad}")
    with app.app_context():
        assert not repo.get_student_by_id(sid).personal_verified

    good = _token(app, "personal-verify", {"sid": sid, "email": "maya.codes@gmail.com"})
    client.get(f"/verify/personal/{good}")
    with app.app_context():
        student = repo.get_student_by_id(sid)
        assert student.personal_verified and student.is_fully_active

    # Step 3: login with personal email + password.
    tok = _csrf(client, "/login")
    r = client.post("/login", data=dict(csrf_token=tok, email="maya.codes@gmail.com", password="longenough"))
    assert r.status_code == 302 and "/dashboard" in r.headers["Location"]
    assert b"Hey Maya" in client.get("/dashboard").data

    # The edu address never logs in, even fully active.
    c2 = app.test_client()
    tok = _csrf(c2, "/login")
    r = c2.post("/login", data=dict(csrf_token=tok, email="maya@ucsc.edu", password="longenough"))
    assert r.status_code == 401


def test_resume_setup_reenters_unfinished_flow(app, client):
    _register(client, edu_email="sam@berkeley.edu", campus="Berkeley", name="Sam")
    with app.app_context():
        sid = repo.get_student_by_edu_email("sam@berkeley.edu").id
    client.get(f"/verify/edu/{_token(app, 'edu-verify', sid)}")

    # Fresh client (lost session mid-onboarding) resumes with edu email + password.
    c2 = app.test_client()
    tok = _csrf(c2, "/login")
    r = c2.post("/resume-setup", data=dict(csrf_token=tok, edu_email="sam@berkeley.edu", password="longenough"))
    assert r.status_code == 302 and "/onboarding/personal-email" in r.headers["Location"]
    # Wrong password does not.
    c3 = app.test_client()
    tok = _csrf(c3, "/login")
    r = c3.post("/resume-setup", data=dict(csrf_token=tok, edu_email="sam@berkeley.edu", password="wrongwrong"))
    assert r.status_code == 401
