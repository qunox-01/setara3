/**
 * drift.js — Dataset Drift Detector Tool
 * Handles dual file upload, sample data loading, API call, and result rendering.
 */

// ─── State ────────────────────────────────────────────────────────────────────

let driftData       = null;
let refFile         = null;
let curFile         = null;
let distributionChart = null;

// ─── DOM Ready ────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const refInput = document.getElementById('ref-file-input');
    const curInput = document.getElementById('cur-file-input');

    if (refInput) {
        refInput.addEventListener('change', () => {
            if (refInput.files[0]) onRefSelected(refInput.files[0]);
        });
    }
    if (curInput) {
        curInput.addEventListener('change', () => {
            if (curInput.files[0]) onCurSelected(curInput.files[0]);
        });
    }

    setupDropZone('drop-zone-ref', refInput, onRefSelected, ['border-rose-400', 'bg-rose-50']);
    setupDropZone('drop-zone-cur', curInput, onCurSelected, ['border-indigo-400', 'bg-indigo-50']);
});

// ─── File Selection ───────────────────────────────────────────────────────────

function onRefSelected(file) {
    refFile = file;
    const el = document.getElementById('ref-file-name');
    if (el) { el.textContent = file.name; el.classList.remove('hidden'); }
    updateAnalyzeBtn();
}

function onCurSelected(file) {
    curFile = file;
    const el = document.getElementById('cur-file-name');
    if (el) { el.textContent = file.name; el.classList.remove('hidden'); }
    updateAnalyzeBtn();
}

function updateAnalyzeBtn() {
    const btn = document.getElementById('drift-analyse-btn');
    if (btn) btn.disabled = !(refFile && curFile);
}

// ─── Drag-and-Drop Setup ──────────────────────────────────────────────────────

