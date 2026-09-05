#!/usr/bin/env python3
"""显式 SQL 迁移执行器。

BaseDao 只会 `Base.metadata.create_all()`（server/dao/base_dao.py:23-36），
对已存在的表不补列，所以新增列必须走这里。

用法：
    uv run python -m server.migrations.migrate                # 迁移 db/app.db
    uv run python -m server.migrations.migrate --db /path/to/app.db
    uv run python -m server.migrations.migrate --db old.db --dry-run

已执行的脚本记录在 schema_migrations 表里，重复执行是空操作；
单条语句层面也做了幂等（IF NOT EXISTS / 忽略 duplicate column）。
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent
DEFAULT_DB = "db/app.db"

# 这些错误意味着"该变更已经在库里了"或"该表还没被 DAO 建出来"，都不算失败。
IGNORABLE = (
    "duplicate column name",
    "no such table: event_triggers",
)


def _split_statements(sql_text: str):
    """按分号切分语句，去掉纯注释块。"""
    statements = []
    for raw in sql_text.split(";"):
        lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


def _ensure_ledger(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )


def _applied(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE name = ?", (name,)).fetchone()
    return row is not None


def apply_file(conn, path: Path, dry_run: bool = False) -> dict:
    result = {"file": path.name, "executed": 0, "skipped": 0, "details": []}
    for stmt in _split_statements(path.read_text(encoding="utf-8")):
        head = " ".join(stmt.split())[:70]
        if dry_run:
            result["details"].append(f"WOULD RUN  {head}")
            continue
        try:
            conn.execute(stmt)
            result["executed"] += 1
            result["details"].append(f"OK         {head}")
        except sqlite3.OperationalError as err:
            message = str(err).lower()
            if any(token in message for token in IGNORABLE):
                result["skipped"] += 1
                result["details"].append(f"SKIP({err}) {head}")
                continue
            raise
    return result


def migrate(db_path: str, dry_run: bool = False) -> int:
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"[migrate] database not found: {db_file}", file=sys.stderr)
        return 1
    print(f"[migrate] database: {db_file.resolve()}")
    conn = sqlite3.connect(str(db_file))
    try:
        _ensure_ledger(conn)
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if _applied(conn, sql_file.name):
                print(f"[migrate] {sql_file.name}: already applied, skipping")
                continue
            print(f"[migrate] {sql_file.name}: applying"
                  f"{' (dry run)' if dry_run else ''}")
            result = apply_file(conn, sql_file, dry_run=dry_run)
            for line in result["details"]:
                print(f"           {line}")
            if not dry_run:
                conn.execute(
                    "INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)",
                    (sql_file.name, datetime.now().isoformat()))
                conn.commit()
            print(f"[migrate] {sql_file.name}: executed={result['executed']} "
                  f"skipped={result['skipped']}")
    finally:
        conn.close()
    print("[migrate] done")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.environ.get("APP_DB_PATH", DEFAULT_DB),
                        help=f"sqlite file path (default: {DEFAULT_DB})")
    parser.add_argument("--dry-run", action="store_true",
                        help="print statements without executing them")
    args = parser.parse_args()
    sys.exit(migrate(args.db, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
