document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.guard("admin")) return;
  renderSidebar("admin", "Requests");
  await loadRequests();
});

let currentRequests = [];

async function loadRequests() {
  const tbody = document.getElementById("requestsTable");
  try {
    currentRequests = await api.get("/admin/requests");
    renderTable();
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" style="color:var(--danger)">${err.message}</td></tr>`;
    showToast(err.message, "error");
  }
}

function renderTable() {
  const tbody = document.getElementById("requestsTable");
  if (!currentRequests.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;">No pending requests.</td></tr>`;
    return;
  }
  
  tbody.innerHTML = currentRequests.map(r => `
    <tr>
      <td>${r.user_name}</td>
      <td style="text-transform: capitalize;">${r.user_role}</td>
      <td>${r.course_name}</td>
      <td><span class="badge" style="background:#ffb347;color:#000;">Pending</span></td>
      <td>
        <button class="btn btn-sm btn-primary" onclick="approveReq(${r.id})">Approve</button>
        <button class="btn btn-sm btn-outline" style="color:var(--danger); border-color:var(--danger)" onclick="denyReq(${r.id})">Deny</button>
      </td>
    </tr>
  `).join("");
}

async function approveReq(id) {
  try {
    await api.post(`/admin/requests/${id}/approve`);
    showToast("Request approved", "success");
    await loadRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function denyReq(id) {
  try {
    await api.post(`/admin/requests/${id}/deny`);
    showToast("Request denied", "info");
    await loadRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}
