from functools import wraps

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template,
    request, session, url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import repository
from models import CAMPUSES, now_iso
from services import mailer

auth_bp = Blueprint("auth", __name__)

# Registration allowlist for edu_email ONLY (personal_email accepts anything).
# g.ucla.edu is UCLA's student mail domain; ucla.edu kept for grad/other
# affiliations. Confirm remaining campuses with real accounts before pilot.
ALLOWED_EMAIL_DOMAINS = (
    "ucsc.edu", "ucla.edu", "g.ucla.edu", "ucsd.edu", "berkeley.edu",
    "ucdavis.edu", "uci.edu", "ucsb.edu", "ucr.edu", "ucmerced.edu",
)

VERIFY_TOKEN_MAX_AGE = 24 * 60 * 60  # 24h

# The edu address proves UC affiliation, once. It is never a login
# credential and no password is ever collected for it: clicking a link only
# that inbox could receive is the entire proof of ownership. Login is
# personal_email + the account password set at registration.


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        student = None
        student_id = session.get("student_id")
        if student_id:
            student = repository.get_student_by_id(student_id)
        if not student or not student.is_fully_active:
            # Drop only the stale login key — clearing the whole session here
            # would destroy an in-progress onboarding session.
            session.pop("student_id", None)
            return redirect(url_for("auth.login"))
        g.student = student
        return view(*args, **kwargs)
    return wrapped


def _serializer(salt):
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def _send_edu_verification(student):
    token = _serializer("edu-verify").dumps(student.id)
    verify_url = url_for("auth.verify_edu", token=token, _external=True)
    mailer.send_verification_email(student.edu_email, verify_url)


def _send_personal_verification(student):
    token = _serializer("personal-verify").dumps(
        {"sid": student.id, "email": student.personal_email}
    )
    verify_url = url_for("auth.verify_personal", token=token, _external=True)
    mailer.send_verification_email(student.personal_email, verify_url)


def _load_token(salt, token):
    try:
        return _serializer(salt).loads(token, max_age=VERIFY_TOKEN_MAX_AGE), None
    except SignatureExpired:
        return None, "That verification link has expired. Request a new one."
    except BadSignature:
        return None, "Invalid verification link."


# --- Step 1: register with campus email (verification-only) + password ---

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", campuses=CAMPUSES)

    name = (request.form.get("name") or "").strip()
    edu_email = (request.form.get("edu_email") or "").strip().lower()
    password = request.form.get("password") or ""
    campus = request.form.get("campus") or ""
    year = (request.form.get("year") or "").strip()
    consent = request.form.get("ferpa_consent")

    def fail(message):
        flash(message, "error")
        return render_template("register.html", campuses=CAMPUSES), 400

    if not all([name, edu_email, password, campus, year]):
        return fail("All fields are required.")
    if "@" not in edu_email:
        return fail("Enter a valid email address.")
    domain = edu_email.rsplit("@", 1)[1]
    if domain not in ALLOWED_EMAIL_DOMAINS:
        return fail(
            "Registration requires a UC campus email address "
            f"({', '.join(ALLOWED_EMAIL_DOMAINS)}). '{domain}' is not a UC campus domain."
        )
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    if campus not in CAMPUSES:
        return fail("Select a valid UC campus.")
    if not consent:
        return fail(
            "Campus Crosswalk cannot create your account without your consent to share "
            "your course enrollments for peer matching (FERPA)."
        )
    if repository.get_student_by_edu_email(edu_email):
        return fail("An account with this campus email already exists. "
                    "Use 'Resume setup' on the login page if yours is unfinished.")

    student = repository.create_student(
        name=name, edu_email=edu_email, password=password, campus=campus,
        year=year, consent_given_at=now_iso(),
    )
    _send_edu_verification(student)
    return render_template(
        "verify_pending.html", email=student.edu_email,
        blurb="This confirms you're a UC student. After clicking it you'll "
              "add the personal email you'll actually log in with.",
    )


@auth_bp.route("/verify/edu/<token>")
def verify_edu(token):
    student_id, error = _load_token("edu-verify", token)
    if error:
        flash(error, "error")
        return redirect(url_for("auth.login"))
    student = repository.mark_edu_verified(student_id)
    if not student:
        flash("Invalid verification link.", "error")
        return redirect(url_for("auth.login"))

    if student.is_fully_active:
        flash("Your account is already active — log in with your personal email.", "success")
        return redirect(url_for("auth.login"))

    # Limited onboarding session: allowed to finish setup, not logged in.
    session.clear()
    session["onboarding_student_id"] = student.id
    flash("Campus email verified — one more step.", "success")
    return redirect(url_for("auth.personal_email_step"))


