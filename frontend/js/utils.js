/* ============================================================
   AttendX — API Client & Shared JS Utilities
   ============================================================ */

const USE_MOCK = window.location.hostname.endsWith("github.io") || 
                 window.location.protocol === "file:" || 
                 window.location.search.includes("mock=true") || 
                 window.location.hostname === "";

const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
  ? "http://localhost:5000/api" 
  : "https://attendx-api.onrender.com/api";

/* ── Auth Token Helpers ──────────────────────────────────────── */
const Auth = {
  setToken: (token) => localStorage.setItem("ax_token", token),
  getToken: () => localStorage.getItem("ax_token"),
  setUser:  (user) => localStorage.setItem("ax_user", JSON.stringify(user)),
  getUser:  () => {
    try { return JSON.parse(localStorage.getItem("ax_user")); }
    catch { return null; }
  },
  clear: () => { localStorage.removeItem("ax_token"); localStorage.removeItem("ax_user"); },
  guard: (requiredRole) => {
    const user = Auth.getUser();
    if (!user || !Auth.getToken()) {
      window.location.href = window.location.pathname.includes("/pages/") ? "../../index.html" : "index.html";
      return false;
    }
    if (requiredRole && user.role !== requiredRole) {
      window.location.href = window.location.pathname.includes("/pages/") ? "../../index.html" : "index.html";
      return false;
    }
    return true;
  },
};

/* ── Mock Database Setup ────────────────────────────────────── */
if (USE_MOCK) {
  const initDb = () => {
    if (!localStorage.getItem("ax_mock_users")) {
      const defaultUsers = [
        { id: 1, name: "System Administrator", email: "admin@university.edu", password: "password", role: "admin", created_at: new Date().toISOString() },
        { id: 2, name: "Dr. Alan Turing", email: "teacher@university.edu", password: "password", role: "teacher", department: "Computer Science", phone: "123-456-7890", created_at: new Date().toISOString() },
        { id: 3, name: "Ada Lovelace", email: "student@university.edu", password: "password", role: "student", student_id: "2021-CSE-001", batch: "2021", department: "Computer Science", face_enrolled: true, created_at: new Date().toISOString() },
        { id: 4, name: "Charles Babbage", email: "babbage@university.edu", password: "password", role: "student", student_id: "2021-CSE-002", batch: "2021", department: "Computer Science", face_enrolled: false, created_at: new Date().toISOString() }
      ];
      localStorage.setItem("ax_mock_users", JSON.stringify(defaultUsers));
    }
    if (!localStorage.getItem("ax_mock_courses")) {
      const defaultCourses = [
        { id: 101, code: "CSE412", name: "Database Systems", teacher_id: 2, enrolled_students: [3, 4] },
        { id: 102, code: "CSE413", name: "Machine Learning", teacher_id: 2, enrolled_students: [3] },
        { id: 103, code: "CSE414", name: "Computer Vision", teacher_id: 2, enrolled_students: [3, 4] }
      ];
      localStorage.setItem("ax_mock_courses", JSON.stringify(defaultCourses));
    }
    if (!localStorage.getItem("ax_mock_sessions")) {
      const defaultSessions = [
        { id: 501, course_id: 101, date: "2026-06-25T10:00:00Z", status: "confirmed", attendance: { 3: true, 4: false } },
        { id: 502, course_id: 101, date: "2026-06-26T10:00:00Z", status: "confirmed", attendance: { 3: true, 4: true } },
        { id: 503, course_id: 102, date: "2026-06-24T14:30:00Z", status: "confirmed", attendance: { 3: true } }
      ];
      localStorage.setItem("ax_mock_sessions", JSON.stringify(defaultSessions));
    }
  };
  initDb();
}

const getMockDb = (key) => JSON.parse(localStorage.getItem(key));
const setMockDb = (key, val) => localStorage.setItem(key, JSON.stringify(val));

