CREATE TABLE votes (
	story_id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	vote INTEGER NOT NULL,
	date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)