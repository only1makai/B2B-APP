import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

# The 9 UC campuses — the only legal values for any campus column (spec §5).
CAMPUSES = (
    "Berkeley", "UCLA", "UCSD", "UCSC", "Davis",
    "Irvine", "UCSB", "Riverside", "Merced",
)

VISIBILITY_OPTIONS = ("peers", "hidden")


def new_uuid():
    return str(uuid.uuid4())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    campus = db.Column(db.String(20), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    interests = db.Column(db.JSON, nullable=False, default=list)
    social_handles = db.Column(db.JSON, nullable=False, default=dict)
    # FERPA: set at registration when the consent box is checked; registration
    # fails without it (spec §6.5).
    consent_given_at = db.Column(db.String(40), nullable=True)
    # FERPA user control: "hidden" students never appear in peer discovery.
    course_visibility = db.Column(db.String(10), nullable=False, default="peers")
    # Campus-email verification gate: unverified accounts cannot log in and
    # must never surface in peer discovery.
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.String(40), nullable=False, default=now_iso)

    @validates("campus")
    def validate_campus(self, key, value):
        if value not in CAMPUSES:
            raise ValueError(f"Invalid campus {value!r}; must be one of {CAMPUSES}")
        return value

    @validates("course_visibility")
    def validate_visibility(self, key, value):
        if value not in VISIBILITY_OPTIONS:
            raise ValueError(f"Invalid course_visibility {value!r}")
        return value

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    campus = db.Column(db.String(20), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(30), nullable=False, default="uc_directory")

    __table_args__ = (db.UniqueConstraint("campus", "course_code"),)

    @validates("campus")
    def validate_campus(self, key, value):
        if value not in CAMPUSES:
            raise ValueError(f"Invalid campus {value!r}; must be one of {CAMPUSES}")
        return value


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey("courses.id"), nullable=False)
    term = db.Column(db.String(30), nullable=False)

    student = db.relationship("Student", backref=db.backref("enrollments", lazy=True))
    course = db.relationship("Course")

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "term"),)


class Equivalency(db.Model):
    """Persistent equivalency database: mapped once, stays mapped.

    Pairs are stored canonically (lower UUID in course_a_id) so A<->B and
    B<->A never duplicate. repository.py enforces the ordering.
    """
    __tablename__ = "equivalencies"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    course_a_id = db.Column(db.String(36), db.ForeignKey("courses.id"), nullable=False)
    course_b_id = db.Column(db.String(36), db.ForeignKey("courses.id"), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=False)  # gemini_deep_research | gemini_flash | student_confirmed
    confirmations = db.Column(db.Integer, nullable=False, default=0)
    denials = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.String(40), nullable=False, default=now_iso)

    course_a = db.relationship("Course", foreign_keys=[course_a_id])
    course_b = db.relationship("Course", foreign_keys=[course_b_id])

    __table_args__ = (db.UniqueConstraint("course_a_id", "course_b_id"),)


class HelpRequest(db.Model):
    __tablename__ = "help_requests"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    # Nullable: account deletion anonymizes authorship (student_id -> NULL,
    # rendered as "Deleted User") so other students' responses survive.
    student_id = db.Column(db.String(36), db.ForeignKey("students.id"), nullable=True)
    course_id = db.Column(db.String(36), db.ForeignKey("courses.id"), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="open")  # open | resolved
    created_at = db.Column(db.String(40), nullable=False, default=now_iso)

    student = db.relationship("Student")
    course = db.relationship("Course")


class HelpResponse(db.Model):
    __tablename__ = "help_responses"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    request_id = db.Column(db.String(36), db.ForeignKey("help_requests.id"), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey("students.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.String(40), nullable=False, default=now_iso)

    request = db.relationship("HelpRequest", backref=db.backref("responses", lazy=True))
    student = db.relationship("Student")


class InteractionLog(db.Model):
    """Event metadata only (course ids, action names) — never email, never
    message bodies. Payload is Fernet-encrypted by services/crypto.py before
    it reaches this table (spec §5)."""
    __tablename__ = "interaction_log"

    id = db.Column(db.String(36), primary_key=True, default=new_uuid)
    student_id = db.Column(db.String(36), db.ForeignKey("students.id"), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    payload_encrypted = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.String(40), nullable=False, default=now_iso)
