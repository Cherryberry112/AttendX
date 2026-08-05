document.addEventListener("DOMContentLoaded", async () => {
  const user = Auth.getUser();
  if (!user || !Auth.guard()) return;
  
  renderSidebar(user.type, "Notifications");
  await loadNotifications();
});

async function loadNotifications() {
  const list = document.getElementById("notificationsList");
  try {
    const notifs = await api.get("/auth/notifications");
    if (!notifs || notifs.length === 0) {
      list.innerHTML = `<div class="empty-state">No notifications yet.</div>`;
      return;
    }

    const hasUnread = notifs.some(n => !n.is_read);

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

    if (hasUnread) {
      // Silently mark as read on the server
      api.post("/auth/notifications/read_all").catch(console.error);
      
      // Update sidebar badge immediately if present
      const badge = document.getElementById("notifBadge");
      if (badge) badge.style.display = "none";
    }
  } catch (err) {
    list.innerHTML = `<div class="empty-state" style="color:var(--danger)">Failed to load notifications.</div>`;
    showToast(err.message, "error");
  }
}
