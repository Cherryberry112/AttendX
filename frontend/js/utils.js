/* ============================================================
   AttendX — API Client & Shared JS Utilities
   Updated for new 3-table schema (users, courses, attendance)
   ============================================================ */

const USE_MOCK = window.location.search.includes("mock=true");

const API_BASE = window.location.protocol === "file:" || window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
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
  guard: (requiredType) => {
    const user = Auth.getUser();
    const token = Auth.getToken();
    if (!user || !token) {
      Auth.clear();
      window.location.href = window.location.pathname.includes("/pages/") ? "../../index.html" : "index.html";
      return false;
    }
    const userType = (user.type || user.role || "").toLowerCase();
    if (requiredType && userType !== requiredType.toLowerCase()) {
      Auth.clear();
      window.location.href = window.location.pathname.includes("/pages/") ? "../../index.html" : "index.html";
      return false;
    }
    return true;
  },
};

/* ── Mock Database Setup ────────────────────────────────────── */
if (USE_MOCK) {
  const initDb = () => {
    if (localStorage.getItem("ax_mock_version") !== "v3_user_data") {
      localStorage.removeItem("ax_mock_users");
      localStorage.removeItem("ax_mock_courses");
      localStorage.removeItem("ax_mock_attendance");
      localStorage.setItem("ax_mock_version", "v3_user_data");
    }
    if (!localStorage.getItem("ax_mock_users")) {
      const defaultUsers = [
        { id: 1, username: "admin_boss", email: "admin@example.com", password: "1234", type: "admin", phone: "+8801700000000", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 2, username: "adnan_sir", email: "adnan@example.com", password: "1234", type: "teacher", phone: "+8801711111111", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 3, username: "tanvir_sir", email: "tanvir@example.com", password: "1234", type: "teacher", phone: "+8801711111112", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 4, username: "farhana_maam", email: "farhana@example.com", password: "1234", type: "teacher", phone: "+8801711111113", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 5, username: "rahim_sir", email: "rahim@example.com", password: "1234", type: "teacher", phone: "+8801711111114", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 6, username: "nusrat_maam", email: "nusrat@example.com", password: "1234", type: "teacher", phone: "+8801711111115", student_id: null, guardian_number: null, face_embedding: null, created_at: new Date().toISOString() },
        { id: 7, username: "mohua", email: "mohua@example.com", password: "1234", type: "student", phone: "+8801811111101", student_id: "2022-3-60-110", guardian_number: "+8801911111101", face_embedding: null, created_at: new Date().toISOString() },
        { id: 8, username: "kabira", email: "kabira@example.com", password: "1234", type: "student", phone: "+8801811111102", student_id: "2022-3-60-111", guardian_number: "+8801911111102", face_embedding: null, created_at: new Date().toISOString() },
        { id: 9, username: "priya", email: "priya@example.com", password: "1234", type: "student", phone: "+8801811111103", student_id: "2022-3-60-112", guardian_number: "+8801911111103", face_embedding: null, created_at: new Date().toISOString() },
        { id: 10, username: "mim", email: "mim@example.com", password: "1234", type: "student", phone: "+8801811111104", student_id: "2022-3-60-113", guardian_number: "+8801911111104", face_embedding: null, created_at: new Date().toISOString() },
        { id: 11, username: "arman", email: "arman@example.com", password: "1234", type: "student", phone: "+8801811111105", student_id: "2022-3-60-114", guardian_number: "+8801911111105", face_embedding: null, created_at: new Date().toISOString() },
        { id: 12, username: "sifat", email: "sifat@example.com", password: "1234", type: "student", phone: "+8801811111106", student_id: "2022-3-60-115", guardian_number: "+8801911111106", face_embedding: null, created_at: new Date().toISOString() },
        { id: 13, username: "tanila", email: "tanila@example.com", password: "1234", type: "student", phone: "+8801811111107", student_id: "2022-3-60-116", guardian_number: "+8801911111107", face_embedding: null, created_at: new Date().toISOString() },
        { id: 14, username: "fardin", email: "fardin@example.com", password: "1234", type: "student", phone: "+8801811111108", student_id: "2022-3-60-117", guardian_number: "+8801911111108", face_embedding: null, created_at: new Date().toISOString() },
        { id: 15, username: "sadia", email: "sadia@example.com", password: "1234", type: "student", phone: "+8801811111109", student_id: "2022-3-60-118", guardian_number: "+8801911111109", face_embedding: null, created_at: new Date().toISOString() },
        { id: 16, username: "nabil", email: "nabil@example.com", password: "1234", type: "student", phone: "+8801811111110", student_id: "2022-3-60-119", guardian_number: "+8801911111110", face_embedding: null, created_at: new Date().toISOString() },
      ];
      localStorage.setItem("ax_mock_users", JSON.stringify(defaultUsers));
    }
    if (!localStorage.getItem("ax_mock_courses")) {
      const defaultCourses = [
        { id: 101, name: "Web Development Fundamentals", teacher_id: 2, student_ids: [7, 8, 9, 10, 11] },
        { id: 102, name: "Data Science for Beginners", teacher_id: 3, student_ids: [7, 8, 12, 13] },
        { id: 103, name: "Digital Marketing Mastery", teacher_id: 4, student_ids: [9, 10, 14, 15] },
        { id: 104, name: "Python for Everybody", teacher_id: 2, student_ids: [7, 11, 12, 16] },
        { id: 105, name: "Graphic Design Essentials", teacher_id: 6, student_ids: [8, 13, 14, 15] },
        { id: 106, name: "Mobile App Development", teacher_id: 2, student_ids: [9, 10, 11, 16] },
        { id: 107, name: "AI and Machine Learning", teacher_id: 3, student_ids: [7, 8, 12, 13] },
        { id: 108, name: "Cybersecurity Fundamentals", teacher_id: 5, student_ids: [14, 15, 16] },
        { id: 109, name: "UX/UI Design Principles", teacher_id: 6, student_ids: [9, 10, 13, 15] },
        { id: 110, name: "Blockchain Essentials", teacher_id: 5, student_ids: [7, 11, 12, 16] },
      ];
      localStorage.setItem("ax_mock_courses", JSON.stringify(defaultCourses));
    }
    if (!localStorage.getItem("ax_mock_attendance")) {
      const defaultAttendance = [
        { id: 1, date: "2026-07-20", student_id: 7, course_id: 101 },
        { id: 2, date: "2026-07-20", student_id: 8, course_id: 101 },
        { id: 3, date: "2026-07-20", student_id: 9, course_id: 101 },
        { id: 4, date: "2026-07-20", student_id: 10, course_id: 101 },
        { id: 5, date: "2026-07-21", student_id: 7, course_id: 104 },
        { id: 6, date: "2026-07-21", student_id: 11, course_id: 104 },
        { id: 7, date: "2026-07-21", student_id: 12, course_id: 104 },
        { id: 8, date: "2026-07-22", student_id: 7, course_id: 107 },
        { id: 9, date: "2026-07-22", student_id: 8, course_id: 107 },
        { id: 10, date: "2026-07-22", student_id: 12, course_id: 107 },
      ];
      localStorage.setItem("ax_mock_attendance", JSON.stringify(defaultAttendance));
    }
  };
  initDb();
}

