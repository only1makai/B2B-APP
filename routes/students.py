from flask import Blueprint, g, render_template

from routes.auth import login_required

students_bp = Blueprint("students", __name__)


@students_bp.route("/dashboard")
@login_required
def dashboard():
    # Phase 7 brings peer discovery here; for now: identity + account actions.
    return render_template("dashboard.html", student=g.student)
