CREATE TABLE rain (
    from_user_id TEXT NOT NULL,
    to_user_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    txid TEXT NOT NULL,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)