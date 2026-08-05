document.addEventListener("DOMContentLoaded", async () => {
  const user = Auth.getUser();
  if (!user || !Auth.guard()) return;
  
  renderSidebar(user.type, "Notifications");
  await loadNotifications();
});

async function loadNotifications() {
  const list = document.getElementById("notificationsList");
  const markBtn = document.getElementById("markReadBtn");
  try {
    const notifs = await api.get("/notifications");
    if (!notifs || notifs.length === 0) {
      list.innerHTML = `<div class="empty-state">No notifications yet.</div>`;
      markBtn.style.display = "none";
      return;
    }

    const hasUnread = notifs.some(n => !n.is_read);
    markBtn.style.display = hasUnread ? "block" : "none";

    list.innerHTML = notifs.map(n => `
      <div class="notification-item ${n.is_read ? '' : 'unread'}">
        <div class="notif-icon">
          <i data-lucide="${n.is_read ? 'bell' : 'bell-ring'}"></i>
        </div>
        <div class="notif-content">
          <div class="notif-message">${n.message}</div>
          <div class="notif-time">${fmtDate(n.created_at)}</div>
        </div>
      </div>
    `).join("");

    if (window.lucide) window.lucide.createIcons();
  } catch (err) {
    list.innerHTML = `<div class="empty-state" style="color:#ff4d6d">Failed to load notifications.</div>`;
    showToast(err.message, "error");
  }
}

async function markAllAsRead() {
  try {
    await api.post("/notifications/read_all");
    showToast("Notifications marked as read", "success");
    await loadNotifications();
  } catch (err) {
    showToast(err.message, "error");
  }
}
