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

// ─── Init on DOM ready ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initDropZone('drop-zone', 'file-input');
    initChartsInElement(document);
});
