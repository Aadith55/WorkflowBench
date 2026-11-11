"""SQLite store for local experiment history."""
import json, os, sqlite3
from pathlib import Path
from typing import Any

def database_path() -> Path:
    return Path(os.getenv("WORKFLOWBENCH_DB", "workflowbench.db"))

def initialise_database(path: str | Path | None = None) -> Path:
    target = Path(path) if path else database_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS experiment_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        case_id TEXT NOT NULL, agent_type TEXT NOT NULL, strategy TEXT NOT NULL, status TEXT NOT NULL,
        metrics_json TEXT NOT NULL, run_json TEXT NOT NULL)""")
    return target

def save_run(metrics: dict[str, Any], run: dict[str, Any], path: str | Path | None = None) -> None:
    target = initialise_database(path)
    with sqlite3.connect(target) as db:
        db.execute("""INSERT INTO experiment_runs
        (case_id,agent_type,strategy,status,metrics_json,run_json) VALUES (?,?,?,?,?,?)""",
        (metrics["case_id"], metrics["agent_type"], metrics["strategy"], metrics["status"],
         json.dumps(metrics), json.dumps(run)))

def recent_runs(limit: int = 30, path: str | Path | None = None) -> list[dict[str, Any]]:
    target = initialise_database(path)
    with sqlite3.connect(target) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT id,created_at,metrics_json,run_json FROM experiment_runs ORDER BY id DESC LIMIT ?",
                          (max(1,min(limit,200)),)).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"], "metrics": json.loads(r["metrics_json"]),
             "run": json.loads(r["run_json"])} for r in rows]