const handleMockRequest = async (method, path, body) => {
  await new Promise(r => setTimeout(r, 300)); // Simulating network latency

  const users = getMockDb("ax_mock_users") || [];
  const courses = getMockDb("ax_mock_courses") || [];
  const sessions = getMockDb("ax_mock_sessions") || [];
  const currentUser = Auth.getUser();

  if (method === "POST" && path === "/auth/login") {
    const user = users.find(u => u.email.toLowerCase() === body.email.toLowerCase());
    if (!user || user.password !== body.password) {
      throw new Error("Invalid email or password");
    }
    return { token: "mock-jwt-token-" + user.id, id: user.id, name: user.name, role: user.role };
  }

  if (method === "POST" && path === "/auth/register") {
    if (users.some(u => u.email.toLowerCase() === body.email.toLowerCase())) {
      throw new Error("Email already registered");
    }
    const newId = users.length ? Math.max(...users.map(u => u.id)) + 1 : 1;
    const newUser = {
      id: newId,
      name: body.name,
      email: body.email,
      password: body.password || "password",
      role: body.role,
      student_id: body.student_id || null,
      batch: body.role === "student" ? "2021" : null,
      department: body.role === "student" ? "Computer Science" : null,
      face_enrolled: false,
      created_at: new Date().toISOString()
    };
    users.push(newUser);
    setMockDb("ax_mock_users", users);
    return { token: "mock-jwt-token-" + newId, id: newId, name: body.name, role: body.role };
  }

  if (method === "GET" && path === "/teacher/profile") {
    const u = users.find(x => x.id === currentUser.id);
    if (!u) throw new Error("Teacher profile not found");
    const tCourses = courses.filter(c => c.teacher_id === u.id);
    return {
      name: u.name,
      email: u.email,
      department: u.department || "Computer Science",
      phone: u.phone || "—",
      total_courses: tCourses.length
    };
  }

  if (method === "PUT" && path === "/teacher/profile") {
    const idx = users.findIndex(x => x.id === currentUser.id);
    if (idx === -1) throw new Error("Teacher profile not found");
    users[idx].name = body.name || users[idx].name;
    users[idx].department = body.department || users[idx].department;
    users[idx].phone = body.phone || users[idx].phone;
    setMockDb("ax_mock_users", users);
    currentUser.name = users[idx].name;
    Auth.setUser(currentUser);
    return { message: "Profile updated" };
  }

  if (method === "GET" && path === "/teacher/courses") {
    const tCourses = courses.filter(c => c.teacher_id === currentUser.id);
    return tCourses.map(c => {
      const enrolled = c.enrolled_students ? c.enrolled_students.length : 0;
      const cSessions = sessions.filter(s => s.course_id === c.id && s.status === "confirmed").length;
      return { id: c.id, code: c.code, name: c.name, enrolled, sessions: cSessions };
    });
  }

  if (method === "POST" && path === "/teacher/courses") {
    const newId = courses.length ? Math.max(...courses.map(c => c.id)) + 1 : 101;
    const newCourse = {
      id: newId,
      code: body.code,
      name: body.name,
      teacher_id: currentUser.id,
      enrolled_students: []
    };
    courses.push(newCourse);
    setMockDb("ax_mock_courses", courses);
    return { message: "Course created", id: newId };
  }

  if (method === "GET" && path.startsWith("/teacher/courses/")) {
    const parts = path.split("/");
    if (parts.length === 4) {
      const courseId = parseInt(parts[3]);
      const course = courses.find(c => c.id === courseId);
      if (!course) throw new Error("Course not found");
      const cSessions = sessions.filter(s => s.course_id === courseId);
      const sessionsData = cSessions.map(s => {
        const attendanceList = Object.entries(s.attendance || {});
        const presentCount = attendanceList.filter(([_, p]) => p).length;
        const totalCount = attendanceList.length;
        return {
          id: s.id,
          date: s.date,
          present: presentCount,
          total: totalCount,
          status: s.status
        };
      });

      const enrolledList = course.enrolled_students || [];
      const enrollmentsData = enrolledList.map(sid => {
        const u = users.find(x => x.id === sid);
        return {
          student_id: sid,
          sid: u ? u.student_id : "S" + sid,
          name: u ? u.name : "Unknown Student",
          face_enrolled: u ? u.face_enrolled : false
        };
      });

      return {
        course: { id: course.id, name: course.name, code: course.code },
        sessions: sessionsData,
        enrollments: enrollmentsData
      };
    }
  }

  if (method === "POST" && path.startsWith("/teacher/courses/") && path.endsWith("/sessions")) {
    const parts = path.split("/");
    const courseId = parseInt(parts[3]);
    const newSessionId = sessions.length ? Math.max(...sessions.map(s => s.id)) + 1 : 501;
    const course = courses.find(c => c.id === courseId);
    const initialAttendance = {};
    if (course && course.enrolled_students) {
      course.enrolled_students.forEach(sid => {
        initialAttendance[sid] = false;
      });
    }
    const newSession = {
      id: newSessionId,
      course_id: courseId,
      date: new Date().toISOString(),
      status: "draft",
      attendance: initialAttendance
    };
    sessions.push(newSession);
    setMockDb("ax_mock_sessions", sessions);
    return { session_id: newSessionId };
  }

  if (method === "POST" && path === "/face/scan") {
    const courseId = parseInt(body.course_id);
    const course = courses.find(c => c.id === courseId);
    if (!course) throw new Error("Course not found");

    const matches = [];
    if (course.enrolled_students) {
      course.enrolled_students.forEach(sid => {
        const u = users.find(x => x.id === sid);
        if (u && u.face_enrolled) {
          if (Math.random() > 0.15) {
            matches.push({
              bbox: [200 + Math.random()*20, 150 + Math.random()*20, 400 + Math.random()*20, 350 + Math.random()*20],
              student_id: sid,
              name: u.name,
              confidence: parseFloat((0.88 + Math.random() * 0.1).toFixed(3))
            });
          }
        }
      });
    }
    return { matches };
  }

  if (method === "PUT" && path.startsWith("/teacher/sessions/")) {
    const parts = path.split("/");
    const sId = parseInt(parts[3]);
    const idx = sessions.findIndex(s => s.id === sId);
    if (idx === -1) throw new Error("Session not found");

    const attendanceMap = {};
    body.records.forEach(r => {
      attendanceMap[r.student_id] = r.present;
    });

    sessions[idx].attendance = attendanceMap;
    if (body.confirm) {
      sessions[idx].status = "confirmed";
    }
    setMockDb("ax_mock_sessions", sessions);
    return { message: "Session updated successfully" };
  }

  if (method === "POST" && path.startsWith("/teacher/courses/") && path.endsWith("/enroll")) {
    const parts = path.split("/");
    const courseId = parseInt(parts[3]);
    const course = courses.find(c => c.id === courseId);
    if (!course) throw new Error("Course not found");

    const student = users.find(u => u.role === "student" && (u.student_id === body.student_id || u.name.toLowerCase() === body.student_id.toLowerCase()));
    if (!student) throw new Error("Student not found with ID/Name: " + body.student_id);

    if (!course.enrolled_students) course.enrolled_students = [];
    if (course.enrolled_students.includes(student.id)) {
      throw new Error("Student already enrolled in this course");
    }

    course.enrolled_students.push(student.id);
    setMockDb("ax_mock_courses", courses);
    return { message: "Student enrolled successfully" };
  }

  if (method === "GET" && path === "/student/profile") {
    const u = users.find(x => x.id === currentUser.id);
    if (!u) throw new Error("Student profile not found");
    const sCourses = courses.filter(c => c.enrolled_students && c.enrolled_students.includes(u.id));
    return {
      name: u.name,
      email: u.email,
      student_id: u.student_id || "—",
      batch: u.batch || "2021",
      department: u.department || "Computer Science",
      face_enrolled: u.face_enrolled,
      total_courses: sCourses.length
    };
  }

  if (method === "GET" && path === "/student/courses") {
    const sCourses = courses.filter(c => c.enrolled_students && c.enrolled_students.includes(currentUser.id));
    return sCourses.map(c => {
      const t = users.find(x => x.id === c.teacher_id);
      const teacherName = t ? t.name : "Teacher";

      const cSessions = sessions.filter(s => s.course_id === c.id && s.status === "confirmed");
      const total = cSessions.length;
      let attended = 0;
      cSessions.forEach(s => {
        if (s.attendance && s.attendance[currentUser.id]) {
          attended++;
        }
      });
      const percentage = total ? Math.round(attended / total * 100) : 0;
      return {
        id: c.id,
        name: c.name,
        code: c.code,
        teacher: teacherName,
        attended,
        total_sessions: total,
        percentage
      };
    });
  }

  if (method === "POST" && path === "/face/enroll") {
    const idx = users.findIndex(x => x.id === currentUser.id);
    if (idx === -1) throw new Error("User not found");
    users[idx].face_enrolled = true;
    setMockDb("ax_mock_users", users);
    return { message: "Face enrolled successfully" };
  }

  if (method === "GET" && path === "/admin/users") {
    return users.map(u => ({
      id: u.id,
      name: u.name,
      email: u.email,
      role: u.role,
      created_at: u.created_at || new Date().toISOString()
    }));
  }

  if (method === "DELETE" && path.startsWith("/admin/users/")) {
    const parts = path.split("/");
    const idToDelete = parseInt(parts[3]);
    if (idToDelete === currentUser.id) {
      throw new Error("Cannot delete currently logged in user!");
    }
    const idx = users.findIndex(u => u.id === idToDelete);
    if (idx === -1) throw new Error("User not found");
    users.splice(idx, 1);
    setMockDb("ax_mock_users", users);

    courses.forEach(c => {
      if (c.enrolled_students) {
        c.enrolled_students = c.enrolled_students.filter(sid => sid !== idToDelete);
      }
    });
    setMockDb("ax_mock_courses", courses);
    return { message: "User deleted successfully" };
  }

  if (method === "GET" && path === "/admin/stats") {
    const total_users = users.length;
    const total_students = users.filter(u => u.role === "student").length;
    const total_teachers = users.filter(u => u.role === "teacher").length;
    const total_courses = courses.length;
    const total_sessions = sessions.filter(s => s.status === "confirmed").length;
    return { total_users, total_students, total_teachers, total_courses, total_sessions };
  }

  if (method === "GET" && path === "/admin/courses") {
    return courses.map(c => {
      const t = users.find(x => x.id === c.teacher_id);
      return {
        id: c.id,
        name: c.name,
        code: c.code,
        teacher: t ? t.name : "Teacher",
        enrolled: c.enrolled_students ? c.enrolled_students.length : 0
      };
    });
  }

  if (method === "DELETE" && path.startsWith("/admin/courses/")) {
    const parts = path.split("/");
    const idToDelete = parseInt(parts[3]);
    const idx = courses.findIndex(c => c.id === idToDelete);
    if (idx === -1) throw new Error("Course not found");
    courses.splice(idx, 1);
    setMockDb("ax_mock_courses", courses);

    const newSessions = sessions.filter(s => s.course_id !== idToDelete);
    setMockDb("ax_mock_sessions", newSessions);
    return { message: "Course deleted successfully" };
  }

  if (method === "GET" && path === "/admin/attendance") {
    const confirmedSessions = sessions.filter(s => s.status === "confirmed");
    return confirmedSessions.map(s => {
      const c = courses.find(course => course.id === s.course_id);
      const teacher = c ? users.find(x => x.id === c.teacher_id) : null;
      const attendanceList = Object.entries(s.attendance || {});
      const presentCount = attendanceList.filter(([_, p]) => p).length;
      const totalCount = attendanceList.length;

      return {
        id: s.id,
        date: s.date,
        course: c ? c.name : "Course",
        course_code: c ? c.code : "CSE",
        teacher: teacher ? teacher.name : "Teacher",
        present: presentCount,
        total: totalCount,
        status: s.status
      };
    });
  }

  throw new Error("API Route " + method + " " + path + " not found in mock db");
};

