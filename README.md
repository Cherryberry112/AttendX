# AttendX — Smart Attendance System with Face Recognition

A web-based smart attendance management system that uses real-time face recognition to automate classroom attendance while reducing manual effort and improving accuracy.

---

## 📘 Course Information

| Item | Details |
|------|---------|
| **Course Code** | CSE 412 |
| **Course Title** | Software Engineering |

---

## 👨‍🏫 Course Instructor

| Information | Details |
|------------|---------|
| **Instructor** | [Ahmed Adnan](https://fse.ewubd.edu/computer-science-engineering/faculty-view/ahmed.adnan) |
| **Designation** | Lecturer |
| **Department** | Department of Computer Science & Engineering |
| **Email** | <ahmed.adnan@ewubd.edu> |

---

# Project Overview

AttendX is a modern web-based automated attendance system that utilizes real-time face recognition technology to simplify classroom attendance. Instead of manually recording attendance, the system automatically detects, identifies, and marks students through a classroom webcam.

The system is designed to reduce classroom time, eliminate proxy attendance, automate attendance calculations, and provide secure role-based access for administrators, teachers, and students.

---

# Project Vision

Traditional attendance systems consume valuable class time, are prone to proxy attendance, and require manual calculation of attendance records.

AttendX addresses these challenges by providing an automated, secure, and efficient attendance management solution using facial recognition technology.

---

# Core Objectives

- Save classroom time through automated attendance.
- Reduce proxy attendance.
- Automate attendance statistics and reporting.
- Provide secure role-based system access.
- Maintain centralized attendance records.

---

# User Roles

## Student

- Register an account.
- Complete face enrollment using five different face angles.
- View attendance statistics.
- Manage personal profile.

---

## Teacher

- Manage assigned courses.
- Start live attendance sessions.
- Review attendance draft before confirmation.
- Export attendance reports.

---

## Administrator

- Manage student and teacher accounts.
- Create and assign courses.
- Monitor attendance activities.
- Manage system-wide records.

---

# Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | HTML5, CSS3, JavaScript (ES6) |
| Backend | Python, Flask |
| Database | Supabase PostgreSQL, SQLite |
| Authentication | JWT, bcrypt |
| Face Recognition | InsightFace, ArcFace (ResNet50) |
| ORM | Flask-SQLAlchemy |

---

# Key Features

- Real-time Face Recognition Attendance
- Five-Step Face Enrollment
- Student Portal
- Teacher Portal
- Administrator Portal
- Attendance Draft Verification
- Excel Report Export
- Cloud Database Integration
- Local SQLite Fallback
- GitHub Pages Mock Mode

---

# Database Structure

The system consists of the following primary database tables:

- `users`
- `courses`
- `student_courses`
- `sessions`
- `attendance_records`

---

# Current Project Status

- Backend API Development
- Frontend Portal Development
- Face Recognition Integration
- Database Integration
- GitHub Repository Setup
- GitHub Pages Mock Showcase

---

## Project Repository

This repository is maintained as part of the **CSE 412 — Software Engineering** course project.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

---

> **Academic Notice**
>
> This repository is an ongoing university course project developed for academic purposes.
> Unauthorized copying, redistribution, or submission of this work for academic credit is strictly discouraged.
