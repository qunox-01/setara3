/**
 * xariff — profiler.js
 * Dataset Profiler: upload, analyse, render results with charts.
 */

// ─── State ──────────────────────────────────────────────────────────────────

let profileData = null;
let sortKey = 'name';
let sortAsc = true;
const chartInstances = {};

// ─── Drop Zone ──────────────────────────────────────────────────────────────

function initProfilerDropZone() {
    const zone = document.getElementById('drop-zone-profiler');
    const input = document.getElementById('profiler-file-input');
    if (!zone || !input) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); });
    });
    ['dragenter', 'dragover'].forEach(evt => {
        zone.addEventListener(evt, () => zone.classList.add('drop-zone-active'));
    });
    ['dragleave', 'drop'].forEach(evt => {
        zone.addEventListener(evt, () => zone.classList.remove('drop-zone-active'));
    });

    zone.addEventListener('drop', e => {
        const file = e.dataTransfer.files[0];
        if (!file) return;
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showBanner('Only CSV files are supported.', 'error');
            return;
        }
        setProfilerFile(file);
    });

    input.addEventListener('change', () => {
        if (input.files[0]) setProfilerFile(input.files[0]);
    });
}

function setProfilerFile(file) {
    const nameEl = document.getElementById('profiler-file-name');
    if (nameEl) {
        nameEl.textContent = `${file.name} (${formatBytes(file.size)})`;
        nameEl.classList.remove('hidden');
    }
    document.getElementById('drop-zone-profiler').classList.add('border-blue-400', 'bg-blue-50');
    document.getElementById('profiler-analyse-btn').disabled = false;
}

// ─── Upload & Analyse ────────────────────────────────────────────────────────

async function startProfiler() {
    const input = document.getElementById('profiler-file-input');
    if (!input.files[0]) return;
    const file = input.files[0];

    setState('loading');
    document.getElementById('profiler-loading-filename').textContent = `${file.name} · ${formatBytes(file.size)}`;

    const form = new FormData();
    form.append('file', file);

    try {
        const res = await fetch('/api/tools/profiler/analyze', { method: 'POST', body: form });
        if (!res.ok) {
            let msg = `Error ${res.status}`;
            try { const j = await res.json(); msg = j.detail || msg; } catch (_) {}
            throw new Error(msg);
        }
        profileData = await res.json();
        renderResults(profileData);
        setState('results');
    } catch (err) {
        showError(err.message || 'Something went wrong. Please try again.');
    }
}

function loadProfilerSample() {
    fetch('/sample-data/quality')
        .then(r => r.blob())
        .then(blob => {
            const file = new File([blob], 'sample.csv', { type: 'text/csv' });
            const dt = new DataTransfer();
            dt.items.add(file);
            const input = document.getElementById('profiler-file-input');
            input.files = dt.files;
            setProfilerFile(file);
            setTimeout(startProfiler, 200);
        })
        .catch(() => showBanner('Could not load sample data.', 'error'));
}

// ─── State management ────────────────────────────────────────────────────────

function setState(state) {
    document.getElementById('upload-section').classList.toggle('hidden', state !== 'upload' && state !== 'results');
    document.getElementById('profiler-loading').classList.toggle('hidden', state !== 'loading');
    document.getElementById('profiler-error').classList.toggle('hidden', state !== 'error');
    document.getElementById('profiler-results').classList.toggle('hidden', state !== 'results');
    if (state === 'results') {
        document.getElementById('upload-section').classList.remove('hidden');
    }
}

function showError(msg) {
    const el = document.getElementById('profiler-error');
    el.textContent = msg;
    el.classList.remove('hidden');
    setState('upload');
}

// ─── Render Results ──────────────────────────────────────────────────────────

function renderResults(data) {
    renderOverview(data.dataset);
    renderFeatureTable(data.features);
    renderCorrelations(data.correlations);
}

// ─── Section A: Overview ─────────────────────────────────────────────────────

