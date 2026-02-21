'use strict';

// ── State ────────────────────────────────────────────────────
let goals   = { protein_g: 0, fat_g: 0, carbs_g: 0 };
let totals  = { protein_g: 0, fat_g: 0, carbs_g: 0, calories: 0 };
let selectedFood = null;  // currently selected common food object

// ── Helpers ──────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const round1 = v => Math.round(v * 10) / 10;

function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove('hidden');
}
function clearError(el) {
  el.classList.add('hidden');
}

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

// ── Date heading ─────────────────────────────────────────────
function setDateHeading() {
  const today = new Date();
  const opts = { weekday: 'long', month: 'long', day: 'numeric' };
  $('log-date-heading').textContent = "Today's Log — " + today.toLocaleDateString(undefined, opts);
}

// ── Progress bars ─────────────────────────────────────────────
function renderProgress() {
  const hasGoals = goals.protein_g > 0 || goals.fat_g > 0 || goals.carbs_g > 0;
  $('no-goals-msg').classList.toggle('hidden', hasGoals);
  $('progress-bars').classList.toggle('hidden', !hasGoals);
  if (!hasGoals) return;

  renderMacroBar('protein', totals.protein_g, goals.protein_g, 'protein-bar');
  renderMacroBar('fat',     totals.fat_g,     goals.fat_g,     'fat-bar');
  renderMacroBar('carbs',   totals.carbs_g,   goals.carbs_g,   'carbs-bar');

  const calText = totals.calories > 0 ? `${round1(totals.calories)} kcal consumed` : '';
  $('calories-total').textContent = calText;
}

function renderMacroBar(macro, consumed, goal, barId) {
  const bar     = $(barId);
  const stat    = $('stat-'   + macro);
  const remain  = $('remain-' + macro);

  const pct  = goal > 0 ? (consumed / goal) * 100 : 0;
  const over = consumed > goal && goal > 0;

  bar.style.width = Math.min(pct, 100) + '%';
  bar.classList.toggle('over', over);

  stat.textContent = `${round1(consumed)} / ${goal}g`;

  if (goal > 0) {
    if (over) {
      const excess = round1(consumed - goal);
      remain.textContent = `+${excess}g over`;
      remain.className = 'macro-remain over';
    } else {
      const left = round1(goal - consumed);
      remain.textContent = `${left}g left`;
      remain.className = 'macro-remain ok';
    }
  } else {
    remain.textContent = '';
  }
}

// ── Log ──────────────────────────────────────────────────────
async function loadLog() {
  const data = await api('GET', '/api/log');
  totals = data.totals;
  renderLog(data.entries);
  renderProgress();
}

function renderLog(entries) {
  const list    = $('log-list');
  const empty   = $('log-empty');
  const totalsEl = $('log-totals');

  list.innerHTML = '';
  if (entries.length === 0) {
    empty.classList.remove('hidden');
    totalsEl.classList.add('hidden');
    return;
  }
  empty.classList.add('hidden');
  totalsEl.classList.remove('hidden');

  entries.forEach(entry => {
    const li = document.createElement('li');
    const calStr = entry.calories != null ? ` · ${round1(entry.calories)} kcal` : '';
    li.innerHTML = `
      <span class="log-desc">${escHtml(entry.description)}</span>
      <span class="log-macros">
        <span class="lp">P ${round1(entry.protein_g)}g</span>
        &nbsp;<span class="lf">F ${round1(entry.fat_g)}g</span>
        &nbsp;<span class="lc">C ${round1(entry.carbs_g)}g</span>
        ${calStr ? `<span> · ${round1(entry.calories)} kcal</span>` : ''}
      </span>
      <button class="delete-btn" data-id="${entry.id}" title="Remove">&#x2715;</button>
    `;
    list.appendChild(li);
  });

  // Totals row
  $('total-protein').textContent  = `P: ${round1(totals.protein_g)}g`;
  $('total-fat').textContent      = `F: ${round1(totals.fat_g)}g`;
  $('total-carbs').textContent    = `C: ${round1(totals.carbs_g)}g`;
  $('total-calories').textContent = totals.calories > 0
    ? `${round1(totals.calories)} kcal`
    : '— kcal';

  // Delete buttons
  list.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      await api('DELETE', `/api/log/${id}`);
      loadLog();
    });
  });
}

