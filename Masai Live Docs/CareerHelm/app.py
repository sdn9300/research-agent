"""
EdgeDash Subsystem 10: Interactive Streamlit Dashboard (Deployed & Hardened)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 10 & W4_S2_Prompt.md (Rules 47-51)
Decoupled read-only presentation reading from the latest verified passing cycle.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
import pandas as pd
import streamlit as st

from edgedash.config import load_config
from edgedash.storage import Storage
from edgedash.health import check_health
from edgedash.query.ask import ask
from edgedash.query.tools import tool_best_matches, tool_top_gaps, tool_listing_count

logger = logging.getLogger("edgedash.app")

st.set_page_config(
    page_title="CareerHelm — Autonomous Career Radar",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------
# Hostile Startup & Config Initialization (Rule 50)
# -------------------------------------------------------------------
storage = None
config = None
db_error_msg = None

try:
    config = load_config()
    storage = Storage(config.db_path)
except Exception as e:
    db_error_msg = f"Database initialization warning: {e}"
    logger.error(db_error_msg)

# Custom header
st.title("🧭 CareerHelm — Autonomous Career Radar")
role_name = config.target_role if config else "Machine Learning Engineer"
city_name = config.target_city if config else "Bengaluru"
st.caption(f"Tracking **{role_name}** in **{city_name}** | CareerHelm Autonomous Market Loop")

# -------------------------------------------------------------------
# Health Status Line Banner (C8-P4 / Rule 50)
# -------------------------------------------------------------------
try:
    if storage:
        health = check_health(storage)
        if health.status_label == "green":
            st.success("🟢 **Live Status: Operational** — Latest market cycle verified within 24 hours.")
        elif health.status_label == "amber":
            st.warning("🟡 **Live Status: Stale** — Last successful market cycle was >24 hours ago.")
        else:
            st.error(f"🔴 **Live Status: Attention Needed** — {health.message}")
    else:
        st.info("ℹ️ **Database not configured** — Operating in offline presentation mode.")
except Exception as e:
    logger.warning(f"Health banner error: {e}")
    st.info("ℹ️ System status unavailable.")

# -------------------------------------------------------------------
# Top Metrics (Protected against empty/failed database)
# -------------------------------------------------------------------
total_listings = 0
scored_listings = 0
cand_skills_count = len(config.my_skills) if config else 0
verdict_status = "UNKNOWN"

if storage:
    try:
        counts = tool_listing_count(storage)
        total_listings = counts.get("total_listings", 0)
        scored_listings = counts.get("scored_listings", 0)
        verdict = storage.get_latest_verdict()
        verdict_status = verdict["verdict"].upper() if verdict else "PASS"
    except Exception as e:
        logger.warning(f"Metrics fetch error: {e}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Listings", total_listings)
col2.metric("Scored Listings", scored_listings)
col3.metric("Candidate Skills", cand_skills_count)
col4.metric("Verification Status", verdict_status, delta="Passing" if verdict_status == "PASS" else "Needs Check")

st.divider()

# -------------------------------------------------------------------
# Natural Language Query Section ("Ask Your Data")
# -------------------------------------------------------------------
st.subheader("💬 Ask Your Market Data")
user_query = st.text_input("Ask a question about your jobs, missing skills, or companies hiring:", placeholder="e.g. What are my top skill gaps? or Who is hiring for ML?")

example_col1, example_col2, example_col3 = st.columns(3)
if example_col1.button("🏆 Show best matches"):
    user_query = "What are my best job matches?"
if example_col2.button("📊 Top skill gaps"):
    user_query = "What are my top skill gaps by opportunity cost?"
if example_col3.button("🏢 Who is hiring?"):
    user_query = "Which companies are hiring?"

if user_query:
    if storage:
        with st.spinner("Querying market database..."):
            try:
                ans = ask(user_query, storage)
                if ans.get("status") == "answered":
                    st.success(ans["answer"])
                    if ans.get("data") and isinstance(ans["data"], list):
                        with st.expander("Inspect Raw Data Table"):
                            st.dataframe(pd.DataFrame(ans["data"]), use_container_width=True)
                else:
                    st.warning(ans.get("answer", "No data available for this query."))
            except Exception as e:
                st.warning(f"Query could not be answered: {e}")
    else:
        st.info("Market database not available to answer query.")

st.divider()

# -------------------------------------------------------------------
# 3 Presentation Panels (Each wrapped per Rule 50)
# -------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🏆 Best Matches", "📈 Skill Gaps & Opportunity Cost", "📋 Agent Activity & Verdicts"])

# Panel 1: Best Matches
with tab1:
    st.subheader("Highest-Fit Job Opportunities")
    try:
        if storage and scored_listings > 0:
            min_score_filter = st.slider("Minimum Fit Score", min_value=0, max_value=100, value=50, step=5)
            matches = tool_best_matches(storage, limit=25, min_score=min_score_filter)
            if matches:
                df_matches = pd.DataFrame(matches)[["title", "company", "location", "fit_score", "fit_reason", "url"]]
                st.dataframe(
                    df_matches,
                    column_config={
                        "url": st.column_config.LinkColumn("Job Link"),
                        "fit_score": st.column_config.ProgressColumn("Fit Score", min_value=0, max_value=100, format="%d"),
                    },
                    use_container_width=True,
                )
            else:
                st.info("No listings found matching the selected score threshold.")
        else:
            st.info("No cycles yet — first run is scheduled for 06:00 AM IST. Listings will appear here after the initial cycle.")
    except Exception as e:
        logger.error(f"Panel 1 error: {e}")
        st.info("Unable to render match data. Please refresh or check database status.")

# Panel 2: Skill Gaps
with tab2:
    st.subheader("Opportunity Cost Skill Gaps")
    st.caption("Opportunity Cost = $\\sum \\frac{\\text{Fit Score}}{100}$ across all jobs blocked by missing skill.")
    try:
        if storage:
            gaps = tool_top_gaps(storage, limit=15)
            if gaps:
                df_gaps = pd.DataFrame(gaps)[["skill", "opportunity_cost", "listings_blocked", "mean_score", "top_score"]]
                df_gaps["skill"] = df_gaps["skill"].str.title()
                col_chart, col_table = st.columns([1, 1])
                with col_chart:
                    st.bar_chart(df_gaps.set_index("skill")["opportunity_cost"])
                with col_table:
                    st.dataframe(df_gaps, use_container_width=True)
            else:
                st.info("No skill gaps computed yet. Gaps will be calculated automatically during the next cycle.")
        else:
            st.info("Storage offline.")
    except Exception as e:
        logger.error(f"Panel 2 error: {e}")
        st.info("Unable to render skill gaps.")

# Panel 3: Cycle Logs & Verdicts
with tab3:
    st.subheader("Autonomous Cycle Log & Verifier Verdicts")
    try:
        if storage:
            col_v, col_l = st.columns(2)
            with col_v:
                st.markdown("#### Historical Verifier Verdicts")
                query_v = "SELECT checked_at, verdict, failed_check, action_taken FROM verdicts ORDER BY checked_at DESC LIMIT 10"
                with storage.get_connection() as conn:
                    df_v = pd.read_sql_query(query_v, conn)
                st.dataframe(df_v, use_container_width=True)

            with col_l:
                st.markdown("#### Recent Sub-Agent Execution Logs")
                recent_logs = storage.get_recent_cycle_logs(limit=15)
                if recent_logs:
                    df_logs = pd.DataFrame(recent_logs)[["started_at", "agent", "status", "records_touched", "notes"]]
                    st.dataframe(df_logs, use_container_width=True)
                else:
                    st.info("No cycle logs recorded yet.")
        else:
            st.info("Storage offline.")
    except Exception as e:
        logger.error(f"Panel 3 error: {e}")
        st.info("Unable to load execution logs.")

# -------------------------------------------------------------------
# Footer (Rule 48 & Rule 50)
# -------------------------------------------------------------------
st.divider()
last_ts = "Recent"
try:
    if storage:
        latest_verdict = storage.get_latest_verdict()
        if latest_verdict and latest_verdict.get("checked_at"):
            last_ts = latest_verdict["checked_at"][:19].replace("T", " ") + " UTC"
except Exception:
    pass

footer_col1, footer_col2 = st.columns([2, 1])
with footer_col1:
    st.caption(f"Last verified autonomous cycle: **{last_ts}** | Backend: **{storage.backend.upper() if storage else 'OFFLINE'}**")
with footer_col2:
    st.caption("[GitHub Repository: sdn9300/research-agent](https://github.com/sdn9300)")
