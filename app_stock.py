# app_stock.py
# ------------------------------------------------------------
# 장전 주식 분석 시스템 3차 버전
# - FinanceDataReader: 국내 종목 가격/거래량 + 해외 지표
# - NewsAPI: 장전 뉴스 수집
# - OpenAI: 장전 매매 후보 해석
# - Streamlit Cloud 대응
# - app_editor.py의 Workspace / Buffer 반영 구조와 호환
# ------------------------------------------------------------

from __future__ import annotations

from zoneinfo import ZoneInfo
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import datetime as dt
import math
import os
import re

import pandas as pd
import streamlit as st

try:
    import requests
except Exception:
    requests = None

try:
    import FinanceDataReader as fdr
except Exception:
    fdr = None

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    OpenAI = None
    HAS_OPENAI = False


# ============================================================
# 기본 설정
# ============================================================
NEWSAPI_BASE = "https://newsapi.org/v2/everything"

DEFAULT_NEWS_QUERY = (
    "반도체 OR AI OR 엔비디아 OR HBM OR "
    "방산 OR 조선 OR 원전 OR 2차전지 OR 바이오 OR "
    "한국증시 OR 코스피 OR 환율 OR 금리"
)

DEFAULT_STOCKS: List[Tuple[str, str, str]] = [
    # 반도체 / AI
    ("005930", "삼성전자", "KOSPI"),
    ("000660", "SK하이닉스", "KOSPI"),
    ("042700", "한미반도체", "KOSPI"),
    ("058470", "리노공업", "KOSDAQ"),
    ("095340", "ISC", "KOSDAQ"),
    ("036930", "주성엔지니어링", "KOSDAQ"),
    ("240810", "원익IPS", "KOSDAQ"),
    ("108320", "LX세미콘", "KOSPI"),
    # 2차전지
    ("373220", "LG에너지솔루션", "KOSPI"),
    ("006400", "삼성SDI", "KOSPI"),
    ("247540", "에코프로비엠", "KOSDAQ"),
    ("086520", "에코프로", "KOSDAQ"),
    ("003670", "포스코퓨처엠", "KOSPI"),
    ("051910", "LG화학", "KOSPI"),
    # 방산 / 조선 / 원전
    ("012450", "한화에어로스페이스", "KOSPI"),
    ("079550", "LIG넥스원", "KOSPI"),
    ("064350", "현대로템", "KOSPI"),
    ("329180", "HD현대중공업", "KOSPI"),
    ("010140", "삼성중공업", "KOSPI"),
    ("009540", "HD한국조선해양", "KOSPI"),
    ("034020", "두산에너빌리티", "KOSPI"),
    ("052690", "한전기술", "KOSPI"),
    # 자동차 / 인터넷 / 바이오 / 금융
    ("005380", "현대차", "KOSPI"),
    ("000270", "기아", "KOSPI"),
    ("035420", "NAVER", "KOSPI"),
    ("035720", "카카오", "KOSPI"),
    ("068270", "셀트리온", "KOSPI"),
    ("207940", "삼성바이오로직스", "KOSPI"),
    ("105560", "KB금융", "KOSPI"),
    ("055550", "신한지주", "KOSPI"),
]


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
    trading_value_est: float
    news_hits: int
    reasons: List[str]


@dataclass
class NewsItem:
    title: str
    url: str
    published: str
    source: str
    description: str
    content: str


# ============================================================
# 유틸
# ============================================================
def _now_kst() -> dt.datetime:
    return dt.datetime.now(ZoneInfo("Asia/Seoul"))


def _now_iso() -> str:
    return _now_kst().strftime("%Y-%m-%d %H:%M:%S")


def _today_str() -> str:
    return _now_kst().strftime("%Y-%m-%d")


def _today_kst_date() -> dt.date:
    return _now_kst().date()


def _clean(s: Any) -> str:
    s = str(s or "")
    return re.sub(r"\s+", " ", s).strip()


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        if pd.isna(v):
            return default
        return int(float(v))
    except Exception:
        return default


def _fmt_num(n: float) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def _fmt_ratio(x: float) -> str:
    if x <= 0:
        return "-"
    return f"{x:.2f}배"


def _normalize_ticker(ticker: str) -> str:
    return str(ticker or "").strip().zfill(6)


def get_secret_or_env(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key, "")
    except Exception:
        value = ""
    return str(value or os.getenv(key, default) or "").strip()


# ============================================================
# FinanceDataReader 데이터
# ============================================================
def _require_fdr() -> None:
    if fdr is None:
        raise RuntimeError("FinanceDataReader가 설치되어 있지 않습니다. requirements.txt에 finance-datareader를 추가하세요.")


