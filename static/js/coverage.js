/**
 * coverage.js — Feature-Space Coverage Tool
 * Handles file upload, API call, and all result rendering.
 */

// ─── State ──────────────────────────────────────────────────────────────────

let coverageData = null;
let coverageFile = null;
let showScatter = true;
let labelColorMode = false;
let heatmapCanvas = null;
let heatmapCtx = null;
let currentSort = { col: 'type', dir: 'asc' };

function hasCoverageConsent() {
    return !!document.getElementById('coverage-legal-consent')?.checked;
}

function updateCoverageAnalyzeButton() {
    const btn = document.getElementById('coverage-analyse-btn');
    if (btn) btn.disabled = !(!!coverageFile && hasCoverageConsent());
}

// ─── File Input Handling ─────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('coverage-file-input');
    const dropZone  = document.getElementById('drop-zone-coverage');
    const legal = document.getElementById('coverage-legal-consent');

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
            dropZone.addEventListener(e, () => dropZone.classList.add('border-blue-400','bg-blue-50'))
        );
        ['dragleave','drop'].forEach(e =>
            dropZone.addEventListener(e, () => dropZone.classList.remove('border-blue-400','bg-blue-50'))
        );
        dropZone.addEventListener('drop', ev => {
            const f = ev.dataTransfer.files[0];
            if (!f) return;
            if (!f.name.toLowerCase().endsWith('.csv')) {
                showBanner('Only CSV files are supported.', 'error');
                return;
            }
            const dt = new DataTransfer();
            dt.items.add(f);
            fileInput.files = dt.files;
            onFileSelected(f);
        });
    }

    if (legal) {
        legal.addEventListener('change', updateCoverageAnalyzeButton);
    }
});

function onFileSelected(file) {
    coverageFile = file;
    const nameEl = document.getElementById('coverage-file-name');
    if (nameEl) { nameEl.textContent = file.name; nameEl.classList.remove('hidden'); }
    updateCoverageAnalyzeButton();
}

// ─── Sample Data ─────────────────────────────────────────────────────────────

async function loadCoverageSample() {
    try {
        const resp = await fetch('/sample-data/coverage');
        const blob = await resp.blob();
        const file = new File([blob], 'sample_dataset.csv', { type: 'text/csv' });
        const fileInput = document.getElementById('coverage-file-input');
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        onFileSelected(file);
        showBanner('Sample dataset loaded. Click "Analyse Coverage" to run.', 'info');
    } catch (e) {
        showBanner('Could not load sample data.', 'error');
    }
}

// ─── Main Analysis ───────────────────────────────────────────────────────────

async function startCoverage() {
    if (!coverageFile) return;
    if (!hasCoverageConsent()) {
        showBanner('Please accept Terms, Privacy Policy, and Cookie Policy first.', 'error');
        return;
    }

    const labelCol  = (document.getElementById('label-col-input')?.value || '').trim() || null;
    const gridSizeEl = document.getElementById('grid-size-input');
    const gridSize  = gridSizeEl && gridSizeEl.value ? parseInt(gridSizeEl.value) : null;

    setLoading(true);
    clearResults();

    const formData = new FormData();
    formData.append('file', coverageFile);
    formData.append('accept_legal', 'true');
    formData.append('policy_version', '2026-03-16');

    let url = '/api/tools/coverage/analyze';
    const params = new URLSearchParams();
    if (labelCol) params.set('label_col', labelCol);
    if (gridSize)  params.set('grid_size', String(gridSize));
    if (params.toString()) url += '?' + params.toString();

    try {
        const resp = await fetch(url, { method: 'POST', body: formData });
        const json = await resp.json();
        if (!resp.ok) {
            showError(json.detail || `Error ${resp.status}`);
            return;
        }
        coverageData = json;
        renderAll(json);
    } catch (e) {
        showError('Network error. Please try again.');
    } finally {
        setLoading(false);
    }
}

// ─── Render Orchestrator ─────────────────────────────────────────────────────

function renderAll(data) {
    document.getElementById('coverage-results').classList.remove('hidden');
    renderScoreBanner(data);
    renderCoverageMap(data);
    renderFlaggedTable(data);
    renderPCAPanel(data);
}

