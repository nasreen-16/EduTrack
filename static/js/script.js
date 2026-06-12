// Sidebar toggle on mobile
const toggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');

if (toggle && sidebar) {
  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 &&
        !sidebar.contains(e.target) &&
        !toggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

// Confirm delete helper
function confirmDelete(name) {
  return confirm(`Delete student "${name}" and all their records? This cannot be undone.`);
}

// Auto-dismiss alerts after 4s
document.querySelectorAll('.custom-alert').forEach(alert => {
  setTimeout(() => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
    if (bsAlert) bsAlert.close();
  }, 4000);
});