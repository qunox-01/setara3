/**
 * outliers.js — Outlier Detector Tool
 * Handles file upload, API call, and all result rendering.
 */

// ─── State ───────────────────────────────────────────────────────────────────

let outliersData = null;
let outliersFile = null;
let advancedOpen = false;
let scoreChartCanvas = null;

// ─── File Input / Drag-Drop ───────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('outliers-file-input');
    const dropZone  = document.getElementById('drop-zone-outliers');

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files[0]) onFileSelected(fileInput.files[0]);
        });
    }

    if (dropZone) {
        ['dragenter','dragover','dragleave','drop'].forEach(e =>
            dropZone.addEventListener(e, ev => { ev.preventDefault(); ev.stopPropagation(); })
        );
        ['dragenter','dragover'].forEach(e =>
            dropZone.addEventListener(e, () => dropZone.classList.add('border-rose-400','bg-rose-50'))
        );
        ['dragleave','drop'].forEach(e =>
            dropZone.addEventListener(e, () => dropZone.classList.remove('border-rose-400','bg-rose-50'))
        );
        dropZone.addEventListener('drop', ev => {
            const f = ev.dataTransfer.files[0];
            if (!f) return;
            if (!f.name.toLowerCase().endsWith('.csv')) {
                showError('Only CSV files are supported.');
                return;
            }
            const dt = new DataTransfer();
            dt.items.add(f);
            fileInput.files = dt.files;
            onFileSelected(f);
        });
    }
});

function onFileSelected(file) {
    outliersFile = file;
    const nameEl = document.getElementById('outliers-file-name');
    if (nameEl) { nameEl.textContent = file.name; nameEl.classList.remove('hidden'); }
    const btn = document.getElementById('outliers-analyse-btn');
    if (btn) btn.disabled = false;
}

// ─── Advanced Panel Toggle ────────────────────────────────────────────────────

function toggleAdvanced() {
    advancedOpen = !advancedOpen;
    const panel   = document.getElementById('advanced-params');
    const chevron = document.getElementById('advanced-chevron');
    if (panel)   panel.classList.toggle('hidden', !advancedOpen);
    if (chevron) chevron.style.transform = advancedOpen ? 'rotate(90deg)' : '';
}

// ─── Sample Data ─────────────────────────────────────────────────────────────

async function loadOutliersSample() {
    try {
        const resp = await fetch('/sample-data/outliers');
        const blob = await resp.blob();
        const file = new File([blob], 'sample_outliers.csv', { type: 'text/csv' });
        const fileInput = document.getElementById('outliers-file-input');
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        onFileSelected(file);
        // Pre-fill label column and auto-run
        const labelInput = document.getElementById('label-col-input');
        if (labelInput) labelInput.value = 'label';
        startOutliers();
    } catch (e) {
        showError('Could not load sample data.');
    }
}

// ─── Main Analysis ────────────────────────────────────────────────────────────

async function startOutliers() {
    if (!outliersFile) return;

    const method        = document.getElementById('method-select')?.value || 'ensemble';
    const labelCol      = (document.getElementById('label-col-input')?.value || '').trim() || null;
    const contamination = parseFloat(document.getElementById('contamination-input')?.value || '0.05');
    const epsRaw        = document.getElementById('eps-input')?.value;
    const minSamplesRaw = document.getElementById('min-samples-input')?.value;

    setLoading(true);
    clearResults();

    const formData = new FormData();
    formData.append('file', outliersFile);

    const params = new URLSearchParams();
    params.set('method', method);
    params.set('contamination', String(contamination));
    if (labelCol)        params.set('label_col', labelCol);
    if (epsRaw)          params.set('eps', epsRaw);
    if (minSamplesRaw)   params.set('min_samples', minSamplesRaw);

    const url = '/api/tools/outliers/analyze?' + params.toString();

    try {
        const resp = await fetch(url, { method: 'POST', body: formData });
        const json = await resp.json();
        if (!resp.ok) {
            showError(json.detail || `Error ${resp.status}`);
            return;
        }
        outliersData = json;
        renderAll(json);
    } catch (e) {
        showError('Network error. Please try again.');
    } finally {
        setLoading(false);
    }
}