// ─── Component 1: Score Banner ───────────────────────────────────────────────

function renderScoreBanner(data) {
    const score = data.coverage_score;
    let color, verdict, msg;

    if (score >= 85) {
        color = 'from-green-50 to-emerald-50 border-green-200';
        verdict = '<span class="text-green-700 font-bold">Good Coverage</span>';
        msg = `Your feature space is well-covered. The dataset has data in most regions of the combined feature space. <strong>${data.flagged_regions.length}</strong> minor gaps were detected, but they are unlikely to cause significant model issues.`;
    } else if (score >= 60) {
        color = 'from-yellow-50 to-amber-50 border-yellow-200';
        verdict = '<span class="text-yellow-700 font-bold">Fair Coverage</span>';
        msg = `Your feature space has some coverage gaps. <strong>${data.flagged_regions.length}</strong> regions were flagged where the dataset has thin or missing data. Review the gaps below to decide if these regions matter for your use case.`;
    } else {
        color = 'from-red-50 to-rose-50 border-red-200';
        verdict = '<span class="text-red-700 font-bold">Poor Coverage</span>';
        msg = `Significant coverage gaps detected. Your dataset has substantial holes in the combined feature space. We strongly recommend reviewing the flagged regions and expanding your data collection before training.`;
    }

    const scoreColor = score >= 85 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600';
    const ringColor  = score >= 85 ? 'border-green-400' : score >= 60 ? 'border-yellow-400' : 'border-red-400';

    let lowVarWarning = '';
    if (data.pca_total_explained < 0.40) {
        lowVarWarning = `<div class="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            ⚠ The 2D projection captures only ${Math.round(data.pca_total_explained * 100)}% of the data's variance. Some gaps may be projection artifacts.
        </div>`;
    }

    document.getElementById('coverage-score-banner').innerHTML = `
        <div class="bg-gradient-to-br ${color} border rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col sm:flex-row items-center gap-6">
                <div class="flex-shrink-0 w-28 h-28 rounded-full border-4 ${ringColor} flex flex-col items-center justify-center bg-white shadow-inner">
                    <span class="text-4xl font-extrabold ${scoreColor}">${score}</span>
                    <span class="text-xs text-slate-500 font-medium">/ 100</span>
                </div>
                <div class="flex-1 text-center sm:text-left">
                    <p class="text-lg mb-1">${verdict}</p>
                    <p class="text-slate-600 text-sm leading-relaxed">${msg}</p>
                    ${lowVarWarning}
                    <div class="mt-3 flex flex-wrap gap-4 text-xs text-slate-500 justify-center sm:justify-start">
                        <span><strong class="text-slate-700">${data.total_samples.toLocaleString()}</strong> samples</span>
                        <span><strong class="text-slate-700">${data.total_features}</strong> features analysed</span>
                        <span><strong class="text-slate-700">${data.grid_size}×${data.grid_size}</strong> grid</span>
                        <span><strong class="text-slate-700">${data.flagged_regions.length}</strong> flagged regions</span>
                    </div>
                </div>
            </div>
        </div>`;
}

// ─── Component 2: 2D Coverage Map ────────────────────────────────────────────

