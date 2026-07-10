# stock/story_graph.py
# ------------------------------------------------------------
# MYAIEDITOR Story Graph Engine v3.0
# ------------------------------------------------------------
# 역할
# - reasoning_engine.py와 theme_graph.py 결과를 받아
#   "뉴스 → 원인 → 테마 → 섹터 → 종목 → 체크포인트" 흐름을
#   하나의 Story Graph 객체로 표준화한다.
# - story_generator.py, market_story_engine.py가 이 Graph를 읽어
#   기사형 시장 브리핑을 만들 수 있게 한다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence
import math
import re


# ------------------------------------------------------------
# Data models
# ------------------------------------------------------------

@dataclass
class StoryNode:
    id: str
    label: str
    type: str
    weight: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryPath:
    rank: int
    root_theme: str
    sector: str
    flow: List[str]
    stocks: List[str]
    causes: List[str]
    effects: List[str]
    evidences: List[str]
    risks: List[str]
    checkpoints: List[str]
    confidence: float
    story_strength: float
    market_impact: str
    money_flow: str = ""
    trading_idea: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def build_story_graph(
    *,
    reasoning_layer: Optional[Sequence[Dict[str, Any]]] = None,
    theme_graph: Optional[Sequence[Dict[str, Any]]] = None,
    sector_results: Optional[Sequence[Dict[str, Any]]] = None,
    candidate_scores: Optional[Sequence[Dict[str, Any]]] = None,
    after_hours_data: Optional[Sequence[Dict[str, Any]]] = None,
    indicators: Optional[Sequence[Dict[str, Any]]] = None,
    market_decision: Optional[Dict[str, Any]] = None,
    max_paths: int = 5,
) -> Dict[str, Any]:
    """
    Story Graph 표준 객체를 생성한다.

    반환 구조
    {
        "paths": [...],
        "nodes": [...],
        "edges": [...],
        "primary_path": {...},
        "summary": {...}
    }
    """
    reasonings = [_as_dict(x) for x in _as_list(reasoning_layer)]
    themes = [_as_dict(x) for x in _as_list(theme_graph)]
    sectors = [_as_dict(x) for x in _as_list(sector_results)]
    candidates = [_as_dict(x) for x in _as_list(candidate_scores)]
    after_hours = [_as_dict(x) for x in _as_list(after_hours_data)]
    inds = [_as_dict(x) for x in _as_list(indicators)]
    md = _as_dict(market_decision)

    paths: List[StoryPath] = []

    if reasonings:
        for idx, item in enumerate(reasonings[:max_paths], start=1):
            paths.append(
                _path_from_reasoning(
                    rank=idx,
                    reasoning=item,
                    theme_graph=themes,
                    sector_results=sectors,
                    candidate_scores=candidates,
                    after_hours_data=after_hours,
                    indicators=inds,
                    market_decision=md,
                )
            )
    elif themes:
        for idx, item in enumerate(themes[:max_paths], start=1):
            paths.append(
                _path_from_theme_node(
                    rank=idx,
                    theme_node=item,
                    sector_results=sectors,
                    candidate_scores=candidates,
                    after_hours_data=after_hours,
                    indicators=inds,
                    market_decision=md,
                )
            )
    else:
        paths.append(
            StoryPath(
                rank=1,
                root_theme="시장",
                sector=_top_sector_name(sectors) or "시장 전반",
                flow=["뉴스 흐름", "섹터 점검", "거래량 확인"],
                stocks=_top_candidate_names(candidates, limit=3),
                causes=["뚜렷한 단일 주도 테마는 아직 확인되지 않았습니다."],
                effects=["장 초반 지수 방향성과 거래대금 변화를 먼저 확인할 필요가 있습니다."],
                evidences=[],
                risks=["주도 테마가 약할 경우 종목별 변동성이 커질 수 있습니다."],
                checkpoints=["시초가 갭 확인", "거래량 유지 여부", "외국인·기관 수급 확인"],
                confidence=0.35,
                story_strength=40.0,
                market_impact="LOW",
            )
        )

    paths.sort(key=lambda p: (p.story_strength, p.confidence), reverse=True)
    for idx, p in enumerate(paths, start=1):
        p.rank = idx

    nodes, edges = _build_graph_objects(paths)
    primary = paths[0].to_dict() if paths else {}

    return {
        "paths": [p.to_dict() for p in paths[:max_paths]],
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges],
        "primary_path": primary,
        "summary": _build_graph_summary(paths, md),
    }