def fetch_stock_history(ticker: str, days: int = 45) -> Optional[pd.DataFrame]:
    _require_fdr()
    end = _today_kst_date()
    start = end - dt.timedelta(days=days)
    ticker = _normalize_ticker(ticker)

    try:
        df = fdr.DataReader(ticker, start, end)
        if df is None or df.empty:
            return None
        df = df.dropna().copy()
        return df
    except Exception:
        return None


def analyze_one_stock(ticker: str, name: str, market: str, news_items: List[NewsItem]) -> Optional[Dict[str, Any]]:
    df = fetch_stock_history(ticker)
    if df is None or len(df) < 3:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = _safe_float(last.get("Close"))
    prev_close = _safe_float(prev.get("Close"))
    volume = _safe_int(last.get("Volume"))
    prev_volume = _safe_int(prev.get("Volume"))

    if close <= 0 or prev_close <= 0:
        return None

    change_rate = (close - prev_close) / prev_close * 100
    volume_ratio = volume / prev_volume if prev_volume > 0 else 0
    trading_value_est = close * volume

    ma5 = _safe_float(df["Close"].tail(5).mean()) if "Close" in df.columns else 0
    ma20 = _safe_float(df["Close"].tail(20).mean()) if len(df) >= 20 and "Close" in df.columns else ma5

    news_hits = count_news_hits(name, ticker, news_items)

    return {
        "ticker": ticker,
        "name": name,
        "market": market,
        "date": str(df.index[-1].date()),
        "close": close,
        "change_rate": change_rate,
        "volume": volume,
        "volume_ratio": volume_ratio,
        "trading_value_est": trading_value_est,
        "ma5": ma5,
        "ma20": ma20,
        "news_hits": news_hits,
    }


def fetch_global_indicators(days: int = 10) -> List[Dict[str, Any]]:
    if fdr is None:
        return []

    end = _today_kst_date()
    start = end - dt.timedelta(days=days + 5)

    candidates = [
        ("나스닥", "IXIC"),
        ("S&P500", "US500"),
        ("다우존스", "DJI"),
        ("달러/원", "USD/KRW"),
    ]

    out: List[Dict[str, Any]] = []

    for name, symbol in candidates:
        try:
            df = fdr.DataReader(symbol, start, end)
            if df is None or df.empty or "Close" not in df.columns:
                continue
            df = df.dropna()
            if len(df) < 2:
                continue
            last = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2])
            chg = (last - prev) / prev * 100 if prev else 0
            out.append({"name": name, "symbol": symbol, "last": last, "change_rate": chg, "date": str(df.index[-1].date())})
        except Exception:
            continue

    return out


