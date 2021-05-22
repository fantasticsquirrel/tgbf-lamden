SELECT time, price
FROM trades
WHERE token_symbol = ? COLLATE NOCASE AND time >= ?
ORDER BY time DESC