/**
 * StudyBot — Main Application
 * Handles routing, toast notifications, auth state, and global UI state.
 */

const App = (() => {
    async function init() {
        // Check authentication
        const token = localStorage.getItem('studybot_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Validate token is still valid
        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!res.ok) {
                localStorage.removeItem('studybot_token');
                localStorage.removeItem('studybot_user_name');
                localStorage.removeItem('studybot_user_email');
                window.location.href = '/login';
                return;
            }
        } catch (e) {
            window.location.href = '/login';
            return;
        }

        // Display user info
        displayUser();

        setupRouting();
        Chat.init();
        Upload.init();
        Scraper.init();
        Flashcards.init();
        Quiz.init();

        // Profile click → navigate to profile page
        document.getElementById('profile-toggle').addEventListener('click', () => {
            navigateTo('profile');
        });

        // Logout button
        document.getElementById('logout-btn').addEventListener('click', logout);

        // Save profile button
        document.getElementById('profile-save-btn').addEventListener('click', saveProfile);

        // Navigate to initial page
        const hash = window.location.hash.slice(1) || 'chat';
        navigateTo(hash);
    }

    function displayUser() {
        const name = localStorage.getItem('studybot_user_name') || 'User';
        const email = localStorage.getItem('studybot_user_email') || '';

        const nameEl = document.getElementById('user-display-name');
        if (nameEl) nameEl.textContent = name;

        // Also populate profile page fields
        const profileName = document.getElementById('profile-name');
        const profileEmail = document.getElementById('profile-email');
        if (profileName) profileName.value = name;
        if (profileEmail) profileEmail.value = email;
    }

    function logout() {
        localStorage.removeItem('studybot_token');
        localStorage.removeItem('studybot_user_name');
        localStorage.removeItem('studybot_user_email');
        window.location.href = '/login';
    }

    function saveProfile() {
        const newName = document.getElementById('profile-name').value.trim();
        if (newName) {
            localStorage.setItem('studybot_user_name', newName);
            displayUser();
            showToast('Profile updated!', 'success');
        }
    }

    // ── Routing ────────────────────────────────────────
    function setupRouting() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                const currentHash = window.location.hash.slice(1) || 'chat';

                // If they click 'chat' while already on 'chat', start a new session
                if (page === 'chat' && currentHash === 'chat') {
                    if (typeof Chat !== 'undefined' && Chat.clearChat) {
                        Chat.clearChat();
                    }
                }

                navigateTo(page);
            });
        });

        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.slice(1) || 'chat';
            navigateTo(hash);
        });
    }

    function navigateTo(page) {
        // Update URL hash
        window.location.hash = page;

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        const activeLink = document.querySelector(`.nav-link[data-page="${page}"]`);
        if (activeLink) activeLink.classList.add('active');

        // Show page
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const activePage = document.getElementById(`page-${page}`);
        if (activePage) activePage.classList.add('active');

        // Refresh data on navigation
        if (page === 'upload') Upload.loadDocuments();
        if (page === 'flashcards') Flashcards.loadDecks();
        if (page === 'quiz') Quiz.loadHistory();
        if (page === 'profile') displayUser();
    }

    // ── Toast Notifications ────────────────────────────
    function showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icon = type === 'success' ? 'fa-check-circle'
            : type === 'error' ? 'fa-exclamation-circle'
                : 'fa-info-circle';

        toast.innerHTML = `<i class="fas ${icon}"></i><span>${escapeHtml(message)}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3500);
    }

    // ── Loading Overlay ────────────────────────────────
    function showLoading(text = 'Processing...') {
        document.getElementById('loading-text').textContent = text;
        document.getElementById('loading-overlay').style.display = 'flex';
    }

    function hideLoading() {
        document.getElementById('loading-overlay').style.display = 'none';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, navigateTo, showToast, showLoading, hideLoading };
})();

// Boot
document.addEventListener('DOMContentLoaded', App.init);
