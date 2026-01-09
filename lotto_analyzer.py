import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Sidian Automaton 3.0", layout="wide", initial_sidebar_state="expanded")

# --- CSS FOR VISUALS ---
st.markdown("""
<style>
    .big-font { font-size:20px !important; font-weight: bold; }
    .highlight { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .red-alert { color: #ff4b4b; font-weight: bold; }
    .green-go { color: #00c853; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE (To keep manual data alive) ---
if 'manual_draws' not in st.session_state:
    st.session_state.manual_draws = []

def get_numbers(row):
    """Extract numbers from a row regardless of column names"""
    cols = [c for c in row.index if str(c).startswith('N') or c == 'Bonus']
    return [int(x) for x in row[cols] if pd.notnull(x) and isinstance(x, (int, float))]

# --- MAIN APP ---
st.title("🎱 Sidian Automaton: The 3D Logic Engine")
st.markdown("This system scans for **Time Echoes**, **Rapid Fire Patterns**, and **Grid Vacuums**.")

# 1. SIDEBAR - DATA ENTRY
with st.sidebar:
    st.header("1. Load Data")
    uploaded_file = st.file_uploader("Upload History (CSV/Excel)", type=['xlsx', 'csv'])
    
    st.header("2. Update Live")
    st.caption("Add draws missing from your file:")
    with st.form("add_draw"):
        m_date = st.date_input("Draw Date", datetime.today())
        m_nums = st.text_input("Numbers (e.g. 5,18,24,36,41,48,20)")
        submit_m = st.form_submit_button("Inject Draw")
        
        if submit_m and m_nums:
            try:
                # Parse
                n_list = [int(x.strip()) for x in m_nums.split(',')]
                if len(n_list) >= 6:
                    entry = {'Date': pd.Timestamp(m_date)}
                    for i in range(6): entry[f'N{i+1}'] = n_list[i]
                    entry['Bonus'] = n_list[6] if len(n_list) > 6 else 0
                    st.session_state.manual_draws.append(entry)
                    st.success("Draw Injected!")
                else:
                    st.error("Need 6+ numbers")
            except:
                st.error("Invalid Format")

    if st.session_state.manual_draws:
        st.write("---")
        st.write(f"**Injected Draws:** {len(st.session_state.manual_draws)}")
        if st.button("Clear Manual Data"):
            st.session_state.manual_draws = []
            st.rerun()

# 2. DATA PROCESSING
if uploaded_file or st.session_state.manual_draws:
    # A. Load File
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    else:
        df = pd.DataFrame(columns=['Date', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'Bonus'])

    # B. Clean Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # C. Merge Manual Data
    if st.session_state.manual_draws:
        manual_df = pd.DataFrame(st.session_state.manual_draws)
        # Filter duplicates based on Date
        existing_dates = set(df['Date'].dt.date)
        manual_df = manual_df[~manual_df['Date'].dt.date.isin(existing_dates)]
        df = pd.concat([df, manual_df], ignore_index=True)
    
    df = df.sort_values('Date').reset_index(drop=True)
    last_date = df.iloc[-1]['Date']

    # --- THE SIDIAN SCANNER (Logic Engine) ---
    st.write("---")
    st.subheader(f"🔍 The Sidian Scan (Status: {last_date.date()})")
    
    col_scan, col_grid = st.columns([2, 1])
    
    with col_scan:
        target_date = st.date_input("Predicting For:", last_date + timedelta(days=1))
        
        candidates = []
        for num in range(1, 50):
            # Get History
            hits = []
            for idx, row in df.iterrows():
                if num in get_numbers(row):
                    hits.append(row['Date'])
            
            if len(hits) >= 3:
                last_hit = hits[-1]
                prev_hit = hits[-2]
                prev_prev = hits[-3]
                
                # Intervals
                current_gap = (pd.Timestamp(target_date) - last_hit).days
                last_interval = (last_hit - prev_hit).days
                prev_interval = (prev_hit - prev_prev).days
                
                reason = None
                score = 0
                pattern = f"{prev_interval}d → {last_interval}d"

                # LOGIC 1: RAPID FIRE ECHO (Long -> Short -> Short)
                # E.g., 20 days -> 4 days -> Expect < 5 days
                if prev_interval > 12 and last_interval <= 6:
                    if current_gap <= 6:
                        reason = "🔥 Rapid Fire Echo"
                        score = 95
                
                # LOGIC 2: CONSISTENT RHYTHM
                # E.g., 4 days -> 4 days -> Expect 4 days
                elif abs(last_interval - prev_interval) <= 1:
                    if abs(current_gap - last_interval) <= 1:
                        reason = "🥁 Consistent Rhythm"
                        score = 85
                
                # LOGIC 3: THE ACCELERATOR
                # E.g., 10 days -> 7 days -> Expect 4 days
                elif prev_interval > last_interval and (prev_interval - last_interval) > 1:
                    trend = prev_interval - last_interval
                    expected = last_interval - trend
                    if expected > 0 and abs(current_gap - expected) <= 2:
                        reason = "⚡ Acceleration"
                        score = 80
                
                # LOGIC 4: THE STRAGGLER (Overdue Echo)
                # Like Number 10 today
                if prev_interval > 15 and last_interval <= 5 and current_gap >= 4 and current_gap <= 8:
                    reason = "⚠️ Overdue Echo (Critical)"
                    score = 98

                if reason:
                    candidates.append({
                        'Ball': num,
                        'Strategy': reason,
                        'Pattern': pattern,
                        'Current Gap': f"{current_gap} days",
                        'Score': score
                    })
        
        # Display Results
        if candidates:
            res_df = pd.DataFrame(candidates).sort_values('Score', ascending=False)
            st.dataframe(res_df.style.apply(lambda x: ['background-color: #e6fffa' if v > 90 else '' for v in x.Score], axis=1), use_container_width=True)
        else:
            st.info("No high-probability patterns detected for this specific date.")

    # --- GRID LOGIC ---
    with col_grid:
        st.markdown("### 🗺️ Grid Analysis")
        # Build Grid based on Last Draw
        last_nums = get_numbers(df.iloc[-1])
        
        # 7x7 Grid
        grid = np.zeros((7, 7))
        for n in last_nums:
            if 1 <= n <= 49:
                r, c = (n-1)//7, (n-1)%7
                grid[r, c] = 1
        
        st.write("Last Draw Distribution:")
        st.write(grid)
        
        # Calc Empty
        empty_rows = [r+1 for r in range(7) if sum(grid[r, :]) == 0]
        empty_cols = [c+1 for c in range(7) if sum(grid[:, c]) == 0]
        
        st.error(f"**Empty Rows:** {empty_rows}")
        st.error(f"**Empty Cols:** {empty_cols}")
        st.caption("Tip: Pick numbers that sit in these Empty Zones.")

    # --- INDIVIDUAL DEEP DIVE ---
    st.write("---")
    st.subheader("🔭 Deep Dive Trajectory")
    
    target_num = st.number_input("Check specific number:", 1, 49, 40)
    if target_num:
        hits = []
        for idx, row in df.iterrows():
            nums = get_numbers(row)
            if target_num in nums:
                pos = nums.index(target_num) + 1
                hits.append({'Date': row['Date'], 'Pos': pos})
        
        t_df = pd.DataFrame(hits)
        if not t_df.empty:
            t_df['Prev'] = t_df['Date'].shift(1)
            t_df['Interval'] = (t_df['Date'] - t_df['Prev']).dt.days
            
            # Prediction Logic
            last_pos = t_df.iloc[-1]['Pos']
            last_int = t_df.iloc[-1]['Interval']
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Last Hit", f"{t_df.iloc[-1]['Date'].date()}")
            c2.metric("Last Interval", f"{int(last_int)} days" if pd.notnull(last_int) else "N/A")
            c3.metric("Last Position", f"Ball {last_pos}")
            
            st.table(t_df[['Date', 'Pos', 'Interval']].tail(5))
            
            # Suggestion
            if last_pos <= 2: suggest_pos = "Bounce High (4-6)"
            elif last_pos >= 5: suggest_pos = "Bounce Low (1-3)"
            else: suggest_pos = "Stabilize Mid (3-4)"
            
            st.success(f"**Prediction:** If playing {target_num}, target **{suggest_pos}**.")
            
else:
    st.info("👋 Welcome. Upload your history file to activate the Sidian Logic.")

