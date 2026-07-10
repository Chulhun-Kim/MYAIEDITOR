# stock/money_flow_engine.py
# ------------------------------------------------------------
# v2.3 Money Flow Engine
# ------------------------------------------------------------
# 목적
# - 해외시장, 시간외 거래, 환율, 유가, 뉴스 흐름, Theme Graph를 하나의 자금 흐름 객체로 통합한다.
# - Reasoning Engine과 Story Engine이 같은 Money Flow 데이터를 읽도록 표준화한다.
# - 기존 시스템과 충돌하지 않도록 독립 모듈로 설계한다.
#
# 핵심 출력 형식
# {
#   "main_flow": [
#       {
#           "rank": 1,
#           "source": "마이크로소프트",
#           "source_type": "overseas_index",
#           "direction": "positive",
#           "change_pct": 1.62,
#           "impact": "AI 투자 확대 기대",
#           "theme": "반도체AI",
#           "sector": "반도체",
#           "stocks": ["삼성전자", "SK하이닉스"],
#           "chain": ["마이크로소프트", "AI 투자 확대 기대", "데이터센터 CAPEX", "HBM 수요", "반도체AI"],
#           "score": 82.0,
#           "confidence": 0.82,
#           "evidence": [...],
#           "action_hint": "장 초반 반도체 대장주의 거래대금과 외국인 수급을 확인합니다."
#       }
#   ],
#   "summary": "...",
#   "risk_flows": [...],
#   "theme_scores": {...},
#   "sector_scores": {...},
#   "dashboard": {...}
# }
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math
import re


# ------------------------------------------------------------
# 1. 기본 매핑 테이블
# ------------------------------------------------------------

THEME_PROFILE: Dict[str, Dict[str, Any]] = {
    "반도체AI": {
        "sector": "반도체",
        "stocks": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업", "ISC"],
        "keywords": [
            "ai", "인공지능", "반도체", "hbm", "메모리", "dram", "낸드", "gpu",
            "엔비디아", "nvidia", "마이크로소프트", "microsoft", "ms", "데이터센터",
            "data center", "클라우드", "capex", "고대역폭", "파운드리", "tsmc",
        ],
        "chain_core": ["AI 투자 확대 기대", "데이터센터 CAPEX", "HBM 수요", "반도체AI"],
        "positive_impact": "AI 투자 확대와 HBM 수요 기대",
        "negative_impact": "글로벌 기술주 약세와 반도체 투자심리 둔화",
    },
    "AI인프라": {
        "sector": "AI인프라",
        "stocks": ["LS ELECTRIC", "HD현대일렉트릭", "효성중공업", "일진전기"],
        "keywords": [
            "ai", "데이터센터", "전력", "전력망", "변압기", "전선", "냉각", "서버",
            "클라우드", "gpu", "mcp", "피지컬 ai", "physical ai",
        ],
        "chain_core": ["AI 서비스 확산", "데이터센터 증설", "전력 수요 증가", "AI인프라"],
        "positive_impact": "데이터센터와 전력 인프라 투자 기대",
        "negative_impact": "AI 인프라 투자 속도 둔화 우려",
    },
    "원전": {
        "sector": "원전",
        "stocks": ["두산에너빌리티", "한전기술", "우진", "비에이치아이"],
        "keywords": [
            "원전", "원자력", "smr", "소형모듈원전", "전력수급", "전력", "원자로",
            "한수원", "두산에너빌리티", "한전기술", "에너지", "기저전원",
        ],
        "chain_core": ["전력 수요 증가", "원전 정책 기대", "원전 밸류체인"],
        "positive_impact": "전력 수요 증가와 원전 정책 기대",
        "negative_impact": "정책 불확실성과 수주 지연 우려",
    },
    "자동차": {
        "sector": "자동차",
        "stocks": ["현대차", "기아", "현대모비스"],
        "keywords": ["자동차", "전기차", "ev", "하이브리드", "관세", "수출", "현대차", "기아", "테슬라"],
        "chain_core": ["수출 환경", "완성차 판매", "자동차"],
        "positive_impact": "수출 환율과 완성차 판매 기대",
        "negative_impact": "전기차 수요 둔화와 관세 부담",
    },
    "2차전지": {
        "sector": "2차전지",
        "stocks": ["LG에너지솔루션", "삼성SDI", "에코프로비엠", "포스코퓨처엠"],
        "keywords": ["2차전지", "이차전지", "배터리", "전기차", "ev", "양극재", "리튬", "테슬라"],
        "chain_core": ["전기차 수요", "배터리 밸류체인", "2차전지"],
        "positive_impact": "전기차와 배터리 수요 회복 기대",
        "negative_impact": "전기차 수요 둔화와 소재 가격 부담",
    },
    "조선": {
        "sector": "조선",
        "stocks": ["HD한국조선해양", "삼성중공업", "한화오션"],
        "keywords": ["조선", "선박", "lng", "lng선", "탱커", "수주", "해운", "선가", "조선업"],
        "chain_core": ["선가 흐름", "수주 기대", "조선"],
        "positive_impact": "고부가 선박 수주와 선가 상승 기대",
        "negative_impact": "유가·운임 변동과 수주 공백 우려",
    },
    "방산": {
        "sector": "방산",
        "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원"],
        "keywords": ["방산", "방위산업", "국방", "안보", "수출", "무기", "미사일", "전차", "자주포", "폴란드"],
        "chain_core": ["지정학 리스크", "방산 수요", "수출 기대", "방산"],
        "positive_impact": "지정학 리스크와 방산 수출 기대",
        "negative_impact": "수주 지연과 차익실현 부담",
    },
    "금융": {
        "sector": "금융",
        "stocks": ["KB금융", "신한지주", "하나금융지주"],
        "keywords": ["금융", "은행", "보험", "증권", "금리", "배당", "주주환원", "밸류업"],
        "chain_core": ["금리 흐름", "배당 기대", "금융"],
        "positive_impact": "배당과 주주환원 기대",
        "negative_impact": "금리 하락과 금융주 수익성 둔화 우려",
    },
}

