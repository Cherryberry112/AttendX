-- ============================================================
-- AttendX Database Schema for Supabase (PostgreSQL + pgvector)
-- Run this in the Supabase SQL Editor
-- ============================================================

-- Enable pgvector for face embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- ENUM types
-- ============================================================
CREATE TYPE user_role AS ENUM ('admin', 'teacher', 'student');
CREATE TYPE session_status AS ENUM ('draft', 'confirmed');

-- ============================================================
-- Users (shared auth table)
-- ============================================================
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,               -- bcrypt hash
    role        user_role NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Teacher profiles
-- ============================================================
CREATE TABLE teachers (
    id          SERIAL PRIMARY KEY,
    user_id     INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    department  TEXT,
    phone       TEXT
);

-- ============================================================
-- Student profiles
-- ============================================================
CREATE TABLE students (
    id              SERIAL PRIMARY KEY,
    user_id         INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    student_id      TEXT UNIQUE NOT NULL,     -- e.g. "2021-CSE-001"
    department      TEXT,
    batch           TEXT,
    face_embedding  vector(512),              -- InsightFace ArcFace embedding
    face_enrolled   BOOLEAN DEFAULT FALSE
);

-- ============================================================
-- Courses
-- ============================================================
CREATE TABLE courses (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    code        TEXT UNIQUE NOT NULL,
    teacher_id  INT REFERENCES teachers(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Enrollments (student <-> course)
-- ============================================================
CREATE TABLE enrollments (
    id          SERIAL PRIMARY KEY,
    student_id  INT REFERENCES students(id) ON DELETE CASCADE,
    course_id   INT REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (student_id, course_id)
);

-- ============================================================
-- Attendance Sessions
-- ============================================================
CREATE TABLE attendance_sessions (
    id          SERIAL PRIMARY KEY,
    course_id   INT REFERENCES courses(id) ON DELETE CASCADE,
    teacher_id  INT REFERENCES teachers(id) ON DELETE SET NULL,
    date        DATE NOT NULL DEFAULT CURRENT_DATE,
    status      session_status DEFAULT 'draft',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Attendance Records
-- ============================================================
CREATE TABLE attendance_records (
    id          SERIAL PRIMARY KEY,
    session_id  INT REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    student_id  INT REFERENCES students(id) ON DELETE CASCADE,
    present     BOOLEAN DEFAULT FALSE,
    confidence  FLOAT,                        -- cosine similarity score
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (session_id, student_id)
);

-- ============================================================
-- Activity Log
-- ============================================================
CREATE TABLE activity_log (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    details     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Default Admin User (password: Admin@1234)
-- Update the hash after running: python -c "import bcrypt; print(bcrypt.hashpw(b'Admin@1234', bcrypt.gensalt()).decode())"
-- ============================================================
INSERT INTO users (name, email, password, role)
VALUES ('System Admin', 'admin@attendx.com', '$2b$12$PLACEHOLDER_HASH', 'admin');