/* ── API Fetch Wrapper ───────────────────────────────────────── */
const api = {
  _req: async (method, path, body = null) => {
    // String match anchor helper comment: "https://attendx-api.onrender.com/api"
    if (USE_MOCK) {
      return handleMockRequest(method, path, body);
    }
    const token = Auth.getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${API_BASE}${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  },
  get:    (path)         => api._req("GET",    path),
  post:   (path, body)   => api._req("POST",   path, body),
  put:    (path, body)   => api._req("PUT",    path, body),
  delete: (path)         => api._req("DELETE", path),
};

/* ── Toast Notifications ─────────────────────────────────────── */
function ensureToastContainer() {
  let c = document.getElementById("toast-container");
  if (!c) {
    c = document.createElement("div");
    c.id = "toast-container";
    c.className = "toast-container";
    document.body.appendChild(c);
  }
  return c;
}

function showToast(message, type = "info", duration = 3500) {
  const container = ensureToastContainer();
  const icons = { success: "check-circle", error: "x-circle", info: "info" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span><i data-lucide="${icons[type] || "info"}"></i></span><span>${message}</span>`;
  container.appendChild(toast);
  if (window.lucide) {
    window.lucide.createIcons();
  }
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.4s ease forwards";
    toast.addEventListener("animationend", () => toast.remove());
  }, duration);
}

/* ── Modal Helpers ───────────────────────────────────────────── */
function openModal(id) {
  document.getElementById(id)?.classList.add("open");
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove("open");
}

/* ── Sidebar Rendering ───────────────────────────────────────── */
function renderSidebar(role, activePage) {
  const user = Auth.getUser();
  if (!user) return;

  const navs = {
    teacher: [
      { icon: "layout-dashboard", label: "Dashboard",     href: "dashboard.html" },
      { icon: "book-open", label: "My Courses",    href: "dashboard.html" },
      { icon: "user", label: "Profile",       href: "profile.html" },
    ],
    student: [
      { icon: "layout-dashboard", label: "Dashboard",     href: "dashboard.html" },
      { icon: "book-open", label: "My Courses",    href: "dashboard.html" },
      { icon: "smile", label: "Face Enroll",   href: "enroll.html" },
      { icon: "user", label: "Profile",       href: "profile.html" },
    ],
    admin: [
      { icon: "layout-dashboard", label: "Dashboard",     href: "dashboard.html" },
      { icon: "users", label: "Users",         href: "users.html" },
      { icon: "book-open", label: "Courses",       href: "courses.html" },
      { icon: "calendar",  label: "Attendance",   href: "attendance_log.html" },
    ],
  };

  const links = navs[role] || [];
  const navHTML = links.map(n => `
    <a class="nav-link ${n.label === activePage ? "active" : ""}" href="${n.href}">
      <span class="nav-icon"><i data-lucide="${n.icon}"></i></span> ${n.label}
    </a>
  `).join("");

  const initials = user.name?.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  document.getElementById("sidebar-placeholder")?.insertAdjacentHTML("afterend", `
    <!-- Mobile top bar header -->
    <header class="mobile-header">
      <div class="mobile-logo">
        <div class="logo-icon">AX</div>
        <span class="logo-text">Attend<span>X</span></span>
      </div>
      <button class="menu-toggle" onclick="toggleSidebar(true)">
        <i data-lucide="menu"></i>
      </button>
    </header>

    <!-- Sidebar backdrop overlay -->
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar(false)"></div>

    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <div class="logo-icon">AX</div>
        <span class="logo-text">Attend<span>X</span></span>
      </div>
      <nav class="nav-section">
        <div class="nav-label">Navigation</div>
        ${navHTML}
      </nav>
      <div class="sidebar-footer">
        <div class="user-chip">
          <div class="avatar">${initials}</div>
          <div class="user-info">
            <div class="user-name">${user.name}</div>
            <div class="user-role">${user.role}</div>
          </div>
        </div>
        <button id="logoutBtn" class="btn btn-outline btn-sm btn-block" onclick="logout()"><i data-lucide="log-out"></i> Logout</button>
      </div>
    </aside>
  `);
  document.getElementById("sidebar-placeholder")?.remove();
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function toggleSidebar(open) {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  if (open) {
    sidebar?.classList.add("open");
    overlay?.classList.add("active");
  } else {
    sidebar?.classList.remove("open");
    overlay?.classList.remove("active");
  }
}

function logout() {
  Auth.clear();
  window.location.href = window.location.pathname.includes("/pages/") ? "../../index.html" : "index.html";
}

/* ── Attendance Ring ─────────────────────────────────────────── */
function createRing(pct, size = 100, strokeWidth = 8) {
  const r = (size / 2) - strokeWidth;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;
  const color = pct >= 75 ? "#0F9B58" : pct >= 50 ? "#FFB347" : "#FF4D6D";

  return `
    <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${r}"
        fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="${strokeWidth}"/>
      <circle cx="${size/2}" cy="${size/2}" r="${r}"
        fill="none" stroke="${color}" stroke-width="${strokeWidth}"
        stroke-linecap="round"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${offset}"
        transform="rotate(-90 ${size/2} ${size/2})"
        style="transition: stroke-dashoffset 1s ease"/>
    </svg>
  `;
}

/* ── Date Formatter ──────────────────────────────────────────── */
function fmtDate(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric"
  });
}

/* ── Export all ──────────────────────────────────────────────── */
window.Auth = Auth;
window.api = api;
window.showToast = showToast;
window.openModal = openModal;
window.closeModal = closeModal;
window.renderSidebar = renderSidebar;
window.toggleSidebar = toggleSidebar;
window.logout = logout;
window.createRing = createRing;
window.fmtDate = fmtDate;
window.USE_MOCK = USE_MOCK;