SOURCE_RULES: List[Dict[str, Any]] = [
    {
        "source_keys": ["나스닥", "nasdaq", "ixic"],
        "label": "나스닥",
        "source_type": "overseas_index",
        "themes": ["반도체AI", "AI인프라"],
        "positive_impact": "미국 성장주·기술주 선호 회복",
        "negative_impact": "미국 성장주·기술주 투자심리 약화",
        "weight": 1.35,
    },
    {
        "source_keys": ["s&p500", "sp500", "s&p 500", "us500"],
        "label": "S&P500",
        "source_type": "overseas_index",
        "themes": ["반도체AI", "금융"],
        "positive_impact": "미국 전체 위험자산 선호 회복",
        "negative_impact": "미국 전체 위험자산 선호 약화",
        "weight": 1.0,
    },
    {
        "source_keys": ["다우", "dow", "dji"],
        "label": "다우존스",
        "source_type": "overseas_index",
        "themes": ["금융", "자동차", "조선"],
        "positive_impact": "미국 대형 가치주 선호 개선",
        "negative_impact": "미국 대형 가치주 투자심리 약화",
        "weight": 0.85,
    },
    {
        "source_keys": ["엔비디아", "nvidia", "nvda"],
        "label": "엔비디아",
        "source_type": "global_stock",
        "themes": ["반도체AI", "AI인프라"],
        "positive_impact": "GPU·AI 반도체 투자심리 개선",
        "negative_impact": "AI 반도체 투자심리 둔화",
        "weight": 1.8,
    },
    {
        "source_keys": ["마이크로소프트", "microsoft", "msft", "azure"],
        "label": "마이크로소프트",
        "source_type": "global_stock",
        "themes": ["반도체AI", "AI인프라"],
        "positive_impact": "AI 클라우드와 데이터센터 투자 기대",
        "negative_impact": "AI 클라우드 투자 기대 약화",
        "weight": 1.55,
    },
    {
        "source_keys": ["애플", "apple", "aapl"],
        "label": "애플",
        "source_type": "global_stock",
        "themes": ["반도체AI", "IT소부장"],
        "positive_impact": "글로벌 IT 소비재 투자심리 개선",
        "negative_impact": "글로벌 IT 소비재 투자심리 둔화",
        "weight": 1.0,
    },
    {
        "source_keys": ["테슬라", "tesla", "tsla"],
        "label": "테슬라",
        "source_type": "global_stock",
        "themes": ["2차전지", "자동차"],
        "positive_impact": "전기차·배터리 투자심리 개선",
        "negative_impact": "전기차·배터리 투자심리 둔화",
        "weight": 1.45,
    },
    {
        "source_keys": ["환율", "달러/원", "원/달러", "usd/krw", "usdkrw"],
        "label": "달러/원 환율",
        "source_type": "fx",
        "themes": ["자동차", "조선", "반도체AI"],
        "positive_impact": "수출주 환율 민감도 확대",
        "negative_impact": "외국인 수급 부담과 위험자산 선호 약화",
        "weight": 0.9,
        "inverse_for_risk": True,
    },
    {
        "source_keys": ["wti", "유가", "원유", "cl", "brent", "브렌트"],
        "label": "WTI 유가",
        "source_type": "commodity",
        "themes": ["조선", "정유", "화학"],
        "positive_impact": "에너지·해양플랜트 관련 기대",
        "negative_impact": "비용 부담과 인플레이션 경계",
        "weight": 0.8,
    },
]


# ------------------------------------------------------------
# 2. 데이터 구조
# ------------------------------------------------------------

@dataclass
class MoneyFlowItem:
    rank: int
    source: str
    source_type: str
    direction: str
    change_pct: Optional[float]
    impact: str
    theme: str
    sector: str
    stocks: List[str]
    chain: List[str]
    score: float
    confidence: float
    evidence: List[str]
    action_hint: str
    raw_factors: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# 3. Public API
# ------------------------------------------------------------

def build_money_flow_layer(
    news_items: Optional[List[Dict[str, Any]]] = None,
    indicators: Optional[List[Dict[str, Any]]] = None,
    after_hours_data: Optional[List[Dict[str, Any]]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
    candidate_scores: Optional[List[Dict[str, Any]]] = None,
    theme_graph: Optional[List[Dict[str, Any]]] = None,
    limit: int = 6,
) -> Dict[str, Any]:
    """
    장전 입력 데이터를 Money Flow 표준 객체로 변환한다.

    Parameters
    ----------
    news_items:
        수집 뉴스 목록. title/headline/summary/content 필드를 우선 사용한다.
    indicators:
        해외지수·환율·유가·글로벌 종목 지표. name/symbol/change_rate/memo 필드를 우선 사용한다.
    after_hours_data:
        시간외 주요 종목 데이터. name/after_change_pct/reason 필드를 우선 사용한다.
    sector_results:
        섹터 분석 결과. sector/name/score 필드를 우선 사용한다.
    candidate_scores:
        관심 종목 결과. name/stock_name/score/reason 필드를 우선 사용한다.
    theme_graph:
        Theme Graph 결과. theme/name/score 필드를 우선 사용한다.
    limit:
        main_flow 최대 개수.
    """

    safe_news = _as_list(news_items)
    safe_indicators = _as_list(indicators)
    safe_after_hours = _as_list(after_hours_data)
    safe_sectors = _as_list(sector_results)
    safe_candidates = _as_list(candidate_scores)
    safe_theme_graph = _as_list(theme_graph)

    flows: List[MoneyFlowItem] = []

    flows.extend(
        _build_indicator_flows(
            indicators=safe_indicators,
            news_items=safe_news,
            theme_graph=safe_theme_graph,
            sector_results=safe_sectors,
            candidate_scores=safe_candidates,
        )
    )

    flows.extend(
        _build_news_flows(
            news_items=safe_news,
            theme_graph=safe_theme_graph,
            sector_results=safe_sectors,
            candidate_scores=safe_candidates,
        )
    )

    flows.extend(
        _build_after_hours_flows(
            after_hours_data=safe_after_hours,
            theme_graph=safe_theme_graph,
            sector_results=safe_sectors,
            candidate_scores=safe_candidates,
        )
    )

    flows = _merge_similar_flows(flows)
    flows.sort(key=lambda x: x.score, reverse=True)

    for idx, item in enumerate(flows, start=1):
        item.rank = idx

    main_flow = [item.to_dict() for item in flows[:limit]]
    risk_flows = [item.to_dict() for item in flows if item.direction == "negative"][:limit]

    theme_scores = _build_theme_scores(main_flow, safe_theme_graph)
    sector_scores = _build_sector_scores(main_flow, safe_sectors)
    summary = build_money_flow_brief(main_flow=main_flow, risk_flows=risk_flows)

    return {
        "main_flow": main_flow,
        "risk_flows": risk_flows,
        "theme_scores": theme_scores,
        "sector_scores": sector_scores,
        "summary": summary,
        "top_flow": main_flow[0] if main_flow else {},
        "dashboard": _build_dashboard_payload(main_flow, risk_flows, theme_scores, sector_scores),
        "meta": {
            "news_count": len(safe_news),
            "indicator_count": len(safe_indicators),
            "after_hours_count": len(safe_after_hours),
            "flow_count": len(main_flow),
        },
    }


def build_money_flow_brief(
    money_flow: Optional[Dict[str, Any]] = None,
    main_flow: Optional[List[Dict[str, Any]]] = None,
    risk_flows: Optional[List[Dict[str, Any]]] = None,
    max_sentences: int = 4,
) -> str:
    """Money Flow를 Story Engine에서 바로 쓸 수 있는 자연어 브리핑으로 변환한다."""

    if money_flow is not None:
        main_flow = _as_list(money_flow.get("main_flow"))
        risk_flows = _as_list(money_flow.get("risk_flows"))

    main = _as_list(main_flow)
    risks = _as_list(risk_flows)

    if not main:
        return "뚜렷한 자금 흐름은 아직 확인되지 않았습니다. 장 초반 거래대금과 외국인 수급 확인이 필요합니다."

    top = _as_dict(main[0])
    source = _clean_text(top.get("source")) or "핵심 지표"
    theme = _clean_text(top.get("theme")) or "주도 테마"
    sector = _clean_text(top.get("sector")) or "관련 섹터"
    impact = _clean_text(top.get("impact")) or "투자심리 변화"
    confidence = _to_float(top.get("confidence"))

    sentences = [
        f"자금 흐름은 {source}에서 출발해 {impact}를 거쳐 {theme}·{sector}로 연결되는 모습입니다."
    ]

    if confidence is not None:
        sentences.append(f"이 흐름의 신뢰도는 {confidence:.2f} 수준으로, 장 초반 거래량이 붙을 경우 주도 테마로 확장될 수 있습니다.")

    if len(main) >= 2:
        second = _as_dict(main[1])
        second_theme = _clean_text(second.get("theme"))
        second_source = _clean_text(second.get("source"))
        if second_theme and second_source:
            sentences.append(f"보조 흐름으로는 {second_source}에서 {second_theme} 쪽으로 이어지는 자금 이동 가능성이 확인됩니다.")

    if risks:
        risk = _as_dict(risks[0])
        risk_source = _clean_text(risk.get("source")) or "일부 지표"
        risk_theme = _clean_text(risk.get("theme")) or "관련 테마"
        sentences.append(f"다만 {risk_source} 약세는 {risk_theme}의 장중 변동성을 키울 수 있어 추격 매수는 제한적으로 접근해야 합니다.")

    return " ".join(sentences[:max_sentences])


# Backward-compatible aliases

def build_money_flow(*args, **kwargs) -> Dict[str, Any]:
    return build_money_flow_layer(*args, **kwargs)


def analyze_money_flow(*args, **kwargs) -> Dict[str, Any]:
    return build_money_flow_layer(*args, **kwargs)


# ------------------------------------------------------------
# 4. Flow builders
# ------------------------------------------------------------

def _build_indicator_flows(
    indicators: List[Dict[str, Any]],
    news_items: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
) -> List[MoneyFlowItem]:
    flows: List[MoneyFlowItem] = []

    for row in indicators:
        item = _as_dict(row)
        raw_name = _clean_text(item.get("name") or item.get("symbol") or item.get("ticker"))
        symbol = _clean_text(item.get("symbol") or item.get("ticker"))
        memo = _clean_text(item.get("memo") or item.get("description") or item.get("reason"))
        text_blob = " ".join([raw_name, symbol, memo])
        change_pct = _to_float(
            item.get("change_rate")
            or item.get("change_pct")
            or item.get("rate")
            or item.get("등락률")
        )

        rule = _match_source_rule(text_blob)
        if not rule:
            continue

        direction = _direction_from_change(change_pct)
        if direction == "flat" and not memo:
            continue

        impact = rule.get("positive_impact") if direction != "negative" else rule.get("negative_impact")
        for theme in rule.get("themes", []):
            profile = _theme_profile(theme)
            sector = profile.get("sector", theme)
            stocks = _select_stocks(theme, sector, candidate_scores, profile.get("stocks", []))
            score = _score_indicator_flow(change_pct, rule, theme, theme_graph, sector_results, candidate_scores)
            evidence = _compact_texts([
                _format_change_evidence(rule.get("label") or raw_name, change_pct),
                memo,
                _theme_evidence(theme, theme_graph),
                _sector_evidence(sector, sector_results),
            ])
            chain = _compact_texts([rule.get("label") or raw_name, impact] + profile.get("chain_core", [theme]) + stocks[:1])

            flows.append(MoneyFlowItem(
                rank=0,
                source=rule.get("label") or raw_name,
                source_type=rule.get("source_type", "indicator"),
                direction=direction,
                change_pct=change_pct,
                impact=impact or profile.get("positive_impact", "투자심리 변화"),
                theme=theme,
                sector=sector,
                stocks=stocks,
                chain=chain,
                score=score,
                confidence=_confidence_from_score(score),
                evidence=evidence,
                action_hint=_action_hint(theme, sector, direction),
                raw_factors={"source": item, "rule": rule.get("label")},
            ))

    return flows


def _build_news_flows(
    news_items: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
) -> List[MoneyFlowItem]:
    flows: List[MoneyFlowItem] = []
    if not news_items:
        return flows

    theme_hits: Dict[str, Dict[str, Any]] = {}
    for news in news_items[:50]:
        item = _as_dict(news)
        title = _clean_text(item.get("title") or item.get("headline"))
        summary = _clean_text(item.get("summary") or item.get("content") or item.get("description"))
        text = _normalize(" ".join([title, summary]))
        if not text:
            continue

        for theme, profile in THEME_PROFILE.items():
            hit_count = _keyword_count(text, profile.get("keywords", []))
            if hit_count <= 0:
                continue
            bucket = theme_hits.setdefault(theme, {"count": 0, "titles": [], "hit_score": 0})
            bucket["count"] += 1
            bucket["hit_score"] += hit_count
            if title and len(bucket["titles"]) < 4:
                bucket["titles"].append(title)

    for theme, data in theme_hits.items():
        profile = _theme_profile(theme)
        sector = profile.get("sector", theme)
        stocks = _select_stocks(theme, sector, candidate_scores, profile.get("stocks", []))
        count = int(data.get("count", 0))
        hit_score = float(data.get("hit_score", 0))
        base_score = 42 + min(24, count * 4) + min(10, hit_score * 1.2)
        base_score += _theme_bonus(theme, theme_graph)
        base_score += _sector_bonus(sector, sector_results)
        base_score += _candidate_bonus(stocks, candidate_scores)
        score = _clamp(base_score, 0, 100)
        direction = "positive"
        impact = profile.get("positive_impact", "뉴스 모멘텀")
        titles = data.get("titles", [])
        evidence = _compact_texts([
            f"관련 뉴스 {count}건 감지",
            *[_shorten(t, 56) for t in titles[:3]],
            _theme_evidence(theme, theme_graph),
            _sector_evidence(sector, sector_results),
        ])
        chain = _compact_texts(["뉴스 흐름", impact] + profile.get("chain_core", [theme]) + stocks[:1])

        flows.append(MoneyFlowItem(
            rank=0,
            source="뉴스 흐름",
            source_type="news",
            direction=direction,
            change_pct=None,
            impact=impact,
            theme=theme,
            sector=sector,
            stocks=stocks,
            chain=chain,
            score=score,
            confidence=_confidence_from_score(score),
            evidence=evidence,
            action_hint=_action_hint(theme, sector, direction),
            raw_factors={"news_count": count, "hit_score": hit_score, "titles": titles[:4]},
        ))

    return flows


def _build_after_hours_flows(
    after_hours_data: List[Dict[str, Any]],
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
) -> List[MoneyFlowItem]:
    flows: List[MoneyFlowItem] = []

    for row in after_hours_data[:30]:
        item = _as_dict(row)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        reason = _clean_text(item.get("reason") or item.get("signal") or item.get("memo"))
        change_pct = _to_float(item.get("after_change_pct") or item.get("change_pct") or item.get("rate") or item.get("등락률"))
        if not name and not reason:
            continue

        theme = _infer_theme_from_text(" ".join([name, reason]))
        if not theme:
            theme = _infer_theme_from_candidate(name, candidate_scores) or _top_theme_name(theme_graph)
        if not theme:
            continue

        profile = _theme_profile(theme)
        sector = profile.get("sector", theme)
        direction = _direction_from_change(change_pct)
        if direction == "flat":
            direction = "positive" if "강세" in reason or "상승" in reason else "neutral"
        impact = profile.get("positive_impact") if direction != "negative" else profile.get("negative_impact")
        score = 38 + _abs_change_score(change_pct, multiplier=5.0)
        score += _theme_bonus(theme, theme_graph)
        score += _sector_bonus(sector, sector_results)
        score += _candidate_bonus([name], candidate_scores)
        if direction == "negative":
            score -= 5
        score = _clamp(score, 0, 100)
        stocks = _select_stocks(theme, sector, candidate_scores, [name] + profile.get("stocks", []))
        evidence = _compact_texts([
            _format_change_evidence(f"{name} 시간외", change_pct),
            reason,
            _theme_evidence(theme, theme_graph),
        ])
        chain = _compact_texts([f"{name} 시간외", impact] + profile.get("chain_core", [theme]) + stocks[:1])

        flows.append(MoneyFlowItem(
            rank=0,
            source=name or "시간외 종목",
            source_type="after_hours",
            direction=direction,
            change_pct=change_pct,
            impact=impact or "시간외 수급 변화",
            theme=theme,
            sector=sector,
            stocks=stocks,
            chain=chain,
            score=score,
            confidence=_confidence_from_score(score),
            evidence=evidence,
            action_hint=_action_hint(theme, sector, direction),
            raw_factors={"source": item},
        ))

    return flows


# ------------------------------------------------------------
# 5. Aggregation
# ------------------------------------------------------------

def _merge_similar_flows(flows: List[MoneyFlowItem]) -> List[MoneyFlowItem]:
    buckets: Dict[Tuple[str, str, str], MoneyFlowItem] = {}

    for flow in flows:
        key = (flow.theme, flow.sector, flow.direction)
        if key not in buckets:
            buckets[key] = flow
            continue

        current = buckets[key]
        # 더 높은 점수의 흐름을 대표로 삼되, 증거와 체인은 합친다.
        if flow.score > current.score:
            flow.evidence = _compact_texts(flow.evidence + current.evidence)[:8]
            flow.chain = _compact_texts(flow.chain + current.chain)[:8]
            flow.stocks = _compact_texts(flow.stocks + current.stocks)[:6]
            flow.score = _clamp(max(flow.score, current.score) + min(8, current.score * 0.08), 0, 100)
            flow.confidence = _confidence_from_score(flow.score)
            buckets[key] = flow
        else:
            current.evidence = _compact_texts(current.evidence + flow.evidence)[:8]
            current.chain = _compact_texts(current.chain + flow.chain)[:8]
            current.stocks = _compact_texts(current.stocks + flow.stocks)[:6]
            current.score = _clamp(max(current.score, flow.score) + min(8, flow.score * 0.08), 0, 100)
            current.confidence = _confidence_from_score(current.score)

    return list(buckets.values())


def _build_theme_scores(main_flow: List[Dict[str, Any]], theme_graph: List[Dict[str, Any]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for flow in main_flow:
        item = _as_dict(flow)
        theme = _clean_text(item.get("theme"))
        score = _to_float(item.get("score")) or 0
        if theme:
            scores[theme] = max(scores.get(theme, 0.0), score)

    for node in theme_graph:
        item = _as_dict(node)
        theme = _clean_text(item.get("theme") or item.get("name") or item.get("label") or item.get("keyword"))
        score = _to_float(item.get("score") or item.get("strength") or item.get("weight"))
        if theme and score is not None:
            scores[theme] = max(scores.get(theme, 0.0), min(100.0, score))

    return dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True))


def _build_sector_scores(main_flow: List[Dict[str, Any]], sector_results: List[Dict[str, Any]]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for flow in main_flow:
        item = _as_dict(flow)
        sector = _clean_text(item.get("sector"))
        score = _to_float(item.get("score")) or 0
        if sector:
            scores[sector] = max(scores.get(sector, 0.0), score)

    for row in sector_results:
        item = _as_dict(row)
        sector = _clean_text(item.get("sector") or item.get("name") or item.get("sector_name") or item.get("업종"))
        score = _to_float(item.get("score") or item.get("total_score") or item.get("strength"))
        if sector and score is not None:
            scores[sector] = max(scores.get(sector, 0.0), min(100.0, score))

    return dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True))


