from flask import Blueprint, flash, g, redirect, render_template, request, url_for

import repository
from routes.auth import login_required
from services import equivalency as eq_engine

courses_bp = Blueprint("courses", __name__)

DEFAULT_TERM = "Fall 2026"


@courses_bp.route("/courses")
@login_required
def my_courses():
    enrollments = repository.get_enrollments_for_student(g.student.id)
    catalog = repository.get_all_courses_by_campus()
    return render_template(
        "my_courses.html", enrollments=enrollments, catalog=catalog,
        default_term=DEFAULT_TERM,
    )


@courses_bp.route("/courses/add", methods=["POST"])
@login_required
def add_course():
    course_id = request.form.get("course_id")
    term = (request.form.get("term") or DEFAULT_TERM).strip()
    course = repository.get_course_by_id(course_id) if course_id else None

    if not course:
        flash("Select a valid course.", "error")
        return redirect(url_for("courses.my_courses"))

    repository.create_enrollment(g.student.id, course.id, term)
    flash(f"Added {course.campus} {course.course_code}.", "success")
    return redirect(url_for("courses.my_courses"))


@courses_bp.route("/courses/<enrollment_id>/remove", methods=["POST"])
@login_required
def remove_course(enrollment_id):
    if repository.delete_enrollment(g.student.id, enrollment_id):
        flash("Course removed.", "success")
    else:
        flash("Couldn't remove that course.", "error")
    return redirect(url_for("courses.my_courses"))


@courses_bp.route("/equivalencies/<equivalency_id>/confirm", methods=["POST"])
@login_required
def confirm_equivalency(equivalency_id):
    if eq_engine.confirm_equivalency(equivalency_id) is None:
        flash("That equivalency no longer exists.", "error")
    else:
        flash("Thanks — confirmed.", "success")
    return redirect(request.referrer or url_for("students.peers"))


@courses_bp.route("/equivalencies/<equivalency_id>/deny", methods=["POST"])
@login_required
def deny_equivalency(equivalency_id):
    if eq_engine.deny_equivalency(equivalency_id) is None:
        flash("That equivalency no longer exists.", "error")
    else:
        flash("Thanks — noted as not equivalent.", "success")
    return redirect(request.referrer or url_for("students.peers"))
