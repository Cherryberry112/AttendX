"""
AttendX — Email Notification Utilities
Sends HTML-rich emails via Resend API (HTTPS — works on all hosts including Render free tier).
Falls back to SMTP if RESEND_API_KEY is not set (for local development).
"""
import os
import re
import threading
from datetime import datetime

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

_BRAND_COLOR = "#6C63FF"
_BG          = "#0D0D1A"
_CARD_BG     = "#13131F"
_TEXT        = "#E2E2F0"
_MUTED       = "#8A8AA0"


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))


# ── Low-level sender ──────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str) -> tuple:
    """Send one HTML email. Returns (success:bool, error_msg:str).
    Uses Resend API (HTTPS) if RESEND_API_KEY is set, otherwise falls back to SMTP.
    """
    if not is_valid_email(to_email):
        msg = f"Invalid recipient: {to_email}"
        print(f"[EMAIL] {msg}")
        return False, msg

    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if resend_key:
        return _send_via_resend(to_email, subject, html, resend_key)
    else:
        return _send_via_smtp(to_email, subject, html)


def _send_via_resend(to_email: str, subject: str, html: str, api_key: str) -> tuple:
    """Send via Resend HTTP API — works on Render free tier (uses HTTPS port 443)."""
    try:
        import requests as _req

        resp = _req.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
                "User-Agent":    "AttendX-Mailer/1.0",
            },
            json={
                "from":    "AttendX <onboarding@resend.dev>",
                "to":      [to_email],
                "subject": subject,
                "html":    html,
            },
            timeout=15,
        )

        if resp.status_code in (200, 201):
            print(f"[EMAIL] Resend OK: '{subject}' -> {to_email}")
            return True, ""
        else:
            msg = f"Resend HTTP {resp.status_code}: {resp.text[:200]}"
            print(f"[EMAIL] {msg}")
            return False, msg

    except Exception as exc:
        msg = f"Resend exception: {exc}"
        print(f"[EMAIL] {msg}")
        return False, msg


def _send_via_smtp(to_email: str, subject: str, html: str) -> tuple:
    """Fallback: send via Gmail SMTP (works locally, blocked on Render free tier)."""
    import smtplib, ssl as _ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sender   = os.environ.get("MAIL_SENDER", "").strip()
    password = os.environ.get("MAIL_APP_PASSWORD", "").replace(" ", "").strip()

    if not sender or not password:
        msg = "No RESEND_API_KEY and no SMTP credentials set"
        print(f"[EMAIL] {msg}")
        return False, msg

    email_msg = MIMEMultipart("alternative")
    email_msg["Subject"] = subject
    email_msg["From"]    = f"AttendX <{sender}>"
    email_msg["To"]      = to_email
    email_msg.attach(MIMEText(html, "html", "utf-8"))
    raw = email_msg.as_string()

    last_error = ""
    for method, port in [("ssl", 465), ("starttls", 587)]:
        try:
            if method == "ssl":
                ctx = _ssl.create_default_context()
                with smtplib.SMTP_SSL("smtp.gmail.com", port, context=ctx, timeout=15) as s:
                    s.login(sender, password)
                    s.sendmail(sender, [to_email], raw)
            else:
                with smtplib.SMTP("smtp.gmail.com", port, timeout=15) as s:
                    s.ehlo(); s.starttls(); s.ehlo()
                    s.login(sender, password)
                    s.sendmail(sender, [to_email], raw)
            print(f"[EMAIL] SMTP port {port}: sent '{subject}' -> {to_email}")
            return True, ""
        except Exception as exc:
            last_error = f"port {port}: {exc}"
            print(f"[EMAIL] SMTP {last_error}")

    return False, last_error


def _send_async(to_email: str, subject: str, html: str):
    """Fire-and-forget in a daemon thread."""
    def _run():
        ok, err = _send(to_email, subject, html)
        if not ok:
            print(f"[EMAIL] Async failed: {err}")
    threading.Thread(target=_run, daemon=True).start()


