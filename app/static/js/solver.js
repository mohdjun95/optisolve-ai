// --- State ---
let selectedFile = null;

// --- File Handling ---
function handleDrop(event) {
    event.preventDefault();
    const zone = document.getElementById('upload-zone');
    zone.classList.remove('drag-over');
    const files = event.dataTransfer.files;
    if (files.length > 0) setFile(files[0]);
}

function handleFileSelect(input) {
    if (input.files.length > 0) setFile(input.files[0]);
}

function setFile(file) {
    selectedFile = file;
    document.getElementById('upload-placeholder').style.display = 'none';
    var preview = document.getElementById('file-preview');
    preview.classList.add('visible');
    document.getElementById('file-name').textContent = file.name;
    var sizeKB = (file.size / 1024).toFixed(1);
    var sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    var sizeStr = file.size > 1024 * 1024 ? sizeMB + ' MB' : sizeKB + ' KB';
    document.getElementById('file-meta').textContent = (file.type || 'unknown') + ' \u2014 ' + sizeStr;
    document.getElementById('solve-btn').disabled = false;
    hideAll();
}

function clearFile() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('upload-placeholder').style.display = '';
    document.getElementById('file-preview').classList.remove('visible');
    document.getElementById('solve-btn').disabled = true;
    hideAll();
}