function renderCoverageMap(data) {
    const container = document.getElementById('coverage-map-container');
    const pc1 = Math.round(data.pca_explained_variance[0] * 100);
    const pc2 = Math.round(data.pca_explained_variance[1] * 100);

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <div>
                    <h2 class="text-lg font-bold text-slate-800">2D Feature-Space Coverage Map</h2>
                    <p class="text-xs text-slate-500 mt-0.5">PC1: ${pc1}% variance &nbsp;|&nbsp; PC2: ${pc2}% variance</p>
                </div>
                <div class="flex gap-2 flex-wrap">
                    <button onclick="toggleScatter()" id="toggle-scatter-btn"
                        class="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors">
                        Hide points
                    </button>
                    ${data.sample_labels ? `<button onclick="toggleLabelColor()" id="toggle-label-btn"
                        class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 transition-colors">
                        Color by label
                    </button>` : ''}
                </div>
            </div>
            <div class="relative">
                <canvas id="coverage-heatmap-canvas" style="width:100%;max-height:480px;"></canvas>
            </div>
            <div class="mt-3 flex flex-wrap gap-4 text-xs text-slate-500 items-center">
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-sm bg-white border border-gray-300"></span> Empty</span>
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-sm" style="background:#bfdbfe"></span> Sparse</span>
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-sm" style="background:#1d4ed8"></span> Dense</span>
                <span class="flex items-center gap-1.5"><span class="inline-block w-3 h-3 rounded-sm border-2 border-red-500"></span> Flagged gap</span>
            </div>
            <div id="map-tooltip" class="hidden absolute text-xs bg-slate-800 text-white px-2 py-1 rounded pointer-events-none z-10 whitespace-nowrap"></div>
        </div>`;

    requestAnimationFrame(() => drawHeatmap(data));
}

function drawHeatmap(data) {
    const canvas = document.getElementById('coverage-heatmap-canvas');
    if (!canvas) return;
    heatmapCanvas = canvas;
    heatmapCtx = canvas.getContext('2d');

    const dpr    = window.devicePixelRatio || 1;
    const W      = canvas.offsetWidth || 600;
    const H      = Math.min(480, W * 0.75);
    canvas.width  = W * dpr;
    canvas.height = H * dpr;
    canvas.style.height = H + 'px';

    const ctx = heatmapCtx;
    ctx.scale(dpr, dpr);

    const { counts, x_edges, y_edges } = data.grid_data;
    const gs  = data.grid_size;
    const PAD = { top: 10, right: 10, bottom: 36, left: 36 };
    const pw  = W - PAD.left - PAD.right;
    const ph  = H - PAD.top  - PAD.bottom;

    const cellW = pw / gs;
    const cellH = ph / gs;
    const maxCount = Math.max(...counts.flat());

    // Flagged lookup
    const flaggedSet = new Set(data.flagged_regions.map(r => `${r.cell_row}_${r.cell_col}`));

    // Draw heatmap cells
    for (let row = 0; row < gs; row++) {
        for (let col = 0; col < gs; col++) {
            const count = counts[row][col];
            const x = PAD.left + col * cellW;
            const y = PAD.top  + row * cellH;

            ctx.fillStyle = densityColor(count, maxCount);
            ctx.fillRect(x, y, cellW, cellH);
            ctx.strokeStyle = '#e2e8f0';
            ctx.lineWidth = 0.5;
            ctx.strokeRect(x, y, cellW, cellH);

            // Flagged cell overlay
            if (flaggedSet.has(`${row}_${col}`)) {
                const region = data.flagged_regions.find(r => r.cell_row === row && r.cell_col === col);
                if (region?.cell_type === 'empty') {
                    ctx.fillStyle = 'rgba(239,68,68,0.12)';
                    ctx.fillRect(x, y, cellW, cellH);
                }
                ctx.strokeStyle = '#ef4444';
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 3]);
                ctx.strokeRect(x + 1, y + 1, cellW - 2, cellH - 2);
                ctx.setLineDash([]);
            }
        }
    }

    // Scatter points
    if (showScatter && data.sample_2d_coords) {
        const xMin = x_edges[0], xMax = x_edges[x_edges.length - 1];
        const yMin = y_edges[0], yMax = y_edges[y_edges.length - 1];
        const xRange = xMax - xMin, yRange = yMax - yMin;

        const labelColors = buildLabelColorMap(data.sample_labels);

        ctx.globalAlpha = 0.5;
        data.sample_2d_coords.forEach(([px, py], i) => {
            const cx = PAD.left + ((px - xMin) / xRange) * pw;
            const cy = PAD.top  + ((py - yMin) / yRange) * ph;
            ctx.beginPath();
            ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
            if (labelColorMode && data.sample_labels) {
                ctx.fillStyle = labelColors[data.sample_labels[i]] || '#6366f1';
            } else {
                ctx.fillStyle = '#1e40af';
            }
            ctx.fill();
        });
        ctx.globalAlpha = 1.0;
    }

    // Axis labels
    ctx.fillStyle = '#64748b';
    ctx.font = '11px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`PC1 (${Math.round(data.pca_explained_variance[0] * 100)}% variance)`, PAD.left + pw / 2, H - 6);
    ctx.save();
    ctx.translate(12, PAD.top + ph / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(`PC2 (${Math.round(data.pca_explained_variance[1] * 100)}% variance)`, 0, 0);
    ctx.restore();

    // Hover interaction
    canvas.onmousemove = (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left - PAD.left;
        const my = e.clientY - rect.top  - PAD.top;
        const col = Math.floor(mx / cellW);
        const row = Math.floor(my / cellH);
        const tooltip = document.getElementById('map-tooltip');
        if (col >= 0 && col < gs && row >= 0 && row < gs) {
            const count = counts[row][col];
            const flagged = flaggedSet.has(`${row}_${col}`);
            let tip;
            if (count === 0 && flagged)    tip = 'No samples in this region — coverage gap';
            else if (flagged)              tip = `Only ${count} sample(s) — sparse coverage`;
            else                           tip = `${count} samples in this region`;
            if (tooltip) {
                tooltip.textContent = tip;
                tooltip.style.left  = (e.clientX - rect.left + 10) + 'px';
                tooltip.style.top   = (e.clientY - rect.top  - 28) + 'px';
                tooltip.classList.remove('hidden');
            }
        } else {
            tooltip?.classList.add('hidden');
        }
    };
    canvas.onmouseleave = () => document.getElementById('map-tooltip')?.classList.add('hidden');

    // Click: scroll to flagged table row
    canvas.onclick = (e) => {
        const rect = canvas.getBoundingClientRect();
        const col = Math.floor((e.clientX - rect.left - PAD.left) / cellW);
        const row = Math.floor((e.clientY - rect.top  - PAD.top)  / cellH);
        const key = `${row}_${col}`;
        if (flaggedSet.has(key)) {
            const el = document.getElementById(`flag-row-${key}`);
            if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.classList.add('bg-blue-50'); setTimeout(() => el.classList.remove('bg-blue-50'), 1500); }
        }
    };
}

function densityColor(count, maxCount) {
    if (count === 0)      return '#ffffff';
    const t = count / Math.max(maxCount, 1);
    if (t < 0.1)  return '#dbeafe'; // very sparse — light blue
    if (t < 0.3)  return '#93c5fd';
    if (t < 0.6)  return '#3b82f6';
    return '#1d4ed8';
}

function buildLabelColorMap(labels) {
    if (!labels) return {};
    const palette = ['#ef4444','#3b82f6','#10b981','#f59e0b','#8b5cf6','#ec4899','#06b6d4','#84cc16'];
    const unique  = [...new Set(labels)];
    const map = {};
    unique.forEach((lbl, i) => { map[lbl] = palette[i % palette.length]; });
    return map;
}

function toggleScatter() {
    showScatter = !showScatter;
    const btn = document.getElementById('toggle-scatter-btn');
    if (btn) btn.textContent = showScatter ? 'Hide points' : 'Show points';
    if (coverageData) drawHeatmap(coverageData);
}

function toggleLabelColor() {
    labelColorMode = !labelColorMode;
    const btn = document.getElementById('toggle-label-btn');
    if (btn) btn.textContent = labelColorMode ? 'Default colors' : 'Color by label';
    if (labelColorMode) showBanner('Points are now colored by target class. Look for regions where only one class appears.', 'info');
    if (coverageData) drawHeatmap(coverageData);
}

// ─── Component 3: Flagged Regions Table ──────────────────────────────────────

function renderFlaggedTable(data) {
    const container = document.getElementById('coverage-flagged-table');
    if (!data.flagged_regions || data.flagged_regions.length === 0) {
        container.innerHTML = `
            <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
                <h2 class="text-lg font-bold text-slate-800 mb-2">Flagged Regions</h2>
                <p class="text-slate-500 text-sm">No significant coverage gaps were detected. Your dataset covers the feature space well.</p>
            </div>`;
        return;
    }

    const regions = [...data.flagged_regions];

    container.innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-1">Flagged Regions</h2>
            <p class="text-slate-500 text-sm mb-4">${regions.length} region(s) with sparse or missing coverage. Click a row to expand its feature profile.</p>
            <div class="overflow-x-auto">
                <table class="w-full text-sm text-left">
                    <thead>
                        <tr class="border-b border-gray-200 text-xs text-slate-500 uppercase tracking-wide">
                            <th class="pb-2 pr-4 font-semibold cursor-pointer hover:text-slate-700" onclick="sortTable('type')">Gap Type ↕</th>
                            <th class="pb-2 pr-4 font-semibold">Top Features</th>
                            <th class="pb-2 pr-4 font-semibold cursor-pointer hover:text-slate-700" onclick="sortTable('confidence')">Confidence ↕</th>
                            <th class="pb-2 pr-4 font-semibold">Label Split</th>
                            <th class="pb-2 font-semibold">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="flagged-tbody">
                        ${regions.map(r => flaggedRow(r, data)).join('')}
                    </tbody>
                </table>
            </div>
        </div>`;
}

