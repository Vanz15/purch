"""Read-only introspection of the live Supabase Postgres schema.
Mirrors how db_backend.py connects (REFLEX_DB_URL first, then DB_URL),
but uses psycopg directly. NO DDL is run — pure SELECT from
information_schema / pg_catalog. Writes db/live_schema.sql and prints
a focused summary (wallet tables, user_id type, sample row).
"""
import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

url = os.getenv("REFLEX_DB_URL") or os.getenv("DB_URL")
if not url:
    raise SystemExit("Neither REFLEX_DB_URL nor DB_URL set in .env")

# Normalize SQLAlchemy dialect scheme to a plain psycopg URL if needed.
if url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)

out_lines = []
print(f"Connecting to host from REFLEX_DB_URL/DB_URL (masked): {url[:18]}…")


def w(s=""):
    out_lines.append(s)
    print(s)


with psycopg.connect(url, connect_timeout=15, options="-c statement_timeout=10000") as conn:
    w("# ===== Live Supabase schema (introspected, read-only) =====\n")

    # All tables in public schema
    tables = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' AND table_type='BASE TABLE' "
        "ORDER BY table_name"
    ).fetchall()
    w(f"-- {len(tables)} tables found\n")
    w("TABLES: " + ", ".join(t[0] for t in tables) + "\n")

    # Per-table columns
    w("\n-- ===== Columns per table =====")
    for (tname,) in tables:
        cols = conn.execute(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
            (tname,),
        ).fetchall()
        w(f"\n-- {tname}")
        for cname, dtype, nullable, default in cols:
            nn = "NOT NULL" if nullable == "NO" else "NULL"
            df = f" DEFAULT {default}" if default else ""
            w(f"--   {cname}: {dtype} {nn}{df}")

    # RLS status per table
    w("\n\n-- ===== Row Level Security (enabled?) =====")
    rls = conn.execute(
        "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity "
        "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname"
    ).fetchall()
    for tname, rowsec, forcerow in rls:
        w(f"--   {tname}: rowsecurity={rowsec} forcerowsecurity={forcerow}")

    # RLS policies
    w("\n-- ===== RLS Policies =====")
    pols = conn.execute(
        "SELECT schemaname, tablename, policyname, cmd, qual "
        "FROM pg_policies WHERE schemaname='public' ORDER BY tablename, policyname"
    ).fetchall()
    if not pols:
        w("--   (none defined)")
    for sch, tname, pname, cmd, qual in pols:
        w(f"--   {tname}.{pname} [{cmd}] USING ({qual})")

    # Focused: wallet tables
    w("\n\n-- ===== WALLET TABLES (focus) =====")
    wallet_tables = [t[0] for t in tables if "wallet" in t[0].lower()]
    w("-- matched: " + (", ".join(wallet_tables) if wallet_tables else "(NONE — check naming)"))
    # Reconstruct DDL from column info (pg_get_tabledef unavailable on Supabase)
    for wt in wallet_tables:
        w(f"\n-- Reconstructed DDL for {wt}:")
        cols = conn.execute(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
            (wt,),
        ).fetchall()
        w(f"CREATE TABLE public.{wt} (")
        col_lines = []
        for cname, dtype, nullable, default in cols:
            nn = "NOT NULL" if nullable == "NO" else ""
            df = f" DEFAULT {default}" if default else ""
            col_lines.append(f"    {cname} {dtype} {nn}{df}".rstrip())
        w(",\n".join(col_lines))
        w(");")

    # user_id type + sample
    w("\n\n-- ===== user_id identity probe =====")
    # Try the most likely tables
    for probe in ["transactions", "wallets", "users", "wallet_ledger", "budgets"]:
        if probe in [t[0] for t in tables]:
            try:
                colinfo = conn.execute(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s AND column_name='user_id'",
                    (probe,),
                ).fetchone()
                if colinfo:
                    w(f"-- {probe}.user_id type = {colinfo[0]}")
            except Exception as e:
                w(f"-- {probe}.user_id probe failed: {e}")
    # Sample a user_id value from the first table that has one
    for probe in ["transactions", "wallets", "users"]:
        if probe in [t[0] for t in tables]:
            try:
                row = conn.execute(
                    f"SELECT user_id FROM {probe} WHERE user_id IS NOT NULL LIMIT 1"
                ).fetchone()
                if row:
                    val = str(row[0])
                    looks_like_email = "@" in val
                    w(f"-- SAMPLE {probe}.user_id = {val!r}  -> "
                      + ("EMAIL string" if looks_like_email else "UUID/other"))
                    break
            except Exception as e:
                w(f"-- sample from {probe} failed: {e}")

os.makedirs("db", exist_ok=True)
with open("db/live_schema.sql", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines) + "\n")
print("\nWROTE db/live_schema.sql")
