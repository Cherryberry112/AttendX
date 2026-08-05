document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.guard("teacher")) return;
  renderSidebar("teacher", "Browse Courses");
  await loadCourses();
});

let availableCourses = [];

async function loadCourses() {
  const tbody = document.getElementById("browseTable");
  try {
    availableCourses = await api.get("/teacher/courses/available");
    renderTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="3" style="color:var(--danger)">${err.message}</td></tr>`;
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("browseTable");
  if (!availableCourses.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="text-muted" style="text-align:center;">No available courses to teach.</td></tr>`;
    return;
  }
  
  tbody.innerHTML = availableCourses.map(c => `
    <tr>
      <td>${c.name}</td>
      <td>${c.section || 'N/A'}</td>
      <td>
        <button class="btn btn-sm btn-primary" onclick="requestCourse(${c.id})">Request to Teach</button>
      </td>
    </tr>
  `).join("");
}

async function requestCourse(id) {
  try {
    await api.post("/teacher/requests", { course_id: id });
    showToast("Teaching requested", "success");
    await loadCourses();
  } catch (err) {
    showToast(err.message, "error");
  }
}
