from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

from navigation import make_sidebar


def get_massive_key() -> str | None:
    try:
        return st.secrets.get("MASSIVE_KEY") or st.secrets.get("POLYGON_API_KEY")
    except StreamlitSecretNotFoundError:
        return None


@st.cache_data(ttl=5)
def fetch_intraday_bars(symbol: str, api_key: str, date_str: str) -> list[dict]:
    response = requests.get(
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{date_str}/{date_str}",
        params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    return [
        {
            "time": int(row["t"] / 1000),
            "open": row["o"],
            "high": row["h"],
            "low": row["l"],
            "close": row["c"],
        }
        for row in results
    ]


def render_lightweight_chart(symbol: str, title: str) -> None:
    make_sidebar()

    if not st.session_state.get("logged_in", False):
        st.error("Unauthorized. Please log in from the main page.")
        st.page_link("streamlit_app.py", label="Go to Home")
        st.stop()

    st.title(title)

    api_key = get_massive_key()
    if not api_key:
        st.error("Missing MASSIVE_KEY in Streamlit secrets.")
        st.stop()

    est_now = datetime.now(ZoneInfo("America/New_York"))
    est_date = est_now.strftime("%Y-%m-%d")

    try:
        data = fetch_intraday_bars(symbol=symbol, api_key=api_key, date_str=est_date)
    except requests.HTTPError as exc:
        st.error(f"Failed to fetch {symbol} data from Polygon/Massive: {exc}")
        st.stop()

    if not data:
        st.warning(f"No 1-minute data available yet for {symbol} on {est_date} (EST).")
        st.stop()

    st.caption(f"Source: Polygon/Massive • Cached for 5 seconds • Date: {est_date} EST")

    chart_html = f"""
    <div id='chart' style='height:460px;'></div>
    <script src='https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js'></script>
    <script>
      const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
        layout: {{ background: {{ color: '#0e1117' }}, textColor: '#d1d4dc' }},
        grid: {{ vertLines: {{ color: '#1f2430' }}, horzLines: {{ color: '#1f2430' }} }},
        width: 1200,
        height: 460,
        rightPriceScale: {{ borderColor: '#485c7b' }},
        timeScale: {{ borderColor: '#485c7b', timeVisible: true, secondsVisible: false }}
      }});

      const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {{
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350'
      }});

      candleSeries.setData({data});
      chart.timeScale().fitContent();
    </script>
    """

    components.html(chart_html, height=480)
