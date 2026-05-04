SELECT
    (SELECT SUM(total_aum)     FROM {schema}.clients)   AS total_aum,
    (SELECT COUNT(*)           FROM {schema}.clients)   AS num_clients,
    (SELECT COUNT(*)           FROM {schema}.accounts)  AS num_accounts,
    (SELECT SUM(unrealized_gl) FROM {schema}.holdings)  AS total_gl,
    (SELECT SUM(market_value)  FROM {schema}.holdings)  AS total_mv