// ─── Render Orchestrator ──────────────────────────────────────────────────────

function renderAll(data) {
    document.getElementById('outliers-results').classList.remove('hidden');
    renderScoreBanner(data);
    renderMethodCards(data);
    renderScoreChart(data);
    renderFeatureContributions(data);
    renderOutlierRows(data);
}

// ─── Component 1: Score Banner ────────────────────────────────────────────────

function renderScoreBanner(data) {
    const { score, verdict, outlier_count, outlier_pct, consensus_count, total_rows, method } = data.summary;

    let gradient, verdictHtml, msg;
    if (score >= 80) {
        gradient   = 'from-green-50 to-emerald-50 border-green-200';
        verdictHtml = '<span class="text-green-700 font-bold">Healthy</span>';
        msg = `Only <strong>${outlier_count.toLocaleString()}</strong> row${outlier_count !== 1 ? 's' : ''} (${outlier_pct}%) were flagged as outliers — well within a normal range. Your dataset looks clean.`;
    } else if (score >= 50) {
        gradient   = 'from-yellow-50 to-amber-50 border-yellow-200';
        verdictHtml = '<span class="text-yellow-700 font-bold">Needs attention</span>';
        msg = `<strong>${outlier_count.toLocaleString()}</strong> rows (${outlier_pct}%) were flagged as outliers. Review the feature contributions and flagged rows to decide which ones to investigate.`;
    } else {
        gradient   = 'from-red-50 to-rose-50 border-red-200';
        verdictHtml = '<span class="text-red-700 font-bold">Critical</span>';
        msg = `A high proportion of rows (${outlier_pct}%) are anomalous. This may indicate data quality issues, incorrect contamination settings, or genuinely unusual data. Investigate before training.`;
    }

    const scoreColor = score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600';
    const ringColor  = score >= 80 ? 'border-green-400' : score >= 50 ? 'border-yellow-400' : 'border-red-400';

    const consensusNote = (method === 'ensemble' && consensus_count > 0)
        ? `<span class="px-2 py-1 bg-rose-100 text-rose-700 text-xs rounded-lg font-semibold">${consensus_count.toLocaleString()} consensus outliers</span>`
        : '';

    document.getElementById('outliers-score-banner').innerHTML = `
        <div class="bg-gradient-to-br ${gradient} border rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col sm:flex-row items-center gap-6">
                <div class="flex-shrink-0 w-28 h-28 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center bg-white shadow-inner">
                    <span class="text-4xl font-extrabold ${scoreColor}">${score}</span>
                    <span class="text-xs text-slate-500 font-medium">/ 100</span>
                </div>
                <div class="flex-1 text-center sm:text-left">
                    <p class="text-lg mb-1">${verdictHtml}</p>
                    <p class="text-slate-600 text-sm leading-relaxed">${msg}</p>
                    <div class="mt-3 flex flex-wrap gap-3 text-xs text-slate-500 justify-center sm:justify-start items-center">
                        <span><strong class="text-slate-700">${total_rows.toLocaleString()}</strong> rows analysed</span>
                        <span><strong class="text-slate-700">${data.summary.total_features}</strong> features</span>
                        <span><strong class="text-slate-700">${methodLabel(method)}</strong></span>
                        ${consensusNote}
                    </div>
                </div>
            </div>
        </div>`;
}

function methodLabel(method) {
    return { ensemble: 'Ensemble mode', isolation_forest: 'Isolation Forest', dbscan: 'DBSCAN' }[method] || method;
}

// ─── Component 2: Method Stats Cards ─────────────────────────────────────────