function flaggedRow(r, data) {
    const key    = `${r.cell_row}_${r.cell_col}`;
    const typeTag = r.cell_type === 'empty'
        ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">Empty</span>'
        : `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700">Sparse (${r.sample_count})</span>`;

    const confTag = r.confidence.level === 'high'
        ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-700">High</span>'
        : r.confidence.level === 'medium'
        ? '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700">Medium</span>'
        : '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">Low</span>';

    const labelSplit = r.label_distribution
        ? Object.entries(r.label_distribution).map(([k,v]) => `${k}: ${v}`).join(', ')
        : '—';

    const topFeats = (r.top_deviating_features || []).slice(0, 3).join(', ') || '—';

    const expandedId = `expand-${key}`;
    return `
        <tr id="flag-row-${key}" class="border-b border-gray-100 hover:bg-slate-50 transition-colors cursor-pointer" onclick="toggleExpand('${key}')">
            <td class="py-3 pr-4">${typeTag}</td>
            <td class="py-3 pr-4 text-slate-700 font-medium">${topFeats}</td>
            <td class="py-3 pr-4">${confTag}</td>
            <td class="py-3 pr-4 text-slate-600">${labelSplit}</td>
            <td class="py-3">
                <button onclick="event.stopPropagation(); showNearestRows('${key}')"
                    class="text-xs text-blue-600 hover:underline font-medium">View rows</button>
            </td>
        </tr>
        <tr id="${expandedId}" class="hidden">
            <td colspan="5" class="pb-4 pt-1">
                ${featureProfileCard(r, data)}
            </td>
        </tr>`;
}