function renderOverview(ds) {
    const el = document.getElementById('profiler-overview');
    const sampleBanner = ds.sampled
        ? `<div class="mb-4 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
               Analysis based on a random sample of <strong>100,000</strong> rows from <strong>${fmtNum(ds.original_rows)}</strong> total rows.
           </div>`
        : '';

    el.innerHTML = `
        <div>
            <h2 class="text-xl font-bold text-slate-800 mb-4">Dataset Overview</h2>
            ${sampleBanner}
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                ${metricCard(fmtNum(ds.rows), 'Rows')}
                ${metricCard(fmtNum(ds.columns), 'Columns')}
                ${metricCard(ds.missing_pct + '%', 'Missing cells', missingColor(ds.missing_pct))}
                ${metricCard(ds.duplicate_pct + '%', 'Duplicate rows', ds.duplicate_pct > 5 ? 'text-yellow-600' : 'text-slate-900')}
                ${metricCard(fmtNum(ds.missing_total), 'Missing count')}
                ${metricCard(formatBytes(ds.memory_bytes), 'Memory')}
            </div>
        </div>`;
}

function metricCard(value, label, colorClass = 'text-slate-900') {
    return `<div class="bg-white border border-gray-200 rounded-xl p-4 text-center">
        <div class="text-2xl font-bold ${colorClass} leading-tight">${value}</div>
        <div class="text-xs text-slate-500 mt-1">${label}</div>
    </div>`;
}

// ─── Section B & C: Feature Table ────────────────────────────────────────────

function renderFeatureTable(features) {
    const el = document.getElementById('profiler-features');
    el.innerHTML = `
        <div>
            <h2 class="text-xl font-bold text-slate-800 mb-4">Features <span class="text-slate-400 font-normal text-base">(${features.length})</span></h2>
            <div class="bg-white border border-gray-200 rounded-2xl overflow-hidden">
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-50 border-b border-gray-200">
                            <tr>
                                ${thCell('name', 'Name', sortKey, sortAsc)}
                                ${thCell('type', 'Type', sortKey, sortAsc)}
                                ${thCell('missing_pct', 'Missing %', sortKey, sortAsc)}
                                ${thCell('unique_count', 'Unique', sortKey, sortAsc)}
                                <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Key stat</th>
                            </tr>
                        </thead>
                        <tbody id="feature-tbody">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>`;

    renderFeatureTbody(features);
}

function thCell(key, label, currentKey, asc) {
    const active = currentKey === key;
    const arrow = active ? (asc ? ' ↑' : ' ↓') : '';
    return `<th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide cursor-pointer hover:text-slate-700 select-none"
                onclick="setSortKey('${key}')">${label}${arrow}</th>`;
}

function setSortKey(key) {
    if (sortKey === key) sortAsc = !sortAsc;
    else { sortKey = key; sortAsc = true; }
    if (profileData) {
        renderFeatureTable(profileData.features);
    }
}

function renderFeatureTbody(features) {
    const sorted = [...features].sort((a, b) => {
        let av = a[sortKey], bv = b[sortKey];
        if (typeof av === 'string') av = av.toLowerCase();
        if (typeof bv === 'string') bv = bv.toLowerCase();
        if (av < bv) return sortAsc ? -1 : 1;
        if (av > bv) return sortAsc ? 1 : -1;
        return 0;
    });

    const tbody = document.getElementById('feature-tbody');
    tbody.innerHTML = '';

    sorted.forEach((f, idx) => {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors';
        row.setAttribute('data-feature', f.name);
        row.innerHTML = `
            <td class="px-4 py-3 font-medium text-slate-800 max-w-[160px] truncate" title="${esc(f.name)}">${esc(f.name)}</td>
            <td class="px-4 py-3">${typeBadge(f.type)}</td>
            <td class="px-4 py-3 font-mono text-sm"><span class="${missingColor(f.missing_pct)} font-semibold">${f.missing_pct}%</span></td>
            <td class="px-4 py-3 text-slate-600">${fmtNum(f.unique_count)}</td>
            <td class="px-4 py-3 text-slate-500 text-xs">${keyStatLabel(f)}</td>`;
        row.addEventListener('click', () => toggleDetail(f, row));
        tbody.appendChild(row);

        const detailRow = document.createElement('tr');
        detailRow.id = `detail-${CSS.escape(f.name)}`;
        detailRow.className = 'hidden bg-slate-50';
        detailRow.innerHTML = `<td colspan="5" class="px-6 py-5">${renderDetailHTML(f)}</td>`;
        tbody.appendChild(detailRow);
    });
}