def get_primary_story_path(story_graph: Dict[str, Any]) -> Dict[str, Any]:
    graph = _as_dict(story_graph)
    primary = _as_dict(graph.get("primary_path"))
    if primary:
        return primary
    paths = _as_list(graph.get("paths"))
    return _as_dict(paths[0]) if paths else {}


def story_graph_to_markdown(story_graph: Dict[str, Any], limit: int = 3) -> str:
    graph = _as_dict(story_graph)
    paths = [_as_dict(x) for x in _as_list(graph.get("paths"))]
    if not paths:
        return "- 생성된 Story Graph가 없습니다."

    lines: List[str] = []
    for p in paths[:limit]:
        lines.append(f"### {p.get('rank')}. {p.get('root_theme')} / {p.get('market_impact')}")
        if p.get("flow"):
            lines.append(f"- 흐름: {' → '.join(_as_list(p.get('flow'))[:8])}")
        if p.get("stocks"):
            lines.append(f"- 관련 종목: {', '.join(_as_list(p.get('stocks'))[:5])}")
        if p.get("causes"):
            lines.append(f"- 원인: {_as_list(p.get('causes'))[0]}")
        if p.get("effects"):
            lines.append(f"- 영향: {_as_list(p.get('effects'))[0]}")
        if p.get("checkpoints"):
            lines.append(f"- 확인: {', '.join(_as_list(p.get('checkpoints'))[:3])}")
        lines.append("")
    return "\n".join(lines).strip()


# ------------------------------------------------------------
# Path builders
# ------------------------------------------------------------

def _path_from_reasoning(
    *,
    rank: int,
    reasoning: Dict[str, Any],
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    market_decision: Dict[str, Any],
) -> StoryPath:
    theme = _clean(reasoning.get("theme")) or _top_theme_name(theme_graph) or "시장"
    sector = _clean(reasoning.get("sector")) or _sector_for_theme(theme, sector_results)
    stocks = _safe_text_list(reasoning.get("stocks")) or _stocks_for_theme(theme, theme_graph, candidate_scores)
    chain = _safe_text_list(reasoning.get("chain"))
    causes = _unique([reasoning.get("cause")] + _extract_theme_triggers(theme, theme_graph))
    effects = _unique([reasoning.get("effect")] + _extract_theme_story(theme, theme_graph))
    evidences = _safe_text_list(reasoning.get("evidence"))
    risks = _build_risks_for_path(theme, theme_graph, indicators, after_hours_data, candidate_scores)
    checkpoints = _build_checkpoints_for_path(theme, stocks, theme_graph, reasoning)
    confidence = _to_float(reasoning.get("confidence"), 0.5)
    base_score = _to_float(reasoning.get("score"), confidence * 100)

    flow = _build_flow_chain(
        theme=theme,
        sector=sector,
        chain=chain,
        stocks=stocks,
        theme_graph=theme_graph,
        indicators=indicators,
    )

    strength = _calc_story_strength(
        confidence=confidence,
        base_score=base_score,
        flow=flow,
        stocks=stocks,
        evidences=evidences,
        risks=risks,
        market_decision=market_decision,
    )

    money_flow = _extract_theme_field(theme, theme_graph, "money_flow")
    trading_idea = _extract_theme_field(theme, theme_graph, "trading_idea")

    return StoryPath(
        rank=rank,
        root_theme=theme,
        sector=sector,
        flow=flow,
        stocks=stocks[:6],
        causes=causes[:5],
        effects=effects[:5],
        evidences=evidences[:7],
        risks=risks[:6],
        checkpoints=checkpoints[:7],
        confidence=round(_clip(confidence, 0.0, 1.0), 2),
        story_strength=round(strength, 1),
        market_impact=_impact_label(strength),
        money_flow=money_flow,
        trading_idea=trading_idea,
    )


