document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.guard("student")) return;
  renderSidebar("student", "Browse Courses");
  await loadCourses();
});

let availableCourses = [];

async function loadCourses() {
  const tbody = document.getElementById("browseTable");
  try {
    availableCourses = await api.get("/student/courses/available");
    renderTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="color:var(--danger)">${err.message}</td></tr>`;
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("browseTable");
  if (!availableCourses.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-muted" style="text-align:center;">No available courses to request.</td></tr>`;
    return;
  }
  
  tbody.innerHTML = availableCourses.map(c => `
    <tr>
      <td>${c.name}</td>
      <td>${c.section || 'N/A'}</td>
      <td>${c.teacher}</td>
      <td>
        <button class="btn btn-sm btn-primary" onclick="requestCourse(${c.id})">Request Enroll</button>
      </td>
    </tr>
  `).join("");
}

async function requestCourse(id) {
  try {
    await api.post("/student/requests", { course_id: id });
    showToast("Enrollment requested", "success");
    await loadCourses();
  } catch (err) {
    showToast(err.message, "error");
  }
}
