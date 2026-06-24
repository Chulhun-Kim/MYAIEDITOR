# app_stock.py
# ------------------------------------------------------------
# 장전 주식 분석 시스템 - FinanceDataReader 안정화 버전
# - pykrx/KRX 로그인 없이 동작하는 1차 버전
# - 한국 종목: FinanceDataReader 가격/거래량 기반 분석
# - 해외 지표: FinanceDataReader 참고 지표
# - app_editor.py의 Workspace / Buffer 반영 구조와 호환
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import datetime as dt
import math
import re

import pandas as pd
import streamlit as st

try:
    import FinanceDataReader as fdr
except Exception:
    fdr = None


# ============================================================
# 기본 종목군
# ============================================================
DEFAULT_KOSPI_TICKERS: Dict[str, str] = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "005380": "현대차",
    "000270": "기아",
    "207940": "삼성바이오로직스",
    "068270": "셀트리온",
    "005490": "POSCO홀딩스",
    "035420": "NAVER",
    "035720": "카카오",
    "105560": "KB금융",
    "055550": "신한지주",
    "012330": "현대모비스",
    "028260": "삼성물산",
    "066570": "LG전자",
    "096770": "SK이노베이션",
    "051910": "LG화학",
    "003670": "포스코퓨처엠",
    "032830": "삼성생명",
    "086790": "하나금융지주",
}

DEFAULT_KOSDAQ_TICKERS: Dict[str, str] = {
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "091990": "셀트리온헬스케어",
    "028300": "HLB",
    "196170": "알테오젠",
    "277810": "레인보우로보틱스",
    "035900": "JYP Ent.",
    "041510": "에스엠",
    "112040": "위메이드",
    "293490": "카카오게임즈",
    "058470": "리노공업",
    "039030": "이오테크닉스",
    "403870": "HPSP",
    "214150": "클래시스",
    "263750": "펄어비스",
}

GLOBAL_INDICATORS = [
    ("나스닥", "IXIC"),
    ("S&P500", "US500"),
    ("다우존스", "DJI"),
    ("달러/원", "USD/KRW"),
]


# ============================================================
# 데이터 구조
# ============================================================
@dataclass
class StockPick:
    ticker: str
    name: str
    market: str
    direction: str
    score: float
    close: float
    change_rate: float
    volume: int
    volume_ratio: float
    trading_value: float
    date: str
    reasons: List[str]


