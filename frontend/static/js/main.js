/**
 * Pickle Legends Admin Platform - Core Frontend Script
 * Handles navigation, interactive AJAX actions, profile inspector, court grid toggles, and modals.
 */

function getCsrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Toast Notifications System
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || (() => {
    const el = document.createElement('div');
    el.id = 'toast-container';
    el.className = 'fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-50 pointer-events-none flex flex-col space-y-2';
    document.body.appendChild(el);
    return el;
  })();

  const toast = document.createElement('div');
  const bgColor = type === 'success' ? 'bg-emerald-600' : (type === 'danger' ? 'bg-rose-600' : 'bg-indigo-600');
  
  toast.className = `${bgColor} text-white px-4 py-3 rounded-2xl shadow-xl flex items-center space-x-3 transition-all duration-300 transform translate-y-2 opacity-0 text-xs sm:text-sm font-semibold pointer-events-auto border border-white/20`;
  toast.innerHTML = `
    <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
    </svg>
    <span class="flex-1">${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Mobile Sidebar Toggle
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('mobileSidebarToggle');
  const overlay = document.getElementById('sidebarOverlay');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('-translate-x-full');
      if (overlay) overlay.classList.toggle('hidden');
    });
  }

  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.add('-translate-x-full');
      overlay.classList.add('hidden');
    });
  }

  // Close mobile sidebar when clicking a nav link
  if (sidebar) {
    sidebar.querySelectorAll('nav a').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth < 768) {
          sidebar.classList.add('-translate-x-full');
          if (overlay) overlay.classList.add('hidden');
        }
      });
    });
  }
});


// Quick Admin Actions (Executive Dashboard)
async function triggerQuickAction(actionType, customPayload = {}) {
  try {
    let endpoint = `/api/action/${actionType}`;
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(customPayload)
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
    } else {
      showToast(data.message || 'Action failed.', 'danger');
    }
  } catch (err) {
    console.error(err);
    showToast('Network error triggering admin action.', 'danger');
  }
}

// User Profile Inspector Selection & Filter Logic
function selectPlayer(playerJson) {
  const player = typeof playerJson === 'string' ? JSON.parse(playerJson) : playerJson;
  const inspector = document.getElementById('profileInspector');
  if (!inspector) return;

  document.getElementById('inspPlayerId').innerText = player.id;
  document.getElementById('inspPlayerName').innerText = player.name;
  document.getElementById('inspElo').innerText = player.elo;
  document.getElementById('inspTier').innerText = player.tier;
  document.getElementById('inspWinRate').innerText = player.win_rate;
  document.getElementById('inspMatches').innerText = player.matches;
  document.getElementById('inspStatus').innerText = player.status;
  document.getElementById('inspNotes').innerText = player.notes || 'No notes available.';

  const avatarLetter = document.getElementById('inspAvatarLetter');
  if (avatarLetter && player.name) {
    avatarLetter.innerText = player.name.charAt(0).toUpperCase();
  }

  // Highlight status badge color
  const statusBadge = document.getElementById('inspStatus');
  statusBadge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold ' + (
    player.status === 'Active' ? 'bg-emerald-100 text-emerald-800' :
    player.status === 'Frozen' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
  );

  // Set active row highlight
  document.querySelectorAll('.player-row').forEach(row => row.classList.remove('bg-indigo-50/70', 'border-l-4', 'border-indigo-600'));
  const selectedRow = document.getElementById(`row-${player.id}`);
  if (selectedRow) selectedRow.classList.add('bg-indigo-50/70', 'border-l-4', 'border-indigo-600');

  // Smooth scroll to inspector on mobile screens
  if (window.innerWidth < 1024) {
    inspector.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}


async function performPlayerAction(action) {
  const playerId = document.getElementById('inspPlayerId').innerText;
  if (!playerId || playerId === '-') {
    showToast('Please select a player first.', 'info');
    return;
  }

  try {
    const res = await fetch(`/api/users/${playerId}/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      if (data.status) {
        document.getElementById('inspStatus').innerText = data.status;
        const rowStatus = document.getElementById(`status-${playerId}`);
        if (rowStatus) {
          rowStatus.innerText = data.status;
          rowStatus.className = 'px-2.5 py-1 rounded-full text-xs font-semibold ' + (
            data.status === 'Active' ? 'bg-emerald-100 text-emerald-800' :
            data.status === 'Frozen' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
          );
        }
      }
      if (data.elo !== undefined) {
        document.getElementById('inspElo').innerText = data.elo;
        const rowElo = document.getElementById(`elo-${playerId}`);
        if (rowElo) rowElo.innerText = data.elo;
      }
    } else {
      showToast(data.message || 'Player action failed.', 'danger');
    }
  } catch (err) {
    showToast('Failed to connect to backend server.', 'danger');
  }
}

// User Search & Filter Handler
function filterPlayers() {
  const query = document.getElementById('userSearchInput')?.value.toLowerCase() || '';
  const tierFilter = document.getElementById('tierFilterSelect')?.value || 'ALL';
  const statusFilter = document.getElementById('statusFilterSelect')?.value || 'ALL';

  document.querySelectorAll('.player-row').forEach(row => {
    const name = row.getAttribute('data-name').toLowerCase();
    const id = row.getAttribute('data-id').toLowerCase();
    const tier = row.getAttribute('data-tier');
    const status = row.getAttribute('data-status');

    const matchesSearch = name.includes(query) || id.includes(query);
    const matchesTier = tierFilter === 'ALL' || tier === tierFilter;
    const matchesStatus = statusFilter === 'ALL' || status === statusFilter;

    if (matchesSearch && matchesTier && matchesStatus) {
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  });
}

// Moderation Actions
async function handleReportAction(reportId, action) {
  try {
    const res = await fetch('/api/moderation/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id: reportId, action })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, 'success');
      const card = document.getElementById(`report-card-${reportId}`);
      if (card) {
        card.style.transition = 'all 0.3s ease';
        card.style.opacity = '0';
        setTimeout(() => card.remove(), 300);
      }
    } else {
      showToast(data.message || 'Error processing report.', 'danger');
    }
  } catch (err) {
    showToast('Error handling moderation report.', 'danger');
  }
}