// ── Goals overlay ─────────────────────────────────────────────
async function loadGoals() {
  goals = await api('GET', '/api/goals');
  renderProgress();
}

$('goals-btn').addEventListener('click', () => {
  $('goal-protein').value = goals.protein_g || '';
  $('goal-fat').value     = goals.fat_g     || '';
  $('goal-carbs').value   = goals.carbs_g   || '';
  clearError($('goals-error'));
  $('goals-overlay').classList.remove('hidden');
});

$('goals-cancel-btn').addEventListener('click', () => {
  $('goals-overlay').classList.add('hidden');
});

$('goals-overlay').addEventListener('click', e => {
  if (e.target === $('goals-overlay')) $('goals-overlay').classList.add('hidden');
});

$('goals-save-btn').addEventListener('click', async () => {
  clearError($('goals-error'));
  const p = parseFloat($('goal-protein').value);
  const f = parseFloat($('goal-fat').value);
  const c = parseFloat($('goal-carbs').value);

  if (isNaN(p) || isNaN(f) || isNaN(c) || p < 0 || f < 0 || c < 0) {
    showError($('goals-error'), 'Please enter valid non-negative numbers for all three macros.');
    return;
  }

  const btn = $('goals-save-btn');
  btn.disabled = true;
  const res = await api('POST', '/api/goals', { protein_g: p, fat_g: f, carbs_g: c });
  btn.disabled = false;

  if (res.ok) {
    goals = { protein_g: p, fat_g: f, carbs_g: c };
    renderProgress();
    $('goals-overlay').classList.add('hidden');
  } else {
    showError($('goals-error'), res.error || 'Failed to save goals.');
  }
});

// ── Tabs ──────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.add('hidden'));
    btn.classList.add('active');
    $('tab-' + btn.dataset.tab).classList.remove('hidden');
  });
});

// ── Common foods ──────────────────────────────────────────────
let searchDebounce;

$('food-search').addEventListener('input', () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => loadFoods($('food-search').value), 250);
});

async function loadFoods(q) {
  $('food-list-loading').classList.remove('hidden');
  $('food-list-empty').classList.add('hidden');

  // Deselect if search changes
  if (selectedFood) {
    const qLower = q.toLowerCase();
    if (!selectedFood.name.toLowerCase().includes(qLower)) {
      clearSelectedFood();
    }
  }

  const foods = await api('GET', `/api/foods?q=${encodeURIComponent(q)}`);
  $('food-list-loading').classList.add('hidden');
  renderFoodList(foods);
}

