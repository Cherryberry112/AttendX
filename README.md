# AttendX — AI-Powered Smart Attendance System 


**AttendX** is a modern, end-to-end web application that revolutionizes educational attendance tracking by replacing manual roll-calls and basic sign-in sheets with **AI-powered facial recognition** and **dynamic session verification**.

Built with a high-performance **Python/Flask** backend, a sleek **Vanilla CSS/JS** frontend, and a cloud-native **Supabase (PostgreSQL)** database, AttendX guarantees secure, tamper-proof attendance marking while delivering a beautiful dark-themed user experience for **Students**, **Teachers**, and **Administrators**.

🌐 **Live Frontend (Vercel):** [https://attendx-virid-mu.vercel.app/](https://attendx-virid-mu.vercel.app/)  
☁️ **Live Backend (Render):** [https://attendx.onrender.com](https://attendx.onrender.com)  
📸 **Website Gallery:** [View Screenshots Folder](https://github.com/Cherryberry112/AttendX/tree/main/Gallery)  
🎥 **Live Demonstration Video:** [Link to be added]

---

## ✨ Key Features & User Workflows

###  For Students
- **Biometric Identity Enrollment:** Easily capture and register facial vectors securely using any standard laptop or mobile webcam via `face-api.js`.
- **Course Browsing & Requests:** Browse available courses, request to enroll, and easily cancel pending requests.
- **Frictionless Attendance Marking:** Mark attendance in seconds by verifying your face against active classroom sessions—preventing buddy punching.
- **Live Attendance Dashboard:** View real-time attendance percentages, course schedules, and historical records at a glance.
- **Instant Email Receipts:** Receive beautifully styled confirmation emails upon registration and attendance events.

###  For Teachers & Instructors
- **Course & Classroom Management:** Browse available courses and request to teach them. 
- **Dynamic Attendance Sessions:** Launch time-bound attendance sessions with live facial recognition directly from the classroom.
- **Live Roster Monitoring:** Watch in real-time as students check in, view attendance statistics, and identify chronic absences.
- **Course Dropout:** Safely drop/unenroll from a course if reassigned.

###  For Administrators
- **System-Wide Analytics:** High-level metrics tracking total active users, enrolled courses, and daily attendance volumes.
- **Course Request Management:** Approve or deny incoming course requests from Students and Teachers directly from the admin dashboard.
- **Automated Email Notifications:** Instantly receive structured email notifications whenever a user requests a course.
- **Security & Audit Logs:** Traceable records of all system actions.

---

##  Technology Stack

```mermaid
graph TD
    subgraph Frontend [Vercel Hosting / Client Browser]
        UI[HTML5 / Vanilla CSS Design System]
        JS[JavaScript ES6+ & face-api.js]
    end

    subgraph Backend [Render Cloud Web Service]
        API[Python Flask REST API]
        DB_ORM[SQLAlchemy ORM]
        Email[Brevo HTTP Email API]
    end

    subgraph Database [Supabase Cloud]
        PG[(PostgreSQL 15 Database)]
    end

    UI --> JS
    JS -- "HTTPS REST / JSON / JWT" --> API
    API --> DB_ORM
    DB_ORM -- "SQL / Relational Queries" --> PG
    API -- "HTTPS POST" --> Email
```

| Layer | Technology | Highlights |
| :--- | :--- | :--- |
| **Frontend UI/UX** | HTML5, Vanilla CSS, Lucide Icons | Custom design system featuring dark mode, glassmorphic cards, smooth micro-animations, and responsive CSS Grid/Flexbox layouts. |
| **Client Logic** | Vanilla JavaScript (ES6+) | Modular state management, Fetch API client, real-time camera stream capture (`getUserMedia`), and `face-api.js` for facial detection. |
| **Backend API** | Python 3, Flask, JWT | Lightweight, high-throughput RESTful API handling authentication, role-based authorization, and business logic. |
| **AI / Biometrics** | OpenCV & face-api.js | Extracts facial embeddings from webcam captures, performing Euclidean distance matching to verify student identities. |
| **Database** | Supabase (PostgreSQL 15) | Relational schema storing users, courses, enrollments, facial biometric vectors, and timestamped attendance logs. |
| **Email Service** | Brevo HTTP API | Automated transactional email service using custom-designed HTML email templates for user onboarding, course requests, and attendance notifications. |
| **Cloud Deployment**| Render & Vercel | **Vercel** delivers the static frontend globally via edge CDN; **Render** hosts the Python Flask backend containers. |

---

## 📁 Project Folder Structure

```text
attendX/
├── backend/
│   ├── app.py                  # Flask Application Entry Point
│   ├── models.py               # SQLAlchemy Database Models
│   ├── config.py               # Application Configuration & Env Vars
│   ├── routes/                 # REST API Blueprints
│   │   ├── auth.py             # Login, Registration & Auth routes
│   │   ├── student.py          # Student-specific operations
│   │   ├── teacher.py          # Teacher-specific operations
│   │   └── admin.py            # Admin oversight and management
│   ├── utils/
│   │   └── notifications.py    # Brevo Email templates & dispatching
│   ├── requirements.txt        # Python Dependencies
│   └── seed_courses.py         # DB seeding scripts
│
└── frontend/
    ├── css/
    │   ├── global.css          # CSS Variables, Animations, Utilities
    │   └── login.css           # Authentication UI styles
    ├── js/
    │   ├── api.js              # Centralized Fetch wrapper & JWT interceptor
    │   ├── auth.js             # Client-side Auth state management
    │   └── utils.js            # Toast notifications, sidebars, badges
    └── pages/
        ├── admin/              # Admin Dashboards (Requests, Dashboard)
        ├── student/            # Student Dashboards (Enroll, Mark, Browse)
        ├── teacher/            # Teacher Dashboards (Course view, Browse)
        └── shared/             # Shared UI components (Notifications)
```

---

##  Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Cherryberry112/AttendX.git
cd AttendX
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory with the following variables:
```ini
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
JWT_SECRET_KEY=your_super_secret_jwt_key
BREVO_API_KEY=your_brevo_api_key
MAIL_SENDER=admin@attendx.com
```

Run the backend server:
```bash
flask run --port=5000
```

### 3. Frontend Setup
The frontend uses standard HTML/CSS/JS. To serve it locally and avoid CORS/WebRTC issues, you should use a local web server (like Live Server in VS Code, or Python's `http.server`):
```bash
cd ../frontend
python -m http.server 3000
```
Open `http://localhost:3000` in your browser.

> **Note:** Make sure to update the `API_BASE_URL` in `frontend/js/api.js` to point to `http://localhost:5000/api` if you are testing the backend locally.

---

##  Automated Email Workflows

AttendX implements a robust email notification system that triggers highly-styled HTML emails for the following events:
1. **Welcome/Registration:** Sent immediately when a user creates an account.
2. **Attendance Logged:** Sent to a student when a teacher successfully marks them present using the live face recognition stream.
3. **Course Requests:** Sent to all Administrators when a student requests to enroll in a course or when a teacher requests to teach one.

---
*Developed as a modern capstone solution for next-generation classroom management.*
