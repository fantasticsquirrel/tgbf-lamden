CREATE TABLE approved (
	address TEXT NOT NULL,
	contract TEXT NOT NULL,
	token TEXT NOT NULL,
	amount INTEGER NOT NULL,
	tx_hash TEXT NOT NULL,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)