# ── Shared HTML shell ─────────────────────────────────────────────────────────

def _wrap(content: str, preview: str = "") -> str:
    year = datetime.now().year
    preview_tag = (
        f'<span style="display:none;font-size:0;max-height:0;overflow:hidden;">{preview}</span>'
        if preview else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>AttendX</title>
  {preview_tag}
  <style>
    body      {{ margin:0; padding:0; background:{_BG}; font-family:'Segoe UI',Arial,sans-serif; color:{_TEXT}; }}
    a         {{ color:{_BRAND_COLOR}; text-decoration:none; }}
    .shell    {{ max-width:600px; margin:40px auto; background:{_CARD_BG}; border-radius:16px;
                 border:1px solid rgba(108,99,255,0.18); overflow:hidden;
                 box-shadow:0 8px 40px rgba(0,0,0,0.5); }}
    .top-bar  {{ background:linear-gradient(135deg,#6C63FF 0%,#9B59B6 100%);
                 padding:30px 40px 26px; text-align:center; }}
    .logo-box {{ display:inline-flex; align-items:center; gap:12px; }}
    .logo-icon{{ width:44px; height:44px; background:rgba(255,255,255,0.2); border-radius:10px;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1rem; font-weight:900; color:#fff; }}
    .logo-txt {{ font-size:1.5rem; font-weight:800; color:#fff; letter-spacing:-0.5px; }}
    .logo-txt span {{ color:rgba(255,255,255,0.65); }}
    .body     {{ padding:36px 40px; }}
    .footer   {{ padding:18px 40px; text-align:center; background:rgba(0,0,0,0.25);
                 border-top:1px solid rgba(255,255,255,0.05); }}
    .footer p {{ margin:0; font-size:0.72rem; color:{_MUTED}; line-height:1.8; }}
    h2        {{ margin:0 0 6px; font-size:1.3rem; font-weight:800; color:#fff; }}
    .sub      {{ font-size:0.84rem; color:{_MUTED}; margin:0 0 26px; }}
    p         {{ font-size:0.88rem; line-height:1.7; color:{_TEXT}; margin:0 0 14px; }}
    .divider  {{ border:none; border-top:1px solid rgba(255,255,255,0.07); margin:22px 0; }}
    .badge    {{ display:inline-block; background:rgba(108,99,255,0.15); color:{_BRAND_COLOR};
                 border:1px solid rgba(108,99,255,0.3); border-radius:6px;
                 font-size:0.76rem; font-weight:700; padding:3px 10px; }}
    .present  {{ background:rgba(15,155,88,0.15); color:#0F9B58;
                 border:1px solid rgba(15,155,88,0.3); border-radius:6px;
                 padding:3px 12px; font-size:0.82rem; font-weight:700; }}
  </style>
</head>
<body>
<div class="shell">
  <div class="top-bar">
    <div class="logo-box">
      <div class="logo-icon">AX</div>
      <div class="logo-txt">Attend<span>X</span></div>
    </div>
  </div>
  <div class="body">{content}</div>
  <div class="footer">
    <p>&copy; {year} AttendX &mdash; Smart Attendance System<br>
    This is an automated message. Please do not reply.</p>
  </div>
</div>
</body>
</html>"""


# ── Registration email ────────────────────────────────────────────────────────

def send_registration_email(username: str, email: str, role: str):
    if not is_valid_email(email):
        print(f"[EMAIL] Skipping registration email — invalid address: {email}")
        return

    role_label = role.capitalize()
    role_tip = {
        "student": "Your first step is to enroll your face from the student dashboard so you can be recognized automatically in class.",
        "teacher": "You can begin taking live attendance for your courses right away from the teacher dashboard.",
        "admin":   "You have full access to manage users, courses, and attendance records across the system.",
    }.get(role, "We are glad to have you on board.")

    content = f"""
    <h2>Welcome to AttendX, {username}!</h2>
    <p class="sub">Your account has been successfully created</p>
    <p>Thank you for joining <strong>AttendX</strong> &mdash; the smart face-recognition attendance platform.
    Your account is now active and ready to use.</p>
    <hr class="divider"/>
    <p style="font-size:0.78rem;color:{_MUTED};margin-bottom:6px;text-transform:uppercase;
              letter-spacing:0.08em;font-weight:700;">Your Role</p>
    <p><span class="badge">{role_label}</span></p>
    <p style="margin-top:18px;">{role_tip}</p>
    <hr class="divider"/>
    <p style="font-size:0.82rem;color:{_MUTED};">
      <strong>Next steps:</strong> Head over to your
      <a href="https://cherryberry112.github.io/AttendX/">AttendX Dashboard</a>
      and sign in with your email and password to get started.
    </p>"""

    html = _wrap(content, f"Welcome to AttendX, {username}! Your account is ready.")
    _send_async(email, f"Welcome to AttendX, {username}!", html)


# ── Attendance confirmation email ─────────────────────────────────────────────

def notify_students_attendance(student_ids: list, course_name: str, att_date: str,
                                teacher_name: str = "Your teacher"):
    from models import User
    try:
        date_fmt = datetime.strptime(att_date, "%Y-%m-%d").strftime("%A, %B %d, %Y")
    except Exception:
        date_fmt = att_date

    students = User.query.filter(User.id.in_(student_ids), User.type == "student").all()
    sent = 0
    for student in students:
        if not is_valid_email(student.email or ""):
            continue
        _send_attendance_email(student.username, student.email, course_name, date_fmt, teacher_name)
        sent += 1
    print(f"[EMAIL] Queued attendance emails for {sent}/{len(students)} students")


def _send_attendance_email(username: str, email: str, course_name: str,
                            date_fmt: str, teacher_name: str):
    content = f"""
    <h2>Attendance Confirmed!</h2>
    <p class="sub">{course_name} &mdash; {date_fmt}</p>
    <p>Hi <strong>{username}</strong>,</p>
    <p>Your attendance for today&rsquo;s class has been successfully recorded.</p>
    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
      <tr style="background:rgba(108,99,255,0.12);">
        <td style="padding:12px 16px;font-size:0.78rem;color:{_MUTED};font-weight:700;
                   text-transform:uppercase;letter-spacing:0.07em;width:38%;">Course</td>
        <td style="padding:12px 16px;font-size:0.86rem;color:{_TEXT};font-weight:600;">{course_name}</td>
      </tr>
      <tr style="background:rgba(255,255,255,0.03);">
        <td style="padding:12px 16px;font-size:0.78rem;color:{_MUTED};font-weight:700;
                   text-transform:uppercase;letter-spacing:0.07em;">Date</td>
        <td style="padding:12px 16px;font-size:0.86rem;color:{_TEXT};font-weight:600;">{date_fmt}</td>
      </tr>
      <tr style="background:rgba(108,99,255,0.12);">
        <td style="padding:12px 16px;font-size:0.78rem;color:{_MUTED};font-weight:700;
                   text-transform:uppercase;letter-spacing:0.07em;">Status</td>
        <td style="padding:12px 16px;"><span class="present">Present</span></td>
      </tr>
      <tr style="background:rgba(255,255,255,0.03);">
        <td style="padding:12px 16px;font-size:0.78rem;color:{_MUTED};font-weight:700;
                   text-transform:uppercase;letter-spacing:0.07em;">Recorded by</td>
        <td style="padding:12px 16px;font-size:0.86rem;color:{_TEXT};font-weight:600;">{teacher_name}</td>
      </tr>
    </table>
    <hr class="divider"/>
    <p style="font-size:0.83rem;color:{_MUTED};">
      Keep up the great work! View your full attendance history on your
      <a href="https://cherryberry112.github.io/AttendX/frontend/pages/student/dashboard.html">AttendX Dashboard</a>.
    </p>"""

    html = _wrap(content, f"Your attendance for {course_name} on {date_fmt} has been confirmed.")
    _send_async(email, f"Attendance Recorded — {course_name}", html)
