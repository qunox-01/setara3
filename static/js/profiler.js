/**
 * xariff — profiler.js
 * Dataset Profiler: upload, analyse, render results with charts.
 */

// ─── State ──────────────────────────────────────────────────────────────────

let profileData = null;
let sortKey = 'name';
let sortAsc = true;
const chartInstances = {};

function hasProfilerConsent() {
    return !!document.getElementById('profiler-legal-consent')?.checked;
}

function updateProfilerAnalyseButton() {
    const hasFile = !!document.getElementById('profiler-file-input')?.files?.[0];
    const btn = document.getElementById('profiler-analyse-btn');
    if (btn) btn.disabled = !(hasFile && hasProfilerConsent());
}

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
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
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
    updateProfilerAnalyseButton();
}

// ─── Upload & Analyse ────────────────────────────────────────────────────────

async function startProfiler() {
    const input = document.getElementById('profiler-file-input');
    if (!input.files[0]) return;
    if (!hasProfilerConsent()) {
        showBanner('Please accept Terms, Privacy Policy, and Cookie Policy first.', 'error');
        return;
    }
    const file = input.files[0];

    setState('loading');
    document.getElementById('profiler-loading-filename').textContent = `${file.name} · ${formatBytes(file.size)}`;

    const form = new FormData();
    form.append('file', file);
    form.append('accept_legal', 'true');
    form.append('policy_version', '2026-03-16');

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
            if (hasProfilerConsent()) {
                setTimeout(startProfiler, 200);
            } else {
                showBanner('Sample loaded. Accept legal terms, then click "Profile dataset".', 'info');
            }
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
    renderDistributions(data.features);
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
            <div class="grid grid-cols-3 gap-3">
                ${metricCard(fmtNum(ds.rows), 'Rows')}
                ${metricCard(fmtNum(ds.columns), 'Columns')}
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
    // ── Metadata pills ────────────────────────────────────────────────────────
    const metaPills = `
        <div class="flex flex-wrap gap-2 mb-4 text-xs">
            <span class="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-full">dtype: <strong>${esc(f.dtype)}</strong></span>
            <span class="px-2.5 py-1 ${f.missing_pct > 20 ? 'bg-red-50 text-red-700' : f.missing_pct > 5 ? 'bg-yellow-50 text-yellow-700' : 'bg-green-50 text-green-700'} rounded-full">
                missing: <strong>${f.missing_count} (${f.missing_pct}%)</strong>
            </span>
            <span class="px-2.5 py-1 bg-slate-100 text-slate-600 rounded-full">unique: <strong>${fmtNum(f.unique_count)} (${f.unique_pct}%)</strong></span>
        </div>`;

    let html = `<div>${metaPills}`;

    if (f.type === 'numeric' && f.stats) {
        // ── Two stat cards + charts ───────────────────────────────────────────
        html += `<div class="grid lg:grid-cols-2 gap-4 mb-4">`;

        // Card 1: Central tendency
        html += `<div>
            <h4 class="text-xs font-semibold text-blue-600 uppercase tracking-wider mb-2">Central tendency</h4>
            <div class="bg-white rounded-xl border border-gray-200 overflow-hidden text-sm">
                <table class="w-full">
                    <tbody>
                        ${statRow('Mean', fmtNum6(f.stats.mean), 'Average value')}
                        ${statRow('Median', fmtNum6(f.stats.median), 'Middle value')}
                        ${statRow('Mode', fmtNum6(f.stats.mode), 'Most common value')}
                    </tbody>
                </table>
            </div>
        </div>`;

        // Card 2: Spread / variability
        const spreadRows = [
            statRow('Std deviation', fmtNum6(f.stats.std), 'σ'),
            statRow('Variance', fmtNum6(f.stats.variance), 'σ²'),
            statRow('Min', fmtNum6(f.stats.min)),
            statRow('Max', fmtNum6(f.stats.max)),
            statRow('Range', fmtNum6(f.stats.range), 'Max − Min'),
            statRow('IQR', fmtNum6(f.stats.iqr), 'Q3 − Q1'),
            statRow('Q1 / Q3', `${fmtNum6(f.stats.q1)} / ${fmtNum6(f.stats.q3)}`),
            f.stats.skewness !== null ? statRow('Skewness', f.stats.skewness) : '',
            f.stats.kurtosis !== null ? statRow('Kurtosis', f.stats.kurtosis) : '',
        ].join('');

        html += `<div>
            <h4 class="text-xs font-semibold text-purple-600 uppercase tracking-wider mb-2">Spread / variability</h4>
            <div class="bg-white rounded-xl border border-gray-200 overflow-hidden text-sm">
                <table class="w-full"><tbody>${spreadRows}</tbody></table>
            </div>
        </div>`;

        html += `</div>`; // end two-card grid

        // Charts row
        html += `<div class="grid lg:grid-cols-2 gap-4">`;
        if (f.histogram && f.histogram.length) {
            html += `<div>
                <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Distribution</h4>
                <div class="bg-white rounded-xl border border-gray-200 p-3">
                    <canvas id="hist-${CSS.escape(f.name)}" height="140"></canvas>
                </div>
            </div>`;
        }
        if (f.box_plot) {
            html += `<div>
                <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Box Plot</h4>
                <div id="boxplot-${CSS.escape(f.name)}" class="bg-white rounded-xl border border-gray-200 p-4"></div>
            </div>`;
        }
        html += `</div>`;

    } else {
        // ── Non-numeric: single stats table + chart ───────────────────────────
        html += `<div class="grid lg:grid-cols-2 gap-4">`;
        html += `<div>
            <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Statistics</h4>
            <div class="bg-white rounded-xl border border-gray-200 overflow-hidden text-sm">
                <table class="w-full"><tbody>`;

        if (f.type === 'categorical' && f.stats) {
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

        if ((f.type === 'categorical' || f.type === 'text') && f.top_values && f.top_values.length) {
            html += `<div>
                <h4 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Top values</h4>
                <div class="bg-white rounded-xl border border-gray-200 p-3">
                    <canvas id="bar-${CSS.escape(f.name)}" height="180"></canvas>
                </div>
            </div>`;
        }

        html += `</div>`;
    }

    html += `</div>`;
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

// ─── Section E: Numeric Distributions ────────────────────────────────────────

function classifyDistribution(skewness, kurtosis) {
    if (skewness == null) return { label: null, color: 'gray', desc: '' };
    const s = skewness, k = kurtosis ?? 0;
    if (Math.abs(s) <= 0.5 && k > 2)  return { label: 'Heavy-tailed',       color: 'amber',  desc: 'Excess kurtosis — more extreme values than a normal distribution' };
    if (Math.abs(s) <= 0.5 && k < -1) return { label: 'Light-tailed',        color: 'teal',   desc: 'Platykurtic — fewer extreme values than normal' };
    if (Math.abs(s) <= 0.5)            return { label: 'Normal-like',         color: 'green',  desc: 'Approximately symmetric and bell-shaped' };
    if (s > 1)                         return { label: 'Highly right-skewed', color: 'red',    desc: 'Heavy right tail — consider log transform' };
    if (s > 0.5)                       return { label: 'Right-skewed',        color: 'orange', desc: 'Tail extends to the right' };
    if (s < -1)                        return { label: 'Highly left-skewed',  color: 'red',    desc: 'Heavy left tail' };
    return                                    { label: 'Left-skewed',         color: 'purple', desc: 'Tail extends to the left' };
}

function buildBoxPlotSVG(bp, stats) {
    const W = 520, H = 130;
    const PL = 14, PR = 14;
    const plotW = W - PL - PR;

    // Scale bounds — extend to include outliers so dots don't clip
    let lo = bp.whisker_low, hi = bp.whisker_high;
    if (bp.outlier_values?.length) {
        lo = Math.min(lo, Math.min(...bp.outlier_values));
        hi = Math.max(hi, Math.max(...bp.outlier_values));
    }
    const span = (hi - lo) || 1;
    const pad  = span * 0.07;
    lo -= pad; hi += pad;
    const range = hi - lo;
    const px = v => PL + ((v - lo) / range) * plotW;

    const BOX_Y = 42, BOX_H = 34, BOX_MID = BOX_Y + BOX_H / 2;

    const xWL   = px(bp.whisker_low);
    const xQ1   = px(bp.q1);
    const xMed  = px(bp.median);
    const xQ3   = px(bp.q3);
    const xWH   = px(bp.whisker_high);
    const xMean = stats?.mean != null ? px(stats.mean) : null;

    // Clamp label anchor x to stay inside viewBox
    const clamp = x => Math.max(PL + 24, Math.min(W - PR - 24, x));

    let s = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" class="w-full" style="max-height:${H}px">`;

    // ── Whisker lines ─────────────────────────────────────────────────────────
    s += `<line x1="${xWL}" y1="${BOX_MID}" x2="${xQ1}"  y2="${BOX_MID}" stroke="#cbd5e1" stroke-width="1.5"/>`;
    s += `<line x1="${xQ3}" y1="${BOX_MID}" x2="${xWH}"  y2="${BOX_MID}" stroke="#cbd5e1" stroke-width="1.5"/>`;
    // End caps
    const capH = 12;
    s += `<line x1="${xWL}" y1="${BOX_MID - capH/2}" x2="${xWL}" y2="${BOX_MID + capH/2}" stroke="#94a3b8" stroke-width="2"/>`;
    s += `<line x1="${xWH}" y1="${BOX_MID - capH/2}" x2="${xWH}" y2="${BOX_MID + capH/2}" stroke="#94a3b8" stroke-width="2"/>`;

    // ── IQR box ───────────────────────────────────────────────────────────────
    const boxW = Math.max(2, xQ3 - xQ1);
    s += `<rect x="${xQ1}" y="${BOX_Y}" width="${boxW}" height="${BOX_H}" fill="rgba(59,130,246,0.13)" stroke="#3b82f6" stroke-width="1.5" rx="3"/>`;

    // ── Median line ───────────────────────────────────────────────────────────
    s += `<line x1="${xMed}" y1="${BOX_Y}" x2="${xMed}" y2="${BOX_Y + BOX_H}" stroke="#1d4ed8" stroke-width="2.5"/>`;

    // ── Mean diamond ─────────────────────────────────────────────────────────
    if (xMean !== null) {
        const d = 5;
        s += `<polygon points="${xMean},${BOX_MID-d} ${xMean+d},${BOX_MID} ${xMean},${BOX_MID+d} ${xMean-d},${BOX_MID}" fill="#fbbf24" stroke="#d97706" stroke-width="1.2"/>`;
    }

    // ── Outlier dots (deterministic jitter on y so stacked values spread) ────
    if (bp.outlier_values?.length) {
        bp.outlier_values.forEach((v, i) => {
            const x = px(v);
            const jitter = ((i * 7 + 3) % 9 - 4) * 0.9;
            s += `<circle cx="${x}" cy="${BOX_MID + jitter}" r="3" fill="rgba(239,68,68,0.38)" stroke="rgba(220,38,38,0.65)" stroke-width="0.8"/>`;
        });
    }

    // ── Labels above box: Q1, Median, Q3 ─────────────────────────────────────
    const aboveY  = BOX_Y - 4;
    const tickLen = 9;

    const aboveLabel = (x, text, color) => {
        const cx = clamp(x);
        return `<line x1="${x}" y1="${aboveY}" x2="${cx}" y2="${aboveY - tickLen}" stroke="${color}" stroke-width="0.8" opacity="0.55"/>` +
               `<text x="${cx}" y="${aboveY - tickLen - 3}" text-anchor="middle" font-size="9" fill="${color}" font-family="ui-monospace,monospace">${text}</text>`;
    };

    s += aboveLabel(xQ1,  `Q1 ${fmtNum6(bp.q1)}`,       '#3b82f6');
    s += aboveLabel(xMed, `Med ${fmtNum6(bp.median)}`,   '#1d4ed8');
    s += aboveLabel(xQ3,  `Q3 ${fmtNum6(bp.q3)}`,       '#3b82f6');

    // ── Labels below box: Min, Mean, Max ─────────────────────────────────────
    const belowY = BOX_Y + BOX_H + 4;

    const belowLabel = (x, text, color) => {
        const cx = clamp(x);
        return `<line x1="${x}" y1="${belowY}" x2="${cx}" y2="${belowY + tickLen}" stroke="${color}" stroke-width="0.8" opacity="0.55"/>` +
               `<text x="${cx}" y="${belowY + tickLen + 11}" text-anchor="middle" font-size="9" fill="${color}" font-family="ui-monospace,monospace">${text}</text>`;
    };

    s += belowLabel(xWL, `Min ${fmtNum6(bp.whisker_low)}`,  '#64748b');
    s += belowLabel(xWH, `Max ${fmtNum6(bp.whisker_high)}`, '#64748b');
    if (xMean !== null) {
        s += belowLabel(xMean, `Mean ${fmtNum6(stats.mean)}`, '#d97706');
    }

    s += '</svg>';
    return s;
}

function renderDistributionHistogram(canvas, bins, stats) {
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    // Pick bar color by distribution shape
    const s = stats?.skewness ?? 0;
    const k = stats?.kurtosis ?? 0;
    let color;
    if (Math.abs(s) <= 0.5 && k > 2)  color = 'rgba(245,158,11,0.65)';   // amber  — heavy-tailed
    else if (Math.abs(s) <= 0.5)       color = 'rgba(99,102,241,0.65)';   // indigo — normal-like
    else if (s > 0)                    color = 'rgba(249,115,22,0.65)';   // orange — right-skewed
    else                               color = 'rgba(168,85,247,0.65)';   // purple — left-skewed

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: bins.map(b => fmtNum6(b.bin_start)),
            datasets: [{
                data: bins.map(b => b.count),
                backgroundColor: color,
                borderColor: color.replace('0.65', '0.9'),
                borderWidth: 1,
                borderRadius: 2,
                barPercentage: 1.0,
                categoryPercentage: 1.0,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: items => {
                            const i = items[0].dataIndex;
                            return `${fmtNum6(bins[i].bin_start)} – ${fmtNum6(bins[i].bin_end)}`;
                        },
                        label: item => ` count: ${fmtNum(item.raw)}`,
                    }
                }
            },
            scales: {
                x: { ticks: { maxTicksLimit: 5, font: { size: 9 } }, grid: { display: false } },
                y: { ticks: { font: { size: 9 } }, grid: { color: 'rgba(0,0,0,0.04)' } }
            }
        }
    });
}

