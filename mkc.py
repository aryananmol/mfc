import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Fitness Challenge Sync", layout="wide")
ADMIN_PASSWORD = "jersey_fitness"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1f8n5P3spYqRbBvS8bqqoGYFA9Zt_5ixzyuUJmQjiSuI/edit?usp=sharing"

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Reading from the specific tabs we discussed: 'logs' and 'users'
    try:
        df_logs = conn.read(spreadsheet=SHEET_URL, worksheet="logs", ttl=0)
    except:
        df_logs = pd.DataFrame(columns=["id", "user", "weight", "timestamp"])
        
    try:
        df_users = conn.read(spreadsheet=SHEET_URL, worksheet="users", ttl=0)
    except:
        df_users = pd.DataFrame(columns=["username"])
        
    return df_logs, df_users

df_logs, df_users = get_data()

# --- ADMIN SIDEBAR ---
with st.sidebar:
    st.header("🔐 Admin Access")
    pwd = st.text_input("Password", type="password")
    if pwd == ADMIN_PASSWORD:
        st.success("Admin Active")
        new_user = st.text_input("Add Competitor")
        if st.button("Add"):
            new_row = pd.DataFrame([{"username": new_user}])
            updated_users = pd.concat([df_users, new_row], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="users", data=updated_users)
            st.rerun()

# --- DASHBOARD ---
st.title("🏆 Competition Tracker")
col_lb, col_chart = st.columns([1, 2])

with col_lb:
    st.subheader("Leaderboard")
    stats = []
    if not df_logs.empty and not df_users.empty:
        # We ensure weights are numeric for calculations
        df_logs["weight"] = pd.to_numeric(df_logs["weight"], errors='coerce')
        for user in df_users['username'].dropna().unique():
            u_data = df_logs[df_logs['user'] == user].sort_values('timestamp')
            if not u_data.empty:
                start_w = u_data.iloc[0]['weight']
                curr_w = u_data.iloc[-1]['weight']
                if start_w and curr_w and start_w > 0:
                    loss_pct = ((start_w - curr_w) / start_w) * 100
                    stats.append({"User": user, "Current": curr_w, "Loss %": round(loss_pct, 2)})
    
    if stats:
        st.dataframe(pd.DataFrame(stats).sort_values("Loss %", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("No data found in the sheet. Start by adding users in the Admin panel.")

with col_chart:
    st.subheader("Progress Trends")
    if not df_logs.empty:
        fig = px.line(df_logs, x="timestamp", y="weight", color="user", markers=True, template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log some weights to see the progress chart!")

# --- INTERACTIVE CHAT ---
st.divider()
st.subheader("💬 Competition Bot")
user_list = df_users['username'].dropna().tolist() if not df_users.empty else []
current_user = st.selectbox("Identify Yourself:", ["Select..."] + user_list)

if prompt := st.chat_input("Ex: 'Update weight to 185'"):
    if current_user == "Select...":
        st.error("Please select your name from the dropdown first.")
    else:
        p = prompt.lower()
        if "update" in p or "log" in p:
            # Extract number from the chat message
            nums = [float(s) for s in p.split() if s.replace('.','',1).isdigit()]
            if nums:
                new_entry = pd.DataFrame([{
                    "id": len(df_logs) + 1,
                    "user": current_user,
                    "weight": nums[0],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                updated_logs = pd.concat([df_logs, new_entry], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="logs", data=updated_logs)
                st.success(f"Weight updated to {nums[0]}!")
                st.rerun()
        
        elif "undo" in p or "delete" in p:
            if not df_logs.empty:
                user_indices = df_logs[df_logs['user'] == current_user].index
                if not user_indices.empty:
                    updated_logs = df_logs.drop(user_indices[-1])
                    conn.update(spreadsheet=SHEET_URL, worksheet="logs", data=updated_logs)
                    st.warning("Last entry removed.")
                    st.rerun()
