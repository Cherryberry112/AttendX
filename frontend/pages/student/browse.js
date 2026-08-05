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
  
  tbody.innerHTML = availableCourses.map(c => {
    let actionBtn = "";
    if (c.request_status === "pending") {
      actionBtn = `<button class="btn btn-sm btn-outline" style="color:var(--danger); border-color:var(--danger);" onclick="cancelRequest(${c.id})">Cancel Request</button>`;
    } else {
      actionBtn = `<button class="btn btn-sm btn-primary" onclick="requestCourse(${c.id})">Request Enroll</button>`;
    }

    return `
    <tr>
      <td>${c.name}</td>
      <td>${c.section || 'N/A'}</td>
      <td>${c.teacher}</td>
      <td>
        ${actionBtn}
      </td>
    </tr>
  `}).join("");
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

async function cancelRequest(id) {
  try {
    await api.delete(`/student/requests/${id}/cancel`);
    showToast("Request cancelled", "success");
    await loadCourses();
  } catch (err) {
    showToast(err.message, "error");
  }
}
