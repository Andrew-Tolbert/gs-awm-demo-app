"""SQL query builders.

Each function loads a .sql template from the sql/ directory, injects
the supplied parameters, and returns the final SQL string ready to pass
to run_query(). SQL files use {placeholder} syntax — see each file for
the full list of parameters it accepts.
"""

from pathlib import Path
from lib.db import SCHEMA

_SQL_DIR = Path(__file__).parent.parent / "sql"


def _load(filename: str) -> str:
    return (_SQL_DIR / filename).read_text()


# ── Parameterised queries ─────────────────────────────────────────────────────

def advisor_holdings_sql(start_dt: str, end_dt: str, benchmark: str) -> str:
    """Holdings with period P&L, alpha, and fee attribution.

    Multi-select filters (advisor, account_type, ticker) are NOT applied here;
    apply them in pandas on the returned DataFrame so filter widgets can be
    populated from the full result before any filtering happens.
    """
    return _load("advisor_holdings.sql").format(
        schema=SCHEMA,
        start_dt=start_dt,
        end_dt=end_dt,
        benchmark=benchmark,
    )


def advisor_timeseries_sql(
    start_dt: str,
    end_dt: str,
    benchmark: str,
    advisor_ids: list[str],
    account_types: list[str],
    tickers: list[str],
) -> str:
    """Daily portfolio return, benchmark return, and cumulative alpha.

    Multi-select filters are injected directly into SQL because they affect
    portfolio composition (the baseline value calculation depends on which
    positions are included).
    """
    return _load("advisor_timeseries.sql").format(
        schema=SCHEMA,
        start_dt=start_dt,
        end_dt=end_dt,
        benchmark=benchmark,
        advisor_filter=_in_clause("c.advisor_id", advisor_ids),
        account_filter=_in_clause("a.account_type", account_types),
        ticker_filter=_in_clause("t.ticker", tickers),
    )


def _in_clause(column: str, values: list[str]) -> str:
    """Return a SQL IN clause, or '1=1' when the list is empty."""
    if not values:
        return "1=1"
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"
