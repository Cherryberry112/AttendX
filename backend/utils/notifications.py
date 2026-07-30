"""
AttendX — Email Notification Utilities
Sends HTML-rich welcome and attendance emails via Gmail SMTP.
"""
import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ── SMTP config from env ──────────────────────────────────────────────────────
MAIL_SENDER       = os.environ.get("MAIL_SENDER", "")
MAIL_APP_PASSWORD = os.environ.get("MAIL_APP_PASSWORD", "").replace(" ", "")
SMTP_HOST         = "smtp.gmail.com"
SMTP_PORT         = 587

_BRAND_COLOR  = "#6C63FF"
_GREEN        = "#0F9B58"
_BG           = "#0D0D1A"
_CARD_BG      = "#13131F"
_TEXT         = "#E2E2F0"
_MUTED        = "#8A8AA0"


# ── Low-level sender ──────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str) -> bool:
    """Send one HTML email. Returns True on success."""
    if not MAIL_SENDER or not MAIL_APP_PASSWORD:
        print(f"[EMAIL] No credentials set — skipping email to {to_email}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"AttendX Notifications <{MAIL_SENDER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(MAIL_SENDER, MAIL_APP_PASSWORD)
            server.sendmail(MAIL_SENDER, [to_email], msg.as_string())
        print(f"[EMAIL] ✓ Sent '{subject}' → {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] ✗ Failed to send to {to_email}: {e}")
        return False


def _send_async(to_email: str, subject: str, html: str):
    """Fire-and-forget email in a background thread so routes don't block."""
    t = threading.Thread(target=_send, args=(to_email, subject, html), daemon=True)
    t.start()


# ── Shared HTML shell ─────────────────────────────────────────────────────────

def _wrap(content: str, preview: str = "") -> str:
    """Wrap content in the AttendX branded email shell."""
    year = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AttendX</title>
  {'<span style="display:none;font-size:0;max-height:0;overflow:hidden;">' + preview + '</span>' if preview else ''}
  <style>
    body      {{ margin:0; padding:0; background:{_BG}; font-family:'Segoe UI',Arial,sans-serif; color:{_TEXT}; }}
    a         {{ color:{_BRAND_COLOR}; text-decoration:none; }}
    .shell    {{ max-width:600px; margin:40px auto; background:{_CARD_BG}; border-radius:16px;
                 border:1px solid rgba(108,99,255,0.18); overflow:hidden;
                 box-shadow:0 8px 40px rgba(0,0,0,0.5); }}
    .top-bar  {{ background:linear-gradient(135deg,#6C63FF 0%,#9B59B6 100%);
                 padding:32px 40px 28px; text-align:center; }}
    .logo     {{ display:inline-flex; align-items:center; gap:12px; }}
    .logo-box {{ width:46px; height:46px; background:rgba(255,255,255,0.2);
                 border-radius:10px; display:flex; align-items:center; justify-content:center;
                 font-size:1.1rem; font-weight:900; color:#fff; letter-spacing:-1px; }}
    .logo-txt {{ font-size:1.6rem; font-weight:800; color:#fff; letter-spacing:-0.5px; }}
    .logo-txt span {{ color:rgba(255,255,255,0.7); }}
    .body     {{ padding:36px 40px; }}
    .footer   {{ padding:20px 40px; text-align:center; background:rgba(0,0,0,0.2);
                 border-top:1px solid rgba(255,255,255,0.05); }}
    .footer p {{ margin:0; font-size:0.72rem; color:{_MUTED}; line-height:1.8; }}
    h2        {{ margin:0 0 6px; font-size:1.35rem; font-weight:800; color:#fff; }}
    .sub      {{ font-size:0.85rem; color:{_MUTED}; margin:0 0 28px; }}
    p         {{ font-size:0.9rem; line-height:1.7; color:{_TEXT}; margin:0 0 16px; }}
    .divider  {{ border:none; border-top:1px solid rgba(255,255,255,0.07); margin:24px 0; }}
    .badge    {{ display:inline-block; background:rgba(108,99,255,0.15); color:{_BRAND_COLOR};
                 border:1px solid rgba(108,99,255,0.3); border-radius:6px;
                 font-size:0.78rem; font-weight:700; padding:3px 10px; }}
  </style>
</head>
<body>
<div class="shell">
  <div class="top-bar">
    <div class="logo">
      <div class="logo-box">AX</div>
      <div class="logo-txt">Attend<span>X</span></div>
    </div>
  </div>
  <div class="body">
    {content}
  </div>
  <div class="footer">
    <p>© {year} AttendX — Smart Attendance System<br>
    This is an automated message. Please do not reply to this email.</p>
  </div>
</div>
</body>
</html>"""


# ── Welcome email ─────────────────────────────────────────────────────────────

def send_welcome_email(username: str, email: str, role: str):
    """Send a warm welcome email after a successful login."""
    role_label = role.capitalize()
    role_icon  = {"student": "🎓", "teacher": "📚", "admin": "🛡️"}.get(role, "👋")
    role_tip   = {
        "student": "You can enroll your face for automatic attendance, view your enrolled courses, and track your attendance rate — all from your dashboard.",
        "teacher": "You can take live attendance using face recognition, view session history for each course, and track student participation.",
        "admin":   "You have full access to manage users, courses, and attendance records across the entire system.",
    }.get(role, "Explore your dashboard to get started.")

    time_now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    content = f"""
    <h2>{role_icon} Welcome back, {username}!</h2>
    <p class="sub">You signed in successfully at {time_now}</p>

    <p>We're glad to see you again at <strong>AttendX</strong> — your smart face-recognition attendance platform. Your account is active and everything is ready for you.</p>

    <hr class="divider"/>

    <p style="font-size:0.82rem;color:{_MUTED};margin-bottom:8px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;">Your Role</p>
    <p><span class="badge">{role_label}</span></p>

    <p style="margin-top:20px;">{role_tip}</p>

    <hr class="divider"/>

    <p style="font-size:0.82rem;color:{_MUTED};">
      🔒 <strong>Security tip:</strong> If you did not sign in just now, please change your password immediately by contacting your system administrator.
    </p>
    """

    html = _wrap(content, preview=f"Welcome back, {username}! You signed in to AttendX.")
    _send_async(email, f"✅ Welcome back to AttendX, {username}!", html)


# ── Attendance confirmation email ─────────────────────────────────────────────

def notify_students_attendance(student_ids: list, course_name: str, att_date: str,
                                teacher_name: str = "Your teacher"):
    """Send attendance confirmation emails to all present students."""
    from models import User

    try:
        date_fmt = datetime.strptime(att_date, "%Y-%m-%d").strftime("%A, %B %d %Y")
    except Exception:
        date_fmt = att_date

    students = User.query.filter(User.id.in_(student_ids), User.type == "student").all()

    for student in students:
        if not student.email:
            continue
        _send_attendance_email(student.username, student.email, course_name, date_fmt, teacher_name)


def _send_attendance_email(username: str, email: str, course_name: str,
                            date_fmt: str, teacher_name: str):
    content = f"""
    <h2>🎉 Attendance Confirmed!</h2>
    <p class="sub">{course_name} — {date_fmt}</p>

    <p>Hi <strong>{username}</strong>,</p>

    <p>Great news! Your attendance for today's class has been successfully recorded. Here are the details:</p>

    <table style="width:100%;border-collapse:collapse;margin:20px 0;border-radius:10px;overflow:hidden;">
      <tr style="background:rgba(108,99,255,0.12);">
        <td style="padding:12px 16px;font-size:0.8rem;color:{_MUTED};font-weight:700;text-transform:uppercase;letter-spacing:0.07em;width:40%;">Course</td>
        <td style="padding:12px 16px;font-size:0.88rem;color:{_TEXT};font-weight:600;">{course_name}</td>
      </tr>
      <tr style="background:rgba(255,255,255,0.03);">
        <td style="padding:12px 16px;font-size:0.8rem;color:{_MUTED};font-weight:700;text-transform:uppercase;letter-spacing:0.07em;">Date</td>
        <td style="padding:12px 16px;font-size:0.88rem;color:{_TEXT};font-weight:600;">{date_fmt}</td>
      </tr>
      <tr style="background:rgba(108,99,255,0.12);">
        <td style="padding:12px 16px;font-size:0.8rem;color:{_MUTED};font-weight:700;text-transform:uppercase;letter-spacing:0.07em;">Status</td>
        <td style="padding:12px 16px;">
          <span style="background:rgba(15,155,88,0.15);color:#0F9B58;border:1px solid rgba(15,155,88,0.3);
                       border-radius:6px;padding:3px 12px;font-size:0.82rem;font-weight:700;">
            ✓ Present
          </span>
        </td>
      </tr>
      <tr style="background:rgba(255,255,255,0.03);">
        <td style="padding:12px 16px;font-size:0.8rem;color:{_MUTED};font-weight:700;text-transform:uppercase;letter-spacing:0.07em;">Recorded by</td>
        <td style="padding:12px 16px;font-size:0.88rem;color:{_TEXT};font-weight:600;">{teacher_name}</td>
      </tr>
    </table>

    <hr class="divider"/>

    <p style="font-size:0.85rem;color:{_MUTED};">
      Keep up the great work! Maintaining a strong attendance record is important for your academic progress. You can view your full attendance history on your
      <a href="https://cherryberry112.github.io/AttendX/frontend/pages/student/dashboard.html">AttendX Dashboard</a>.
    </p>
    """

    html = _wrap(content, preview=f"Your attendance for {course_name} on {date_fmt} has been confirmed!")
    _send_async(email, f"✅ Attendance Recorded — {course_name}", html)