def _path_from_theme_node(
    *,
    rank: int,
    theme_node: Dict[str, Any],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    market_decision: Dict[str, Any],
) -> StoryPath:
    theme = _clean(theme_node.get("theme") or theme_node.get("name")) or "테마"
    sector = _first_text(theme_node.get("industries")) or _sector_for_theme(theme, sector_results)
    stocks = _companies_from_theme_node(theme_node) or _stocks_for_theme(theme, [theme_node], candidate_scores)
    flow = _safe_text_list(theme_node.get("supply_chain")) or [theme, sector]
    if stocks:
        flow = _unique(flow + [stocks[0]])

    causes = _safe_text_list(theme_node.get("triggers")) or [f"{theme} 관련 뉴스 흐름이 부각되었습니다."]
    effects = [_clean(theme_node.get("story"))] if _clean(theme_node.get("story")) else [f"{sector} 업종 투자심리에 영향을 줄 수 있습니다."]
    evidences = [f"Theme Graph 점수 {theme_node.get('score')}"] + _safe_text_list(theme_node.get("matched_keywords"))
    risks = _safe_text_list(theme_node.get("risks")) or _build_risks_for_path(theme, [theme_node], indicators, after_hours_data, candidate_scores)
    checkpoints = _safe_text_list(theme_node.get("watch_points")) or _build_checkpoints_for_path(theme, stocks, [theme_node], {})
    confidence = _clip(_to_float(theme_node.get("score"), 50.0) / 100.0, 0.25, 0.90)

    strength = _calc_story_strength(
        confidence=confidence,
        base_score=_to_float(theme_node.get("score"), 50.0),
        flow=flow,
        stocks=stocks,
        evidences=evidences,
        risks=risks,
        market_decision=market_decision,
    )

    return StoryPath(
        rank=rank,
        root_theme=theme,
        sector=sector,
        flow=flow[:8],
        stocks=stocks[:6],
        causes=causes[:5],
        effects=effects[:5],
        evidences=evidences[:7],
        risks=risks[:6],
        checkpoints=checkpoints[:7],
        confidence=round(confidence, 2),
        story_strength=round(strength, 1),
        market_impact=_impact_label(strength),
        money_flow=_clean(theme_node.get("money_flow")),
        trading_idea=_clean(theme_node.get("trading_idea")),
    )


# ------------------------------------------------------------
# Graph object construction
# ------------------------------------------------------------

def _build_graph_objects(paths: List[StoryPath]) -> tuple[List[StoryNode], List[StoryEdge]]:
    node_map: Dict[str, StoryNode] = {}
    edge_map: Dict[str, StoryEdge] = {}

    def add_node(label: str, typ: str, weight: float = 1.0, meta: Optional[Dict[str, Any]] = None):
        label = _clean(label)
        if not label:
            return
        node_id = _node_id(label, typ)
        if node_id not in node_map:
            node_map[node_id] = StoryNode(id=node_id, label=label, type=typ, weight=weight, meta=meta or {})
        else:
            node_map[node_id].weight = max(node_map[node_id].weight, weight)

    def add_edge(source: str, target: str, relation: str, weight: float = 1.0):
        source = _clean(source)
        target = _clean(target)
        if not source or not target or source == target:
            return
        key = f"{source}->{target}:{relation}"
        if key not in edge_map:
            edge_map[key] = StoryEdge(
                source=_node_id(source, "auto"),
                target=_node_id(target, "auto"),
                relation=relation,
                weight=weight,
            )

    for path in paths:
        add_node(path.root_theme, "theme", path.story_strength / 100, {"rank": path.rank})
        add_node(path.sector, "sector", path.story_strength / 100)
        add_edge(path.root_theme, path.sector, "theme_to_sector", 0.9)

        prev = ""
        for idx, step in enumerate(path.flow):
            typ = "cause" if idx < 2 else "flow"
            if step == path.root_theme:
                typ = "theme"
            if step == path.sector:
                typ = "sector"
            if step in path.stocks:
                typ = "stock"
            add_node(step, typ, max(0.3, path.story_strength / 100))
            if prev:
                add_edge(prev, step, "story_flow", 0.8)
            prev = step

        for stock in path.stocks:
            add_node(stock, "stock", path.story_strength / 100)
            add_edge(path.sector, stock, "sector_to_stock", 0.75)

        for risk in path.risks[:3]:
            add_node(risk, "risk", 0.4)
            add_edge(path.root_theme, risk, "theme_to_risk", 0.35)

    return list(node_map.values()), list(edge_map.values())