def _build_dashboard_payload(
    main_flow: List[Dict[str, Any]],
    risk_flows: List[Dict[str, Any]],
    theme_scores: Dict[str, float],
    sector_scores: Dict[str, float],
) -> Dict[str, Any]:
    top_flow = _as_dict(main_flow[0]) if main_flow else {}
    return {
        "top_source": _clean_text(top_flow.get("source")) or "-",
        "top_theme": _clean_text(top_flow.get("theme")) or "-",
        "top_sector": _clean_text(top_flow.get("sector")) or "-",
        "top_chain": _as_list(top_flow.get("chain"))[:6],
        "confidence": _to_float(top_flow.get("confidence")) or 0.0,
        "risk_count": len(risk_flows),
        "theme_scores": theme_scores,
        "sector_scores": sector_scores,
    }


# ------------------------------------------------------------
# 6. Matching / scoring helpers
# ------------------------------------------------------------

def _match_source_rule(text: str) -> Optional[Dict[str, Any]]:
    norm = _normalize(text)
    for rule in SOURCE_RULES:
        for key in rule.get("source_keys", []):
            if _normalize(key) in norm:
                return rule
    return None


def _infer_theme_from_text(text: str) -> str:
    norm = _normalize(text)
    best_theme = ""
    best_count = 0
    for theme, profile in THEME_PROFILE.items():
        count = _keyword_count(norm, profile.get("keywords", []))
        if count > best_count:
            best_theme = theme
            best_count = count
    return best_theme if best_count > 0 else ""


