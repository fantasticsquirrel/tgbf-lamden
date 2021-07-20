SELECT token_symbol, avg_price, last_price, chg_perc
FROM (
         SELECT t1.token_symbol
              , COALESCE(AVG(t_agg.price), t_last.price)AS avg_price
              , COALESCE(COUNT(t_agg._ROWID_), 1) AS txcnt
              , COALESCE(MIN(t_agg.time), t_last.time) AS first_time
              , t_last.price AS last_price
              , t_last.time AS last_time
              , CASE WHEN t_last.price <> 0
                    THEN ROUND(ROUND(1 - (COALESCE(AVG(t_agg.price), t_last.price) / t_last.price), 2) * 100) ELSE  0 END  AS chg_perc
         FROM trades t1
                  LEFT OUTER JOIN (
                                     SELECT lt1.*
                                     FROM trades lt1
                                              INNER JOIN
                                          (
                                              SELECT token_symbol, MAX(time) AS last_time
                                              FROM trades
                                              GROUP BY token_symbol
                                          ) lt2
                                          ON lt1.token_symbol = lt2.token_symbol
                                              AND lt1.time = lt2.last_time
                                 ) t_last
                    ON t1.token_symbol = t_last.token_symbol
                  LEFT OUTER JOIN trades t_agg
                    ON t1.token_symbol = t_agg.token_symbol
                        AND t_agg.time <> t_last.time
                        AND t_agg.time >= strftime('%s', 'now', ?)
         WHERE t1.token_symbol <> ''
         GROUP BY t1.token_symbol
     ) data
WHERE ABS(chg_perc) >= ?