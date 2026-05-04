"""Shared Databricks connection utilities.

All pages import run_query and workspace_client from here so connection
setup is never duplicated.
"""

import os
import streamlit as st
import pandas as pd
from databricks import sql as dbsql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

SCHEMA = "ahtsa.awm"

BENCHMARKS = [
    "Dow Jones Industrial Average",
    "S&P 500",
    "NASDAQ Composite",
    "Russell 2000",
]


@st.cache_resource
def _db_config() -> Config:
    return Config()


@st.cache_resource
def workspace_client() -> WorkspaceClient:
    return WorkspaceClient(config=Config(http_timeout_seconds=600))


def run_query(sql: str) -> pd.DataFrame:
    """Execute SQL against the configured warehouse and return a DataFrame."""
    cfg = _db_config()
    hostname = cfg.host.removeprefix("https://").removeprefix("http://")
    warehouse_id = os.environ["DATABRICKS_WAREHOUSE_ID"]
    with dbsql.connect(
        server_hostname=hostname,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall_arrow().to_pandas()
