-- ============================================================
-- AttendX Database Schema for Supabase (PostgreSQL + pgvector)
-- 3-Table Relational Schema (Users, Courses, Attendance)
-- Run this in the Supabase SQL Editor (SQL -> New Query)
-- ============================================================

-- 1. Enable pgvector for face embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. DROP OLD/CONFLICTING TABLES & ENUMS (clean migration)
DROP TABLE IF EXISTS attendance_records CASCADE;
DROP TABLE IF EXISTS attendance_sessions CASCADE;
DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS activity_log CASCADE;
DROP TABLE IF EXISTS teachers CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS attendance CASCADE;
DROP TABLE IF EXISTS course_students CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS session_status CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

-- 3. CREATE ENUM TYPES
CREATE TYPE user_role AS ENUM ('admin', 'teacher', 'student');

-- ============================================================
-- Table 1: Users (unified — all roles in one table)
-- ============================================================
CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    type             user_role NOT NULL,
    student_id       TEXT UNIQUE,                  -- format: 2022-3-60-110 (NULL for teacher/admin)
    email            TEXT UNIQUE NOT NULL,
    phone            TEXT,
    username         TEXT NOT NULL,
    password         TEXT NOT NULL,                 -- bcrypt hash
    face_embedding   TEXT,                             -- JSON array of pose embeddings (NULL for teacher/admin)
    guardian_number  TEXT,                          -- parent/guardian phone (NULL for teacher/admin)
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Table 2: Courses
-- ============================================================
CREATE TABLE courses (
    id               SERIAL PRIMARY KEY,
    name             TEXT NOT NULL,
    teacher_id       INT REFERENCES users(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Junction: Course ↔ Student enrollment
-- (Maps: assigned_to -> student_id rows)
-- ============================================================
CREATE TABLE course_students (
    course_id   INT REFERENCES courses(id) ON DELETE CASCADE,
    student_id  INT REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (course_id, student_id)
);

-- ============================================================
-- Table 3: Attendance records
-- ============================================================
CREATE TABLE attendance (
    id           SERIAL PRIMARY KEY,
    date         DATE NOT NULL DEFAULT CURRENT_DATE,
    student_id   INT REFERENCES users(id) ON DELETE CASCADE,
    course_id    INT REFERENCES courses(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, student_id, course_id)
);

-- ============================================================
-- Indexes for performance
-- ============================================================
CREATE INDEX idx_attendance_student  ON attendance(student_id);
CREATE INDEX idx_attendance_course   ON attendance(course_id);
CREATE INDEX idx_attendance_date     ON attendance(date);
CREATE INDEX idx_course_students_sid ON course_students(student_id);
CREATE INDEX idx_users_type          ON users(type);

-- ============================================================
-- 4. SEED DATA (All passwords are '1234', hashed with bcrypt)
-- ============================================================

-- Users (1 Admin, 5 Teachers, 10 Students)
INSERT INTO users (
    id, type, student_id, email, phone, username, password, face_embedding, guardian_number
) VALUES
-- Admin (ID 1)
(1, 'admin', NULL, 'admin@example.com', '+8801700000000', 'admin_boss', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),

-- Teachers (IDs 2 - 6)
(2, 'teacher', NULL, 'adnan@example.com', '+8801711111111', 'adnan_sir', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),
(3, 'teacher', NULL, 'tanvir@example.com', '+8801711111112', 'tanvir_sir', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),
(4, 'teacher', NULL, 'farhana@example.com', '+8801711111113', 'farhana_maam', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),
(5, 'teacher', NULL, 'rahim@example.com', '+8801711111114', 'rahim_sir', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),
(6, 'teacher', NULL, 'nusrat@example.com', '+8801711111115', 'nusrat_maam', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, NULL),

-- Students (IDs 7 - 16)
(7, 'student', '2022-3-60-110', 'mohua@example.com', '+8801811111101', 'mohua', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111101'),
(8, 'student', '2022-3-60-111', 'kabira@example.com', '+8801811111102', 'kabira', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111102'),
(9, 'student', '2022-3-60-112', 'priya@example.com', '+8801811111103', 'priya', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111103'),
(10, 'student', '2022-3-60-113', 'mim@example.com', '+8801811111104', 'mim', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111104'),
(11, 'student', '2022-3-60-114', 'arman@example.com', '+8801811111105', 'arman', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111105'),
(12, 'student', '2022-3-60-115', 'sifat@example.com', '+8801811111106', 'sifat', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111106'),
(13, 'student', '2022-3-60-116', 'tanila@example.com', '+8801811111107', 'tanila', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111107'),
(14, 'student', '2022-3-60-117', 'fardin@example.com', '+8801811111108', 'fardin', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111108'),
(15, 'student', '2022-3-60-118', 'sadia@example.com', '+8801811111109', 'sadia', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111109'),
(16, 'student', '2022-3-60-119', 'nabil@example.com', '+8801811111110', 'nabil', '$2b$12$.l7MezcghInCuxrhyd3r5uj5Hrt.fL4ZSq/fVqwzI6jLx19rj/l2K', NULL, '+8801911111110');

-- Courses (IDs 101 - 110)
INSERT INTO courses (id, name, teacher_id) VALUES
(101, 'Web Development Fundamentals', 2),
(102, 'Data Science for Beginners', 3),
(103, 'Digital Marketing Mastery', 4),
(104, 'Python for Everybody', 2),
(105, 'Graphic Design Essentials', 6),
(106, 'Mobile App Development', 2),
(107, 'AI and Machine Learning', 3),
(108, 'Cybersecurity Fundamentals', 5),
(109, 'UX/UI Design Principles', 6),
(110, 'Blockchain Essentials', 5);

-- Course ↔ Student Enrollments (course_students junction table)
INSERT INTO course_students (course_id, student_id) VALUES
-- Course 101: 7, 8, 9, 10, 11
(101, 7), (101, 8), (101, 9), (101, 10), (101, 11),
-- Course 102: 7, 8, 12, 13
(102, 7), (102, 8), (102, 12), (102, 13),
-- Course 103: 9, 10, 14, 15
(103, 9), (103, 10), (103, 14), (103, 15),
-- Course 104: 7, 11, 12, 16
(104, 7), (104, 11), (104, 12), (104, 16),
-- Course 105: 8, 13, 14, 15
(105, 8), (105, 13), (105, 14), (105, 15),
-- Course 106: 9, 10, 11, 16
(106, 9), (106, 10), (106, 11), (106, 16),
-- Course 107: 7, 8, 12, 13
(107, 7), (107, 8), (107, 12), (107, 13),
-- Course 108: 14, 15, 16
(108, 14), (108, 15), (108, 16),
-- Course 109: 9, 10, 13, 15
(109, 9), (109, 10), (109, 13), (109, 15),
-- Course 110: 7, 11, 12, 16
(110, 7), (110, 11), (110, 12), (110, 16);

-- Attendance Records
INSERT INTO attendance (id, date, student_id, course_id) VALUES
-- Web Dev (Course 101) Attendance
(1, '2026-07-20', 7, 101),  -- Mohua
(2, '2026-07-20', 8, 101),  -- Kabira
(3, '2026-07-20', 9, 101),  -- Priya
(4, '2026-07-20', 10, 101), -- Mim

-- Python (Course 104) Attendance
(5, '2026-07-21', 7, 104),  -- Mohua
(6, '2026-07-21', 11, 104), -- Arman
(7, '2026-07-21', 12, 104), -- Sifat

-- AI & Machine Learning (Course 107) Attendance
(8, '2026-07-22', 7, 107),  -- Mohua
(9, '2026-07-22', 8, 107),  -- Kabira
(10, '2026-07-22', 12, 107); -- Sifat

-- 5. UPDATE SEQUENCE COUNTERS (so new UI additions don't collide with explicit IDs)
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users), true);
SELECT setval('courses_id_seq', (SELECT MAX(id) FROM courses), true);
SELECT setval('attendance_id_seq', (SELECT MAX(id) FROM attendance), true);
