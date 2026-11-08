import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


EXPECTED_TABLES = {
    "alembic_version",
    "bouquet_items",
    "bouquet_occasions",
    "bouquets",
    "clients",
    "delivery_methods",
    "flowers",
    "loyalty_cards",
    "notifications",
    "occasions",
    "order_items",
    "orders",
    "packaging_options",
    "salons",
    "users",
}


def test_alembic_initial_migration_builds_complete_schema(tmp_path: Path):
    backend_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    env = {**os.environ, "DATABASE_URL": database_url}

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    inspector = inspect(create_engine(database_url))
    assert EXPECTED_TABLES == set(inspector.get_table_names())

    check = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "check"],
        cwd=backend_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "No new upgrade operations detected" in check.stdout + check.stderr