function renderMethodCards(data) {
    const container = document.getElementById('outliers-method-cards');
    const m = data.methods;

    let cards = '';

    if (m.isolation_forest) {
        const if_ = m.isolation_forest;
        cards += `
            <div class="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-9 h-9 bg-rose-100 rounded-xl flex items-center justify-center flex-shrink-0">
                        <svg class="w-5 h-5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-bold text-slate-800">Isolation Forest</p>
                        <p class="text-xs text-slate-400">Tree-based anomaly scoring</p>
                    </div>
                </div>
                <div class="space-y-2 text-sm">
                    ${statRow('Outliers flagged', `${if_.outlier_count.toLocaleString()} (${if_.outlier_pct}%)`)}
                    ${statRow('Contamination used', if_.contamination)}
                    ${statRow('Avg anomaly score', if_.avg_anomaly_score)}
                    ${if_.avg_outlier_score != null ? statRow('Avg outlier score', if_.avg_outlier_score) : ''}
                </div>
            </div>`;
    }

    if (m.dbscan) {
        const db = m.dbscan;
        const clusterList = Object.entries(db.cluster_sizes).slice(0, 5).map(([k,v]) =>
            `<span class="px-1.5 py-0.5 bg-slate-100 rounded text-xs">C${k}: ${v}</span>`
        ).join(' ');
        cards += `
            <div class="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-9 h-9 bg-violet-100 rounded-xl flex items-center justify-center flex-shrink-0">
                        <svg class="w-5 h-5 text-violet-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14v6m-3-3h6M6 10h.01M6 14h.01M10 10h.01M10 14h.01M14 10h.01" />
                        </svg>
                    </div>
                    <div>
                        <p class="font-bold text-slate-800">DBSCAN</p>
                        <p class="text-xs text-slate-400">Density-based clustering</p>
                    </div>
                </div>
                <div class="space-y-2 text-sm">
                    ${statRow('Noise points (outliers)', `${db.outlier_count.toLocaleString()} (${db.outlier_pct}%)`)}
                    ${statRow('Clusters found', db.n_clusters)}
                    ${statRow('Eps used', db.eps)}
                    ${statRow('Min samples', db.min_samples)}
                    ${db.n_clusters > 0 ? `<div class="mt-1 flex flex-wrap gap-1">${clusterList}</div>` : ''}
                </div>
            </div>`;
    }

    if (!cards) { container.innerHTML = ''; return; }

    container.innerHTML = `<div class="grid sm:grid-cols-2 gap-4">${cards}</div>`;
}

function statRow(label, value) {
    return `<div class="flex justify-between items-center border-b border-gray-50 pb-1.5">
        <span class="text-slate-500">${label}</span>
        <span class="font-semibold text-slate-800">${value}</span>
    </div>`;
}

// ─── Component 3: Anomaly Score Scatter ──────────────────────────────────────

