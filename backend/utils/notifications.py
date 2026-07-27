"""
AttendX — Notification Utilities (Placeholder)

Real SMS integration (Twilio / SSL Wireless) to be added later.
For now, notifications are logged to console.
"""


def notify_students_attendance(student_ids, course_name, date):
    """Notify students that their attendance has been recorded.
    
    In production, this would send push notifications or SMS.
    For now, it logs to console.
    """
    for sid in student_ids:
        print(f"[NOTIFICATION] Student #{sid} — attendance recorded for {course_name} on {date}")


def send_monthly_guardian_report():
    """Send monthly attendance summary SMS to each student's guardian.
    
    This should be called by a scheduled job (e.g. cron, APScheduler, Celery Beat).
    For now, it logs the report to console.
    """
    from models import User, Course, Attendance
    from __init__ import db
    from datetime import date, timedelta
    import calendar

    today = date.today()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])

    students = User.query.filter_by(type="student").filter(User.guardian_number.isnot(None)).all()

    for student in students:
        report_lines = []
        for course in student.enrolled_courses:
            # Total classes this month
            total = (db.session.query(db.func.count(db.distinct(Attendance.date)))
                     .filter(Attendance.course_id == course.id,
                             Attendance.date >= first_day,
                             Attendance.date <= last_day)
                     .scalar()) or 0
            # Student's attendance this month
            attended = (Attendance.query
                        .filter_by(course_id=course.id, student_id=student.id)
                        .filter(Attendance.date >= first_day,
                                Attendance.date <= last_day)
                        .count())
            report_lines.append(f"  {course.name}: {attended}/{total}")

        if report_lines:
            msg = (f"AttendX Monthly Report for {student.username} "
                   f"({first_day.strftime('%B %Y')}):\n" + "\n".join(report_lines))
            # TODO: Replace with real SMS API call
            print(f"[SMS → {student.guardian_number}] {msg}")