function featureProfileCard(r, data) {
    const confMsg = {
        high:   'This gap is well-supported by the projection. It is likely a genuine coverage hole in your data.',
        medium: 'This gap appears in the projection but may be partially caused by dimensionality reduction. Verify by checking the nearest rows directly.',
        low:    'This flagged region has low projection reliability. It may be an artifact of compressing your data into 2D. Check the nearest rows before acting on this.',
    }[r.confidence.level];

    const topFeats = r.top_deviating_features || [];

    let gapMessage = '';
    if (r.cell_type === 'empty' && topFeats.length >= 2) {
        const f1 = topFeats[0], f2 = topFeats[1];
        const s1 = r.feature_summary[f1], s2 = r.feature_summary[f2];
        gapMessage = `<p class="text-sm text-slate-600 mb-3 bg-slate-50 rounded-lg p-3 border border-slate-200">
            No data found in this region. Based on neighboring samples, this gap corresponds to conditions where
            <strong>${f1}</strong> is around <strong>${s1?.region_median}</strong> (typical: ${s1?.dataset_median})
            and <strong>${f2}</strong> is around <strong>${s2?.region_median}</strong> (typical: ${s2?.dataset_median}).
            If your model will encounter these conditions in production, this is a coverage gap that may need additional data collection.
        </p>`;
    } else if (r.cell_type === 'sparse' && topFeats.length >= 2) {
        const f1 = topFeats[0], f2 = topFeats[1];
        const s1 = r.feature_summary[f1], s2 = r.feature_summary[f2];
        gapMessage = `<p class="text-sm text-slate-600 mb-3 bg-slate-50 rounded-lg p-3 border border-slate-200">
            Only <strong>${r.sample_count}</strong> sample(s) found in this region. The samples here have
            <strong>${f1}</strong> values around ${s1?.region_q25}–${s1?.region_q75}
            and <strong>${f2}</strong> values around ${s2?.region_q25}–${s2?.region_q75}.
            With so few samples, the model has minimal training signal for this part of the feature space.
        </p>`;
    }

    const featureRows = Object.entries(r.feature_summary || {}).map(([feat, s]) => {
        const dev = s.deviation_from_center;
        const devLabel = dev > (s.dataset_median * 0.5 + 0.5) ? 'HIGH' : dev > (s.dataset_median * 0.2 + 0.1) ? 'MEDIUM' : 'LOW';
        const devColor = devLabel === 'HIGH' ? 'text-red-600 font-semibold' : devLabel === 'MEDIUM' ? 'text-yellow-600' : 'text-slate-400';
        const highlight = r.top_deviating_features?.includes(feat) ? 'bg-blue-50' : '';
        return `<tr class="${highlight}">
            <td class="py-1.5 pr-3 font-medium text-slate-700">${feat}</td>
            <td class="py-1.5 pr-3 text-slate-600">${s.region_q25} – ${s.region_q75}</td>
            <td class="py-1.5 pr-3 text-slate-500">${s.dataset_median}</td>
            <td class="py-1.5 ${devColor}">${devLabel}</td>
        </tr>`;
    }).join('');

    return `<div class="mx-2 p-4 bg-white border border-slate-200 rounded-xl text-sm">
        ${gapMessage}
        <table class="w-full text-xs mb-3">
            <thead>
                <tr class="text-slate-400 uppercase tracking-wide text-left border-b border-gray-100">
                    <th class="pb-1.5 pr-3">Feature</th>
                    <th class="pb-1.5 pr-3">Region Range (Q25–Q75)</th>
                    <th class="pb-1.5 pr-3">Dataset Median</th>
                    <th class="pb-1.5">Deviation</th>
                </tr>
            </thead>
            <tbody>${featureRows}</tbody>
        </table>
        <p class="text-xs text-slate-500 italic">${confMsg}</p>
    </div>`;
}