# ============================================================
# NewsAPI
# ============================================================
def fetch_newsapi_items(api_key: str, query: str, limit: int = 20, days_back: int = 2) -> List[NewsItem]:
    if requests is None:
        raise RuntimeError("requests가 설치되어 있지 않습니다.")

    api_key = (api_key or "").strip()
    if not api_key:
        return []

    today = _today_kst_date()
    from_date = today - dt.timedelta(days=int(days_back))

    params = {
        "q": query.strip(),
        "language": "ko",
        "sortBy": "publishedAt",
        "pageSize": int(limit),
        "from": from_date.isoformat(),
        "to": today.isoformat(),
    }
    headers = {"X-Api-Key": api_key}

    resp = requests.get(NEWSAPI_BASE, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    if payload.get("status") != "ok":
        return []

    out: List[NewsItem] = []
    for a in (payload.get("articles") or [])[: int(limit)]:
        src = a.get("source") or {}
        out.append(
            NewsItem(
                title=_clean(a.get("title")),
                url=_clean(a.get("url")),
                published=_clean(a.get("publishedAt")),
                source=_clean(src.get("name")),
                description=_clean(a.get("description")),
                content=_clean(a.get("content")),
            )
        )
    return out


def count_news_hits(name: str, ticker: str, news_items: List[NewsItem]) -> int:
    name = _clean(name)
    if not name:
        return 0
    count = 0
    for it in news_items:
        text = f"{it.title} {it.description} {it.content}"
        if name in text:
            count += 1
    return count


def build_news_keywords_summary(news_items: List[NewsItem]) -> List[str]:
    keywords = [
        "반도체", "AI", "엔비디아", "HBM", "삼성전자", "SK하이닉스",
        "방산", "조선", "원전", "2차전지", "바이오", "환율", "금리", "코스피",
        "유가", "중동", "관세", "수출", "실적", "수주",
    ]
    text = " ".join([f"{n.title} {n.description} {n.content}" for n in news_items])
    found = []
    for k in keywords:
        c = text.count(k)
        if c > 0:
            found.append((k, c))
    found.sort(key=lambda x: x[1], reverse=True)
    return [f"{k}({c})" for k, c in found[:10]]


# ============================================================
# 점수화
# ============================================================
def make_candidate_reasons(row: Dict[str, Any], news_items: List[NewsItem]) -> List[str]:
    reasons: List[str] = []
    change_rate = _safe_float(row.get("change_rate"))
    volume_ratio = _safe_float(row.get("volume_ratio"))
    trading_value = _safe_float(row.get("trading_value_est"))
    ma5 = _safe_float(row.get("ma5"))
    ma20 = _safe_float(row.get("ma20"))
    news_hits = _safe_int(row.get("news_hits"))

    if change_rate > 0:
        reasons.append(f"직전 거래일 등락률 {_fmt_pct(change_rate)}")
    elif change_rate < 0:
        reasons.append(f"직전 거래일 조정({_fmt_pct(change_rate)}) 후 반등 여부 확인")

    if volume_ratio >= 2:
        reasons.append(f"거래량이 직전 거래일 대비 {_fmt_ratio(volume_ratio)}로 급증")
    elif volume_ratio >= 1.3:
        reasons.append(f"거래량이 직전 거래일 대비 {_fmt_ratio(volume_ratio)}로 증가")

    if ma5 > ma20 and ma20 > 0:
        reasons.append("5일 평균가격이 20일 평균가격을 상회")

    if trading_value >= 100_000_000_000:
        reasons.append(f"추정 거래대금 {_fmt_num(trading_value)}원으로 유동성 양호")

    if news_hits > 0:
        reasons.append(f"최근 뉴스에서 종목명 직접 언급 {news_hits}건")

    if not reasons:
        reasons.append("가격·거래량·뉴스 흐름을 종합해 장전 점검 필요")

    return reasons[:5]


def make_risk_reasons(row: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    change_rate = _safe_float(row.get("change_rate"))
    volume_ratio = _safe_float(row.get("volume_ratio"))
    trading_value = _safe_float(row.get("trading_value_est"))

    if change_rate <= -3:
        reasons.append(f"직전 거래일 하락폭 확대({_fmt_pct(change_rate)})")
    if change_rate >= 8:
        reasons.append(f"직전 거래일 급등({_fmt_pct(change_rate)})에 따른 단기 과열 가능성")
    if volume_ratio >= 2:
        reasons.append(f"거래량이 {_fmt_ratio(volume_ratio)}로 확대돼 변동성 주의")
    if trading_value >= 100_000_000_000:
        reasons.append("거래대금이 커 장중 변동성 확대 가능성")
    if not reasons:
        reasons.append("단기 변동성 확인 필요")
    return reasons[:4]


def score_candidates(rows: List[Dict[str, Any]], top_n: int = 10) -> Tuple[List[StockPick], List[StockPick]]:
    candidates: List[StockPick] = []
    risks: List[StockPick] = []

    for r in rows:
        change_rate = _safe_float(r.get("change_rate"))
        volume_ratio = _safe_float(r.get("volume_ratio"))
        trading_value = _safe_float(r.get("trading_value_est"))
        ma5 = _safe_float(r.get("ma5"))
        ma20 = _safe_float(r.get("ma20"))
        news_hits = _safe_int(r.get("news_hits"))

        momentum_score = max(min(change_rate, 10), -10) * 2.5
        volume_score = min(volume_ratio, 5) * 7.0
        liquidity_score = min(math.log10(max(trading_value, 1)) * 2.2, 30)
        trend_score = 8 if ma5 > ma20 and ma20 > 0 else 0
        news_score = min(news_hits * 8, 24)

        buy_score = 45 + momentum_score + volume_score + liquidity_score + trend_score + news_score

        if volume_ratio >= 1.2 or news_hits > 0 or change_rate > 1:
            candidates.append(
                StockPick(
                    ticker=str(r.get("ticker")),
                    name=str(r.get("name")),
                    market=str(r.get("market")),
                    direction="매매 관심",
                    score=round(buy_score, 1),
                    close=round(_safe_float(r.get("close")), 2),
                    change_rate=round(change_rate, 2),
                    volume=_safe_int(r.get("volume")),
                    volume_ratio=round(volume_ratio, 2),
                    trading_value_est=round(trading_value, 0),
                    news_hits=news_hits,
                    reasons=make_candidate_reasons(r, []),
                )
            )

        risk_score = 45 + abs(change_rate) * 3.0 + min(volume_ratio, 5) * 7.0 + min(math.log10(max(trading_value, 1)) * 2.0, 24)
        if change_rate <= -3 or change_rate >= 8 or volume_ratio >= 2.5:
            risks.append(
                StockPick(
                    ticker=str(r.get("ticker")),
                    name=str(r.get("name")),
                    market=str(r.get("market")),
                    direction="주의",
                    score=round(risk_score, 1),
                    close=round(_safe_float(r.get("close")), 2),
                    change_rate=round(change_rate, 2),
                    volume=_safe_int(r.get("volume")),
                    volume_ratio=round(volume_ratio, 2),
                    trading_value_est=round(trading_value, 0),
                    news_hits=news_hits,
                    reasons=make_risk_reasons(r),
                )
            )

    candidates.sort(key=lambda x: x.score, reverse=True)
    risks.sort(key=lambda x: x.score, reverse=True)
    return candidates[: int(top_n)], risks[: int(top_n)]



# ============================================================
# OpenAI 장전 해석
# ============================================================
def build_ai_input_text(
    latest_date: str,
    markets: List[str],
    candidates: List[StockPick],
    risks: List[StockPick],
    indicators: List[Dict[str, Any]],
    news_items: List[NewsItem],
) -> str:
    parts: List[str] = []
    parts.append(f"[브리핑 기준시각] {_today_str()} 07:00")
    parts.append(f"[국내시장 가격 기준일] {latest_date}")
    parts.append(f"[분석 시장] {', '.join(markets) if markets else '사용자 입력'}")
    parts.append("")

    parts.append("[해외시장 참고 지표]")
    if indicators:
        for it in indicators:
            parts.append(
                f"- {it.get('name')}({it.get('symbol')}): {it.get('last')}, "
                f"전일 대비 {_fmt_pct(_safe_float(it.get('change_rate')))} / {it.get('date')}"
            )
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[장전 주요 뉴스]")
    if news_items:
        for i, n in enumerate(news_items[:12], start=1):
            parts.append(f"- {i}. {n.title} / {n.source} / {n.published}")
            if n.description:
                parts.append(f"  요약: {n.description}")
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[시스템 점수 기반 매매 관심 후보]")
    if candidates:
        for i, p in enumerate(candidates, start=1):
            parts.append(
                f"- {i}. {p.name}({p.ticker}) {p.market} / 점수 {p.score} / "
                f"등락률 {_fmt_pct(p.change_rate)} / 거래량배율 {_fmt_ratio(p.volume_ratio)} / "
                f"뉴스언급 {p.news_hits}건 / 근거: {'; '.join(p.reasons)}"
            )
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[시스템 점수 기반 주의 후보]")
    if risks:
        for i, p in enumerate(risks, start=1):
            parts.append(
                f"- {i}. {p.name}({p.ticker}) {p.market} / 점수 {p.score} / "
                f"등락률 {_fmt_pct(p.change_rate)} / 거래량배율 {_fmt_ratio(p.volume_ratio)} / "
                f"근거: {'; '.join(p.reasons)}"
            )
    else:
        parts.append("- 없음")

    return "\n".join(parts).strip()


def rule_based_ai_brief(candidates: List[StockPick], risks: List[StockPick], news_items: List[NewsItem]) -> str:
    lines: List[str] = []
    lines.append("- OpenAI 분석을 사용할 수 없어 규칙 기반 요약으로 대체했습니다.")

    keywords = build_news_keywords_summary(news_items)
    if keywords:
        lines.append(f"- 장전 뉴스에서 반복된 키워드는 {', '.join(keywords[:6])}입니다.")

    if candidates:
        top_names = ", ".join([f"{p.name}({p.ticker})" for p in candidates[:5]])
        lines.append(f"- 시스템 점수 기준 매매 관심 상위 후보는 {top_names}입니다.")
        lines.append("- 장 시작 직후에는 시초가 갭, 첫 10~30분 거래량, 전일 고점 돌파 여부를 확인하는 방식이 안전합니다.")
    else:
        lines.append("- 시스템 점수 기준 매매 관심 후보가 뚜렷하지 않습니다.")

    if risks:
        risk_names = ", ".join([f"{p.name}({p.ticker})" for p in risks[:5]])
        lines.append(f"- 변동성 주의 후보는 {risk_names}입니다.")

    lines.append("- 이 내용은 투자 권유가 아니라 공개 데이터 기반 장전 체크리스트입니다.")
    return "\n".join(lines)


def generate_ai_preopen_brief(
    latest_date: str,
    markets: List[str],
    candidates: List[StockPick],
    risks: List[StockPick],
    indicators: List[Dict[str, Any]],
    news_items: List[NewsItem],
    model: str,
    temperature: float = 0.2,
) -> str:
    api_key = get_secret_or_env("OPENAI_API_KEY")

    if not HAS_OPENAI or not api_key:
        return rule_based_ai_brief(candidates, risks, news_items)

    client = OpenAI(api_key=api_key)
    input_text = build_ai_input_text(
        latest_date=latest_date,
        markets=markets,
        candidates=candidates,
        risks=risks,
        indicators=indicators,
        news_items=news_items,
    )

    system_prompt = """당신은 한국 주식시장 장전 브리핑을 작성하는 데이터 분석가다.
반드시 제공된 데이터 안에서만 판단하고, 확인되지 않은 사실은 단정하지 않는다.
투자 권유처럼 쓰지 말고, 장전 체크리스트와 매매 후보 검토 자료로 작성한다.
종목을 제시할 때는 이유와 확인 조건을 함께 쓴다."""

    user_prompt = f"""아래 데이터를 바탕으로 한국시간 오전 7시 기준 장전 브리핑을 작성하라.

[출력 형식]
- 오늘 시장 방향성 3~5줄
- 오늘 매매 후보 TOP 5: 종목명, 근거, 장 시작 후 확인 조건
- 오늘 주의 종목: 종목명, 주의 이유
- 장 시작 후 체크포인트 5개
- 마지막 줄에는 '투자 권유가 아닌 참고용 분석'이라고 명기

[데이터]
{input_text}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=float(temperature),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as e:
        return (
            f"- OpenAI 분석 생성에 실패해 규칙 기반 요약으로 대체했습니다. 오류: {e}\n"
            + rule_based_ai_brief(candidates, risks, news_items)
        )

# ============================================================
# 출력 변환
# ============================================================
def picks_to_dataframe(picks: List[StockPick]) -> pd.DataFrame:
    rows = []
    for p in picks:
        rows.append(
            {
                "구분": p.direction,
                "시장": p.market,
                "종목코드": p.ticker,
                "종목명": p.name,
                "점수": p.score,
                "종가": p.close,
                "등락률": p.change_rate,
                "거래량": p.volume,
                "거래량배율": p.volume_ratio,
                "추정거래대금": p.trading_value_est,
                "뉴스언급": p.news_hits,
                "근거": " / ".join(p.reasons),
            }
        )
    return pd.DataFrame(rows)


def news_to_dataframe(news_items: List[NewsItem]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "일시": n.published,
                "출처": n.source,
                "제목": n.title,
                "요약": n.description,
                "링크": n.url,
            }
            for n in news_items
        ]
    )


def build_market_brief(indicators: List[Dict[str, Any]]) -> str:
    if not indicators:
        return "- 해외시장 참고 지표를 가져오지 못했습니다."
    lines = []
    for it in indicators:
        lines.append(f"- {it['name']}({it['symbol']}): {it['last']:.2f}, 전일 대비 {_fmt_pct(it['change_rate'])} ({it['date']})")
    return "\n".join(lines)


def build_news_brief(news_items: List[NewsItem]) -> str:
    if not news_items:
        return "- NewsAPI 뉴스가 수집되지 않았습니다."

    lines = []
    keywords = build_news_keywords_summary(news_items)
    if keywords:
        lines.append(f"- 주요 반복 키워드: {', '.join(keywords)}")

    for i, n in enumerate(news_items[:10], start=1):
        lines.append(f"- {i}. {n.title} / {n.source} / {n.published}")
        if n.description:
            lines.append(f"  - {n.description}")
        if n.url:
            lines.append(f"  - 링크: {n.url}")
    return "\n".join(lines)


def build_workspace_text(
    latest_date: str,
    markets: List[str],
    target_count: int,
    candidates: List[StockPick],
    risks: List[StockPick],
    indicators: List[Dict[str, Any]],
    news_items: List[NewsItem],
    news_query: str,
    ai_brief: str = "",
) -> str:
    today = _today_str()

    lines: List[str] = []
    lines.append("# 장전 주식 분석")
    lines.append(f"- 브리핑 기준시각: {today} 07:00")
    lines.append(f"- 국내시장 가격 기준일: {latest_date}")
    lines.append(f"- 실제 분석시각: {_now_iso()}")
    lines.append(f"- 분석 시장: {', '.join(markets) if markets else '사용자 입력'}")
    lines.append(f"- 분석 대상 종목 수: {target_count}개")
    lines.append("- 데이터 소스: FinanceDataReader + NewsAPI")
    lines.append(f"- 뉴스 검색어: {news_query}")
    lines.append("")

    lines.append("## ① 오늘 시장 환경")
    lines.append(build_market_brief(indicators))
    lines.append("")

    lines.append("## ② 장전 주요 뉴스")
    lines.append(build_news_brief(news_items))
    lines.append("")

    lines.append("## ③ 오늘 매매 관심 종목 TOP")
    if not candidates:
        lines.append("- 조건에 맞는 매매 관심 종목이 없습니다.")
    else:
        for i, p in enumerate(candidates, start=1):
            lines.append(f"### {i}. {p.name}({p.ticker}) / {p.market} / {p.score}점")
            lines.append(f"- 종가: {_fmt_num(p.close)}원")
            lines.append(f"- 직전 거래일 등락률: {_fmt_pct(p.change_rate)}")
            lines.append(f"- 거래량: {_fmt_num(p.volume)}주")
            lines.append(f"- 거래량 배율: {_fmt_ratio(p.volume_ratio)}")
            lines.append(f"- 추정 거래대금: {_fmt_num(p.trading_value_est)}원")
            lines.append(f"- 뉴스 언급: {p.news_hits}건")
            for r in p.reasons:
                lines.append(f"- {r}")
            lines.append("")

    lines.append("## ④ 오늘 주의 종목 TOP")
    if not risks:
        lines.append("- 조건에 맞는 주의 종목이 없습니다.")
    else:
        for i, p in enumerate(risks, start=1):
            lines.append(f"### {i}. {p.name}({p.ticker}) / {p.market} / {p.score}점")
            lines.append(f"- 종가: {_fmt_num(p.close)}원")
            lines.append(f"- 직전 거래일 등락률: {_fmt_pct(p.change_rate)}")
            lines.append(f"- 거래량 배율: {_fmt_ratio(p.volume_ratio)}")
            lines.append(f"- 추정 거래대금: {_fmt_num(p.trading_value_est)}원")
            for r in p.reasons:
                lines.append(f"- {r}")
            lines.append("")

    lines.append("## ⑤ AI 장전 판단")
    if ai_brief.strip():
        lines.append(ai_brief.strip())
    else:
        lines.append("- OpenAI 장전 판단을 사용하지 않았습니다.")
    lines.append("")

    lines.append("## ⑥ 해석상 유의사항")
    lines.append("- 이 자료는 공개 주가·거래량·뉴스 흐름을 바탕으로 한 장전 참고자료입니다.")
    lines.append("- 투자 권유나 매매 추천이 아니며, 실제 매매 판단은 사용자가 별도로 검토해야 합니다.")
    lines.append("- 현재 버전은 수급·시간외 거래·실시간 호가를 반영하지 않습니다.")

    return "\n".join(lines).strip() + "\n"


def build_buffer_items(
    ws_text: str,
    latest_date: str,
    markets: List[str],
    candidates: List[StockPick],
    risks: List[StockPick],
    indicators: List[Dict[str, Any]],
    news_items: List[NewsItem],
    ai_brief: str = "",
) -> List[Dict[str, Any]]:
    return [
        {
            "type": "stock_preopen_analysis",
            "title": f"장전 주식 분석 {latest_date}",
            "text": ws_text,
            "meta": {
                "source": "FinanceDataReader + NewsAPI",
                "published": latest_date,
                "fetched_at": _now_iso(),
                "markets": markets,
                "candidate_count": len(candidates),
                "risk_count": len(risks),
                "indicators": indicators,
                "news_count": len(news_items),
                "ai_brief": ai_brief,
                "raw": {
                    "candidates": [asdict(p) for p in candidates],
                    "risks": [asdict(p) for p in risks],
                    "news": [asdict(n) for n in news_items],
                },
            },
        }
    ]


# ============================================================
# 캐시
# ============================================================
def _init_stock_cache() -> None:
    defaults = {
        "stock_last_ws_text": None,
        "stock_last_buffer": [],
        "stock_last_info": "",
        "stock_last_candidates_df": pd.DataFrame(),
        "stock_last_risks_df": pd.DataFrame(),
        "stock_last_news_df": pd.DataFrame(),
        "stock_last_indicators": [],
        "stock_last_ai_brief": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def clear_stock_cache() -> None:
    st.session_state.stock_last_ws_text = None
    st.session_state.stock_last_buffer = []
    st.session_state.stock_last_info = ""
    st.session_state.stock_last_candidates_df = pd.DataFrame()
    st.session_state.stock_last_risks_df = pd.DataFrame()
    st.session_state.stock_last_news_df = pd.DataFrame()
    st.session_state.stock_last_indicators = []
    st.session_state.stock_last_ai_brief = ""


# ============================================================
# Streamlit UI
# ============================================================
def render_stock_panel() -> Tuple[Optional[str], List[Dict[str, Any]]]:
    st.subheader("📈 장전 주식 분석 시스템")
    _init_stock_cache()

    if fdr is None:
        st.error("FinanceDataReader가 설치되어 있지 않습니다. requirements.txt에 `finance-datareader`를 추가하세요.")
        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

    newsapi_key = get_secret_or_env("NEWSAPI_KEY")
    openai_key = get_secret_or_env("OPENAI_API_KEY")

    top = st.columns([1.2, 1.2, 1, 1])

    with top[0]:
        markets = st.multiselect(
            "분석 시장",
            ["KOSPI", "KOSDAQ"],
            default=["KOSPI", "KOSDAQ"],
            key="stock_markets",
        )

    with top[1]:
        target_count = st.number_input(
            "분석 대상 종목 수",
            min_value=10,
            max_value=len(DEFAULT_STOCKS),
            value=min(30, len(DEFAULT_STOCKS)),
            step=5,
            key="stock_target_count",
            help="현재는 주요 관심 종목 풀에서 앞쪽 N개를 분석합니다.",
        )

    with top[2]:
        top_n = st.number_input(
            "TOP 종목 수",
            min_value=5,
            max_value=20,
            value=10,
            step=5,
            key="stock_top_n",
        )

    with top[3]:
        if st.button("캐시 비우기", use_container_width=True, key="stock_clear_cache"):
            clear_stock_cache()
            st.success("Stock 캐시를 비웠습니다.")
            st.rerun()

    with st.expander("뉴스 설정", expanded=True):
        use_news = st.checkbox("NewsAPI 뉴스 반영", value=True, key="stock_use_news")

        news_query = st.text_area(
            "뉴스 검색어",
            value=DEFAULT_NEWS_QUERY,
            height=90,
            key="stock_news_query",
            help="NewsAPI Everything 검색어입니다. OR를 사용해 여러 이슈를 묶을 수 있습니다.",
        )

        n1, n2 = st.columns(2)
        with n1:
            news_limit = st.number_input("뉴스 수집 개수", min_value=5, max_value=50, value=20, step=5, key="stock_news_limit")
        with n2:
            news_days = st.number_input("뉴스 기간(일)", min_value=1, max_value=7, value=2, step=1, key="stock_news_days")

        if use_news and not newsapi_key:
            st.warning("NEWSAPI_KEY가 없습니다. 뉴스 반영 없이 가격·거래량 중심으로 분석합니다.")

    with st.expander("AI 장전 판단 설정", expanded=True):
        use_ai = st.checkbox("OpenAI 장전 판단 사용", value=True, key="stock_use_ai")
        ai_model = st.text_input(
            "OpenAI 모델",
            value=get_secret_or_env("OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini",
            key="stock_ai_model",
        )
        ai_temperature = st.slider(
            "AI temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.05,
            key="stock_ai_temperature",
        )
        if use_ai and not openai_key:
            st.warning("OPENAI_API_KEY가 없습니다. 규칙 기반 요약으로 대체됩니다.")

    st.caption(
        "이번 버전은 전일 주가·거래량, NewsAPI 뉴스 흐름, OpenAI 장전 판단을 결합해 '오늘 매매 관심 종목'을 선별합니다. "
        "투자 권유가 아니라 장전 체크리스트입니다."
    )

    do_run = st.button("장전 분석 실행", use_container_width=True, key="stock_run")

    if not do_run:
        if st.session_state.stock_last_info:
            st.success(st.session_state.stock_last_info)

            if st.session_state.stock_last_indicators:
                with st.expander("해외시장 참고 지표", expanded=False):
                    st.dataframe(pd.DataFrame(st.session_state.stock_last_indicators), use_container_width=True, hide_index=True)

            if not st.session_state.stock_last_news_df.empty:
                with st.expander("수집 뉴스 미리보기", expanded=False):
                    st.dataframe(st.session_state.stock_last_news_df, use_container_width=True, hide_index=True)

            if not st.session_state.stock_last_candidates_df.empty:
                with st.expander("매매 관심 종목", expanded=True):
                    st.dataframe(st.session_state.stock_last_candidates_df, use_container_width=True, hide_index=True)

            if not st.session_state.stock_last_risks_df.empty:
                with st.expander("주의 종목", expanded=True):
                    st.dataframe(st.session_state.stock_last_risks_df, use_container_width=True, hide_index=True)

            if st.session_state.get("stock_last_ai_brief"):
                with st.expander("AI 장전 판단", expanded=True):
                    st.markdown(st.session_state.stock_last_ai_brief)

        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

    try:
        selected_stocks = [x for x in DEFAULT_STOCKS if not markets or x[2] in markets]
        selected_stocks = selected_stocks[: int(target_count)]

        indicators: List[Dict[str, Any]] = []
        news_items: List[NewsItem] = []

        with st.spinner("해외시장 참고 지표를 수집 중입니다..."):
            indicators = fetch_global_indicators()

        if use_news and newsapi_key and news_query.strip():
            with st.spinner("NewsAPI로 장전 뉴스를 수집 중입니다..."):
                try:
                    news_items = fetch_newsapi_items(newsapi_key, news_query, limit=int(news_limit), days_back=int(news_days))
                except Exception as e:
                    st.warning(f"NewsAPI 수집 실패: {e}")
                    news_items = []

        rows: List[Dict[str, Any]] = []
        latest_dates: List[str] = []

        progress = st.progress(0)
        status = st.empty()

        for i, (ticker, name, market) in enumerate(selected_stocks, start=1):
            status.caption(f"분석 중: {name}({ticker}) {i}/{len(selected_stocks)}")
            row = analyze_one_stock(ticker, name, market, news_items)
            if row:
                rows.append(row)
                if row.get("date"):
                    latest_dates.append(str(row.get("date")))
            progress.progress(i / max(len(selected_stocks), 1))

        status.empty()
        progress.empty()

        if not rows:
            st.error("분석 가능한 종목 데이터가 없습니다. FinanceDataReader 연결 상태를 확인하세요.")
            return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer

        latest_date = max(latest_dates) if latest_dates else _today_str()
        candidates, risks = score_candidates(rows, top_n=int(top_n))

        ai_brief = ""
        if use_ai:
            with st.spinner("OpenAI로 AI 장전 판단을 생성 중입니다..."):
                ai_brief = generate_ai_preopen_brief(
                    latest_date=latest_date,
                    markets=markets,
                    candidates=candidates,
                    risks=risks,
                    indicators=indicators,
                    news_items=news_items,
                    model=ai_model,
                    temperature=float(ai_temperature),
                )

        ws_text = build_workspace_text(
            latest_date=latest_date,
            markets=markets,
            target_count=len(selected_stocks),
            candidates=candidates,
            risks=risks,
            indicators=indicators,
            news_items=news_items,
            news_query=news_query,
            ai_brief=ai_brief,
        )

        buffer_items = build_buffer_items(
            ws_text=ws_text,
            latest_date=latest_date,
            markets=markets,
            candidates=candidates,
            risks=risks,
            indicators=indicators,
            news_items=news_items,
            ai_brief=ai_brief,
        )

        candidates_df = picks_to_dataframe(candidates)
        risks_df = picks_to_dataframe(risks)
        news_df = news_to_dataframe(news_items)

        st.session_state.stock_last_ws_text = ws_text
        st.session_state.stock_last_buffer = buffer_items
        st.session_state.stock_last_candidates_df = candidates_df
        st.session_state.stock_last_risks_df = risks_df
        st.session_state.stock_last_news_df = news_df
        st.session_state.stock_last_indicators = indicators
        st.session_state.stock_last_ai_brief = ai_brief
        st.session_state.stock_last_info = (
            f"장전 주식 분석 완료: 가격 기준일 {latest_date} / "
            f"매매 관심 {len(candidates)}개 / 주의 {len(risks)}개 / 뉴스 {len(news_items)}건 / 생성 {_now_iso()}"
        )

        st.success(st.session_state.stock_last_info)

        if indicators:
            with st.expander("해외시장 참고 지표", expanded=True):
                st.dataframe(pd.DataFrame(indicators), use_container_width=True, hide_index=True)

        if not news_df.empty:
            with st.expander("수집 뉴스", expanded=True):
                st.dataframe(news_df, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 오늘 매매 관심 종목")
            if candidates_df.empty:
                st.info("조건에 맞는 매매 관심 종목이 없습니다.")
            else:
                st.dataframe(candidates_df, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("### 오늘 주의 종목")
            if risks_df.empty:
                st.info("조건에 맞는 주의 종목이 없습니다.")
            else:
                st.dataframe(risks_df, use_container_width=True, hide_index=True)

        if ai_brief.strip():
            with st.expander("AI 장전 판단", expanded=True):
                st.markdown(ai_brief)

        with st.expander("Workspace 반영용 텍스트 미리보기", expanded=False):
            st.text_area("분석 결과", value=ws_text, height=420, disabled=True, key="stock_ws_preview")

        return ws_text, buffer_items

    except Exception as e:
        st.error(
            "장전 주식 분석 실패:\n"
            f"- {e}\n\n"
            "체크 포인트:\n"
            "- requirements.txt에 finance-datareader, pandas<3가 있는지 확인\n"
            "- Streamlit Cloud에서 앱을 Reboot했는지 확인\n"
            "- NEWSAPI_KEY가 Streamlit Secrets에 저장되어 있는지 확인\n"
            "- OpenAI 장전 판단 사용 시 OPENAI_API_KEY가 Streamlit Secrets에 저장되어 있는지 확인\n"
            "- FinanceDataReader 데이터 호출이 일시적으로 실패할 수 있음"
        )
        return st.session_state.stock_last_ws_text, st.session_state.stock_last_buffer
