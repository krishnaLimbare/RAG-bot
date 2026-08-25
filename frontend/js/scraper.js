/**
 * StudyBot — Web Research Module
 * Handles web scraping and adding results to the knowledge base.
 */

const Scraper = (() => {
    function init() {
        const input = document.getElementById('research-input');
        const btn = document.getElementById('research-btn');

        btn.addEventListener('click', () => doSearch());
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') doSearch();
        });
    }

    async function doSearch() {
        const input = document.getElementById('research-input');
        const topic = input.value.trim();
        if (!topic) return;

        const results = document.getElementById('research-results');
        results.innerHTML = `
            <div class="empty-state">
                <div class="spinner" style="margin:0 auto 16px;width:36px;height:36px;border-width:2px;"></div>
                <p>Searching the web for "${escapeHtml(topic)}"...</p>
            </div>`;

        try {
            const data = await API.scrape(topic);

            if (!data.success || data.results.length === 0) {
                results.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>${data.error || 'No results found. Try a different topic.'}</p>
                    </div>`;
                return;
            }

            results.innerHTML = data.results.map((r, i) => `
                <div class="research-card glass-card">
                    <div class="research-card-header">
                        <h4>${escapeHtml(r.title || r.url)}</h4>
                    </div>
                    <div class="card-url">
                        <a href="${escapeHtml(r.url)}" target="_blank" rel="noopener">${escapeHtml(r.url)}</a>
                    </div>
                    <div class="card-content">${escapeHtml(r.content.substring(0, 1000))}${r.content.length > 1000 ? '...' : ''}</div>
                    <div class="research-card-actions">
                        <button class="btn btn-primary btn-sm add-kb-btn" data-index="${i}">
                            <i class="fas fa-plus"></i> Add to Knowledge Base
                        </button>
                        <span class="doc-meta">${(r.full_length / 1000).toFixed(1)}k chars</span>
                    </div>
                </div>
            `).join('');

            // Add to KB handlers
            results.querySelectorAll('.add-kb-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const idx = parseInt(btn.dataset.index);
                    const result = data.results[idx];
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
                    try {
                        await API.addToKnowledgeBase(result.content, result.title || result.url);
                        btn.innerHTML = '<i class="fas fa-check"></i> Added';
                        btn.classList.remove('btn-primary');
                        btn.classList.add('btn-ghost');
                        App.showToast('Added to knowledge base!', 'success');
                    } catch (error) {
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fas fa-plus"></i> Retry';
                        App.showToast(error.message, 'error');
                    }
                });
            });
        } catch (error) {
            results.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Error: ${escapeHtml(error.message)}</p>
                </div>`;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init };
})();
