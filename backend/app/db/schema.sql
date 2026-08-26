-- SQLite compatibility schema for local development and tests.
-- Production deployments should use the Supabase/PostgreSQL adapter.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    tone_pref TEXT DEFAULT 'neutral',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    tx_timestamp TEXT DEFAULT (datetime('now')),
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL,
    limit_amount REAL NOT NULL,
    period TEXT NOT NULL DEFAULT 'monthly',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, category, period)
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    intent TEXT,
    extracted_json TEXT,
    response TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