# --- Step 2: mandatory personal email, own verification ---

@auth_bp.route("/onboarding/personal-email", methods=["GET", "POST"])
def personal_email_step():
    student = None
    if session.get("onboarding_student_id"):
        student = repository.get_student_by_id(session["onboarding_student_id"])
    if not student or not student.edu_verified:
        flash("Use 'Resume setup' on the login page to continue where you left off.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("personal_email.html", student=student)

    personal_email = (request.form.get("personal_email") or "").strip().lower()

    def fail(message):
        flash(message, "error")
        return render_template("personal_email.html", student=student), 400

    if "@" not in personal_email:
        return fail("Enter a valid email address.")
    if personal_email == student.edu_email:
        return fail("Your personal email must be different from your campus email — "
                    "it's what you'll use to log in after you graduate or transfer.")
    existing_personal = repository.get_student_by_personal_email(personal_email)
    if existing_personal and existing_personal.id != student.id:
        return fail("That email is already in use on another account.")
    existing_edu = repository.get_student_by_edu_email(personal_email)
    if existing_edu and existing_edu.id != student.id:
        return fail("That email is already in use on another account.")

    student = repository.set_personal_email(student.id, personal_email)
    _send_personal_verification(student)
    return render_template(
        "verify_pending.html", email=student.personal_email,
        blurb="Click it to activate your account, then log in with this "
              "personal email and your password.",
    )


@auth_bp.route("/verify/personal/<token>")
def verify_personal(token):
    payload, error = _load_token("personal-verify", token)
    if error:
        flash(error, "error")
        return redirect(url_for("auth.login"))

    student = repository.get_student_by_id((payload or {}).get("sid"))
    # Token is bound to the address it was sent to; a later address change
    # invalidates old links.
    if not student or student.personal_email != (payload or {}).get("email"):
        flash("Invalid verification link.", "error")
        return redirect(url_for("auth.login"))

    repository.mark_personal_verified(student.id)
    session.pop("onboarding_student_id", None)
    flash("Account active — log in with your personal email.", "success")
    return redirect(url_for("auth.login"))


# --- Resume / resend paths (no dead ends, no enumeration) ---

@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    """Resend the edu link for accounts that never verified Step 1."""
    email = (request.form.get("email") or "").strip().lower()
    student = repository.get_student_by_edu_email(email) if email else None
    if student and not student.edu_verified:
        _send_edu_verification(student)
    flash("If that address has an unverified account, a new link was sent.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resume-setup", methods=["POST"])
def resume_setup():
    """Password-authenticated re-entry into whichever step is unfinished."""
    edu_email = (request.form.get("edu_email") or "").strip().lower()
    password = request.form.get("password") or ""
    student = repository.get_student_by_edu_email(edu_email)

    if not student or not student.check_password(password):
        flash("Invalid campus email or password.", "error")
        return render_template("login.html"), 401

    if student.is_fully_active:
        flash("Your account is already active — log in with your personal email.", "success")
        return redirect(url_for("auth.login"))

    if not student.edu_verified:
        _send_edu_verification(student)
        flash("We re-sent the verification link to your campus email.", "success")
        return redirect(url_for("auth.login"))

    if student.personal_email and not student.personal_verified:
        _send_personal_verification(student)

    session.clear()
    session["onboarding_student_id"] = student.id
    return redirect(url_for("auth.personal_email_step"))


# --- Step 3 onward: login is personal_email + password ---

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    student = repository.get_student_by_personal_email(email)

    if not student or not student.check_password(password):
        flash("Invalid email or password. (Log in with your personal email, "
              "not your campus address.)", "error")
        return render_template("login.html"), 401
    if not student.is_fully_active:
        flash("Your account setup isn't finished — use 'Resume setup' below.", "error")
        return render_template("login.html"), 403

    session.clear()
    session["student_id"] = student.id
    return redirect(url_for("students.dashboard"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


# Spec §6.3: the legacy impersonation path must never authenticate.
@auth_bp.route("/login_as")
@auth_bp.route("/login_as/<path:rest>")
def login_as(rest=None):
    return redirect(url_for("auth.login"))


@auth_bp.route("/account/delete", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "GET":
        return render_template("delete_confirm.html", student=g.student)

    if not request.form.get("confirm_delete"):
        flash("Check the confirmation box to delete your account.", "error")
        return render_template("delete_confirm.html", student=g.student), 400

    repository.delete_student_and_data(g.student.id)
    session.clear()
    return render_template("goodbye.html")
