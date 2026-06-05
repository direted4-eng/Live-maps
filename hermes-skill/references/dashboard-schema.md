# Контракт `dashboard.json` (фронт ↔ ETL)

Раздаётся на `/static/dashboard.json`. Фронт (`Live-maps/app.js`) читает секции; каждая имеет `available` — если `false`, рисуется заглушка «нет данных».

```jsonc
{
  "generated_at": "ISO-8601 (MSK)",

  "study": {                       // ← study.json (NeuroTutor)
    "available": true,
    "overall": { "mastery_pct": 0, "concepts": 10, "reviewed": 3, "due": 4 },
    "domains": [
      { "code": "anatomy", "title": "Нейроанатомия",
        "mastery_pct": 0, "target_pct": 90,
        "concepts": 7, "reviewed": 3, "due": 4 }
    ],
    "generated_at": "ISO-8601"
  },

  "schedule": {                    // ← schedule.json (логика движка)
    "available": true,
    "weekday": "tuesday",
    "date": "2026-06-02",
    "events": [ { "time": "06:25", "label": "...", "text": "..." } ]
  },

  "tasks": {                       // ← eugene_profile.db.kanban_tasks
    "available": true,
    "todo": 5, "in_progress": 0, "done": 0,
    "items": [ { "title": "...", "project": "...", "status": "todo",
                 "energy": "high", "duration_min": 30 } ]
  },

  "energy": {                      // ← eugene_profile.db.daily_logs
    "available": true,
    "today": 7, "clarity": null, "main_project": "...",
    "logged_at": "ISO-8601",
    "trend7": [ { "date": "2026-04-29", "energy": 7 } ]
  },

  "finance": { "available": false },              // financial_records пуст

  "habits": {                                     // SSRT (см. SKILL.md)
    "available": false,
    "note": "ssrt_results живёт в БД контейнера kiske-api"
    // когда подключим: "ssrt_last": 471, "trend": [...]
  },

  "week": {                        // ← eugene_profile.db.weekly_dashboards (ретроспектива)
    "available": false,
    // когда заполнено недельной job Hermes:
    // "week_start","week_end","energy_avg","clarity_avg","total_hours",
    // "top_achievements","top_frustrations","next_week_priority","insights"
  },

  "advice": {                      // ← Hermes (LLM)
    "text": "...", "mood": "support|push|celebrate",
    "generated_at": "ISO-8601 | null"
  }
}
```

## Правила
- ETL всегда пересобирает `study/schedule/tasks/energy/finance/habits`.
- `advice` — **carry-forward**: обычный пересбор сохраняет прошлый совет; перезаписывает только `--advice`.
- Атомарная запись (tmp→replace) — фронт никогда не читает полу-файл.
- Распределение по панелям Mini App: `study→brain`, `schedule+tasks→planner`, `finance→piggy`, `energy(спарклайн)+habits→v60`, `advice+week→scroll` (панель «Рефлексия»).