# ============================================================
# 유틸
# ============================================================
def _now_iso() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean_text(s: str) -> str:
    s = str(s or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _fmt_num(n: float) -> str:
    try:
        return f"{int(float(n)):,}"
    except Exception:
        return str(n)


def _fmt_pct(x: float) -> str:
    try:
        return f"{float(x):+.2f}%"
    except Exception:
        return str(x)


def _fmt_ratio(x: float) -> str:
    try:
        if float(x) <= 0:
            return "-"
        return f"{float(x):.2f}배"
    except Exception:
        return "-"


def _safe_float(v, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _safe_int(v, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def _require_fdr() -> None:
    if fdr is None:
        raise RuntimeError("FinanceDataReader가 설치되어 있지 않습니다. requirements.txt에 finance-datareader를 추가하세요.")


# ============================================================
# 종목 목록
# ============================================================
def parse_custom_tickers(text: str) -> Dict[str, str]:
    """
    입력 예:
    005930 삼성전자
    000660,SK하이닉스
    035420
    """
    out: Dict[str, str] = {}
    for line in str(text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"[,\s]+", line, maxsplit=1)
        ticker = re.sub(r"\D", "", parts[0]).zfill(6)
        name = parts[1].strip() if len(parts) > 1 else ticker
        if len(ticker) == 6:
            out[ticker] = name
    return out


def get_target_tickers(markets: List[str], mode: str, custom_text: str) -> Dict[str, Dict[str, str]]:
    targets: Dict[str, Dict[str, str]] = {}

    if mode == "직접 입력":
        custom = parse_custom_tickers(custom_text)
        if custom:
            targets["사용자입력"] = custom
        return targets

    if "KOSPI" in markets:
        targets["KOSPI"] = DEFAULT_KOSPI_TICKERS.copy()
    if "KOSDAQ" in markets:
        targets["KOSDAQ"] = DEFAULT_KOSDAQ_TICKERS.copy()

    return targets


# ============================================================
# FinanceDataReader 수집
# ============================================================
def fetch_price_frame(ticker: str, days: int = 20) -> pd.DataFrame:
    _require_fdr()
    end = dt.date.today()
    start = end - dt.timedelta(days=days + 20)
    df = fdr.DataReader(ticker, start, end)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.dropna().copy()
    return df


def analyze_one_stock(ticker: str, name: str, market: str) -> Optional[Dict]:
    try:
        df = fetch_price_frame(ticker, days=20)
        if df is None or df.empty or len(df) < 2:
            return None

        df = df.tail(10).copy()
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = _safe_float(latest.get("Close"))
        prev_close = _safe_float(prev.get("Close"))
        volume = _safe_int(latest.get("Volume"))
        prev_volume = _safe_int(prev.get("Volume"))

        if close <= 0 or prev_close <= 0 or volume <= 0:
            return None

        change_rate = (close - prev_close) / prev_close * 100
        volume_ratio = volume / prev_volume if prev_volume > 0 else 0
        trading_value = close * volume
        date = str(df.index[-1].date())

        return {
            "ticker": ticker,
            "name": name,
            "market": market,
            "close": close,
            "change_rate": change_rate,
            "volume": volume,
            "volume_ratio": volume_ratio,
            "trading_value": trading_value,
            "date": date,
        }
    except Exception:
        return None


def fetch_global_indicators(days: int = 7) -> List[Dict]:
    if fdr is None:
        return []

    end = dt.date.today()
    start = end - dt.timedelta(days=days + 10)
    out: List[Dict] = []

    for name, symbol in GLOBAL_INDICATORS:
        try:
            df = fdr.DataReader(symbol, start, end)
            if df is None or df.empty or "Close" not in df.columns or len(df.dropna()) < 2:
                continue
            df = df.dropna()
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg = (last - prev) / prev * 100 if prev else 0
            out.append({"name": name, "symbol": symbol, "last": last, "change_rate": chg, "date": str(df.index[-1].date())})
        except Exception:
            continue

    return out


# ============================================================
# 점수화
# ============================================================
def make_reasons(item: Dict, direction: str) -> List[str]:
    pct = _safe_float(item.get("change_rate"))
    vr = _safe_float(item.get("volume_ratio"))
    tv = _safe_float(item.get("trading_value"))

    reasons: List[str] = []

    if direction == "상승 관심":
        if pct > 0:
            reasons.append(f"최근 거래일 등락률이 {_fmt_pct(pct)}로 상승 마감")
        if vr >= 2:
            reasons.append(f"거래량이 직전 거래일 대비 {_fmt_ratio(vr)} 수준으로 증가")
        elif vr >= 1.3:
            reasons.append("거래량이 직전 거래일보다 증가")
        if tv >= 50_000_000_000:
            reasons.append(f"거래대금이 약 {_fmt_num(tv)}원으로 시장 관심 확대")
        reasons.append("가격 흐름과 거래량을 함께 고려한 장전 관심 종목")
    else:
        if pct < 0:
            reasons.append(f"최근 거래일 등락률이 {_fmt_pct(pct)}로 하락 마감")
        if vr >= 1.5:
            reasons.append(f"변동 과정에서 거래량이 {_fmt_ratio(vr)}로 증가")
        if pct >= 7:
            reasons.append("최근 거래일 급등에 따른 단기 과열 가능성")
        if tv >= 50_000_000_000:
            reasons.append(f"거래대금이 약 {_fmt_num(tv)}원으로 변동성 확대 가능성")
        reasons.append("장전 변동성 주의 종목")

    return reasons[:4]


def score_items(items: List[Dict], min_trading_value: int, min_volume_ratio: float, top_n: int) -> Tuple[List[StockPick], List[StockPick]]:
    up: List[StockPick] = []
    down: List[StockPick] = []

    for it in items:
        pct = _safe_float(it.get("change_rate"))
        vr = _safe_float(it.get("volume_ratio"))
        tv = _safe_float(it.get("trading_value"))

        if tv < min_trading_value:
            continue

        up_score = 50 + max(min(pct, 10), -10) * 3.0 + min(max(vr, 0), 5) * 8.0 + min(math.log10(max(tv, 1)) * 3, 35)
        down_score = 50 + max(min(-pct, 10), -10) * 3.5 + min(max(vr, 0), 5) * 7.0 + min(math.log10(max(tv, 1)) * 2.5, 30)

        if pct > 0 and vr >= min_volume_ratio:
            up.append(
                StockPick(
                    ticker=it["ticker"], name=it["name"], market=it["market"], direction="상승 관심",
                    score=round(up_score, 1), close=it["close"], change_rate=round(pct, 2),
                    volume=it["volume"], volume_ratio=round(vr, 2), trading_value=tv,
                    date=it["date"], reasons=make_reasons(it, "상승 관심")
                )
            )

        if (pct < 0 and vr >= max(1.0, min_volume_ratio - 0.3)) or (pct >= 7 and vr >= 1.5):
            down.append(
                StockPick(
                    ticker=it["ticker"], name=it["name"], market=it["market"], direction="하락 주의",
                    score=round(down_score, 1), close=it["close"], change_rate=round(pct, 2),
                    volume=it["volume"], volume_ratio=round(vr, 2), trading_value=tv,
                    date=it["date"], reasons=make_reasons(it, "하락 주의")
                )
            )

    up = sorted(up, key=lambda x: x.score, reverse=True)[:top_n]
    down = sorted(down, key=lambda x: x.score, reverse=True)[:top_n]
    return up, down


# ============================================================
# 출력 변환
# ============================================================
def picks_to_dataframe(picks: List[StockPick]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "구분": p.direction,
            "시장": p.market,
            "종목코드": p.ticker,
            "종목명": p.name,
            "점수": p.score,
            "기준일": p.date,
            "종가": round(p.close, 0),
            "등락률": p.change_rate,
            "거래량": p.volume,
            "거래량배율": p.volume_ratio,
            "거래대금": round(p.trading_value, 0),
            "근거": " / ".join(p.reasons),
        }
        for p in picks
    ])


def build_market_brief(indicators: List[Dict]) -> str:
    if not indicators:
        return "- 해외 참고 지표를 가져오지 못했습니다."
    return "\n".join([
        f"- {it['name']}({it['symbol']}): {it['last']:.2f}, 전일 대비 {_fmt_pct(it['change_rate'])} ({it['date']})"
        for it in indicators
    ])


def build_workspace_text(markets: List[str], up_picks: List[StockPick], down_picks: List[StockPick], indicators: List[Dict], target_count: int) -> str:
    dates = sorted({p.date for p in up_picks + down_picks})
    latest_date = dates[-1] if dates else dt.date.today().isoformat()

    today = dt.date.today().strftime("%Y-%m-%d")

    lines: List[str] = []
    lines.append("# 장전 주식 분석")
    lines.append(f"- 브리핑 기준시각: {today} 07:00")
    lines.append(f"- 국내시장 가격 기준일: {latest_date}")
    lines.append(f"- 실제 분석시각: {_now_iso()}")
    lines.append(f"- 분석 시장: {', '.join(markets) if markets else '사용자 입력'}")
    lines.append(f"- 분석 대상 종목 수: {target_count}개")
    lines.append("- 데이터 소스: FinanceDataReader")
    lines.append("")

    lines.append("## 상승 관심 종목")
    if not up_picks:
        lines.append("- 조건에 맞는 상승 관심 종목이 없습니다.")
    else:
        for i, p in enumerate(up_picks, start=1):
            lines.append(f"### {i}. {p.name}({p.ticker}) / {p.market} / {p.score}점")
            lines.append(f"- 기준일: {p.date}")
            lines.append(f"- 종가: {_fmt_num(p.close)}원")
            lines.append(f"- 등락률: {_fmt_pct(p.change_rate)}")
            lines.append(f"- 거래량: {_fmt_num(p.volume)}주")
            lines.append(f"- 거래량 배율: {_fmt_ratio(p.volume_ratio)}")
            lines.append(f"- 거래대금: 약 {_fmt_num(p.trading_value)}원")
            for r in p.reasons:
                lines.append(f"- {r}")
            lines.append("")
    lines.append("## 하락 주의 종목")
    if not down_picks:
        lines.append("- 조건에 맞는 하락 주의 종목이 없습니다.")
    else:
        for i, p in enumerate(down_picks, start=1):
            lines.append(f"### {i}. {p.name}({p.ticker}) / {p.market} / {p.score}점")
            lines.append(f"- 기준일: {p.date}")
            lines.append(f"- 종가: {_fmt_num(p.close)}원")
            lines.append(f"- 등락률: {_fmt_pct(p.change_rate)}")
            lines.append(f"- 거래량: {_fmt_num(p.volume)}주")
            lines.append(f"- 거래량 배율: {_fmt_ratio(p.volume_ratio)}")
            lines.append(f"- 거래대금: 약 {_fmt_num(p.trading_value)}원")
            for r in p.reasons:
                lines.append(f"- {r}")
            lines.append("")
    lines.append("## 유의사항")
    lines.append("- 본 분석은 공개 가격·거래량 데이터를 바탕으로 한 장전 참고 자료입니다.")
    lines.append("- 투자 권유나 매매 추천이 아닙니다.")
    lines.append("- 이 안정화 버전은 pykrx 수급 데이터를 사용하지 않으며, 외국인·기관 수급 분석은 추후 KRX 인증 문제 해결 뒤 추가할 수 있습니다.")
    return "\n".join(lines).strip() + "\n"


def build_buffer_items(ws_text: str, up_picks: List[StockPick], down_picks: List[StockPick], indicators: List[Dict]) -> List[Dict]:
    dates = sorted({p.date for p in up_picks + down_picks})
    latest_date = dates[-1] if dates else dt.date.today().isoformat()
    return [
        {
            "type": "stock_preopen_analysis",
            "title": f"장전 주식 분석 {latest_date}",
            "text": ws_text,
            "meta": {
                "source": "FinanceDataReader",
                "published": latest_date,
                "fetched_at": _now_iso(),
                "up_count": len(up_picks),
                "down_count": len(down_picks),
                "indicators": indicators,
                "raw": {
                    "up_picks": [asdict(p) for p in up_picks],
                    "down_picks": [asdict(p) for p in down_picks],
                },
            },
        }
    ]


# ============================================================
# 캐시
# ============================================================
def _init_stock_cache() -> None:
    if "stock_last_ws_text" not in st.session_state:
        st.session_state.stock_last_ws_text = None
    if "stock_last_buffer" not in st.session_state:
        st.session_state.stock_last_buffer = []
    if "stock_last_info" not in st.session_state:
        st.session_state.stock_last_info = ""
    if "stock_last_up_df" not in st.session_state:
        st.session_state.stock_last_up_df = pd.DataFrame()
    if "stock_last_down_df" not in st.session_state:
        st.session_state.stock_last_down_df = pd.DataFrame()
    if "stock_last_indicators" not in st.session_state:
        st.session_state.stock_last_indicators = []


def clear_stock_cache() -> None:
    st.session_state.stock_last_ws_text = None
    st.session_state.stock_last_buffer = []
    st.session_state.stock_last_info = ""
    st.session_state.stock_last_up_df = pd.DataFrame()
    st.session_state.stock_last_down_df = pd.DataFrame()
    st.session_state.stock_last_indicators = []


# ============================================================
# Streamlit UI
# ============================================================
def render_stock_panel() -> Tuple[Optional[str], List[Dict]]:
    st.subheader("📈 장전 주식 분석 시스템")
    _init_stock_cache()

    if fdr is None:
        st.error("FinanceDataReader가 설치되어 있지 않습니다. requirements.txt에 `finance-datareader`를 추가하세요.")
        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

    top = st.columns([1.2, 1.2, 1, 1])

    with top[0]:
        mode = st.selectbox("분석 방식", ["대표 종목", "직접 입력"], index=0, key="stock_mode")

    with top[1]:
        markets = st.multiselect("분석 시장", ["KOSPI", "KOSDAQ"], default=["KOSPI", "KOSDAQ"], key="stock_markets")

    with top[2]:
        top_n = st.number_input("표시 종목 수", min_value=3, max_value=30, value=10, step=1, key="stock_top_n")

    with top[3]:
        if st.button("캐시 비우기", use_container_width=True, key="stock_clear_cache"):
            clear_stock_cache()
            st.success("Stock 캐시를 비웠습니다.")
            st.rerun()

    opt = st.columns([1, 1, 1])

    with opt[0]:
        min_trading_value_100m = st.number_input("최소 거래대금(억원)", min_value=1, max_value=5000, value=50, step=10, key="stock_min_trading_value_100m")

    with opt[1]:
        min_volume_ratio = st.slider("최소 거래량 배율", min_value=1.0, max_value=5.0, value=1.3, step=0.1, key="stock_min_volume_ratio")

    with opt[2]:
        use_global = st.checkbox("해외 지표 포함", value=True, key="stock_use_global")

    custom_text = ""
    if mode == "직접 입력":
        custom_text = st.text_area(
            "분석할 종목 입력",
            value="005930 삼성전자\n000660 SK하이닉스\n035420 NAVER",
            height=120,
            key="stock_custom_text",
            help="한 줄에 하나씩 입력하세요. 예: 005930 삼성전자",
        )

    st.caption(
        "이 버전은 FinanceDataReader 기반 안정화 버전입니다. 가격·거래량·거래대금 기준으로 장전 관심 종목을 선별합니다. "
        "pykrx 기반 외국인·기관 수급 분석은 추후 KRX 인증 문제 해결 뒤 추가합니다."
    )

    do_run = st.button("장전 분석 실행", use_container_width=True, key="stock_run")

    if not do_run:
        if st.session_state.stock_last_info:
            st.success(st.session_state.stock_last_info)
            if st.session_state.stock_last_indicators:
                with st.expander("해외시장 참고 지표", expanded=False):
                    st.dataframe(pd.DataFrame(st.session_state.stock_last_indicators), use_container_width=True, hide_index=True)
            if not st.session_state.stock_last_up_df.empty:
                with st.expander("상승 관심 종목 미리보기", expanded=True):
                    st.dataframe(st.session_state.stock_last_up_df, use_container_width=True, hide_index=True)
            if not st.session_state.stock_last_down_df.empty:
                with st.expander("하락 주의 종목 미리보기", expanded=True):
                    st.dataframe(st.session_state.stock_last_down_df, use_container_width=True, hide_index=True)
        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

    try:
        targets = get_target_tickers(markets, mode, custom_text)
        target_count = sum(len(v) for v in targets.values())

        if target_count == 0:
            st.error("분석할 종목이 없습니다. 시장을 선택하거나 직접 종목을 입력하세요.")
            return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

        items: List[Dict] = []
        progress = st.progress(0)
        done = 0

        with st.spinner("FinanceDataReader로 종목 가격·거래량 데이터를 수집 중입니다..."):
            for market, ticker_map in targets.items():
                for ticker, name in ticker_map.items():
                    item = analyze_one_stock(ticker, name, market)
                    if item:
                        items.append(item)
                    done += 1
                    progress.progress(min(done / target_count, 1.0))

        progress.empty()

        if not items:
            st.error("분석 가능한 종목 데이터를 가져오지 못했습니다. 네트워크 상태나 종목코드를 확인하세요.")
            return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

        min_trading_value = int(min_trading_value_100m) * 100_000_000
        up_picks, down_picks = score_items(items, min_trading_value, float(min_volume_ratio), int(top_n))

        indicators: List[Dict] = []
        if use_global:
            with st.spinner("해외 참고 지표를 확인 중입니다..."):
                indicators = fetch_global_indicators()

        ws_text = build_workspace_text(markets, up_picks, down_picks, indicators, target_count)
        buffer_items = build_buffer_items(ws_text, up_picks, down_picks, indicators)
        up_df = picks_to_dataframe(up_picks)
        down_df = picks_to_dataframe(down_picks)

        st.session_state.stock_last_ws_text = ws_text
        st.session_state.stock_last_buffer = buffer_items
        st.session_state.stock_last_up_df = up_df
        st.session_state.stock_last_down_df = down_df
        st.session_state.stock_last_indicators = indicators
        st.session_state.stock_last_info = f"장전 주식 분석 완료: 분석 대상 {target_count}개 / 상승 관심 {len(up_picks)}개 / 하락 주의 {len(down_picks)}개 / 생성 {_now_iso()}"

        st.success(st.session_state.stock_last_info)

        if indicators:
            with st.expander("해외시장 참고 지표", expanded=True):
                st.dataframe(pd.DataFrame(indicators), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 상승 관심 종목")
            if up_df.empty:
                st.info("조건에 맞는 상승 관심 종목이 없습니다.")
            else:
                st.dataframe(up_df, use_container_width=True, hide_index=True)
        with c2:
            st.markdown("### 하락 주의 종목")
            if down_df.empty:
                st.info("조건에 맞는 하락 주의 종목이 없습니다.")
            else:
                st.dataframe(down_df, use_container_width=True, hide_index=True)

        with st.expander("Workspace 반영용 텍스트 미리보기", expanded=False):
            st.text_area("분석 결과", value=ws_text, height=360, disabled=True, key="stock_ws_preview")

        return ws_text, buffer_items

    except Exception as e:
        st.error(
            "장전 주식 분석 실패:\n"
            f"- {e}\n\n"
            "체크 포인트:\n"
            "- requirements.txt에 finance-datareader가 들어 있는지 확인\n"
            "- 로컬에서 `python -c \"import FinanceDataReader as fdr; print('OK')\"` 확인\n"
            "- 네트워크 또는 FinanceDataReader 데이터 소스 장애 여부 확인\n"
            "- 종목코드가 6자리인지 확인"
        )
        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer
