import os
import streamlit as st
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

cfg = Config()

def sql_query_with_user_token(query: str, user_token: str) -> pd.DataFrame:
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        access_token=user_token,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

st.set_page_config(layout="wide")

user_token = st.context.headers.get("X-Forwarded-Access-Token")

with st.sidebar.expander("Debug", expanded=True):
    st.write("host:", cfg.host)
    st.write("warehouse_id:", os.getenv('DATABRICKS_WAREHOUSE_ID'))
    st.write("token present:", bool(user_token))

@st.cache_data(ttl=30)
def getData(token):
    return sql_query_with_user_token("select * from samples.nyctaxi.trips limit 5000", token)

data = getData(user_token)

st.header("Taxi fare distribution !!! :)")
col1, col2 = st.columns([3, 1])
with col1:
    st.scatter_chart(data=data, height=400, width=700, y="fare_amount", x="trip_distance")
with col2:
    st.subheader("Predict fare")
    pickup = st.text_input("From (zipcode)", value="10003")
    dropoff = st.text_input("To (zipcode)", value="11238")
    d = data[(data['pickup_zip'] == int(pickup)) & (data['dropoff_zip'] == int(dropoff))]
    st.write(f"# **${d['fare_amount'].mean() if len(d) > 0 else 99:.2f}**")

st.dataframe(data=data, height=600, use_container_width=True)
