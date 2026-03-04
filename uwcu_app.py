import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ──────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gym Performance Dashboard",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────
# CSS STYLING (Claude-assisted)
# This section controls visual presentation only — colors,
# fonts, spacing. No analytical logic lives here.
# ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Base font for the app */
    .stApp { font-family: 'DM Sans', sans-serif; }
    
    /* Dark sidebar with readable text */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: #e2e8f0 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label {
        font-weight: 700;
        text-transform: uppercase;
        font-size: 0.75rem;
        color: #f1f5f9 !important;
        letter-spacing: 0.05em;
    }
    /* Make sidebar dropdown text dark so it's readable on white input bg */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] span {
        color: #1e293b !important;
    }
    section[data-testid="stSidebar"] .stCaption p {
        color: #94a3b8 !important;
    }

    /* Style the metric cards */
    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.8rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #475569 !important;
    }
    /* Prevent metric labels from truncating */
    [data-testid="stMetricLabel"] > div {
        overflow: visible !important;
        white-space: normal !important;
        text-overflow: unset !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #0f172a !important;
    }

    /* Section dividers — high contrast with blue accent */
    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 3px solid #2563eb;
    }

    /* Dataframe table header styling */
    .stDataFrame [data-testid="glideDataEditor"] th {
        font-weight: 700 !important;
    }

    /* Status badge styles for tables */
    .status-on-track { color: #15803d; font-weight: 700; }
    .status-at-risk { color: #c2410c; font-weight: 700; }
    .status-behind { color: #dc2626; font-weight: 700; }
    .pace-positive { color: #15803d; font-weight: 600; }
    .pace-negative { color: #dc2626; font-weight: 600; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────────────────
# @st.cache_data tells Streamlit to only reload the file
# when it changes — not on every interaction. This is how
# the dashboard stays fast when users click filters.
@st.cache_data
def load_data():
    df = pd.read_excel("Dashboard Exercise Data.xlsx")

    # Clean up column names (strip whitespace, lowercase)
    df.columns = df.columns.str.strip().str.lower()

    # Parse dates
    df["start_dt"] = pd.to_datetime(df["start_dt"])
    df["year"] = df["start_dt"].dt.year

    # "day_of_summer" = how many days since June 1 of that year
    # This lets us compare 2017 and 2018 on the same x-axis
    # Example: June 1 = day 0, June 2 = day 1, Aug 31 = day 91
    df["day_of_summer"] = df.apply(
        lambda row: (row["start_dt"] - pd.Timestamp(f"{row['year']}-06-01")).days,
        axis=1
    )

    # Readable gym label instead of just a number
    df["store_label"] = "Gym " + df["store_nbr"].astype(str)

    return df


df = load_data()


# ──────────────────────────────────────────────────────────
# KEY DATES & CONSTANTS
# All dates are derived from the data itself — nothing is
# hardcoded. When new rows are appended to the Excel file,
# these values update automatically.
# ──────────────────────────────────────────────────────────
CURRENT_DATE = df["start_dt"].max()             # Latest date in the data
CURRENT_YEAR = CURRENT_DATE.year                # 2018
PRIOR_YEAR = CURRENT_YEAR - 1                   # 2017

SUMMER_START = pd.Timestamp(f"{CURRENT_YEAR}-06-01")
SUMMER_END = pd.Timestamp(f"{CURRENT_YEAR}-08-31")
TOTAL_SUMMER_DAYS = (SUMMER_END - SUMMER_START).days + 1  # 92 days
ELAPSED_DAYS = (CURRENT_DATE - SUMMER_START).days + 1     # How far into summer we are

GOAL_MULTIPLIER = 1.10  # 10% growth target


# ──────────────────────────────────────────────────────────
# FILTER TO NEW MEMBERS ONLY
# The exercise says "this analysis is focused on New Members"
# ──────────────────────────────────────────────────────────
new_df = df[df["cust_type"] == "NEW"].copy()

# Split into current year and prior year
curr_all = new_df[new_df["year"] == CURRENT_YEAR]
prior_all = new_df[new_df["year"] == PRIOR_YEAR]

# Prior year "same window" — only dates through the equivalent
# calendar day. This is crucial for fair pace comparison.
# If current data goes through Aug 14 2018, we compare against
# 2017 data through Aug 14 2017 (not all of 2017 summer).
prior_window_end = pd.Timestamp(
    f"{PRIOR_YEAR}-{CURRENT_DATE.month:02d}-{CURRENT_DATE.day:02d}"
)
prior_same_window = prior_all[prior_all["start_dt"] <= prior_window_end]


# ──────────────────────────────────────────────────────────
# PROJECTION FUNCTION
#
# This is the core analytical logic. Instead of a naive
# "linear extrapolation" (current / days_elapsed * total_days),
# we use 2017's seasonality as a scaling factor.
#
# WHY: Gym signups aren't evenly spread across summer.
# There are peaks (start of June, early August) and valleys.
# If 2017 shows that 50.5% of signups happen by Aug 14,
# we can project: 2018_total = 2018_current / 0.505
#
# This is the same concept as "pace" in sales forecasting.
# In SQL terms, it would be:
#   projected = current_count / (prior_same_window / prior_full)
# ──────────────────────────────────────────────────────────
def project_total(current_count, prior_full_count, prior_window_count):
    """
    Project end-of-summer total using prior year seasonality.

    Example:
        2017 full summer = 100 members
        2017 through Aug 14 = 50 members  (50% of summer done by this date)
        2018 through Aug 14 = 60 members
        Projected 2018 total = 60 / 0.50 = 120 members
    """
    # Edge case: no prior year data (new gym, etc.)
    if prior_window_count == 0 or prior_full_count == 0:
        # Fall back to simple linear extrapolation
        if ELAPSED_DAYS > 0:
            return int(current_count * TOTAL_SUMMER_DAYS / ELAPSED_DAYS)
        return current_count

    # What percentage of the full summer had occurred by this date in the prior year?
    seasonality_factor = prior_window_count / prior_full_count

    # Project current year total
    return int(current_count / seasonality_factor)


def get_status(projected, goal):
    """Classify performance status based on projected vs goal."""
    if goal == 0:
        return "N/A"
    pct = projected / goal
    if pct >= 1.0:
        return "On Track"
    elif pct >= 0.90:
        return "At Risk"
    else:
        return "Behind"


def color_status(status):
    """Return colored HTML for status text."""
    if status == "On Track":
        return '<span style="color:#15803d;font-weight:700;">✅ On Track</span>'
    elif status == "At Risk":
        return '<span style="color:#c2410c;font-weight:700;">⚠️ At Risk</span>'
    elif status == "Behind":
        return '<span style="color:#dc2626;font-weight:700;">🔴 Behind</span>'
    return status


def color_pace(pace_value):
    """Return colored HTML for pace text."""
    if pace_value > 0:
        return f'<span style="color:#15803d;font-weight:600;">▲ {abs(pace_value):.1f}%</span>'
    elif pace_value < 0:
        return f'<span style="color:#dc2626;font-weight:600;">▼ {abs(pace_value):.1f}%</span>'
    else:
        return f'<span style="color:#64748b;">0.0%</span>'


# ──────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# These cascade: selecting a region limits which districts
# are available, and selecting a district limits which gyms
# are shown. This is the same pattern as a hierarchy filter
# in QuickSight or Tableau.
# ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏋️ Gym Dashboard")
    st.markdown(f"**Data through:** {CURRENT_DATE.strftime('%B %d, %Y')}")
    st.markdown(f"**Summer progress:** Day {ELAPSED_DAYS} of {TOTAL_SUMMER_DAYS}")
    st.markdown("---")

    # Region filter
    all_regions = sorted(new_df["region"].unique())
    sel_region = st.selectbox("Region", ["All"] + all_regions)

    # District filter — options depend on selected region
    if sel_region != "All":
        avail_districts = sorted(new_df[new_df["region"] == sel_region]["district"].unique())
    else:
        avail_districts = sorted(new_df["district"].unique())
    sel_district = st.selectbox("District", ["All"] + avail_districts)

    # Gym filter — options depend on selected district/region
    if sel_district != "All":
        avail_gyms = sorted(new_df[new_df["district"] == sel_district]["store_label"].unique())
    elif sel_region != "All":
        avail_gyms = sorted(new_df[new_df["region"] == sel_region]["store_label"].unique())
    else:
        avail_gyms = sorted(new_df["store_label"].unique())
    sel_gym = st.selectbox("Gym", ["All"] + avail_gyms)

    st.markdown("---")
    st.caption("Dashboard refreshes automatically when new data is appended to the source file.")


# ──────────────────────────────────────────────────────────
# APPLY FILTERS
# Same logic as a WHERE clause in SQL:
#   WHERE region = 'EAST' AND district = 'A' AND store = 262
# ──────────────────────────────────────────────────────────
def apply_filters(data):
    filtered = data.copy()
    if sel_region != "All":
        filtered = filtered[filtered["region"] == sel_region]
    if sel_district != "All":
        filtered = filtered[filtered["district"] == sel_district]
    if sel_gym != "All":
        filtered = filtered[filtered["store_label"] == sel_gym]
    return filtered


f_curr = apply_filters(curr_all)
f_prior = apply_filters(prior_all)
f_prior_window = apply_filters(prior_same_window)


# ──────────────────────────────────────────────────────────
# BUILD FILTER LABEL (for display)
# ──────────────────────────────────────────────────────────
if sel_gym != "All":
    filter_label = sel_gym
elif sel_district != "All":
    filter_label = f"District {sel_district}"
elif sel_region != "All":
    filter_label = f"{sel_region} Region"
else:
    filter_label = "Company-Wide"


# ──────────────────────────────────────────────────────────
# PLOTLY CHART DEFAULTS
# Consistent styling for all charts — darker gridlines
# for readability on light background
# ──────────────────────────────────────────────────────────
GRID_COLOR = "#d1d5db"  # Darker grid so it's visible on white

CHART_LAYOUT = dict(
    font=dict(family="DM Sans, sans-serif", size=12, color="#1e293b"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=60, b=40),
    hoverlabel=dict(bgcolor="#1e293b", font_color="#f8fafc", font_size=12),
)


# ══════════════════════════════════════════════════════════
# TAB 1: MEMBER ACQUISITION
# ══════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["📊  Member Acquisition", "🎯  Personal Training"])

with tab1:
    st.markdown(f"### New Member Acquisition — {filter_label}")

    # ── Calculate top-level KPIs ──
    actual = len(f_curr)                                  # How many new members so far in 2018
    prior_full = len(f_prior)                             # Total new members in 2017 (full summer)
    prior_window = len(f_prior_window)                    # 2017 members through same date
    goal = int(prior_full * GOAL_MULTIPLIER)              # 2017 total + 10%
    projected = project_total(actual, prior_full, prior_window)
    progress_pct = (actual / goal * 100) if goal > 0 else 0
    status = get_status(projected, goal)

    # Pace: how 2018 compares to 2017 through the same date
    # Positive = ahead of last year, Negative = behind
    if prior_window > 0:
        pace_vs_prior = (actual - prior_window) / prior_window * 100
    else:
        pace_vs_prior = 0

    # ── Display KPIs ──
    # Using st.metric for most, but custom HTML for Projected Total
    # and Pace so we can control the colors properly.
    # Streamlit's delta auto-colors green=up red=down, but "At Risk"
    # should be orange, not green.
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Current New Members", f"{actual:,}",
              help="New members acquired so far this summer")
    k2.metric("Summer Goal", f"{goal:,}",
              help=f"{PRIOR_YEAR} total ({prior_full:,}) + 10%")

    # Projected Total — custom HTML so status color is correct
    with k3:
        status_color = {"On Track": "#15803d", "At Risk": "#c2410c", "Behind": "#dc2626"}.get(status, "#64748b")
        st.markdown(
            f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.03em;color:#475569;">Projected Total</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:#0f172a;">{projected:,}</div>
                <div style="font-size:0.82rem;font-weight:700;color:{status_color};">{'✅' if status=='On Track' else '⚠️' if status=='At Risk' else '🔴'} {status}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    k4.metric("Progress to Goal", f"{progress_pct:.1f}%",
              help=f"{actual:,} of {goal:,}")

    # Pace vs Prior — custom HTML so color matches direction
    with k5:
        pace_color = "#15803d" if pace_vs_prior > 0 else "#dc2626" if pace_vs_prior < 0 else "#64748b"
        pace_arrow = "▲" if pace_vs_prior > 0 else "▼"
        st.markdown(
            f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.03em;color:#475569;">Pace vs {PRIOR_YEAR}</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:{pace_color};">{pace_arrow} {abs(pace_vs_prior):.1f}%</div>
                <div style="font-size:0.82rem;color:{pace_color};font-weight:600;">{actual - prior_window:+,} members</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Cumulative Trend Chart ──
    st.markdown(
        '<div class="section-header">Cumulative New Members — Daily Trend</div>',
        unsafe_allow_html=True
    )

    # Group by day_of_summer and get cumulative sum
    # This is like: SELECT day_of_summer, COUNT(*) OVER (ORDER BY day_of_summer) FROM ...
    curr_daily = (
        f_curr.groupby("day_of_summer")
        .size()
        .reset_index(name="daily_count")
        .sort_values("day_of_summer")
    )
    curr_daily["cumulative"] = curr_daily["daily_count"].cumsum()

    prior_daily = (
        f_prior.groupby("day_of_summer")
        .size()
        .reset_index(name="daily_count")
        .sort_values("day_of_summer")
    )
    prior_daily["cumulative"] = prior_daily["daily_count"].cumsum()

    # Date labels for hover tooltips
    curr_daily["label"] = curr_daily["day_of_summer"].apply(
        lambda d: (SUMMER_START + pd.Timedelta(days=d)).strftime("%b %d")
    )
    prior_daily["label"] = prior_daily["day_of_summer"].apply(
        lambda d: (pd.Timestamp(f"{PRIOR_YEAR}-06-01") + pd.Timedelta(days=d)).strftime("%b %d")
    )

    fig_trend = go.Figure()

    # 2017 line — darker gray so it's visible on white background
    fig_trend.add_trace(go.Scatter(
        x=prior_daily["day_of_summer"],
        y=prior_daily["cumulative"],
        name=f"{PRIOR_YEAR} Actual",
        line=dict(color="#6b7280", width=2, dash="dot"),
        customdata=prior_daily["label"],
        hovertemplate="%{customdata}: %{y:,} members<extra></extra>",
    ))

    # 2018 line (solid blue — current performance)
    fig_trend.add_trace(go.Scatter(
        x=curr_daily["day_of_summer"],
        y=curr_daily["cumulative"],
        name=f"{CURRENT_YEAR} Actual",
        line=dict(color="#2563eb", width=3),
        customdata=curr_daily["label"],
        hovertemplate="%{customdata}: %{y:,} members<extra></extra>",
    ))

    # Projection line (dashed green from today to projected end-of-summer)
    if len(curr_daily) > 0:
        last_day = curr_daily["day_of_summer"].max()
        last_total = curr_daily["cumulative"].iloc[-1]
        fig_trend.add_trace(go.Scatter(
            x=[last_day, TOTAL_SUMMER_DAYS - 1],
            y=[last_total, projected],
            name="Projected",
            line=dict(color="#16a34a", width=2, dash="dash"),
            hovertemplate="Projected: %{y:,}<extra></extra>",
        ))

    # Goal reference line (red dashed horizontal)
    fig_trend.add_hline(
        y=goal, line_dash="dash", line_color="#dc2626", line_width=1.5,
        annotation_text=f"Goal: {goal:,}",
        annotation_position="top right",
        annotation_font=dict(color="#dc2626", size=11, family="JetBrains Mono"),
    )

    # X-axis: show weekly tick marks as date labels
    fig_trend.update_layout(
        **CHART_LAYOUT,
        height=400,
        legend=dict(
            orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0,
            font=dict(size=12, color="#1e293b"),
        ),
        xaxis=dict(
            tickvals=list(range(0, TOTAL_SUMMER_DAYS, 7)),
            ticktext=[
                (SUMMER_START + pd.Timedelta(days=d)).strftime("%b %d")
                for d in range(0, TOTAL_SUMMER_DAYS, 7)
            ],
            gridcolor=GRID_COLOR,
            showgrid=True,
        ),
        yaxis=dict(title="Cumulative New Members", gridcolor=GRID_COLOR, showgrid=True),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── Performance Breakdown Tables ──
    # Depending on filter level, show the next level of detail:
    #   Company view → show by Region
    #   Region view  → show by District
    #   District view → show by Gym
    #   Gym view     → show daily detail

    def build_performance_table(group_col, group_label):
        """
        Build a summary table grouped by a column.
        This is the equivalent of:
            SELECT group_col,
                   COUNT(CASE WHEN year=2018) as current_count,
                   COUNT(CASE WHEN year=2017) as prior_count,
                   ...
            FROM new_members
            GROUP BY group_col
        """
        rows = []
        for name, group in f_curr.groupby(group_col):
            grp_prior = f_prior[f_prior[group_col] == name]
            grp_prior_w = f_prior_window[f_prior_window[group_col] == name]
            g = int(len(grp_prior) * GOAL_MULTIPLIER)
            proj = project_total(len(group), len(grp_prior), len(grp_prior_w))
            pace = ((len(group) - len(grp_prior_w)) / len(grp_prior_w) * 100) if len(grp_prior_w) > 0 else 0

            display_name = f"District {name}" if group_col == "district" else name
            status = get_status(proj, g)

            rows.append({
                group_label: display_name,
                f"{CURRENT_YEAR} Actual": len(group),
                f"{PRIOR_YEAR} Full Summer": len(grp_prior),
                "Goal (+10%)": g,
                "Projected": proj,
                "Progress": f"{len(group)/g*100:.1f}%" if g > 0 else "N/A",
                f"Pace vs {PRIOR_YEAR}": f"{'▲' if pace>0 else '▼'} {abs(pace):.1f}%",
                "Status": status,
                "_pace_num": pace,
            })
        return pd.DataFrame(rows)

    def render_perf_table(perf_df, group_label):
        """Render performance table as HTML with colored Status and Pace."""
        # Build HTML table with inline styles for color
        html = '<table style="width:100%;border-collapse:collapse;font-family:DM Sans,sans-serif;font-size:0.85rem;">'

        # Header
        display_cols = [c for c in perf_df.columns if not c.startswith("_")]
        html += '<tr>'
        for col in display_cols:
            html += f'<th style="text-align:left;padding:0.6rem 0.75rem;border-bottom:2px solid #cbd5e1;font-weight:700;color:#0f172a;font-size:0.78rem;text-transform:uppercase;letter-spacing:0.03em;">{col}</th>'
        html += '</tr>'

        # Rows
        for _, row in perf_df.iterrows():
            html += '<tr style="border-bottom:1px solid #e2e8f0;">'
            for col in display_cols:
                val = row[col]
                style = "padding:0.55rem 0.75rem;"

                if col == "Status":
                    if val == "On Track":
                        style += "color:#15803d;font-weight:700;"
                        val = "✅ On Track"
                    elif val == "At Risk":
                        style += "color:#c2410c;font-weight:700;"
                        val = "⚠️ At Risk"
                    elif val == "Behind":
                        style += "color:#dc2626;font-weight:700;"
                        val = "🔴 Behind"
                elif col == f"Pace vs {PRIOR_YEAR}":
                    pace_num = row["_pace_num"]
                    if pace_num > 0:
                        style += "color:#15803d;font-weight:600;"
                    elif pace_num < 0:
                        style += "color:#dc2626;font-weight:600;"
                elif col in [f"{CURRENT_YEAR} Actual", f"{PRIOR_YEAR} Full Summer", "Goal (+10%)", "Projected"]:
                    val = f"{val:,}" if isinstance(val, (int, float)) else val
                    style += "font-family:'JetBrains Mono',monospace;"

                html += f'<td style="{style}">{val}</td>'
            html += '</tr>'

        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)

    if sel_gym != "All":
        # At gym level — show daily detail
        st.markdown(
            '<div class="section-header">Daily New Member Detail</div>',
            unsafe_allow_html=True
        )
        daily = (
            f_curr.groupby(f_curr["start_dt"].dt.strftime("%Y-%m-%d"))
            .size()
            .reset_index(name="New Members")
        )
        daily.columns = ["Date", "New Members"]
        st.dataframe(daily, use_container_width=True, hide_index=True)

    else:
        # Determine which level to break down by
        if sel_district != "All":
            group_col, group_label = "store_label", "Gym"
        elif sel_region != "All":
            group_col, group_label = "district", "District"
        else:
            group_col, group_label = "region", "Region"

        st.markdown(
            f'<div class="section-header">Performance by {group_label}</div>',
            unsafe_allow_html=True
        )
        perf_df = build_performance_table(group_col, group_label)
        render_perf_table(perf_df, group_label)

        # Bar chart: Projected vs Goal
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=perf_df[group_label], y=perf_df["Goal (+10%)"],
            name="Goal", marker_color="#93c5fd",
        ))
        fig_bar.add_trace(go.Bar(
            x=perf_df[group_label], y=perf_df["Projected"],
            name="Projected",
            marker_color=[
                "#16a34a" if p >= g else "#dc2626"
                for p, g in zip(perf_df["Projected"], perf_df["Goal (+10%)"])
            ],
        ))
        fig_bar.update_layout(
            **CHART_LAYOUT, height=350, barmode="group",
            legend=dict(
                orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0,
                font=dict(size=12, color="#1e293b"),
            ),
            xaxis=dict(gridcolor=GRID_COLOR),
            yaxis=dict(title="New Members", gridcolor=GRID_COLOR, showgrid=True),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # At company level, also show district + gym tables for full drilldown
        if sel_region == "All" and sel_district == "All":
            st.markdown(
                '<div class="section-header">Performance by District</div>',
                unsafe_allow_html=True
            )
            dist_df = build_performance_table("district", "District")
            render_perf_table(dist_df, "District")

            st.markdown(
                '<div class="section-header">Performance by Gym</div>',
                unsafe_allow_html=True
            )
            gym_df = build_performance_table("store_label", "Gym")
            gym_df = gym_df.sort_values("Projected", ascending=False)
            render_perf_table(gym_df, "Gym")


# ══════════════════════════════════════════════════════════
# TAB 2: PERSONAL TRAINING
# ══════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"### Personal Training Performance — {filter_label}")

    # ── Key Metrics ──
    # prod_cnt = number of personal training sessions purchased
    # Every new member gets 1 free session, so:
    #   prod_cnt = 1  means they only used the free session
    #   prod_cnt > 1  means the gym successfully sold extra sessions
    #
    # "Extra sessions" = prod_cnt - 1 (removing the free one)
    # This isolates the actual SALES performance of gym staff.

    avg_sessions_curr = f_curr["prod_cnt"].mean() if len(f_curr) > 0 else 0
    avg_sessions_prior = f_prior["prod_cnt"].mean() if len(f_prior) > 0 else 0
    sessions_change = (
        (avg_sessions_curr - avg_sessions_prior) / avg_sessions_prior * 100
        if avg_sessions_prior > 0 else 0
    )

    # Conversion rate: % of new members who bought beyond the free session
    conv_curr = (
        (f_curr["prod_cnt"] > 1).sum() / len(f_curr) * 100
        if len(f_curr) > 0 else 0
    )
    conv_prior = (
        (f_prior["prod_cnt"] > 1).sum() / len(f_prior) * 100
        if len(f_prior) > 0 else 0
    )

    # Average EXTRA sessions (beyond the 1 free)
    avg_extra_curr = (
        (f_curr["prod_cnt"] - 1).clip(lower=0).mean()
        if len(f_curr) > 0 else 0
    )
    avg_extra_prior = (
        (f_prior["prod_cnt"] - 1).clip(lower=0).mean()
        if len(f_prior) > 0 else 0
    )
    extra_change = (
        (avg_extra_curr - avg_extra_prior) / avg_extra_prior * 100
        if avg_extra_prior > 0 else 0
    )

    # ── KPI Row — custom HTML for all 4 to control delta colors ──
    m1, m2, m3, m4 = st.columns(4)

    def pt_kpi_card(label, value, delta_text, delta_positive, help_text=""):
        delta_color = "#15803d" if delta_positive else "#dc2626"
        return f"""<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.03em;color:#475569;">{label}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:#0f172a;">{value}</div>
            <div style="font-size:0.82rem;font-weight:600;color:{delta_color};">{delta_text}</div>
        </div>"""

    with m1:
        arrow = "▲" if sessions_change > 0 else "▼"
        st.markdown(pt_kpi_card(
            "Avg Sessions / Member",
            f"{avg_sessions_curr:.2f}",
            f"{arrow} {abs(sessions_change):.1f}% vs {PRIOR_YEAR}",
            sessions_change > 0,
        ), unsafe_allow_html=True)

    with m2:
        diff = conv_curr - conv_prior
        arrow = "▲" if diff > 0 else "▼"
        st.markdown(pt_kpi_card(
            "Upsell Conversion Rate",
            f"{conv_curr:.1f}%",
            f"{arrow} {abs(diff):.1f}pp vs {PRIOR_YEAR}",
            diff > 0,
        ), unsafe_allow_html=True)

    with m3:
        arrow = "▲" if extra_change > 0 else "▼"
        st.markdown(pt_kpi_card(
            "Avg Extra Sessions Sold",
            f"{avg_extra_curr:.2f}",
            f"{arrow} {abs(extra_change):.1f}% vs {PRIOR_YEAR}",
            extra_change > 0,
        ), unsafe_allow_html=True)

    with m4:
        total_diff = f_curr['prod_cnt'].sum() - f_prior['prod_cnt'].sum()
        st.markdown(pt_kpi_card(
            f"Total Sessions ({CURRENT_YEAR})",
            f"{f_curr['prod_cnt'].sum():,}",
            f"{'▲' if total_diff>0 else '▼'} {abs(total_diff):,} vs {PRIOR_YEAR}",
            total_diff > 0,
        ), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Distribution Comparison: Did the Spring Training Work? ──
    st.markdown(
        '<div class="section-header">Session Distribution — Impact of Spring Sales Training</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        # Side-by-side histogram showing how session counts are distributed
        # If the training worked, we should see the 2018 distribution
        # shift toward higher session counts.
        fig_dist = go.Figure()

        if len(f_prior) > 0:
            prior_dist = f_prior["prod_cnt"].value_counts(normalize=True).sort_index() * 100
            fig_dist.add_trace(go.Bar(
                x=prior_dist.index, y=prior_dist.values,
                name=f"{PRIOR_YEAR} (Pre-Training)", marker_color="#9ca3af", opacity=0.8,
            ))
        if len(f_curr) > 0:
            curr_dist = f_curr["prod_cnt"].value_counts(normalize=True).sort_index() * 100
            fig_dist.add_trace(go.Bar(
                x=curr_dist.index, y=curr_dist.values,
                name=f"{CURRENT_YEAR} (Post-Training)", marker_color="#2563eb", opacity=0.9,
            ))

        fig_dist.update_layout(
            **CHART_LAYOUT, height=380, barmode="group",
            title=dict(text="Sessions Distribution", font=dict(size=14, color="#0f172a")),
            xaxis=dict(title="Sessions Purchased", dtick=1, gridcolor=GRID_COLOR),
            yaxis=dict(title="% of New Members", gridcolor=GRID_COLOR, showgrid=True),
            legend=dict(
                orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0,
                font=dict(size=11, color="#1e293b"),
            ),
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with col2:
        # Monthly average sessions — shows if performance improved
        # over the course of summer (especially after spring training)
        monthly_curr = (
            f_curr.groupby(f_curr["start_dt"].dt.to_period("M"))["prod_cnt"]
            .mean()
        )
        monthly_prior = (
            f_prior.groupby(f_prior["start_dt"].dt.to_period("M"))["prod_cnt"]
            .mean()
        )

        month_labels = ["Jun", "Jul", "Aug"]

        fig_monthly = go.Figure()
        if len(monthly_prior) > 0:
            fig_monthly.add_trace(go.Scatter(
                x=month_labels[:len(monthly_prior)],
                y=monthly_prior.values,
                name=f"{PRIOR_YEAR}",
                line=dict(color="#6b7280", width=2.5, dash="dot"),
                mode="lines+markers",
                marker=dict(size=8),
            ))
        if len(monthly_curr) > 0:
            fig_monthly.add_trace(go.Scatter(
                x=month_labels[:len(monthly_curr)],
                y=monthly_curr.values,
                name=f"{CURRENT_YEAR}",
                line=dict(color="#2563eb", width=3),
                mode="lines+markers",
                marker=dict(size=8),
            ))

        fig_monthly.update_layout(
            **CHART_LAYOUT, height=380,
            title=dict(text="Monthly Avg Sessions per Member", font=dict(size=14, color="#0f172a")),
            xaxis=dict(gridcolor=GRID_COLOR),
            yaxis=dict(title="Avg Sessions", gridcolor=GRID_COLOR, showgrid=True),
            legend=dict(
                orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0,
                font=dict(size=11, color="#1e293b"),
            ),
        )
        st.plotly_chart(fig_monthly, use_container_width=True)

    # ── Breakdown Table + Bar Chart ──
    def build_pt_table(group_col, group_label):
        """Build personal training comparison table by group."""
        rows = []
        for name in sorted(f_curr[group_col].unique()):
            c = f_curr[f_curr[group_col] == name]["prod_cnt"]
            p = f_prior[f_prior[group_col] == name]["prod_cnt"]
            avg_c = c.mean() if len(c) > 0 else 0
            avg_p = p.mean() if len(p) > 0 else 0
            chg = ((avg_c - avg_p) / avg_p * 100) if avg_p > 0 else 0

            # Extra sessions (beyond the free one)
            extra_c = (c - 1).clip(lower=0).mean() if len(c) > 0 else 0
            extra_p = (p - 1).clip(lower=0).mean() if len(p) > 0 else 0

            display_name = f"District {name}" if group_col == "district" else name

            rows.append({
                group_label: display_name,
                f"{PRIOR_YEAR} Avg Sessions": round(avg_p, 2),
                f"{CURRENT_YEAR} Avg Sessions": round(avg_c, 2),
                "YoY Change": chg,
                f"{PRIOR_YEAR} Avg Extra": round(extra_p, 2),
                f"{CURRENT_YEAR} Avg Extra": round(extra_c, 2),
                "Improved": "Yes" if chg > 0 else "No",
            })
        return pd.DataFrame(rows)

    def render_pt_table(pt_df, group_label):
        """Render PT table as HTML with colored change values."""
        html = '<table style="width:100%;border-collapse:collapse;font-family:DM Sans,sans-serif;font-size:0.85rem;">'

        # Header
        html += '<tr>'
        for col in pt_df.columns:
            html += f'<th style="text-align:left;padding:0.6rem 0.75rem;border-bottom:2px solid #cbd5e1;font-weight:700;color:#0f172a;font-size:0.78rem;text-transform:uppercase;letter-spacing:0.03em;">{col}</th>'
        html += '</tr>'

        for _, row in pt_df.iterrows():
            html += '<tr style="border-bottom:1px solid #e2e8f0;">'
            for col in pt_df.columns:
                val = row[col]
                style = "padding:0.55rem 0.75rem;"

                if col == "YoY Change":
                    color = "#15803d" if val > 0 else "#dc2626"
                    arrow = "▲" if val > 0 else "▼"
                    style += f"color:{color};font-weight:600;"
                    val = f"{arrow} {abs(val):.1f}%"
                elif col == "Improved":
                    if val == "Yes":
                        style += "color:#15803d;font-weight:700;"
                        val = "✅ Yes"
                    else:
                        style += "color:#dc2626;font-weight:700;"
                        val = "❌ No"
                elif col in [f"{PRIOR_YEAR} Avg Sessions", f"{CURRENT_YEAR} Avg Sessions",
                             f"{PRIOR_YEAR} Avg Extra", f"{CURRENT_YEAR} Avg Extra"]:
                    style += "font-family:'JetBrains Mono',monospace;"

                html += f'<td style="{style}">{val}</td>'
            html += '</tr>'

        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)

    if sel_gym != "All":
        pass  # No further breakdown at individual gym level
    else:
        if sel_district != "All":
            group_col, group_label = "store_label", "Gym"
        elif sel_region != "All":
            group_col, group_label = "district", "District"
        else:
            group_col, group_label = "region", "Region"

        st.markdown(
            f'<div class="section-header">PT Performance by {group_label}</div>',
            unsafe_allow_html=True
        )
        pt_df = build_pt_table(group_col, group_label)
        render_pt_table(pt_df, group_label)

        # Horizontal bar chart of YoY change
        fig_change = go.Figure()
        fig_change.add_trace(go.Bar(
            y=pt_df[group_label],
            x=pt_df["YoY Change"],
            orientation="h",
            marker_color=["#16a34a" if c > 0 else "#dc2626" for c in pt_df["YoY Change"]],
            text=[f"{c:+.1f}%" for c in pt_df["YoY Change"]],
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=11, color="#1e293b"),
        ))
        fig_change.add_vline(x=0, line_color="#6b7280", line_width=1)
        fig_change.update_layout(
            **CHART_LAYOUT,
            height=max(250, len(pt_df) * 45 + 80),
            title=dict(text=f"Avg Sessions YoY Change by {group_label}", font=dict(size=14, color="#0f172a")),
            xaxis=dict(title="% Change", gridcolor=GRID_COLOR, showgrid=True),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_change, use_container_width=True)

        # At company level, also show full gym breakdown
        if sel_region == "All" and sel_district == "All":
            st.markdown(
                '<div class="section-header">PT Performance by Gym — Full Breakdown</div>',
                unsafe_allow_html=True
            )
            gym_pt_df = build_pt_table("store_label", "Gym")
            gym_pt_df_sorted = gym_pt_df.sort_values(f"{CURRENT_YEAR} Avg Sessions", ascending=False)
            render_pt_table(gym_pt_df_sorted, "Gym")
