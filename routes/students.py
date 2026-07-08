from flask import Blueprint, g, render_template

from routes.auth import login_required
from services import equivalency as eq_engine

students_bp = Blueprint("students", __name__)


@students_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", student=g.student)


@students_bp.route("/peers")
@login_required
def peers():
    groups = eq_engine.find_peer_matches(g.student.id)
    return render_template("peers.html", groups=groups)
