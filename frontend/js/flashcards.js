/**
 * StudyBot — Flashcards Module
 * Handles flashcard generation, viewing, navigation, and export.
 */

const Flashcards = (() => {
    let currentDeck = null;
    let currentIndex = 0;
    let isFlipped = false;

    function init() {
        const generateBtn = document.getElementById('fc-generate-btn');
        const backBtn = document.getElementById('fc-back-btn');
        const prevBtn = document.getElementById('fc-prev');
        const nextBtn = document.getElementById('fc-next');
        const exportBtn = document.getElementById('fc-export-btn');
        const card = document.getElementById('fc-card');

        generateBtn.addEventListener('click', generateDeck);
        backBtn.addEventListener('click', closeViewer);
        prevBtn.addEventListener('click', prevCard);
        nextBtn.addEventListener('click', nextCard);
        exportBtn.addEventListener('click', exportDeck);
        card.addEventListener('click', flipCard);

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (!currentDeck) return;
            const page = document.getElementById('page-flashcards');
            if (!page.classList.contains('active')) return;

            if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                flipCard();
            } else if (e.key === 'ArrowLeft') {
                prevCard();
            } else if (e.key === 'ArrowRight') {
                nextCard();
            }
        });

        // Topic input enter
        document.getElementById('fc-topic-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') generateBtn.click();
        });

        loadDecks();
    }

    async function generateDeck() {
        const topicInput = document.getElementById('fc-topic-input');
        const countSelect = document.getElementById('fc-count');
        const topic = topicInput.value.trim();
        if (!topic) {
            App.showToast('Please enter a topic', 'error');
            return;
        }

        const btn = document.getElementById('fc-generate-btn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

        try {
            const count = parseInt(countSelect.value);
            const data = await API.generateFlashcards({ topic, count });
            App.showToast(`Created ${data.card_count} flashcards!`, 'success');
            topicInput.value = '';
            loadDecks();
            openDeck(data);
        } catch (error) {
            App.showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sparkles"></i> Generate';
        }
    }

    async function loadDecks() {
        const list = document.getElementById('decks-list');
        try {
            const decks = await API.listFlashcardDecks();
            if (decks.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-layer-group"></i>
                        <p>No flashcard decks yet. Generate one above!</p>
                    </div>`;
                return;
            }

            list.innerHTML = decks.map(deck => `
                <div class="deck-card" data-id="${deck.id}">
                    <h4>${escapeHtml(deck.title)}</h4>
                    <div class="deck-card-meta">
                        <span><i class="fas fa-clone"></i> ${deck.card_count} cards</span>
                        <span>${deck.created_at ? new Date(deck.created_at).toLocaleDateString() : ''}</span>
                    </div>
                    <div class="deck-card-actions">
                        <button class="btn btn-primary btn-sm view-deck-btn" data-id="${deck.id}">
                            <i class="fas fa-play"></i> Study
                        </button>
                        <button class="btn btn-danger btn-sm delete-deck-btn" data-id="${deck.id}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>
            `).join('');

            // View handlers
            list.querySelectorAll('.view-deck-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    try {
                        const deck = await API.getFlashcardDeck(btn.dataset.id);
                        openDeck(deck);
                    } catch (error) {
                        App.showToast(error.message, 'error');
                    }
                });
            });

            // Delete handlers
            list.querySelectorAll('.delete-deck-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (!confirm('Delete this flashcard deck?')) return;
                    try {
                        await API.deleteFlashcardDeck(btn.dataset.id);
                        App.showToast('Deck deleted', 'info');
                        loadDecks();
                    } catch (error) {
                        App.showToast(error.message, 'error');
                    }
                });
            });

            // Click card to study
            list.querySelectorAll('.deck-card').forEach(card => {
                card.addEventListener('click', async () => {
                    try {
                        const deck = await API.getFlashcardDeck(card.dataset.id);
                        openDeck(deck);
                    } catch (error) {
                        App.showToast(error.message, 'error');
                    }
                });
            });
        } catch (error) {
            list.innerHTML = `<div class="empty-state"><p>Failed to load decks</p></div>`;
        }
    }

    function openDeck(deck) {
        currentDeck = deck;
        currentIndex = 0;
        isFlipped = false;

        document.getElementById('flashcard-viewer').style.display = 'block';
        document.getElementById('flashcard-decks-area').style.display = 'none';
        document.querySelector('.flashcard-generate').style.display = 'none';
        document.getElementById('fc-deck-title').textContent = deck.title;

        showCard();
    }

    function closeViewer() {
        currentDeck = null;
        document.getElementById('flashcard-viewer').style.display = 'none';
        document.getElementById('flashcard-decks-area').style.display = 'block';
        document.querySelector('.flashcard-generate').style.display = 'block';
        loadDecks();
    }

    function showCard() {
        if (!currentDeck || !currentDeck.cards || currentDeck.cards.length === 0) return;

        const card = currentDeck.cards[currentIndex];
        document.getElementById('fc-question').textContent = card.question;
        document.getElementById('fc-answer').textContent = card.answer;
        document.getElementById('fc-counter').textContent = `${currentIndex + 1} / ${currentDeck.cards.length}`;

        // Reset flip
        isFlipped = false;
        document.getElementById('fc-card-inner').classList.remove('flipped');

        // Update progress
        const progress = ((currentIndex + 1) / currentDeck.cards.length) * 100;
        document.getElementById('fc-progress-bar').style.width = progress + '%';
    }

    function flipCard() {
        isFlipped = !isFlipped;
        document.getElementById('fc-card-inner').classList.toggle('flipped', isFlipped);
    }

    function prevCard() {
        if (!currentDeck || currentIndex <= 0) return;
        currentIndex--;
        showCard();
    }

    function nextCard() {
        if (!currentDeck || currentIndex >= currentDeck.cards.length - 1) return;
        currentIndex++;
        showCard();
    }

    async function exportDeck() {
        if (!currentDeck) return;
        try {
            const data = await API.exportFlashcardDeck(currentDeck.id);
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${data.title.replace(/[^a-z0-9]/gi, '_')}_flashcards.json`;
            a.click();
            URL.revokeObjectURL(url);
            App.showToast('Deck exported!', 'success');
        } catch (error) {
            App.showToast(error.message, 'error');
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, loadDecks };
})();
