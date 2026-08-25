/**
 * StudyBot — Quiz Module
 * Handles MCQ quiz generation, interactive answering, submission, and results.
 */

const Quiz = (() => {
    let currentQuiz = null;
    let selectedAnswers = {};

    function init() {
        const generateBtn = document.getElementById('quiz-generate-btn');
        const submitBtn = document.getElementById('quiz-submit-btn');
        const retryBtn = document.getElementById('quiz-retry-btn');
        const backBtn = document.getElementById('quiz-back-btn');

        generateBtn.addEventListener('click', generateQuiz);
        submitBtn.addEventListener('click', submitQuiz);
        retryBtn.addEventListener('click', resetQuiz);
        backBtn.addEventListener('click', resetQuiz);

        document.getElementById('quiz-topic-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') generateBtn.click();
        });

        loadHistory();
    }

    async function generateQuiz() {
        const topicInput = document.getElementById('quiz-topic-input');
        const countSelect = document.getElementById('quiz-count');
        const topic = topicInput.value.trim();
        if (!topic) {
            App.showToast('Please enter a topic', 'error');
            return;
        }

        const btn = document.getElementById('quiz-generate-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

        try {
            const count = parseInt(countSelect.value);
            const data = await API.generateQuiz(topic, count);
            currentQuiz = data;
            selectedAnswers = {};
            renderQuiz(data);
        } catch (error) {
            App.showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Start Quiz';
        }
    }

    function renderQuiz(data) {
        // Hide generate area, show quiz area
        document.getElementById('quiz-generate-area').style.display = 'none';
        document.getElementById('quiz-history-area').style.display = 'none';
        document.getElementById('quiz-active-area').style.display = 'block';
        document.getElementById('quiz-results-area').style.display = 'none';

        document.getElementById('quiz-active-title').textContent = data.topic;
        document.getElementById('quiz-active-count').textContent = `${data.total} Questions`;

        const container = document.getElementById('quiz-questions');
        container.innerHTML = data.questions.map((q, idx) => `
            <div class="quiz-question-card glass-card" id="quiz-q-${idx}">
                <div class="quiz-q-header">
                    <span class="quiz-q-number">Q${idx + 1}</span>
                    <span class="quiz-q-text">${escapeHtml(q.question)}</span>
                </div>
                <div class="quiz-options">
                    ${q.options.map((opt, optIdx) => `
                        <label class="quiz-option" id="quiz-opt-${idx}-${optIdx}" onclick="Quiz.selectOption(${idx}, ${optIdx})">
                            <span class="quiz-option-letter">${String.fromCharCode(65 + optIdx)}</span>
                            <span class="quiz-option-text">${escapeHtml(opt)}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    function selectOption(questionIdx, optionIdx) {
        // Deselect previous
        document.querySelectorAll(`#quiz-q-${questionIdx} .quiz-option`).forEach(o => o.classList.remove('selected'));
        // Select new
        document.getElementById(`quiz-opt-${questionIdx}-${optionIdx}`).classList.add('selected');
        selectedAnswers[questionIdx] = optionIdx;

        // Update submit button state
        const totalQ = currentQuiz.questions.length;
        const answered = Object.keys(selectedAnswers).length;
        const submitBtn = document.getElementById('quiz-submit-btn');
        submitBtn.textContent = `Submit Quiz (${answered}/${totalQ} answered)`;
        submitBtn.disabled = false;
    }

    async function submitQuiz() {
        if (!currentQuiz) return;

        const totalQ = currentQuiz.questions.length;
        const answers = [];
        for (let i = 0; i < totalQ; i++) {
            answers.push(selectedAnswers[i] !== undefined ? selectedAnswers[i] : -1);
        }

        const unanswered = answers.filter(a => a === -1).length;
        if (unanswered > 0) {
            if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
        }

        const btn = document.getElementById('quiz-submit-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Evaluating...';

        try {
            const result = await API.submitQuiz(currentQuiz.quiz_id, answers);
            showResults(result);
        } catch (error) {
            App.showToast(error.message, 'error');
            btn.disabled = false;
            btn.innerHTML = 'Submit Quiz';
        }
    }

    function showResults(result) {
        document.getElementById('quiz-active-area').style.display = 'none';
        document.getElementById('quiz-results-area').style.display = 'block';

        // Score display
        const percentage = result.percentage;
        document.getElementById('quiz-score-num').textContent = `${result.score}/${result.total}`;
        document.getElementById('quiz-score-pct').textContent = `${percentage}%`;
        document.getElementById('quiz-score-comment').textContent = result.comment;

        // Score ring color
        const ring = document.getElementById('quiz-score-ring');
        if (percentage >= 80) ring.style.borderColor = '#22c55e';
        else if (percentage >= 60) ring.style.borderColor = '#eab308';
        else if (percentage >= 40) ring.style.borderColor = '#f97316';
        else ring.style.borderColor = '#ef4444';

        // Answer review
        const reviewContainer = document.getElementById('quiz-review');
        reviewContainer.innerHTML = result.review.map((r, idx) => {
            const hasUserAnswer = r.user_answer !== undefined;
            const statusClass = hasUserAnswer ? (r.is_correct ? 'correct' : 'wrong') : 'neutral';
            const statusIcon = hasUserAnswer ? (r.is_correct ? 'fa-check' : 'fa-times') : 'fa-history';

            return `
            <div class="quiz-review-item ${statusClass}">
                <div class="quiz-review-header">
                    <span class="quiz-review-badge ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                    </span>
                    <span class="quiz-review-q">Q${idx + 1}: ${escapeHtml(r.question)}</span>
                </div>
                <div class="quiz-review-answers">
                    ${r.options.map((opt, optIdx) => {
                let cls = '';
                if (optIdx === r.correct_answer) cls = 'correct-answer';
                if (hasUserAnswer && optIdx === r.user_answer && !r.is_correct) cls = 'wrong-answer';

                let icon = '';
                if (optIdx === r.correct_answer) icon = ' <i class="fas fa-check"></i>';
                else if (hasUserAnswer && optIdx === r.user_answer && !r.is_correct) icon = ' <i class="fas fa-times"></i>';

                return `<div class="quiz-review-option ${cls}">
                            <span>${String.fromCharCode(65 + optIdx)}</span> ${escapeHtml(opt)}
                            ${icon}
                        </div>`;
            }).join('')}
                </div>
                ${!hasUserAnswer ? '<div style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted);"><em>Your exact answer choices were not saved for this older quiz.</em></div>' : ''}
            </div>
            `;
        }).join('');
    }

    function resetQuiz() {
        currentQuiz = null;
        selectedAnswers = {};
        document.getElementById('quiz-generate-area').style.display = 'block';
        document.getElementById('quiz-history-area').style.display = 'block';
        document.getElementById('quiz-active-area').style.display = 'none';
        document.getElementById('quiz-results-area').style.display = 'none';
        loadHistory();
    }

    async function loadHistory() {
        const list = document.getElementById('quiz-history-list');
        try {
            const history = await API.getQuizHistory();
            if (history.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-trophy"></i>
                        <p>No quiz history yet. Take your first quiz!</p>
                    </div>`;
                return;
            }

            list.innerHTML = history.map(q => {
                const pct = q.total > 0 ? Math.round((q.score / q.total) * 100) : 0;
                let color = '#ef4444';
                if (pct >= 80) color = '#22c55e';
                else if (pct >= 60) color = '#eab308';
                else if (pct >= 40) color = '#f97316';

                return `
                    <div class="quiz-history-item" onclick="Quiz.viewResult('${q.id}')" title="Click to review answers" style="cursor: pointer; transition: background 0.2s;">
                        <div class="quiz-history-score" style="border-color: ${color}; color: ${color};">${pct}%</div>
                        <div class="quiz-history-info">
                            <div class="quiz-history-topic">${escapeHtml(q.topic)}</div>
                            <div class="quiz-history-meta">${q.score}/${q.total} · ${q.created_at ? new Date(q.created_at).toLocaleDateString() : ''}</div>
                        </div>
                    </div>`;
            }).join('');
        } catch (error) {
            list.innerHTML = `<div class="empty-state"><p>Failed to load history</p></div>`;
        }
    }

    async function viewResult(quizId) {
        try {
            const btn = document.getElementById('quiz-generate-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';

            const detail = await API.getQuizDetail(quizId);
            showResults(detail);
        } catch (error) {
            App.showToast(error.message, 'error');
        } finally {
            const btn = document.getElementById('quiz-generate-btn');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Start Quiz';
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, loadHistory, selectOption, viewResult };
})();
