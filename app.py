import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="WPL Auction Intelligence",
    page_icon="🏏",
    layout="wide",
)

st.title("🏏 WPL Auction Intelligence")
st.caption("Player scouting and auction analysis from one uploaded dataset.")
st.info(
    "Upload one CSV containing the player list and any available performance/auction attributes. "
    "The app validates the columns it finds; it does not invent missing statistics."
)

uploaded_file = st.file_uploader(
    "Upload your WPL dataset (CSV)",
    type=["csv"],
    accept_multiple_files=False,
)

REQUIRED_ID_CANDIDATES = [
    "player_name", "player", "playername", "name", "Player_Name", "Player Name"
]
ROLE_CANDIDATES = ["role", "auction_role", "player_role", "specialism", "playing_role"]
NATIONALITY_CANDIDATES = ["nationality", "country", "player_country"]
SEASON_CANDIDATES = ["season", "year", "season_year"]

PERFORMANCE_HINTS = [
    "matches_played", "runs_scored", "balls_faced", "fours", "sixes",
    "strike_rate", "wickets", "overs_bowled", "runs_conceded",
    "bowling_economy", "batting_position", "bowling_type",
    "bowling_arm_style", "bowling_specialism", "base_price_lakhs", "reserve_price", "capped_status", "auction_status", "previous_wpl_team", "previous_wpl_matches"
]


