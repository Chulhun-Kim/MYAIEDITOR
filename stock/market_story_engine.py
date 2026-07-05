"""
market_story_engine.py
---------------------------------------------------------
v2.2

오늘 시장 전체를 하나의 스토리로 만드는 엔진

News
 ↓
Theme Graph
 ↓
Money Flow
 ↓
Sector
 ↓
Candidate
 ↓
Risk / Watch Point
 ↓
Market Story

Author : MYAIEDITOR
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


# --------------------------------------------------------
# Optional modules
# --------------------------------------------------------

try:
    from stock.theme_reasoner import (
        analyze_theme_graph,
        summarize_theme_graph_from_news,
    )
except Exception:
    def analyze_theme_graph(
        news_items=None,
        indicators=None,
        extra_text: str = "",
        min_score: float = 18.0,
        limit: int = 8,
    ):
        return []

    def summarize_theme_graph_from_news(
        news_items=None,
        indicators=None,
        limit: int = 3,
    ):
        return "뚜렷하게 부각된 테마 그래프가 감지되지 않았습니다."

try:
    from stock.theme_graph import (
        build_money_flow_story,
        build_trading_idea,
        theme_graph_to_markdown,
    )
except Exception:
    def build_money_flow_story(theme_nodes, limit: int = 4):
        return "테마 간 자금 이동은 장 초반 거래량 확인이 필요합니다."

    def build_trading_idea(theme_nodes, limit: int = 3):
        return ["시초가 갭과 거래량을 확인한 뒤 주도 테마 여부를 판단합니다."]

    def theme_graph_to_markdown(theme_nodes, limit: int = 5):
        return "- 감지된 핵심 테마가 없습니다."


# --------------------------------------------------------
# Public API
# --------------------------------------------------------

def build_market_story(
    market_decision: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    dart_items: List[Dict[str, Any]],
    indicators: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    장전 분석 결과를 하나의 시장 스토리로 조립한다.

    기존 app_stock.py / market_dashboard.py가 기대하던 핵심 키
    headline, summary, flow, drivers, risks, watch_points는 그대로 유지한다.

    v2.2 추가 키
    theme_summary, money_flow_story, theme_graph_markdown, trading_ideas,
    opportunities, strategy_comment, recommendation, story_score,
    market_temperature, dashboard를 함께 반환한다.
    """

    safe_market_decision = _as_dict(market_decision)
    safe_news_items = _as_list(news_items)
    safe_sector_results = _as_list(sector_results)
    safe_candidate_scores = _as_list(candidate_scores)
    safe_after_hours_data = _as_list(after_hours_data)
    safe_dart_items = _as_list(dart_items)
    safe_indicators = _as_list(indicators)

    theme_graph = _safe_theme_graph(
        news_items=safe_news_items,
        indicators=safe_indicators,
        limit=5,
    )

    theme_summary = _safe_theme_summary(
        news_items=safe_news_items,
        indicators=safe_indicators,
        limit=3,
    )

    money_flow_story = _safe_money_flow_story(
        theme_graph,
        limit=4,
    )

    trading_ideas = _safe_trading_ideas(
        theme_graph,
        limit=3,
    )

    theme_graph_markdown = _safe_theme_graph_markdown(
        theme_graph,
        limit=5,
    )

    story_score = _build_story_score(
        market_decision=safe_market_decision,
        news_items=safe_news_items,
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        after_hours_data=safe_after_hours_data,
        dart_items=safe_dart_items,
        theme_graph=theme_graph,
    )

    market_temperature = _build_market_temperature(story_score)

    headline = _build_headline(
        safe_market_decision,
        safe_sector_results,
        theme_graph,
    )

    summary = _build_summary(
        safe_market_decision,
        safe_sector_results,
        theme_summary=theme_summary,
        money_flow_story=money_flow_story,
        story_score=story_score,
        market_temperature=market_temperature,
    )

    flow = _build_flow(
        safe_news_items,
        safe_sector_results,
        safe_candidate_scores,
        theme_graph=theme_graph,
        money_flow_story=money_flow_story,
    )

    drivers = _build_drivers(
        safe_news_items,
        safe_after_hours_data,
        safe_sector_results,
        theme_graph=theme_graph,
    )

    risks = _build_risks(
        safe_market_decision,
        safe_candidate_scores,
        safe_after_hours_data=safe_after_hours_data,
        dart_items=safe_dart_items,
        story_score=story_score,
    )

    opportunities = _build_opportunities(
        safe_sector_results,
        safe_candidate_scores,
        theme_graph,
        safe_after_hours_data,
    )

    watch_points = _build_watch_points(
        safe_candidate_scores,
        safe_dart_items,
        trading_ideas,
        risks=risks,
    )

    strategy_comment = _build_strategy_comment(
        safe_market_decision,
        story_score,
        market_temperature,
        top_sector=_top_sector_name(safe_sector_results),
        top_theme=_top_theme_name(theme_graph),
    )

    recommendation = _build_recommendation(
        market_decision=safe_market_decision,
        story_score=story_score,
        market_temperature=market_temperature,
        risks=risks,
        opportunities=opportunities,
    )

    dashboard = _build_dashboard_payload(
        headline=headline,
        story_score=story_score,
        market_temperature=market_temperature,
        top_sector=_top_sector_name(safe_sector_results),
        top_theme=_top_theme_name(theme_graph),
        candidate_scores=safe_candidate_scores,
        risks=risks,
        opportunities=opportunities,
    )

    return {
        # 기존 호환 키
        "headline": headline,
        "summary": summary,
        "flow": flow,
        "drivers": drivers,
        "risks": risks,
        "watch_points": watch_points,

        # v2.2 확장 키
        "theme_graph": theme_graph,
        "theme_summary": theme_summary,
        "theme_graph_markdown": theme_graph_markdown,
        "money_flow_story": money_flow_story,
        "trading_ideas": trading_ideas,
        "opportunities": opportunities,
        "strategy_comment": strategy_comment,
        "recommendation": recommendation,
        "story_score": story_score,
        "market_temperature": market_temperature,
        "dashboard": dashboard,
    }


