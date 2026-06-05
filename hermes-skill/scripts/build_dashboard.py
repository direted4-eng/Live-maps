#!/usr/bin/env python3
"""Live-maps dashboard ETL — assemble every section into one dashboard.json.

This is the *deterministic* layer of the Live-maps Hermes skill. It pulls from
all of Eugene's data sources into a single payload the pixel-art Mini App
fetches at /static/dashboard.json. The *analytical* layer — the «Советы Hermes»
section — is written separately by the Hermes cron job via --advice (see
SKILL.md); this script carries any existing advice forward so a plain data
refresh never wipes Hermes's last insight.

stdlib-only, runs under system python3 (3.12). Atomic write (tmp→replace) so the
dashboard never reads a half-written file. Best-effort per section: a missing
source degrades to {"available": false}, never crashes the whole build.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("live-maps")

# ── Sources (all overridable via env) ──────────────────────────────────────
STUDY_JSON   = Path(os.getenv("LIVEMAPS_STUDY_JSON",   "/root/eugene_life/static/study.json"))
SCHEDULE_JSON = Path(os.getenv("LIVEMAPS_SCHEDULE_JSON", "/root/eugene_life/schedule.json"))
PROFILE_DB   = Path(os.getenv("LIVEMAPS_PROFILE_DB",   "/root/eugene_life/eugene_profile.db"))
OUTPUT       = Path(os.getenv("LIVEMAPS_DASHBOARD_JSON", "/root/eugene_life/static/dashboard.json"))

MSK = timezone(timedelta(hours=3))
# Fixed English weekday names — schedule.json keys exceptions by these.
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ── Sections ────────────────────────────────────────────────────────────────
def section_study() -> dict:
    """Embed NeuroTutor's snapshot (kept as a separate, decoupled source)."""
    try:
        data = json.loads(STUDY_JSON.read_text(encoding="utf-8"))
        return {
            "available": True,
            "overall": data.get("overall", {}),
            "domains": [d for d in data.get("domains", []) if d.get("concepts")],
            "generated_at": data.get("generated_at"),
        }
    except Exception:
        log.warning("study.json unavailable at %s", STUDY_JSON)
        return {"available": False}


def section_schedule(now: datetime) -> dict:
    """Today's events: per-weekday schedule (or default) + one-off date_exceptions."""
    try:
        sch = json.loads(SCHEDULE_JSON.read_text(encoding="utf-8"))
    except Exception:
        log.warning("schedule.json unavailable at %s", SCHEDULE_JSON)
        return {"available": False}

    weekday = WEEKDAYS[now.weekday()]
    today_str = now.strftime("%Y-%m-%d")
    # Mirror schedule_engine.py exactly — priority REPLACEMENT, not merge:
    #   date_exception > weekday-exception > default.
    date_exc = sch.get("date_exceptions", {})
    if today_str in date_exc:
        src = date_exc[today_str]
    else:
        src = sch.get("exceptions", {}).get(weekday, sch.get("default", []))
    events = sorted(
        [{"time": e.get("time", ""), "label": e.get("label", ""),
          "text": e.get("text", "")} for e in (src or [])],
        key=lambda e: e["time"],
    )
    return {"available": True, "weekday": weekday, "date": today_str,
            "events": events}


def section_tasks() -> dict:
    try:
        with _connect(PROFILE_DB) as conn:
            rows = [dict(r) for r in conn.execute(
                "SELECT title, project, status, energy, duration_min "
                "FROM kanban_tasks ORDER BY "
                "CASE status WHEN 'in_progress' THEN 0 WHEN 'todo' THEN 1 "
                "ELSE 2 END, id")]
    except Exception:
        log.warning("kanban_tasks unavailable")
        return {"available": False}
    counts = {"todo": 0, "in_progress": 0, "done": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"available": True, **counts, "items": rows}


def section_energy() -> dict:
    try:
        with _connect(PROFILE_DB) as conn:
            latest = conn.execute(
                "SELECT date, energy_level, clarity, main_project, logged_at "
                "FROM daily_logs ORDER BY date DESC LIMIT 1").fetchone()
            trend = conn.execute(
                "SELECT date, energy_level FROM daily_logs "
                "WHERE energy_level IS NOT NULL ORDER BY date DESC LIMIT 7"
            ).fetchall()
    except Exception:
        log.warning("daily_logs unavailable")
        return {"available": False}
    if not latest:
        return {"available": False}
    return {
        "available": True,
        "today": latest["energy_level"],
        "clarity": latest["clarity"],
        "main_project": latest["main_project"],
        "logged_at": latest["logged_at"],
        "trend7": [{"date": r["date"], "energy": r["energy_level"]}
                   for r in reversed(trend)],
    }


def section_finance() -> dict:
    try:
        with _connect(PROFILE_DB) as conn:
            n = conn.execute("SELECT COUNT(*) FROM financial_records").fetchone()[0]
    except Exception:
        return {"available": False}
    # Honest: no records yet → the front-end shows a "нет данных" placeholder.
    return {"available": bool(n)}


def section_habits() -> dict:
    # SSRT results currently live in the kiske-api container's own DB (the host
    # eugene_profile.db has no ssrt_results table), so they're not reachable
    # here. Until that storage is pointed at a shared volume, report unavailable.
    return {"available": False, "note": "ssrt_results живёт в БД контейнера kiske-api"}


def section_week() -> dict:
    """Latest weekly retrospective (filled by Hermes's weekly cron job)."""
    try:
        with _connect(PROFILE_DB) as conn:
            row = conn.execute(
                "SELECT week_start, week_end, energy_avg, clarity_avg, "
                "total_hours, top_achievements, top_frustrations, "
                "next_week_priority, insights "
                "FROM weekly_dashboards ORDER BY week_start DESC LIMIT 1"
            ).fetchone()
    except Exception:
        return {"available": False}
    if not row:
        return {"available": False}
    return {"available": True, **{k: row[k] for k in row.keys()}}


def _carry_advice(args) -> dict:
    """Set advice from CLI args, else carry forward the existing one."""
    if args.advice is not None:
        return {
            "text": args.advice,
            "mood": args.advice_mood or "support",
            "generated_at": datetime.now(MSK).isoformat(),
        }
    try:
        prev = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if isinstance(prev.get("advice"), dict):
            return prev["advice"]
    except Exception:
        pass
    return {"text": "", "mood": "support", "generated_at": None}


def build(args) -> dict:
    now = datetime.now(MSK)
    return {
        "generated_at": now.isoformat(),
        "study":    section_study(),
        "schedule": section_schedule(now),
        "tasks":    section_tasks(),
        "energy":   section_energy(),
        "finance":  section_finance(),
        "habits":   section_habits(),
        "week":     section_week(),
        "advice":   _carry_advice(args),
    }


def write_atomic(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Build Live-maps dashboard.json")
    ap.add_argument("--advice", help="Set the «Советы Hermes» text (else carried forward)")
    ap.add_argument("--advice-mood", choices=["support", "push", "celebrate"],
                    help="Tone tag for the advice block")
    ap.add_argument("--print", action="store_true", dest="print_only",
                    help="Print the payload to stdout without writing the file")
    args = ap.parse_args()

    data = build(args)
    if args.print_only:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    write_atomic(data, OUTPUT)
    log.info("dashboard written: %s", OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