function toggleDetail(f, row) {
    const detailRow = document.getElementById(`detail-${CSS.escape(f.name)}`);
    if (!detailRow) return;
    const isOpen = !detailRow.classList.contains('hidden');
    detailRow.classList.toggle('hidden', isOpen);
    row.classList.toggle('bg-blue-50', !isOpen);
    if (!isOpen) {
        initDetailCharts(f);
    }
}

// ─── Section C: Per-Feature Detail ───────────────────────────────────────────

function renderDetailHTML(f) {
    let html = `<div class="grid lg:grid-cols-2 gap-6">`;

    // Stats table
    html += `<div>
        <h4 class="text-sm font-semibold text-slate-600 mb-2 uppercase tracking-wide">Statistics</h4>
        <div class="bg-white rounded-xl border border-gray-200 overflow-hidden text-sm">
            <table class="w-full">
                <tbody>
                    ${statRow('Type', f.type)}
                    ${statRow('dtype', f.dtype)}
                    ${statRow('Missing', f.missing_count + ' (' + f.missing_pct + '%)')}
                    ${statRow('Unique', fmtNum(f.unique_count) + ' (' + f.unique_pct + '%)')}`;

    if (f.type === 'numeric' && f.stats) {
        html += statRow('Mean', fmtNum6(f.stats.mean));
        html += statRow('Median', fmtNum6(f.stats.median));
        html += statRow('Std dev', fmtNum6(f.stats.std));
        html += statRow('Min', fmtNum6(f.stats.min));
        html += statRow('Max', fmtNum6(f.stats.max));
        html += statRow('Q1 / Q3', fmtNum6(f.stats.q1) + ' / ' + fmtNum6(f.stats.q3));
        html += statRow('IQR', fmtNum6(f.stats.iqr));
        if (f.stats.skewness !== null) html += statRow('Skewness', f.stats.skewness);
        if (f.stats.kurtosis !== null) html += statRow('Kurtosis', f.stats.kurtosis);
    } else if (f.type === 'categorical' && f.stats) {
        html += statRow('Mode', esc(String(f.stats.mode ?? '—')));
    } else if (f.type === 'datetime' && f.stats) {
        html += statRow('Min date', f.stats.min_date ?? '—');
        html += statRow('Max date', f.stats.max_date ?? '—');
        html += statRow('Date range', f.stats.date_range_days != null ? f.stats.date_range_days + ' days' : '—');
    } else if (f.type === 'text' && f.stats) {
        html += statRow('Avg length', f.stats.avg_length);
        html += statRow('Min length', f.stats.min_length);
        html += statRow('Max length', f.stats.max_length);
    }

    html += `</tbody></table></div></div>`;

    // Charts column
    html += `<div class="space-y-4">`;

    if (f.type === 'numeric') {
        if (f.histogram && f.histogram.length) {
            html += `<div>
                <h4 class="text-sm font-semibold text-slate-600 mb-2 uppercase tracking-wide">Distribution</h4>
                <div class="bg-white rounded-xl border border-gray-200 p-3">
                    <canvas id="hist-${CSS.escape(f.name)}" height="140"></canvas>
                </div>
            </div>`;
        }
        if (f.box_plot) {
            html += `<div>
                <h4 class="text-sm font-semibold text-slate-600 mb-2 uppercase tracking-wide">Box Plot</h4>
                <div id="boxplot-${CSS.escape(f.name)}" class="bg-white rounded-xl border border-gray-200 p-4">
                </div>
            </div>`;
        }
    } else if ((f.type === 'categorical' || f.type === 'text') && f.top_values && f.top_values.length) {
        html += `<div>
            <h4 class="text-sm font-semibold text-slate-600 mb-2 uppercase tracking-wide">Top values</h4>
            <div class="bg-white rounded-xl border border-gray-200 p-3">
                <canvas id="bar-${CSS.escape(f.name)}" height="180"></canvas>
            </div>
        </div>`;
    }

    html += `</div></div>`;
    return html;
}

function initDetailCharts(f) {
    if (f.type === 'numeric') {
        if (f.histogram && f.histogram.length) {
            const canvas = document.getElementById(`hist-${CSS.escape(f.name)}`);
            if (canvas) renderHistogram(canvas, f.histogram, f.name);
        }
        if (f.box_plot) {
            const container = document.getElementById(`boxplot-${CSS.escape(f.name)}`);
            if (container) renderBoxPlot(container, f.box_plot);
        }
    } else if ((f.type === 'categorical' || f.type === 'text') && f.top_values) {
        const canvas = document.getElementById(`bar-${CSS.escape(f.name)}`);
        if (canvas) renderBarChart(canvas, f.top_values, f.name);
    }
}