def norm_column(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def find_column(columns, candidates):
    lookup = {norm_column(c): c for c in columns}
    for candidate in candidates:
        found = lookup.get(norm_column(candidate))
        if found is not None:
            return found
    return None


def clean_text(series):
    return series.astype("string").str.strip().replace("", pd.NA)


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")



def auto_close_multiselect(container, label, options, state_key, help_text=None):
    """Keep multi-select choices, but remount the widget after a choice so its menu closes."""
    options = list(options)
    saved = st.session_state.get(state_key, [])
    saved = [value for value in saved if value in options]
    st.session_state[state_key] = saved
    signature = re.sub(r"[^a-zA-Z0-9_-]", "", str(abs(hash(tuple(map(str, saved))))))
    widget_key = f"{state_key}_widget_{signature}"

    def save_selection():
        st.session_state[state_key] = st.session_state.get(widget_key, [])

    return container.multiselect(
        label, options, default=saved, key=widget_key, on_change=save_selection, help=help_text
    )


def add_all_rounder_rating(frame):
    """Calculate the requested Impact Index only when all four inputs exist."""
    out = frame.copy()
    runs_col = find_column(out.columns, ["Runs_Scored", "Runs Scored", "Runs", "Total_Runs"])
    sr_col = find_column(out.columns, ["Strike_Rate", "Strike Rate", "Batting_Strike_Rate", "Batting Strike Rate", "SR"])
    wickets_col = find_column(out.columns, ["Wickets", "Total_Wickets", "Wickets_Taken", "Wickets Taken"])
    economy_col = find_column(out.columns, ["Bowling_Economy", "Bowling Economy", "Economy"])
    out["All_Rounder_Rating"] = pd.NA
    if all([runs_col, sr_col, wickets_col, economy_col]):
        runs = safe_numeric(out[runs_col])
        strike_rate = safe_numeric(out[sr_col])
        wickets = safe_numeric(out[wickets_col])
        economy = safe_numeric(out[economy_col])
        valid = runs.notna() & strike_rate.notna() & wickets.notna() & economy.notna()
        out.loc[valid, "All_Rounder_Rating"] = (
            runs[valid] * strike_rate[valid] / 100
            + wickets[valid] * 20
            - economy[valid] * 5
        ).round(2)
    return out


def normalized_player_name(series):
    return (
        clean_text(series)
        .str.lower()
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def role_key(value):
    """Normalize role labels such as 'WICKETKEEPER' and 'Wicket Keeper'."""
    return norm_column(value)


def available_columns(df, candidates):
    """Return matching real column names once, in the requested order."""
    lookup = {norm_column(c): c for c in df.columns}
    result = []
    seen = set()
    for candidate in candidates:
        key = norm_column(candidate)
        actual = lookup.get(key)
        if actual is not None and actual not in seen:
            result.append(actual)
            seen.add(actual)
    return result


if not uploaded_file:
    st.subheader("What you can do")
    c1, c2, c3 = st.columns(3)
    c1.markdown("**📊 Explore players**\n\nBrowse the available player records and statistics.")
    c2.markdown("**⚖️ Compare players**\n\nCompare available batting and bowling metrics.")
    c3.markdown("**🎯 Build a shortlist**\n\nFilter players by role, nationality, and available performance data.")
    st.stop()

# Reset any open player profile when the uploaded dataset changes.
_dataset_signature = (getattr(uploaded_file, "name", ""), getattr(uploaded_file, "size", None))
if st.session_state.get("loaded_dataset_signature") != _dataset_signature:
    st.session_state["active_profile_player_key"] = None
    st.session_state["player_table_version"] = 0
    st.session_state["loaded_dataset_signature"] = _dataset_signature

try:
    df = pd.read_csv(uploaded_file)
except Exception as exc:
    st.error(f"Could not read this CSV: {exc}")
    st.stop()

if df.empty:
    st.error("The uploaded CSV has no data rows.")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
name_col = find_column(df.columns, REQUIRED_ID_CANDIDATES)
role_col = find_column(df.columns, ROLE_CANDIDATES)
nationality_col = find_column(df.columns, NATIONALITY_CANDIDATES)
season_col = find_column(df.columns, SEASON_CANDIDATES)

st.success(f"Loaded {len(df):,} rows and {len(df.columns):,} columns.")

if name_col is None:
    st.error(
        "I couldn't identify a player-name column. Please include a column such as "
        "`Player_Name`, `Player Name`, `player_name`, or `name`."
    )
    st.write("Columns found:", list(df.columns))
    st.stop()

df[name_col] = clean_text(df[name_col])
blank_names = int(df[name_col].isna().sum())
df["_player_name_normalized"] = normalized_player_name(df[name_col])

# Identify likely performance columns without altering their original values.
performance_cols = [
    col for col in df.columns
    if norm_column(col) in {norm_column(x) for x in PERFORMANCE_HINTS}
]
numeric_candidate_cols = [
    col for col in df.columns
    if any(token in norm_column(col) for token in [
        "matches", "runs", "balls", "fours", "sixes", "strike", "wickets",
        "overs", "conceded", "economy", "average", "maidens", "catches",
        "stumpings", "points", "price", "baseprice"
    ])
]
for col in numeric_candidate_cols:
    df[col] = safe_numeric(df[col])

# Derive boundary percentage from fours and sixes, then display it instead of raw boundary counts.
runs_source_col = find_column(df.columns, ["Runs_Scored", "Runs Scored", "Runs", "Total_Runs"])
fours_source_col = find_column(df.columns, ["Fours", "4s", "Boundaries_Fours"])
sixes_source_col = find_column(df.columns, ["Sixes", "6s", "Boundaries_Sixes"])
if runs_source_col and fours_source_col and sixes_source_col:
    runs_values = safe_numeric(df[runs_source_col])
    boundary_runs = safe_numeric(df[fours_source_col]).fillna(0) * 4 + safe_numeric(df[sixes_source_col]).fillna(0) * 6
    df["Boundary_Percentage"] = (boundary_runs.div(runs_values.where(runs_values > 0)) * 100).round(2)

# Batting average = runs scored / times dismissed (not matches played).
runs_for_average_col = find_column(df.columns, ["Runs_Scored", "Runs Scored", "Runs", "Total_Runs"])
dismissals_col = find_column(df.columns, ["Dismissals", "Times_Dismissed", "Times Dismissed", "Outs", "Dismissed", "Innings_Outs"])
if runs_for_average_col and dismissals_col:
    dismissals = safe_numeric(df[dismissals_col])
    df["Batting_Average"] = (safe_numeric(df[runs_for_average_col]) / dismissals.where(dismissals > 0)).round(2)

st.header("Dataset validation")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Rows", f"{len(df):,}")
m2.metric("Columns", f"{len(df.columns) - 1:,}")
m3.metric("Unique named players", f"{df.loc[df[name_col].notna(), '_player_name_normalized'].nunique():,}")
m4.metric("Blank player names", f"{blank_names:,}")

issues = []
if blank_names:
    issues.append(f"{blank_names} row(s) have no player name.")
duplicate_mask = (
    df["_player_name_normalized"].notna()
    & df.duplicated(subset=["_player_name_normalized"], keep=False)
)
if duplicate_mask.any():
    issues.append(
        f"{int(duplicate_mask.sum())} row(s) share a player name with another row. "
        "This may be valid when the dataset contains multiple seasons."
    )
if role_col is None:
    issues.append("No recognizable role column found; role-based filters will be unavailable.")
if nationality_col is None:
    issues.append("No recognizable nationality/country column found; nationality filters will be unavailable.")
if not performance_cols and not numeric_candidate_cols:
    issues.append("No familiar performance-stat columns were detected. The app will still show the uploaded data.")

if issues:
    for issue in issues:
        st.warning(issue)
else:
    st.success("No basic validation issues detected in the player-name and recognized-column checks.")

with st.expander("Column inventory", expanded=False):
    inventory = pd.DataFrame({
        "Column": [c for c in df.columns if c != "_player_name_normalized"],
        "Non-empty values": [int(df[c].notna().sum()) for c in df.columns if c != "_player_name_normalized"],
        "Missing values": [int(df[c].isna().sum()) for c in df.columns if c != "_player_name_normalized"],
        "Data type": [str(df[c].dtype) for c in df.columns if c != "_player_name_normalized"],
    })
    st.dataframe(inventory, use_container_width=True, hide_index=True)

st.header("Player explorer")
st.write("Choose the filters below to display matching players and role-appropriate performance statistics.")
filtered = df.copy()
selected_roles = []

filter_cols = st.columns(3)
if role_col:
    role_values = sorted(clean_text(df[role_col]).dropna().unique().tolist(), key=str.casefold)
    selected_roles = auto_close_multiselect(filter_cols[0], "Role", role_values, "player_explorer_roles")
    if selected_roles:
        selected_role_keys = {role_key(role) for role in selected_roles}
        # If BATTER and WICKETKEEPER are the only selected roles, prioritize WKs.
        # If every role is selected (the default), keep all roles visible.
        all_role_keys = {role_key(role) for role in role_values}
        batter_wk_keys = {"batter", "wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"}
        if selected_role_keys != all_role_keys and selected_role_keys.issubset(batter_wk_keys) and "wicketkeeper" in selected_role_keys:
            actual_roles = clean_text(df[role_col]).map(role_key)
            filtered = filtered[actual_roles.isin({"wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"})]
        else:
            filtered = filtered[clean_text(filtered[role_col]).isin(selected_roles)]
    # An empty multiselect means "all roles", not "show zero rows".

# Role-specific scouting filters: batting position for batters, bowling category and style for bowlers.
position_col = find_column(df.columns, ["Batting_Position", "Batting Position", "Batting_Order", "Batting Order"])
bowling_type_col = find_column(df.columns, ["Bowling_Type", "Bowling Type"])
bowling_style_col = find_column(df.columns, ["Bowling_Arm_Style", "Bowling Arm Style", "Bowling_Specialism", "Bowling Specialism"])
selected_role_keys_for_subfilters = {role_key(r) for r in selected_roles}


def classify_bowling_type(value):
    v = norm_column(value)
    if any(x in v for x in ["spin", "orthodox", "legbreak", "offbreak", "googly", "chinaman", "wristspin", "finger spin"]):
        return "Spin"
    if any(x in v for x in ["pace", "fast", "medium", "seam"]):
        return "Pace"
    return None

if role_col and selected_role_keys_for_subfilters and selected_role_keys_for_subfilters.issubset({"batter"}):
    if position_col:
        positions = clean_text(df[position_col]).dropna().unique().tolist()

        positions = sorted(
            positions,
            key=lambda x: (
                0 if str(x).strip().casefold() == "opener"
                else 1 if str(x).strip().isdigit()
                else 2,
                int(str(x).strip()) if str(x).strip().isdigit()
                else str(x).casefold()
            )
        )

        selected_positions = auto_close_multiselect(
            st,
            "Batting position",
            positions,
            "player_explorer_batting_positions",
            help_text="Optional: choose batting positions. Leave empty to include all positions."
        )

        if selected_positions:
            filtered = filtered[
                clean_text(filtered[position_col]).isin(selected_positions)
            ]

        # Leaving batting position blank keeps all batting positions.

elif role_col and selected_role_keys_for_subfilters and selected_role_keys_for_subfilters.issubset({"bowler"}):
    # Broad category comes from Bowling_Type when available, otherwise infer it from the style field.
    broad_source_col = bowling_type_col or bowling_style_col
    if broad_source_col:
        raw_bowling_values = clean_text(df[broad_source_col]).dropna().unique().tolist()
        bowling_categories = sorted({classify_bowling_type(v) for v in raw_bowling_values if classify_bowling_type(v)}, key=str.casefold)
        if bowling_categories:
            selected_bowling_categories = auto_close_multiselect(
                st, "Bowling type", bowling_categories, "player_explorer_bowling_categories",
                help_text="Optional: choose Pace or Spin. Leave empty to include both."
            )
            if selected_bowling_categories:
                broad_mask = clean_text(filtered[broad_source_col]).map(classify_bowling_type).isin(selected_bowling_categories)
                filtered = filtered[broad_mask]

                # Optional subtype filter appears after Pace/Spin is selected.
                if bowling_style_col:
                    styles_in_category = clean_text(filtered[bowling_style_col]).dropna().unique().tolist()
                    styles_in_category = sorted(styles_in_category, key=str.casefold)
                    if styles_in_category:
                        selected_bowling_styles = auto_close_multiselect(
                            st, "Bowling arm / style", styles_in_category, "player_explorer_bowling_styles",
                            help_text="Optional: narrow the selection to styles such as Right Arm Fast, Left Arm Medium, Right Arm Offbreak, or Left Arm Orthodox. Leave empty to include all styles in the selected category."
                        )
                        if selected_bowling_styles:
                            filtered = filtered[clean_text(filtered[bowling_style_col]).isin(selected_bowling_styles)]
                # Leaving subtype blank keeps every style within the selected Pace/Spin category.

# Auction filters sourced from the auction list (when these columns exist in the uploaded CSV).
status_col = find_column(df.columns, ["Capped_Status", "C/U/A", "Auction_Status", "Capped Status"])
price_col = find_column(df.columns, ["Base_Price_Lakhs", "Reserve_Price", "Reserve Price Rs Lakh", "Reserve_Price_Lakhs"])
previous_team_col = find_column(df.columns, ["Previous_WPL_Team", "2026 WPL Team", "WPL_Team", "Previous Team"])
previous_matches_col = find_column(df.columns, ["Previous_WPL_Matches", "2026 WPL Matches", "WPL_Matches", "Previous WPL Matches"])

auction_filter_cols = st.columns(3)
if status_col:
    status_values = sorted(clean_text(df[status_col]).dropna().unique().tolist(), key=str.casefold)
    selected_statuses = auto_close_multiselect(
        auction_filter_cols[0], "Capped status", status_values, "player_explorer_capped_status",
        help_text="Optional. Leave empty to include Capped, Uncapped, and Associate players."
    )
    if selected_statuses:
        filtered = filtered[clean_text(filtered[status_col]).isin(selected_statuses)]
    # Optional filter: no selection means include all capped-status categories.

if price_col:
    price_values = safe_numeric(df[price_col]).dropna()
    if not price_values.empty:
        min_price = float(price_values.min())
        max_price = float(price_values.max())
        budget_options = sorted(price_values.unique().tolist())
        budget_labels = [f"₹{v:g} lakh" for v in budget_options]
        chosen_budget_label = auction_filter_cols[1].selectbox(
            "Maximum base-price budget",
            ["No budget limit"] + budget_labels,
            index=0,
            help="Optional: leave at No budget limit to include every base-price bracket."
        )
        if chosen_budget_label != "No budget limit":
            max_budget = budget_options[budget_labels.index(chosen_budget_label)]
            filtered = filtered[safe_numeric(filtered[price_col]).le(max_budget)]

if previous_team_col:
    team_values = sorted(clean_text(df[previous_team_col]).dropna().unique().tolist(), key=str.casefold)
    if df[previous_team_col].isna().any() or clean_text(df[previous_team_col]).eq("None").any():
        team_values = sorted(set(team_values) | {"None"}, key=str.casefold)
    selected_previous_teams = auto_close_multiselect(
        auction_filter_cols[2], "Previous WPL team", team_values, "player_explorer_previous_teams",
        help_text="Optional. Leave empty to include all players, or choose a franchise / None."
    )
    if selected_previous_teams:
        # Treat blank source values as "None" so the no-team option can match.
        team_series = clean_text(filtered[previous_team_col]).fillna("None")
        filtered = filtered[team_series.isin(selected_previous_teams)]
    # Optional filter: no selection means include players from every previous-team category.

# Prefer the country field copied from the auction list when available.
# Fall back to the performance dataset's Nationality/Country column.
auction_country_col = find_column(df.columns, ["Auction_Country", "Auction Country", "Country"])
country_source_col = auction_country_col or nationality_col
if country_source_col:
    raw_country_values = clean_text(df[country_source_col])

    def display_country(value):
        # Correct a common spelling variant in the auction CSV for a clean UI.
        if str(value).strip().casefold() in {"netherland", "the netherlands"}:
            return "Netherlands"
        if str(value).strip().casefold() in {"india", "indian"}:
            return "India"
        return str(value).strip()

    country_display_to_raw = {}
    for raw_value in raw_country_values.dropna().unique().tolist():
        country_display_to_raw.setdefault(display_country(raw_value), set()).add(raw_value)
    country_names = sorted(country_display_to_raw, key=str.casefold)
    india_names = {name for name in country_names if name.casefold() == "india"}
    overseas_values = [name for name in country_names if name not in india_names]

    nationality_group = auto_close_multiselect(
        filter_cols[1], "Nationality", ["Indian", "Overseas"], "player_explorer_nationality",
        help_text="Optional. Leave blank to include Indian and overseas players."
    )

    selected_overseas_countries = []
    if "Overseas" in nationality_group:
        selected_overseas_countries = auto_close_multiselect(
            filter_cols[1], "Overseas country", overseas_values, "player_explorer_overseas_countries",
            help_text="Country options are taken from the auction list. Leave blank to include every overseas country."
        )

    if nationality_group:
        include_country_names = set()
        if "Indian" in nationality_group:
            include_country_names.update(india_names)
        if "Overseas" in nationality_group:
            include_country_names.update(selected_overseas_countries or overseas_values)
        raw_names_to_include = set()
        for country_name in include_country_names:
            raw_names_to_include.update(country_display_to_raw.get(country_name, set()))
        filtered = filtered[clean_text(filtered[country_source_col]).isin(raw_names_to_include)]
    # If no parent group is selected, include every country.

# Verify the performance Role labels against the auction-list Auction_Role labels.
auction_role_col = find_column(df.columns, ["Auction_Role", "Auction Role"])
if role_col and auction_role_col:
    role_audit = df[[name_col, role_col, auction_role_col]].dropna(subset=[name_col]).copy()
    role_audit[role_col] = clean_text(role_audit[role_col])
    role_audit[auction_role_col] = clean_text(role_audit[auction_role_col])
    role_audit = role_audit.drop_duplicates(subset=[name_col])
    role_mismatches = role_audit[
        role_audit[role_col].map(role_key) != role_audit[auction_role_col].map(role_key)
    ]
    with st.expander("Auction role verification", expanded=False):
        if role_mismatches.empty:
            st.success("All player roles in this dataset match the Auction_Role field.")
        else:
            st.warning(f"Found {len(role_mismatches)} player(s) whose Role differs from Auction_Role.")
            st.dataframe(role_mismatches, use_container_width=True, hide_index=True)

# The season selector is intentionally removed from the explorer to avoid confusion.
# Player profiles show the available season-by-season performance instead.

# Calculate the all-rounder Impact Index where all required source metrics exist.
filtered = add_all_rounder_rating(filtered)

# Find common column variants using normalized names.
runs_col = find_column(filtered.columns, ["Runs_Scored", "Runs Scored", "Runs", "Total_Runs"])
strike_rate_col = find_column(filtered.columns, ["Strike_Rate", "Strike Rate", "Batting_Strike_Rate", "SR"])

# Optional team-controlled ranking for the selected role.
selected_role_keys = {role_key(role) for role in selected_roles}
sort_preference = None
if selected_role_keys and selected_role_keys.issubset({"batter", "wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"}):
    sort_preference = st.selectbox(
        "Rank batting players by",
        ["Highest runs", "Highest strike rate"],
        index=None,
        placeholder="Choose a ranking (optional)",
        key="batting_sort_preference",
    )
elif selected_role_keys == {"bowler"}:
    sort_preference = st.selectbox(
        "Rank bowlers by",
        ["Highest wickets", "Lowest economy"],
        index=None,
        placeholder="Choose a ranking (optional)",
        key="bowling_sort_preference",
    )
elif selected_role_keys and selected_role_keys.issubset({"allrounder", "allrounders"}):
    sort_preference = st.selectbox(
        "Rank all-rounders by",
        ["Highest Impact Index", "Highest runs", "Highest wickets", "Highest strike rate", "Lowest economy"],
        index=None,
        placeholder="Choose a ranking (optional)",
        help="Choose the main all-rounder metric. The complementary batting or bowling metric is used as a tiebreaker when available.",
        key="allrounder_sort_preference",
    )

runs_col = find_column(filtered.columns, ["Runs_Scored", "Runs Scored", "Runs", "Total_Runs"])
strike_rate_col = find_column(filtered.columns, ["Strike_Rate", "Strike Rate", "Batting_Strike_Rate", "SR"])
wickets_col = find_column(filtered.columns, ["Wickets", "Total_Wickets", "Wickets_Taken"])
economy_col = find_column(filtered.columns, ["Bowling_Economy", "Bowling Economy", "Economy"])
impact_col = "All_Rounder_Rating" if "All_Rounder_Rating" in filtered.columns else None

if sort_preference == "Highest Impact Index" and impact_col and safe_numeric(filtered[impact_col]).notna().any():
    sort_cols, ascending = [impact_col], [False]
elif sort_preference == "Highest runs" and runs_col:
    sort_cols, ascending = [runs_col], [False]
elif sort_preference == "Highest strike rate" and strike_rate_col:
    sort_cols, ascending = [strike_rate_col], [False]
elif sort_preference == "Highest wickets" and wickets_col:
    sort_cols, ascending = [wickets_col], [False]
elif sort_preference == "Lowest economy" and economy_col:
    sort_cols, ascending = [economy_col], [True]
else:
    sort_cols, ascending = [], []

if sort_cols:
    # Use the requested primary ranking; use the other relevant metric as a tiebreaker.
    if selected_role_keys and selected_role_keys.issubset({"batter", "wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"}):
        if sort_preference == "Highest runs" and strike_rate_col:
            sort_cols.append(strike_rate_col); ascending.append(False)
        elif sort_preference == "Highest strike rate" and runs_col:
            sort_cols.append(runs_col); ascending.append(False)
    elif selected_role_keys == {"bowler"}:
        if sort_preference == "Highest wickets" and economy_col:
            sort_cols.append(economy_col); ascending.append(True)
        elif sort_preference == "Lowest economy" and wickets_col:
            sort_cols.append(wickets_col); ascending.append(False)
    elif selected_role_keys and selected_role_keys.issubset({"allrounder", "allrounders"}):
        if sort_preference == "Highest runs" and strike_rate_col:
            sort_cols.append(strike_rate_col); ascending.append(False)
        elif sort_preference == "Highest strike rate" and runs_col:
            sort_cols.append(runs_col); ascending.append(False)
        elif sort_preference == "Highest wickets" and economy_col:
            sort_cols.append(economy_col); ascending.append(True)
        elif sort_preference == "Lowest economy" and wickets_col:
            sort_cols.append(wickets_col); ascending.append(False)
    filtered = filtered.sort_values(by=sort_cols, ascending=ascending, na_position="last", kind="stable")

# Dynamic role-specific display columns, in the requested scouting order.
# Boundary_Percentage is calculated from fours and sixes; the raw Fours/Sixes columns are hidden.
auction_number_candidates = [
    "Auction_List_No", "Auction List No", "Auction_List_Number", "Auction List Number",
    "Auction_Number", "Auction Number", "Auction_No", "Auction No", "List_No", "List No",
    "Serial_No", "Serial No", "S.No", "Sl No", "Sr No", "Auction_List_Serial_Number",
]
identity_candidates = auction_number_candidates + ["Season", "Player_Name", "Player Name", "player_name"]
base_price_candidates = ["Base_Price_Lakhs", "Base Price Lakhs", "Reserve_Price", "Reserve Price Rs Lakh", "Reserve_Price_Lakhs"]
role_candidates_for_display = ["Role", "Auction_Role", "Auction Role"]
bowling_metadata_candidates = [
    "Bowling_Type", "Bowling Type",
    "Bowling_Arm_Style", "Bowling Arm Style",
    "Bowling_Specialism", "Bowling Specialism",
]
shared_performance_candidates = [
    "Matches_Played", "Matches Played",
    "Runs_Scored", "Runs Scored", "Runs", "Total_Runs",
    "Balls_Faced", "Balls Faced",
    "Boundary_Percentage",
    "Batting_Average", "Batting Average",
    "Strike_Rate", "Strike Rate", "Batting_Strike_Rate", "SR",
    "Batting_Position", "Batting Position", "Batting_Order", "Batting Order",
]
bowling_performance_candidates = [
    "Wickets", "Total_Wickets", "Wickets_Taken",
    "Overs_Bowled", "Overs Bowled",
    "Runs_Conceded", "Runs Conceded",
    "Bowling_Economy", "Bowling Economy", "Economy",
]
auction_tail_candidates = [
    "Previous_WPL_Team", "Previous WPL Team", "2026 WPL Team", "WPL_Team",
    "Previous_WPL_Matches", "Previous WPL Matches", "2026 WPL Matches", "WPL_Matches",
]
status_last_candidates = ["Capped_Status", "Capped Status", "C/U/A", "Auction_Status"]

# Determine the effective roles after the WK-priority filter rule.
effective_role_keys = set()
if role_col and not filtered.empty:
    effective_role_keys = set(clean_text(filtered[role_col]).dropna().map(role_key).unique())

is_batter_view = bool(effective_role_keys) and effective_role_keys.issubset({"batter"})
is_wicketkeeper_view = bool(effective_role_keys) and effective_role_keys.issubset({"wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"})
is_bowler_view = bool(effective_role_keys) and effective_role_keys.issubset({"bowler"})
is_allrounder_view = bool(effective_role_keys) and effective_role_keys.issubset({"allrounder", "allrounders"})

if is_batter_view or is_wicketkeeper_view:
    ordered_candidates = identity_candidates + base_price_candidates + role_candidates_for_display + shared_performance_candidates + auction_tail_candidates + status_last_candidates
elif is_bowler_view:
    ordered_candidates = identity_candidates + base_price_candidates + role_candidates_for_display + bowling_metadata_candidates + ["Matches_Played", "Matches Played"] + bowling_performance_candidates + auction_tail_candidates + status_last_candidates
elif is_allrounder_view:
    # Requested order: identity, base price, role, bowling details, then batting and bowling stats; status last.
    ordered_candidates = identity_candidates + base_price_candidates + role_candidates_for_display + bowling_metadata_candidates + shared_performance_candidates + bowling_performance_candidates + auction_tail_candidates + status_last_candidates
else:
    # Mixed-role view keeps the same preferred order, then appends any other source columns.
    ordered_candidates = identity_candidates + base_price_candidates + role_candidates_for_display + bowling_metadata_candidates + shared_performance_candidates + bowling_performance_candidates + auction_tail_candidates + status_last_candidates

# Do not show raw fours/sixes: Boundary_Percentage summarizes boundary contribution.
ordered_candidates = [c for c in ordered_candidates if norm_column(c) not in {"fours", "sixes", "4s", "6s"}]
desired_columns = available_columns(filtered, ordered_candidates)
# Ensure actual detected name and role columns are included even if named unusually.
for required_col in [name_col, role_col]:
    if required_col and required_col in filtered.columns and required_col not in desired_columns:
        desired_columns.insert(1 if required_col == name_col else min(3, len(desired_columns)), required_col)
# IMPORTANT: do not append arbitrary source columns here. That was causing bowling
# statistics to appear in the batter view (and batting statistics in the bowler view).
# Only the allowlisted columns for the effective role are displayed; the source data
# remains intact so users can switch roles without losing any statistics.
# Always place capped status as the final visible column, when present.
status_display_col = find_column(filtered.columns, status_last_candidates)
if status_display_col and status_display_col in desired_columns:
    desired_columns = [c for c in desired_columns if c != status_display_col] + [status_display_col]
# Deduplicate defensively: Streamlit/PyArrow rejects repeated column labels.
display_cols = []
_seen_display_cols = set()
for col in desired_columns:
    if col in filtered.columns and col != "_player_name_normalized" and col not in _seen_display_cols:
        display_cols.append(col)
        _seen_display_cols.add(col)

# Single shortlist implementation follows below.

# ============================================================
# UNIQUE PLAYER SHORTLIST — KEEP ALL SEASON RECORDS FOR POPUP
# ============================================================

auction_number_col = find_column(
    filtered.columns, auction_number_candidates
)

player_list_cols = []
for col in [auction_number_col, name_col, price_col, role_col]:
    if col and col in filtered.columns and col not in player_list_cols:
        player_list_cols.append(col)

list_labels = {}

if auction_number_col:
    list_labels[auction_number_col] = "Auction List No."

list_labels[name_col] = "Player Name"

if price_col:
    list_labels[price_col] = "Base Price (Lakhs)"

if role_col:
    list_labels[role_col] = "Role"


st.divider()

# Keep every season record in `filtered`.
# Create a separate shortlist containing only one row per player.
player_list_source = filtered[
    player_list_cols + ["_player_name_normalized"]
].copy()

# Remove blank player names from the shortlist.
player_list_source = player_list_source[
    player_list_source["_player_name_normalized"].notna()
    & player_list_source["_player_name_normalized"].ne("")
].copy()

# One entry per normalized player name.
# This does NOT remove season records from the original dataset.
player_list_source = player_list_source.drop_duplicates(
    subset=["_player_name_normalized"],
    keep="first"
).reset_index(drop=True)

player_list = player_list_source[player_list_cols].copy()
player_list = player_list.rename(columns=list_labels)

if "Base Price (Lakhs)" in player_list.columns:
    player_list["Base Price (Lakhs)"] = pd.to_numeric(
        player_list["Base Price (Lakhs)"],
        errors="coerce"
    )

st.caption(
    f"Showing {len(player_list):,} unique available players. "
    "Click a player's row in the table to open their detailed profile."
)

# Clicking a row in the table opens the profile. A new widget key clears selection.
if "player_table_version" not in st.session_state:
    st.session_state.player_table_version = 0
if "active_profile_player_key" not in st.session_state:
    st.session_state.active_profile_player_key = None

player_table_event = st.dataframe(
    player_list,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key=f"player_shortlist_{st.session_state.player_table_version}",
)

# ============================================================
# PLAYER COMPARISON — independent of the main explorer filters
# ============================================================
st.divider()
st.header("⚖️ Player comparison")
st.caption("Compare players side by side using batting or bowling metrics appropriate to their role.")
st.caption("All-rounder Impact Index = (Runs × Strike Rate / 100) + (Wickets × 20) − (Economy × 5). It is calculated only when all four inputs are available.")

compare_role_col, compare_season_col = st.columns(2)
comparison_source = df.copy()
comparison_roles = sorted(clean_text(df[role_col]).dropna().unique().tolist(), key=str.casefold) if role_col else []
comparison_role = compare_role_col.selectbox(
    "Comparison role",
    options=comparison_roles,
    index=0 if comparison_roles else None,
    placeholder="Choose a role",
    key="comparison_role_select",
) if comparison_roles else None

comparison_season_col = find_column(df.columns, SEASON_CANDIDATES)
comparison_season = None
if comparison_season_col:
    seasons = clean_text(df[comparison_season_col]).dropna().unique().tolist()
    seasons = sorted(seasons, key=str.casefold)
    if seasons:
        # Latest-looking year is the default when the season values are year labels.
        year_like = [v for v in seasons if str(v).strip().isdigit()]
        default_season = max(year_like, key=int) if year_like else seasons[-1]
        comparison_season = compare_season_col.selectbox(
            "Season to compare",
            options=seasons,
            index=seasons.index(default_season),
            key="comparison_season_select",
        )

comparison_rows = add_all_rounder_rating(comparison_source)
if role_col and comparison_role:
    comparison_rows = comparison_rows[clean_text(comparison_rows[role_col]) == comparison_role]
if comparison_season_col and comparison_season is not None:
    comparison_rows = comparison_rows[clean_text(comparison_rows[comparison_season_col]) == comparison_season]

comparison_name_col = name_col
comparison_rows = comparison_rows[comparison_rows[comparison_name_col].notna()].copy()
comparison_rows = comparison_rows.drop_duplicates(subset=["_player_name_normalized"], keep="last")
player_options = sorted(comparison_rows[comparison_name_col].dropna().astype(str).unique().tolist(), key=str.casefold)
selected_compare_players = st.multiselect(
    "Select players to compare (choose 2 or more)",
    options=player_options,
    default=[],
    max_selections=6,
    key="comparison_players_select",
)

if selected_compare_players:
    role_normalized = role_key(comparison_role or "")
    batting_compare_candidates = [
        "Matches_Played", "Matches Played", "Runs_Scored", "Runs Scored", "Runs", "Total_Runs",
        "Balls_Faced", "Balls Faced", "Batting_Average", "Batting Average", "Strike_Rate", "Strike Rate",
        "Batting_Strike_Rate", "SR", "Highest_Score", "Highest Score", "Fours", "Sixes", "Boundary_Percentage",
    ]
    bowling_compare_candidates = [
        "Matches_Played", "Matches Played", "Wickets", "Total_Wickets", "Wickets_Taken",
        "Overs_Bowled", "Overs Bowled", "Runs_Conceded", "Runs Conceded", "Bowling_Economy", "Bowling Economy", "Economy",
    ]
    batter_roles = {"batter", "wicketkeeper", "wicketkeeperbatter", "wicketkeeperbatsman"}
    bowler_roles = {"bowler"}
    allrounder_roles = {"allrounder", "allrounders"}
    if role_normalized in batter_roles:
        compare_candidates = batting_compare_candidates
    elif role_normalized in bowler_roles:
        compare_candidates = bowling_compare_candidates
    elif role_normalized in allrounder_roles:
        compare_candidates = batting_compare_candidates + bowling_compare_candidates + ["All_Rounder_Rating"]
    else:
        compare_candidates = batting_compare_candidates + bowling_compare_candidates
    comparison_metric_cols = available_columns(comparison_rows, compare_candidates)
    compare_view = comparison_rows[comparison_rows[comparison_name_col].astype(str).isin(selected_compare_players)].copy()
    # Show batting hand (RHB/LHB) instead of auction role in the comparison table.
    batting_hand_candidates = [
        "Batting_Hand", "Batting Hand", "Batting_Style", "Batting Style",
        "Batting", "Batting_Type", "Batting Type", "Batting_Handedness",
        "Batting Handedness", "Bats"
    ]
    batting_hand_col = find_column(comparison_rows.columns, batting_hand_candidates)

    def to_batting_hand(value):
        if pd.isna(value) or not str(value).strip():
            return "Not available"
        text = str(value).strip().upper()
        compact = re.sub(r"[^A-Z]", "", text)
        if compact in {"RHB", "RIGHTHANDBAT", "RIGHTHANDED", "RIGHTHAND"} or "RIGHTHAND" in compact or compact.startswith("RHB"):
            return "RHB"
        if compact in {"LHB", "LEFTHANDBAT", "LEFTHANDED", "LEFTHAND"} or "LEFTHAND" in compact or compact.startswith("LHB"):
            return "LHB"
        return str(value).strip()

    compare_view["Batting Hand"] = (
        compare_view[batting_hand_col].map(to_batting_hand)
        if batting_hand_col and batting_hand_col in compare_view.columns
        else "Not available"
    )
    compare_display_cols = [comparison_name_col, "Batting Hand"] + comparison_metric_cols
    compare_display_cols = list(dict.fromkeys(c for c in compare_display_cols if c in compare_view.columns))
    compare_view = compare_view[compare_display_cols].rename(columns={comparison_name_col: "Player"})
    if len(selected_compare_players) < 2:
        st.info("Choose at least two players to compare their statistics side by side.")
    elif not comparison_metric_cols:
        st.warning("No role-appropriate performance columns were found in this CSV.")
    else:
        st.dataframe(compare_view, use_container_width=True, hide_index=True)
else:
    st.info("Choose at least two players above to display the comparison table.")



selected_row_positions = player_table_event.selection.rows
if selected_row_positions:
    selected_position = selected_row_positions[0]
    if 0 <= selected_position < len(player_list_source):
        st.session_state.active_profile_player_key = player_list_source.iloc[
            selected_position
        ]["_player_name_normalized"]

selected_player_key = st.session_state.active_profile_player_key
if selected_player_key is not None:
    # Use the full dataset to identify the player; performance rows are gathered inside the dialog.
    matching_selected_rows = df[
        df["_player_name_normalized"] == selected_player_key
    ].copy()
    if not matching_selected_rows.empty:
        selected_player_row = matching_selected_rows.iloc[0]
        selected_player_name = str(selected_player_row[name_col])

        @st.dialog(
            f"Player profile: {selected_player_name}",
            width="large",
            dismissible=False,
        )
        def show_player_profile():
            _, close_col = st.columns([12, 1])
            with close_col:
                if st.button("×", key="close_player_profile", help="Close player profile"):
                    st.session_state.active_profile_player_key = None
                    st.session_state.player_table_version += 1
                    st.rerun()

            # Use the full dataset so all available seasons are included.
            player_records = df[
                df["_player_name_normalized"]
                == selected_player_key
            ].copy()

            if player_records.empty:
                st.warning("No performance records were found for this player.")
                return

            # Remove exact duplicate records only.
            # Distinct 2024 and 2025 records are retained.
            player_records = player_records.drop_duplicates()

            profile_role_keys = (
                set(
                    clean_text(player_records[role_col])
                    .dropna()
                    .map(role_key)
                    .unique()
                )
                if role_col
                else set()
            )

            profile_is_batter = bool(profile_role_keys) and (
                profile_role_keys.issubset({"batter"})
            )

            profile_is_wk = bool(profile_role_keys) and (
                profile_role_keys.issubset({
                    "wicketkeeper",
                    "wicketkeeperbatter",
                    "wicketkeeperbatsman"
                })
            )

            profile_is_bowler = bool(profile_role_keys) and (
                profile_role_keys.issubset({"bowler"})
            )

            profile_is_allrounder = bool(profile_role_keys) and (
                profile_role_keys.issubset({
                    "allrounder",
                    "allrounders"
                })
            )

            # Display player identity once.
            header_cols = available_columns(
                player_records,
                auction_number_candidates
                + [name_col]
                + base_price_candidates
                + role_candidates_for_display
                + auction_tail_candidates
                + status_last_candidates
            )

            if header_cols:
                header_row = player_records.iloc[0]
                left, right = st.columns(2)

                batting_hand_candidates = [
                    "Batting_Hand", "Batting Hand", "Batting_Style", "Batting Style",
                    "Batting", "Batting_Type", "Batting Type", "Batting_Handedness",
                    "Batting Handedness", "Bats"
                ]
                batting_hand_col = find_column(player_records.columns, batting_hand_candidates)

                def profile_batting_hand(value):
                    if pd.isna(value) or not str(value).strip():
                        return "Not available"
                    raw = str(value).strip().upper()
                    compact = re.sub(r"[^A-Z]", "", raw)
                    if "RIGHTHAND" in compact or compact.startswith("RHB") or compact == "RIGHT":
                        return "RHB"
                    if "LEFTHAND" in compact or compact.startswith("LHB") or compact == "LEFT":
                        return "LHB"
                    return str(value).strip()

                for idx, col in enumerate(header_cols):
                    value = header_row[col]
                    if norm_column(col) == norm_column(name_col):
                        label = "Batting Hand"
                        value = profile_batting_hand(header_row[batting_hand_col]) if batting_hand_col else "Not available"
                    else:
                        if pd.isna(value):
                            value = "Not available"
                        if norm_column(col) in {norm_column(x) for x in auction_number_candidates}:
                            label = "Auction List No."
                        elif norm_column(col) in {norm_column(x) for x in base_price_candidates}:
                            label = "Base Price (Lakhs)"
                        else:
                            label = col.replace("_", " ")

                    (left if idx % 2 == 0 else right).markdown(
                        f"**{label}:** {value}"
                    )

            # Show stable player characteristics once, before season-by-season stats.
            if profile_is_bowler or profile_is_allrounder:
                st.subheader("Bowling profile")
                metadata_cols = available_columns(player_records, bowling_metadata_candidates)
                if metadata_cols:
                    meta = player_records.iloc[0]
                    meta_cols = st.columns(len(metadata_cols))
                    for i, col in enumerate(metadata_cols):
                        value = meta[col]
                        if pd.isna(value) or str(value).strip() == "":
                            value = "Not available"
                        meta_cols[i].markdown(f"**{col.replace('_', ' ')}**")
                        meta_cols[i].write(str(value))
                else:
                    st.caption("Bowling type, arm style, and specialism are not available in this dataset.")

            # Batting average: never estimate using matches played.
            if profile_is_batter or profile_is_wk or profile_is_allrounder:
                st.markdown("#### Batting average")
                if (
                    runs_for_average_col
                    and dismissals_col
                    and runs_for_average_col in player_records.columns
                    and dismissals_col in player_records.columns
                ):
                    total_runs = safe_numeric(player_records[runs_for_average_col]).fillna(0).sum()
                    total_outs = safe_numeric(player_records[dismissals_col]).fillna(0).sum()
                    if total_outs > 0:
                        st.metric("Batting Average", f"{total_runs / total_outs:.2f}")
                    else:
                        st.metric("Batting Average", "Not available")
                        st.caption("Not enough batting data to calculate average.")
                else:
                    st.metric("Batting Average", "Not available")
                    st.caption("Not enough batting data to calculate average.")

            batting_candidates = [
                "Matches_Played", "Matches Played", "Innings_Batted", "Innings Batted",
                "Runs_Scored", "Runs Scored", "Runs", "Total_Runs", "Balls_Faced", "Balls Faced",
                "Fours", "Sixes", "Boundary_Percentage", "Strike_Rate", "Strike Rate",
                "Batting_Strike_Rate", "Batting_Position", "Batting Position", "Batting_Order", "Batting Order"
            ]
            bowling_candidates = [
                "Matches_Played", "Matches Played", "Innings_Bowled", "Innings Bowled",
                "Wickets", "Total_Wickets", "Wickets_Taken", "Overs_Bowled", "Overs Bowled",
                "Runs_Conceded", "Runs Conceded", "Bowling_Economy", "Bowling Economy", "Economy",
                "Maidens", "Dot_Balls", "Dot Balls"
            ]
            batting_cols = [c for c in available_columns(player_records, batting_candidates)
                            if norm_column(c) not in {"fours", "sixes", "4s", "6s"}]
            bowling_cols = available_columns(player_records, bowling_candidates)

            # Keep only role-relevant performance tables; characteristics are shown above.
            if season_col and season_col in player_records.columns:
                player_records["_profile_season_label"] = clean_text(player_records[season_col]).fillna("Season not specified").astype(str)
                season_labels = player_records["_profile_season_label"].drop_duplicates().tolist()
                def season_sort_key(value):
                    try:
                        return (0, float(value))
                    except (ValueError, TypeError):
                        return (1, str(value).casefold())
                for season_label in sorted(season_labels, key=season_sort_key):
                    st.markdown(f"#### {season_label}")
                    season_rows = player_records[player_records["_profile_season_label"] == season_label].copy()
                    if profile_is_batter or profile_is_wk:
                        if batting_cols:
                            st.markdown("**Batting performance**")
                            st.dataframe(season_rows[batting_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                        else:
                            st.info("No batting performance columns are available for this season.")
                    elif profile_is_bowler:
                        if bowling_cols:
                            st.markdown("**Bowling performance**")
                            st.dataframe(season_rows[bowling_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                        else:
                            st.info("No bowling performance columns are available for this season.")
                    elif profile_is_allrounder:
                        left, right = st.columns(2)
                        with left:
                            st.markdown("**Batting performance**")
                            if batting_cols:
                                st.dataframe(season_rows[batting_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                            else:
                                st.caption("No batting performance data available.")
                        with right:
                            st.markdown("**Bowling performance**")
                            if bowling_cols:
                                st.dataframe(season_rows[bowling_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                            else:
                                st.caption("No bowling performance data available.")
                    else:
                        st.info("Role not recognized, so split performance tables cannot be selected safely.")
            else:
                st.caption("No season/year column was found. Showing available performance without year grouping.")
                if profile_is_allrounder:
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**Batting performance**")
                        if batting_cols: st.dataframe(player_records[batting_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                    with right:
                        st.markdown("**Bowling performance**")
                        if bowling_cols: st.dataframe(player_records[bowling_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                elif profile_is_bowler:
                    if bowling_cols: st.dataframe(player_records[bowling_cols].reset_index(drop=True), use_container_width=True, hide_index=True)
                elif batting_cols:
                    st.dataframe(player_records[batting_cols].reset_index(drop=True), use_container_width=True, hide_index=True)

        show_player_profile()