# ------------------------------------------------------------
# Flow helpers
# ------------------------------------------------------------

def _build_flow_chain(
    *,
    theme: str,
    sector: str,
    chain: List[str],
    stocks: List[str],
    theme_graph: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
) -> List[str]:
    flow: List[str] = []

    macro = _macro_lead_from_indicators(indicators, theme)
    if macro:
        flow.append(macro)

    if chain:
        flow.extend(chain)
    else:
        supply = _extract_theme_list(theme, theme_graph, "supply_chain")
        flow.extend(supply[:6])

    if theme and theme not in flow:
        flow.append(theme)
    if sector and sector not in flow:
        flow.append(sector)
    if stocks:
        flow.append(stocks[0])

    return _unique(flow)[:8]


def _macro_lead_from_indicators(indicators: List[Dict[str, Any]], theme: str) -> str:
    text = _join_text(indicators)
    theme_l = theme.lower()

    if any(k in text.lower() for k in ["나스닥", "엔비디아", "microsoft", "마이크로소프트", "gpu"]):
        if "ai" in theme_l or "반도체" in theme or "hbm" in theme_l:
            return "미국 기술주 흐름"
    if any(k in text.lower() for k in ["달러", "환율", "원/달러"]):
        return "환율 변수"
    if any(k in text.lower() for k in ["유가", "wti", "브렌트"]):
        return "국제유가 흐름"
    return ""


def _stocks_for_theme(theme: str, theme_graph: List[Dict[str, Any]], candidate_scores: List[Dict[str, Any]]) -> List[str]:
    stocks: List[str] = []

    for node in theme_graph:
        if _clean(node.get("theme")) != theme and theme not in _join_text([node]):
            continue
        stocks.extend(_companies_from_theme_node(node))

    candidate_text = theme.lower()
    for item in candidate_scores:
        name = _clean(item.get("name") or item.get("stock_name") or item.get("종목명") or item.get("stock"))
        if not name:
            continue
        if theme.lower() in _join_text([item]).lower() or not stocks:
            stocks.append(name)

    return _unique(stocks)[:6]


def _companies_from_theme_node(node: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for c in _as_list(node.get("companies")):
        c = _as_dict(c)
        name = _clean(c.get("name"))
        if name:
            out.append(name)
    return _unique(out)


def _sector_for_theme(theme: str, sector_results: List[Dict[str, Any]]) -> str:
    if sector_results:
        for item in sector_results:
            sector = _clean(item.get("sector") or item.get("name") or item.get("sector_name"))
            if sector and (sector in theme or theme in _join_text([item])):
                return sector
        top = _top_sector_name(sector_results)
        if top:
            return top
    if "반도체" in theme or "HBM" in theme or "AI" in theme:
        return "반도체·AI"
    if "원전" in theme or "SMR" in theme:
        return "원전"
    if "전력" in theme:
        return "전력기기"
    return theme


def _extract_theme_list(theme: str, theme_graph: List[Dict[str, Any]], key: str) -> List[str]:
    for node in theme_graph:
        if _clean(node.get("theme")) == theme:
            return _safe_text_list(node.get(key))
    return []


def _extract_theme_field(theme: str, theme_graph: List[Dict[str, Any]], key: str) -> str:
    for node in theme_graph:
        if _clean(node.get("theme")) == theme:
            return _clean(node.get(key))
    return ""


def _extract_theme_triggers(theme: str, theme_graph: List[Dict[str, Any]]) -> List[str]:
    return _extract_theme_list(theme, theme_graph, "triggers")


def _extract_theme_story(theme: str, theme_graph: List[Dict[str, Any]]) -> List[str]:
    story = _extract_theme_field(theme, theme_graph, "story")
    money = _extract_theme_field(theme, theme_graph, "money_flow")
    return _unique([story, money])


# ------------------------------------------------------------
# Risk / checkpoint / score
# ------------------------------------------------------------

def _build_risks_for_path(
    theme: str,
    theme_graph: List[Dict[str, Any]],
    indicators: List[Dict[str, Any]],
    after_hours_data: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
) -> List[str]:
    risks = _extract_theme_list(theme, theme_graph, "risks")

    for item in indicators:
        name = _clean(item.get("name"))
        pct = _to_float(item.get("change_rate"), None)
        if pct is None:
            continue
        if name in ("나스닥", "엔비디아", "S&P500") and pct <= -1:
            risks.append(f"{name} 약세에 따른 성장주 투자심리 둔화")
        if name == "테슬라" and pct <= -2:
            risks.append("테슬라 약세에 따른 2차전지 변동성 확대")
        if name in ("달러/원", "원/달러") and abs(pct) >= 0.5:
            risks.append("환율 변동성에 따른 외국인 수급 불확실성")

    for item in after_hours_data:
        name = _clean(item.get("name") or item.get("stock_name") or item.get("종목명"))
        pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("등락률"), None)
        if name and pct is not None and pct <= -3:
            risks.append(f"{name} 시간외 약세")

    if len(candidate_scores) >= 8:
        risks.append("관심 종목 과다에 따른 수급 분산")

    if not risks:
        risks.append("장 초반 거래대금과 지수 방향 확인 필요")

    return _unique(risks)[:7]


def _build_checkpoints_for_path(
    theme: str,
    stocks: List[str],
    theme_graph: List[Dict[str, Any]],
    reasoning: Dict[str, Any],
) -> List[str]:
    out = _extract_theme_list(theme, theme_graph, "watch_points")
    action = _clean(reasoning.get("action_hint"))
    if action:
        out.append(action)

    out.extend([
        "시초가 갭 확인",
        "거래량 유지 여부",
        "외국인·기관 수급 확인",
    ])

    if stocks:
        out.append(f"{stocks[0]} 대장주 역할 유지 여부 확인")

    return _unique(out)[:8]


def _calc_story_strength(
    *,
    confidence: float,
    base_score: float,
    flow: List[str],
    stocks: List[str],
    evidences: List[str],
    risks: List[str],
    market_decision: Dict[str, Any],
) -> float:
    score = 35.0
    score += _clip(confidence, 0, 1) * 30
    score += _clip(base_score, 0, 100) * 0.18
    score += min(len(flow), 7) * 2.0
    score += min(len(stocks), 4) * 2.0
    score += min(len(evidences), 5) * 1.2
    score -= max(0, len(risks) - 3) * 1.0

    md_score = _to_float(market_decision.get("score"), None)
    if md_score is not None:
        score += (md_score - 50) * 0.12

    return _clip(score, 0, 100)


def _impact_label(strength: float) -> str:
    if strength >= 80:
        return "HIGH"
    if strength >= 60:
        return "MEDIUM"
    return "LOW"


