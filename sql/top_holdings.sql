SELECT
    ticker,
    company_name,
    sector,
    ROUND(SUM(market_value) / 1e6, 1)      AS market_value_m,
    ROUND(SUM(unrealized_gl) / 1e6, 1)     AS unrealized_gl_m,
    ROUND(AVG(unrealized_gl_pct), 1)        AS gl_pct,
    ROUND(AVG(pct_of_total_aum) * 100, 2)  AS weight_pct,
    MAX(analyst_consensus)                  AS analyst_view
FROM {schema}.gold_portfolio_fundamentals
WHERE holdings_date = (SELECT MAX(holdings_date) FROM {schema}.gold_portfolio_fundamentals)
  AND is_etf = false
  AND sector IS NOT NULL
GROUP BY ticker, company_name, sector
ORDER BY SUM(market_value) DESC
LIMIT 10