def _infer_theme_from_candidate(name: str, candidate_scores: List[Dict[str, Any]]) -> str:
    if not name:
        return ""
    norm_name = _normalize(name)
    for row in candidate_scores:
        item = _as_dict(row)
        cname = _normalize(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if cname and (cname == norm_name or norm_name in cname or cname in norm_name):
            text = " ".join([
                _clean_text(item.get("theme")),
                _clean_text(item.get("sector")),
                _clean_text(item.get("reason")),
                _clean_text(item.get("ai_reason")),
            ])
            return _infer_theme_from_text(text) or _clean_text(item.get("theme"))
    return ""


def _score_indicator_flow(
    change_pct: Optional[float],
    rule: Dict[str, Any],
    theme: str,
    theme_graph: List[Dict[str, Any]],
    sector_results: List[Dict[str, Any]],
    candidate_scores: List[Dict[str, Any]],
) -> float:
    base = 38.0
    weight = _to_float(rule.get("weight")) or 1.0
    base += _abs_change_score(change_pct, multiplier=9.0 * weight)
    base += _theme_bonus(theme, theme_graph)
    sector = _theme_profile(theme).get("sector", theme)
    base += _sector_bonus(sector, sector_results)
    base += _candidate_bonus(_theme_profile(theme).get("stocks", []), candidate_scores)
    return _clamp(base, 0, 100)


def _abs_change_score(change_pct: Optional[float], multiplier: float = 8.0) -> float:
    if change_pct is None:
        return 4.0
    return min(28.0, abs(change_pct) * multiplier)


def _theme_bonus(theme: str, theme_graph: List[Dict[str, Any]]) -> float:
    for node in theme_graph:
        item = _as_dict(node)
        name = _clean_text(item.get("theme") or item.get("name") or item.get("label") or item.get("keyword"))
        if name and (name == theme or theme in name or name in theme):
            score = _to_float(item.get("score") or item.get("strength") or item.get("weight"))
            if score is None:
                return 8.0
            return min(14.0, max(4.0, score / 8.0))
    return 0.0


def _sector_bonus(sector: str, sector_results: List[Dict[str, Any]]) -> float:
    norm_sector = _normalize(sector)
    for row in sector_results:
        item = _as_dict(row)
        name = _normalize(item.get("sector") or item.get("name") or item.get("sector_name") or item.get("업종"))
        if name and (name == norm_sector or norm_sector in name or name in norm_sector):
            score = _to_float(item.get("score") or item.get("total_score") or item.get("strength"))
            if score is None:
                return 6.0
            return min(10.0, max(3.0, score / 10.0))
    return 0.0


def _candidate_bonus(stocks: List[str], candidate_scores: List[Dict[str, Any]]) -> float:
    if not stocks or not candidate_scores:
        return 0.0
    stock_norms = [_normalize(x) for x in stocks if x]
    bonus = 0.0
    for row in candidate_scores[:12]:
        item = _as_dict(row)
        name = _normalize(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if not name:
            continue
        if any(s and (s == name or s in name or name in s) for s in stock_norms):
            score = _to_float(item.get("score") or item.get("final_score") or item.get("total_score"))
            bonus += 2.0 if score is None else min(5.0, max(2.0, score / 20.0))
    return min(10.0, bonus)


def _confidence_from_score(score: float) -> float:
    # 0.45~0.95 사이로 압축해 과신을 방지한다.
    return round(_clamp(0.45 + (score / 100.0) * 0.50, 0.0, 0.95), 2)


def _direction_from_change(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return "neutral"
    if change_pct >= 0.3:
        return "positive"
    if change_pct <= -0.3:
        return "negative"
    return "flat"


# ------------------------------------------------------------
# 7. Extractors / utilities
# ------------------------------------------------------------

def _theme_profile(theme: str) -> Dict[str, Any]:
    if theme in THEME_PROFILE:
        return THEME_PROFILE[theme]
    return {
        "sector": theme,
        "stocks": [],
        "keywords": [theme],
        "chain_core": [theme],
        "positive_impact": f"{theme} 관련 기대",
        "negative_impact": f"{theme} 관련 투자심리 둔화",
    }


def _top_theme_name(theme_graph: List[Dict[str, Any]]) -> str:
    if not theme_graph:
        return ""
    top = _as_dict(theme_graph[0])
    return _clean_text(top.get("theme") or top.get("name") or top.get("label") or top.get("keyword"))


def _select_stocks(
    theme: str,
    sector: str,
    candidate_scores: List[Dict[str, Any]],
    defaults: List[str],
    limit: int = 5,
) -> List[str]:
    result: List[str] = []
    norm_theme = _normalize(theme)
    norm_sector = _normalize(sector)

    for row in candidate_scores:
        item = _as_dict(row)
        name = _clean_text(item.get("name") or item.get("stock_name") or item.get("종목명"))
        if not name:
            continue
        text = _normalize(" ".join([
            name,
            _clean_text(item.get("sector")),
            _clean_text(item.get("theme")),
            _clean_text(item.get("reason")),
            _clean_text(item.get("ai_reason")),
        ]))
        if norm_theme in text or norm_sector in text or _keyword_count(text, _theme_profile(theme).get("keywords", [])) > 0:
            result.append(name)

    result.extend(defaults)
    return _compact_texts(result)[:limit]


def _theme_evidence(theme: str, theme_graph: List[Dict[str, Any]]) -> str:
    for node in theme_graph:
        item = _as_dict(node)
        name = _clean_text(item.get("theme") or item.get("name") or item.get("label") or item.get("keyword"))
        if name and (name == theme or theme in name or name in theme):
            score = _to_float(item.get("score") or item.get("strength") or item.get("weight"))
            if score is not None:
                return f"Theme Graph에서 {name} 점수 {score:.1f} 확인"
            return f"Theme Graph에서 {name} 부각"
    return ""


def _sector_evidence(sector: str, sector_results: List[Dict[str, Any]]) -> str:
    norm_sector = _normalize(sector)
    for row in sector_results:
        item = _as_dict(row)
        name = _clean_text(item.get("sector") or item.get("name") or item.get("sector_name") or item.get("업종"))
        if name and (norm_sector == _normalize(name) or norm_sector in _normalize(name) or _normalize(name) in norm_sector):
            score = _to_float(item.get("score") or item.get("total_score") or item.get("strength"))
            if score is not None:
                return f"섹터 분석에서 {name} 점수 {score:.1f} 확인"
            return f"섹터 분석에서 {name} 강세 확인"
    return ""


def _format_change_evidence(label: str, change_pct: Optional[float]) -> str:
    label = _clean_text(label) or "지표"
    if change_pct is None:
        return f"{label} 흐름 확인"
    return f"{label} {change_pct:+.2f}%"


def _action_hint(theme: str, sector: str, direction: str) -> str:
    if direction == "negative":
        return f"{sector or theme} 관련 종목은 반등 확인 전 추격 매수보다 변동성 관리를 우선합니다."
    if theme == "반도체AI":
        return "장 초반 반도체 대장주의 거래대금과 외국인 수급을 확인합니다."
    if theme == "AI인프라":
        return "전력기기·데이터센터 관련주의 시초가 갭과 거래량 지속 여부를 확인합니다."
    if theme == "원전":
        return "정책 뉴스의 지속성과 원전 대장주의 체결 강도를 확인합니다."
    return f"{sector or theme} 대장주의 시초가와 거래량 지속 여부를 확인합니다."


def _keyword_count(text: str, keywords: Iterable[str]) -> int:
    norm = _normalize(text)
    count = 0
    for keyword in keywords:
        key = _normalize(keyword)
        if key and key in norm:
            count += 1
    return count


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


def _normalize(value: Any) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return None
        return float(value)
    try:
        text = str(value).strip().replace("%", "").replace(",", "")
        if not text:
            return None
        return float(text)
    except Exception:
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _shorten(text: str, limit: int = 50) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _compact_texts(items: Sequence[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        text = _clean_text(item)
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


# ------------------------------------------------------------
# 8. Manual smoke test
# ------------------------------------------------------------

if __name__ == "__main__":
    sample = build_money_flow_layer(
        indicators=[
            {"name": "마이크로소프트", "symbol": "MSFT", "change_rate": 1.62, "memo": "AI 클라우드"},
            {"name": "엔비디아", "symbol": "NVDA", "change_rate": -1.39, "memo": "반도체·AI·HBM"},
            {"name": "달러/원", "symbol": "USD/KRW", "change_rate": -0.62, "memo": "외국인 수급"},
        ],
        news_items=[
            {"title": "반도체 산업, AI 경쟁에서 인프라 경쟁으로", "summary": "데이터센터와 HBM 수요 기대"},
            {"title": "원전 확대 검토", "summary": "전력수요와 SMR 투자 필요"},
        ],
        after_hours_data=[
            {"name": "삼성전자", "after_change_pct": 3.05, "reason": "반도체AI 관련 뉴스"},
        ],
        candidate_scores=[
            {"name": "삼성전자", "score": 96, "sector": "반도체AI"},
            {"name": "SK하이닉스", "score": 76, "sector": "반도체AI"},
        ],
        theme_graph=[{"theme": "반도체AI", "score": 80}, {"theme": "원전", "score": 62}],
        sector_results=[{"sector": "반도체", "score": 85}],
    )
    from pprint import pprint
    pprint(sample)