def _build_graph_summary(paths: List[StoryPath], market_decision: Dict[str, Any]) -> Dict[str, Any]:
    primary = paths[0] if paths else None
    return {
        "path_count": len(paths),
        "primary_theme": primary.root_theme if primary else "",
        "primary_sector": primary.sector if primary else "",
        "primary_strength": primary.story_strength if primary else 0,
        "market_impact": primary.market_impact if primary else "LOW",
        "strategy": _clean(market_decision.get("strategy")) or "",
    }


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def _node_id(label: str, typ: str) -> str:
    base = re.sub(r"\s+", "_", _clean(label))
    return f"{typ}:{base}" if typ != "auto" else base


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


def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def _safe_text_list(value: Any) -> List[str]:
    return _unique(_as_list(value))


def _first_text(value: Any) -> str:
    items = _safe_text_list(value)
    return items[0] if items else ""


def _unique(items: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items or []:
        text = _clean(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _to_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace("%", "").replace(",", "").strip()
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _join_text(items: Sequence[Any]) -> str:
    parts: List[str] = []
    for item in items or []:
        if isinstance(item, dict):
            for v in item.values():
                if isinstance(v, (str, int, float)):
                    parts.append(str(v))
                elif isinstance(v, list):
                    parts.extend(str(x) for x in v if isinstance(x, (str, int, float)))
        else:
            parts.append(str(item))
    return " ".join(parts)


def _top_sector_name(sector_results: List[Dict[str, Any]]) -> str:
    if not sector_results:
        return ""
    top = _as_dict(sector_results[0])
    return _clean(top.get("sector") or top.get("name") or top.get("sector_name") or top.get("업종"))


def _top_theme_name(theme_graph: List[Dict[str, Any]]) -> str:
    if not theme_graph:
        return ""
    top = _as_dict(theme_graph[0])
    return _clean(top.get("theme") or top.get("name") or top.get("label") or top.get("keyword"))


def _top_candidate_names(candidate_scores: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    names: List[str] = []
    for item in candidate_scores[:limit]:
        item = _as_dict(item)
        name = _clean(item.get("name") or item.get("stock_name") or item.get("종목명") or item.get("stock") or item.get("code"))
        if name:
            names.append(name)
    return _unique(names)[:limit]


# ------------------------------------------------------------
# Backward-compatible aliases
# ------------------------------------------------------------

def build_graph(*args, **kwargs) -> Dict[str, Any]:
    return build_story_graph(*args, **kwargs)


def build_market_story_graph(*args, **kwargs) -> Dict[str, Any]:
    return build_story_graph(*args, **kwargs)


if __name__ == "__main__":
    sample = build_story_graph(
        reasoning_layer=[
            {
                "theme": "반도체AI",
                "sector": "반도체",
                "stocks": ["삼성전자", "SK하이닉스"],
                "cause": "AI 데이터센터 투자 기대가 부각되었습니다.",
                "effect": "HBM 수요 기대가 강화되며 반도체 투자심리가 개선될 수 있습니다.",
                "chain": ["AI 투자 확대", "데이터센터 CAPEX", "HBM 수요", "반도체AI", "삼성전자"],
                "confidence": 0.82,
                "score": 82,
                "evidence": ["뉴스 단서: 엔비디아 강세에 HBM 수요 기대 부각"],
            }
        ],
        theme_graph=[
            {
                "theme": "HBM",
                "score": 90,
                "supply_chain": ["AI 서버", "GPU", "HBM", "후공정"],
                "companies": [{"name": "SK하이닉스"}, {"name": "삼성전자"}],
                "risks": ["엔비디아 약세", "단기 급등 부담"],
                "watch_points": ["외국인 수급", "후공정 장비주 확산 여부"],
                "money_flow": "대형 메모리주에서 후공정·소부장으로 수급이 확산될 가능성이 있습니다.",
                "trading_idea": "대형주가 먼저 강하고 후공정 종목이 따라붙는 순환 흐름을 확인합니다.",
            }
        ],
        candidate_scores=[{"name": "삼성전자"}, {"name": "SK하이닉스"}],
        market_decision={"score": 70, "strategy": "선별 관심"},
    )

    from pprint import pprint
    pprint(sample)
    print(story_graph_to_markdown(sample))
