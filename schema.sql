
CREATE TABLE users (
	id TEXT NOT NULL, 
	tone_pref TEXT DEFAULT 'neutral'::text, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT users_pkey PRIMARY KEY (id)
)



CREATE TABLE pg_stat_statements_info (
	dealloc BIGINT, 
	stats_reset TIMESTAMP WITH TIME ZONE
)



CREATE TABLE pg_stat_statements (
	userid OID, 
	dbid OID, 
	toplevel BOOLEAN, 
	queryid BIGINT, 
	query TEXT, 
	plans BIGINT, 
	total_plan_time DOUBLE PRECISION, 
	min_plan_time DOUBLE PRECISION, 
	max_plan_time DOUBLE PRECISION, 
	mean_plan_time DOUBLE PRECISION, 
	stddev_plan_time DOUBLE PRECISION, 
	calls BIGINT, 
	total_exec_time DOUBLE PRECISION, 
	min_exec_time DOUBLE PRECISION, 
	max_exec_time DOUBLE PRECISION, 
	mean_exec_time DOUBLE PRECISION, 
	stddev_exec_time DOUBLE PRECISION, 
	rows BIGINT, 
	shared_blks_hit BIGINT, 
	shared_blks_read BIGINT, 
	shared_blks_dirtied BIGINT, 
	shared_blks_written BIGINT, 
	local_blks_hit BIGINT, 
	local_blks_read BIGINT, 
	local_blks_dirtied BIGINT, 
	local_blks_written BIGINT, 
	temp_blks_read BIGINT, 
	temp_blks_written BIGINT, 
	shared_blk_read_time DOUBLE PRECISION, 
	shared_blk_write_time DOUBLE PRECISION, 
	local_blk_read_time DOUBLE PRECISION, 
	local_blk_write_time DOUBLE PRECISION, 
	temp_blk_read_time DOUBLE PRECISION, 
	temp_blk_write_time DOUBLE PRECISION, 
	wal_records BIGINT, 
	wal_fpi BIGINT, 
	wal_bytes NUMERIC, 
	jit_functions BIGINT, 
	jit_generation_time DOUBLE PRECISION, 
	jit_inlining_count BIGINT, 
	jit_inlining_time DOUBLE PRECISION, 
	jit_optimization_count BIGINT, 
	jit_optimization_time DOUBLE PRECISION, 
	jit_emission_count BIGINT, 
	jit_emission_time DOUBLE PRECISION, 
	jit_deform_count BIGINT, 
	jit_deform_time DOUBLE PRECISION, 
	stats_since TIMESTAMP WITH TIME ZONE, 
	minmax_stats_since TIMESTAMP WITH TIME ZONE
)



CREATE TABLE budgets (
	id SERIAL NOT NULL, 
	user_id TEXT NOT NULL, 
	category TEXT NOT NULL, 
	limit_amount NUMERIC(12, 2) NOT NULL, 
	period TEXT DEFAULT 'monthly'::text NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT budgets_pkey PRIMARY KEY (id), 
	CONSTRAINT budgets_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT budgets_user_id_category_period_key UNIQUE NULLS DISTINCT (user_id, category, period)
)


CREATE INDEX idx_budgets_user_id ON budgets (user_id)

CREATE TABLE transactions (
	id SERIAL NOT NULL, 
	user_id TEXT NOT NULL, 
	raw_text TEXT NOT NULL, 
	item TEXT NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	category TEXT NOT NULL, 
	tx_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT transactions_pkey PRIMARY KEY (id), 
	CONSTRAINT transactions_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)


CREATE INDEX idx_transactions_user_id ON transactions (user_id)

CREATE TABLE interaction_log (
	id SERIAL NOT NULL, 
	user_id TEXT NOT NULL, 
	raw_message TEXT NOT NULL, 
	intent TEXT, 
	extracted_json JSONB, 
	response TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	CONSTRAINT interaction_log_pkey PRIMARY KEY (id), 
	CONSTRAINT interaction_log_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)


CREATE INDEX idx_interaction_log_user_id ON interaction_log (user_id)