function renderScoreChart(data) {
    const container = document.getElementById('outliers-score-chart');
    const hasDist   = data.score_distribution && data.score_distribution.length > 0;
    const hasIF     = data.methods.isolation_forest != null;

    if (!hasDist || !hasIF) {
        // DBSCAN only — show a cluster distribution bar chart
        renderClusterBars(data, container);
        return;
    }

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
                <div>
                    <h2 class="text-lg font-bold text-slate-800">Anomaly Score Distribution</h2>
                    <p class="text-xs text-slate-500 mt-0.5">Each point is a row. Score closer to 1 = more anomalous. Red = outlier, blue = inlier.</p>
                </div>
                ${data.summary.method === 'ensemble'
                    ? `<span class="text-xs px-2 py-1 bg-rose-100 text-rose-700 rounded-lg font-medium self-start sm:self-center">
                        Rose outline = consensus (both methods)
                       </span>`
                    : ''}
            </div>
            <div class="relative">
                <canvas id="score-scatter-canvas" style="width:100%;max-height:320px;"></canvas>
            </div>
            <div class="mt-3 flex flex-wrap gap-4 text-xs text-slate-500 items-center">
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full bg-blue-400"></span> Inlier</span>
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full bg-rose-500"></span> Outlier</span>
                ${data.summary.method === 'ensemble'
                    ? `<span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-full border-2 border-rose-500 bg-rose-200"></span> Consensus</span>`
                    : ''}
            </div>
        </div>`;

    requestAnimationFrame(() => drawScoreScatter(data));
}

function drawScoreScatter(data) {
    const canvas = document.getElementById('score-scatter-canvas');
    if (!canvas) return;
    scoreChartCanvas = canvas;

    const dpr = window.devicePixelRatio || 1;
    const W   = canvas.offsetWidth || 600;
    const H   = Math.min(320, W * 0.5);
    canvas.width  = W * dpr;
    canvas.height = H * dpr;
    canvas.style.height = H + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const PAD = { top: 16, right: 16, bottom: 36, left: 48 };
    const pw  = W - PAD.left - PAD.right;
    const ph  = H - PAD.top  - PAD.bottom;

    const dist   = data.score_distribution;
    const n      = dist.length;
    const isEns  = data.summary.method === 'ensemble';

    // Draw axes
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth   = 1;
    ctx.beginPath();
    ctx.moveTo(PAD.left, PAD.top);
    ctx.lineTo(PAD.left, PAD.top + ph);
    ctx.lineTo(PAD.left + pw, PAD.top + ph);
    ctx.stroke();

    // Y-axis labels (score 0–1)
    ctx.fillStyle   = '#94a3b8';
    ctx.font        = '10px system-ui, sans-serif';
    ctx.textAlign   = 'right';
    [0, 0.25, 0.5, 0.75, 1.0].forEach(v => {
        const y = PAD.top + ph - v * ph;
        ctx.fillText(v.toFixed(2), PAD.left - 5, y + 4);
        ctx.strokeStyle = '#f1f5f9';
        ctx.beginPath();
        ctx.moveTo(PAD.left, y);
        ctx.lineTo(PAD.left + pw, y);
        ctx.stroke();
    });

    // X axis label
    ctx.fillStyle = '#64748b';
    ctx.textAlign = 'center';
    ctx.font      = '11px system-ui, sans-serif';
    ctx.fillText('Row index (sampled)', PAD.left + pw / 2, H - 6);

    // Y axis label
    ctx.save();
    ctx.translate(12, PAD.top + ph / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Anomaly score', 0, 0);
    ctx.restore();

    // Threshold line at contamination
    const contamination = data.methods.isolation_forest?.contamination ?? 0.05;
    const thresholdY    = PAD.top + ph - (1 - contamination) * ph;
    ctx.strokeStyle = '#fca5a5';
    ctx.lineWidth   = 1;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(PAD.left, thresholdY);
    ctx.lineTo(PAD.left + pw, thresholdY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle   = '#ef4444';
    ctx.font        = '9px system-ui, sans-serif';
    ctx.textAlign   = 'left';
    ctx.fillText('threshold', PAD.left + 4, thresholdY - 3);

    // Draw points — inliers first, then outliers on top
    const inliers  = dist.filter(d => !d.is_outlier);
    const outliers = dist.filter(d => d.is_outlier);

    function drawPoints(pts, color, outlineColor) {
        pts.forEach((pt, i) => {
            const score = pt.if_score ?? 0;
            const x = PAD.left + (pt.row_index / (data.summary.total_rows || n)) * pw;
            const y = PAD.top + ph - score * ph;
            ctx.beginPath();
            ctx.arc(x, y, pt.in_consensus ? 3.5 : 2.5, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            if (pt.in_consensus && isEns) {
                ctx.strokeStyle = outlineColor || '#be123c';
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }
        });
    }

    ctx.globalAlpha = 0.6;
    drawPoints(inliers, '#60a5fa');
    ctx.globalAlpha = 0.85;
    drawPoints(outliers, '#f43f5e', '#be123c');
    ctx.globalAlpha = 1;

    // Tooltip
    canvas.onmousemove = (e) => {
        const rect  = canvas.getBoundingClientRect();
        const mx    = e.clientX - rect.left;
        const my    = e.clientY - rect.top;
        let closest = null, minDist = 12;

        dist.forEach(pt => {
            const x = PAD.left + (pt.row_index / (data.summary.total_rows || n)) * pw;
            const y = PAD.top + ph - (pt.if_score ?? 0) * ph;
            const d = Math.sqrt((mx-x)**2 + (my-y)**2);
            if (d < minDist) { minDist = d; closest = pt; }
        });

        let tip = document.getElementById('score-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'score-tooltip';
            tip.className = 'absolute text-xs bg-slate-800 text-white px-2 py-1.5 rounded pointer-events-none z-10 whitespace-nowrap hidden';
            canvas.parentElement.style.position = 'relative';
            canvas.parentElement.appendChild(tip);
        }

        if (closest) {
            const lines = [
                `Row ${closest.row_index}`,
                `Score: ${(closest.if_score ?? '—')}`,
                closest.is_outlier ? (closest.in_consensus ? 'Consensus outlier' : 'Outlier') : 'Inlier',
            ];
            if (closest.dbscan_label != null) lines.push(`Cluster: ${closest.dbscan_label === -1 ? 'noise' : closest.dbscan_label}`);
            tip.innerHTML = lines.join('<br>');
            tip.style.left = (e.clientX - rect.left + 12) + 'px';
            tip.style.top  = (e.clientY - rect.top  - 36) + 'px';
            tip.classList.remove('hidden');
        } else {
            tip.classList.add('hidden');
        }
    };
    canvas.onmouseleave = () => document.getElementById('score-tooltip')?.classList.add('hidden');
}

function renderClusterBars(data, container) {
    // DBSCAN only: show cluster membership bars
    const db = data.methods.dbscan;
    if (!db) { container.innerHTML = ''; return; }

    const entries = [
        { label: 'Outliers (noise)', count: db.outlier_count, color: 'bg-rose-400' },
        ...Object.entries(db.cluster_sizes).map(([k, v]) => ({
            label: `Cluster ${k}`, count: v, color: 'bg-violet-400'
        }))
    ];
    const max = Math.max(...entries.map(e => e.count));

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-4">DBSCAN Cluster Distribution</h2>
            <div class="space-y-2">
                ${entries.map(e => `
                    <div class="flex items-center gap-3 text-sm">
                        <span class="w-28 text-slate-600 text-right flex-shrink-0">${e.label}</span>
                        <div class="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
                            <div class="h-full ${e.color} rounded-full transition-all" style="width:${Math.round(e.count/max*100)}%"></div>
                        </div>
                        <span class="w-14 text-slate-700 font-semibold">${e.count.toLocaleString()}</span>
                    </div>`).join('')}
            </div>
        </div>`;
}

