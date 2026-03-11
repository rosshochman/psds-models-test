from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

from navigation import make_sidebar

EST = ZoneInfo("America/New_York")
TIMEFRAME_OPTIONS = {
    "1 Min": (1, "minute"),
    "5 Min": (5, "minute"),
    "1 Hour": (1, "hour"),
}
EMA_OPTIONS = (9, 21, 50)


def get_massive_key() -> str | None:
    try:
        return st.secrets.get("MASSIVE_KEY") or st.secrets.get("POLYGON_API_KEY")
    except StreamlitSecretNotFoundError:
        return None


@st.cache_data(ttl=5)
def fetch_intraday_bars(
    symbol: str, api_key: str, date_str: str, multiplier: int, timespan: str
) -> list[dict]:
    response = requests.get(
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{date_str}/{date_str}",
        params={"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": api_key},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    bars: list[dict] = []
    for row in results:
        est_time = datetime.fromtimestamp(int(row["t"] / 1000), tz=EST)
        in_regular_session = (
            est_time.weekday() < 5
            and (
                (est_time.hour > 9 or (est_time.hour == 9 and est_time.minute >= 30))
                and est_time.hour < 16
            )
        )
        bars.append(
            {
                "time": int(row["t"] / 1000),
                "open": row["o"],
                "high": row["h"],
                "low": row["l"],
                "close": row["c"],
                "volume": row.get("v", 0),
                "session": "regular" if in_regular_session else "extended",
            }
        )
    return bars


def _ema(data: list[dict], length: int) -> list[dict]:
    if not data:
        return []
    alpha = 2 / (length + 1)
    ema_value = data[0]["close"]
    result: list[dict] = []
    for row in data:
        ema_value = (row["close"] * alpha) + (ema_value * (1 - alpha))
        result.append({"time": row["time"], "value": round(ema_value, 4)})
    return result


def _vwap(data: list[dict]) -> list[dict]:
    cumulative_pv = 0.0
    cumulative_volume = 0.0
    result: list[dict] = []
    for row in data:
        price = (row["high"] + row["low"] + row["close"]) / 3
        volume = row.get("volume", 1) or 1
        cumulative_pv += price * volume
        cumulative_volume += volume
        result.append({"time": row["time"], "value": round(cumulative_pv / cumulative_volume, 4)})
    return result


def _toggle_button(label: str, key: str) -> None:
    toggle_state = st.session_state.get(key, False)
    button_label = f"{label} {'✅' if toggle_state else ''}".strip()
    if st.button(button_label, key=f"{key}_button", use_container_width=True):
        st.session_state[key] = not toggle_state


def _render_chart(symbol: str, est_date: str) -> None:
    api_key = get_massive_key()
    if not api_key:
        st.error("Missing MASSIVE_KEY in Streamlit secrets.")
        st.stop()
        return

    timeframe_label = st.session_state.get(f"{symbol}_timeframe", "1 Min")
    multiplier, timespan = TIMEFRAME_OPTIONS[timeframe_label]

    try:
        data = fetch_intraday_bars(
            symbol=symbol,
            api_key=api_key,
            date_str=est_date,
            multiplier=multiplier,
            timespan=timespan,
        )
    except requests.HTTPError as exc:
        st.error(f"Failed to fetch {symbol} data from Polygon/Massive: {exc}")
        st.stop()
        return

    if not data:
        st.warning(f"No {timeframe_label} data available yet for {symbol} on {est_date} (EST).")
        return

    candle_data = []
    for row in data:
        is_regular = row["session"] == "regular"
        up = row["close"] >= row["open"]
        candle_data.append(
            {
                "time": row["time"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "color": "#26a69a" if (is_regular and up) else "#7dd1c9" if up else "#ef5350" if is_regular else "#f3a4aa",
                "wickColor": "#26a69a" if (is_regular and up) else "#7dd1c9" if up else "#ef5350" if is_regular else "#f3a4aa",
            }
        )

    ema_payload = {
        f"ema_{length}": _ema(data, length)
        for length in EMA_OPTIONS
        if st.session_state.get(f"{symbol}_ema_{length}", False)
    }
    vwap_payload = _vwap(data) if st.session_state.get(f"{symbol}_vwap", False) else []

    last_candle_est = datetime.fromtimestamp(data[-1]["time"], tz=EST)
    st.caption(
        "Source: Polygon/Massive • Pull interval: every 5 seconds • "
        f"Timeframe: {timeframe_label} • "
        f"Last candle: {last_candle_est.strftime('%Y-%m-%d %I:%M:%S %p EST')} • "
        "Session-aware candles: regular session is vivid; extended hours are muted"
    )

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
        timeScale: {{ borderColor: '#485c7b', timeVisible: true, secondsVisible: false }},
        localization: {{
          locale: 'en-US',
          timeFormatter: (time) => new Intl.DateTimeFormat('en-US', {{
            timeZone: 'America/New_York',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
          }}).format(new Date(time * 1000)),
        }}
      }});

      const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {{
        borderVisible: false,
      }});
      candleSeries.setData({candle_data});

      const emaPayload = {ema_payload};
      const emaColors = {{ ema_9: '#00d1ff', ema_21: '#f7b500', ema_50: '#d86bff' }};
      Object.entries(emaPayload).forEach(([key, points]) => {{
        const series = chart.addSeries(LightweightCharts.LineSeries, {{
          color: emaColors[key] || '#bbbbbb',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: key.toUpperCase(),
        }});
        series.setData(points);
      }});

      const vwapData = {vwap_payload};
      if (vwapData.length) {{
        const vwapSeries = chart.addSeries(LightweightCharts.LineSeries, {{
          color: '#ffffff',
          lineWidth: 2,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'VWAP',
        }});
        vwapSeries.setData(vwapData);
      }}

      chart.timeScale().fitContent();
    </script>
    """

    components.html(chart_html, height=480)


@st.fragment(run_every="5s")
def _autorefresh_chart(symbol: str, est_date: str) -> None:
    _render_chart(symbol=symbol, est_date=est_date)


def render_lightweight_chart(symbol: str, title: str) -> None:
    make_sidebar()

    if not st.session_state.get("logged_in", False):
        st.error("Unauthorized. Please log in from the main page.")
        st.page_link("streamlit_app.py", label="Go to Home")
        st.stop()

    st.title(title)

    if f"{symbol}_timeframe" not in st.session_state:
        st.session_state[f"{symbol}_timeframe"] = "1 Min"

    st.subheader("Timeframe")
    tf_cols = st.columns(3)
    for idx, label in enumerate(TIMEFRAME_OPTIONS.keys()):
        if tf_cols[idx].button(label, key=f"{symbol}_tf_{label}", use_container_width=True):
            st.session_state[f"{symbol}_timeframe"] = label

    st.subheader("Indicators")
    indicator_cols = st.columns(4)
    for idx, length in enumerate(EMA_OPTIONS):
        with indicator_cols[idx]:
            _toggle_button(f"EMA {length}", key=f"{symbol}_ema_{length}")
    with indicator_cols[3]:
        _toggle_button("VWAP", key=f"{symbol}_vwap")

    active_emas = [str(length) for length in EMA_OPTIONS if st.session_state.get(f"{symbol}_ema_{length}", False)]
    st.caption(
        f"Active indicators → EMAs: {', '.join(active_emas) if active_emas else 'None'} | "
        f"VWAP: {'On' if st.session_state.get(f'{symbol}_vwap', False) else 'Off'}"
    )

    est_now = datetime.now(EST)
    est_date = est_now.strftime("%Y-%m-%d")

    _autorefresh_chart(symbol=symbol, est_date=est_date)
