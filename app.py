import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# ============================================================
# MARKETSTRENGTH MASTER DASHBOARD
# Technical version - Fundamentals will be added later
# ============================================================

st.set_page_config(
    page_title="MarketStrength Master Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 MarketStrength Master Dashboard")
st.caption("India | Global | Sector Strength | Relative Strength | Stage Analysis")

# -------------------- MARKET UNIVERSES --------------------

US_STOCKS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "AVGO": "Broadcom",
    "LLY": "Eli Lilly",
    "JPM": "JPMorgan Chase",
    "COST": "Costco"
}

INDIAN_ETFS = {
    "NIFTYBEES.NS": "Nifty 50 ETF",
    "JUNIORBEES.NS": "Nifty Next 50 ETF",
    "MONQ50.NS": "MONQ50 ETF",
    "GOLDBEES.NS": "Gold ETF"
}

GLOBAL_ETFS = {
    "VWRA.L": "Vanguard FTSE All-World ETF",
    "CSPX.L": "iShares Core S&P 500 ETF",
    "AGAC.L": "Global Aggregate Bond ETF"
}

BENCHMARK = "^NSEI"


# -------------------- NIFTY 500 UNIVERSE --------------------

@st.cache_data(ttl=86400, show_spinner=False)
def get_nifty500():

    url = (
        "https://www.niftyindices.com/"
        "IndexConstituent/ind_nifty500list.csv"
    )

    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    df = pd.read_csv(io.BytesIO(response.content))
    df.columns = df.columns.str.strip()

    if "Symbol" not in df.columns:
        raise ValueError("Symbol column not found.")

    company_col = (
        "Company Name"
        if "Company Name" in df.columns
        else "Symbol"
    )

    industry_col = next(
        (
            col for col in
            ["Industry", "Industry Name", "Sector"]
            if col in df.columns
        ),
        None
    )

    df = df.dropna(subset=["Symbol"]).copy()

    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    df["Company"] = df[company_col].astype(str).str.strip()

    if industry_col:
        df["Industry"] = (
            df[industry_col].fillna("Unclassified").astype(str).str.strip()
        )
    else:
        df["Industry"] = "Unclassified"

    df["Industry"] = df["Industry"].replace(
        ["nan", "None", ""],
        "Unclassified"
    )

    df = df.drop_duplicates(subset=["Symbol"])

    df["Yahoo Ticker"] = df["Symbol"] + ".NS"

    return df[
        ["Symbol", "Company", "Industry", "Yahoo Ticker"]
    ]


# -------------------- PRICE DOWNLOAD --------------------

@st.cache_data(ttl=1800, show_spinner=False)
def download_prices(tickers):

    prices = {}

    tickers = list(tickers)

    for start in range(0, len(tickers), 25):

        batch = tickers[start:start + 25]

        try:

            data = yf.download(
                tickers=batch,
                period="2y",
                interval="1d",
                auto_adjust=True,
                progress=False,
                group_by="ticker",
                threads=False
            )

            if data is None or data.empty:
                continue

            for ticker in batch:

                try:

                    if isinstance(data.columns, pd.MultiIndex):

                        if ticker in data.columns.get_level_values(0):
                            close = data[ticker]["Close"]

                        elif ticker in data.columns.get_level_values(1):
                            close = data.xs(
                                ticker,
                                axis=1,
                                level=1
                            )["Close"]

                        else:
                            continue

                    else:

                        if len(batch) != 1:
                            continue

                        close = data["Close"]

                    if isinstance(close, pd.DataFrame):
                        close = close.iloc[:, 0]

                    close = pd.to_numeric(
                        close,
                        errors="coerce"
                    ).dropna()

                    if not close.empty:
                        prices[ticker] = close

                except Exception:
                    continue

        except Exception:
            continue

    return prices


# -------------------- RETURN CALCULATIONS --------------------

def calculate_return(close, days):

    if close is None or len(close) <= days:
        return None

    old_price = float(close.iloc[-days - 1])
    current_price = float(close.iloc[-1])

    if old_price == 0:
        return None

    return round(
        (current_price / old_price - 1) * 100,
        2
    )


def calculate_rs(asset_close, benchmark_close, days):

    asset_return = calculate_return(asset_close, days)
    benchmark_return = calculate_return(benchmark_close, days)

    if asset_return is None or benchmark_return is None:
        return None

    return round(asset_return - benchmark_return, 2)