function hideAll() {
    document.getElementById('progress-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
}

// --- Progress ---
function setStep(stepId, state) {
    var el = document.getElementById(stepId);
    if (!el) return;
    var icon = el.querySelector('.step-icon');
    icon.className = 'step-icon ' + (state === 'active' ? 'step-active' : state === 'done' ? 'step-done' : 'step-pending');
    if (state === 'done') icon.innerHTML = '<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>';
}

function showProgress(text) {
    document.getElementById('progress-section').classList.remove('hidden');
    document.getElementById('error-section').classList.add('hidden');
    document.getElementById('results-section').classList.add('hidden');
    document.getElementById('progress-text').textContent = text;
}

// --- Solve ---
async function solve() {
    if (!selectedFile) return;

    var apiKey = document.getElementById('api-key').value.trim();
    if (!apiKey) {
        showError('Please enter your Gemini API key. You can get one free at ai.google.dev.');
        return;
    }
    var modelName = document.getElementById('model-select').value;

    hideAll();
    showProgress('Preparing upload...');
    setStep('step-upload', 'active');
    setStep('step-extract', 'pending');
    setStep('step-solve', 'pending');
    setStep('step-done', 'pending');

    var btn = document.getElementById('solve-btn');
    btn.disabled = true;
    btn.textContent = 'Processing...';

    document.getElementById('progress-section').scrollIntoView({ behavior: 'smooth', block: 'center' });

    var formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('api_key', apiKey);
    formData.append('model_name', modelName);

    setTimeout(function() {
        setStep('step-upload', 'done');
        setStep('step-extract', 'active');
        showProgress('AI is analyzing your document...');
    }, 1500);

    try {
        var response = await fetch('/api/solve', { method: 'POST', body: formData });
        setStep('step-extract', 'done');
        setStep('step-solve', 'active');
        showProgress('Solving optimization problem...');

        var data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Server error');

        await new Promise(function(r) { setTimeout(r, 500); });
        setStep('step-solve', 'done');
        setStep('step-done', 'active');
        showProgress('Preparing results...');

        await new Promise(function(r) { setTimeout(r, 300); });
        setStep('step-done', 'done');
        document.getElementById('progress-section').classList.add('hidden');

        if (data.success) {
            renderResults(data);
        } else {
            showError(data.error || 'Extraction or solving failed. Check your document and try again.');
        }
    } catch (err) {
        document.getElementById('progress-section').classList.add('hidden');
        showError(err.message || 'An unexpected error occurred.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Extract & Solve';
    }
}

// --- Error ---
function showError(message) {
    var section = document.getElementById('error-section');
    section.classList.remove('hidden');
    document.getElementById('error-message').textContent = message;
    section.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// --- Equation Rendering Helpers ---
function buildEquationHTML(coeffs, varNames) {
    var terms = [];
    var isFirst = true;
    for (var j = 0; j < coeffs.length; j++) {
        if (coeffs[j] === 0) continue;
        var abs = Math.abs(coeffs[j]);
        var sign = coeffs[j] < 0 ? ' \u2212 ' : (isFirst ? '' : ' + ');
        var coStr = (abs === 1) ? '' : formatNum(abs);
        terms.push(sign + coStr + '<span class="eq-var">' + varNames[j] + '</span>');
        isFirst = false;
    }
    return terms.length > 0 ? terms.join('') : '0';
}

function formatNum(n) {
    if (Number.isInteger(n)) return n.toString();
    var s = n.toFixed(4).replace(/\.?0+$/, '');
    return s;
}

// --- Render Formulation Equations ---
function renderFormulation(extraction) {
    var card = document.getElementById('formulation-card');
    var container = document.getElementById('formulation-display');
    var names = extraction.variable_names || [];
    var c = extraction.c || [];

    if (c.length === 0) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');

    var html = '';

    // Objective function
    html += '<div class="eq-section">';
    html += '<div class="eq-label">' + extraction.problem_type + '</div>';
    html += '<div class="eq-expr">Z = ' + buildEquationHTML(c, names) + '</div>';
    html += '</div>';

    // Subject to
    html += '<div class="eq-label" style="margin-top:16px;">Subject to</div>';

    // Inequality constraints
    if (extraction.A_ub && extraction.b_ub) {
        for (var i = 0; i < extraction.A_ub.length; i++) {
            html += '<div class="eq-constraint">' +
                buildEquationHTML(extraction.A_ub[i], names) +
                ' <span class="eq-op">\u2264</span> ' +
                formatNum(extraction.b_ub[i]) +
                '</div>';
        }
    }

    // Equality constraints
    if (extraction.A_eq && extraction.b_eq) {
        for (var i = 0; i < extraction.A_eq.length; i++) {
            html += '<div class="eq-constraint">' +
                buildEquationHTML(extraction.A_eq[i], names) +
                ' <span class="eq-op">=</span> ' +
                formatNum(extraction.b_eq[i]) +
                '</div>';
        }
    }

    // Variable bounds
    html += '<div class="eq-label" style="margin-top:16px;">Bounds</div>';
    if (extraction.bounds) {
        for (var i = 0; i < extraction.bounds.length; i++) {
            var lb = extraction.bounds[i][0];
            var ub = extraction.bounds[i][1];
            var lbStr = (lb !== null && lb !== undefined) ? formatNum(lb) : '\u2212\u221e';
            var ubStr = (ub !== null && ub !== undefined) ? formatNum(ub) : '+\u221e';
            var intLabel = (extraction.is_integer_variable && extraction.is_integer_variable[i])
                ? ' <span class="eq-int-badge">integer</span>' : '';
            html += '<div class="eq-bound">' + lbStr +
                ' \u2264 <span class="eq-var">' + names[i] + '</span> \u2264 ' +
                ubStr + intLabel + '</div>';
        }
    }

    container.innerHTML = html;
}

// --- Render Constraint Grid (Excel-like) ---
function renderConstraintGrid(extraction) {
    var card = document.getElementById('constraint-grid-card');
    var table = document.getElementById('constraint-grid-table');
    var names = extraction.variable_names || [];

    var hasUb = extraction.A_ub && extraction.A_ub.length > 0;
    var hasEq = extraction.A_eq && extraction.A_eq.length > 0;
    if (!hasUb && !hasEq) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');

    var html = '<thead><tr><th></th>';
    for (var j = 0; j < names.length; j++) {
        html += '<th class="center">' + names[j] + '</th>';
    }
    html += '<th class="center">Rel.</th><th class="center">RHS</th></tr></thead><tbody>';

    var rowNum = 0;
    if (hasUb) {
        for (var i = 0; i < extraction.A_ub.length; i++) {
            rowNum++;
            html += '<tr><td class="mono constraint-label">C' + rowNum + '</td>';
            for (var j = 0; j < extraction.A_ub[i].length; j++) {
                var val = extraction.A_ub[i][j];
                var cls = val === 0 ? 'zero-cell' : '';
                html += '<td class="center mono ' + cls + '">' + formatNum(val) + '</td>';
            }
            html += '<td class="center eq-op">\u2264</td>';
            html += '<td class="center mono val">' + formatNum(extraction.b_ub[i]) + '</td></tr>';
        }
    }
    if (hasEq) {
        for (var i = 0; i < extraction.A_eq.length; i++) {
            rowNum++;
            html += '<tr><td class="mono constraint-label">C' + rowNum + '</td>';
            for (var j = 0; j < extraction.A_eq[i].length; j++) {
                var val = extraction.A_eq[i][j];
                var cls = val === 0 ? 'zero-cell' : '';
                html += '<td class="center mono ' + cls + '">' + formatNum(val) + '</td>';
            }
            html += '<td class="center eq-op">=</td>';
            html += '<td class="center mono val">' + formatNum(extraction.b_eq[i]) + '</td></tr>';
        }
    }

    html += '</tbody>';
    table.innerHTML = html;
}

// --- Render Constraints Summary (Sensitivity) ---
function renderConstraintsSummary(data) {
    var card = document.getElementById('constraints-summary-card');
    var thead = document.getElementById('constraints-summary-thead');
    var tbody = document.getElementById('constraints-summary-tbody');
    var noteEl = document.getElementById('sensitivity-note');
    var solution = data.solution;
    var isPureLP = solution.is_pure_lp;
    var details = solution.constraint_details;

    if (!solution.success) { card.classList.add('hidden'); return; }

    // For MILP, show note and hide table
    if (!isPureLP) {
        card.classList.remove('hidden');
        noteEl.classList.remove('hidden');
        thead.innerHTML = '';
        tbody.innerHTML = '';
        return;
    }

    noteEl.classList.add('hidden');

    if (!details || details.length === 0) { card.classList.add('hidden'); return; }
    card.classList.remove('hidden');

    var headerHtml = '<tr><th>Constraint</th><th class="center">Type</th>' +
        '<th style="text-align:right;">LHS Value</th>' +
        '<th style="text-align:right;">RHS</th>' +
        '<th style="text-align:right;">Slack</th>' +
        '<th style="text-align:right;">Shadow Price</th>' +
        '<th class="center">Status</th></tr>';
    thead.innerHTML = headerHtml;

    var bodyHtml = '';
    for (var i = 0; i < details.length; i++) {
        var d = details[i];
        var label = 'C' + (i + 1);
        var typeStr = d.type === 'ub' ? '\u2264' : '=';
        var isBinding = Math.abs(d.slack) < 1e-6;
        var statusBadge = isBinding
            ? '<span class="binding-badge">Binding</span>'
            : '<span class="nonbinding-badge">Non-binding</span>';

        bodyHtml += '<tr>';
        bodyHtml += '<td class="mono">' + label + '</td>';
        bodyHtml += '<td class="center">' + typeStr + '</td>';
        bodyHtml += '<td class="val mono">' + formatNum(d.lhs_value) + '</td>';
        bodyHtml += '<td class="val mono">' + formatNum(d.rhs) + '</td>';
        bodyHtml += '<td class="val mono">' + formatNum(d.slack) + '</td>';
        var dualStr = (d.dual_value !== null && d.dual_value !== undefined) ? formatNum(d.dual_value) : 'N/A';
        bodyHtml += '<td class="val mono">' + dualStr + '</td>';
        bodyHtml += '<td class="center">' + statusBadge + '</td>';
        bodyHtml += '</tr>';
    }
    tbody.innerHTML = bodyHtml;
}

// --- Render Results ---
function renderResults(data) {
    var section = document.getElementById('results-section');
    section.classList.remove('hidden');

    var solution = data.solution;
    var extraction = data.extraction;
    var isSuccess = solution.success;

    // Banner
    var banner = document.getElementById('result-banner');
    banner.className = 'result-banner ' + (isSuccess ? 'success' : 'error');
    document.getElementById('result-icon').innerHTML = isSuccess
        ? '<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
        : '<svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

    var title = document.getElementById('result-title');
    var subtitle = document.getElementById('result-subtitle');
    if (isSuccess) {
        title.textContent = 'Solution Found \u2014 ' + solution.status_str;
        subtitle.textContent = 'The solver found ' + (solution.status_str === 'OPTIMAL' ? 'an optimal' : 'a feasible') + ' solution for this ' + solution.problem_type.toLowerCase() + ' problem.';
    } else {
        title.textContent = 'No Feasible Solution \u2014 ' + solution.status_str;
        subtitle.textContent = 'The solver could not find a feasible solution. The problem may be infeasible, unbounded, or the extracted formulation may contain errors.';
    }

    // Metrics
    var metricsRow = document.getElementById('metrics-row');
    var metrics = [
        { label: 'Variables', value: extraction.num_vars },
        { label: 'Inequality', value: extraction.num_inequality },
        { label: 'Equality', value: extraction.num_equality },
        { label: 'Integer Vars', value: extraction.num_integer }
    ];
    metricsRow.innerHTML = '';
    metrics.forEach(function(m) {
        metricsRow.innerHTML += '<div class="metric"><p class="metric-value">' + m.value + '</p><p class="metric-label">' + m.label + '</p></div>';
    });

    // Objective
    var objCard = document.getElementById('objective-card');
    if (isSuccess && solution.obj_val !== null) {
        objCard.classList.remove('hidden');
        document.getElementById('objective-label').textContent = 'Optimal Value (' + solution.problem_type + ')';
        document.getElementById('objective-value').textContent = Number(solution.obj_val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    } else {
        objCard.classList.add('hidden');
    }

    // Solver Info
    var info = document.getElementById('solver-info');
    info.innerHTML =
        '<div><p class="info-label">Solver</p><p class="info-value">' + (solution.solver_version || 'N/A') + '</p></div>' +
        '<div><p class="info-label">Status</p><p class="info-value">' + solution.status_str + '</p></div>' +
        '<div><p class="info-label">Variables</p><p class="info-value">' + solution.num_vars + ' (' + solution.num_integer_vars + ' int)</p></div>' +
        '<div><p class="info-label">Constraints</p><p class="info-value">' + solution.num_constraints + '</p></div>';

    // Variables Table
    var varsCard = document.getElementById('variables-card');
    var tbody = document.getElementById('variables-tbody');
    if (isSuccess && solution.var_vals && solution.var_vals.length > 0) {
        varsCard.classList.remove('hidden');

        // Rebuild thead to conditionally include Reduced Cost
        var theadHtml = '<tr><th>Variable</th><th style="text-align:right;">Optimal Value</th><th class="center">Type</th><th class="center">Bounds</th>';
        if (solution.is_pure_lp) {
            theadHtml += '<th style="text-align:right;">Reduced Cost</th>';
        }
        theadHtml += '</tr>';
        var theadEl = document.querySelector('#variables-card thead');
        if (theadEl) theadEl.innerHTML = theadHtml;

        tbody.innerHTML = '';
        solution.var_vals.forEach(function(v) {
            var lb = v.lower_bound !== null ? v.lower_bound : '-\u221e';
            var ub = v.upper_bound !== null ? v.upper_bound : '+\u221e';
            var typeClass = v.type === 'Integer' ? 'integer' : 'continuous';
            var row = '<tr>' +
                '<td class="mono">' + v.name + '</td>' +
                '<td class="val mono">' + Number(v.value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 }) + '</td>' +
                '<td class="center"><span class="type-badge ' + typeClass + '">' + v.type + '</span></td>' +
                '<td class="center bounds-text">[' + lb + ', ' + ub + ']</td>';
            if (solution.is_pure_lp) {
                var rc = (v.reduced_cost !== null && v.reduced_cost !== undefined) ? formatNum(v.reduced_cost) : 'N/A';
                row += '<td class="val mono">' + rc + '</td>';
            }
            row += '</tr>';
            tbody.innerHTML += row;
        });
    } else {
        varsCard.classList.add('hidden');
    }

    // Formulation equations
    renderFormulation(extraction);

    // Constraint matrix grid
    renderConstraintGrid(extraction);

    // Sensitivity analysis
    renderConstraintsSummary(data);

    // Raw JSON dump
    document.getElementById('formulation-json').textContent = JSON.stringify(extraction, null, 2);

    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