const getMockDb = (key) => JSON.parse(localStorage.getItem(key)) || [];
const setMockDb = (key, val) => localStorage.setItem(key, JSON.stringify(val));

const handleMockRequest = async (method, path, body) => {
  await new Promise(r => setTimeout(r, 250));

  let users = getMockDb("ax_mock_users");
  let courses = getMockDb("ax_mock_courses");
  let attendance = getMockDb("ax_mock_attendance");
  const currentUser = Auth.getUser();

  // ── Auth ──────────────────────────────────────────────────
  if (method === "POST" && path === "/auth/login") {
    const user = users.find(u => u.email.toLowerCase() === body.email.toLowerCase());
    if (!user || user.password !== body.password) throw new Error("Invalid email or password");
    return { token: "mock-jwt-token-" + user.id, id: user.id, username: user.username, type: user.type };
  }

  if (method === "POST" && path === "/auth/register") {
    if (users.some(u => u.email.toLowerCase() === body.email.toLowerCase())) throw new Error("Email already registered");
    if (body.type === "student") {
      if (!body.student_id) throw new Error("Student ID is required for students");
      const sidRegex = /^\d{4}-\d{1,2}-\d{2}-\d{3}$/;
      if (!sidRegex.test(body.student_id)) throw new Error("Student ID must be in format YYYY-D-DD-DDD (e.g. 2022-3-60-110)");
      if (users.some(u => u.student_id === body.student_id)) throw new Error("Student ID already exists");
    }
    const newId = users.length ? Math.max(...users.map(u => u.id)) + 1 : 1;
    const newUser = {
      id: newId, username: body.username, email: body.email, password: body.password || "password",
      type: body.type, phone: body.phone || null, student_id: body.student_id || null,
      guardian_number: body.guardian_number || null, face_embedding: null,
      created_at: new Date().toISOString(),
    };
    users.push(newUser);
    setMockDb("ax_mock_users", users);
    return { message: "User registered successfully", id: newId };
  }

  if (method === "GET" && path === "/auth/me") {
    const u = users.find(x => x.id === currentUser.id);
    if (!u) throw new Error("User not found");
    return { id: u.id, username: u.username, email: u.email, type: u.type, phone: u.phone, student_id: u.student_id, guardian_number: u.guardian_number };
  }

  // ── Teacher Profile ───────────────────────────────────────
  if (method === "GET" && path === "/teacher/profile") {
    const u = users.find(x => x.id === currentUser.id);
    if (!u) throw new Error("Teacher profile not found");
    const tCourses = courses.filter(c => c.teacher_id === u.id);
    return { id: u.id, username: u.username, email: u.email, phone: u.phone || "—", total_courses: tCourses.length };
  }

  if (method === "PUT" && path === "/teacher/profile") {
    const idx = users.findIndex(x => x.id === currentUser.id);
    if (idx === -1) throw new Error("Teacher profile not found");
    if (body.username) users[idx].username = body.username;
    if (body.phone) users[idx].phone = body.phone;
    setMockDb("ax_mock_users", users);
    currentUser.username = users[idx].username;
    Auth.setUser(currentUser);
    return { message: "Profile updated" };
  }

  // ── Teacher Courses (Read-Only) ───────────────────────────
  if (method === "GET" && path === "/teacher/courses") {
    const tCourses = courses.filter(c => c.teacher_id === currentUser.id);
    return tCourses.map(c => {
      const enrolled = c.student_ids ? c.student_ids.length : 0;
      const dates = [...new Set(attendance.filter(a => a.course_id === c.id).map(a => a.date))];
      return { id: c.id, name: c.name, enrolled, total_classes: dates.length };
    });
  }

  if (method === "GET" && path.match(/^\/teacher\/courses\/\d+$/)) {
    const courseId = parseInt(path.split("/")[3]);
    const course = courses.find(c => c.id === courseId);
    if (!course) throw new Error("Course not found");

    const students = (course.student_ids || []).map(sid => {
      const u = users.find(x => x.id === sid);
      return { id: sid, student_id: u ? u.student_id : "N/A", username: u ? u.username : "Unknown", face_enrolled: u ? !!u.face_embedding : false };
    });

    const dateMap = {};
    attendance.filter(a => a.course_id === courseId).forEach(a => {
      dateMap[a.date] = (dateMap[a.date] || 0) + 1;
    });
    const total = students.length;
    const sessions = Object.entries(dateMap).sort(([a],[b]) => b.localeCompare(a)).map(([date, present]) => ({ date, present, total }));

    return { course: { id: course.id, name: course.name }, students, sessions };
  }

  // ── Teacher Attendance ────────────────────────────────────
  if (method === "POST" && path.match(/^\/teacher\/courses\/\d+\/attendance$/)) {
    const courseId = parseInt(path.split("/")[3]);
    const course = courses.find(c => c.id === courseId);
    if (!course) throw new Error("Course not found");
    const att_date = body.date || new Date().toISOString().split("T")[0];
    let recorded = 0;
    (body.present_ids || []).forEach(sid => {
      if (!(course.student_ids || []).includes(sid)) return;
      const exists = attendance.find(a => a.date === att_date && a.student_id === sid && a.course_id === courseId);
      if (!exists) {
        const newId = attendance.length ? Math.max(...attendance.map(a => a.id)) + 1 : 1;
        attendance.push({ id: newId, date: att_date, student_id: sid, course_id: courseId });
        recorded++;
      }
    });
    setMockDb("ax_mock_attendance", attendance);
    return { message: `Attendance recorded: ${recorded} students`, recorded };
  }

  // ── Face scan (mock) ──────────────────────────────────────
  if (method === "POST" && path === "/face/scan") {
    const courseId = parseInt(body.course_id);
    const course = courses.find(c => c.id === courseId);
    if (!course) throw new Error("Course not found");
    const matches = [];
    (course.student_ids || []).forEach(sid => {
      const u = users.find(x => x.id === sid);
      if (u && u.face_embedding && Math.random() > 0.15) {
        matches.push({
          bbox: [200+Math.random()*20, 150+Math.random()*20, 400+Math.random()*20, 350+Math.random()*20],
          student_id: sid, name: u.username, confidence: parseFloat((0.88 + Math.random()*0.1).toFixed(3)),
        });
      }
    });
    return { matches };
  }

  if (method === "POST" && path === "/face/enroll") {
    const idx = users.findIndex(x => x.id === currentUser.id);
    if (idx === -1) throw new Error("User not found");
    users[idx].face_embedding = "enrolled";
    setMockDb("ax_mock_users", users);
    return { message: "Face enrolled successfully" };
  }

  // ── Student Profile ───────────────────────────────────────
  if (method === "GET" && path === "/student/profile") {
    const u = users.find(x => x.id === currentUser.id);
    if (!u) throw new Error("Student profile not found");
    const sCourses = courses.filter(c => c.student_ids && c.student_ids.includes(u.id));
    return {
      id: u.id, username: u.username, email: u.email, student_id: u.student_id || "—",
      phone: u.phone, guardian_number: u.guardian_number, face_enrolled: !!u.face_embedding,
      total_courses: sCourses.length,
    };
  }

  if (method === "GET" && path === "/student/courses") {
    const sCourses = courses.filter(c => c.student_ids && c.student_ids.includes(currentUser.id));
    return sCourses.map(c => {
      const t = users.find(x => x.id === c.teacher_id);
      const allDates = [...new Set(attendance.filter(a => a.course_id === c.id).map(a => a.date))];
      const total_classes = allDates.length;
      const attended = attendance.filter(a => a.course_id === c.id && a.student_id === currentUser.id).length;
      const percentage = total_classes ? Math.round(attended / total_classes * 100) : 0;
      return { id: c.id, name: c.name, teacher: t ? t.username : "N/A", total_classes, attended, percentage };
    });
  }

  // ── Admin Stats ───────────────────────────────────────────
  if (method === "GET" && path === "/admin/stats") {
    return {
      total_users: users.length,
      total_students: users.filter(u => u.type === "student").length,
      total_teachers: users.filter(u => u.type === "teacher").length,
      total_courses: courses.length,
      total_attendance: attendance.length,
    };
  }

  // ── Admin Users ───────────────────────────────────────────
  if (method === "GET" && path === "/admin/users") {
    return users.map(u => ({
      id: u.id, username: u.username, email: u.email, type: u.type,
      student_id: u.student_id, phone: u.phone, guardian_number: u.guardian_number,
      created_at: u.created_at || new Date().toISOString(),
    }));
  }

  if (method === "PUT" && path.match(/^\/admin\/users\/\d+$/)) {
    const userId = parseInt(path.split("/")[3]);
    const idx = users.findIndex(u => u.id === userId);
    if (idx === -1) throw new Error("User not found");
    if (body.username) users[idx].username = body.username;
    if (body.email) users[idx].email = body.email;
    if (body.phone !== undefined) users[idx].phone = body.phone;
    if (body.student_id !== undefined) users[idx].student_id = body.student_id;
    if (body.guardian_number !== undefined) users[idx].guardian_number = body.guardian_number;
    if (body.password) users[idx].password = body.password;
    setMockDb("ax_mock_users", users);
    return { message: "User updated" };
  }

  if (method === "DELETE" && path.match(/^\/admin\/users\/\d+$/)) {
    const idToDelete = parseInt(path.split("/")[3]);
    if (idToDelete === currentUser.id) throw new Error("Cannot delete currently logged in user!");
    const idx = users.findIndex(u => u.id === idToDelete);
    if (idx === -1) throw new Error("User not found");
    users.splice(idx, 1);
    setMockDb("ax_mock_users", users);
    courses.forEach(c => {
      if (c.student_ids) c.student_ids = c.student_ids.filter(sid => sid !== idToDelete);
      if (c.teacher_id === idToDelete) c.teacher_id = null;
    });
    setMockDb("ax_mock_courses", courses);
    return { message: "User deleted successfully" };
  }

  // ── Admin Courses ─────────────────────────────────────────
  if (method === "GET" && path === "/admin/courses") {
    return courses.map(c => {
      const t = users.find(x => x.id === c.teacher_id);
      return { id: c.id, name: c.name, teacher: t ? t.username : "Unassigned", teacher_id: c.teacher_id, enrolled: c.student_ids ? c.student_ids.length : 0 };
    });
  }

  if (method === "POST" && path === "/admin/courses") {
    const newId = courses.length ? Math.max(...courses.map(c => c.id)) + 1 : 101;
    const newCourse = { id: newId, name: body.name, teacher_id: body.teacher_id || null, student_ids: body.student_ids || [] };
    courses.push(newCourse);
    setMockDb("ax_mock_courses", courses);
    return { message: "Course created", id: newId };
  }

  if (method === "PUT" && path.match(/^\/admin\/courses\/\d+$/)) {
    const courseId = parseInt(path.split("/")[3]);
    const idx = courses.findIndex(c => c.id === courseId);
    if (idx === -1) throw new Error("Course not found");
    if (body.name !== undefined) courses[idx].name = body.name;
    if (body.teacher_id !== undefined) courses[idx].teacher_id = body.teacher_id;
    if (body.student_ids !== undefined) courses[idx].student_ids = body.student_ids;
    setMockDb("ax_mock_courses", courses);
    return { message: "Course updated" };
  }

  if (method === "DELETE" && path.match(/^\/admin\/courses\/\d+$/)) {
    const idToDelete = parseInt(path.split("/")[3]);
    const idx = courses.findIndex(c => c.id === idToDelete);
    if (idx === -1) throw new Error("Course not found");
    courses.splice(idx, 1);
    setMockDb("ax_mock_courses", courses);
    const newAtt = attendance.filter(a => a.course_id !== idToDelete);
    setMockDb("ax_mock_attendance", newAtt);
    return { message: "Course deleted successfully" };
  }

  // ── Admin Attendance Log ──────────────────────────────────
  if (method === "GET" && path === "/admin/attendance") {
    return attendance.sort((a, b) => b.date.localeCompare(a.date)).map(a => {
      const student = users.find(u => u.id === a.student_id);
      const course = courses.find(c => c.id === a.course_id);
      const teacher = course ? users.find(u => u.id === course.teacher_id) : null;
      return {
        id: a.id, date: a.date,
        student_name: student ? student.username : "Unknown",
        student_id: student ? student.student_id : "N/A",
        course: course ? course.name : "N/A",
        teacher: teacher ? teacher.username : "N/A",
      };
    });
  }

  throw new Error("API Route " + method + " " + path + " not found in mock db");
};