function setupDropZone(zoneId, input, onSelect, hoverClasses) {
    const zone = document.getElementById(zoneId);
    if (!zone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(e =>
        zone.addEventListener(e, ev => { ev.preventDefault(); ev.stopPropagation(); })
    );
    ['dragenter', 'dragover'].forEach(e =>
        zone.addEventListener(e, () => zone.classList.add(...hoverClasses))
    );
    ['dragleave', 'drop'].forEach(e =>
        zone.addEventListener(e, () => zone.classList.remove(...hoverClasses))
    );
    zone.addEventListener('drop', ev => {
        const f = ev.dataTransfer.files[0];
        if (!f) return;
        if (!f.name.toLowerCase().endsWith('.csv')) {
            showError('Only CSV files are supported.');
            return;
        }
        if (input) {
            const dt = new DataTransfer();
            dt.items.add(f);
            input.files = dt.files;
        }
        onSelect(f);
    });
}

// ─── Sample Data ──────────────────────────────────────────────────────────────

async function loadDriftSample() {
    try {
        const [refResp, curResp] = await Promise.all([
            fetch('/sample-data/drift_reference'),
            fetch('/sample-data/drift_current'),
        ]);
        if (!refResp.ok || !curResp.ok) throw new Error('Sample data unavailable.');

        const [refBlob, curBlob] = await Promise.all([refResp.blob(), curResp.blob()]);

        const rFile = new File([refBlob], 'reference_sample.csv', { type: 'text/csv' });
        const cFile = new File([curBlob], 'current_sample.csv',   { type: 'text/csv' });

        // Populate file inputs via DataTransfer so the browser reflects the files
        const refInput = document.getElementById('ref-file-input');
        const curInput = document.getElementById('cur-file-input');
        if (refInput) { const dt = new DataTransfer(); dt.items.add(rFile); refInput.files = dt.files; }
        if (curInput) { const dt = new DataTransfer(); dt.items.add(cFile); curInput.files = dt.files; }

        onRefSelected(rFile);
        onCurSelected(cFile);

        startDrift();
    } catch (err) {
        showError('Could not load sample data: ' + err.message);
    }
}

// ─── Main Analysis ────────────────────────────────────────────────────────────

async function startDrift() {
    if (!refFile || !curFile) return;

    const nBins = document.getElementById('bins-select')?.value || '10';

    setLoading(true);
    clearResults();

    const formData = new FormData();
    formData.append('reference_file', refFile);
    formData.append('current_file',   curFile);

    const url = `/api/tools/drift/analyze?n_bins=${nBins}`;

    try {
        const resp = await fetch(url, { method: 'POST', body: formData });
        const json = await resp.json();
        if (!resp.ok) {
            showError(json.detail || `Error ${resp.status}`);
            return;
        }
        driftData = json;
        renderAll(json);
    } catch (err) {
        showError('Network error. Please try again.');
    } finally {
        setLoading(false);
    }
}

// ─── Render Orchestrator ──────────────────────────────────────────────────────

function renderAll(data) {
    document.getElementById('drift-results').classList.remove('hidden');
    renderScoreBanner(data.summary);
    renderSummaryCards(data.summary);
    renderFeaturesTable(data.features);
    renderNumericStats(data.features);
    populateChartSelector(data.features);
    renderSelectedChart();
}

// ─── Component 1: Score Banner ────────────────────────────────────────────────

function renderScoreBanner(s) {
    const el = document.getElementById('drift-score-banner');
    if (!el) return;

    let gradient, ringColor, scoreColor, msg;
    if (s.score >= 80) {
        gradient   = 'from-green-50 to-emerald-50 border-green-200';
        ringColor  = 'border-green-400';
        scoreColor = 'text-green-600';
        msg = `Distributions look stable. Only <strong>${s.drifted_count}</strong> of ${s.total_features} features show drift — well within a normal range.`;
    } else if (s.score >= 50) {
        gradient   = 'from-yellow-50 to-amber-50 border-yellow-200';
        ringColor  = 'border-yellow-400';
        scoreColor = 'text-yellow-600';
        msg = `<strong>${s.drifted_count}</strong> of ${s.total_features} features have drifted (${s.drifted_pct}%). Review the feature table for which ones need attention.`;
    } else {
        gradient   = 'from-red-50 to-rose-50 border-red-200';
        ringColor  = 'border-red-400';
        scoreColor = 'text-red-600';
        msg = `Significant drift detected in <strong>${s.drifted_count}</strong> of ${s.total_features} features (${s.drifted_pct}%). Model predictions may be unreliable on this data.`;
    }

    el.innerHTML = `
        <div class="bg-gradient-to-br ${gradient} border rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col sm:flex-row items-center gap-6">
                <div class="flex-shrink-0 w-28 h-28 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center bg-white shadow-inner">
                    <span class="text-4xl font-extrabold ${scoreColor}">${s.score}</span>
                    <span class="text-xs text-slate-500 font-medium">/ 100</span>
                </div>
                <div class="flex-1 text-center sm:text-left">
                    <p class="text-lg mb-1 font-bold ${scoreColor}">${s.verdict}</p>
                    <p class="text-slate-600 text-sm leading-relaxed">${msg}</p>
                    <div class="mt-3 flex flex-wrap gap-3 text-xs text-slate-500 justify-center sm:justify-start">
                        <span><strong class="text-slate-700">${s.ref_rows.toLocaleString()}</strong> reference rows</span>
                        <span><strong class="text-slate-700">${s.cur_rows.toLocaleString()}</strong> current rows</span>
                        <span><strong class="text-slate-700">${s.total_features}</strong> features compared</span>
                    </div>
                </div>
            </div>
        </div>`;
}

// ─── Component 2: Summary Cards ───────────────────────────────────────────────

function renderSummaryCards(s) {
    const el = document.getElementById('drift-summary-cards');
    if (!el) return;

    const cards = [
        { label: 'Critical Drift',  value: s.critical_count,    color: 'text-red-600',     bg: 'bg-red-50',     border: 'border-red-100'    },
        { label: 'Moderate Drift',  value: s.moderate_count,    color: 'text-amber-600',   bg: 'bg-amber-50',   border: 'border-amber-100'  },
        { label: 'Stable',          value: s.stable_count,      color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-100'},
        { label: 'KS Significant',  value: s.ks_drifted_count,  color: 'text-indigo-600',  bg: 'bg-indigo-50',  border: 'border-indigo-100' },
    ];

    el.innerHTML = cards.map(c => `
        <div class="${c.bg} border ${c.border} rounded-xl p-4 text-center shadow-sm">
            <p class="text-3xl font-black ${c.color}">${c.value}</p>
            <p class="text-xs text-slate-500 mt-1 font-medium">${c.label}</p>
        </div>`).join('');
}

// ─── Component 3: Feature Drift Table ────────────────────────────────────────

function renderFeaturesTable(features) {
    const tbody = document.getElementById('drift-features-tbody');
    if (!tbody) return;

    tbody.innerHTML = features.map((f, i) => {
        const sevBadge = sev => {
            const map = {
                critical: 'bg-red-100 text-red-700',
                moderate: 'bg-amber-100 text-amber-700',
                stable:   'bg-emerald-100 text-emerald-700',
            };
            return `<span class="px-2 py-0.5 rounded-full text-xs font-semibold ${map[sev] || ''}">${sev}</span>`;
        };
        const ksBadge = drifted =>
            drifted === null ? '<span class="text-slate-300">—</span>' :
            drifted ? '<span class="text-red-600 font-semibold text-xs">Yes</span>' :
                      '<span class="text-emerald-600 text-xs">No</span>';

        return `
            <tr class="hover:bg-slate-50 transition-colors cursor-pointer"
                onclick="selectChartFeature('${f.feature}')">
                <td class="px-4 py-3 font-medium text-slate-800 max-w-[160px] truncate" title="${f.feature}">${f.feature}</td>
                <td class="px-4 py-3 text-slate-500 text-xs">${f.type}</td>
                <td class="px-4 py-3 text-right font-mono text-sm font-semibold
                    ${f.psi >= 0.2 ? 'text-red-600' : f.psi >= 0.1 ? 'text-amber-600' : 'text-emerald-600'}">
                    ${f.psi.toFixed(4)}
                </td>
                <td class="px-4 py-3">${sevBadge(f.psi_severity)}</td>
                <td class="px-4 py-3 text-right font-mono text-sm text-slate-600">
                    ${f.ks_statistic !== null ? f.ks_statistic.toFixed(4) : '<span class="text-slate-300">—</span>'}
                </td>
                <td class="px-4 py-3 text-right font-mono text-sm text-slate-600">
                    ${f.ks_p_value !== null ? f.ks_p_value.toFixed(4) : '<span class="text-slate-300">—</span>'}
                </td>
                <td class="px-4 py-3">${ksBadge(f.ks_drift)}</td>
            </tr>`;
    }).join('');
}

// ─── Component 4: Distribution Chart ─────────────────────────────────────────

function populateChartSelector(features) {
    const sel = document.getElementById('feature-chart-select');
    if (!sel || !driftData) return;
    sel.innerHTML = features
        .filter(f => driftData.chart_data[f.feature])
        .map(f => `<option value="${f.feature}">${f.feature} (${f.psi_severity})</option>`)
        .join('');
}

function selectChartFeature(featureName) {
    const sel = document.getElementById('feature-chart-select');
    if (sel) sel.value = featureName;
    renderSelectedChart();
    document.getElementById('drift-chart-section')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderSelectedChart() {
    if (!driftData) return;
    const col = document.getElementById('feature-chart-select')?.value;
    if (!col) return;

    const cd = driftData.chart_data[col];
    if (!cd) return;

    if (distributionChart) { distributionChart.destroy(); distributionChart = null; }

    const ctx = document.getElementById('distribution-chart')?.getContext('2d');
    if (!ctx) return;

    const isNumeric = cd.type === 'numeric';

    if (isNumeric) {
        const labels = cd.ref.labels.map(v => Number(v).toFixed(2));
        distributionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Reference', data: cd.ref.counts, backgroundColor: 'rgba(244,63,94,0.5)',  borderColor: 'rgba(244,63,94,0.8)',  borderWidth: 1 },
                    { label: 'Current',   data: cd.cur.counts, backgroundColor: 'rgba(99,102,241,0.5)', borderColor: 'rgba(99,102,241,0.8)', borderWidth: 1 },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } },
                scales: {
                    x: { title: { display: true, text: col } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                },
            },
        });
    } else {
        const allCats  = [...new Set([...cd.ref.labels, ...cd.cur.labels])];
        const refMap   = Object.fromEntries(cd.ref.labels.map((l, i) => [l, cd.ref.counts[i]]));
        const curMap   = Object.fromEntries(cd.cur.labels.map((l, i) => [l, cd.cur.counts[i]]));
        distributionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: allCats,
                datasets: [
                    { label: 'Reference', data: allCats.map(c => refMap[c] || 0), backgroundColor: 'rgba(244,63,94,0.5)',  borderColor: 'rgba(244,63,94,0.8)',  borderWidth: 1 },
                    { label: 'Current',   data: allCats.map(c => curMap[c] || 0), backgroundColor: 'rgba(99,102,241,0.5)', borderColor: 'rgba(99,102,241,0.8)', borderWidth: 1 },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top' } },
                scales: {
                    x: { title: { display: true, text: col } },
                    y: { title: { display: true, text: 'Count' }, beginAtZero: true },
                },
            },
        });
    }
}

