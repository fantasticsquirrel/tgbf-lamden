SELECT time, price
FROM trade_history
WHERE token_symbol = ? AND time >= ?
ORDER BY time DESC