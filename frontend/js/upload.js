/**
 * StudyBot — Upload Module
 * Handles file upload, drag & drop, and document management.
 */

const Upload = (() => {
    function init() {
        const dropzone = document.getElementById('upload-dropzone');
        const fileInput = document.getElementById('file-input');

        // Click to open file browser
        dropzone.addEventListener('click', () => fileInput.click());

        // File selected via browser
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleFiles(Array.from(e.target.files));
        });

        // Drag & drop
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf'));
            if (files.length > 0) handleFiles(files);
            else App.showToast('Only PDF files are supported', 'error');
        });

        // Load existing documents
        loadDocuments();
    }

    async function handleFiles(files) {
        const progressArea = document.getElementById('upload-progress');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const dropzoneContent = document.querySelector('.dropzone-content');

        dropzoneContent.style.display = 'none';
        progressArea.style.display = 'block';

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const progress = ((i) / files.length) * 100;
            progressFill.style.width = progress + '%';
            progressText.textContent = `Processing ${i + 1}/${files.length}: ${file.name}...`;

            try {
                await API.uploadDocument(file);
                App.showToast(`${file.name} uploaded successfully`, 'success');
            } catch (error) {
                App.showToast(`Failed to upload ${file.name}: ${error.message}`, 'error');
            }
        }

        progressFill.style.width = '100%';
        progressText.textContent = 'All files processed!';

        setTimeout(() => {
            progressArea.style.display = 'none';
            dropzoneContent.style.display = 'block';
            progressFill.style.width = '0%';
        }, 2000);

        loadDocuments();
    }

    async function loadDocuments() {
        const list = document.getElementById('documents-list');

        try {
            const docs = await API.listDocuments();
            if (docs.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No documents uploaded yet</p>
                    </div>`;
                return;
            }

            list.innerHTML = docs.map(doc => `
                <div class="document-item" data-id="${doc.id}">
                    <div class="doc-icon"><i class="fas fa-file-pdf"></i></div>
                    <div class="doc-info">
                        <div class="doc-name">${escapeHtml(doc.filename)}</div>
                        <div class="doc-meta">${doc.total_chunks} chunks · ${doc.processed_date ? new Date(doc.processed_date).toLocaleDateString() : 'N/A'}</div>
                    </div>
                    <button class="btn btn-danger btn-sm delete-doc-btn" data-id="${doc.id}" title="Delete document">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `).join('');

            // Delete handlers
            list.querySelectorAll('.delete-doc-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const docId = btn.dataset.id;
                    if (!confirm('Delete this document and all its chunks?')) return;
                    try {
                        await API.deleteDocument(docId);
                        App.showToast('Document deleted', 'info');
                        loadDocuments();
                    } catch (error) {
                        App.showToast(error.message, 'error');
                    }
                });
            });
        } catch (error) {
            list.innerHTML = `<div class="empty-state"><p>Failed to load documents</p></div>`;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    return { init, loadDocuments };
})();
