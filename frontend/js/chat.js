/**
 * StudyBot — Chat Module
 * Handles the chat interface, message rendering, and mode switching.
 */

const Chat = (() => {
    let mode = 'explain';
    let currentSessionId = 'session_' + Date.now();

    function init() {
        const input = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const clearBtn = document.getElementById('clear-chat-btn');

        // Send on Enter
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Auto-resize textarea
        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        });

        sendBtn.addEventListener('click', sendMessage);
        clearBtn.addEventListener('click', clearChat);

        loadSidebarHistory();
        loadChatThread();
    }

    async function loadSidebarHistory() {
        try {
            const history = await API.getChatHistory();
            const list = document.getElementById('sidebar-chats-list');
            if (!list) return;

            if (history.length === 0) {
                list.innerHTML = '<div class="sidebar-chat-empty">No recent chats</div>';
                return;
            }

            list.innerHTML = history.map(h => `
                <div class="sidebar-chat-item ${h.id === currentSessionId ? 'active' : ''}" onclick="Chat.openSession('${h.id}')" title="${escapeHtml(h.preview)}">
                    <div class="sidebar-chat-item-content">
                        <i class="far fa-comment-dots"></i>
                        <span>${escapeHtml(h.preview)}</span>
                    </div>
                    <button class="delete-session-btn" onclick="Chat.deleteSession('${h.id}', event)" title="Delete Chat">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `).join('');
        } catch (e) {
            console.error('Failed to load sidebar chats', e);
        }
    }

    async function loadChatThread(sessionId) {
        if (sessionId) {
            currentSessionId = sessionId;
        }
        try {
            const thread = await API.getChatThread(currentSessionId);
            const container = document.getElementById('chat-messages');

            if (thread && thread.length > 0) {
                const welcome = document.querySelector('.welcome-message');
                if (welcome) welcome.remove();

                container.innerHTML = '';

                thread.forEach(msg => {
                    if (msg.role === 'user' || msg.role === 'assistant') {
                        appendMessage(msg.role, msg.content, []);
                    }
                });
            } else {
                container.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon"><i class="fas fa-graduation-cap"></i></div>
                    <h2>Welcome to StudyBot</h2>
                    <p>Upload your study materials, ask questions, and I'll help you learn.</p>
                    <div class="welcome-tips">
                        <div class="tip"><i class="fas fa-lightbulb"></i> <strong>Chat</strong> — Ask questions and get explanations</div>
                        <div class="tip"><i class="fas fa-clipboard-check"></i> <strong>Quiz</strong> — Test yourself in the Quiz tab</div>
                        <div class="tip"><i class="fas fa-layer-group"></i> <strong>Flashcards</strong> — Generate study cards</div>
                    </div>
                </div>`;
            }
            loadSidebarHistory();
        } catch (e) {
            console.error('Failed to load chat thread', e);
        }
    }

    async function openSession(sessionId) {
        App.navigateTo('chat');
        await loadChatThread(sessionId);
    }

    async function deleteSession(sessionId, event) {
        if (event) {
            event.stopPropagation();
        }
        if (!confirm('Are you sure you want to delete this chat history?')) {
            return;
        }

        try {
            await API.deleteChatSession(sessionId);
            App.showToast('Chat deleted', 'success');

            // If the deleted session is the currently active one, clear the chat window
            if (sessionId === currentSessionId) {
                clearChat();
            } else {
                loadSidebarHistory(); // just refresh the sidebar list
            }
        } catch (e) {
            console.error('Failed to delete chat session', e);
            App.showToast('Failed to delete chat', 'error');
        }
    }

    async function sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message) return;

        // Clear welcome message
        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        // Add user message
        appendMessage('user', message);
        input.value = '';
        input.style.height = 'auto';

        // Show typing indicator
        const typingEl = showTypingIndicator();

        try {
            const response = await API.chat(message, mode, currentSessionId);
            typingEl.remove();
            appendMessage('assistant', response.answer, response.sources);
            loadSidebarHistory(); // update preview if it was a new session
        } catch (error) {
            typingEl.remove();
            appendMessage('assistant', `Sorry, I encountered an error: ${error.message}`);
            App.showToast(error.message, 'error');
        }
    }

    function appendMessage(role, content, sources = []) {
        const container = document.getElementById('chat-messages');
        const msg = document.createElement('div');
        msg.className = `message ${role}`;

        const avatarIcon = role === 'user' ? 'fa-user' : 'fa-robot';
        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            const sourceItems = sources.map((s, i) =>
                `<div class="source-item"><strong>Source ${i + 1}:</strong> ${escapeHtml(s.text)}</div>`
            ).join('');
            sourcesHtml = `
                <div class="message-sources">
                    <details>
                        <summary><i class="fas fa-book-open"></i> ${sources.length} source(s) used</summary>
                        ${sourceItems}
                    </details>
                </div>`;
        }

        const renderedContent = role === 'assistant' ? renderMarkdown(content) : escapeHtml(content);

        msg.innerHTML = `
            <div class="message-avatar"><i class="fas ${avatarIcon}"></i></div>
            <div class="message-content">
                ${renderedContent}
                ${sourcesHtml}
            </div>
        `;

        container.appendChild(msg);
        container.scrollTop = container.scrollHeight;
    }

    function showTypingIndicator() {
        const container = document.getElementById('chat-messages');
        const typing = document.createElement('div');
        typing.className = 'message assistant';
        typing.innerHTML = `
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
        return typing;
    }

    async function clearChat() {
        try {
            currentSessionId = 'session_' + Date.now();
            const container = document.getElementById('chat-messages');
            container.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon"><i class="fas fa-graduation-cap"></i></div>
                    <h2>Welcome to StudyBot</h2>
                    <p>Upload your study materials, ask questions, and I'll help you learn.</p>
                    <div class="welcome-tips">
                        <div class="tip"><i class="fas fa-lightbulb"></i> <strong>Chat</strong> — Ask questions and get explanations</div>
                        <div class="tip"><i class="fas fa-clipboard-check"></i> <strong>Quiz</strong> — Test yourself in the Quiz tab</div>
                        <div class="tip"><i class="fas fa-layer-group"></i> <strong>Flashcards</strong> — Generate study cards</div>
                    </div>
                </div>`;
            App.showToast('Chat history cleared', 'info');
            loadSidebarHistory();
        } catch (error) {
            App.showToast(error.message, 'error');
        }
    }

    function renderMarkdown(text) {
        try {
            return marked.parse(text);
        } catch {
            return escapeHtml(text).replace(/\n/g, '<br>');
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, loadSidebarHistory, openSession, deleteSession, clearChat };
})();