function renderDistributions(features) {
    const el = document.getElementById('profiler-distributions');
    if (!el) return;

    const numFeatures = features.filter(f => f.type === 'numeric');
    if (!numFeatures.length) { el.innerHTML = ''; return; }

    const badgeClass = {
        green:  'bg-green-100 text-green-700',
        orange: 'bg-orange-100 text-orange-700',
        red:    'bg-red-100 text-red-700',
        purple: 'bg-purple-100 text-purple-700',
        amber:  'bg-amber-100 text-amber-700',
        teal:   'bg-teal-100 text-teal-700',
        gray:   'bg-gray-100 text-gray-500',
    };

    const cards = numFeatures.map(f => {
        const dist = classifyDistribution(f.stats?.skewness, f.stats?.kurtosis);
        const badge = dist.label
            ? `<span class="px-2 py-0.5 rounded-full text-xs font-medium ${badgeClass[dist.color] || badgeClass.gray}">${dist.label}</span>`
            : '';
        const statsLine = [
            f.stats?.skewness != null ? `skew ${f.stats.skewness}` : null,
            f.stats?.kurtosis != null ? `kurt ${f.stats.kurtosis}` : null,
        ].filter(Boolean).join(' · ');

        const histPanel = f.histogram?.length ? `
            <div>
                <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Histogram</p>
                <div class="rounded-xl bg-slate-50 p-2">
                    <canvas id="dist-hist-${CSS.escape(f.name)}" height="110"></canvas>
                </div>
                ${dist.desc ? `<p class="text-xs text-slate-400 mt-1.5 italic leading-tight">${dist.desc}</p>` : ''}
            </div>` : '<div></div>';

        const outlierNote = f.box_plot?.outlier_count > 0
            ? `<span class="inline-flex items-center gap-1 text-red-400"><span class="w-2 h-2 rounded-full bg-red-400 inline-block opacity-60"></span>${fmtNum(f.box_plot.outlier_count)} outlier${f.box_plot.outlier_count !== 1 ? 's' : ''}</span>`
            : '';

        const boxPanel = f.box_plot ? `
            <div>
                <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Box Plot</p>
                <div class="rounded-xl bg-slate-50 p-3">
                    <div id="dist-box-${CSS.escape(f.name)}"></div>
                </div>
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-xs text-slate-400">
                    <span class="inline-flex items-center gap-1"><span class="w-3 h-0.5 bg-blue-300 inline-block rounded"></span>IQR box</span>
                    <span class="inline-flex items-center gap-1"><span class="w-0.5 h-3 bg-blue-700 inline-block"></span>Median</span>
                    <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 bg-amber-400 rotate-45"></span>Mean</span>
                    ${outlierNote}
                </div>
            </div>` : '';

        return `
        <div class="bg-white border border-gray-200 rounded-2xl p-5">
            <div class="flex items-start justify-between gap-2 mb-4">
                <h3 class="font-semibold text-slate-800 text-sm truncate">${esc(f.name)}</h3>
                <div class="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                    ${badge}
                    ${statsLine ? `<span class="text-xs text-slate-400 font-mono">${statsLine}</span>` : ''}
                </div>
            </div>
            <div class="grid sm:grid-cols-2 gap-4">
                ${histPanel}
                ${boxPanel}
            </div>
        </div>`;
    }).join('');

    el.innerHTML = `
        <div>
            <h2 class="text-xl font-bold text-slate-800 mb-4">
                Numeric Distributions
                <span class="text-slate-400 font-normal text-base">(${numFeatures.length} feature${numFeatures.length !== 1 ? 's' : ''})</span>
            </h2>
            <div class="grid lg:grid-cols-2 gap-5">${cards}</div>
        </div>`;

    numFeatures.forEach(f => {
        if (f.histogram?.length) {
            const canvas = document.getElementById(`dist-hist-${CSS.escape(f.name)}`);
            if (canvas) renderDistributionHistogram(canvas, f.histogram, f.stats);
        }
        if (f.box_plot) {
            const container = document.getElementById(`dist-box-${CSS.escape(f.name)}`);
            if (container) container.innerHTML = buildBoxPlotSVG(f.box_plot, f.stats);
        }
    });
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
    if (f.type === 'numeric' && f.stats) {
        const parts = [];
        if (f.stats.mean != null) parts.push(`mean: ${fmtNum6(f.stats.mean)}`);
        if (f.stats.std != null) parts.push(`σ: ${fmtNum6(f.stats.std)}`);
        return parts.join(' · ') || '—';
    }
    if (f.type === 'categorical' && f.stats && f.stats.mode != null) return `mode: ${esc(String(f.stats.mode))}`;
    if (f.type === 'datetime' && f.stats && f.stats.min_date) return f.stats.min_date + ' → ' + f.stats.max_date;
    if (f.type === 'text' && f.stats && f.stats.avg_length != null) return `avg len: ${f.stats.avg_length}`;
    return '—';
}

function statRow(label, value, hint = '') {
    const hintHtml = hint ? `<span class="ml-1 text-slate-400 font-normal">(${hint})</span>` : '';
    return `<tr class="border-b border-gray-50 last:border-0">
        <td class="px-3 py-2 text-slate-500 font-medium w-36 whitespace-nowrap">${label}${hintHtml}</td>
        <td class="px-3 py-2 text-slate-800 font-mono text-xs">${esc(String(value))}</td>
    </tr>`;
}

function statSectionHeader(label) {
    return `<tr class="bg-slate-50 border-b border-gray-100">
        <td colspan="2" class="px-3 py-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">${label}</td>
    </tr>`;
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initProfilerDropZone();
    document.getElementById('profiler-legal-consent')?.addEventListener('change', updateProfilerAnalyseButton);
});
