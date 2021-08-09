SELECT
    lt1.token_symbol
    ,lt1.price
    ,lt1.time
    ,datetime(lt1.time, 'unixepoch', 'localtime') AS localtime
FROM trades lt1
      INNER JOIN
      (
          SELECT token_symbol, MAX(time) AS last_time
          FROM trades
          GROUP BY token_symbol
      ) lt2
      ON lt1.token_symbol = lt2.token_symbol
          AND lt1.time = lt2.last_time
WHERE IFNULL(lt1.token_symbol, '') <> ''
ORDER BY lt1.token_symbol