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

# Registration allowlist (Makai, 2026-07-03). NOTE before pilot: UCLA issues
# student mail on g.ucla.edu — this list will reject real UCLA students until
# confirmed/extended with real campus test accounts.
ALLOWED_EMAIL_DOMAINS = (
    "ucsc.edu", "ucla.edu", "ucsd.edu", "berkeley.edu", "ucdavis.edu",
    "uci.edu", "ucsb.edu", "ucr.edu", "ucmerced.edu",
)

VERIFY_TOKEN_MAX_AGE = 24 * 60 * 60  # 24h (spec: link expires in 24 hours)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        student = None
        student_id = session.get("student_id")
        if student_id:
            student = repository.get_student_by_id(student_id)
        if not student:
            session.clear()
            return redirect(url_for("auth.login"))
        g.student = student
        return view(*args, **kwargs)
    return wrapped


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="email-verify")


def _send_verification(student):
    token = _serializer().dumps(student.id)
    verify_url = url_for("auth.verify_email", token=token, _external=True)
    mailer.send_verification_email(student.email, verify_url)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", campuses=CAMPUSES)

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    campus = request.form.get("campus") or ""
    year = (request.form.get("year") or "").strip()
    consent = request.form.get("ferpa_consent")

    def fail(message):
        flash(message, "error")
        return render_template("register.html", campuses=CAMPUSES), 400

    if not all([name, email, password, campus, year]):
        return fail("All fields are required.")
    if "@" not in email:
        return fail("Enter a valid email address.")
    domain = email.rsplit("@", 1)[1]
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
            "B2B cannot create your account without your consent to share "
            "your course enrollments for peer matching (FERPA)."
        )
    if repository.get_student_by_email(email):
        return fail("An account with this email already exists. Try logging in.")

    student = repository.create_student(
        name=name, email=email, password=password, campus=campus, year=year,
        consent_given_at=now_iso(),
    )
    _send_verification(student)
    return render_template("verify_pending.html", email=student.email)


@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        student_id = _serializer().loads(token, max_age=VERIFY_TOKEN_MAX_AGE)
    except SignatureExpired:
        flash("That verification link has expired. Request a new one below.", "error")
        return redirect(url_for("auth.login"))
    except BadSignature:
        flash("Invalid verification link.", "error")
        return redirect(url_for("auth.login"))

    student = repository.mark_email_verified(student_id)
    if not student:
        flash("Invalid verification link.", "error")
        return redirect(url_for("auth.login"))
    flash("Email verified — you can log in now.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    email = (request.form.get("email") or "").strip().lower()
    student = repository.get_student_by_email(email) if email else None
    if student and not student.email_verified:
        _send_verification(student)
    # Same message regardless — no account enumeration.
    flash("If that address has an unverified account, a new link was sent.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    student = repository.get_student_by_email(email)

    if not student or not student.check_password(password):
        flash("Invalid email or password.", "error")
        return render_template("login.html"), 401
    if not student.email_verified:
        flash("Verify your campus email before logging in — check your inbox "
              "or request a new link below.", "error")
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
