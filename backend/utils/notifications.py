"""
AttendX — Email Notification Utilities
Sends HTML-rich emails via Brevo (Sendinblue) API — works on Render free tier.
Falls back to SMTP if BREVO_API_KEY is not set (for local development).
"""
import os
import re
import threading
from datetime import datetime

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

_BRAND_PURPLE = "#6C63FF"
_BRAND_DARK   = "#4834D4"
_SUCCESS_GREEN = "#0F9B58"


def is_valid_email(email: str) -> bool:
    return bool(email) and bool(EMAIL_REGEX.match(email.strip()))


# ── Low-level sender ──────────────────────────────────────────────────────────

def _send(to_email: str, subject: str, html: str) -> tuple:
    """Send one HTML email. Returns (success:bool, error_msg:str)."""
    if not is_valid_email(to_email):
        msg = f"Invalid recipient: {to_email}"
        print(f"[EMAIL] {msg}")
        return False, msg

    brevo_key = os.environ.get("BREVO_API_KEY", "").strip()
    if brevo_key:
        return _send_via_brevo(to_email, subject, html, brevo_key)
    else:
        return _send_via_smtp(to_email, subject, html)


def _send_via_brevo(to_email: str, subject: str, html: str, api_key: str) -> tuple:
    """Send via Brevo (Sendinblue) REST API."""
    try:
        import requests as _req

        sender_email = os.environ.get("MAIL_SENDER", "attendx.offitial@gmail.com").strip()

        resp = _req.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key":      api_key,
                "Content-Type": "application/json",
                "Accept":       "application/json",
            },
            json={
                "sender":      {"name": "AttendX", "email": sender_email},
                "to":          [{"email": to_email}],
                "subject":     subject,
                "htmlContent": html,
            },
            timeout=15,
        )

        if resp.status_code in (200, 201):
            print(f"[EMAIL] Brevo OK: '{subject}' -> {to_email}")
            return True, ""
        else:
            msg = f"Brevo HTTP {resp.status_code}: {resp.text[:300]}"
            print(f"[EMAIL] {msg}")
            return False, msg

    except Exception as exc:
        msg = f"Brevo exception: {exc}"
        print(f"[EMAIL] {msg}")
        return False, msg


def _send_via_smtp(to_email: str, subject: str, html: str) -> tuple:
    """Fallback: send via Gmail SMTP for local dev."""
    import smtplib, ssl as _ssl
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sender   = os.environ.get("MAIL_SENDER", "").strip()
    password = os.environ.get("MAIL_APP_PASSWORD", "").replace(" ", "").strip()

    if not sender or not password:
        msg = "No BREVO_API_KEY and no SMTP credentials set"
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
    def _run():
        ok, err = _send(to_email, subject, html)
        if not ok:
            print(f"[EMAIL] Async failed: {err}")
    threading.Thread(target=_run, daemon=True).start()


# ── Shared Email Card Layout (Inline CSS for 100% Email Client Support) ────────

def _wrap_email(header_title: str, header_subtitle: str, body_content: str, to_email: str, header_color: str = _BRAND_PURPLE) -> str:
    """Wraps body content inside a beautiful, responsive card layout in AttendX theme."""
    year = datetime.now().year
    subtitle_html = f'<p style="margin: 6px 0 0 0; font-size: 14px; color: rgba(255, 255, 255, 0.88); font-weight: 400;">{header_subtitle}</p>' if header_subtitle else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>AttendX</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F4F5FB; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
  <!-- Background Table -->
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #F4F5FB; padding: 40px 12px;">
    <tr>
      <td align="center">
        <!-- Main Card -->
        <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 560px; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 8px 30px rgba(108, 99, 255, 0.12); border: 1px solid #E2E8F0;">
          
          <!-- Top Header Banner -->
          <tr>
            <td align="center" style="background-color: {header_color}; background: linear-gradient(135deg, {header_color} 0%, {_BRAND_DARK} 100%); padding: 36px 28px; text-align: center;">
              <div style="display: inline-block; background-color: rgba(255, 255, 255, 0.18); border-radius: 8px; padding: 4px 12px; margin-bottom: 12px;">
                <span style="font-weight: 800; color: #ffffff; font-size: 13px; letter-spacing: 1.5px;">ATTENDX</span>
              </div>
              <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; line-height: 1.3; letter-spacing: -0.3px;">{header_title}</h1>
              {subtitle_html}
            </td>
          </tr>

          <!-- Main Body -->
          <tr>
            <td style="padding: 36px 32px; background-color: #ffffff; color: #2D3748; font-size: 15px; line-height: 1.65;">
              {body_content}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="background-color: #F8F9FA; padding: 22px 32px; border-top: 1px solid #EDF2F7; text-align: center;">
              <p style="margin: 0 0 4px 0; font-size: 12px; color: #718096; line-height: 1.5;">
                &copy; {year} <strong>AttendX</strong> &mdash; Smart Attendance System
              </p>
              <p style="margin: 0; font-size: 11px; color: #A0AEC0; line-height: 1.5;">
                This automated notification was sent to <span style="color: #6C63FF;">{to_email}</span>.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Registration Email ────────────────────────────────────────────────────────

