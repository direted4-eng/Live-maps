#!/usr/bin/env python3
"""Live-maps weekly retrospective — fill one row of weekly_dashboards.

This is the missing link of the «Рефлексия» panel. The front-end (app.js) and
the dashboard ETL (build_dashboard.py::section_week) were already wired to read
`weekly_dashboards`, but nothing ever wrote a row — so the panel stayed empty.
This script closes that loop.

Two responsibilities, matching Eugene's chosen *hybrid* model:

  1. METRICS (deterministic) — aggregate the week Eugene actually lived from his
     real sources: NeuroTutor study data (sessions, knowledge-graph growth,
     retrieval accuracy), kanban tasks done, energy/clarity logs, mastery
     snapshot. Always refreshed on every run.

  2. REFLECTION (the soul) — the four text fields (achievements / frustrations /
     next-week focus / insight). On first build they get a numbers-based DRAFT
     so the panel is never empty. Hermes's weekly LLM job and Eugene himself
     overwrite them with real words via the --achievements/--frustrations/
     --focus/--insight flags. Re-running metrics never clobbers existing text
     (unless --force-text).

Idempotent: upserts by week_start, so the morning and evening dashboard builds
can refresh metrics all week without creating duplicate rows.

stdlib-only, system python3 (3.12). Mirrors build_dashboard.py conventions
(MSK, read-only source connections, best-effort per source).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

log = logging.getLogger("live-maps.retro")

# ── Sources (all overridable via env, same names as build_dashboard.py) ──────
PROFILE_DB   = Path(os.getenv("LIVEMAPS_PROFILE_DB",   "/root/eugene_life/eugene_profile.db"))
KNOWLEDGE_DB = Path(os.getenv("LIVEMAPS_KNOWLEDGE_DB", "/root/.openclaw/workspace-tutor/data/db/knowledge.db"))
STUDY_JSON   = Path(os.getenv("LIVEMAPS_STUDY_JSON",   "/root/eugene_life/static/study.json"))

MSK = timezone(timedelta(hours=3))


def _connect_ro(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ── Week window ──────────────────────────────────────────────────────────────
def week_window(now: datetime, offset: int = 0) -> tuple[date, date]:
    """ISO Monday→Sunday week containing `now`, shifted by `offset` weeks.

    offset=0 → the current week (default, for the Sunday-evening cron that
    summarises the week just lived). offset=-1 → the previous full week.
    """
    monday = now.date() - timedelta(days=now.weekday()) + timedelta(weeks=offset)
    return monday, monday + timedelta(days=6)


# ── Metrics ──────────────────────────────────────────────────────────────────
def study_metrics(start: date, end: date) -> dict:
    """Aggregate NeuroTutor's week: sessions, graph growth, retrieval accuracy.

    Timestamps in knowledge.db are UTC (datetime('now')); we compare on the
    date prefix, accepting the ≤3h MSK/UTC skew at week boundaries.
    """
    lo, hi = start.isoformat(), (end + timedelta(days=1)).isoformat()
    try:
        with _connect_ro(KNOWLEDGE_DB) as c:
            s = c.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(minutes),0) mins, "
                "COALESCE(SUM(nodes_reviewed),0) reviewed, "
                "COALESCE(SUM(new_knowledge),0) newk, "
                "COALESCE(SUM(edges_built),0) edges, "
                "AVG(NULLIF(accuracy,0)) acc "
                "FROM study_sessions WHERE session_start >= ? AND session_start < ?",
                (lo, hi)).fetchone()
            nodes_created = c.execute(
                "SELECT COUNT(*) FROM knowledge_nodes WHERE created_at >= ? AND created_at < ?",
                (lo, hi)).fetchone()[0]
            edges_created = c.execute(
                "SELECT COUNT(*) FROM edges WHERE created_at >= ? AND created_at < ?",
                (lo, hi)).fetchone()[0]
            total_nodes = c.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
            total_edges = c.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            rl = c.execute(
                "SELECT COUNT(*) n, "
                "COALESCE(SUM(CASE WHEN correct=1 THEN 1 ELSE 0 END),0) ok "
                "FROM retrieval_log WHERE created_at >= ? AND created_at < ?",
                (lo, hi)).fetchone()
    except Exception as e:
        log.warning("knowledge.db unavailable (%s): %s", KNOWLEDGE_DB, e)
        return {"available": False}

    acc = s["acc"]
    rl_acc = (rl["ok"] / rl["n"]) if rl["n"] else None
    return {
        "available": True,
        "sessions": s["n"],
        "minutes": round(s["mins"], 1),
        "nodes_reviewed": s["reviewed"],
        "new_knowledge": s["newk"],
        "edges_built": s["edges"],
        "accuracy": round(acc, 2) if acc is not None else (round(rl_acc, 2) if rl_acc is not None else None),
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "reviews": rl["n"],
    }


def task_metrics(start: date, end: date) -> dict:
    """Kanban tasks done this week + per-project minutes (project_breakdown)."""
    lo, hi = start.isoformat(), end.isoformat()
    try:
        with _connect_ro(PROFILE_DB) as c:
            rows = [dict(r) for r in c.execute(
                "SELECT project, status, duration_min, date FROM kanban_tasks "
                "WHERE date IS NULL OR (date >= ? AND date <= ?)", (lo, hi))]
    except Exception as e:
        log.warning("kanban_tasks unavailable: %s", e)
        return {"available": False, "breakdown": {}}
    done = [r for r in rows if r["status"] == "done"]
    breakdown: dict[str, float] = {}
    for r in done:
        mins = r["duration_min"] or 0
        breakdown[r["project"] or "—"] = breakdown.get(r["project"] or "—", 0) + mins
    return {"available": True, "done": len(done), "total": len(rows), "breakdown": breakdown}


def mood_metrics(start: date, end: date) -> dict:
    """Average energy/clarity from daily_logs in the window (often empty → None)."""
    lo, hi = start.isoformat(), end.isoformat()
    try:
        with _connect_ro(PROFILE_DB) as c:
            r = c.execute(
                "SELECT AVG(energy_level) e, AVG(clarity) cl, "
                "COALESCE(SUM(time_spent_min),0) mins "
                "FROM daily_logs WHERE date >= ? AND date <= ?", (lo, hi)).fetchone()
    except Exception:
        return {"energy_avg": None, "clarity_avg": None, "log_minutes": 0}
    return {
        "energy_avg": round(r["e"], 1) if r["e"] is not None else None,
        "clarity_avg": round(r["cl"], 1) if r["cl"] is not None else None,
        "log_minutes": r["mins"] or 0,
    }


def mastery_snapshot() -> dict:
    """NeuroTutor mastery overall + weakest domain (gap vs target)."""
    try:
        d = json.loads(STUDY_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {"available": False, "domains": []}
    domains = [dom for dom in d.get("domains", []) if dom.get("concepts")]
    weakest = None
    if domains:
        weakest = min(domains, key=lambda x: (x.get("mastery_pct", 0) - x.get("target_pct", 0)))
    return {
        "available": True,
        "overall": d.get("overall", {}),
        "domains": domains,
        "weakest": weakest,
    }


# ── Reflection draft (overwritten by Hermes's LLM job / Eugene) ──────────────
def draft_text(study: dict, tasks: dict, mastery: dict, hours: float) -> dict:
    """Numbers-based first draft so the panel is never empty before the LLM runs."""
    ach_bits = []
    if study.get("available"):
        if study["sessions"]:
            ach_bits.append(f"{study['sessions']} учебн. сессий ({hours} ч)")
        if study["nodes_created"]:
            ach_bits.append(f"+{study['nodes_created']} концептов в графе")
        if study["edges_created"]:
            ach_bits.append(f"+{study['edges_created']} связей")
        if study.get("accuracy") is not None:
            ach_bits.append(f"точность {round(study['accuracy']*100)}%")
    if tasks.get("done"):
        ach_bits.append(f"{tasks['done']} задач закрыто")
    achievements = "; ".join(ach_bits) if ach_bits else "Тихая неделя — данных мало."

    frustrations = ""
    if study.get("available") and study["sessions"] == 0:
        frustrations = "Ни одной учебной сессии за неделю."

    focus = ""
    insight = ""
    w = mastery.get("weakest")
    if w:
        gap = w.get("target_pct", 0) - w.get("mastery_pct", 0)
        focus = f"{w.get('title','?')}: подтянуть с {w.get('mastery_pct',0)}% к цели {w.get('target_pct',0)}%."
        if gap > 0:
            insight = (f"Слабое звено недели — «{w.get('title','?')}» "
                       f"(разрыв {gap} п.п. до цели). Там же {w.get('due',0)} карт на повторение.")
    return {
        "top_achievements": achievements,
        "top_frustrations": frustrations,
        "next_week_priority": focus,
        "insights": insight,
    }


# ── Upsert ───────────────────────────────────────────────────────────────────
TEXT_COLS = ("top_achievements", "top_frustrations", "next_week_priority", "insights")


def upsert_week(week_start: date, week_end: date, metrics: dict,
                overrides: dict, force_text: bool) -> dict:
    """Insert/update the row for week_start. Metrics always refreshed; text
    fields set from overrides, else keep existing, else fall back to draft."""
    conn = sqlite3.connect(PROFILE_DB)
    conn.row_factory = sqlite3.Row
    try:
        existing = conn.execute(
            "SELECT * FROM weekly_dashboards WHERE week_start = ?",
            (week_start.isoformat(),)).fetchone()
        existing = dict(existing) if existing else {}

        text_vals = {}
        for col in TEXT_COLS:
            if overrides.get(col):                      # explicit flag wins
                text_vals[col] = overrides[col]
            elif existing.get(col) and not force_text:  # keep human/LLM text
                text_vals[col] = existing[col]
            else:                                        # first draft
                text_vals[col] = metrics["draft"][col]

        cols = {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_hours": metrics["total_hours"],
            "project_breakdown": json.dumps(metrics["project_breakdown"], ensure_ascii=False),
            "energy_avg": metrics["energy_avg"],
            "clarity_avg": metrics["clarity_avg"],
            "insights": text_vals["insights"],
            "top_achievements": text_vals["top_achievements"],
            "top_frustrations": text_vals["top_frustrations"],
            "next_week_priority": text_vals["next_week_priority"],
        }
        if existing:
            sets = ", ".join(f"{k} = ?" for k in cols)
            conn.execute(f"UPDATE weekly_dashboards SET {sets} WHERE id = ?",
                         (*cols.values(), existing["id"]))
            action = "updated"
        else:
            keys = ", ".join(cols)
            qs = ", ".join("?" for _ in cols)
            conn.execute(f"INSERT INTO weekly_dashboards ({keys}) VALUES ({qs})",
                         tuple(cols.values()))
            action = "inserted"
        conn.commit()
    finally:
        conn.close()
    return {"action": action, **cols}


# ── Build ────────────────────────────────────────────────────────────────────
def build_metrics(start: date, end: date) -> dict:
    study = study_metrics(start, end)
    tasks = task_metrics(start, end)
    mood = mood_metrics(start, end)
    mastery = mastery_snapshot()

    study_min = study.get("minutes", 0) if study.get("available") else 0
    total_hours = round((study_min + mood["log_minutes"]) / 60, 1)

    breakdown = dict(tasks.get("breakdown", {}))
    if study_min:
        breakdown["NeuroTutor (учёба)"] = round(study_min)

    return {
        "total_hours": total_hours or None,
        "project_breakdown": breakdown,
        "energy_avg": mood["energy_avg"],
        "clarity_avg": mood["clarity_avg"],
        "draft": draft_text(study, tasks, mastery, total_hours),
        "_study": study,
        "_tasks": tasks,
        "_mastery": mastery,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Build the weekly retrospective row")
    ap.add_argument("--week-offset", type=int, default=0,
                    help="0=current week (default), -1=previous full week")
    ap.add_argument("--achievements", help="Set «Достижения» (else keep/draft)")
    ap.add_argument("--frustrations", help="Set «Срывы»")
    ap.add_argument("--focus", dest="next_week_priority", help="Set «Фокус недели»")
    ap.add_argument("--insight", dest="insights", help="Set «Инсайт»")
    ap.add_argument("--force-text", action="store_true",
                    help="Overwrite existing text fields with the fresh draft")
    ap.add_argument("--print", action="store_true", dest="print_only",
                    help="Print computed metrics + would-be row without writing")
    args = ap.parse_args()

    now = datetime.now(MSK)
    start, end = week_window(now, args.week_offset)
    metrics = build_metrics(start, end)

    overrides = {
        "top_achievements": args.achievements,
        "top_frustrations": args.frustrations,
        "next_week_priority": args.next_week_priority,
        "insights": args.insights,
    }

    if args.print_only:
        print(json.dumps({
            "week": [start.isoformat(), end.isoformat()],
            "metrics": {k: v for k, v in metrics.items() if not k.startswith("_")},
            "study": metrics["_study"],
            "tasks": metrics["_tasks"],
        }, ensure_ascii=False, indent=2))
        return 0

    res = upsert_week(start, end, metrics, overrides, args.force_text)
    log.info("weekly_dashboards %s: %s — %s", res["action"], res["week_start"], res["week_end"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
