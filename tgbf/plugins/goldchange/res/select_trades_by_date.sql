SELECT
    token_symbol
    ,price
    ,time
    ,datetime(time, 'unixepoch', 'localtime') AS localtime
FROM trades
WHERE time >= strftime('%s', 'now', ?)
ORDER BY token_symbol