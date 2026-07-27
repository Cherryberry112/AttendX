import bcrypt
from datetime import date
from models import db, User, Course, Attendance

def seed_all_data():
    Attendance.query.delete()
    Course.query.delete()
    User.query.delete()
    db.session.commit()

    # All passwords are "1234"
    pwd_1234 = bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode()

    # 1. Users
    users_data = [
        # (id, type, student_id, email, phone, username, guardian_number)
        (1, 'admin', None, 'admin@example.com', '+8801700000000', 'admin_boss', None),
        (2, 'teacher', None, 'adnan@example.com', '+8801711111111', 'adnan_sir', None),
        (3, 'teacher', None, 'tanvir@example.com', '+8801711111112', 'tanvir_sir', None),
        (4, 'teacher', None, 'farhana@example.com', '+8801711111113', 'farhana_maam', None),
        (5, 'teacher', None, 'rahim@example.com', '+8801711111114', 'rahim_sir', None),
        (6, 'teacher', None, 'nusrat@example.com', '+8801711111115', 'nusrat_maam', None),
        (7, 'student', '2022-3-60-110', 'mohua@example.com', '+8801811111101', 'mohua', '+8801911111101'),
        (8, 'student', '2022-3-60-111', 'kabira@example.com', '+8801811111102', 'kabira', '+8801911111102'),
        (9, 'student', '2022-3-60-112', 'priya@example.com', '+8801811111103', 'priya', '+8801911111103'),
        (10, 'student', '2022-3-60-113', 'mim@example.com', '+8801811111104', 'mim', '+8801911111104'),
        (11, 'student', '2022-3-60-114', 'arman@example.com', '+8801811111105', 'arman', '+8801911111105'),
        (12, 'student', '2022-3-60-115', 'sifat@example.com', '+8801811111106', 'sifat', '+8801911111106'),
        (13, 'student', '2022-3-60-116', 'tanila@example.com', '+8801811111107', 'tanila', '+8801911111107'),
        (14, 'student', '2022-3-60-117', 'fardin@example.com', '+8801811111108', 'fardin', '+8801911111108'),
        (15, 'student', '2022-3-60-118', 'sadia@example.com', '+8801811111109', 'sadia', '+8801911111109'),
        (16, 'student', '2022-3-60-119', 'nabil@example.com', '+8801811111110', 'nabil', '+8801911111110'),
    ]

    user_objs = {}
    for uid, utype, sid, email, phone, uname, gnum in users_data:
        u = User(
            id=uid,
            type=utype,
            student_id=sid,
            email=email,
            phone=phone,
            username=uname,
            password=pwd_1234,
            guardian_number=gnum
        )
        db.session.add(u)
        user_objs[uid] = u
    db.session.commit()

    # 2. Courses
    courses_data = [
        (101, 'Web Development Fundamentals', 2, [7, 8, 9, 10, 11]),
        (102, 'Data Science for Beginners', 3, [7, 8, 12, 13]),
        (103, 'Digital Marketing Mastery', 4, [9, 10, 14, 15]),
        (104, 'Python for Everybody', 2, [7, 11, 12, 16]),
        (105, 'Graphic Design Essentials', 6, [8, 13, 14, 15]),
        (106, 'Mobile App Development', 2, [9, 10, 11, 16]),
        (107, 'AI and Machine Learning', 3, [7, 8, 12, 13]),
        (108, 'Cybersecurity Fundamentals', 5, [14, 15, 16]),
        (109, 'UX/UI Design Principles', 6, [9, 10, 13, 15]),
        (110, 'Blockchain Essentials', 5, [7, 11, 12, 16]),
    ]

    for cid, name, tid, st_ids in courses_data:
        c = Course(id=cid, name=name, teacher_id=tid)
        for sid in st_ids:
            if sid in user_objs:
                c.students.append(user_objs[sid])
        db.session.add(c)
    db.session.commit()

    # 3. Attendance
    attendance_data = [
        (1, date(2026, 7, 20), 7, 101),
        (2, date(2026, 7, 20), 8, 101),
        (3, date(2026, 7, 20), 9, 101),
        (4, date(2026, 7, 20), 10, 101),
        (5, date(2026, 7, 21), 7, 104),
        (6, date(2026, 7, 21), 11, 104),
        (7, date(2026, 7, 21), 12, 104),
        (8, date(2026, 7, 22), 7, 107),
        (9, date(2026, 7, 22), 8, 107),
        (10, date(2026, 7, 22), 12, 107),
    ]

    for aid, d, sid, cid in attendance_data:
        att = Attendance(id=aid, date=d, student_id=sid, course_id=cid)
        db.session.add(att)
    db.session.commit()
    print("[SUCCESS] Seeded 16 users, 10 courses, enrollments, and 10 attendance records.")

if __name__ == '__main__':
    from __init__ import create_app
    app = create_app()
    with app.app_context():
        seed_all_data()
