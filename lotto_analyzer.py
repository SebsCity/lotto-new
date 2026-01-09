import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Sidian Delta 4.0", layout="wide")
st.markdown("""
<style>
    .big-metric { font-size: 30px !important; font-weight: bold; color: #4CAF50; }
    .pair-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin: 5px; text-align: center; border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'manual_draws' not in st.session_state:
    st.session_state.manual_draws = []

def get_numbers(row):
    cols = [c for c in row.index if str(c).startswith('N') or c == 'Bonus']
    return [int(x) for x in row[cols] if pd.notnull(x) and isinstance(x, (int, float))]

# --- SIDEBAR ---
with st.sidebar:
    st.header("1. Data Hub")
    uploaded_file = st.file_uploader("Upload History", type=['xlsx', 'csv'])
    
    st.header("2. Manual Injector")
    with st.form("add_draw"):
        m_date = st.date_input("Date", datetime.today())
        m_nums = st.text_input("Numbers (e.g. 5,18,24,36,41,48,20)")
        submit_m = st.form_submit_button("Inject Draw")
        if submit_m and m_nums:
            try:
                n_list = [int(x.strip()) for x in m_nums.split(',')]
                if len(n_list) >= 6:
                    entry = {'Date': pd.Timestamp(m_date)}
                    for i in range(6): entry[f'N{i+1}'] = n_list[i]
                    if len(n_list) > 6: entry['Bonus'] = n_list[6]
                    st.session_state.manual_draws.append(entry)
                    st.success("Draw Added!")
    
    if st.session_state.manual_draws:
        if st.button("Clear Manual Data"):
            st.session_state.manual_draws = []
            st.rerun()

st.title("🎱 Sidian Delta 4.0: The Pair Engine")

# --- MAIN LOGIC ---
if uploaded_file or st.session_state.manual_draws:
    # Load & Clean
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
    else:
        df = pd.DataFrame(columns=['Date', 'N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'Bonus'])

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    if st.session_state.manual_draws:
        manual_df = pd.DataFrame(st.session_state.manual_draws)
        existing_dates = set(df['Date'].dt.date)
        manual_df = manual_df[~manual_df['Date'].dt.date.isin(existing_dates)]
        df = pd.concat([df, manual_df], ignore_index=True)
    
    df = df.sort_values('Date').reset_index(drop=True)
    last_date = df.iloc[-1]['Date']
    last_draw_nums = sorted(get_numbers(df.iloc[-1]))
    
    st.info(f"System Active. Last Data: **{last_date.date()}** | Draw: {last_draw_nums}")

    # --- TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Split-Delta Calculator", "🔍 Single Number Scan", "🧬 Pair Analysis", "🗺️ Grid"])

    # --- TAB 1: THE SPLIT-DELTA (CALIBRATION) ---
    with tab1:
        st.subheader("Lunchtime -> Teatime Calibrator")
        st.write("Enter the Lunchtime Winner and its Partner to find the Teatime Gap.")
        
        c1, c2 = st.columns(2)
        winner = c1.number_input("Lunchtime Winner (e.g., 22)", 1, 49, 22)
        partner = c2.number_input("Closest Partner (e.g., 18)", 1, 49, 18)
        
        if winner and partner:
            delta = abs(winner - partner)
            st.markdown(f"### 🔑 The Key is Delta: **{delta}**")
            
            st.write("👇 **Target Pairs for Next Draw:**")
            
            # Suggest pairs based on Hot Numbers + Delta
            # Find hot numbers from last 10 draws
            recent_nums = []
            for i in range(1, 11):
                if len(df) >= i:
                    recent_nums.extend(get_numbers(df.iloc[-i]))
            hot_candidates = [num for num, count in pd.Series(recent_nums).value_counts().head(5).items()]
            
            cols = st.columns(len(hot_candidates))
            for idx, hot in enumerate(hot_candidates):
                p1 = hot - delta
                p2 = hot + delta
                with cols[idx]:
                    st.markdown(f"<div class='pair-box'><b>Base: {hot}</b><br>{p1 if p1>0 else 'X'} & {p2 if p2<=49 else 'X'}</div>", unsafe_allow_html=True)
            
            st.caption(f"Strategy: Play the Hot Number ({hot_candidates}) paired with numbers {delta} units away.")

    # --- TAB 2: SINGLE SCAN (OLD LOGIC) ---
    with tab2:
        st.subheader("Single Number Trajectory")
        target_date = st.date_input("Predicting For:", last_date + timedelta(days=1))
        
        candidates = []
        for num in range(1, 50):
            hits = df[df.apply(lambda r: num in get_numbers(r), axis=1)]['Date'].tolist()
            
            if len(hits) >= 3:
                last_hit = hits[-1]
                prev_hit = hits[-2]
                current_gap = (pd.Timestamp(target_date) - last_hit).days
                last_int = (last_hit - prev_hit).days
                prev_int = (hits[-2] - hits[-3]).days
                
                score = 0
                reason = ""
                
                # Rapid Fire
                if prev_int > 15 and last_int <= 6 and current_gap <= 6:
                    score = 95; reason = "🔥 Aftershock"
                # Accelerator
                elif prev_int > last_int and (prev_int - last_int) > 1:
                     expected = last_int - (prev_int - last_int)
                     if abs(current_gap - expected) <= 2: score = 85; reason = "⚡ Accelerator"
                # Straggler
                if prev_int > 15 and last_int <= 5 and current_gap >= 4 and current_gap <= 8:
                    score = 99; reason = "⚠️ Critical Straggler"
                
                if score > 0:
                    candidates.append({'Ball': num, 'Logic': reason, 'Gap': current_gap, 'Score': score})
        
        if candidates:
            st.dataframe(pd.DataFrame(candidates).sort_values('Score', ascending=False), use_container_width=True)
        else:
            st.write("No critical single patterns.")

    # --- TAB 3: PAIR ANALYSIS (NEW) ---
    with tab3:
        st.subheader("Analyze Last Draw's Gaps")
        nums = sorted(last_draw_nums)
        # Calculate diffs
        diffs = [nums[i+1] - nums[i] for i in range(len(nums)-1)]
        
        st.write(f"Last Draw Sequence: {nums}")
        st.write(f"Gaps found: {diffs}")
        
        common_gap = max(set(diffs), key=diffs.count)
        st.success(f"Dominant Gap Pattern: **{common_gap}**")
        
        st.write(f"If the machine repeats the Gap of **{common_gap}**, watch these Hot Pairs:")
        
        # Generator
        hot_pairs = []
        for i in range(1, 49-common_gap):
            hot_pairs.append(f"{i} - {i+common_gap}")
        
        st.text_area("All Possible Pairs with this Gap:", ", ".join(hot_pairs[:10]) + "...")

    # --- TAB 4: GRID ---
    with tab4:
        st.subheader("The Empty Zones")
        grid = np.zeros((7, 7))
        for n in sorted(get_numbers(df.iloc[-1])):
            if 1 <= n <= 49:
                r, c = (n-1)//7, (n-1)%7
                grid[r, c] = 1
        
        c1, c2 = st.columns(2)
        c1.write(grid)
        empty_rows = [r+1 for r in range(7) if sum(grid[r, :]) == 0]
        c2.error(f"Empty Rows: {empty_rows}")

else:
    st.info("Upload File to Start.")
