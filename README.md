# Live-maps — пиксель-арт дашборд жизни (Telegram Mini App)

Telegram Mini App в пиксель-арте: комната, где каждый предмет — секция жизни Евгения
(учёба, расписание, задачи, энергия, финансы, привычки, недельная рефлексия, совет дня).

Ключевая идея архитектуры: **данные владеет бэкенд (Hermes), фронт только рендерит.**
Детерминированный ETL собирает всё в один `dashboard.json`, а LLM (Hermes) поверх пишет
человеческую секцию «Советы» — интерпретирует цифры, а не просто показывает их.

Этот репозиторий — **полный снимок системы** (фронт + ETL-скил + контекст), достаточный,
чтобы поднять её с нуля на другом сервере. См. раздел [«Перенос на другой сервер»](#перенос-на-другой-сервер).

---

## Архитектура

```
ИСТОЧНИКИ                          ETL (hermes-skill/)            MINI APP (этот фронт)
study.json (NeuroTutor) ─┐
schedule.json            ├─ build_dashboard.py ──► dashboard.json ──► fetch /static/dashboard.json
eugene_profile.db        │   (детерминир. сбор)        ▲                 (раздаёт kiske-api :5000
  kanban_tasks/daily_logs│                             │                  + cloudflare-tunnel, HTTPS)
  weekly_dashboards ◄──┐ │   Hermes (LLM) ─────────────┘
                       │ │   пишет секцию advice (--advice)
knowledge.db ──────────┴── build_weekly_retro.py (метрики недели + черновик рефлексии)
 (NeuroTutor: граф)        ▲ Hermes/Eugene дописывают смысл (--achievements/--insight/…)
```

Два слоя:

1. **ETL (детерминированный, stdlib python3):** `hermes-skill/scripts/build_dashboard.py`
   агрегирует все источники в один атомарно записываемый `dashboard.json`. Каждая секция —
   best-effort: нет источника → `{"available": false}`, скрипт не падает.
2. **Аналитика (LLM):** Hermes читает агрегат и дописывает секцию `advice` (совет дня) и
   текстовые поля недельной рефлексии. Запускается тихими cron-job (см. ниже).

Источники остаются **развязанными**: NeuroTutor сам пишет `study.json`, расписание —
`schedule.json`, профиль — в SQLite. ETL только вкладывает их, образы контейнеров не
пересобираются и не связываются.

---

## Структура репозитория

```
Live-maps/
├── index.html               # каркас Mini App (комната-сцена)
├── app.js                   # фронт: fetch /static/dashboard.json → раскладка по панелям
├── style.css                # пиксель-арт стили
├── public/sprites/          # реальные спрайты (rooms/ items/ decor/) — фон по времени суток
├── docs/
│   └── art-prompts.md       # промпты для генерации пиксель-арт ассетов
└── hermes-skill/            # БЭКЕНД: ETL-скил Hermes (живёт в ~/.hermes/skills/live-maps/)
    ├── SKILL.md             # инструкция скила для Hermes
    ├── scripts/
    │   ├── build_dashboard.py      # ETL: источники → dashboard.json
    │   └── build_weekly_retro.py   # метрики недели → weekly_dashboards (idempotent upsert)
    └── references/
        └── dashboard-schema.md     # контракт dashboard.json (фронт ↔ ETL)
```

> `hermes-skill/` — копия того, что на рабочем сервере лежит в `~/.hermes/skills/live-maps/`.
> Здесь она в репозитории, чтобы перенос был самодостаточным.

---

## Раскладка по панелям Mini App

| Секция `dashboard.json` | Источник | Панель фронта |
|---|---|---|
| `study`   | `study.json` (NeuroTutor) | brain (мозг) |
| `schedule`| `schedule.json` | planner |
| `tasks`   | `eugene_profile.db.kanban_tasks` | planner |
| `finance` | `eugene_profile.db.financial_records` | piggy (копилка) |
| `energy`  | `eugene_profile.db.daily_logs` | v60 (спарклайн `trend7`) |
| `habits`  | SSRT (`ssrt_results`) | v60 |
| `week`    | `eugene_profile.db.weekly_dashboards` | scroll — «Рефлексия» |
| `advice`  | **Hermes (LLM)** | scroll — «Рефлексия» |

Полный контракт JSON — `hermes-skill/references/dashboard-schema.md`.

---

## Запуск ETL (на рабочем сервере)

```bash
# Полный пересбор данных (совет сохраняется = carry-forward):
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py

# Записать секцию «Советы Hermes»:
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py \
  --advice "текст совета" --advice-mood support|push|celebrate

# Посмотреть результат без записи:
python3 ~/.hermes/skills/live-maps/scripts/build_dashboard.py --print

# Недельная рефлексия: метрики + черновик (текст-поля заполнятся если пустые):
python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py
# Вписать живую рефлексию (метрики сохранятся, текст не затрётся без --force-text):
python3 ~/.hermes/skills/live-maps/scripts/build_weekly_retro.py \
  --achievements "…" --frustrations "…" --focus "…" --insight "…"
```

Пути источников переопределяются env-переменными:
`LIVEMAPS_STUDY_JSON`, `LIVEMAPS_SCHEDULE_JSON`, `LIVEMAPS_PROFILE_DB`, `LIVEMAPS_DASHBOARD_JSON`.

---

## Cron (тихие job Hermes, `--deliver local` — НЕ шлют в Telegram)

| Job | Расписание (UTC) | МСК | Что делает |
|---|---|---|---|
| Утренняя сборка | `30 3 * * *` | 06:30 | ETL → совет дня |
| Вечерняя сборка | `0 19 * * *` | 22:00 | ETL → совет дня |
| Недельная рефлексия | `0 18 * * 0` | вс 21:00 | метрики недели → LLM пишет рефлексию → ETL |

Каждая: `build_dashboard.py` → читает агрегат → пишет совет в киске-стиле через `--advice`.
(ID job на текущем сервере — в `~/.hermes/`; при переносе создаются заново, см. ниже.)

---

## Деплой фронта (на рабочем сервере)

Раздаётся контейнером **kiske-api** из тома `/root/eugene_life/static/`. Симлинк не работает
(цель вне volume-маунта), поэтому после правок файлы **копируются**:

```bash
cp /root/Live-maps/{app.js,style.css,index.html} /root/eugene_life/static/livemaps/
cp -r /root/Live-maps/public/sprites          /root/eugene_life/static/livemaps/public/
```

URL: `<kiske-tunnel>/static/livemaps/index.html`. Публичный HTTPS даёт контейнер
**cloudflare-tunnel** (`docker compose up -d cloudflare-tunnel`). Compose-команда использует
`--url` = **quick tunnel** → URL **эфемерный** (меняется при пересоздании контейнера).
Для постоянного URL: переключить compose на token-режим `tunnel run` + публичный hostname
в Cloudflare Zero-Trust.

---

## Перенос на другой сервер

Минимальный набор для воспроизведения:

1. **Фронт.** Скопировать содержимое этого репозитория в раздаваемую статикой папку
   нового сервера (на старом это `/root/eugene_life/static/livemaps/`). Нужны:
   `index.html`, `app.js`, `style.css`, `public/sprites/`. Любой статик-сервер, который
   отдаёт их по пути `/static/livemaps/` и `dashboard.json` по `/static/dashboard.json`.

2. **ETL-скил.** Положить `hermes-skill/` в `~/.hermes/skills/live-maps/` нового сервера
   (или туда, где у тебя живут скилы Hermes). Скрипты — чистый stdlib python3, зависимостей нет.

3. **Источники данных.** ETL читает (пути настраиваются env-переменными выше):
   - `study.json` — снапшот NeuroTutor (пишет сам NeuroTutor после каждого ответа);
   - `schedule.json` — расписание (логика движка: date_exc > weekday > default);
   - `eugene_profile.db` (SQLite) — таблицы `kanban_tasks`, `daily_logs`,
     `financial_records`, `weekly_dashboards`;
   - `knowledge.db` (SQLite, NeuroTutor) — для недельных метрик графа.
   Перенести эти файлы/БД и указать на них env-переменными, либо положить по дефолтным путям.

4. **Проверка.** `python3 hermes-skill/scripts/build_dashboard.py --print` — должен собрать
   агрегат (секции без источника честно покажут `available:false`). Затем записать
   `dashboard.json` в статик-папку и открыть Mini App.

5. **Cron.** Создать три job Hermes (см. таблицу выше) с `--deliver local`, скилы
   `live-maps` + `kiske-productivity-system`.

6. **Публичный HTTPS.** Поднять cloudflare-tunnel (или любой reverse-proxy с HTTPS) на
   статик-сервер. Для Telegram Mini App обязателен HTTPS.

---

## Известные ограничения / открытые хвосты

- **SSRT (`habits`)** — данные `ssrt_results` сейчас в эфемерной БД контейнера kiske-api
  (том `./data` не используется), на хосте их нет → секция `available:false`. Чинится
  перенаправлением `ssrt_router` на хостовую/персистентную БД.
- **Live-maps ≠ основной фронт** на `:5000` (там React) — живёт как `/static/livemaps/` превью.
- **Эфемерный URL** туннеля (quick tunnel) — для постоянного нужен token `tunnel run` + hostname.
- Пустые таблицы (`financial_records`) → секции честно показывают «нет данных».

---

## Связанные системы

- **NeuroTutor** — пишет `study.json` и `knowledge.db` (граф знаний, FSRS-повторения).
- **kiske-productivity-system** — киске-стиль советов, профиль `eugene_profile.db`.
- **Hermes** — оркестратор: владеет данными, гоняет ETL и LLM-аналитику по cron.
