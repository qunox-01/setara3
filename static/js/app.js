/**
 * xariff — app.js
 * Drag-and-drop enhancement + HTMX chart init
 */

// ─── Drag & Drop Enhancement ───────────────────────────────────────────────

function initDropZone(dropZoneId, fileInputId) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(fileInputId);
    if (!dropZone || !fileInput) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); });
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, () => {
            dropZone.classList.add('drop-zone-active');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, () => {
            dropZone.classList.remove('drop-zone-active');
        });
    });

    dropZone.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (!files.length) return;

        const file = files[0];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['csv', 'tsv'].includes(ext)) {
            showBanner('Only CSV and TSV files are supported.', 'error');
            return;
        }

        // Transfer file to the input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;

        // Trigger the change handler if it exists
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));

        const nameEl = document.getElementById('file-name');
        if (nameEl) {
            nameEl.textContent = file.name;
            nameEl.classList.remove('hidden');
        }

        const analyseBtn = document.getElementById('analyse-btn');
        if (analyseBtn) analyseBtn.disabled = false;
    });
}

// ─── Simple banner notification ────────────────────────────────────────────

function showBanner(message, type = 'info') {
    const existing = document.getElementById('xariff-banner');
    if (existing) existing.remove();

    const colours = {
        info: 'bg-blue-50 border-blue-200 text-blue-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        success: 'bg-green-50 border-green-200 text-green-800',
    };

    const banner = document.createElement('div');
    banner.id = 'xariff-banner';
    banner.className = `fixed top-20 left-1/2 -translate-x-1/2 z-50 px-6 py-3 rounded-xl border shadow-lg text-sm font-medium ${colours[type] || colours.info}`;
    banner.textContent = message;
    document.body.appendChild(banner);

    setTimeout(() => banner.remove(), 4000);
}

// ─── Mobile menu toggle ────────────────────────────────────────────────────

function initMobileMenu() {
    const btn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    if (!btn || !menu) return;

    btn.addEventListener('click', () => {
        menu.classList.toggle('hidden');
    });
}

// ─── HTMX afterSwap — re-init charts after HTMX partial swaps ──────────────

function initChartsInElement(container) {
    container.querySelectorAll('[data-chart]').forEach(canvas => {
        try {
            const config = JSON.parse(canvas.dataset.chart);
            // Destroy existing chart on canvas if any
            const existing = Chart.getChart(canvas);
            if (existing) existing.destroy();
            new Chart(canvas, config);
        } catch (err) {
            console.warn('Chart init failed:', err);
        }
    });
}

document.addEventListener('htmx:afterSwap', e => {
    if (e.detail && e.detail.target) {
        initChartsInElement(e.detail.target);
    }
});

// ─── HTMX request error handling ───────────────────────────────────────────

document.addEventListener('htmx:responseError', e => {
    const status = e.detail.xhr.status;
    let msg = 'Something went wrong. Please try again.';
    try {
        const body = JSON.parse(e.detail.xhr.responseText);
        if (body.detail) msg = body.detail;
    } catch (_) { /* not JSON */ }

    const target = e.detail.target;
    if (target) {
        target.innerHTML = `
            <div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-sm">
                <strong>Error ${status}:</strong> ${msg}
            </div>`;
    }
    showBanner(msg, 'error');
});

// ─── PDF Share Section ──────────────────────────────────────────────────────

function renderShareSection(containerId, tool, resultId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const pdfUrl = `${location.origin}/tools/${tool}/pdf/${resultId}`;

    container.innerHTML = `
        <div class="mt-6 bg-slate-50 border border-slate-200 rounded-2xl p-5">
            <h3 class="font-bold text-slate-800 mb-1">Download &amp; Share</h3>
            <p class="text-slate-500 text-xs mb-4">Save a PDF copy of this report or share the download link.</p>
            <a href="${pdfUrl}"
               class="w-full flex items-center justify-center gap-2 px-4 py-3 bg-slate-900 hover:bg-slate-700 text-white text-sm font-semibold rounded-xl transition-colors mb-3">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V19a2 2 0 002 2h14a2 2 0 002-2v-2" />
                </svg>
                Download PDF Report
            </a>
            <div class="flex items-center gap-3 bg-white border border-slate-200 rounded-xl p-3">
                <svg class="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                <code id="share-url-${resultId}" class="text-xs text-slate-600 flex-1 truncate">${pdfUrl}</code>
                <button onclick="copyToolShareUrl('${resultId}')"
                        class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg transition-colors flex-shrink-0">
                    Copy link
                </button>
            </div>
        </div>`;
}

function copyToolShareUrl(resultId) {
    const el = document.getElementById('share-url-' + resultId);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent.trim()).then(() => {
        const btn = event.target;
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy link'; }, 2000);
    });
}

// ─── Init on DOM ready ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initDropZone('drop-zone', 'file-input');
    initChartsInElement(document);
});
