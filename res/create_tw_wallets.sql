CREATE TABLE tw_wallets (
	username TEXT NOT NULL PRIMARY KEY,
	address TEXT NOT NULL,
	privkey TEXT NOT NULL,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)