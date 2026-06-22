// ── File input → chip list ────────────────────────────────────────────────────
function bindFileInput(inputId, zoneId, multi) {
  const input = document.getElementById(inputId);
  const zone  = document.getElementById(zoneId);
  if (!input || !zone) return;

  const chipList = zone.querySelector('.file-chip-list');
  const dropIcon = zone.querySelector('.drop-icon');
  const dropLabel = zone.querySelector('.drop-label');

  input.addEventListener('change', () => {
    const files = Array.from(input.files);
    if (!chipList) return;

    chipList.innerHTML = '';
    if (files.length) {
      zone.classList.add('has-file');
      files.forEach(f => {
        const chip = document.createElement('span');
        chip.className = 'file-chip';
        chip.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>${truncate(f.name, 28)}</span>
        `;
        chipList.appendChild(chip);
      });
      if (dropIcon)  dropIcon.style.display  = 'none';
      if (dropLabel) dropLabel.style.display = 'none';
    } else {
      zone.classList.remove('has-file');
      if (dropIcon)  dropIcon.style.display  = '';
      if (dropLabel) dropLabel.style.display = '';
    }
  });
}

function truncate(str, n) {
  return str.length > n ? str.slice(0, n - 1) + '…' : str;
}

bindFileInput('brief_file', 'briefDropZone', false);
bindFileInput('assets',     'assetDropZone', true);

// ── Drag-and-drop highlight ───────────────────────────────────────────────────
document.querySelectorAll('.file-drop-zone').forEach(zone => {
  zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('dragover'));
  zone.addEventListener('drop',      ()  => zone.classList.remove('dragover'));
});

// ── Sample brief loader ───────────────────────────────────────────────────────
const SAMPLE = {
  campaign_name: "Summer Launch",
  region: "United States",
  target_audience: "Young adults interested in fitness and convenience",
  campaign_message: "Fuel your day anywhere",
  products: [
    { name: "Spark Energy Drink", description: "A citrus energy drink for busy active consumers" },
    { name: "Pure Protein Bar",   description: "A high protein snack bar for post workout recovery" }
  ],
  brand: {
    name: "Acme Consumer Goods",
    primary_color: "#1E3A5F",
    secondary_color: "#FFFFFF",
    logo_required: false
  }
};

const loadBtn = document.getElementById('loadSample');
if (loadBtn) {
  loadBtn.addEventListener('click', () => {
    const ta = document.getElementById('brief_text');
    if (ta) {
      ta.value = JSON.stringify(SAMPLE, null, 2);
      ta.focus();
      // Brief flash to indicate load
      ta.style.borderColor = 'var(--accent)';
      setTimeout(() => { ta.style.borderColor = ''; }, 600);
    }
  });
}

// ── Loading overlay with sequential pipeline steps ────────────────────────────
const STEPS = [
  { id: 'parse',    label: 'Parsing campaign brief'             },
  { id: 'assets',   label: 'Resolving product assets'           },
  { id: 'generate', label: 'Generating product images'          },
  { id: 'compose',  label: 'Composing creatives (3 ratios each)'},
  { id: 'comply',   label: 'Running compliance checks'          },
  { id: 'report',   label: 'Writing run report'                 },
];

// Estimated ms from form submit when each step becomes active
const STEP_DELAYS = [0, 700, 1500, 3200, 5600, 6400];

const SVG_PENDING = `<svg class="loading-step-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <circle cx="12" cy="12" r="8" stroke-opacity="0.3"/>
</svg>`;

const SVG_ACTIVE = `<svg class="loading-step-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M21 12a9 9 0 11-6.219-8.56"/>
</svg>`;

const SVG_DONE = `<svg class="loading-step-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
  <circle cx="12" cy="12" r="9"/>
  <polyline points="8 12 11 15 16 9" class="step-check" stroke-dasharray="14" stroke-dashoffset="14"
    style="animation: check-draw 0.35s ease 0.05s forwards;"/>
</svg>`;

function buildLoadingSteps(container) {
  const stepsEl = document.createElement('div');
  stepsEl.className = 'loading-steps';

  const divider = document.createElement('div');
  divider.className = 'step-divider';
  stepsEl.appendChild(divider);

  STEPS.forEach(step => {
    const el = document.createElement('div');
    el.className = 'loading-step step-pending';
    el.id = 'step-' + step.id;
    el.innerHTML = `${SVG_PENDING}<span>${step.label}</span>`;
    stepsEl.appendChild(el);
  });

  container.appendChild(stepsEl);
  return stepsEl;
}

function setStepState(id, state) {
  const el = document.getElementById('step-' + id);
  if (!el) return;
  el.className = 'loading-step step-' + state;
  const svg = { pending: SVG_PENDING, active: SVG_ACTIVE, done: SVG_DONE }[state] || SVG_PENDING;
  el.innerHTML = `${svg}<span>${STEPS.find(s => s.id === id).label}</span>`;
}

const form    = document.querySelector('.pipeline-form');
const overlay = document.getElementById('loadingOverlay');

if (form && overlay) {
  const card = overlay.querySelector('.loading-card');
  const stepsEl = buildLoadingSteps(card);

  form.addEventListener('submit', () => {
    overlay.hidden = false;

    // Run through steps with timing
    STEPS.forEach((step, i) => {
      // Mark previous as done, current as active
      setTimeout(() => {
        if (i > 0) setStepState(STEPS[i - 1].id, 'done');
        setStepState(step.id, 'active');
      }, STEP_DELAYS[i]);
    });

    // After last step fires, mark it done too
    const lastDelay = STEP_DELAYS[STEP_DELAYS.length - 1];
    setTimeout(() => {
      setStepState(STEPS[STEPS.length - 1].id, 'done');
    }, lastDelay + 1200);
  });
}
