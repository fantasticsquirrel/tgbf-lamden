CREATE TABLE addressbook (
    user_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    address TEXT NOT NULL,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)