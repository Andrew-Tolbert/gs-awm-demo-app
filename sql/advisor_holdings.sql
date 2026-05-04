-- Advisor 360: position-level holdings with period P&L, alpha, and fee attribution.
-- Parameters: {schema}, {start_dt}, {end_dt}, {benchmark}
-- ETF sector look-through applied in the final SELECT via bronze_etf_sectors.

WITH

-- ── Date range parameters ────────────────────────────────────────────────────
params AS (
  SELECT '{start_dt}' AS start_dt, '{end_dt}' AS end_dt
),

-- ── Nearest trading day on or before each date boundary ─────────────────────
-- Prevents NULL prices when boundaries fall on weekends or holidays.
price_dates AS (
  SELECT
    MAX(CASE WHEN date <= (SELECT end_dt   FROM params) THEN date END) AS end_price_dt,
    MAX(CASE WHEN date <= (SELECT start_dt FROM params) THEN date END) AS start_price_dt
  FROM {schema}.bronze_historical_prices
),

-- ── Equity positions as of end_dt ────────────────────────────────────────────
equity_positions AS (
  SELECT account_id, ticker, SUM(quantity) AS quantity, SUM(gross_amount) AS total_cost
  FROM {schema}.transactions
  WHERE action IN ('BUY', 'DRIP') AND ticker != 'CASH'
    AND date <= (SELECT end_dt FROM params)
  GROUP BY account_id, ticker
),

-- ── Cash balance as of end_dt ────────────────────────────────────────────────
-- initial deposit + dividends + DRIP reinvestment (negative) + fees (negative)
cash_positions AS (
  SELECT
    account_id,
    GREATEST(0.0,
      SUM(CASE WHEN action = 'BUY'      AND ticker = 'CASH' THEN quantity   ELSE 0.0 END)
    + SUM(CASE WHEN action = 'DIVIDEND'                      THEN net_amount ELSE 0.0 END)
    + SUM(CASE WHEN action = 'DRIP'                          THEN net_amount ELSE 0.0 END)
    + SUM(CASE WHEN action = 'FEE'                           THEN net_amount ELSE 0.0 END)
    ) AS cash_balance
  FROM {schema}.transactions
  WHERE date <= (SELECT end_dt FROM params)
  GROUP BY account_id
),

-- ── End-of-period and start-of-period prices ─────────────────────────────────
end_prices AS (
  SELECT symbol, adjClose AS end_price
  FROM {schema}.bronze_historical_prices
  WHERE date = (SELECT end_price_dt FROM price_dates)
),
start_prices AS (
  SELECT symbol, adjClose AS start_price
  FROM {schema}.bronze_historical_prices
  WHERE date = (SELECT start_price_dt FROM price_dates)
),

-- ── Asset class reference (from snapshot holdings, not transactions) ─────────
asset_class_ref AS (
  SELECT DISTINCT account_id, ticker, asset_class
  FROM {schema}.holdings
  WHERE ticker != 'CASH'
),

-- ── Pre-existing positions (opened before start_dt) ──────────────────────────
-- Used to set period cost basis: pre-existing → start_price, new → avg cost paid.
pre_existing_positions AS (
  SELECT DISTINCT account_id, ticker
  FROM {schema}.transactions
  WHERE action IN ('BUY', 'DRIP') AND ticker != 'CASH'
    AND date < (SELECT start_dt FROM params)
),

-- ── Benchmark return for the period ──────────────────────────────────────────
benchmark AS (
  SELECT
    v.symbol                                                                            AS benchmark_symbol,
    '{benchmark}'                                                                       AS benchmark,
    MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END)             AS benchmark_start,
    MAX_BY(v.close, CASE WHEN v.date <= pd.end_price_dt   THEN v.date END)             AS benchmark_end,
    (MAX_BY(v.close, CASE WHEN v.date <= pd.end_price_dt   THEN v.date END)
     - MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END))
    / NULLIF(MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END), 0)
      AS benchmark_return
  FROM {schema}.bronze_indexes_and_vix v
  CROSS JOIN price_dates pd
  WHERE v.index = '{benchmark}'
  GROUP BY ALL
),

