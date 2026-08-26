# ===== Live Supabase schema (introspected, read-only) =====

-- 6 tables found

TABLES: budgets, interaction_log, transactions, users, wallet_ledger, wallets


-- ===== Columns per table =====

-- budgets
--   id: integer NOT NULL DEFAULT nextval('budgets_id_seq'::regclass)
--   user_id: text NOT NULL
--   category: text NOT NULL
--   limit_amount: numeric NOT NULL
--   period: text NOT NULL DEFAULT 'monthly'::text
--   created_at: timestamp without time zone NULL DEFAULT now()

-- interaction_log
--   id: integer NOT NULL DEFAULT nextval('interaction_log_id_seq'::regclass)
--   user_id: text NOT NULL
--   raw_message: text NOT NULL
--   intent: text NULL
--   extracted_json: jsonb NULL
--   response: text NULL
--   created_at: timestamp without time zone NULL DEFAULT now()

-- transactions
--   id: integer NOT NULL DEFAULT nextval('transactions_id_seq'::regclass)
--   user_id: text NOT NULL
--   raw_text: text NOT NULL
--   item: text NOT NULL
--   amount: numeric NOT NULL
--   category: text NOT NULL
--   tx_timestamp: timestamp without time zone NULL DEFAULT now()
--   created_at: timestamp without time zone NULL DEFAULT now()

-- users
--   id: text NOT NULL
--   tone_pref: text NULL DEFAULT 'neutral'::text
--   created_at: timestamp without time zone NULL DEFAULT now()

-- wallet_ledger
--   id: integer NOT NULL
--   wallet_id: integer NOT NULL
--   user_id: text NOT NULL
--   transaction_id: integer NULL
--   amount_delta: numeric NOT NULL
--   entry_type: text NOT NULL
--   description: text NULL
--   created_at: timestamp without time zone NULL DEFAULT now()

-- wallets
--   id: integer NOT NULL
--   user_id: text NOT NULL
--   name: text NOT NULL
--   wallet_type: text NOT NULL
--   balance: numeric NOT NULL DEFAULT 0
--   starting_balance: numeric NOT NULL DEFAULT 0
--   note: text NULL
--   is_archived: boolean NOT NULL DEFAULT false
--   created_at: timestamp without time zone NULL DEFAULT now()
--   updated_at: timestamp without time zone NULL DEFAULT now()


-- ===== Row Level Security (enabled?) =====
--   budgets: rowsecurity=True forcerowsecurity=False
--   interaction_log: rowsecurity=True forcerowsecurity=False
--   transactions: rowsecurity=True forcerowsecurity=False
--   users: rowsecurity=True forcerowsecurity=False
--   wallet_ledger: rowsecurity=False forcerowsecurity=False
--   wallets: rowsecurity=False forcerowsecurity=False

-- ===== RLS Policies =====
--   budgets.Users can delete own budget [DELETE] USING (((auth.uid())::text = user_id))
--   budgets.Users can insert own budgets [INSERT] USING (None)
--   budgets.Users can update own budgets [UPDATE] USING (((auth.uid())::text = user_id))
--   budgets.Users can view own budgets [SELECT] USING (((auth.uid())::text = user_id))
--   interaction_log.Users can insert own interaction logs [INSERT] USING (None)
--   interaction_log.Users can view own interaction log [SELECT] USING (((auth.uid())::text = user_id))
--   transactions.Users can delete own transactions [DELETE] USING (((auth.uid())::text = user_id))
--   transactions.Users can insert own transactions [INSERT] USING (None)
--   transactions.Users can update own transactions [UPDATE] USING (((auth.uid())::text = user_id))
--   transactions.Users can view own transactions [SELECT] USING (((auth.uid())::text = user_id))
--   users.Users can insert own record [INSERT] USING (None)
--   users.Users can update own record [UPDATE] USING (((auth.uid())::text = id))
--   users.Users can view own record [SELECT] USING (((auth.uid())::text = id))


-- ===== WALLET TABLES (focus) =====
-- matched: wallet_ledger, wallets

-- Reconstructed DDL for wallet_ledger:
CREATE TABLE public.wallet_ledger (
    id integer NOT NULL,
    wallet_id integer NOT NULL,
    user_id text NOT NULL,
    transaction_id integer,
    amount_delta numeric NOT NULL,
    entry_type text NOT NULL,
    description text,
    created_at timestamp without time zone  DEFAULT now()
);

-- Reconstructed DDL for wallets:
CREATE TABLE public.wallets (
    id integer NOT NULL,
    user_id text NOT NULL,
    name text NOT NULL,
    wallet_type text NOT NULL,
    balance numeric NOT NULL DEFAULT 0,
    starting_balance numeric NOT NULL DEFAULT 0,
    note text,
    is_archived boolean NOT NULL DEFAULT false,
    created_at timestamp without time zone  DEFAULT now(),
    updated_at timestamp without time zone  DEFAULT now()
);


-- ===== user_id identity probe =====
-- transactions.user_id type = text
-- wallets.user_id type = text
-- wallet_ledger.user_id type = text
-- budgets.user_id type = text
-- SAMPLE transactions.user_id = 'aivannpmartinez@gmail.com'  -> EMAIL string