// ─── Component 5: Numeric Stats Table ────────────────────────────────────────

function renderNumericStats(features) {
    const section = document.getElementById('drift-numeric-stats');
    const tbody   = document.getElementById('drift-numeric-tbody');
    if (!section || !tbody) return;

    const numFeats = features.filter(f => f.type === 'numeric');
    if (numFeats.length === 0) { section.classList.add('hidden'); return; }
    section.classList.remove('hidden');

    const fmt = v => (v !== null && v !== undefined) ? Number(v).toFixed(4) : '—';
    const shiftClass = (ref, cur) => {
        if (ref === null || cur === null) return 'text-slate-600';
        const pct = Math.abs((cur - ref) / (Math.abs(ref) + 1e-9)) * 100;
        return pct > 20 ? 'text-red-600 font-semibold' : pct > 5 ? 'text-amber-600' : 'text-slate-600';
    };

    tbody.innerHTML = numFeats.map(f => `
        <tr class="hover:bg-slate-50 transition-colors">
            <td class="px-4 py-3 font-medium text-slate-800 max-w-[140px] truncate" title="${f.feature}">${f.feature}</td>
            <td class="px-4 py-3 text-right font-mono text-slate-600">${fmt(f.ref_mean)}</td>
            <td class="px-4 py-3 text-right font-mono ${shiftClass(f.ref_mean, f.cur_mean)}">${fmt(f.cur_mean)}</td>
            <td class="px-4 py-3 text-right font-mono text-slate-600">${fmt(f.ref_std)}</td>
            <td class="px-4 py-3 text-right font-mono ${shiftClass(f.ref_std, f.cur_std)}">${fmt(f.cur_std)}</td>
            <td class="px-4 py-3 text-right font-mono text-slate-600">${fmt(f.ref_median)}</td>
            <td class="px-4 py-3 text-right font-mono ${shiftClass(f.ref_median, f.cur_median)}">${fmt(f.cur_median)}</td>
        </tr>`).join('');
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function setLoading(on) {
    document.getElementById('drift-loading')?.classList.toggle('hidden', !on);
    document.getElementById('upload-section')?.classList.toggle('opacity-50', on);
    const btn = document.getElementById('drift-analyse-btn');
    if (btn) { btn.disabled = on; btn.textContent = on ? 'Analysing…' : 'Detect Drift'; }
}

function clearResults() {
    document.getElementById('drift-results')?.classList.add('hidden');
    document.getElementById('drift-error')?.classList.add('hidden');
    if (distributionChart) { distributionChart.destroy(); distributionChart = null; }
}

function showError(msg) {
    const el = document.getElementById('drift-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}
