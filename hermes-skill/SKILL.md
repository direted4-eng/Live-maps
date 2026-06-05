---
name: live-maps
description: "Пиксель-арт дашборд жизни Евгения (Telegram Mini App). Hermes собирает данные из всех источников и пишет совет дня. Раздаётся через kiske-api."
category: productivity
metadata:
  hermes:
    tags: [dashboard, live-maps, mini-app, kiske, productivity, telegram]
    related_skills: [kiske-productivity-system, neurotutor]
---

# Live-maps — дашборд жизни Евгения

Telegram Mini App в пиксель-арте: комната, по предметам — секции жизни. **Hermes владеет данными**: детерминированный ETL собирает всё в один `dashboard.json`, а Hermes (LLM) поверх пишет секцию «Советы» — интерпретирует, а не просто рендерит цифры.

## Архитектура

```
ИСТОЧНИКИ                         ETL (этот скил)              MINI APP
study.json (NeuroTutor) ─┐
schedule.json            ├─ build_dashboard.py ─► dashboard.json ─► fetch /static/dashboard.json
eugene_profile.db        │   (детерминир. сбор)      ▲                (раздаёт kiske-api :5000
  kanban_tasks/daily_logs│                           │                 + kiske-tunnel, HTTPS)
  weekly_dashboards ◄──┐ │   Hermes (LLM) ───────────┘
                       │ │   пишет секцию advice (--advice)
knowledge.db ──────────┴── build_weekly_retro.py (метрики недели + черновик рефлексии)
 (NeuroTutor: граф)        ▲ Hermes/Eugene дописывают смысл (--achievements/--insight/…)
```

- **Источники** остаются отдельными и развязанными. NeuroTutor сам пишет `study.json` (после каждого ответа); ETL лишь вкладывает его. Контейнеры не связаны, образ не пересобирается.
- **Публикация:** `dashboard.json` пишется в `/root/eugene_life/static/` (volume kiske-api) → отдаётся на `/static/dashboard.json`.
- **Фронт:** `/root/Live-maps` (исходник), задеплоен в `/root/eugene_life/static/livemaps/`. URL: `<kiske-tunnel>/static/livemaps/index.html`.

## Скрипт ETL

```bash
# Полный пересбор данных (совет сохраняется = carry-forward):
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py

# Записать секцию «Советы Hermes»:
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py \
  --advice "текст совета" --advice-mood support|push|celebrate

# Посмотреть без записи:
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py --print
```

## Скрипт недельной рефлексии

`build_weekly_retro.py` наполняет `weekly_dashboards` (раньше таблица была пустой → панель «Рефлексия» молчала). Метрики недели считаются детерминированно из реальных источников Eugene (NeuroTutor `knowledge.db`: сессии, рост графа, точность; `eugene_profile.db`: kanban, energy/clarity). Текстовые поля (Достижения / Срывы / Фокус / Инсайт) на первом прогоне получают **черновик из цифр**, который Hermes (LLM) и сам Eugene переписывают своими словами — **гибрид**. Идемпотентно: upsert по `week_start`, повторный пересчёт метрик НЕ затирает уже вписанный текст (если без `--force-text`).

```bash
# Метрики текущей недели + черновик (текст-поля заполнятся, если пустые):
python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py

# Вписать живую рефлексию (Hermes LLM-джоб или Eugene); метрики сохраняются:
python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py \
  --achievements "…" --frustrations "…" --focus "…" --insight "…"

# Прошлая полная неделя; посмотреть без записи:
python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py --week-offset -1 --print
```

После записи строки нужен `build_dashboard.py` — он перекладывает свежий `weekly_dashboards` в секцию `week` дашборда.

stdlib-only, system `python3`. Атомарная запись. Каждая секция best-effort: нет источника → `{"available": false}`, не падает.

