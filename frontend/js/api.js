/**
 * StudyBot — API Client
 * Centralized fetch wrapper for all backend endpoints.
 */

const API = {
    BASE: '',

    _getToken() {
        return localStorage.getItem('studybot_token') || '';
    },

    async _request(url, options = {}) {
        const token = this._getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(this.BASE + url, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            // Token expired or invalid — redirect to login
            localStorage.removeItem('studybot_token');
            localStorage.removeItem('studybot_user_name');
            localStorage.removeItem('studybot_user_email');
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    },

    // ── Auth ───────────────────────────────────────────────
    async signup(name, email, password) {
        const response = await fetch(this.BASE + '/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Signup failed' }));
            throw new Error(error.detail);
        }
        return response.json();
    },

    async login(email, password) {
        const response = await fetch(this.BASE + '/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail);
        }
        return response.json();
    },

    async getMe() {
        return this._request('/api/auth/me');
    },

    // ── Chat ───────────────────────────────────────────
    async chat(message, mode, sessionId = 'default') {
        const payload = {
            message,
            mode,
            session_id: sessionId
        };
        return this._request('/api/chat', {
            method: 'POST',
            body: JSON.stringify(payload),
        });
    },

    async clearChat() {
        return this._request('/api/chat/clear', { method: 'POST' });
    },

    async getChatHistory() {
        return this._request('/api/chat/history');
    },

    // ── Documents ──────────────────────────────────────
    async uploadDocument(file) {
        const token = this._getToken();
        const formData = new FormData();
        formData.append('file', file);
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(this.BASE + '/api/upload', {
            method: 'POST',
            headers,
            body: formData,
        });
        if (response.status === 401) {
            localStorage.removeItem('studybot_token');
            window.location.href = '/login';
            return;
        }
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(error.detail || 'Upload failed');
        }
        return response.json();
    },

    async listDocuments() {
        return this._request('/api/documents');
    },

    async deleteDocument(docId) {
        return this._request(`/api/documents/${docId}`, { method: 'DELETE' });
    },

    // ── Web Research ───────────────────────────────────
    async scrape(topic, maxResults = 3) {
        return this._request('/api/scrape', {
            method: 'POST',
            body: JSON.stringify({ topic, max_results: maxResults }),
        });
    },

    async addToKnowledgeBase(content, sourceName) {
        return this._request('/api/scrape/add-to-kb', {
            method: 'POST',
            body: JSON.stringify({ content, source_name: sourceName }),
        });
    },

    // ── Flashcards ─────────────────────────────────────
    async generateFlashcards({ topic, text, title, count }) {
        return this._request('/api/flashcards/generate', {
            method: 'POST',
            body: JSON.stringify({ topic, text, title, count }),
        });
    },

    async listFlashcardDecks() {
        return this._request('/api/flashcards');
    },

    async getFlashcardDeck(deckId) {
        return this._request(`/api/flashcards/${deckId}`);
    },

    async deleteFlashcardDeck(deckId) {
        return this._request(`/api/flashcards/${deckId}`, { method: 'DELETE' });
    },

    async exportFlashcardDeck(deckId) {
        return this._request(`/api/flashcards/${deckId}/export`);
    },

    // ── Quiz ───────────────────────────────────────────
    async generateQuiz(topic, count = 10) {
        return this._request('/api/quiz/generate', {
            method: 'POST',
            body: JSON.stringify({ topic, count }),
        });
    },

    async submitQuiz(quizId, answers) {
        return this._request('/api/quiz/submit', {
            method: 'POST',
            body: JSON.stringify({ quiz_id: quizId, answers }),
        });
    },

    async getQuizHistory() {
        return this._request('/api/quiz/history');
    },

    async getQuizDetail(quizId) {
        return this._request(`/api/quiz/${quizId}`);
    },

    async getChatHistory() {
        return this._request('/api/chat/history');
    },

    async getChatThread(sessionId = 'default') {
        return this._request(`/api/chat/thread?session_id=${encodeURIComponent(sessionId)}`);
    },

    async deleteChatSession(sessionId) {
        return this._request(`/api/chat/session/${encodeURIComponent(sessionId)}`, {
            method: 'DELETE',
        });
    },
};