function toggleExpand(key) {
    const el = document.getElementById(`expand-${key}`);
    if (el) el.classList.toggle('hidden');
}

function sortTable(col) {
    if (!coverageData) return;
    if (currentSort.col === col) currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
    else { currentSort.col = col; currentSort.dir = 'asc'; }
    renderFlaggedTable(coverageData);
}

// ─── Nearest Rows Modal ───────────────────────────────────────────────────────

function showNearestRows(key) {
    if (!coverageData) return;
    const rows = coverageData.nearest_rows_data?.[key];
    if (!rows || rows.length === 0) { showBanner('No row data available for this region.', 'info'); return; }

    const cols = Object.keys(rows[0]);
    const headerCells = cols.map(c => `<th class="px-3 py-2 text-left text-xs font-semibold text-slate-500 uppercase whitespace-nowrap">${c}</th>`).join('');
    const bodyRows = rows.map(row =>
        `<tr class="border-b border-gray-100 hover:bg-slate-50">${cols.map(c => `<td class="px-3 py-2 text-xs text-slate-700 whitespace-nowrap">${row[c] ?? '—'}</td>`).join('')}</tr>`
    ).join('');

    let modal = document.getElementById('nearest-rows-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'nearest-rows-modal';
        modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 p-4';
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                <h3 class="font-bold text-slate-800">Nearest data rows to this gap</h3>
                <button onclick="document.getElementById('nearest-rows-modal').remove()"
                    class="text-slate-400 hover:text-slate-600 text-2xl leading-none">&times;</button>
            </div>
            <div class="overflow-auto flex-1 p-4">
                <table class="w-full">
                    <thead class="sticky top-0 bg-white">
                        <tr>${headerCells}</tr>
                    </thead>
                    <tbody>${bodyRows}</tbody>
                </table>
            </div>
        </div>`;

    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

// ─── Component 4: PCA Confidence Panel ───────────────────────────────────────

function renderPCAPanel(data) {
    const total = data.pca_total_explained;
    const pc1   = data.pca_explained_variance[0];
    const pc2   = data.pca_explained_variance[1];

    let msg, msgColor;
    if (total >= 0.60) {
        msg = 'The 2D projection captures a good portion of the data\'s variation. The coverage map is a reliable representation of your feature space.';
        msgColor = 'text-green-700';
    } else if (total >= 0.40) {
        msg = 'The 2D projection captures a moderate portion of the variation. Most major coverage patterns should be visible, but some gaps in higher dimensions may not appear on this map.';
        msgColor = 'text-yellow-700';
    } else {
        msg = 'The 2D projection captures limited variation. Flagged gaps should be treated as preliminary hypotheses, not definitive findings. Consider analysing specific feature pairs directly for more reliable coverage checks.';
        msgColor = 'text-red-700';
    }

    const highs   = data.flagged_regions.filter(r => r.confidence.level === 'high').length;
    const mediums = data.flagged_regions.filter(r => r.confidence.level === 'medium').length;
    const lows    = data.flagged_regions.filter(r => r.confidence.level === 'low').length;

    document.getElementById('coverage-pca-panel').innerHTML = `
        <div class="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-800 mb-3">PCA Projection Confidence</h2>
            <div class="space-y-2 mb-4">
                <div class="flex items-center gap-3 text-sm">
                    <span class="w-8 text-slate-500 text-right text-xs">PC1</span>
                    <div class="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                        <div class="h-full bg-blue-500 rounded-full" style="width:${Math.round(pc1*100)}%"></div>
                    </div>
                    <span class="text-xs font-semibold text-slate-700 w-8">${Math.round(pc1*100)}%</span>
                </div>
                <div class="flex items-center gap-3 text-sm">
                    <span class="w-8 text-slate-500 text-right text-xs">PC2</span>
                    <div class="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                        <div class="h-full bg-blue-400 rounded-full" style="width:${Math.round(pc2*100)}%"></div>
                    </div>
                    <span class="text-xs font-semibold text-slate-700 w-8">${Math.round(pc2*100)}%</span>
                </div>
                <div class="flex items-center gap-3 text-sm font-semibold">
                    <span class="w-8 text-slate-500 text-right text-xs">Total</span>
                    <div class="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
                        <div class="h-full bg-indigo-600 rounded-full" style="width:${Math.round(total*100)}%"></div>
                    </div>
                    <span class="text-xs font-bold text-slate-800 w-8">${Math.round(total*100)}%</span>
                </div>
            </div>
            <p class="text-sm ${msgColor} mb-3">${msg}</p>
            ${data.flagged_regions.length ? `<div class="flex flex-wrap gap-3 text-xs">
                <span class="px-2 py-1 bg-green-100 text-green-700 rounded-lg font-medium">${highs} high-confidence gap${highs !== 1 ? 's' : ''}</span>
                <span class="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-lg font-medium">${mediums} medium</span>
                <span class="px-2 py-1 bg-slate-100 text-slate-600 rounded-lg font-medium">${lows} low</span>
            </div>` : ''}
        </div>`;
}

// ─── UI Helpers ───────────────────────────────────────────────────────────────

function setLoading(on) {
    document.getElementById('coverage-loading')?.classList.toggle('hidden', !on);
    const btn = document.getElementById('coverage-analyse-btn');
    if (btn) { btn.disabled = on; btn.textContent = on ? 'Analysing…' : 'Analyse coverage'; }
}

function clearResults() {
    document.getElementById('coverage-results')?.classList.add('hidden');
    document.getElementById('coverage-error')?.classList.add('hidden');
    ['coverage-score-banner','coverage-map-container','coverage-flagged-table','coverage-pca-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '';
    });
}

function showError(msg) {
    const el = document.getElementById('coverage-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
    showBanner(msg, 'error');
}