# --------------------------------------------------------
# Safe wrappers
# --------------------------------------------------------

def _safe_theme_graph(
    news_items: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    try:
        result = analyze_theme_graph(
            news_items=news_items,
            indicators=indicators,
            limit=limit,
        )
        return _as_list(result)[:limit]
    except Exception:
        return []


def _safe_theme_summary(
    news_items: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    limit: int = 3,
) -> str:
    try:
        text = summarize_theme_graph_from_news(
            news_items=news_items,
            indicators=indicators,
            limit=limit,
        )
        return _clean_text(text) or "뚜렷하게 부각된 테마 그래프가 감지되지 않았습니다."
    except Exception:
        return "뚜렷하게 부각된 테마 그래프가 감지되지 않았습니다."


def _safe_money_flow_story(
    theme_graph: List[Dict[str, Any]],
    limit: int = 4,
) -> str:
    try:
        text = build_money_flow_story(theme_graph, limit=limit)
        return _clean_text(text) or "테마 간 자금 이동은 장 초반 거래량 확인이 필요합니다."
    except Exception:
        return "테마 간 자금 이동은 장 초반 거래량 확인이 필요합니다."


def _safe_trading_ideas(
    theme_graph: List[Dict[str, Any]],
    limit: int = 3,
) -> List[str]:
    try:
        ideas = build_trading_idea(theme_graph, limit=limit)
        return _unique_texts(_as_list(ideas))[:limit]
    except Exception:
        return ["시초가 갭과 거래량을 확인한 뒤 주도 테마 여부를 판단합니다."]


def _safe_theme_graph_markdown(
    theme_graph: List[Dict[str, Any]],
    limit: int = 5,
) -> str:
    try:
        text = theme_graph_to_markdown(theme_graph, limit=limit)
        return _clean_text(text) or "- 감지된 핵심 테마가 없습니다."
    except Exception:
        return "- 감지된 핵심 테마가 없습니다."


# --------------------------------------------------------
# Builders
# --------------------------------------------------------

def _build_headline(
    market_decision: Dict[str, Any],
    sector_results: List[Dict[str, Any]],
    theme_graph: Optional[List[Dict[str, Any]]] = None,
) -> str:
    strategy = _clean_text(market_decision.get("strategy")) or "중립"

    top_theme = _top_theme_name(theme_graph or [])
    top_parent = _top_theme_parent(theme_graph or [])

    if top_theme:
        if top_parent and top_parent != top_theme:
            return f"{top_parent} · {top_theme} 중심 {strategy} 전략"
        return f"{top_theme} 중심 {strategy} 전략"

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        return f"{top_sector} 중심 {strategy} 전략"

    return f"{strategy} 전략"


def _build_summary(
    market_decision: Dict[str, Any],
    sector_results: List[Dict[str, Any]],
    theme_summary: str = "",
    money_flow_story: str = "",
    story_score: int = 50,
    market_temperature: str = "중립",
) -> str:
    strategy = _clean_text(market_decision.get("strategy")) or "중립"
    top_sector = _top_sector_name(sector_results)

    if top_sector:
        base = (
            f"오늘 시장은 {top_sector} 중심의 흐름이 우선 확인됩니다. "
            f"시장 온도는 {market_temperature} 구간이며, 현재 전략은 {strategy}입니다. "
        )
    else:
        base = (
            f"오늘 시장은 뚜렷한 단일 주도 섹터보다 선별적인 흐름이 예상됩니다. "
            f"시장 온도는 {market_temperature} 구간이며, 현재 전략은 {strategy}입니다. "
        )

    detail_parts = []
    if theme_summary:
        detail_parts.append(theme_summary)
    if money_flow_story:
        detail_parts.append(money_flow_story)

    detail = " ".join(detail_parts).strip()
    if detail:
        return base + detail + " 주도주를 중심으로 접근하되 과열 종목은 추격보다 눌림과 거래량 지속 여부를 확인하는 전략이 유리합니다."

    return base + "주도주를 중심으로 접근하되 과열 종목은 추격보다 눌림과 거래량 지속 여부를 확인하는 전략이 유리합니다."


def _build_flow(
    news_items: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    theme_graph: Optional[List[Dict[str, Any]]] = None,
    money_flow_story: str = "",
) -> List[str]:
    flow: List[str] = []

    if news_items:
        flow.append(f"주요 뉴스 {len(news_items)}건이 장전 투자심리 형성에 반영됐습니다.")

    top_theme = _top_theme_name(theme_graph or [])
    if top_theme:
        flow.append(f"테마 그래프에서는 {top_theme} 테마가 우선 부각됐습니다.")

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        flow.append(f"섹터 흐름은 {top_sector}가 상대적으로 강하게 나타났습니다.")

    top_names = _top_candidate_names(candidate_scores, limit=3)
    if top_names:
        flow.append("대표 관심 종목 : " + ", ".join(top_names))

    if money_flow_story:
        flow.append(money_flow_story)

    return _unique_texts(flow)[:8]


def _build_drivers(
    news_items: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    theme_graph: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    drivers: List[str] = []

    top_theme = _top_theme_name(theme_graph or [])
    if top_theme:
        drivers.append(f"{top_theme} 테마 부각")

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        drivers.append(f"{top_sector} 섹터 강세")

    for item in after_hours_data[:5]:
        item = _as_dict(item)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        pct = _to_float(
            item.get("after_change_pct")
            or item.get("change_pct")
            or item.get("rate")
            or item.get("등락률")
        )
        if name and pct is not None:
            drivers.append(f"{name} 시간외 {pct:+.2f}%")

    for item in news_items[:3]:
        item = _as_dict(item)
        title = _clean_text(item.get("title") or item.get("headline"))
        if title:
            drivers.append(f"뉴스 모멘텀: {_shorten(title, 42)}")

    return _unique_texts(drivers)[:8]


def _build_risks(
    market_decision: Dict[str, Any],
    candidate_scores: List[Dict[str, Any]],
    safe_after_hours_data: Optional[List[Dict[str, Any]]] = None,
    dart_items: Optional[List[Dict[str, Any]]] = None,
    story_score: int = 50,
    after_hours_data: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    risks: List[str] = []
    ah_data = safe_after_hours_data if safe_after_hours_data is not None else (after_hours_data or [])
    dart_data = dart_items or []

    if len(candidate_scores) >= 8:
        risks.append("관심 종목이 많아 단기 과열 및 수급 분산 가능성이 있습니다.")

    decision_score = _to_float(market_decision.get("score"))
    if decision_score is not None and decision_score < 60:
        risks.append("시장 판단 점수가 높지 않아 공격적 비중 확대에는 신중할 필요가 있습니다.")

    if story_score < 45:
        risks.append("뉴스·섹터·종목 신호의 결합 강도가 약해 장 초반 변동성 확대에 유의해야 합니다.")

    weak_after_hours = []
    for item in ah_data[:8]:
        item = _as_dict(item)
        pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("등락률"))
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if name and pct is not None and pct <= -3:
            weak_after_hours.append(f"{name} 시간외 급락")
    risks.extend(weak_after_hours[:3])

    if dart_data:
        risks.append("공시 재료가 포함돼 있어 세부 내용 확인 전까지 해석 리스크가 있습니다.")

    if not risks:
        risks.append("뚜렷한 구조적 위험은 제한적이나 장 초반 거래대금과 지수 방향 확인이 필요합니다.")

    return _unique_texts(risks)[:8]


def _build_opportunities(
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
) -> List[str]:
    opportunities: List[str] = []

    top_theme = _top_theme_name(theme_graph)
    if top_theme:
        opportunities.append(f"{top_theme} 테마가 뉴스와 수급의 공통 축으로 연결될 경우 주도 테마로 확장될 수 있습니다.")

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        opportunities.append(f"{top_sector} 섹터 내 대장주와 후속주의 순환매 가능성을 점검할 필요가 있습니다.")

    names = _top_candidate_names(candidate_scores, limit=3)
    if names:
        opportunities.append("관심 종목군에서는 " + ", ".join(names) + "의 장 초반 거래량 지속 여부가 핵심입니다.")

    strong_after_hours = []
    for item in after_hours_data[:8]:
        item = _as_dict(item)
        pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("등락률"))
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if name and pct is not None and pct >= 3:
            strong_after_hours.append(f"{name} 시간외 강세 연속성")

    opportunities.extend(strong_after_hours[:3])

    if not opportunities:
        opportunities.append("장 초반에는 단일 테마보다 거래대금이 집중되는 종목 중심의 선별 접근이 유리합니다.")

    return _unique_texts(opportunities)[:8]


def _build_watch_points(
    candidate_scores: List[Dict[str, Any]],
    dart_items: List[Dict[str, Any]],
    trading_ideas: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
) -> List[str]:
    watch = [
        "시초가 갭 확인",
        "거래량 유지 여부",
        "외국인·기관 수급 확인",
        "대장주와 후속주 순환 여부 확인",
    ]

    for idea in trading_ideas or []:
        text = _clean_text(idea)
        if text:
            watch.append(text)

    if candidate_scores:
        watch.append("관심 종목 TOP의 장 초반 체결 강도 확인")

    if dart_items:
        watch.append("공시 내용과 실제 실적·계약 규모 확인")

    if risks and len(risks) >= 3:
        watch.append("과열·변동성 주의 종목은 추격 매수 자제")

    return _unique_texts(watch)[:8]


def _build_strategy_comment(
    market_decision: Dict[str, Any],
    story_score: int,
    market_temperature: str,
    top_sector: str = "",
    top_theme: str = "",
) -> str:
    strategy = _clean_text(market_decision.get("strategy")) or "중립"

    focus = top_theme or top_sector or "거래대금 상위 종목"

    if story_score >= 75:
        tone = "공격적 관심은 가능하지만"
        action = "분할 접근과 장중 눌림 확인이 필요합니다."
    elif story_score >= 60:
        tone = "선별적 관심이 가능한 구간이며"
        action = "대장주 거래량이 유지되는지 확인해야 합니다."
    elif story_score >= 45:
        tone = "중립적 관찰이 필요한 구간이며"
        action = "시초가 이후 방향성이 확인될 때까지 비중 확대는 늦추는 편이 좋습니다."
    else:
        tone = "방어적 접근이 우선인 구간이며"
        action = "무리한 추격보다 현금 비중과 리스크 관리가 중요합니다."

    return (
        f"현재 전략은 {strategy}, 시장 온도는 {market_temperature}입니다. "
        f"{focus}를 중심으로 {tone} {action}"
    )


def _build_recommendation(
    market_decision: Dict[str, Any],
    story_score: int,
    market_temperature: str,
    risks: List[str],
    opportunities: List[str],
) -> Dict[str, Any]:
    if story_score >= 75:
        label = "관심 강화"
        stance = "bullish"
    elif story_score >= 60:
        label = "선별 관심"
        stance = "selective"
    elif story_score >= 45:
        label = "중립 관망"
        stance = "neutral"
    else:
        label = "방어 우선"
        stance = "defensive"

    return {
        "label": label,
        "stance": stance,
        "score": story_score,
        "temperature": market_temperature,
        "reason": _build_recommendation_reason(label, risks, opportunities),
        "risk_count": len(risks),
        "opportunity_count": len(opportunities),
        "market_strategy": _clean_text(market_decision.get("strategy")) or "중립",
    }


def _build_recommendation_reason(
    label: str,
    risks: List[str],
    opportunities: List[str],
) -> str:
    opp = opportunities[0] if opportunities else "뚜렷한 기회 요인은 제한적입니다."
    risk = risks[0] if risks else "특별한 위험 요인은 제한적입니다."
    return f"{label}: {opp} 다만 {risk}"


def _build_dashboard_payload(
    headline: str,
    story_score: int,
    market_temperature: str,
    top_sector: str,
    top_theme: str,
    candidate_scores: List[Dict[str, Any]],
    risks: List[str],
    opportunities: List[str],
) -> Dict[str, Any]:
    return {
        "headline": headline,
        "story_score": story_score,
        "market_temperature": market_temperature,
        "top_sector": top_sector or "-",
        "top_theme": top_theme or "-",
        "top_candidates": _top_candidate_names(candidate_scores, limit=5),
        "risk_count": len(risks),
        "opportunity_count": len(opportunities),
    }


# --------------------------------------------------------
# Score
# --------------------------------------------------------

def _build_story_score(
    market_decision: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    dart_items: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
) -> int:
    score = 40.0

    market_score = _to_float(market_decision.get("score"))
    if market_score is not None:
        score += max(-10, min(20, (market_score - 50) * 0.4))

    if news_items:
        score += min(10, len(news_items) * 1.5)

    if sector_results:
        top_sector_score = _extract_score(sector_results[0])
        if top_sector_score is not None:
            score += max(0, min(12, top_sector_score / 10))
        else:
            score += 6

    if candidate_scores:
        score += min(12, len(candidate_scores) * 1.2)
        top_candidate_score = _extract_score(candidate_scores[0])
        if top_candidate_score is not None:
            score += max(0, min(8, top_candidate_score / 12))

    if theme_graph:
        score += min(10, len(theme_graph) * 2)
        top_theme_score = _extract_score(theme_graph[0])
        if top_theme_score is not None:
            score += max(0, min(8, top_theme_score / 15))

    positive_after_hours = 0
    negative_after_hours = 0
    for item in after_hours_data[:10]:
        pct = _to_float(_as_dict(item).get("after_change_pct") or _as_dict(item).get("change_pct") or _as_dict(item).get("등락률"))
        if pct is not None:
            if pct >= 3:
                positive_after_hours += 1
            elif pct <= -3:
                negative_after_hours += 1

    score += positive_after_hours * 1.5
    score -= negative_after_hours * 2.0

    if dart_items:
        score += min(4, len(dart_items) * 0.8)

    return int(max(0, min(100, round(score))))


def _build_market_temperature(story_score: int) -> str:
    if story_score >= 80:
        return "강한 위험선호"
    if story_score >= 65:
        return "우호적"
    if story_score >= 50:
        return "중립"
    if story_score >= 35:
        return "관망"
    return "방어"


# --------------------------------------------------------
# Extractors / utilities
# --------------------------------------------------------

def _top_sector_name(sector_results: List[Dict[str, Any]]) -> str:
    if not sector_results:
        return ""
    top = _as_dict(sector_results[0])
    return _clean_text(
        top.get("sector")
        or top.get("name")
        or top.get("sector_name")
        or top.get("업종")
    )


def _top_theme_name(theme_graph: List[Dict[str, Any]]) -> str:
    if not theme_graph:
        return ""
    top = _as_dict(theme_graph[0])
    return _clean_text(
        top.get("theme")
        or top.get("name")
        or top.get("label")
        or top.get("keyword")
    )


def _top_theme_parent(theme_graph: List[Dict[str, Any]]) -> str:
    if not theme_graph:
        return ""
    top = _as_dict(theme_graph[0])
    return _clean_text(top.get("parent") or top.get("parent_theme") or top.get("group"))


def _top_candidate_names(candidate_scores: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    names: List[str] = []
    for item in candidate_scores[:limit]:
        item = _as_dict(item)
        name = _clean_text(
            item.get("name")
            or item.get("stock_name")
            or item.get("종목명")
            or item.get("code")
        )
        if name:
            names.append(name)
    return _unique_texts(names)[:limit]


def _extract_score(item: Dict[str, Any]) -> Optional[float]:
    item = _as_dict(item)
    for key in ("score", "total_score", "final_score", "strength", "rank_score"):
        value = _to_float(item.get(key))
        if value is not None:
            return value
    return None


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def _shorten(text: str, limit: int = 40) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        text = str(value).strip().replace("%", "").replace(",", "")
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _unique_texts(items: Sequence[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        text = _clean_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


# --------------------------------------------------------
# Backward-compatible aliases
# --------------------------------------------------------

def build_story(*args, **kwargs) -> Dict[str, Any]:
    """이전 호출부가 build_story를 사용할 경우를 위한 호환 함수."""
    return build_market_story(*args, **kwargs)


def build_ai_market_story(*args, **kwargs) -> Dict[str, Any]:
    """이전 호출부가 build_ai_market_story를 사용할 경우를 위한 호환 함수."""
    return build_market_story(*args, **kwargs)