function renderFoodList(foods) {
  const list  = $('food-list');
  const empty = $('food-list-empty');
  list.innerHTML = '';

  if (foods.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  foods.forEach(food => {
    const li = document.createElement('li');
    const isActive = selectedFood && selectedFood.name === food.name;
    if (isActive) li.classList.add('active');

    const calStr = food.calories != null ? ` · ${round1(food.calories)} kcal` : '';
    li.innerHTML = `
      <span class="food-name">${escHtml(food.name)}</span>
      <span class="food-meta">${food.serving_size}${food.serving_unit}${calStr}</span>
    `;
    li.addEventListener('click', () => selectFood(food));
    list.appendChild(li);
  });
}

function selectFood(food) {
  selectedFood = food;

  // Highlight active row
  document.querySelectorAll('#food-list li').forEach(li => {
    li.classList.toggle('active', li.querySelector('.food-name').textContent === food.name);
  });

  $('selected-name').textContent = food.name;
  $('selected-meta').textContent =
    `${food.serving_size} ${food.serving_unit} per serving · ${food.category || 'Uncategorized'}`;
  $('food-qty').value   = food.serving_size;
  $('food-qty-unit').textContent = food.serving_unit;

  $('food-selected-panel').classList.remove('hidden');
  clearError($('common-error'));
  updatePreview();
}

function clearSelectedFood() {
  selectedFood = null;
  $('food-selected-panel').classList.add('hidden');
}

$('food-qty').addEventListener('input', updatePreview);

function updatePreview() {
  if (!selectedFood) return;
  const qty = parseFloat($('food-qty').value);
  if (isNaN(qty) || qty <= 0) {
    $('food-preview').innerHTML = '';
    return;
  }
  const scale  = qty / selectedFood.serving_size;
  const p = round1(selectedFood.protein_g * scale);
  const f = round1(selectedFood.fat_g     * scale);
  const c = round1(selectedFood.carbs_g   * scale);
  const calStr = selectedFood.calories != null
    ? ` · <span class="pv">${round1(selectedFood.calories * scale)}</span> kcal`
    : '';
  $('food-preview').innerHTML =
    `Protein <span class="pv">${p}g</span> · Fat <span class="pv">${f}g</span> · Carbs <span class="pv">${c}g</span>${calStr}`;
}

$('add-common-btn').addEventListener('click', async () => {
  clearError($('common-error'));
  if (!selectedFood) {
    showError($('common-error'), 'Select a food first.');
    return;
  }
  const qty = parseFloat($('food-qty').value);
  if (isNaN(qty) || qty <= 0) {
    showError($('common-error'), 'Enter a valid quantity greater than 0.');
    return;
  }

  const scale  = qty / selectedFood.serving_size;
  const protein = round1(selectedFood.protein_g * scale);
  const fat     = round1(selectedFood.fat_g     * scale);
  const carbs   = round1(selectedFood.carbs_g   * scale);
  const calories = selectedFood.calories != null ? round1(selectedFood.calories * scale) : null;

  // Format quantity display (trim unnecessary .0)
  const qtyDisplay = qty % 1 === 0 ? qty.toFixed(0) : qty.toFixed(1);
  const desc = `${selectedFood.name} (${qtyDisplay} ${selectedFood.serving_unit})`;

  const btn = $('add-common-btn');
  btn.disabled = true;
  const res = await api('POST', '/api/log', { description: desc, protein_g: protein, fat_g: fat, carbs_g: carbs, calories });
  btn.disabled = false;

  if (res.ok) {
    loadLog();
  } else {
    showError($('common-error'), res.error || 'Failed to add entry.');
  }
});

// ── Custom entry ──────────────────────────────────────────────
$('add-custom-btn').addEventListener('click', async () => {
  clearError($('custom-error'));

  const name = $('custom-name').value.trim();
  if (!name) { showError($('custom-error'), 'Food name is required.'); return; }

  const protein = parseFloat($('custom-protein').value);
  const fat     = parseFloat($('custom-fat').value);
  const carbs   = parseFloat($('custom-carbs').value);

  if (isNaN(protein) || isNaN(fat) || isNaN(carbs)) {
    showError($('custom-error'), 'Protein, fat, and carbs are required.');
    return;
  }
  if (protein < 0 || fat < 0 || carbs < 0) {
    showError($('custom-error'), 'Values cannot be negative.');
    return;
  }

  const calRaw  = $('custom-calories').value;
  const calories = calRaw.trim() !== '' ? parseFloat(calRaw) : null;

  const btn = $('add-custom-btn');
  btn.disabled = true;
  const res = await api('POST', '/api/log', {
    description: name,
    protein_g: round1(protein),
    fat_g:     round1(fat),
    carbs_g:   round1(carbs),
    calories,
  });
  btn.disabled = false;

  if (res.ok) {
    // Clear the form
    $('custom-name').value     = '';
    $('custom-protein').value  = '';
    $('custom-fat').value      = '';
    $('custom-carbs').value    = '';
    $('custom-calories').value = '';
    loadLog();
  } else {
    showError($('custom-error'), res.error || 'Failed to add entry.');
  }
});

// ── XSS-safe html escaping ───────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ─────────────────────────────────────────────────────
(async () => {
  setDateHeading();
  await Promise.all([loadGoals(), loadLog()]);
  await loadFoods('');
})();