// ─── Component 4: Feature Contributions ──────────────────────────────────────

function renderFeatureContributions(data) {
    const container = document.getElementById('outliers-feature-contributions');
    const contribs  = data.feature_contributions;

    if (!contribs || contribs.length === 0) {
        container.innerHTML = ''; return;
    }

    const maxZ  = Math.max(...contribs.map(c => c.mean_shift_z)) || 1;
    const top   = contribs.slice(0, 15);

    const bars = top.map(c => {
        const pct   = Math.round((c.mean_shift_z / maxZ) * 100);
        const level = c.mean_shift_z >= 1.5 ? 'bg-rose-500' : c.mean_shift_z >= 0.5 ? 'bg-amber-400' : 'bg-slate-300';
        return `
            <div class="flex items-center gap-3 text-sm">
                <span class="w-36 text-slate-700 font-medium text-right flex-shrink-0 truncate" title="${c.feature}">${c.feature}</span>
                <div class="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full ${level} rounded-full" style="width:${pct}%"></div>
                </div>
                <span class="w-12 text-slate-600 text-xs font-semibold">z=${c.mean_shift_z.toFixed(2)}</span>
            </div>`;
    }).join('');

    const tableRows = top.map(c => `
        <tr class="border-b border-gray-50 hover:bg-slate-50 cursor-pointer" onclick="toggleContribDetail('cd-${c.feature.replace(/\W/g,'_')}')">
            <td class="py-2 pr-3 font-medium text-slate-700">${c.feature}</td>
            <td class="py-2 pr-3 text-slate-600">${c.outlier_mean.toFixed(3)}</td>
            <td class="py-2 pr-3 text-slate-500">${c.inlier_mean.toFixed(3)} ± ${c.inlier_std.toFixed(3)}</td>
            <td class="py-2 text-rose-600 font-semibold">${c.mean_shift_z.toFixed(2)}</td>
        </tr>
        <tr id="cd-${c.feature.replace(/\W/g,'_')}" class="hidden">
            <td colspan="4" class="pb-3 pt-0">
                <div class="ml-2 p-3 bg-slate-50 rounded-lg text-xs text-slate-600 space-y-1">
                    <p>Outlier range: Q25 ${c.outlier_q25} – Q75 ${c.outlier_q75}</p>
                    <p>Inlier range: Q25 ${c.inlier_q25} – Q75 ${c.inlier_q75}</p>
                </div>
            </td>
        </tr>`).join('');

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-1">Feature Contributions</h2>
            <p class="text-slate-500 text-sm mb-5">
                Features ranked by how much their mean shifts between outliers and inliers (Z-score).
                Higher = more responsible for outlier behaviour.
            </p>

            <!-- Bar chart -->
            <div class="space-y-2 mb-6">
                <div class="flex items-center gap-3 text-xs text-slate-400 mb-1">
                    <span class="w-36 text-right">Feature</span>
                    <span class="flex-1">Mean-shift Z-score</span>
                    <span class="w-12"></span>
                </div>
                ${bars}
            </div>

            <!-- Detail table (expandable rows) -->
            <details class="mt-2">
                <summary class="text-sm font-medium text-slate-600 hover:text-rose-600 cursor-pointer select-none mb-3">
                    Show detailed comparison table
                </summary>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm">
                        <thead>
                            <tr class="text-xs text-slate-400 uppercase tracking-wide border-b border-gray-100">
                                <th class="pb-2 pr-3 text-left font-semibold">Feature</th>
                                <th class="pb-2 pr-3 text-left font-semibold">Outlier mean</th>
                                <th class="pb-2 pr-3 text-left font-semibold">Inlier mean ± std</th>
                                <th class="pb-2 text-left font-semibold">Z-shift ↓</th>
                            </tr>
                        </thead>
                        <tbody>${tableRows}</tbody>
                    </table>
                </div>
            </details>

            <div class="mt-4 flex flex-wrap gap-3 text-xs">
                <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-rose-500 inline-block"></span> Strong driver (z ≥ 1.5)</span>
                <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-amber-400 inline-block"></span> Moderate (z ≥ 0.5)</span>
                <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm bg-slate-300 inline-block"></span> Weak</span>
            </div>
        </div>`;
}

function toggleContribDetail(id) {
    document.getElementById(id)?.classList.toggle('hidden');
}

// ─── Component 5: Outlier Rows Table ─────────────────────────────────────────

function renderOutlierRows(data) {
    const container = document.getElementById('outliers-rows-table');
    const rows      = data.outlier_rows;

    if (!rows || rows.length === 0) {
        container.innerHTML = `
            <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
                <h2 class="text-lg font-bold text-slate-800 mb-2">Flagged Rows</h2>
                <p class="text-slate-500 text-sm">No outlier rows were detected.</p>
            </div>`;
        return;
    }

    const hasIF      = data.methods.isolation_forest != null;
    const hasDB      = data.methods.dbscan != null;
    const isEnsemble = data.summary.method === 'ensemble';
    const featureKeys = Object.keys(rows[0].features || {});

    const tableRows = rows.map((row, i) => {
        const consensusTag = (isEnsemble && row.in_consensus)
            ? '<span class="px-1.5 py-0.5 bg-rose-100 text-rose-700 text-xs rounded-full font-semibold">Consensus</span>'
            : '';
        const scoreTag = (hasIF && row.if_score != null)
            ? `<span class="text-slate-600 text-xs">${row.if_score.toFixed(3)}</span>`
            : '';
        const dbTag = (hasDB && row.dbscan_label != null)
            ? `<span class="text-slate-500 text-xs">${row.dbscan_label === -1 ? 'noise' : `C${row.dbscan_label}`}</span>`
            : '';

        const rowId = `outlier-row-${i}`;
        const expandId = `outlier-expand-${i}`;

        const featureCells = featureKeys.slice(0, 4).map(k => {
            const v = row.features[k];
            return `<td class="py-2 pr-3 text-xs text-slate-600 whitespace-nowrap">${v ?? '—'}</td>`;
        }).join('');

        const allFeatures = featureKeys.map(k => {
            const v = row.features[k];
            return `<tr><td class="pr-4 py-1 text-slate-500 text-xs">${k}</td><td class="py-1 text-xs font-medium text-slate-700">${v ?? '—'}</td></tr>`;
        }).join('');

        return `
            <tr id="${rowId}" class="border-b border-gray-100 hover:bg-rose-50 cursor-pointer transition-colors"
                onclick="toggleOutlierExpand(${i})">
                <td class="py-2.5 pr-3 text-xs text-slate-500">${row.row_index}</td>
                ${scoreTag ? `<td class="py-2.5 pr-3">${scoreTag}</td>` : ''}
                ${dbTag    ? `<td class="py-2.5 pr-3">${dbTag}</td>`    : ''}
                ${featureCells}
                <td class="py-2.5">${consensusTag}</td>
            </tr>
            <tr id="${expandId}" class="hidden bg-rose-50">
                <td colspan="99" class="pb-4 pt-1 px-3">
                    <div class="bg-white border border-rose-100 rounded-xl p-4 text-sm">
                        <p class="font-semibold text-slate-700 mb-2">All feature values — Row ${row.row_index}</p>
                        <table class="text-xs w-full max-w-md"><tbody>${allFeatures}</tbody></table>
                    </div>
                </td>
            </tr>`;
    }).join('');

    const scoreHeader = hasIF ? '<th class="pb-2 pr-3 font-semibold">IF Score</th>' : '';
    const dbHeader    = hasDB ? '<th class="pb-2 pr-3 font-semibold">DBSCAN</th>'   : '';
    const previewCols = featureKeys.slice(0, 4).map(k =>
        `<th class="pb-2 pr-3 font-semibold truncate max-w-24" title="${k}">${k}</th>`
    ).join('');

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-1">Flagged Rows</h2>
            <p class="text-slate-500 text-sm mb-4">
                ${rows.length} row${rows.length !== 1 ? 's' : ''} shown
                ${rows.length === 200 ? '(capped at 200, sorted by anomaly score)' : ''}. Click a row to expand all feature values.
            </p>
            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead>
                        <tr class="border-b border-gray-200 text-xs text-slate-400 uppercase tracking-wide">
                            <th class="pb-2 pr-3 font-semibold">Row #</th>
                            ${scoreHeader}
                            ${dbHeader}
                            ${previewCols}
                            <th class="pb-2 font-semibold"></th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        </div>`;
}

function toggleOutlierExpand(i) {
    document.getElementById(`outlier-expand-${i}`)?.classList.toggle('hidden');
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function setLoading(on) {
    document.getElementById('outliers-loading')?.classList.toggle('hidden', !on);
    const btn = document.getElementById('outliers-analyse-btn');
    if (btn) { btn.disabled = on; btn.textContent = on ? 'Analysing…' : 'Detect outliers'; }
}

function clearResults() {
    document.getElementById('outliers-results')?.classList.add('hidden');
    document.getElementById('outliers-error')?.classList.add('hidden');
    ['outliers-score-banner','outliers-method-cards','outliers-score-chart',
     'outliers-feature-contributions','outliers-rows-table'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '';
    });
}

function showError(msg) {
    const el = document.getElementById('outliers-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}
