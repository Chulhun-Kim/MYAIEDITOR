# stock/market_decision.py
# ------------------------------------------------------------
# MYAIEDITOR 시장 판단 엔진 v1.3
# AI Strategy Engine
# - 해외시장·환율·유가·뉴스·시간외·DART·섹터를 종합해
#   장전 시장 분위기, 투자전략, 현금비중, 섹터전략을 구조화한다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MarketDecision:
    score: float
    stars: str
    sentiment: str
    strategy: str
    strategy_comment: str
    cash_ratio: int
    buy_ratio: int
    sector_strategy: str
    summary: str
    reasons: List[str] = field(default_factory=list)
    strategy_reasons: List[str] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        try:
            return item.to_dict()
        except Exception:
            pass
    try:
        return asdict(item)
    except Exception:
        return {}


def _news_text(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(
            str(item.get(k, "") or "")
            for k in ["title", "description", "content", "summary"]
        )
    return " ".join(
        str(getattr(item, k, "") or "")
        for k in ["title", "description", "content", "summary"]
    )


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def score_to_stars(score: float) -> str:
    if score >= 95:
        return "★★★★★"
    if score >= 85:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    if score >= 55:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def classify_market(score: float) -> tuple[str, str]:
    if score >= 95:
        return "매우 강세", "🟢 매우 강세"
    if score >= 85:
        return "강세", "🟢 강세"
    if score >= 70:
        return "중립 우위", "🟡 중립 우위"
    if score >= 55:
        return "중립", "🟡 중립"
    if score >= 45:
        return "주의", "🔴 주의"
    return "위험", "🔴 위험"


def decide_ai_strategy(score: float, signals: Dict[str, Any]) -> tuple[str, str, int, int, List[str]]:
    """
    AI Strategy Engine 핵심 함수.
    시장점수와 세부 신호를 바탕으로 오늘의 전략을 결정한다.
    """

    negative_news = int(signals.get("negative_news_count", 0) or 0)
    positive_news = int(signals.get("positive_news_count", 0) or 0)
    after_down = int(signals.get("after_hours_down", 0) or 0)
    after_up = int(signals.get("after_hours_up", 0) or 0)
    negative_dart = int(signals.get("negative_dart_count", 0) or 0)
    top_sector = signals.get("top_sector")

    risk_penalty = 0
    strategy_reasons: List[str] = []

    if negative_news >= positive_news + 5:
        risk_penalty += 1
        strategy_reasons.append("부정 뉴스 키워드가 긍정 뉴스보다 많아 추격 매수는 신중해야 합니다.")

    if after_down > after_up:
        risk_penalty += 1
        strategy_reasons.append("시간외 하락 종목 수가 상승 종목보다 많아 장 초반 변동성 확인이 필요합니다.")

    if negative_dart >= 2:
        risk_penalty += 1
        strategy_reasons.append("주의 공시 키워드가 감지돼 개별 종목 리스크 관리가 필요합니다.")

    if top_sector:
        strategy_reasons.append(f"핵심 섹터는 {top_sector}로 판단됩니다.")

    adjusted_score = score - risk_penalty * 5

    if adjusted_score >= 95:
        strategy = "▶ 적극 매수"
        comment = "시장 강도가 매우 높습니다. 강한 섹터와 대형 주도주 중심의 적극 대응이 가능합니다."
        cash_ratio = 20
    elif adjusted_score >= 85:
        strategy = "▶ 선별 매수"
        comment = "시장 분위기는 우호적이지만 업종별 차별화가 예상됩니다. 강한 섹터 중심으로 선별 접근합니다."
        cash_ratio = 30
    elif adjusted_score >= 70:
        strategy = "▶ 관망"
        comment = "방향성은 나쁘지 않지만 추격 매수보다 시초가·거래량·수급 확인 후 접근하는 것이 좋습니다."
        cash_ratio = 50
    elif adjusted_score >= 55:
        strategy = "▶ 현금비중 확대"
        comment = "시장 변동성이 커질 수 있는 구간입니다. 신규 매수보다 리스크 관리가 우선입니다."
        cash_ratio = 70
    else:
        strategy = "▶ 방어적 대응"
        comment = "시장 리스크가 높은 구간입니다. 현금 비중 유지와 손실 방어를 우선합니다."
        cash_ratio = 80

    buy_ratio = 100 - cash_ratio

    if not strategy_reasons:
        strategy_reasons.append("뚜렷한 위험 신호는 제한적이나 장 초반 가격과 거래량 확인이 필요합니다.")

    return strategy, comment, cash_ratio, buy_ratio, strategy_reasons[:5]


def build_sector_strategy(sector_results: Optional[List[Dict[str, Any]]]) -> str:
    if not sector_results:
        return "핵심 섹터 신호가 제한적입니다."

    names: List[str] = []
    for item in sector_results[:3]:
        sector = str(item.get("sector", "") or "")
        if sector:
            names.append(sector)

    if not names:
        return "핵심 섹터 신호가 제한적입니다."

    if len(names) == 1:
        return f"{names[0]} 중심으로 우선 점검합니다."

    return f"{' / '.join(names)} 순서로 우선 점검합니다."


def _indicator_score(indicators: List[Dict[str, Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    signals: Dict[str, Any] = {}

    for item in indicators or []:
        name = str(item.get("name", "") or "")
        symbol = str(item.get("symbol", "") or "")
        change = _safe_float(item.get("change_rate"))
        key = f"{name}({symbol})" if symbol else name
        signals[key] = change

        if name in ["나스닥", "엔비디아", "마이크로소프트"]:
            if change >= 1.0:
                score += 8
                reasons.append(f"{name} 강세({_fmt_pct(change)})로 성장주·AI 투자심리에 우호적")
            elif change <= -1.0:
                score -= 8
                reasons.append(f"{name} 약세({_fmt_pct(change)})로 성장주·AI 투자심리에 부담")
            elif change > 0:
                score += 3
            elif change < 0:
                score -= 3

        elif name == "S&P500":
            if change >= 0.7:
                score += 5
                reasons.append(f"S&P500 상승({_fmt_pct(change)})으로 위험자산 선호 개선")
            elif change <= -0.7:
                score -= 5
                reasons.append(f"S&P500 하락({_fmt_pct(change)})으로 위험자산 선호 약화")

        elif name == "달러/원":
            if change >= 0.7:
                score -= 5
                reasons.append(f"달러/원 상승({_fmt_pct(change)})으로 외국인 수급 부담 가능성")
            elif change <= -0.5:
                score += 4
                reasons.append(f"달러/원 하락({_fmt_pct(change)})으로 외국인 수급 여건 개선 가능성")

        elif name == "WTI유가":
            if change >= 2.0:
                score -= 3
                reasons.append(f"유가 상승({_fmt_pct(change)})으로 비용 부담 업종 주의")
            elif change <= -2.0:
                score += 2

        elif name == "테슬라":
            if change >= 1.0:
                score += 4
                reasons.append(f"테슬라 강세({_fmt_pct(change)})로 2차전지·전기차 심리 개선 가능성")
            elif change <= -1.0:
                score -= 4
                reasons.append(f"테슬라 약세({_fmt_pct(change)})로 2차전지·전기차 심리 부담")

    return score, reasons[:8], signals


def _news_score(news_items: List[Any]) -> tuple[float, List[str], Dict[str, Any]]:
    positive_keywords = [
        "AI", "인공지능", "투자", "수주", "공급계약", "계약", "실적", "흑자", "증익",
        "반등", "상승", "호조", "수출", "완화", "확대", "협력", "엔비디아", "HBM",
    ]
    negative_keywords = [
        "관세", "분쟁", "전쟁", "금리", "인플레이션", "하락", "침체", "둔화",
        "규제", "적자", "손실", "소송", "리콜", "제재", "불확실성",
    ]

    pos = 0
    neg = 0

    for item in news_items or []:
        text = _news_text(item)
        if any(k in text for k in positive_keywords):
            pos += 1
        if any(k in text for k in negative_keywords):
            neg += 1

    score = min(pos * 1.2, 10) - min(neg * 1.2, 10)

    reasons: List[str] = []
    if pos:
        reasons.append(f"긍정 뉴스 키워드 {pos}건 감지")
    if neg:
        reasons.append(f"주의 뉴스 키워드 {neg}건 감지")

    return score, reasons, {
        "positive_news_count": pos,
        "negative_news_count": neg,
    }


def _after_hours_score(after_hours_data: Optional[List[Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    up = 0
    down = 0
    strong_up = 0
    strong_down = 0

    for item in after_hours_data or []:
        d = _item_to_dict(item)
        change = _safe_float(
            d.get("after_change_pct")
            or d.get("after_hours_change_rate")
            or d.get("change_rate")
            or d.get("after_change")
            or d.get("등락률")
            or 0
        )

        if change > 0:
            up += 1
            score += min(change * 0.8, 4)
            if change >= 3:
                strong_up += 1
        elif change < 0:
            down += 1
            score -= min(abs(change) * 0.8, 4)
            if change <= -3:
                strong_down += 1

    reasons: List[str] = []
    if up or down:
        reasons.append(f"시간외 상승 {up}개·하락 {down}개 감지")
    if strong_up:
        reasons.append(f"시간외 3% 이상 강세 종목 {strong_up}개")
    if strong_down:
        reasons.append(f"시간외 3% 이상 약세 종목 {strong_down}개")

    return score, reasons, {
        "after_hours_up": up,
        "after_hours_down": down,
        "after_hours_strong_up": strong_up,
        "after_hours_strong_down": strong_down,
    }


def _dart_score(dart_items: Optional[List[Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    positive_keywords = ["공급계약", "수주", "자사주", "소각", "배당", "신규시설투자", "실적", "영업이익"]
    negative_keywords = ["유상증자", "전환사채", "CB", "BW", "불성실공시", "소송", "적자", "영업손실"]

    pos = 0
    neg = 0

    for item in dart_items or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())
        if any(k in text for k in positive_keywords):
            pos += 1
        if any(k in text for k in negative_keywords):
            neg += 1

    score = min(pos * 2.0, 6) - min(neg * 2.5, 8)

    reasons: List[str] = []
    if pos:
        reasons.append(f"긍정 공시 키워드 {pos}건 감지")
    if neg:
        reasons.append(f"주의 공시 키워드 {neg}건 감지")

    return score, reasons, {
        "positive_dart_count": pos,
        "negative_dart_count": neg,
    }


def _sector_score(sector_results: Optional[List[Dict[str, Any]]]) -> tuple[float, List[str], Dict[str, Any]]:
    if not sector_results:
        return 0.0, [], {"top_sector": None}

    top = sector_results[0]
    top_score = _safe_float(top.get("score"))
    sector_name = str(top.get("sector", "") or "")

    score = min(top_score * 0.08, 8)

    reasons = []
    if sector_name:
        reasons.append(f"강세 예상 섹터 상위: {sector_name}({top_score:.1f}점)")

    return score, reasons, {
        "top_sector": sector_name,
        "top_sector_score": top_score,
    }


def build_market_decision(
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
) -> MarketDecision:
    base = 60.0
    total = base
    reasons: List[str] = []
    signals: Dict[str, Any] = {"base_score": base}

    for score_part, part_reasons, part_signals in [
        _indicator_score(indicators),
        _news_score(news_items),
        _after_hours_score(after_hours_data),
        _dart_score(dart_items),
        _sector_score(sector_results),
    ]:
        total += score_part
        reasons.extend(part_reasons)
        signals.update(part_signals)

    total = max(0.0, min(round(total, 1), 100.0))

    stars = score_to_stars(total)
    sentiment, sentiment_badge = classify_market(total)

    strategy, strategy_comment, cash_ratio, buy_ratio, strategy_reasons = decide_ai_strategy(
        score=total,
        signals=signals,
    )

    sector_strategy = build_sector_strategy(sector_results)

    top_sector = signals.get("top_sector")

    if top_sector:
        summary = (
            f"오늘 시장은 {sentiment}({stars})로 판단됩니다. "
            f"{top_sector} 중심의 흐름을 우선 점검할 필요가 있습니다.\n\n"
            f"전략: {strategy}. {strategy_comment}"
        )
    else:
        summary = (
            f"오늘 시장은 {sentiment}({stars})로 판단됩니다.\n\n"
            f"전략: {strategy}. {strategy_comment}"
        )

    signals["sentiment_badge"] = sentiment_badge
    signals["cash_ratio"] = cash_ratio
    signals["buy_ratio"] = buy_ratio
    signals["sector_strategy"] = sector_strategy

    if not reasons:
        reasons.append("뚜렷한 방향성 신호가 제한적이어서 장 초반 확인이 필요합니다.")

    return MarketDecision(
        score=total,
        stars=stars,
        sentiment=sentiment,
        strategy=strategy,
        strategy_comment=strategy_comment,
        cash_ratio=cash_ratio,
        buy_ratio=buy_ratio,
        sector_strategy=sector_strategy,
        summary=summary,
        reasons=reasons[:10],
        strategy_reasons=strategy_reasons[:5],
        signals=signals,
    )


def format_market_decision(decision: Optional[MarketDecision]) -> str:
    if decision is None:
        return "- 시장 판단 결과가 없습니다."

    lines = [
        f"### 오늘 시장 판단: {decision.sentiment} {decision.stars}",
        f"- 종합점수: {decision.score}/100",
        f"- 전략: {decision.strategy}",
        f"- 현금비중: {decision.cash_ratio}%",
        f"- 매수비중: {decision.buy_ratio}%",
        f"- 섹터전략: {decision.sector_strategy}",
        f"- 요약: {decision.summary}",
    ]

    if decision.strategy_reasons:
        lines.append("- 전략 근거:")
        for r in decision.strategy_reasons[:5]:
            lines.append(f"  - {r}")

    if decision.reasons:
        lines.append("- 주요 근거:")
        for r in decision.reasons[:6]:
            lines.append(f"  - {r}")

    return "\n".join(lines)