-- ── Per-ticker equity rows ────────────────────────────────────────────────────
equity_rows AS (
  SELECT
    ep.account_id,
    ep.ticker,
    COALESCE(ac.asset_class, 'Equity')                                AS asset_class,
    ep.quantity,
    epr.end_price                                                      AS price,
    ep.quantity * epr.end_price                                        AS market_value,
    ep.total_cost / ep.quantity                                        AS cost_basis_per_share,
    ep.total_cost                                                      AS total_cost_basis,
    ep.quantity * epr.end_price - ep.total_cost                        AS unrealized_gl,
    ROUND((ep.quantity * epr.end_price - ep.total_cost)
          / NULLIF(ep.total_cost, 0) * 100, 2)                        AS unrealized_gl_pct,
    spr.start_price,
    ROUND((epr.end_price - spr.start_price)
          / NULLIF(spr.start_price, 0) * 100, 2)                      AS period_return_pct,
    CASE WHEN pp.account_id IS NOT NULL
         THEN spr.start_price
         ELSE ep.total_cost / NULLIF(ep.quantity, 0)
    END                                                                AS period_cost_basis_per_share
  FROM equity_positions ep
  JOIN end_prices   epr ON ep.ticker = epr.symbol
  LEFT JOIN start_prices         spr ON ep.ticker = spr.symbol
  LEFT JOIN asset_class_ref       ac ON ep.account_id = ac.account_id AND ep.ticker = ac.ticker
  LEFT JOIN pre_existing_positions pp ON ep.account_id = pp.account_id AND ep.ticker = pp.ticker
),

-- ── Cash rows (one per account) ───────────────────────────────────────────────
cash_rows AS (
  SELECT
    account_id,
    'CASH'       AS ticker,
    'Cash'       AS asset_class,
    cash_balance AS quantity,
    1.0          AS price,
    cash_balance AS market_value,
    1.0          AS cost_basis_per_share,
    cash_balance AS total_cost_basis,
    0.0          AS unrealized_gl,
    0.0          AS unrealized_gl_pct,
    1.0          AS start_price,
    0.0          AS period_return_pct,
    1.0          AS period_cost_basis_per_share
  FROM cash_positions
  WHERE cash_balance > 0
),

all_holdings AS (
  SELECT * FROM equity_rows
  UNION ALL
  SELECT * FROM cash_rows
),

-- ── Advisory fees attributable to the period ─────────────────────────────────
period_fees AS (
  SELECT account_id, ABS(SUM(net_amount)) AS fees_paid
  FROM {schema}.transactions
  WHERE action = 'FEE'
    AND date BETWEEN (SELECT start_dt FROM params) AND (SELECT end_dt FROM params)
  GROUP BY account_id
),

-- ── Position-level metrics (window functions computed here) ───────────────────
position_level AS (
  SELECT
    (SELECT start_price_dt FROM price_dates) AS period_start_price_date,
    (SELECT end_price_dt   FROM price_dates) AS as_of_date,
    bm.benchmark_symbol,
    ROUND(bm.benchmark_return,       6) AS benchmark_return,
    ROUND(bm.benchmark_return * 100, 4) AS benchmark_return_pct,

    c.client_id, c.client_name, c.advisor_id, c.tier, c.risk_profile,
    ah.account_id, a.account_name, a.account_type,
    ah.ticker, ah.asset_class,

    ROUND(ah.quantity,              4) AS quantity,
    ROUND(ah.price,                 4) AS price,
    ROUND(ah.market_value,          2) AS market_value,
    ROUND(ah.cost_basis_per_share,  4) AS cost_basis_per_share,
    ROUND(ah.total_cost_basis,      2) AS total_cost_basis,
    ROUND(ah.unrealized_gl,         2) AS unrealized_gl,
    ah.unrealized_gl_pct,

    ROUND(ah.quantity * ah.start_price,               2) AS market_value_at_period_start,
    ROUND(ah.period_cost_basis_per_share,              4) AS period_cost_basis_per_share,
    ROUND(ah.quantity * ah.period_cost_basis_per_share, 2) AS period_total_cost_basis,
    ROUND(ah.market_value - ah.quantity * ah.period_cost_basis_per_share, 2) AS period_pl,
    ah.period_return_pct,

    -- Portfolio weights
    ROUND(ah.market_value / NULLIF(SUM(ah.market_value) OVER (PARTITION BY ah.account_id), 0) * 100, 2) AS pct_of_account,
    ROUND(ah.market_value / NULLIF(SUM(ah.market_value) OVER (PARTITION BY c.client_id),   0) * 100, 2) AS pct_of_client_portfolio,
    ROUND(ah.market_value / NULLIF(SUM(ah.market_value) OVER (),                           0) * 100, 4) AS pct_of_total_aum,

    -- Return contribution (sum at any grain = total return %)
    ROUND((ah.market_value - ah.quantity * ah.start_price)
          / NULLIF(SUM(ah.quantity * ah.start_price) OVER (PARTITION BY c.client_id), 0), 6) AS contribution_to_client_return,

    -- Fee attribution (prorated by position weight within account)
    ROUND(COALESCE(pf.fees_paid, 0)
          * ah.market_value
          / NULLIF(SUM(ah.market_value) OVER (PARTITION BY ah.account_id), 0), 2) AS fees_attributed

  FROM all_holdings ah
  JOIN {schema}.accounts a  ON ah.account_id = a.account_id
  JOIN {schema}.clients  c  ON a.client_id   = c.client_id
  CROSS JOIN benchmark bm
  LEFT JOIN period_fees pf  ON ah.account_id = pf.account_id
)

