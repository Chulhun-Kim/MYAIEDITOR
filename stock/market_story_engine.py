"""
stock/market_story_engine.py
---------------------------------------------------------
v2.7 Narrative Polish Architecture

오늘 시장 전체를 하나의 스토리로 만드는 엔진.

핵심 원칙
- build_market_story()는 오케스트레이터 역할만 한다.
- summary / flow / drivers / risks / watch_points는 Narrative Engine 결과를 우선 사용한다.
- 기존 Dashboard와 app_stock.py가 기대하는 반환 키는 그대로 유지한다.
- 외부 모듈이 없거나 실패해도 안전하게 fallback한다.

News
 ↓
Theme Graph
 ↓
Reasoning Layer
 ↓
Narrative Engine
 ↓
Dashboard Payload

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


try:
    from stock.reasoning_engine import (
        build_reasoning_layer,
        build_reasoning_brief,
    )
except Exception:
    def build_reasoning_layer(*args, **kwargs):
        return []

    def build_reasoning_brief(reasonings, max_sentences: int = 5):
        return "뚜렷한 AI 추론 체인이 감지되지 않았습니다."


try:
    from stock.narrative_engine import build_market_narrative
except Exception:
    def build_market_narrative(**kwargs):
        return _fallback_narrative(**kwargs)

try:
    from stock.story_graph import build_story_graph
except Exception:
    def build_story_graph(*args, **kwargs):
        return {
            "paths": [],
            "nodes": [],
            "edges": [],
            "primary_path": {},
            "summary": {},
        }
    
try:
    from stock.story_generator import generate_story
except Exception:
    def generate_story(story_graph):
        return {
            "headline": "",
            "summary": "",
            "story": "",
            "flow": [],
            "top_stocks": [],
            "risks": [],
            "checkpoints": [],
        }

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

    기존 호환 반환 키
    - headline
    - summary
    - flow
    - drivers
    - risks
    - watch_points

    v2.6 확장 반환 키
    - narrative
    - story_text
    - theme_graph
    - reasoning_layer
    - dashboard
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
        theme_graph=theme_graph,
        limit=4,
    )

    trading_ideas = _safe_trading_ideas(
        theme_graph=theme_graph,
        limit=3,
    )

    theme_graph_markdown = _safe_theme_graph_markdown(
        theme_graph=theme_graph,
        limit=5,
    )

    reasoning_layer = _safe_reasoning_layer(
        news_items=safe_news_items,
        theme_graph=theme_graph,
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        after_hours_data=safe_after_hours_data,
        indicators=safe_indicators,
        market_decision=safe_market_decision,
        max_items=5,
    )

    # ==========================================
    # NEW : Story Graph
    # ==========================================

    story_graph = build_story_graph(
        reasoning_layer=reasoning_layer,
        theme_graph=theme_graph,
        sector_results=sector_results,
        candidate_scores=candidate_scores,
        after_hours_data=after_hours_data,
        indicators=indicators,
        market_decision=market_decision,
    )

    # ==========================================

    reasoning_brief = _safe_reasoning_brief(
        reasoning_layer=reasoning_layer,
        max_sentences=5,
    )

    story_score = _build_story_score(
        market_decision=safe_market_decision,
        news_items=safe_news_items,
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        after_hours_data=safe_after_hours_data,
        dart_items=safe_dart_items,
        theme_graph=theme_graph,
        reasoning_layer=reasoning_layer,
    )

    market_temperature = _build_market_temperature(story_score)

    raw_risks = _build_basic_risks(
        market_decision=safe_market_decision,
        candidate_scores=safe_candidate_scores,
        after_hours_data=safe_after_hours_data,
        dart_items=safe_dart_items,
        story_score=story_score,
    )

    opportunities = _build_basic_opportunities(
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        theme_graph=theme_graph,
        after_hours_data=safe_after_hours_data,
        reasoning_layer=reasoning_layer,
    )

    raw_watch_points = _build_basic_watch_points(
        candidate_scores=safe_candidate_scores,
        dart_items=safe_dart_items,
        trading_ideas=trading_ideas,
        risks=raw_risks,
        reasoning_layer=reasoning_layer,
    )

    narrative = _safe_market_narrative(
        market_decision=safe_market_decision,
        reasoning_layer=reasoning_layer,
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        risks=raw_risks,
        opportunities=opportunities,
        watch_points=raw_watch_points,
        story_score=story_score,
        market_temperature=market_temperature,
        news_count=len(safe_news_items),
        money_flow_story=money_flow_story,
        theme_summary=theme_summary,
    )

    # v2.7: Narrative Engine 결과를 그대로 쓰지 않고
    # 기사형 문단 / 시장 관련 핵심 흐름 / 무관 뉴스 제거 기준으로 한 번 더 정제한다.
    narrative = _polish_narrative(
        narrative=narrative,
        market_decision=safe_market_decision,
        news_items=safe_news_items,
        sector_results=safe_sector_results,
        candidate_scores=safe_candidate_scores,
        after_hours_data=safe_after_hours_data,
        indicators=safe_indicators,
        theme_graph=theme_graph,
        reasoning_layer=reasoning_layer,
        risks=raw_risks,
        opportunities=opportunities,
        watch_points=raw_watch_points,
        story_score=story_score,
        market_temperature=market_temperature,
        news_count=len(safe_news_items),
    )

    headline = _clean_text(narrative.get("headline")) or _fallback_headline(
        market_decision=safe_market_decision,
        sector_results=safe_sector_results,
        theme_graph=theme_graph,
    )

    summary = _clean_text(narrative.get("summary")) or _clean_text(narrative.get("lead"))
    if not summary:
        summary = _fallback_summary(
            market_decision=safe_market_decision,
            sector_results=safe_sector_results,
            story_score=story_score,
            market_temperature=market_temperature,
            reasoning_brief=reasoning_brief,
        )

    flow = _safe_text_list(narrative.get("flow"))
    if not flow:
        flow = _fallback_flow(
            news_items=safe_news_items,
            sector_results=safe_sector_results,
            candidate_scores=safe_candidate_scores,
            theme_graph=theme_graph,
            reasoning_layer=reasoning_layer,
            money_flow_story=money_flow_story,
        )

    drivers = _safe_text_list(narrative.get("drivers"))
    if not drivers:
        drivers = _fallback_drivers(
            news_items=safe_news_items,
            after_hours_data=safe_after_hours_data,
            sector_results=safe_sector_results,
            theme_graph=theme_graph,
            reasoning_layer=reasoning_layer,
        )

    risks = _safe_text_list(narrative.get("risks")) or raw_risks
    watch_points = _safe_text_list(narrative.get("checkpoints")) or raw_watch_points

    story_text = _clean_text(narrative.get("story_text"))
    recommendation = _build_recommendation(
        market_decision=safe_market_decision,
        story_score=story_score,
        market_temperature=market_temperature,
        risks=risks,
        opportunities=opportunities,
    )

    strategy_comment = _build_strategy_comment(
        market_decision=safe_market_decision,
        story_score=story_score,
        market_temperature=market_temperature,
        narrative=narrative,
        top_sector=_clean_text(narrative.get("top_sector")) or _top_sector_name(safe_sector_results),
        top_theme=_clean_text(narrative.get("top_theme")) or _top_theme_name(theme_graph),
    )

    dashboard = _build_dashboard_payload(
        headline=headline,
        story_score=story_score,
        market_temperature=market_temperature,
        sector_results=safe_sector_results,
        theme_graph=theme_graph,
        candidate_scores=safe_candidate_scores,
        risks=risks,
        opportunities=opportunities,
        reasoning_layer=reasoning_layer,
        narrative=narrative,
    )

    return {
        # 기존 호환 키
        "headline": headline,
        "summary": summary,
        "flow": flow,
        "drivers": drivers,
        "risks": risks,
        "watch_points": watch_points,

        # v2.6 Narrative 중심 키
        "narrative": narrative,
        "story_text": story_text,
        "narrative_summary": summary,

        # 기존 확장 키 유지
        "theme_graph": theme_graph,
        "theme_summary": theme_summary,
        "theme_graph_markdown": theme_graph_markdown,
        "money_flow_story": money_flow_story,
        "trading_ideas": trading_ideas,
        "reasoning_layer": reasoning_layer,
        "reasoning_brief": reasoning_brief,
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
        return [_as_dict(x) for x in _as_list(result)][:limit]
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


def _safe_reasoning_layer(
    news_items: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    market_decision: Dict[str, Any],
    max_items: int = 5,
) -> List[Dict[str, Any]]:
    try:
        result = build_reasoning_layer(
            news_items=news_items,
            theme_graph=theme_graph,
            sector_results=sector_results,
            candidate_scores=candidate_scores,
            after_hours_data=after_hours_data,
            indicators=indicators,
            market_decision=market_decision,
            max_items=max_items,
            min_confidence=0.30,
        )
        return [_as_dict(item) for item in _as_list(result)][:max_items]
    except Exception:
        return []


def _safe_reasoning_brief(
    reasoning_layer: List[Dict[str, Any]],
    max_sentences: int = 5,
) -> str:
    try:
        text = build_reasoning_brief(reasoning_layer, max_sentences=max_sentences)
        return _clean_text(text) or "뚜렷한 AI 추론 체인이 감지되지 않았습니다."
    except Exception:
        return "뚜렷한 AI 추론 체인이 감지되지 않았습니다."


def _safe_market_narrative(
    *,
    market_decision: Dict[str, Any],
    reasoning_layer: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    risks: List[str],
    opportunities: List[str],
    watch_points: List[str],
    story_score: int,
    market_temperature: str,
    news_count: int,
    money_flow_story: str,
    theme_summary: str,
) -> Dict[str, Any]:
    try:
        narrative = build_market_narrative(
            market_decision=market_decision,
            reasoning_layer=reasoning_layer,
            sector_results=sector_results,
            candidate_scores=candidate_scores,
            risks=risks,
            opportunities=opportunities,
            watch_points=watch_points,
            story_score=story_score,
            market_temperature=market_temperature,
            news_count=news_count,
            money_flow_story=money_flow_story,
            theme_summary=theme_summary,
        )
        return _as_dict(narrative)
    except Exception:
        return _fallback_narrative(
            market_decision=market_decision,
            reasoning_layer=reasoning_layer,
            sector_results=sector_results,
            candidate_scores=candidate_scores,
            risks=risks,
            opportunities=opportunities,
            watch_points=watch_points,
            story_score=story_score,
            market_temperature=market_temperature,
            news_count=news_count,
            money_flow_story=money_flow_story,
            theme_summary=theme_summary,
        )


# --------------------------------------------------------
# Narrative fallback
# --------------------------------------------------------

def _fallback_narrative(
    *,
    market_decision: Optional[Dict[str, Any]] = None,
    reasoning_layer: Optional[Sequence[Dict[str, Any]]] = None,
    sector_results: Optional[Sequence[Dict[str, Any]]] = None,
    candidate_scores: Optional[Sequence[Dict[str, Any]]] = None,
    risks: Optional[Sequence[Any]] = None,
    opportunities: Optional[Sequence[Any]] = None,
    watch_points: Optional[Sequence[Any]] = None,
    story_score: int = 50,
    market_temperature: str = "중립",
    news_count: int = 0,
    money_flow_story: str = "",
    theme_summary: str = "",
    **kwargs,
) -> Dict[str, Any]:
    md = _as_dict(market_decision)
    reasonings = [_as_dict(x) for x in _as_list(reasoning_layer)]
    sectors = [_as_dict(x) for x in _as_list(sector_results)]
    candidates = [_as_dict(x) for x in _as_list(candidate_scores)]

    top = reasonings[0] if reasonings else {}
    top_theme = _clean_text(top.get("theme")) or _top_sector_name(sectors) or "주도 테마"
    top_sector = _clean_text(top.get("sector")) or _top_sector_name(sectors) or top_theme
    top_stocks = _reasoning_stocks(top, limit=3) or _top_candidate_names(candidates, limit=3)
    chain = _reasoning_chain(top)

    strategy = _clean_text(md.get("strategy")) or _strategy_from_score(story_score)
    confidence = _to_float(top.get("confidence"))
    confidence_label = _confidence_label(confidence)

    headline = f"{top_theme} 중심 {strategy} 전략"

    stock_text = ", ".join(top_stocks[:2]) if top_stocks else ""
    lead = (
        f"오늘 시장은 {top_theme} 흐름을 중심으로 {top_sector} 업종의 투자심리를 점검하는 구간입니다. "
        f"시장 온도는 {market_temperature}, 전략은 {strategy}입니다."
    )
    if stock_text:
        lead += f" 대표 관심 종목은 {stock_text}입니다."
    if confidence_label:
        lead += f" 현재 추론 신뢰도는 {confidence_label} 수준입니다."

    body: List[str] = []
    if chain:
        short_chain = " → ".join(chain[:5])
        if stock_text:
            body.append(f"핵심 추론은 {short_chain} 흐름이 {stock_text} 등 대표 종목으로 연결되는 구조입니다.")
        else:
            body.append(f"핵심 추론은 {short_chain} 흐름으로 정리됩니다.")

    cause = _clean_text(top.get("cause"))
    effect = _clean_text(top.get("effect"))
    if cause and not _text_similar(cause, body):
        body.append(cause)
    if effect and not _text_similar(effect, body):
        body.append(effect)

    opps = _unique_texts(opportunities or [])
    if opps and not _text_similar(opps[0], body):
        body.append(opps[0])

    for item in reasonings[1:3]:
        theme = _clean_text(item.get("theme"))
        sector = _clean_text(item.get("sector")) or theme
        conf = _confidence_label(_to_float(item.get("confidence")))
        if theme:
            body.append(f"보조 흐름으로는 {theme} 테마가 확인되며, {sector} 업종은 {conf} 신뢰도로 관찰 대상입니다.")

    risk_out = _unique_texts(risks or [])
    if not risk_out:
        risk_out = ["장 초반 지수 방향성과 거래대금 변화에 따라 변동성이 확대될 수 있습니다."]

    checkpoints = _unique_texts([
        "시초가 갭이 과도하게 벌어지는지 확인",
        "장 초반 거래량이 전일 평균 대비 유지되는지 확인",
        "외국인·기관 수급이 매수 우위로 전환되는지 확인",
    ] + _as_list(watch_points))[:7]

    flow = []
    if news_count:
        flow.append(f"주요 뉴스 {news_count}건이 장전 투자심리 형성에 반영됐습니다.")
    flow.append(f"핵심 테마는 {top_theme}입니다.")
    flow.append(f"섹터 흐름은 {top_sector}를 중심으로 확인됩니다.")
    if top_stocks:
        flow.append("대표 관심 종목: " + ", ".join(top_stocks[:3]))
    if chain:
        flow.append("AI 추론 흐름: " + " → ".join(chain[:6]))

    drivers = []
    if top_sector:
        drivers.append(f"{top_sector} 섹터 중심 투자심리")
    if cause:
        drivers.append(cause)
    if effect:
        drivers.append(effect)
    evidence = top.get("evidence")
    if isinstance(evidence, list):
        drivers.extend(_unique_texts(evidence[:3]))

    story_text = " ".join(_unique_texts([headline, lead] + body + [f"리스크는 {risk_out[0]}", "장 시작 후에는 " + ", ".join(checkpoints[:3]) + "이 필요합니다."]))

    return {
        "headline": headline,
        "lead": lead,
        "body": _unique_texts(body)[:6],
        "summary": lead + " " + " ".join(_unique_texts(body)[:3]),
        "story_text": story_text,
        "flow": _unique_texts(flow)[:6],
        "drivers": _unique_texts(drivers)[:7],
        "risks": risk_out[:5],
        "checkpoints": checkpoints,
        "top_theme": top_theme,
        "top_sector": top_sector,
        "top_stocks": top_stocks,
        "top_chain": " → ".join(chain[:7]),
        "confidence": confidence,
        "confidence_label": confidence_label,
        "strategy": strategy,
    }



# --------------------------------------------------------
# v2.7 Narrative polish layer
# --------------------------------------------------------

def _polish_narrative(
    *,
    narrative: Dict[str, Any],
    market_decision: Dict[str, Any],
    news_items: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    reasoning_layer: List[Dict[str, Any]],
    risks: List[str],
    opportunities: List[str],
    watch_points: List[str],
    story_score: int,
    market_temperature: str,
    news_count: int,
) -> Dict[str, Any]:
    """Narrative Engine의 1차 결과를 화면 출력용으로 재정리한다."""
    n = dict(_as_dict(narrative))

    top_reasoning = _top_reasoning(reasoning_layer)
    top_theme = (
        _clean_text(n.get("top_theme"))
        or _clean_text(top_reasoning.get("theme"))
        or _top_theme_name(theme_graph)
        or _top_sector_name(sector_results)
        or "주도 테마"
    )
    top_sector = (
        _clean_text(n.get("top_sector"))
        or _clean_text(top_reasoning.get("sector"))
        or _top_sector_name(sector_results)
        or top_theme
    )
    top_stocks = (
        _safe_text_list(n.get("top_stocks"))
        or _reasoning_stocks(top_reasoning, limit=3)
        or _top_candidate_names(candidate_scores, limit=3)
    )
    chain = _reasoning_chain(top_reasoning)
    strategy = _clean_text(n.get("strategy")) or _clean_text(market_decision.get("strategy")) or _strategy_from_score(story_score)
    confidence = _to_float(n.get("confidence"))
    if confidence is None:
        confidence = _to_float(top_reasoning.get("confidence"))
    confidence_label = _confidence_label(confidence)

    polished_summary = _build_article_summary(
        top_theme=top_theme,
        top_sector=top_sector,
        top_stocks=top_stocks,
        chain=chain,
        top_reasoning=top_reasoning,
        risks=risks,
        opportunities=opportunities,
        story_score=story_score,
        market_temperature=market_temperature,
        strategy=strategy,
        confidence_label=confidence_label,
    )

    polished_flow = _build_polished_flow(
        news_count=news_count,
        top_theme=top_theme,
        top_sector=top_sector,
        top_stocks=top_stocks,
        chain=chain,
        narrative=n,
    )

    polished_drivers = _build_polished_drivers(
        top_theme=top_theme,
        top_sector=top_sector,
        top_reasoning=top_reasoning,
        reasonings=reasoning_layer,
        after_hours_data=after_hours_data,
        indicators=indicators,
        news_items=news_items,
        raw_drivers=_safe_text_list(n.get("drivers")),
    )

    polished_risks = _build_polished_risks(
        risks=risks,
        market_decision=market_decision,
        indicators=indicators,
        after_hours_data=after_hours_data,
        candidate_scores=candidate_scores,
        story_score=story_score,
    )

    polished_checkpoints = _build_polished_checkpoints(
        watch_points=watch_points,
        top_theme=top_theme,
        top_stocks=top_stocks,
    )

    headline = _clean_text(n.get("headline")) or f"{top_theme} 중심 {strategy} 전략"

    story_text = " ".join(
        _unique_texts(
            [headline, polished_summary]
            + [f"핵심 흐름은 {' → '.join(chain[:5])}입니다." if chain else ""]
            + [f"리스크는 {polished_risks[0]}" if polished_risks else ""]
            + [f"장 시작 후에는 {', '.join(polished_checkpoints[:3])}이 필요합니다." if polished_checkpoints else ""]
        )
    )

    n.update(
        {
            "headline": headline,
            "lead": polished_summary,
            "summary": polished_summary,
            "story_text": story_text,
            "flow": polished_flow,
            "drivers": polished_drivers,
            "risks": polished_risks,
            "checkpoints": polished_checkpoints,
            "top_theme": top_theme,
            "top_sector": top_sector,
            "top_stocks": top_stocks,
            "top_chain": " → ".join(chain[:7]),
            "confidence": confidence,
            "confidence_label": confidence_label,
            "strategy": strategy,
        }
    )
    return n


def _build_article_summary(
    *,
    top_theme: str,
    top_sector: str,
    top_stocks: List[str],
    chain: List[str],
    top_reasoning: Dict[str, Any],
    risks: List[str],
    opportunities: List[str],
    story_score: int,
    market_temperature: str,
    strategy: str,
    confidence_label: str,
) -> str:
    stock_text = ", ".join(top_stocks[:2]) if top_stocks else ""
    cause = _clean_text(top_reasoning.get("cause"))
    effect = _clean_text(top_reasoning.get("effect"))

    sentences: List[str] = []

    if story_score >= 65:
        tone = "투자심리가 우호적으로 형성될 가능성이 있습니다"
    elif story_score >= 50:
        tone = "선별적인 매수세가 유입될 가능성이 있습니다"
    else:
        tone = "장 초반 방향성 확인이 우선인 구간입니다"

    sentences.append(f"오늘 시장은 {top_theme} 흐름을 중심으로 {top_sector} 업종의 {tone}.")
    sentences.append(f"시장 온도는 {market_temperature}, 현재 전략은 {strategy}입니다.")

    if chain:
        if len(chain) >= 4:
            front = " → ".join(chain[:4])
            sentences.append(f"핵심 추론은 {front} 흐름이 국내 {top_sector} 투자심리로 연결되는 구조입니다.")
        else:
            sentences.append(f"핵심 추론은 {' → '.join(chain)} 흐름으로 정리됩니다.")

    if effect and not _text_similar(effect, sentences):
        sentences.append(effect)
    elif cause and not _text_similar(cause, sentences):
        sentences.append(cause)

    if stock_text:
        sentences.append(f"대표 관심 종목은 {stock_text}이며, 장 초반 거래량과 수급 지속 여부가 관건입니다.")

    if opportunities:
        opp = _clean_text(opportunities[0])
        if opp and not _text_similar(opp, sentences):
            sentences.append(opp)

    if risks:
        risk = _clean_text(risks[0])
        if risk:
            sentences.append(f"다만 {risk}")

    if confidence_label:
        sentences.append(f"현재 추론 신뢰도는 {confidence_label} 수준입니다.")

    return " ".join(_unique_texts(sentences)[:7])


def _build_polished_flow(
    *,
    news_count: int,
    top_theme: str,
    top_sector: str,
    top_stocks: List[str],
    chain: List[str],
    narrative: Dict[str, Any],
) -> List[str]:
    flow: List[str] = []

    if news_count:
        flow.append(f"주요 뉴스 {news_count}건 중 시장 관련 신호가 장전 투자심리에 반영됐습니다.")

    if top_theme:
        flow.append(f"핵심 테마는 {top_theme}입니다.")

    if top_sector:
        flow.append(f"섹터 흐름은 {top_sector}를 중심으로 확인됩니다.")

    if top_stocks:
        flow.append("대표 관심 종목: " + ", ".join(top_stocks[:3]))

    if chain:
        flow.append("AI 추론 흐름: " + " → ".join(chain[:6]))

    for item in _safe_text_list(narrative.get("flow")):
        if _is_low_value_flow(item):
            continue
        if not _text_similar(item, flow):
            flow.append(item)

    return _unique_texts(flow)[:6]


def _build_polished_drivers(
    *,
    top_theme: str,
    top_sector: str,
    top_reasoning: Dict[str, Any],
    reasonings: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    news_items: List[Dict[str, Any]],
    raw_drivers: List[str],
) -> List[str]:
    drivers: List[str] = []

    if top_sector:
        drivers.append(f"{top_sector} 섹터 중심 투자심리")

    cause = _clean_text(top_reasoning.get("cause"))
    effect = _clean_text(top_reasoning.get("effect"))
    if cause:
        drivers.append(cause)
    if effect:
        drivers.append(effect)

    for item in reasonings[1:3]:
        theme = _clean_text(item.get("theme"))
        if theme and theme != top_theme:
            drivers.append(f"보조 테마: {theme}")

    for item in after_hours_data[:5]:
        item = _as_dict(item)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("rate") or item.get("등락률"))
        if name and pct is not None and abs(pct) >= 2.0:
            drivers.append(f"{name} 시간외 {pct:+.2f}%")

    for item in indicators[:8]:
        item = _as_dict(item)
        name = _clean_text(item.get("name"))
        pct = _to_float(item.get("change_rate"))
        memo = _clean_text(item.get("memo"))
        if name and pct is not None and _market_driver_indicator(name, memo):
            drivers.append(f"{name} {pct:+.2f}%: {memo or '장전 투자심리 변수'}")

    for item in news_items[:8]:
        title = _clean_text(_as_dict(item).get("title") or _as_dict(item).get("headline"))
        if title and _is_market_relevant_text(title):
            drivers.append(f"뉴스 모멘텀: {_shorten(title, 46)}")

    for item in raw_drivers:
        if _is_irrelevant_news_fragment(item):
            continue
        if _is_low_value_flow(item):
            continue
        drivers.append(item)

    return _unique_texts(drivers)[:7]


def _build_polished_risks(
    *,
    risks: List[str],
    market_decision: Dict[str, Any],
    indicators: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    story_score: int,
) -> List[str]:
    out: List[str] = _unique_texts(risks or [])

    for item in indicators:
        item = _as_dict(item)
        name = _clean_text(item.get("name"))
        pct = _to_float(item.get("change_rate"))

        if pct is None:
            continue
        if name in ("엔비디아", "나스닥", "S&P500") and pct <= -1.0:
            out.append(f"{name} 약세로 성장주·AI 투자심리에 부담이 생길 수 있습니다.")
        if name in ("테슬라",) and pct <= -2.0:
            out.append("테슬라 약세로 2차전지·전기차 관련주는 장 초반 변동성에 유의해야 합니다.")
        if name in ("WTI유가",) and pct >= 2.0:
            out.append("유가 상승은 정유에는 우호적일 수 있으나 비용 부담 업종에는 리스크입니다.")
        if name in ("달러/원",) and abs(pct) >= 0.5:
            out.append("환율 변동성이 커질 경우 외국인 수급과 수출주 흐름을 함께 확인해야 합니다.")

    for item in after_hours_data[:6]:
        item = _as_dict(item)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("등락률"))
        if name and pct is not None and pct <= -3:
            out.append(f"{name} 시간외 약세가 장 초반 변동성으로 이어질 수 있습니다.")

    if len(candidate_scores) >= 8:
        out.append("관심 종목이 많아 단기 과열과 수급 분산 가능성이 있습니다.")

    if story_score < 55:
        out.append("시장 점수가 충분히 높지 않아 신규 매수보다 확인 후 대응이 필요합니다.")

    if not out:
        out.append("뚜렷한 구조적 위험은 제한적이나 장 초반 지수 방향과 거래대금 확인이 필요합니다.")

    return _unique_texts(out)[:6]


def _build_polished_checkpoints(
    *,
    watch_points: List[str],
    top_theme: str,
    top_stocks: List[str],
) -> List[str]:
    out = [
        "시초가 갭이 과도하게 벌어지는지 확인",
        "장 초반 거래량이 전일 평균 대비 유지되는지 확인",
        "외국인·기관 수급이 매수 우위로 전환되는지 확인",
    ]

    if top_theme:
        out.append(f"{top_theme} 대장주가 초반 강세를 유지하는지 확인")

    if top_stocks:
        out.append(f"{top_stocks[0]}의 첫 30분 체결 강도 확인")

    out.extend(_safe_text_list(watch_points))
    return _unique_texts(out)[:7]


def _market_driver_indicator(name: str, memo: str = "") -> bool:
    text = f"{name} {memo}"
    keys = ["나스닥", "S&P500", "엔비디아", "마이크로소프트", "테슬라", "달러", "환율", "WTI", "유가", "반도체", "AI", "클라우드"]
    return any(k in text for k in keys)


def _is_market_relevant_text(text: str) -> bool:
    text = _clean_text(text)
    if not text:
        return False
    include = ["반도체", "AI", "엔비디아", "HBM", "삼성전자", "SK하이닉스", "마이크로소프트", "구글", "데이터센터", "클라우드", "원전", "SMR", "전력", "2차전지", "전기차", "테슬라", "자동차", "수출", "환율", "유가", "금리", "코스피", "조선", "방산", "바이오", "금융", "수주", "실적"]
    exclude = ["임명피해", "서버스 가루", "인근서", "시민서비스", "병명 변경", "강조한 조국혁신당", "자장", "딤터"]
    if any(x in text for x in exclude):
        return False
    return any(x in text for x in include)


def _is_irrelevant_news_fragment(text: str) -> bool:
    text = _clean_text(text)
    if not text:
        return True
    if text.startswith("뉴스 단서") or text.startswith("뉴스 모멘텀"):
        return not _is_market_relevant_text(text)
    return False


def _is_low_value_flow(text: str) -> bool:
    text = _clean_text(text)
    low_values = ["뚜렷한 테마 자금 흐름은 아직 확인되지 않았습니다", "테마 간 자금 이동은 장 초반 거래량 확인이 필요합니다", "감지되지 않았습니다"]
    return any(x in text for x in low_values)


# --------------------------------------------------------
# Basic generators
# --------------------------------------------------------

def _build_basic_risks(
    market_decision: Dict[str, Any],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    dart_items: List[Dict[str, Any]],
    story_score: int,
) -> List[str]:
    risks: List[str] = []

    if len(candidate_scores) >= 8:
        risks.append("관심 종목이 많아 단기 과열 및 수급 분산 가능성이 있습니다.")

    decision_score = _to_float(market_decision.get("score"))
    if decision_score is not None and decision_score < 60:
        risks.append("시장 판단 점수가 높지 않아 공격적 비중 확대에는 신중할 필요가 있습니다.")

    if story_score < 45:
        risks.append("뉴스·섹터·종목 신호의 결합 강도가 약해 장 초반 변동성 확대에 유의해야 합니다.")

    weak = []
    for item in after_hours_data[:8]:
        item = _as_dict(item)
        pct = _to_float(
            item.get("after_change_pct")
            or item.get("change_pct")
            or item.get("rate")
            or item.get("등락률")
        )
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if name and pct is not None and pct <= -3:
            weak.append(f"{name} 시간외 급락")
    risks.extend(weak[:3])

    if dart_items:
        risks.append("공시 재료가 포함돼 있어 세부 내용 확인 전까지 해석 리스크가 있습니다.")

    if not risks:
        risks.append("뚜렷한 구조적 위험은 제한적이나 장 초반 거래대금과 지수 방향 확인이 필요합니다.")

    return _unique_texts(risks)[:8]


def _build_basic_opportunities(
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    reasoning_layer: List[Dict[str, Any]],
) -> List[str]:
    opportunities: List[str] = []

    top_reasoning = _top_reasoning(reasoning_layer)
    top_theme = _clean_text(top_reasoning.get("theme")) or _top_theme_name(theme_graph)
    top_sector = _clean_text(top_reasoning.get("sector")) or _top_sector_name(sector_results)

    if top_theme:
        opportunities.append(f"{top_theme} 테마가 뉴스와 수급의 공통 축으로 연결될 경우 주도 테마로 확장될 수 있습니다.")

    if top_sector:
        opportunities.append(f"{top_sector} 섹터 내 대장주와 후속주의 순환매 가능성을 점검할 필요가 있습니다.")

    names = _top_candidate_names(candidate_scores, limit=3)
    if names:
        opportunities.append("관심 종목군에서는 " + ", ".join(names) + "의 장 초반 거래량 지속 여부가 핵심입니다.")

    strong = []
    for item in after_hours_data[:8]:
        item = _as_dict(item)
        pct = _to_float(
            item.get("after_change_pct")
            or item.get("change_pct")
            or item.get("rate")
            or item.get("등락률")
        )
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if name and pct is not None and pct >= 3:
            strong.append(f"{name} 시간외 강세 연속성")
    opportunities.extend(strong[:3])

    if not opportunities:
        opportunities.append("장 초반에는 단일 테마보다 거래대금이 집중되는 종목 중심의 선별 접근이 유리합니다.")

    return _unique_texts(opportunities)[:8]


def _build_basic_watch_points(
    candidate_scores: List[Dict[str, Any]],
    dart_items: List[Dict[str, Any]],
    trading_ideas: List[str],
    risks: List[str],
    reasoning_layer: List[Dict[str, Any]],
) -> List[str]:
    top_reasoning = _top_reasoning(reasoning_layer)
    top_theme = _clean_text(top_reasoning.get("theme"))

    watch = [
        "시초가 갭 확인",
        "거래량 유지 여부",
        "외국인·기관 수급 확인",
        "대장주와 후속주 순환 여부 확인",
    ]

    if top_theme:
        watch.append(f"{top_theme} 대장주가 초반 강세를 유지하는지 확인")

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


# --------------------------------------------------------
# Strategy / dashboard
# --------------------------------------------------------

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

    opp = opportunities[0] if opportunities else "뚜렷한 기회 요인은 제한적입니다."
    risk = risks[0] if risks else "특별한 위험 요인은 제한적입니다."

    return {
        "label": label,
        "stance": stance,
        "score": story_score,
        "temperature": market_temperature,
        "reason": f"{label}: {opp} 다만 {risk}",
        "risk_count": len(risks),
        "opportunity_count": len(opportunities),
        "market_strategy": _clean_text(market_decision.get("strategy")) or "중립",
    }


def _build_strategy_comment(
    market_decision: Dict[str, Any],
    story_score: int,
    market_temperature: str,
    narrative: Dict[str, Any],
    top_sector: str = "",
    top_theme: str = "",
) -> str:
    strategy = _clean_text(narrative.get("strategy")) or _clean_text(market_decision.get("strategy")) or "중립"
    focus = _clean_text(narrative.get("top_theme")) or top_theme or top_sector or "거래대금 상위 종목"

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

    return f"현재 전략은 {strategy}, 시장 온도는 {market_temperature}입니다. {focus}를 중심으로 {tone} {action}"


def _build_dashboard_payload(
    headline: str,
    story_score: int,
    market_temperature: str,
    sector_results: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    risks: List[str],
    opportunities: List[str],
    reasoning_layer: List[Dict[str, Any]],
    narrative: Dict[str, Any],
) -> Dict[str, Any]:
    top_reasoning = _top_reasoning(reasoning_layer)

    return {
        "headline": headline,
        "story_score": story_score,
        "market_temperature": market_temperature,
        "top_sector": _clean_text(narrative.get("top_sector")) or _top_sector_name(sector_results) or "-",
        "top_theme": _clean_text(narrative.get("top_theme")) or _top_theme_name(theme_graph) or "-",
        "top_candidates": _safe_text_list(narrative.get("top_stocks")) or _top_candidate_names(candidate_scores, limit=5),
        "risk_count": len(risks),
        "opportunity_count": len(opportunities),
        "top_reasoning": top_reasoning or {},
        "reasoning_chain": _clean_text(narrative.get("top_chain")) or _reasoning_chain_text(top_reasoning),
        "confidence": narrative.get("confidence"),
        "confidence_label": narrative.get("confidence_label"),
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
    reasoning_layer: Optional[List[Dict[str, Any]]] = None,
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

    if reasoning_layer:
        top = _as_dict(reasoning_layer[0])
        confidence = _to_float(top.get("confidence"))
        if confidence is not None:
            score += max(0, min(8, confidence * 8))

    positive_after_hours = 0
    negative_after_hours = 0
    for item in after_hours_data[:10]:
        item = _as_dict(item)
        pct = _to_float(
            item.get("after_change_pct")
            or item.get("change_pct")
            or item.get("rate")
            or item.get("등락률")
        )
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

def _fallback_headline(
    market_decision: Dict[str, Any],
    sector_results: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
) -> str:
    strategy = _clean_text(market_decision.get("strategy")) or "중립"
    top_theme = _top_theme_name(theme_graph)
    top_sector = _top_sector_name(sector_results)

    if top_theme:
        return f"{top_theme} 중심 {strategy} 전략"
    if top_sector:
        return f"{top_sector} 중심 {strategy} 전략"
    return f"{strategy} 전략"


def _fallback_summary(
    market_decision: Dict[str, Any],
    sector_results: List[Dict[str, Any]],
    story_score: int,
    market_temperature: str,
    reasoning_brief: str,
) -> str:
    strategy = _clean_text(market_decision.get("strategy")) or "중립"
    top_sector = _top_sector_name(sector_results)

    if top_sector:
        base = f"오늘 시장은 {top_sector} 중심의 흐름이 우선 확인됩니다. "
    else:
        base = "오늘 시장은 뚜렷한 단일 주도 섹터보다 선별적인 흐름이 예상됩니다. "

    base += f"시장 온도는 {market_temperature} 구간이며, 현재 전략은 {strategy}입니다."

    if reasoning_brief and "감지되지" not in reasoning_brief:
        base += " " + _clean_text(reasoning_brief)

    return base


def _fallback_flow(
    news_items: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    reasoning_layer: List[Dict[str, Any]],
    money_flow_story: str,
) -> List[str]:
    flow: List[str] = []

    if news_items:
        flow.append(f"주요 뉴스 {len(news_items)}건이 장전 투자심리 형성에 반영됐습니다.")

    top_theme = _top_theme_name(theme_graph)
    if top_theme:
        flow.append(f"테마 그래프에서는 {top_theme} 테마가 우선 부각됐습니다.")

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        flow.append(f"섹터 흐름은 {top_sector}가 상대적으로 강하게 나타났습니다.")

    names = _top_candidate_names(candidate_scores, limit=3)
    if names:
        flow.append("대표 관심 종목: " + ", ".join(names))

    top_reasoning = _top_reasoning(reasoning_layer)
    chain = _reasoning_chain_text(top_reasoning)
    if chain:
        flow.append(f"AI 추론 흐름: {chain}")

    if money_flow_story:
        flow.append(money_flow_story)

    return _unique_texts(flow)[:8]


def _fallback_drivers(
    news_items: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    reasoning_layer: List[Dict[str, Any]],
) -> List[str]:
    drivers: List[str] = []

    top_theme = _top_theme_name(theme_graph)
    if top_theme:
        drivers.append(f"{top_theme} 테마 부각")

    top_sector = _top_sector_name(sector_results)
    if top_sector:
        drivers.append(f"{top_sector} 섹터 강세")

    top_reasoning = _top_reasoning(reasoning_layer)
    cause = _clean_text(top_reasoning.get("cause"))
    effect = _clean_text(top_reasoning.get("effect"))
    if cause:
        drivers.append(cause)
    if effect:
        drivers.append(effect)

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


def _top_reasoning(reasoning_layer: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not reasoning_layer:
        return {}
    return _as_dict(reasoning_layer[0])


def _reasoning_chain_text(reasoning: Dict[str, Any]) -> str:
    chain = _as_dict(reasoning).get("chain")
    if isinstance(chain, list):
        return " → ".join([_clean_text(item) for item in chain if _clean_text(item)][:6])
    return _clean_text(chain)


def _reasoning_chain(reasoning: Dict[str, Any]) -> List[str]:
    chain = _as_dict(reasoning).get("chain")
    if isinstance(chain, list):
        return _unique_texts(chain)
    text = _clean_text(chain)
    if not text:
        return []
    return _unique_texts([x.strip() for x in text.split("→")])


def _reasoning_stocks(reasoning: Dict[str, Any], limit: int = 3) -> List[str]:
    stocks = _as_dict(reasoning).get("stocks")
    if not isinstance(stocks, list):
        return []
    return _unique_texts(stocks)[:limit]


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


def _top_candidate_names(candidate_scores: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    names: List[str] = []
    for item in candidate_scores[:limit]:
        item = _as_dict(item)
        name = _clean_text(
            item.get("name")
            or item.get("stock_name")
            or item.get("종목명")
            or item.get("stock")
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


def _strategy_from_score(score: int) -> str:
    if score >= 75:
        return "관심 강화"
    if score >= 60:
        return "선별 관심"
    if score >= 45:
        return "중립 관망"
    return "방어 우선"


def _confidence_label(value: Optional[float]) -> str:
    if value is None:
        return "중간"
    if value >= 0.85:
        return "높은"
    if value >= 0.65:
        return "양호한"
    if value >= 0.45:
        return "중간"
    return "낮은"


def _safe_text_list(value: Any) -> List[str]:
    return _unique_texts(_as_list(value))


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
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _text_similar(text: str, existing: Sequence[str]) -> bool:
    target = _clean_text(text).replace(" ", "")
    if not target:
        return False
    for item in existing:
        other = _clean_text(item).replace(" ", "")
        if not other:
            continue
        if target in other or other in target:
            return True
    return False


# --------------------------------------------------------
# Backward-compatible aliases
# --------------------------------------------------------

def build_story(*args, **kwargs) -> Dict[str, Any]:
    """이전 호출부가 build_story를 사용할 경우를 위한 호환 함수."""
    return build_market_story(*args, **kwargs)


def build_ai_market_story(*args, **kwargs) -> Dict[str, Any]:
    """이전 호출부가 build_ai_market_story를 사용할 경우를 위한 호환 함수."""
    return build_market_story(*args, **kwargs)


if __name__ == "__main__":
    sample = build_market_story(
        market_decision={"strategy": "선별 관심", "score": 63},
        news_items=[{"title": "마이크로소프트 AI 데이터센터 투자 확대 기대"}],
        sector_results=[{"sector": "반도체·AI", "score": 80, "stocks": ["삼성전자", "SK하이닉스"]}],
        candidate_scores=[{"name": "삼성전자", "score": 86}, {"name": "SK하이닉스", "score": 91}],
        after_hours_data=[],
        dart_items=[],
        indicators=[],
    )

    from pprint import pprint
    pprint(sample)
