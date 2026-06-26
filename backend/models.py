from flask_sqlalchemy import SQLAlchemy
from __init__ import db

class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.Text, nullable=False)
    email      = db.Column(db.Text, unique=True, nullable=False)
    password   = db.Column(db.Text, nullable=False)
    role       = db.Column(db.Enum("admin", "teacher", "student", name="user_role"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    teacher    = db.relationship("Teacher", backref="user", uselist=False)
    student    = db.relationship("Student", backref="user", uselist=False)

class Teacher(db.Model):
    __tablename__ = "teachers"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department = db.Column(db.Text)
    phone      = db.Column(db.Text)
    courses    = db.relationship("Course", backref="teacher", lazy="dynamic")
    sessions   = db.relationship("AttendanceSession", backref="teacher", lazy="dynamic")

class Student(db.Model):
    __tablename__ = "students"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    student_id     = db.Column(db.Text, unique=True, nullable=False)
    department     = db.Column(db.Text)
    batch          = db.Column(db.Text)
    face_embedding = db.Column(db.Text)   # JSON string of 512-dim vector
    face_enrolled  = db.Column(db.Boolean, default=False)
    enrollments    = db.relationship("Enrollment", backref="student", lazy="dynamic")

class Course(db.Model):
    __tablename__ = "courses"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.Text, nullable=False)
    code       = db.Column(db.Text, unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    enrollments = db.relationship("Enrollment", backref="course", lazy="dynamic")
    sessions    = db.relationship("AttendanceSession", backref="course", lazy="dynamic")

class Enrollment(db.Model):
    __tablename__ = "enrollments"
    id          = db.Column(db.Integer, primary_key=True)
    student_id  = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"))
    course_id   = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"))
    enrolled_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    __table_args__ = (db.UniqueConstraint("student_id", "course_id"),)

class AttendanceSession(db.Model):
    __tablename__ = "attendance_sessions"
    id         = db.Column(db.Integer, primary_key=True)
    course_id  = db.Column(db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id", ondelete="SET NULL"))
    date       = db.Column(db.Date, server_default=db.func.current_date())
    status     = db.Column(db.Enum("draft", "confirmed", name="session_status"), default="draft")
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    records    = db.relationship("AttendanceRecord", backref="session", lazy="dynamic")

class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id         = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id", ondelete="CASCADE"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"))
    present    = db.Column(db.Boolean, default=False)
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    __table_args__ = (db.UniqueConstraint("session_id", "student_id"),)

class ActivityLog(db.Model):
    __tablename__ = "activity_log"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action     = db.Column(db.Text, nullable=False)
    details    = db.Column(db.Text)   # JSON string
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
