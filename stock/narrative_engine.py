"""
stock/narrative_engine.py
------------------------------------------------------------
v2.5 Narrative Engine

Reasoning Layer 결과를 기사형 시장 브리핑으로 변환한다.
- Reasoning Engine: 인과관계 생성
- Narrative Engine: 중복을 줄인 자연어 기사 생성
- Market Story Engine: 결과 조립 및 Dashboard 전달

Author : MYAIEDITOR
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def build_market_narrative(
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
    max_body_sentences: int = 6,
) -> Dict[str, Any]:
    """
    Reasoning Layer를 한 번만 해석해 시장 브리핑을 생성한다.

    Returns
    -------
    Dict[str, Any]
        headline, lead, body, story_text, flow, drivers, risks, checkpoints,
        confidence_label, top_chain 등을 포함한다.
    """

    md = _as_dict(market_decision)
    reasonings = [_as_dict(x) for x in _as_list(reasoning_layer)]
    sectors = [_as_dict(x) for x in _as_list(sector_results)]
    candidates = [_as_dict(x) for x in _as_list(candidate_scores)]
    risk_list = _unique_texts(risks or [])
    opportunity_list = _unique_texts(opportunities or [])
    checkpoint_list = _unique_texts(watch_points or [])

    top = reasonings[0] if reasonings else {}
    top_theme = _clean_text(top.get("theme")) or _top_sector_name(sectors) or "주도 테마"
    top_sector = _clean_text(top.get("sector")) or _top_sector_name(sectors) or top_theme
    top_stocks = _stock_names_from_reasoning(top) or _top_candidate_names(candidates, limit=3)
    chain = _chain_from_reasoning(top)
    confidence = _to_float(top.get("confidence"))
    confidence_label = _confidence_label(confidence)
    strategy = _clean_text(md.get("strategy")) or _strategy_from_score(story_score)

    headline = _build_headline(
        top_theme=top_theme,
        top_sector=top_sector,
        strategy=strategy,
        story_score=story_score,
    )

    lead = _build_lead(
        top_theme=top_theme,
        top_sector=top_sector,
        top_stocks=top_stocks,
        market_temperature=market_temperature,
        strategy=strategy,
        story_score=story_score,
        confidence_label=confidence_label,
    )

    body = _build_body(
        top=top,
        reasonings=reasonings,
        chain=chain,
        top_theme=top_theme,
        top_sector=top_sector,
        top_stocks=top_stocks,
        opportunities=opportunity_list,
        risks=risk_list,
        money_flow_story=money_flow_story,
        theme_summary=theme_summary,
        max_sentences=max_body_sentences,
    )

    flow = _build_flow(
        news_count=news_count,
        top_theme=top_theme,
        top_sector=top_sector,
        top_stocks=top_stocks,
        chain=chain,
        reasonings=reasonings,
        money_flow_story=money_flow_story,
    )

    drivers = _build_drivers(top=top, reasonings=reasonings, top_sector=top_sector)
    checkpoints = _build_checkpoints(checkpoint_list, top_theme=top_theme)
    risks_out = _build_risks(risk_list)

    story_text = _join_story(headline, lead, body, risks_out, checkpoints)

    return {
        "headline": headline,
        "lead": lead,
        "body": body,
        "story_text": story_text,
        "summary": lead + " " + " ".join(body[:3]),
        "flow": flow,
        "drivers": drivers,
        "risks": risks_out,
        "checkpoints": checkpoints,
        "top_theme": top_theme,
        "top_sector": top_sector,
        "top_stocks": top_stocks,
        "top_chain": " → ".join(chain[:7]),
        "confidence": confidence,
        "confidence_label": confidence_label,
        "strategy": strategy,
    }


def build_story_text(narrative: Dict[str, Any]) -> str:
    """narrative dict에서 기사형 텍스트만 꺼낸다."""
    narrative = _as_dict(narrative)
    return _clean_text(narrative.get("story_text"))


# ------------------------------------------------------------
# Builders
# ------------------------------------------------------------

def _build_headline(top_theme: str, top_sector: str, strategy: str, story_score: int) -> str:
    if story_score >= 75:
        tone = "관심 강화"
    elif story_score >= 60:
        tone = "선별 대응"
    elif story_score >= 45:
        tone = "중립 점검"
    else:
        tone = "방어 우선"

    focus = top_theme or top_sector or "주도주"
    return f"{focus} 중심 {tone} 전략"


def _build_lead(
    *,
    top_theme: str,
    top_sector: str,
    top_stocks: List[str],
    market_temperature: str,
    strategy: str,
    story_score: int,
    confidence_label: str,
) -> str:
    stock_text = _join_names(top_stocks, limit=2)

    if story_score >= 65:
        market_tone = "투자심리가 우호적으로 형성될 가능성이 있습니다"
    elif story_score >= 50:
        market_tone = "선별적인 매수세가 유입될 가능성이 있습니다"
    else:
        market_tone = "장 초반 방향성 확인이 우선인 구간입니다"

    base = (
        f"오늘 시장은 {top_theme} 흐름을 중심으로 {top_sector} 업종의 {market_tone}. "
        f"시장 온도는 {market_temperature}, 전략은 {strategy}입니다."
    )

    if stock_text:
        base += f" 대표 관심 종목은 {stock_text}입니다."

    if confidence_label:
        base += f" 현재 추론 신뢰도는 {confidence_label} 수준입니다."

    return base


def _build_body(
    *,
    top: Dict[str, Any],
    reasonings: List[Dict[str, Any]],
    chain: List[str],
    top_theme: str,
    top_sector: str,
    top_stocks: List[str],
    opportunities: List[str],
    risks: List[str],
    money_flow_story: str,
    theme_summary: str,
    max_sentences: int,
) -> List[str]:
    body: List[str] = []

    cause = _clean_text(top.get("cause"))
    effect = _clean_text(top.get("effect"))

    if chain:
        body.append(_chain_sentence(chain, top_theme=top_theme, top_stocks=top_stocks))
    elif cause:
        body.append(cause)

    if effect and not _is_duplicate(effect, body):
        body.append(effect)

    if opportunities:
        body.append(_normalize_sentence(opportunities[0]))

    # 보조 테마는 최대 2개만 문장화해 반복을 줄인다.
    for item in reasonings[1:3]:
        theme = _clean_text(item.get("theme"))
        sector = _clean_text(item.get("sector")) or theme
        conf = _to_float(item.get("confidence"))
        label = _confidence_label(conf)
        if theme and sector:
            sentence = f"보조 흐름으로는 {theme} 테마가 확인되며, {sector} 업종은 {label} 신뢰도로 관찰 대상입니다."
            if not _is_duplicate(sentence, body):
                body.append(sentence)

    if risks:
        body.append(f"다만 {risks[0]}")

    # theme_summary/money_flow_story는 fallback으로만 사용한다.
    for fallback in (theme_summary, money_flow_story):
        fallback = _clean_text(fallback)
        if fallback and len(body) < 3 and not _is_duplicate(fallback, body):
            body.append(_normalize_sentence(fallback))

    if not body:
        body.append("뚜렷한 주도 테마가 확인되지 않아 장 초반에는 거래대금과 지수 방향성을 먼저 확인해야 합니다.")

    return _unique_texts(body)[:max_sentences]


def _chain_sentence(chain: List[str], top_theme: str, top_stocks: List[str]) -> str:
    clean_chain = [x for x in chain if x]
    stock_text = _join_names(top_stocks, limit=2)

    if len(clean_chain) >= 4:
        cause = " → ".join(clean_chain[: min(4, len(clean_chain))])
        if stock_text:
            return f"핵심 추론은 {cause} 흐름이 {stock_text} 등 대표 종목으로 연결되는 구조입니다."
        return f"핵심 추론은 {cause} 흐름으로 정리됩니다."

    if stock_text:
        return f"{top_theme} 관련 모멘텀이 {stock_text} 등 대표 종목으로 연결되고 있습니다."
    return f"{top_theme} 관련 모멘텀이 시장의 핵심 흐름으로 부각되고 있습니다."


def _build_flow(
    *,
    news_count: int,
    top_theme: str,
    top_sector: str,
    top_stocks: List[str],
    chain: List[str],
    reasonings: List[Dict[str, Any]],
    money_flow_story: str,
) -> List[str]:
    flow: List[str] = []

    if news_count:
        flow.append(f"주요 뉴스 {news_count}건이 장전 투자심리 형성에 반영됐습니다.")

    if top_theme:
        flow.append(f"핵심 테마는 {top_theme}입니다.")

    if top_sector:
        flow.append(f"섹터 흐름은 {top_sector}를 중심으로 확인됩니다.")

    if top_stocks:
        flow.append("대표 관심 종목: " + _join_names(top_stocks, limit=3))

    if chain:
        flow.append("AI 추론 흐름: " + " → ".join(chain[:6]))

    # 기존 money_flow_story가 의미 있는 경우에만 마지막에 넣는다.
    mf = _clean_text(money_flow_story)
    if mf and "확인" not in mf and not _is_duplicate(mf, flow):
        flow.append(mf)

    return _unique_texts(flow)[:6]


def _build_drivers(top: Dict[str, Any], reasonings: List[Dict[str, Any]], top_sector: str) -> List[str]:
    drivers: List[str] = []

    if top_sector:
        drivers.append(f"{top_sector} 섹터 중심 투자심리")

    cause = _clean_text(top.get("cause"))
    effect = _clean_text(top.get("effect"))
    if cause:
        drivers.append(cause)
    if effect:
        drivers.append(effect)

    for item in reasonings[1:3]:
        theme = _clean_text(item.get("theme"))
        if theme:
            drivers.append(f"보조 테마: {theme}")

    evidence = top.get("evidence")
    if isinstance(evidence, list):
        for ev in evidence[:3]:
            text = _clean_text(ev)
            if text:
                drivers.append(text)

    return _unique_texts(drivers)[:7]


def _build_risks(risks: List[str]) -> List[str]:
    if not risks:
        return ["장 초반 지수 방향성과 거래대금 변화에 따라 변동성이 확대될 수 있습니다."]
    return _unique_texts(risks)[:5]


def _build_checkpoints(checkpoints: List[str], top_theme: str) -> List[str]:
    base = [
        "시초가 갭이 과도하게 벌어지는지 확인",
        "장 초반 거래량이 전일 평균 대비 유지되는지 확인",
        "외국인·기관 수급이 매수 우위로 전환되는지 확인",
    ]
    if top_theme:
        base.append(f"{top_theme} 대장주가 초반 강세를 유지하는지 확인")
    base.extend(checkpoints)
    return _unique_texts(base)[:7]


def _join_story(
    headline: str,
    lead: str,
    body: List[str],
    risks: List[str],
    checkpoints: List[str],
) -> str:
    parts: List[str] = []
    if headline:
        parts.append(headline)
    if lead:
        parts.append(lead)
    parts.extend(body)
    if risks:
        parts.append("리스크는 " + risks[0])
    if checkpoints:
        parts.append("장 시작 후에는 " + ", ".join(checkpoints[:3]) + "이 필요합니다.")
    return " ".join(_unique_texts(parts))


# ------------------------------------------------------------
# Extractors / utilities
# ------------------------------------------------------------

def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def _normalize_sentence(text: str) -> str:
    text = _clean_text(text)
    if not text:
        return ""
    if text[-1] not in ".!?다요임함됨음됨니다습니다":
        return text + "."
    return text


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


def _strategy_from_score(score: int) -> str:
    if score >= 75:
        return "관심 강화"
    if score >= 60:
        return "선별 매수"
    if score >= 45:
        return "중립 관망"
    return "방어 우선"


def _top_sector_name(sector_results: List[Dict[str, Any]]) -> str:
    if not sector_results:
        return ""
    top = _as_dict(sector_results[0])
    return _clean_text(top.get("sector") or top.get("name") or top.get("sector_name") or top.get("업종"))


def _top_candidate_names(candidate_scores: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    names: List[str] = []
    for item in candidate_scores[:limit]:
        item = _as_dict(item)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명") or item.get("stock") or item.get("code"))
        if name:
            names.append(name)
    return _unique_texts(names)[:limit]


def _stock_names_from_reasoning(reasoning: Dict[str, Any]) -> List[str]:
    stocks = reasoning.get("stocks")
    if not isinstance(stocks, list):
        return []
    return _unique_texts(stocks)[:5]


def _chain_from_reasoning(reasoning: Dict[str, Any]) -> List[str]:
    chain = reasoning.get("chain")
    if isinstance(chain, list):
        return _unique_texts(chain)
    text = _clean_text(chain)
    if not text:
        return []
    return _unique_texts([x.strip() for x in text.split("→")])


def _join_names(names: List[str], limit: int = 3) -> str:
    clean = _unique_texts(names)[:limit]
    return ", ".join(clean)


def _unique_texts(items: Sequence[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        text = _clean_text(item)
        if not text:
            continue
        key = _dedupe_key(text)
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _dedupe_key(text: str) -> str:
    text = _clean_text(text).lower()
    for token in ("관련 ", "AI ", "뉴스 ", "모멘텀", "기대", "부각", "확인"):
        text = text.replace(token.lower(), "")
    return text[:55]


def _is_duplicate(text: str, existing: Sequence[str]) -> bool:
    key = _dedupe_key(text)
    if not key:
        return False
    for item in existing:
        other = _dedupe_key(item)
        if not other:
            continue
        if key in other or other in key:
            return True
    return False


# ------------------------------------------------------------
# Backward-compatible aliases
# ------------------------------------------------------------

def generate_story(*args, **kwargs) -> Dict[str, Any]:
    return build_market_narrative(*args, **kwargs)


def build_narrative(*args, **kwargs) -> Dict[str, Any]:
    return build_market_narrative(*args, **kwargs)


if __name__ == "__main__":
    sample = build_market_narrative(
        market_decision={"strategy": "중립"},
        reasoning_layer=[
            {
                "theme": "반도체AI",
                "sector": "반도체",
                "stocks": ["삼성전자", "SK하이닉스"],
                "chain": ["Microsoft 강세", "AI 투자 확대", "데이터센터 CAPEX", "HBM 수요", "반도체AI"],
                "cause": "AI 데이터센터 투자 기대가 부각되었습니다.",
                "effect": "HBM·메모리 수요 기대가 강화되며 반도체 업종의 투자심리가 개선될 수 있습니다.",
                "confidence": 0.91,
            }
        ],
        risks=["엔비디아 약세로 AI 투자심리에 부담이 있습니다."],
        watch_points=["대장주와 후속주 순환 여부 확인"],
        story_score=62,
        market_temperature="중립",
        news_count=30,
    )
    from pprint import pprint
    pprint(sample)
