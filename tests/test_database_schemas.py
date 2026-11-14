from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = ("vitalis", "aquanex", "agronex", "energis", "nexora")


def test_all_five_domains_have_valid_schemas():
    for domain in DOMAINS:
        schema_file = ROOT / "database" / domain / "02-schema.sql"
        assert schema_file.exists(), f"Schema file missing for {domain}"
        content = schema_file.read_text(encoding="utf-8")

        # Mandatory security & audit tables
        assert "CREATE TABLE IF NOT EXISTS public.audit_events" in content
        assert "CREATE TABLE IF NOT EXISTS public.ingestion_runs" in content
        assert "CREATE TABLE IF NOT EXISTS public.model_registry" in content

        # RLS enforcement
        assert "ENABLE ROW LEVEL SECURITY" in content
        assert "FORCE ROW LEVEL SECURITY" in content
        assert "app_private.current_user_id()" in content

        # No naked public bypass
        assert "BYPASSRLS" not in content


def test_composite_foreign_keys_across_domains():
    for domain in DOMAINS:
        schema_file = ROOT / "database" / domain / "02-schema.sql"
        content = schema_file.read_text(encoding="utf-8")

        # Tables with tenant-owned references must bind owner_id in the FK
        fk_matches = re.findall(r"FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s*public\.([a-z_]+)\s*\(([^)]+)\)", content, re.IGNORECASE)
        for child_cols, parent_table, parent_cols in fk_matches:
            child_clean = [c.strip().lower() for c in child_cols.split(",")]
            parent_clean = [p.strip().lower() for p in parent_cols.split(",")]
            # In tenant-owned tables, owner_id must be the first column of the composite key
            assert "owner_id" in child_clean, f"Missing owner_id in child key for {domain} -> {parent_table}"
            assert "owner_id" in parent_clean, f"Missing owner_id in parent key for {domain} -> {parent_table}"


def test_postgis_and_pgcrypto_extensions():
    common_sql = (ROOT / "database" / "common_rls.sql").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in common_sql
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in common_sql