# -------------------- STAGE ANALYSIS --------------------

def stage_label(close):

    if close is None or len(close) < 170:
        return "Insufficient Data"

    ma150 = close.rolling(150).mean()

    price = close.iloc[-1]
    current_ma = ma150.iloc[-1]
    previous_ma = ma150.iloc[-20]

    if pd.isna(current_ma) or pd.isna(previous_ma):
        return "Insufficient Data"

    if price > current_ma and current_ma > previous_ma:
        return "Stage 2"

    if price < current_ma and current_ma < previous_ma:
        return "Stage 4"

    if price > current_ma and current_ma <= previous_ma:
        return "Stage 3"

    return "Stage 1"


# -------------------- STOCK ANALYSIS --------------------

def build_stock_table(asset_df, prices, benchmark=None):

    rows = []

    for _, asset in asset_df.iterrows():

        ticker = asset["Yahoo Ticker"]
        close = prices.get(ticker)

        if close is None or close.empty:
            continue

        row = {
            "Ticker": asset["Symbol"],
            "Company": asset["Company"],
            "Industry": asset["Industry"],
            "Price": round(float(close.iloc[-1]), 2),

            "1M Return %": calculate_return(close, 21),
            "3M Return %": calculate_return(close, 63),
            "6M Return %": calculate_return(close, 126),
            "12M Return %": calculate_return(close, 252),

            "Stage": stage_label(close)
        }

        if benchmark is not None:

            row["1M RS %"] = calculate_rs(close, benchmark, 21)
            row["3M RS %"] = calculate_rs(close, benchmark, 63)
            row["6M RS %"] = calculate_rs(close, benchmark, 126)
            row["12M RS %"] = calculate_rs(close, benchmark, 252)

        else:

            row["1M RS %"] = None
            row["3M RS %"] = None
            row["6M RS %"] = None
            row["12M RS %"] = None

        rs_values = [
            row["1M RS %"],
            row["3M RS %"],
            row["6M RS %"],
            row["12M RS %"]
        ]

        valid_rs = [x for x in rs_values if x is not None]

        row["RS Score"] = (
            round(sum(valid_rs) / len(valid_rs), 2)
            if valid_rs else None
        )

        if (
            row["Stage"] == "Stage 2"
            and row["3M RS %"] is not None
            and row["3M RS %"] > 0
        ):
            row["Signal"] = "BUY CANDIDATE"

        elif (
            row["Stage"] in ["Stage 1", "Stage 2"]
            or (
                row["3M RS %"] is not None
                and row["3M RS %"] > 0
            )
        ):
            row["Signal"] = "WATCH"

        else:
            row["Signal"] = "AVOID"

        rows.append(row)

    return pd.DataFrame(rows)


# -------------------- SECTOR ANALYSIS --------------------

def build_sector_table(stock_table):

    if stock_table.empty:
        return pd.DataFrame()

    sector = (
        stock_table.groupby("Industry")
        .agg(
            Stocks=("Ticker", "count"),
            **{
                "Avg 1M RS %": ("1M RS %", "mean"),
                "Avg 3M RS %": ("3M RS %", "mean"),
                "Avg 6M RS %": ("6M RS %", "mean"),
                "Avg 12M RS %": ("12M RS %", "mean"),
                "Stage 2 Stocks": (
                    "Stage",
                    lambda x: (x == "Stage 2").sum()
                ),
                "Positive RS Stocks": (
                    "3M RS %",
                    lambda x: (x > 0).sum()
                )
            }
        )
        .reset_index()
        .rename(columns={"Industry": "Sector"})
    )

    rs_columns = [
        "Avg 1M RS %",
        "Avg 3M RS %",
        "Avg 6M RS %",
        "Avg 12M RS %"
    ]

    sector["RS Score"] = (
        sector[rs_columns].mean(axis=1).round(2)
    )

    def rotation(row):

        rs1 = row["Avg 1M RS %"]
        rs3 = row["Avg 3M RS %"]

        if pd.isna(rs1) or pd.isna(rs3):
            return "Insufficient Data"

        if rs1 > 0 and rs3 > 0:
            return "Leading"

        if rs1 > 0 and rs3 <= 0:
            return "Improving"

        if rs1 <= 0 and rs3 > 0:
            return "Weakening"

        return "Lagging"

    sector["Rotation"] = sector.apply(rotation, axis=1)

    return sector.sort_values(
        "RS Score",
        ascending=False,
        na_position="last"
    )


