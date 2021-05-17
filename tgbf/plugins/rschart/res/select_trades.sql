SELECT time, price
FROM trade_history
WHERE token_symbol = ? COLLATE NOCASE AND time >= ?
ORDER BY time DESC