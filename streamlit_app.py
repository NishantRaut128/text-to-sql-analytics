import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Business Analytics Copilot", page_icon="📊", layout="wide")
st.title("📊 Business Analytics Copilot")
st.caption("Ask business questions in plain English. Inspect the generated SQL before trusting the result.")
api_url = os.getenv("API_URL", "http://localhost:8000")
question = st.text_input("Ask a question", placeholder="What was our monthly revenue?")
if st.button("Run analysis", type="primary", disabled=not question):
    with st.spinner("Generating, validating and executing SQL..."):
        try:
            response = requests.post(f"{api_url}/ask", json={"question": question}, timeout=90)
            if response.status_code != 200:
                st.error(response.json().get("detail", "Request failed"))
            else:
                data = response.json()
                st.success(f"Query completed · {data['row_count']} rows returned")
                st.subheader("Generated SQL")
                st.code(data["sql"], language="sql")
                st.caption(data["explanation"])
                df = pd.DataFrame(data["rows"], columns=data["columns"])
                st.subheader("Query results")
                st.dataframe(df, use_container_width=True)
                numeric = df.select_dtypes(include="number").columns.tolist()
                metrics = [c for c in numeric if not c.lower().endswith("_id")]

                dates = [
                    c for c in df.columns
                    if "date" in c.lower() or "month" in c.lower()
                ]

                # Exclude ID columns from category labels too
                labels = [
                    c for c in df.columns
                    if c not in metrics
                    and not c.lower().endswith("_id")
                    and c.lower() != "index"
                ]

                if metrics and len(df) > 1:
                    metric = st.selectbox("Metric to visualize", metrics)

                    if dates:
                        st.plotly_chart(
                            px.line(df, x=dates[0], y=metric, markers=True),
                            use_container_width=True
                        )
                    elif labels:
                        st.plotly_chart(
                            px.bar(df, x=labels[0], y=metric),
                            use_container_width=True
                        )
                st.download_button("Download results as CSV", df.to_csv(index=False), "analytics_results.csv", "text/csv")
        except requests.RequestException as exc:
            st.error(f"Could not connect to API: {exc}")

with st.expander("Example questions"):
    st.markdown("- What was our monthly revenue?\n- Show the top 10 products by revenue.\n- Which customers generated the highest revenue?\n- What is the total order count?")