def send_registration_email(username: str, email: str, role: str):
    if not is_valid_email(email):
        print(f"[EMAIL] Skipping registration email — invalid address: {email}")
        return

    role_label = role.capitalize()
    role_tip = {
        "student": "Your first step is to enroll your face from the student dashboard so you can be recognized automatically in class.",
        "teacher": "You can begin taking live attendance for your courses right away from the teacher dashboard.",
        "admin":   "You have full access to manage users, courses, and attendance records across the system.",
    }.get(role.lower(), "We are glad to have you on board.")

    body = f"""
    <h2 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 700; color: {_BRAND_PURPLE};">Hello, {username}!</h2>
    
    <p style="margin: 0 0 20px 0; color: #4A5568; font-size: 15px; line-height: 1.6;">
      Thank you for joining <strong>AttendX</strong> — the smart face-recognition attendance platform. Your account is now active and ready to use.
    </p>

    <!-- Role Card -->
    <div style="background-color: #F5F4FF; border-left: 4px solid {_BRAND_PURPLE}; border-radius: 8px; padding: 18px 20px; margin: 24px 0;">
      <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; font-weight: 800; color: {_BRAND_PURPLE}; letter-spacing: 1px;">Account Role</p>
      <p style="margin: 0 0 8px 0; font-size: 16px; font-weight: 700; color: #1A202C;">{role_label}</p>
      <p style="margin: 0; font-size: 14px; color: #4A5568; line-height: 1.5;">{role_tip}</p>
    </div>

    <!-- CTA Button -->
    <div style="text-align: center; margin: 32px 0 16px 0;">
      <a href="https://cherryberry112.github.io/AttendX/" target="_blank" style="display: inline-block; background-color: {_BRAND_PURPLE}; background: linear-gradient(135deg, {_BRAND_PURPLE} 0%, {_BRAND_DARK} 100%); color: #ffffff; font-weight: 700; font-size: 15px; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 4px 14px rgba(108, 99, 255, 0.35);">
        Go to Your Dashboard &rarr;
      </a>
    </div>
    """

    html = _wrap_email(
        header_title=f"Welcome to AttendX!",
        header_subtitle="Your smart attendance journey starts now.",
        body_content=body,
        to_email=email,
        header_color=_BRAND_PURPLE
    )
    _send_async(email, f"Welcome to AttendX, {username}!", html)


# ── Attendance Confirmation Email ─────────────────────────────────────────────

def notify_students_attendance(student_ids: list, course_name: str, att_date: str, teacher_name: str = "Your teacher"):
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


def _send_attendance_email(username: str, email: str, course_name: str, date_fmt: str, teacher_name: str):
    body = f"""
    <h2 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 700; color: {_SUCCESS_GREEN};">Hello, {username}!</h2>
    
    <p style="margin: 0 0 20px 0; color: #4A5568; font-size: 15px; line-height: 1.6;">
      Great news! Your attendance for today's class has been successfully recorded into the system.
    </p>

    <!-- Details Table -->
    <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; border-radius: 10px; border: 1px solid #E2E8F0; overflow: hidden; margin: 24px 0;">
      <tr>
        <td style="padding: 14px 18px; font-size: 13px; font-weight: 700; color: #718096; border-bottom: 1px solid #EDF2F7; width: 35%;">Course</td>
        <td style="padding: 14px 18px; font-size: 14px; font-weight: 700; color: #1A202C; border-bottom: 1px solid #EDF2F7;">{course_name}</td>
      </tr>
      <tr>
        <td style="padding: 14px 18px; font-size: 13px; font-weight: 700; color: #718096; border-bottom: 1px solid #EDF2F7;">Date</td>
        <td style="padding: 14px 18px; font-size: 14px; font-weight: 600; color: #2D3748; border-bottom: 1px solid #EDF2F7;">{date_fmt}</td>
      </tr>
      <tr>
        <td style="padding: 14px 18px; font-size: 13px; font-weight: 700; color: #718096; border-bottom: 1px solid #EDF2F7;">Status</td>
        <td style="padding: 14px 18px; border-bottom: 1px solid #EDF2F7;">
          <span style="display: inline-block; background-color: #E6F4EA; color: {_SUCCESS_GREEN}; font-weight: 800; font-size: 12px; padding: 4px 12px; border-radius: 6px; border: 1px solid #A8DADC;">
            &check; PRESENT
          </span>
        </td>
      </tr>
      <tr>
        <td style="padding: 14px 18px; font-size: 13px; font-weight: 700; color: #718096;">Instructor</td>
        <td style="padding: 14px 18px; font-size: 14px; font-weight: 600; color: #2D3748;">{teacher_name}</td>
      </tr>
    </table>

    <!-- CTA Button -->
    <div style="text-align: center; margin: 32px 0 16px 0;">
      <a href="https://cherryberry112.github.io/AttendX/frontend/pages/student/dashboard.html" target="_blank" style="display: inline-block; background-color: {_BRAND_PURPLE}; background: linear-gradient(135deg, {_BRAND_PURPLE} 0%, {_BRAND_DARK} 100%); color: #ffffff; font-weight: 700; font-size: 15px; text-decoration: none; padding: 14px 32px; border-radius: 8px; box-shadow: 0 4px 14px rgba(108, 99, 255, 0.35);">
        View Attendance History &rarr;
      </a>
    </div>
    """

    html = _wrap_email(
        header_title="Attendance Confirmed!",
        header_subtitle=f"{course_name} &bull; {date_fmt}",
        body_content=body,
        to_email=email,
        header_color=_BRAND_PURPLE
    )
    _send_async(email, f"Attendance Recorded — {course_name}", html)
