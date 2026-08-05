from typing import Any
from __init__ import db

# ── Junction table (no ORM class needed, but define for relationship) ────────
course_students = db.Table(
    "course_students",
    db.Column("course_id",  db.Integer, db.ForeignKey("courses.id",  ondelete="CASCADE"), primary_key=True),
    db.Column("student_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(db.Model):
    """Unified user table — admin, teacher, and student share one row."""
    __tablename__ = "users"

    id              = db.Column(db.Integer, primary_key=True)
    type            = db.Column(db.Enum("admin", "teacher", "student", name="user_role"), nullable=False)
    student_id      = db.Column(db.Text, unique=True, nullable=True)       # e.g. "2022-3-60-110"
    email           = db.Column(db.Text, unique=True, nullable=False)
    phone           = db.Column(db.Text, nullable=True)
    username        = db.Column(db.Text, nullable=False)
    password        = db.Column(db.Text, nullable=False)                   # bcrypt hash
    face_embedding  = db.Column(db.Text, nullable=True)                    # JSON array of 128-dim dlib face embeddings (3 poses)
    guardian_number = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Relationships
    taught_courses    = db.relationship("Course", backref="teacher", lazy="dynamic")
    enrolled_courses  = db.relationship("Course", secondary=course_students,
                                        backref=db.backref("students", lazy="dynamic"),
                                        lazy="dynamic")
    attendance_records = db.relationship("Attendance", backref="student", lazy="dynamic")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class Course(db.Model):
    """A course taught by one teacher with many enrolled students."""
    __tablename__ = "courses"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.Text, nullable=False)
    teacher_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    # Relationships
    attendance_records = db.relationship("Attendance", backref="course", lazy="dynamic")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class Attendance(db.Model):
    """One row = one student marked present for one course on one date."""
    __tablename__ = "attendance"

    id          = db.Column(db.Integer, primary_key=True)
    date        = db.Column(db.Date, server_default=db.func.current_date(), nullable=False)
    student_id  = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    created_at  = db.Column(db.DateTime(timezone=True), server_default=db.func.now())

    __table_args__ = (db.UniqueConstraint("date", "student_id", "course_id"),)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