/* ── API Fetch Wrapper ───────────────────────────────────────── */
const api = {
  _req: async (method, path, body = null) => {
    if (USE_MOCK) return handleMockRequest(method, path, body);
    const token = Auth.getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API_BASE}${path}`, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (res.status === 401) {
        Auth.clear();
      }
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  },
  get:    (path)       => api._req("GET",    path),
  post:   (path, body) => api._req("POST",   path, body),
  put:    (path, body) => api._req("PUT",    path, body),
  delete: (path)       => api._req("DELETE", path),
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
  if (window.lucide) window.lucide.createIcons();
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.4s ease forwards";
    toast.addEventListener("animationend", () => toast.remove());
  }, duration);
}

/* ── Modal Helpers ───────────────────────────────────────────── */
function openModal(id) { document.getElementById(id)?.classList.add("open"); }
function closeModal(id) { document.getElementById(id)?.classList.remove("open"); }

/* ── Sidebar Rendering ───────────────────────────────────────── */
function renderSidebar(role, activePage) {
  const user = Auth.getUser();
  if (!user) return;

  const navs = {
    teacher: [
      { icon: "layout-dashboard", label: "Dashboard",   href: "dashboard.html" },
      { icon: "book-open",        label: "My Courses",  href: "dashboard.html" },
      { icon: "user",             label: "Profile",     href: "profile.html" },
    ],
    student: [
      { icon: "layout-dashboard", label: "Dashboard",   href: "dashboard.html" },
      { icon: "book-open",        label: "My Courses",  href: "dashboard.html" },
      { icon: "smile",            label: "Face Enroll", href: "enroll.html" },
      { icon: "user",             label: "Profile",     href: "profile.html" },
    ],
    admin: [
      { icon: "layout-dashboard", label: "Dashboard",   href: "dashboard.html" },
      { icon: "users",            label: "Users",       href: "users.html" },
      { icon: "book-open",        label: "Courses",     href: "courses.html" },
      { icon: "calendar",         label: "Attendance",  href: "attendance_log.html" },
    ],
  };

  const links = navs[role] || [];
  const navHTML = links.map(n => `
    <a class="nav-link ${n.label === activePage ? "active" : ""}" href="${n.href}">
      <span class="nav-icon"><i data-lucide="${n.icon}"></i></span> ${n.label}
    </a>
  `).join("");

  const displayName = user.username || user.name || "User";
  const initials = displayName.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

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
            <div class="user-name">${displayName}</div>
            <div class="user-role">${user.type || user.role}</div>
          </div>
        </div>
        <button id="logoutBtn" class="btn btn-outline btn-sm btn-block" onclick="logout()"><i data-lucide="log-out"></i> Logout</button>
      </div>
    </aside>
  `);
  document.getElementById("sidebar-placeholder")?.remove();
  if (window.lucide) window.lucide.createIcons();
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
