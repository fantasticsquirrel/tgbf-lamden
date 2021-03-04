CREATE TABLE bets (
    user_id TEXT NOT NULL,
    bet_amount INTEGER NOT NULL,
    bet_number INTEGER NOT NULL,
    bet_tx_hash TEXT NOT NULL,
    nr_rolled INTEGER NOT NULL,
    won_amount INTEGER,
    won_tx_hash TEXT,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)