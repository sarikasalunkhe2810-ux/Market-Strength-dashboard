import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="MarketStrength | India Sector Rotation", page_icon="📈", layout="wide")

st.title("📈 MarketStrength")
st.caption("Indian Sector Rotation Dashboard · Relative strength vs Nifty 500")
st.info("Market data is sourced from Yahoo Finance and may be delayed, incomplete, or unavailable. This is an analytical tool, not investment advice.")

SECTORS = {
    "Auto": "^CNXAUTO",
    "Bank": "^NSEBANK",
    "Energy": "^CNXENERGY",
    "FMCG": "^CNXFMCG",
    "IT": "^CNXIT",
    "Media": "^CNXMEDIA",
    "Metal": "^CNXMETAL",
    "Pharma": "^CNXPHARMA",
    "PSU Bank": "^CNXPSUBANK",
    "Realty": "^CNXREALTY",
    "Infrastructure": "^CNXINFRA",
}
BENCHMARK = "^CRSLDX"  # Nifty 500, where available on Yahoo Finance

@st.cache_data(ttl=900, show_spinner=False)
def download_history(tickers, period="2y"):
    # auto_adjust=True avoids split/dividend adjustment inconsistencies for supported symbols.
    return yf.download(
        tickers=list(tickers),
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

def extract_close(raw, ticker):
    if raw is None or raw.empty:
        return pd.Series(dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance layout differs by version; handle either ticker-first or field-first columns.
        if ticker in raw.columns.get_level_values(0):
            frame = raw[ticker]
            if "Close" in frame:
                return frame["Close"].dropna()
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"]
            if ticker in close.columns:
                return close[ticker].dropna()
        return pd.Series(dtype=float)
    if "Close" in raw.columns:
        return raw["Close"].dropna()
    return pd.Series(dtype=float)

with st.sidebar:
    st.header("Settings")
    period = st.selectbox("History to download", ["1y", "2y", "5y"], index=1)
    benchmark = st.text_input("Benchmark Yahoo ticker", value=BENCHMARK, help="Default is ^CRSLDX (Nifty 500 on Yahoo Finance, if available).")
    st.caption("Use Refresh data below if prices look stale.")

if st.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

tickers = list(SECTORS.values()) + [benchmark]
with st.spinner("Downloading available sector-index history…"):
    raw = download_history(tickers, period)

bench_close = extract_close(raw, benchmark)
if bench_close.empty:
    st.error(f"Could not retrieve benchmark data for {benchmark}. Yahoo Finance may not provide this symbol right now. Check the ticker or try again later.")
    st.stop()

def pct_return(series, days):
    series = series.dropna()
    if len(series) <= days:
        return np.nan
    return (series.iloc[-1] / series.iloc[-days-1] - 1) * 100

bench_returns = {d: pct_return(bench_close, d) for d in (21, 63, 126, 252)}
rows = []
for name, ticker in SECTORS.items():
    close = extract_close(raw, ticker)
    if close.empty or len(close) < 22:
        continue
    aligned = pd.concat([close.rename("sector"), bench_close.rename("benchmark")], axis=1).dropna()
    if len(aligned) < 22:
        continue
    r = {d: pct_return(aligned["sector"], d) for d in (21, 63, 126, 252)}
    br = {d: pct_return(aligned["benchmark"], d) for d in (21, 63, 126, 252)}
    rs = {d: r[d] - br[d] if pd.notna(r[d]) and pd.notna(br[d]) else np.nan for d in (21, 63, 126, 252)}
    # Weighted relative-strength score; available horizons are renormalized.
    weights = {21: 0.4, 63: 0.3, 126: 0.2, 252: 0.1}
    usable = [(rs[d], weights[d]) for d in weights if pd.notna(rs[d])]
    score = sum(v*w for v, w in usable) / sum(w for _, w in usable) if usable else np.nan
    momentum = rs[21] - rs[63] if pd.notna(rs[21]) and pd.notna(rs[63]) else np.nan
    rows.append({
        "Sector": name, "Yahoo ticker": ticker,
        "1M return %": r[21], "3M return %": r[63],
        "6M return %": r[126], "12M return %": r[252],
        "1M RS vs Nifty 500 (pp)": rs[21],
        "3M RS vs Nifty 500 (pp)": rs[63],
        "6M RS vs Nifty 500 (pp)": rs[126],
        "12M RS vs Nifty 500 (pp)": rs[252],
        "RS score": score, "RS momentum": momentum,
        "Last close": float(close.dropna().iloc[-1]),
        "Data date": pd.Timestamp(close.dropna().index[-1]).strftime("%Y-%m-%d")
    })

if not rows:
    st.warning("No sector data could be retrieved. Yahoo Finance index symbols can change or be unavailable. Try Refresh data or check the ticker list in app.py.")
    st.stop()

df = pd.DataFrame(rows).sort_values("RS score", ascending=False, na_position="last").reset_index(drop=True)
df.insert(0, "Rank", np.arange(1, len(df) + 1))

# Rotation quadrants are median-centred, so they describe relative position within this sector set.
xmid = df["RS score"].median()
ymid = df["RS momentum"].median()
def quadrant(row):
    if pd.isna(row["RS score"]) or pd.isna(row["RS momentum"]):
        return "Insufficient data"
    if row["RS score"] >= xmid and row["RS momentum"] >= ymid:
        return "Leading"
    if row["RS score"] >= xmid and row["RS momentum"] < ymid:
        return "Weakening"
    if row["RS score"] < xmid and row["RS momentum"] >= ymid:
        return "Improving"
    return "Lagging"
df["Rotation quadrant"] = df.apply(quadrant, axis=1)

valid = df.dropna(subset=["RS score", "RS momentum"])
latest_date = df["Data date"].max()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Sectors with data", len(df))
c2.metric("Leading", int((df["Rotation quadrant"] == "Leading").sum()))
c3.metric("Improving", int((df["Rotation quadrant"] == "Improving").sum()))
c4.metric("Latest available data", latest_date)

st.subheader("Sector strength ranking")
display_cols = ["Rank", "Sector", "RS score", "RS momentum", "1M RS vs Nifty 500 (pp)", "3M RS vs Nifty 500 (pp)", "6M RS vs Nifty 500 (pp)", "12M RS vs Nifty 500 (pp)", "Rotation quadrant", "Last close", "Data date"]
st.dataframe(
    df[display_cols].style.format({
        "RS score": "{:.2f}", "RS momentum": "{:.2f}",
        "1M RS vs Nifty 500 (pp)": "{:.2f}", "3M RS vs Nifty 500 (pp)": "{:.2f}",
        "6M RS vs Nifty 500 (pp)": "{:.2f}", "12M RS vs Nifty 500 (pp)": "{:.2f}",
        "Last close": "{:.2f}",
    }, na_rep="—"),
    use_container_width=True, hide_index=True
)

left, right = st.columns(2)
with left:
    st.subheader("Relative strength score")
    bar = px.bar(df.sort_values("RS score"), x="RS score", y="Sector", orientation="h",
                 color="RS score", color_continuous_scale="RdYlGn",
                 hover_data=["RS momentum", "Rotation quadrant"])
    bar.update_layout(height=480, coloraxis_showscale=False, xaxis_title="Weighted RS score (percentage points)", yaxis_title="")
    st.plotly_chart(bar, use_container_width=True)
with right:
    st.subheader("Sector rotation quadrants")
    if not valid.empty:
        scatter = px.scatter(valid, x="RS score", y="RS momentum", text="Sector",
                             color="Rotation quadrant",
                             hover_data=["1M RS vs Nifty 500 (pp)", "3M RS vs Nifty 500 (pp)", "Data date"])
        scatter.add_vline(x=xmid, line_dash="dash", line_color="gray")
        scatter.add_hline(y=ymid, line_dash="dash", line_color="gray")
        scatter.update_traces(textposition="top center")
        scatter.update_layout(height=480, xaxis_title="Relative strength score", yaxis_title="Short-term RS momentum")
        st.plotly_chart(scatter, use_container_width=True)
    else:
        st.warning("Not enough data to draw the rotation chart.")

st.subheader("How to read the quadrants")
q1, q2, q3, q4 = st.columns(4)
q1.markdown("**Leading**\n\nStronger RS and improving short-term momentum.")
q2.markdown("**Weakening**\n\nStronger RS, but short-term momentum is fading.")
q3.markdown("**Improving**\n\nWeaker RS, but short-term momentum is improving.")
q4.markdown("**Lagging**\n\nWeaker RS and weaker short-term momentum.")
st.caption("Quadrants use medians of the sectors currently available, not fixed buy/sell thresholds. RS is sector return minus benchmark return, in percentage points. The RS score weights 1M/3M/6M/12M RS at 40%/30%/20%/10% where data is available.")

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download sector analysis CSV", data=csv, file_name="marketstrength_sector_rotation.csv", mime="text/csv")

with st.expander("Data quality and limitations"):
    st.markdown("""
    - The app uses Yahoo Finance history via `yfinance`; it is not an official NSE feed.
    - Index symbols may be unavailable, renamed, or return incomplete history. Missing sectors are omitted rather than guessed.
    - The benchmark defaults to `^CRSLDX`. If Yahoo Finance does not return it, verify the benchmark ticker before interpreting relative-strength results.
    - This dashboard is for research and education, not personalized financial advice or a trading signal.
    """)