-- ── Final SELECT: ETF sector look-through ─────────────────────────────────────
-- ETF positions expand into N sector rows via bronze_etf_sectors.
-- All dollar columns are scaled by weight_in_source so SUM() stays correct at any grain.
SELECT
  pl.period_start_price_date,
  pl.as_of_date,
  pl.benchmark_symbol,
  pl.benchmark_return,
  pl.benchmark_return_pct,

  pl.client_id, pl.client_name, pl.advisor_id, pl.tier, pl.risk_profile,
  pl.account_id, pl.account_name, pl.account_type,
  pl.ticker, pl.asset_class,

  CASE
    WHEN pl.ticker = 'CASH'         THEN 'Cash'
    WHEN es.etf_symbol IS NOT NULL  THEN COALESCE(es.sector, 'Unknown')
    ELSE                                 COALESCE(cp.sector, 'Unknown')
  END                                                        AS sector,
  CASE
    WHEN es.etf_symbol IS NULL AND pl.ticker != 'CASH'
    THEN COALESCE(cp.industry, 'Unknown')
  END                                                        AS industry,
  CASE WHEN es.etf_symbol IS NOT NULL THEN 'Indirect' ELSE 'Direct' END AS source_type,
  COALESCE(es.weightPercentage / 100, 1.0)                  AS weight_in_source,

  -- Per-share / rate columns (not scaled — position-level rates are unchanged by sector split)
  pl.price,
  pl.cost_basis_per_share,
  pl.period_cost_basis_per_share,
  pl.period_return_pct,
  pl.unrealized_gl_pct,

  -- Dollar columns scaled by ETF sector weight
  ROUND(pl.quantity              * COALESCE(es.weightPercentage / 100, 1.0), 4) AS quantity,
  ROUND(pl.market_value          * COALESCE(es.weightPercentage / 100, 1.0), 2) AS market_value,
  ROUND(pl.total_cost_basis      * COALESCE(es.weightPercentage / 100, 1.0), 2) AS total_cost_basis,
  ROUND(pl.unrealized_gl         * COALESCE(es.weightPercentage / 100, 1.0), 2) AS unrealized_gl,
  ROUND(pl.period_total_cost_basis * COALESCE(es.weightPercentage / 100, 1.0), 2) AS period_total_cost_basis,
  ROUND(pl.period_pl             * COALESCE(es.weightPercentage / 100, 1.0), 2) AS period_pl,
  ROUND(pl.pct_of_account        * COALESCE(es.weightPercentage / 100, 1.0), 4) AS pct_of_account,
  ROUND(pl.pct_of_client_portfolio * COALESCE(es.weightPercentage / 100, 1.0), 4) AS pct_of_client_portfolio,
  ROUND(pl.pct_of_total_aum      * COALESCE(es.weightPercentage / 100, 1.0), 6) AS pct_of_total_aum,
  ROUND(pl.contribution_to_client_return * COALESCE(es.weightPercentage / 100, 1.0), 6) AS contribution_to_client_return,
  ROUND(pl.fees_attributed       * COALESCE(es.weightPercentage / 100, 1.0), 2) AS fees_attributed

FROM position_level pl
LEFT JOIN {schema}.bronze_etf_sectors     es ON pl.ticker = es.etf_symbol
LEFT JOIN {schema}.bronze_company_profiles cp ON pl.ticker = cp.symbol
ORDER BY pl.client_name, pl.account_id, pl.asset_class, pl.ticker, sector
