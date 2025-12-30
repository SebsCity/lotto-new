import streamlit as st
import pandas as pd
from collections import Counter
from itertools import combinations

# --- Page Configuration ---
st.set_page_config(page_title="Lotto Split Strategy Engine", layout="wide")

st.title("🎱 Lotto Strategy Engine: Splits & Followers")
st.markdown("""
**Advanced Mode:** This engine calculates not just *what* numbers are coming, but *how* they arrive (Direct vs. Splits).
""")

# --- Sidebar: Configuration ---
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload History (.xlsx or .csv)", type=['xlsx', 'csv'])

st.sidebar.header("2. Game Settings")
game_type = st.sidebar.radio("Select Game Type:", ("UK 49s (6 + Bonus)", "SA Daily Lotto (5 Numbers)"))

# --- Helper Functions ---

def clean_data(df, game_type):
    """Standardizes column names."""
    cols = df.columns.tolist()
    if game_type == "SA Daily Lotto (5 Numbers)":
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) >= 5:
            rename_map = {numeric_cols[i]: f'N{i+1}' for i in range(5)}
            df = df.rename(columns=rename_map)
            return df[['N1', 'N2', 'N3', 'N4', 'N5']]
    elif game_type == "UK 49s (6 + Bonus)":
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if len(numeric_cols) >= 7:
            rename_map = {numeric_cols[i]: f'N{i+1}' for i in range(6)}
            rename_map[numeric_cols[6]] = 'Bonus'
            df = df.rename(columns=rename_map)
            return df[['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'Bonus']]
    return df

def get_row_numbers(row, game_type):
    """Returns a set of numbers for a given row."""
    if game_type == "SA Daily Lotto (5 Numbers)":
        return {row[f'N{k}'] for k in range(1, 6)}
    else:
        nums = {row[f'N{k}'] for k in range(1, 7)}
        if 'Bonus' in row:
            nums.add(row['Bonus'])
        return nums

def get_next_numbers_list(df, index, game_type):
    """Returns the next draw numbers as a list."""
    if index + 1 >= len(df): return []
    row = df.iloc[index + 1]
    if game_type == "SA Daily Lotto (5 Numbers)":
        return sorted([row[f'N{k}'] for k in range(1, 6)])
    else:
        # For splits, we look at the main 6 numbers usually
        return sorted([row[f'N{k}'] for k in range(1, 7)])

# --- Core Analysis Engines ---

def analyze_patterns(df, current_numbers, game_type):
    """Standard Frequency Analysis."""
    predictions = Counter()
    matches_found = 0
    match_threshold = 3
    
    # Pre-calculate set for speed
    current_set = set(current_numbers)
    
    for i in range(len(df) - 1):
        row_set = get_row_numbers(df.iloc[i], game_type)
        
        # Intersection Match
        if len(current_set.intersection(row_set)) >= match_threshold:
            matches_found += 1
            predictions.update(get_next_numbers_list(df, i, game_type))
            
        # Bonus Match (High Weight) - UK49 Only
        if game_type == "UK 49s (6 + Bonus)" and len(current_numbers) > 6:
            bonus = current_numbers[-1]
            if 'Bonus' in df.columns and df.iloc[i]['Bonus'] == bonus:
                predictions.update(get_next_numbers_list(df, i, game_type))
                predictions.update(get_next_numbers_list(df, i, game_type)) # Double weight
                
    return predictions

def analyze_splits(df, current_numbers, top_targets, game_type):
    """
    The Discovery Engine: Finds Split Pairs for Top Targets.
    Logic: If Target 'T' is predicted, find pairs (A, B) in next draw where |A-B|=T or A+B=T.
    """
    split_stats = {t: Counter() for t in top_targets}
    match_threshold = 3
    current_set = set(current_numbers)
    
    for i in range(len(df) - 1):
        row_set = get_row_numbers(df.iloc[i], game_type)
        
        # Check if this historical draw is similar to current (3+ matches or Bonus match)
        is_match = len(current_set.intersection(row_set)) >= match_threshold
        if game_type == "UK 49s (6 + Bonus)" and len(current_numbers) > 6:
             if 'Bonus' in df.columns and df.iloc[i]['Bonus'] == current_numbers[-1]:
                 is_match = True
        
        if is_match:
            # Look at the NEXT draw
            next_nums = get_next_numbers_list(df, i, game_type)
            next_pairs = list(combinations(next_nums, 2))
            
            for t in top_targets:
                for (a, b) in next_pairs:
                    # Check Difference Split
                    if abs(a - b) == t:
                        split_stats[t][(a, b, 'Diff')] += 1
                    # Check Sum Split
                    if a + b == t:
                        split_stats[t][(a, b, 'Sum')] += 1
                        
    return split_stats

# --- Main App Interface ---

if uploaded_file is not None:
    try:
        # Load & Clean
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        df_clean = clean_data(df, game_type)
        
        st.success(f"📂 Loaded {len(df_clean)} draws.")
        
        # Input
        st.subheader("Enter Last Draw Results")
        user_input = st.text_input("Numbers (Space separated, Bonus last for UK49):", "")
        
        if st.button("🚀 Run Split Analysis"):
            if user_input:
                current_nums = [int(x) for x in user_input.split()]
                
                # 1. Run Basic Analysis to get Targets
                with st.spinner("Finding most likely targets..."):
                    raw_predictions = analyze_patterns(df_clean, current_nums, game_type)
                
                if not raw_predictions:
                    st.warning("No historical patterns found. Try entering just the Bonus or 3 numbers.")
                else:
                    # Get Top 7 Targets (The numbers we expect to drop)
                    top_targets = [n for n, c in raw_predictions.most_common(7)]
                    
                    # 2. Run Split Analysis on these Targets
                    with st.spinner("Calculating Split Follow-ups..."):
                        split_data = analyze_splits(df_clean, current_nums, top_targets, game_type)
                    
                    # --- DISPLAY RESULTS ---
                    
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.subheader("🏆 Top Targets")
                        st.write("Most likely numbers to follow:")
                        for idx, (num, hits) in enumerate(raw_predictions.most_common(7)):
                            st.metric(f"Rank {idx+1}", num, f"{hits} Hits")
                            
                    with col2:
                        st.subheader("🔀 Split Strategy (The Follow-Ups)")
                        st.info("Instead of playing the Target directly, play these pairs that CREATE the target.")
                        
                        for target in top_targets:
                            splits = split_data[target].most_common(3)
                            if splits:
                                with st.expander(f"Target {target} - Best Splits", expanded=True):
                                    for (p1, p2, type_), count in splits:
                                        if type_ == 'Diff':
                                            st.write(f"**{p1} & {p2}** (Diff {target}) - {count} times")
                                        else:
                                            st.write(f"**{p1} & {p2}** (Sum {target}) - {count} times")
                            else:
                                st.write(f"Target {target}: No strong split pattern.")

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload file to start.")