// ─── Chart helpers ───────────────────────────────────────────────────────────

function renderHistogram(canvas, bins, name) {
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    const labels = bins.map(b => fmtNum6(b.bin_start));
    const counts = bins.map(b => b.count);

    chartInstances[`hist-${name}`] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: counts,
                backgroundColor: 'rgba(59,130,246,0.6)',
                borderColor: 'rgba(59,130,246,0.9)',
                borderWidth: 1,
                borderRadius: 2,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false }, tooltip: {
                callbacks: { title: (items) => {
                    const i = items[0].dataIndex;
                    return `${fmtNum6(bins[i].bin_start)} – ${fmtNum6(bins[i].bin_end)}`;
                }}
            }},
            scales: {
                x: { ticks: { maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
                y: { ticks: { font: { size: 10 } }, grid: { color: 'rgba(0,0,0,0.05)' } }
            }
        }
    });
}

function renderBarChart(canvas, topValues, name) {
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    const labels = topValues.map(v => v.value.length > 20 ? v.value.slice(0, 20) + '…' : v.value);
    const counts = topValues.map(v => v.count);

    chartInstances[`bar-${name}`] = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                data: counts,
                backgroundColor: topValues.map((_, i) => i < topValues.length - 1 || topValues[topValues.length-1].value !== 'Other'
                    ? 'rgba(99,102,241,0.65)' : 'rgba(148,163,184,0.6)'),
                borderColor: topValues.map((_, i) => i < topValues.length - 1 || topValues[topValues.length-1].value !== 'Other'
                    ? 'rgba(99,102,241,0.9)' : 'rgba(148,163,184,0.8)'),
                borderWidth: 1,
                borderRadius: 3,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false }, tooltip: {
                callbacks: { label: (item) => {
                    const v = topValues[item.dataIndex];
                    return ` ${fmtNum(v.count)} (${v.pct}%)`;
                }}
            }},
            scales: {
                x: { ticks: { font: { size: 10 } }, grid: { color: 'rgba(0,0,0,0.05)' } },
                y: { ticks: { font: { size: 10 } }, grid: { display: false } }
            }
        }
    });
}

function renderBoxPlot(container, bp) {
    const range = bp.whisker_high - bp.whisker_low;
    if (range === 0) {
        container.innerHTML = `<p class="text-slate-400 text-sm text-center py-2">No variation in values</p>`;
        return;
    }
    const pct = v => Math.max(0, Math.min(100, ((v - bp.whisker_low) / range) * 100)).toFixed(2);
    const q1p = pct(bp.q1);
    const medp = pct(bp.median);
    const q3p = pct(bp.q3);
    const boxW = (parseFloat(pct(bp.q3)) - parseFloat(pct(bp.q1))).toFixed(2);

    container.innerHTML = `
        <div class="text-xs text-slate-500 mb-1 flex justify-between">
            <span>${fmtNum6(bp.whisker_low)}</span>
            <span>${fmtNum6(bp.whisker_high)}</span>
        </div>
        <div class="relative h-8 flex items-center my-2">
            <div class="absolute h-px bg-gray-400 left-0 right-0"></div>
            <div class="absolute h-6 bg-blue-200 border-2 border-blue-400 rounded-sm"
                 style="left:${q1p}%;width:${boxW}%"></div>
            <div class="absolute h-6 w-0.5 bg-blue-700"
                 style="left:${medp}%"></div>
        </div>
        <div class="flex justify-between text-xs text-slate-500 mt-1">
            <span>Q1: ${fmtNum6(bp.q1)}</span>
            <span>Med: ${fmtNum6(bp.median)}</span>
            <span>Q3: ${fmtNum6(bp.q3)}</span>
        </div>
        ${bp.outlier_count > 0 ? `<p class="text-xs text-orange-600 mt-2">⚠ ${fmtNum(bp.outlier_count)} outlier${bp.outlier_count !== 1 ? 's' : ''} (IQR method)</p>` : ''}`;
}

// ─── Section D: Correlation Heatmap ──────────────────────────────────────────