# -------------------- COLOUR CODING --------------------

def style_dashboard(df):

    def signal_colour(value):

        if value in ["BUY CANDIDATE", "Leading"]:
            return (
                "background-color:#c6efce;"
                "color:#006100;font-weight:bold"
            )

        if value in ["WATCH", "Improving"]:
            return (
                "background-color:#ffeb9c;"
                "color:#9c6500;font-weight:bold"
            )

        if value in ["AVOID", "Lagging"]:
            return (
                "background-color:#ffc7ce;"
                "color:#9c0006;font-weight:bold"
            )

        if value == "Weakening":
            return (
                "background-color:#fce4d6;"
                "color:#9c5700;font-weight:bold"
            )

        return ""

    styled = df.style

    for column in ["Signal", "Rotation"]:

        if column in df.columns:
            styled = styled.map(
                signal_colour,
                subset=[column]
            )

    for column in [
        "1M RS %",
        "3M RS %",
        "6M RS %",
        "12M RS %",
        "Avg 1M RS %",
        "Avg 3M RS %",
        "Avg 6M RS %",
        "Avg 12M RS %",
        "RS Score"
    ]:

        if column in df.columns:

            styled = styled.map(
                lambda value:
                    "color:#006100;font-weight:bold"
                    if pd.notna(value) and value > 0
                    else (
                        "color:#9c0006"
                        if pd.notna(value) and value < 0
                        else ""
                    ),
                subset=[column]
            )

    return styled


def show_table(df, total=None):

    if df.empty:
        st.warning("No usable price data found. Please refresh later.")
        return

    if total is not None:
        st.caption(
            f"Showing {len(df)} assets out of {total} requested."
        )

    st.dataframe(
        style_dashboard(df),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="marketstrength_results.csv",
        mime="text/csv"
    )


# -------------------- SIDEBAR --------------------

st.sidebar.title("Market Settings")

market = st.sidebar.selectbox(
    "Select Market",
    [
        "India",
        "United States",
        "Indian ETFs",
        "Global ETFs"
    ]
)

page = st.sidebar.radio(
    "Dashboard Section",
    [
        "Master Dashboard",
        "Sector Strength",
        "Strong Stocks by Sector",
        "Stock Scanner",
        "Stage Analysis"
    ]
)


# -------------------- LOAD UNIVERSE --------------------

nifty_df = pd.DataFrame()

if market == "India" or page in [
    "Sector Strength",
    "Strong Stocks by Sector"
]:

    try:

        with st.spinner("Loading Nifty 500 constituents..."):
            nifty_df = get_nifty500()

        st.sidebar.success(
            f"Nifty 500 loaded: {len(nifty_df)} stocks"
        )

    except Exception as error:

        st.sidebar.error("Could not load Nifty 500.")
        st.sidebar.caption(str(error))


if market == "India":

    asset_df = nifty_df.copy()

elif market == "United States":

    asset_df = pd.DataFrame([
        {
            "Symbol": ticker,
            "Company": name,
            "Industry": "US Stocks",
            "Yahoo Ticker": ticker
        }
        for ticker, name in US_STOCKS.items()
    ])

elif market == "Indian ETFs":

    asset_df = pd.DataFrame([
        {
            "Symbol": ticker.replace(".NS", ""),
            "Company": name,
            "Industry": "Indian ETFs",
            "Yahoo Ticker": ticker
        }
        for ticker, name in INDIAN_ETFS.items()
    ])

else:

    asset_df = pd.DataFrame([
        {
            "Symbol": ticker,
            "Company": name,
            "Industry": "Global ETFs",
            "Yahoo Ticker": ticker
        }
        for ticker, name in GLOBAL_ETFS.items()
    ])


# -------------------- BENCHMARK --------------------

benchmark_close = None

if market == "India" or page in [
    "Sector Strength",
    "Strong Stocks by Sector"
]:

    benchmark_prices = download_prices((BENCHMARK,))
    benchmark_close = benchmark_prices.get(BENCHMARK)


# -------------------- SECTOR STRENGTH --------------------