Пути переопределяются env: `LIVEMAPS_STUDY_JSON`, `LIVEMAPS_SCHEDULE_JSON`, `LIVEMAPS_PROFILE_DB`, `LIVEMAPS_DASHBOARD_JSON`.

## Секции `dashboard.json`

| Ключ | Источник | Заметки |
|---|---|---|
| `study` | `study.json` (NeuroTutor) | overall + domains[] (mastery%) |
| `schedule` | `schedule.json` | события на сегодня (логика движка: date_exc > weekday > default) |
| `tasks` | `eugene_profile.db.kanban_tasks` | счётчики + items |
| `energy` | `eugene_profile.db.daily_logs` | energy/clarity + trend7 |
| `finance` | `eugene_profile.db.financial_records` | пока пусто → `available:false` |
| `habits` | SSRT | заперт в БД контейнера kiske-api → `available:false` (см. ниже) |
| `week` | `eugene_profile.db.weekly_dashboards` | ретроспектива недели — метрики из `build_weekly_retro.py`, текст от Hermes/Eugene |
| `advice` | **Hermes (LLM)** | text + mood + generated_at |

Фронт: `energy.trend7` рисуется спарклайном (панель Привычки/Фокус); `week`+`advice` вместе образуют панель «Рефлексия» (scroll) — рациональный вывод + ретроспектива.

Полный контракт: `references/dashboard-schema.md`.

## Cron (Hermes jobs, тихие)

Две job, `--deliver local` (НЕ шлют в Telegram, только обновляют дашборд):
- `Live-maps — утренняя сборка` — `30 3 * * *` (06:30 МСК)
- `Live-maps — вечерняя сборка` — `0 19 * * *` (22:00 МСК)

Каждая: ETL → читает агрегат → пишет совет дня в киске-стиле (волна мотивации, идентичность во Христе, без нравоучений).

**Недельная рефлексия** (рекомендуемый джоб, воскресенье вечером, `--deliver local`, тихо):
1. `python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py` — метрики недели + черновик.
2. Прочитать строку: `python3 …/build_weekly_retro.py --print`.
3. Синтез: по цифрам недели (учёба, рост графа, точность, задачи) написать живую рефлексию в голосе Профессора/киске — честно про достижения и срывы, один фокус на след. неделю, один инсайт.
4. Вписать: `python3 …/build_weekly_retro.py --achievements "…" --frustrations "…" --focus "…" --insight "…"`.
5. `python3 …/build_dashboard.py` — переложить в секцию `week`.

## Как Hermes пишет совет

1. `build_dashboard.py` (обновить данные).
2. `cat /root/eugene_life/static/dashboard.json` — прочитать агрегат.
3. Синтез: ОДИН короткий совет (2-4 предложения) по энергии/задачам/due/времени суток. mood: support|push|celebrate.
4. `build_dashboard.py --advice "…" --advice-mood …`.

## Известные ограничения

- **SSRT-данные** (`ssrt_results`) сейчас в эфемерной БД контейнера kiske-api (том `./data` для неё не используется) — на хосте их нет, секция `habits` = `available:false`. Чинится отдельно: перенаправить `ssrt_router` на `./data` или на хостовую базу.
- **Спрайты** `Live-maps/public/sprites/*` пустые → эмодзи-плейсхолдеры. Ок для MVP.
- **Live-maps ≠ основной фронт** на :5000 (там React); живёт как `/static/livemaps/`. Замена основного — отдельное решение.
- Пустые таблицы (`financial_records`, `daily_energy_log`) → секции честно показывают «нет данных».

## Деплой фронта при правках

Исходник — `/root/Live-maps`. После правок скопировать в раздаваемую папку:
```bash
cp /root/Live-maps/{app.js,style.css,index.html} /root/eugene_life/static/livemaps/
```
(Симлинк не работает — цель вне volume-маунта контейнера.) Проверять: `curl .../static/livemaps/app.js`, рендер в браузере (playwright chromium-1223).
