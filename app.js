'use strict';

/* ── Config ── */
const ITEMS = [
  { id: 'brain',   emoji: '🧠', label: 'Учёба',    title: 'Учёба',          sprite: 'public/sprites/items/brain.png?v=2' },
  { id: 'planner', emoji: '📅', label: 'График',   title: 'Расписание',     sprite: 'public/sprites/items/planner.png?v=2' },
  { id: 'piggy',   emoji: '💰', label: 'Финансы',  title: 'Финансы',        sprite: 'public/sprites/items/piggy.png?v=2' },
  { id: 'v60',     emoji: '☕', label: 'Фокус',    title: 'Привычки/Фокус', sprite: 'public/sprites/items/v60.png?v=2' },
  { id: 'scroll',  emoji: '📜', label: 'Hermes',   title: 'Рефлексия',      sprite: 'public/sprites/items/scroll.png?v=2' },
];

const API_BASE = '/api';

/* ── Time of day ── */
function getTimeOfDay() {
  const h = new Date().getHours();
  if (h >= 6 && h < 17)  return 'day';
  if (h >= 17 && h < 20) return 'sunset';
  return 'night';
}

function applyTimeOfDay() {
  const tod = getTimeOfDay();
  document.body.className = tod;
  document.getElementById('time-badge').textContent = tod.toUpperCase();
}

/* ── Build room items ── */
function buildItems() {
  const desk = document.getElementById('desk');
  ITEMS.forEach(item => {
    const el = document.createElement('div');
    el.className = 'item';
    el.id = `item-${item.id}`;
    el.title = item.title;

    // Try real sprite first
    const img = document.createElement('img');
    img.src = item.sprite;
    img.alt = item.label;
    img.onload = () => el.classList.add('has-sprite');
    img.onerror = () => { img.style.display = 'none'; };  // hide broken img, emoji placeholder stays

    // Placeholder (shown until sprite loads)
    const ph = document.createElement('div');
    ph.className = 'placeholder';
    ph.innerHTML = `<span style="font-size:1.6em">${item.emoji}</span><span>${item.label}</span>`;

    el.appendChild(img);
    el.appendChild(ph);
    el.addEventListener('click', () => openPanel(item.id));
    desk.appendChild(el);
  });
}

/* ── Panel ── */
let currentSection = null;

function openPanel(sectionId) {
  const panel = document.getElementById('panel');
  const item  = ITEMS.find(i => i.id === sectionId);
  if (!item) return;

  document.getElementById('panel-title').textContent = item.title;

  // hide all sections, show requested
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById(`sec-${sectionId}`);
  if (sec) sec.classList.add('active');

  currentSection = sectionId;
  panel.classList.add('open');

  // load section data
  loadSection(sectionId);
}

function closePanel() {
  document.getElementById('panel').classList.remove('open');
  currentSection = null;
}

/* ── Section loaders ── */
function loadSection(id) {
  switch (id) {
    case 'brain':   loadStudy();   break;
    case 'planner': loadSchedule(); break;
    case 'piggy':   loadFinance(); break;
    case 'v60':     loadHabits();  break;
    case 'scroll':  loadHermes();  break;
  }
}