if page == "Sector Strength" or page == "Strong Stocks by Sector":

    st.subheader("🏆 Nifty 500 Sector Strength")

    if nifty_df.empty:

        st.error("Nifty 500 data could not be loaded.")

    elif benchmark_close is None:

        st.error("Nifty 50 benchmark data could not be loaded.")

    else:

        tickers = tuple(nifty_df["Yahoo Ticker"].tolist())

        with st.spinner(
            "Analysing Nifty 500 stocks. Please wait..."
        ):

            prices = download_prices(tickers)

        stock_table = build_stock_table(
            nifty_df,
            prices,
            benchmark_close
        )

        sector_table = build_sector_table(stock_table)

        if sector_table.empty:

            st.warning("No sector data available.")

        elif page == "Sector Strength":

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "Industries",
                len(sector_table)
            )

            c2.metric(
                "Leading",
                int((sector_table["Rotation"] == "Leading").sum())
            )

            c3.metric(
                "Improving",
                int((sector_table["Rotation"] == "Improving").sum())
            )

            c4.metric(
                "Stocks Analysed",
                len(stock_table)
            )

            st.markdown("### Sector Rotation Ranking")

            show_table(sector_table)

            st.markdown("### Top 10 Strongest Sectors")

            show_table(sector_table.head(10))

            st.markdown("### Leading Sectors")

            show_table(
                sector_table[
                    sector_table["Rotation"] == "Leading"
                ]
            )

        else:

            industries = sorted(
                stock_table["Industry"].dropna().unique()
            )

            if industries:

                selected_sector = st.selectbox(
                    "Select Sector",
                    industries
                )

                selected_stocks = stock_table[
                    stock_table["Industry"] == selected_sector
                ].sort_values(
                    "RS Score",
                    ascending=False,
                    na_position="last"
                )

                st.markdown(
                    f"### Strong Stocks: {selected_sector}"
                )

                show_table(selected_stocks)

                st.markdown("### Stage 2 Candidates")

                show_table(
                    selected_stocks[
                        selected_stocks["Stage"] == "Stage 2"
                    ]
                )


# -------------------- MASTER DASHBOARD --------------------

elif page == "Master Dashboard":

    st.subheader("📊 Market Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Selected Market", market)
    c2.metric("Universe Size", len(asset_df))
    c3.metric("RS Periods", "1M / 3M / 6M / 12M")
    c4.metric(
        "Updated",
        datetime.now().strftime("%d %b %Y")
    )

    if asset_df.empty:

        st.warning("No assets loaded.")

    else:

        prices = download_prices(
            tuple(asset_df["Yahoo Ticker"].tolist())
        )

        table = build_stock_table(
            asset_df,
            prices,
            benchmark_close
        )

        if not table.empty:

            table = table.sort_values(
                "RS Score",
                ascending=False,
                na_position="last"
            )

        if market == "India":
            st.info(
                "Relative Strength is measured against Nifty 50. "
                "Positive RS means outperformance."
            )

        show_table(table, len(asset_df))


# -------------------- STOCK SCANNER --------------------

elif page == "Stock Scanner":

    st.subheader(f"🔎 {market} Stock Scanner")

    if asset_df.empty:

        st.warning("No assets loaded.")

    else:

        prices = download_prices(
            tuple(asset_df["Yahoo Ticker"].tolist())
        )

        table = build_stock_table(
            asset_df,
            prices,
            benchmark_close
        )

        if not table.empty:

            table = table.sort_values(
                "RS Score",
                ascending=False,
                na_position="last"
            )

        show_table(table, len(asset_df))


# -------------------- STAGE ANALYSIS --------------------

elif page == "Stage Analysis":

    st.subheader("📈 Stage 1–4 Analysis")

    st.info(
        "Approximate daily 150-day moving-average method. "
        "This is not the full weekly Weinstein 30-week method."
    )

    if asset_df.empty:

        st.warning("No assets loaded.")

    else:

        prices = download_prices(
            tuple(asset_df["Yahoo Ticker"].tolist())
        )

        table = build_stock_table(
            asset_df,
            prices,
            benchmark_close
        )

        if not table.empty:

            stage_table = table[
                [
                    "Ticker",
                    "Company",
                    "Industry",
                    "Price",
                    "Stage",
                    "3M RS %",
                    "RS Score",
                    "Signal"
                ]
            ].sort_values(
                "RS Score",
                ascending=False,
                na_position="last"
            )

            show_table(stage_table, len(asset_df))

# -------------------- FOOTER --------------------

st.divider()

st.caption(
    "MarketStrength Master Dashboard | Yahoo Finance data | "
    "Technical screening only | Fundamentals will be added later. "
    "Signals are research filters, not investment advice."
)