function renderCorrelations(corr) {
    const el = document.getElementById('profiler-correlations');
    if (!corr || !corr.columns.length) {
        el.innerHTML = '';
        return;
    }

    const cols = corr.columns;
    let tableHTML = `<table class="text-xs border-collapse w-full">
        <thead><tr>
            <th class="p-1 text-left text-slate-400"></th>`;
    cols.forEach(c => {
        const short = c.length > 10 ? c.slice(0, 10) + '…' : c;
        tableHTML += `<th class="p-1 text-slate-500 font-medium text-center max-w-[60px] overflow-hidden" title="${esc(c)}">${esc(short)}</th>`;
    });
    tableHTML += `</tr></thead><tbody>`;

    corr.matrix.forEach((row, ri) => {
        tableHTML += `<tr><td class="p-1 pr-2 text-slate-500 font-medium text-right whitespace-nowrap" title="${esc(cols[ri])}">${esc(cols[ri].length > 12 ? cols[ri].slice(0, 12) + '…' : cols[ri])}</td>`;
        row.forEach((val, ci) => {
            const bg = corrColor(val);
            const textColor = val !== null && Math.abs(val) > 0.6 ? '#1e40af' : '#374151';
            const display = val !== null ? val.toFixed(2) : '—';
            tableHTML += `<td style="background:${bg};color:${textColor}" class="p-1 text-center border border-white rounded" title="${cols[ri]} × ${cols[ci]}: ${display}">${display}</td>`;
        });
        tableHTML += `</tr>`;
    });

    tableHTML += `</tbody></table>`;

    el.innerHTML = `
        <div>
            <h2 class="text-xl font-bold text-slate-800 mb-4">Correlation Matrix <span class="text-slate-400 font-normal text-base">(numeric columns)</span></h2>
            <div class="bg-white border border-gray-200 rounded-2xl p-4 overflow-x-auto">
                ${tableHTML}
                <p class="text-xs text-slate-400 mt-3">Pearson correlation coefficients. Values near +1 or −1 indicate strong correlation.</p>
            </div>
        </div>`;
}

function corrColor(val) {
    if (val === null || val === undefined) return '#f3f4f6';
    const abs = Math.abs(val);
    const lightness = Math.round(97 - abs * 28);
    const saturation = Math.round(abs * 75);
    return val >= 0
        ? `hsl(220,${saturation}%,${lightness}%)`
        : `hsl(0,${saturation}%,${lightness}%)`;
}

// ─── Utilities ────────────────────────────────────────────────────────────────

function fmtNum(n) {
    if (n == null) return '—';
    return Number(n).toLocaleString();
}

function fmtNum6(n) {
    if (n == null) return '—';
    const v = parseFloat(n);
    return isNaN(v) ? String(n) : (Number.isInteger(v) ? v.toLocaleString() : parseFloat(v.toPrecision(6)).toLocaleString());
}

function formatBytes(bytes) {
    if (bytes == null) return '—';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function esc(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function missingColor(pct) {
    if (pct > 20) return 'text-red-600';
    if (pct > 5) return 'text-yellow-600';
    return 'text-green-600';
}

function typeBadge(type) {
    const styles = {
        numeric: 'bg-blue-100 text-blue-700',
        categorical: 'bg-purple-100 text-purple-700',
        datetime: 'bg-green-100 text-green-700',
        text: 'bg-gray-100 text-gray-600',
    };
    return `<span class="px-2 py-0.5 rounded-full text-xs font-medium ${styles[type] || styles.text}">${type}</span>`;
}

function keyStatLabel(f) {
    if (f.type === 'numeric' && f.stats && f.stats.mean != null) return `mean: ${fmtNum6(f.stats.mean)}`;
    if (f.type === 'categorical' && f.stats && f.stats.mode != null) return `mode: ${esc(String(f.stats.mode))}`;
    if (f.type === 'datetime' && f.stats && f.stats.min_date) return f.stats.min_date + ' → ' + f.stats.max_date;
    if (f.type === 'text' && f.stats && f.stats.avg_length != null) return `avg len: ${f.stats.avg_length}`;
    return '—';
}

function statRow(label, value) {
    return `<tr class="border-b border-gray-50 last:border-0">
        <td class="px-3 py-2 text-slate-500 font-medium w-28">${label}</td>
        <td class="px-3 py-2 text-slate-800 font-mono text-xs">${esc(String(value))}</td>
    </tr>`;
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initProfilerDropZone();
});
