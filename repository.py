"""Data access layer — every query in the app routes through here (spec §4).

Keeping SQL/ORM access in one module is what makes the promised Firestore
migration a single-file swap.
"""
from models import (
    Course,
    Enrollment,
    Equivalency,
    HelpRequest,
    HelpResponse,
    InteractionLog,
    Student,
    db,
)


# --- Students ---

def create_student(name, edu_email, password, campus, year,
                   interests=None, social_handles=None, consent_given_at=None):
    student = Student(
        name=name,
        edu_email=edu_email.strip().lower(),
        campus=campus,
        year=year,
        interests=interests or [],
        social_handles=social_handles or {},
        consent_given_at=consent_given_at,
    )
    student.set_password(password)
    db.session.add(student)
    db.session.commit()
    return student


def get_student_by_id(student_id):
    return db.session.get(Student, student_id)


def get_student_by_edu_email(email):
    return Student.query.filter_by(edu_email=email.strip().lower()).first()


def get_student_by_personal_email(email):
    return Student.query.filter_by(personal_email=email.strip().lower()).first()


def set_course_visibility(student_id, visibility):
    student = db.session.get(Student, student_id)
    if not student:
        return None
    student.course_visibility = visibility
    db.session.commit()
    return student


def delete_student_and_data(student_id):
    """CCPA deletion (spec §6.7, amended by Makai 2026-07-03): fully delete
    the student's own data — enrollments, interaction logs, and every
    response they authored anywhere — but ANONYMIZE their authored help
    requests (student_id -> NULL) so other students' responses on them
    survive. No identifier remains that can re-link the request to the
    deleted account."""
    student = db.session.get(Student, student_id)
    if not student:
        return False

    Enrollment.query.filter_by(student_id=student_id).delete()
    InteractionLog.query.filter_by(student_id=student_id).delete()
    HelpResponse.query.filter_by(student_id=student_id).delete()
    HelpRequest.query.filter_by(student_id=student_id).update({"student_id": None})

    db.session.delete(student)
    db.session.commit()
    return True


def mark_edu_verified(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        return None
    student.edu_verified = True
    db.session.commit()
    return student


def set_personal_email(student_id, email):
    """Setting (or changing) the personal address always re-arms verification."""
    student = db.session.get(Student, student_id)
    if not student:
        return None
    student.personal_email = email.strip().lower()
    student.personal_verified = False
    db.session.commit()
    return student


def mark_personal_verified(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        return None
    student.personal_verified = True
    db.session.commit()
    return student


# --- Courses ---

def create_course(campus, course_code, title, description=None, source="uc_directory"):
    course = Course(
        campus=campus,
        course_code=course_code,
        title=title,
        description=description,
        source=source,
    )
    db.session.add(course)
    db.session.commit()
    return course


def get_course_by_id(course_id):
    return db.session.get(Course, course_id)


def get_course_by_campus_and_code(campus, course_code):
    return Course.query.filter_by(campus=campus, course_code=course_code).first()


def get_courses_by_campus(campus):
    return Course.query.filter_by(campus=campus).order_by(Course.course_code).all()


# --- Enrollments ---

def create_enrollment(student_id, course_id, term):
    enrollment = Enrollment(student_id=student_id, course_id=course_id, term=term)
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


def get_enrollments_for_student(student_id):
    return Enrollment.query.filter_by(student_id=student_id).all()


def get_enrollments_for_course(course_id):
    return Enrollment.query.filter_by(course_id=course_id).all()


# --- Equivalencies ---

def canonical_pair(course_x_id, course_y_id):
    """Lower UUID first, so A<->B and B<->A land on the same row (spec §5)."""
    return tuple(sorted((course_x_id, course_y_id)))


def get_equivalency(course_x_id, course_y_id):
    a, b = canonical_pair(course_x_id, course_y_id)
    return Equivalency.query.filter_by(course_a_id=a, course_b_id=b).first()


def create_equivalency(course_x_id, course_y_id, confidence, method):
    a, b = canonical_pair(course_x_id, course_y_id)
    existing = Equivalency.query.filter_by(course_a_id=a, course_b_id=b).first()
    if existing:
        return existing
    eq = Equivalency(course_a_id=a, course_b_id=b, confidence=confidence, method=method)
    db.session.add(eq)
    db.session.commit()
    return eq


def get_equivalencies_for_course(course_id, min_confidence=None):
    q = Equivalency.query.filter(
        db.or_(
            Equivalency.course_a_id == course_id,
            Equivalency.course_b_id == course_id,
        )
    )
    if min_confidence is not None:
        q = q.filter(Equivalency.confidence >= min_confidence)
    return q.all()


def get_equivalency_by_id(equivalency_id):
    return db.session.get(Equivalency, equivalency_id)


def update_equivalency(equivalency_id, confidence=None, confirmations=None, denials=None):
    eq = db.session.get(Equivalency, equivalency_id)
    if not eq:
        return None
    if confidence is not None:
        eq.confidence = confidence
    if confirmations is not None:
        eq.confirmations = confirmations
    if denials is not None:
        eq.denials = denials
    db.session.commit()
    return eq


# --- Help board ---

def create_help_request(student_id, course_id, topic, body):
    req = HelpRequest(student_id=student_id, course_id=course_id, topic=topic, body=body)
    db.session.add(req)
    db.session.commit()
    return req


def get_help_request_by_id(request_id):
    return db.session.get(HelpRequest, request_id)


def get_help_requests(course_ids=None, status=None):
    q = HelpRequest.query
    if course_ids is not None:
        q = q.filter(HelpRequest.course_id.in_(course_ids))
    if status is not None:
        q = q.filter_by(status=status)
    return q.order_by(HelpRequest.created_at.desc()).all()


def set_help_request_status(request_id, status):
    req = db.session.get(HelpRequest, request_id)
    if not req:
        return None
    req.status = status
    db.session.commit()
    return req


def create_help_response(request_id, student_id, body):
    resp = HelpResponse(request_id=request_id, student_id=student_id, body=body)
    db.session.add(resp)
    db.session.commit()
    return resp


def get_responses_for_request(request_id):
    return (
        HelpResponse.query.filter_by(request_id=request_id)
        .order_by(HelpResponse.created_at.asc())
        .all()
    )


# --- Interaction log ---

def create_interaction_log(student_id, event_type, payload_encrypted):
    log = InteractionLog(
        student_id=student_id,
        event_type=event_type,
        payload_encrypted=payload_encrypted,
    )
    db.session.add(log)
    db.session.commit()
    return log


def get_logs_for_student(student_id):
    return InteractionLog.query.filter_by(student_id=student_id).all()