/* All sections are powered by one payload Hermes assembles: /static/dashboard.json */
function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g,
    c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]));
}
function fmtStamp(iso) {
  return iso ? new Date(iso).toLocaleString('ru-RU',
    { day:'numeric', month:'short', hour:'2-digit', minute:'2-digit' }) : '';
}
async function getDashboard() {
  const res = await fetch('/static/dashboard.json', { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
/* Tiny inline-SVG sparkline (no libs) — pixel-art friendly trend line. */
function sparkline(values, max = 10) {
  const vals = (values || []).filter(v => v != null);
  if (!vals.length) return '';
  const w = 240, h = 38, pad = 4, n = vals.length;
  const x = i => pad + (n === 1 ? (w - 2 * pad) / 2 : i * (w - 2 * pad) / (n - 1));
  const y = v => h - pad - (Math.max(0, Math.min(max, v)) / max) * (h - 2 * pad);
  const dots = vals.map((v, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="2.6"/>`).join('');
  const line = n > 1 ? `<polyline points="${vals.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}"/>` : '';
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${line}${dots}</svg>`;
}
async function loadInto(elId, title, render) {
  // The panel header already shows the section title (panel-title), so the
  // section body adds no redundant <h2>.
  const el = document.getElementById(elId);
  el.innerHTML = `<div class="placeholder-content">Загружаю…</div>`;
  try {
    const d = await getDashboard();
    el.innerHTML = render(d);
  } catch (err) {
    el.innerHTML = `<div class="placeholder-content">Не удалось загрузить данные дашборда.<br>
      Проверь, что Hermes собрал dashboard.json.</div>`;
  }
}

function loadStudy() {
  return loadInto('sec-brain', 'Учёба', d => {
    const s = d.study || {};
    if (!s.available) return '<div class="placeholder-content">Пока нет данных по учёбе.</div>';
    const o = s.overall || {};
    const bars = (s.domains || []).map(dom => {
      const pct = Math.max(0, Math.min(100, dom.mastery_pct || 0));
      const sub = `изучено ${dom.reviewed}/${dom.concepts}` + (dom.due ? ` · к повторению: ${dom.due}` : '');
      return `
        <div class="progress-wrap">
          <div class="progress-label"><span>${esc(dom.title)}</span><span>${pct}%</span></div>
          <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div class="progress-sub">${esc(sub)}</div>
        </div>`;
    }).join('');
    const when = fmtStamp(s.generated_at);
    return `
      <div class="study-overall">
        <span class="study-overall-num">${o.mastery_pct ?? 0}%</span>
        <span class="study-overall-label">общий уровень · ${o.reviewed ?? 0}/${o.concepts ?? 0} концептов${o.due ? ` · ${o.due} к повторению` : ''}</span>
      </div>
      ${bars || '<div class="placeholder-content">Пока нет изученных тем — пройди первый разбор в боте.</div>'}
      ${when ? `<div class="study-stamp">обновлено ${when}</div>` : ''}`;
  });
}

function loadSchedule() {
  return loadInto('sec-planner', 'График', d => {
    const sch = d.schedule || {};
    const tasks = d.tasks || {};
    let html = '';
    if (sch.available && (sch.events || []).length) {
      html += sch.events.map(e => `
        <div class="sched-row">
          <span class="sched-time">${esc(e.time)}</span>
          <span class="sched-label">${esc(e.text || e.label)}</span>
        </div>`).join('');
    } else {
      html += '<div class="placeholder-content">На сегодня событий нет.</div>';
    }
    if (tasks.available) {
      const items = (tasks.items || []).map(t => `
        <div class="sched-row">
          <span class="task-dot task-${esc(t.status)}"></span>
          <span class="sched-label">${esc(t.title)}</span>
          <span class="task-meta">${esc(t.energy || '')}${t.duration_min ? ` · ${t.duration_min}м` : ''}</span>
        </div>`).join('');
      html += `<div class="study-overall" style="margin-top:14px">
          <span class="study-overall-label">Задачи · ${tasks.todo} в очереди · ${tasks.in_progress} в работе · ${tasks.done} готово</span>
        </div>${items}`;
    }
    return html;
  });
}

function loadFinance() {
  return loadInto('sec-piggy', 'Финансы', d => {
    const f = d.finance || {};
    if (!f.available) return '<div class="placeholder-content">Пока нет финансовых записей.<br>Появятся, когда начнёшь их вносить.</div>';
    return '<div class="placeholder-content">Финансовые данные подключены.</div>';
  });
}

function loadHabits() {
  return loadInto('sec-v60', 'Привычки / Фокус', d => {
    const en = d.energy || {};
    const h = d.habits || {};
    let html = '';
    if (en.available) {
      const trend = (en.trend7 || []).map(p => p.energy);
      html += `<div class="study-overall">
          <span class="study-overall-num">${en.today ?? '—'}</span>
          <span class="study-overall-label">энергия сегодня${en.clarity != null ? ` · ясность ${en.clarity}` : ''}${en.main_project ? ` · ${esc(en.main_project)}` : ''}</span>
        </div>
        ${trend.length ? `<div class="spark-wrap"><div class="spark-cap">энергия · последние ${trend.length} дн.</div>${sparkline(trend)}</div>` : ''}`;
    }
    html += `<div class="card"><h3>SSRT тест</h3>
        <p style="font-size:0.8rem;margin-bottom:8px">Тормозной контроль (Stop Signal Reaction Time)</p>
        ${h.available && h.ssrt_last != null ? `<p style="font-size:0.8rem;margin-bottom:8px">Последний: <b>${h.ssrt_last} мс</b></p>` : ''}
        <button onclick="window.location.href='/static/ssrt/index.html'" style="
          background:var(--green);color:white;border:2px solid var(--dark);
          padding:8px 16px;font-family:inherit;font-size:0.8rem;cursor:pointer;
          box-shadow:2px 2px 0 var(--dark)">Пройти тест →</button>
      </div>`;
    return html;
  });
}

function loadHermes() {
  return loadInto('sec-scroll', 'Рефлексия', d => {
    const a = d.advice || {};
    const wk = d.week || {};
    let html = '';

    // Rational reflection — Hermes's synthesized advice.
    if (a.text) {
      const when = fmtStamp(a.generated_at);
      html += `<div class="advice-card advice-${esc(a.mood || 'support')}">${esc(a.text)}</div>
        ${when ? `<div class="study-stamp">Hermes · ${when}</div>` : ''}`;
    }

    // Retrospective — latest weekly dashboard (filled by Hermes's weekly job).
    if (wk.available) {
      const rows = [
        ['Энергия (ср.)', wk.energy_avg],
        ['Ясность (ср.)', wk.clarity_avg],
        ['Часы', wk.total_hours],
      ].filter(([, v]) => v != null && v !== '');
      html += `<div class="retro">
        <div class="retro-head">Неделя ${esc(wk.week_start || '')}${wk.week_end ? ` — ${esc(wk.week_end)}` : ''}</div>
        ${rows.map(([k, v]) => `<div class="sched-row"><span class="sched-label">${k}</span><span class="task-meta">${esc(v)}</span></div>`).join('')}
        ${wk.top_achievements ? `<div class="retro-block"><b>Достижения:</b> ${esc(wk.top_achievements)}</div>` : ''}
        ${wk.top_frustrations ? `<div class="retro-block"><b>Срывы:</b> ${esc(wk.top_frustrations)}</div>` : ''}
        ${wk.next_week_priority ? `<div class="retro-block"><b>Фокус недели:</b> ${esc(wk.next_week_priority)}</div>` : ''}
        ${wk.insights ? `<div class="retro-block"><b>Инсайт:</b> ${esc(wk.insights)}</div>` : ''}
      </div>`;
    }

    if (!html) {
      return '<div class="placeholder-content">Пока пусто.<br>Совет появится после утренней/вечерней сборки, ретроспектива — после недельной.</div>';
    }
    return html;
  });
}

/* ── Telegram Mini App init ── */
function initTelegram() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;
  tg.ready();
  tg.expand();
  if (tg.colorScheme === 'dark') document.body.classList.add('tg-dark');
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  initTelegram();
  applyTimeOfDay();
  buildItems();

  document.getElementById('panel-close').addEventListener('click', closePanel);

  // swipe down to close panel
  let touchStartY = 0;
  const panel = document.getElementById('panel');
  panel.addEventListener('touchstart', e => { touchStartY = e.touches[0].clientY; }, { passive: true });
  panel.addEventListener('touchend', e => {
    if (e.changedTouches[0].clientY - touchStartY > 80) closePanel();
  }, { passive: true });

  // update clock every minute
  setInterval(applyTimeOfDay, 60_000);
});
