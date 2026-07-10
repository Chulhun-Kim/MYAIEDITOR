# stock/reasoning_engine.py
# ------------------------------------------------------------
# v2.2 Reasoning Layer
# ------------------------------------------------------------
# 목적
# - 뉴스 → 테마 → 섹터 → 종목으로 이어지는 인과관계를 표준 객체로 생성한다.
# - Story Engine, Dashboard, AI 투자전략, 관심종목 추천근거가 같은 추론 데이터를 쓰도록 한다.
# - 기존 v2.1 구조와 충돌하지 않도록 독립 모듈로 설계한다.
#
# 핵심 출력 형식
# [
#   {
#       "rank": 1,
#       "theme": "반도체AI",
#       "sector": "반도체",
#       "stocks": ["삼성전자", "SK하이닉스"],
#       "cause": "AI 데이터센터 투자 기대가 부각되었습니다.",
#       "effect": "HBM·메모리 수요 기대가 강화되며 반도체 투자심리가 개선될 수 있습니다.",
#       "chain": ["AI 뉴스", "데이터센터 투자", "HBM 수요", "반도체AI", "삼성전자"],
#       "confidence": 0.82,
#       "score": 82.0,
#       "evidence": [...],
#       "action_hint": "장 초반 거래대금과 외국인 수급 지속 여부를 확인할 필요가 있습니다."
#   }
# ]
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import math
import re


# ------------------------------------------------------------
# 1. 기본 매핑 테이블
# ------------------------------------------------------------

THEME_SECTOR_MAP: Dict[str, Dict[str, Any]] = {
    "반도체AI": {
        "sector": "반도체",
        "keywords": [
            "ai", "인공지능", "반도체", "hbm", "메모리", "dram", "낸드", "gpu",
            "엔비디아", "nvidia", "마이크로소프트", "microsoft", "ms", "데이터센터",
            "data center", "클라우드", "capex", "고대역폭", "파운드리",
        ],
        "stocks": ["삼성전자", "SK하이닉스"],
        "cause": "AI·데이터센터 투자 기대가 부각되었습니다.",
        "effect": "HBM·메모리 수요 기대가 강화되며 반도체 업종의 투자심리가 개선될 수 있습니다.",
        "chain_core": ["AI 투자 확대", "데이터센터 CAPEX", "HBM 수요", "반도체AI"],
    },
    "AI인프라": {
        "sector": "AI인프라",
        "keywords": [
            "ai", "인공지능", "데이터센터", "전력", "전력망", "변압기", "전선", "냉각",
            "클라우드", "서버", "gpu", "mcp", "피지컬 ai", "physical ai",
        ],
        "stocks": ["LS ELECTRIC", "HD현대일렉트릭", "효성중공업"],
        "cause": "AI 서비스 확대와 데이터센터 증설 기대가 이어졌습니다.",
        "effect": "전력기기·전력망·서버 인프라 관련주의 수혜 기대가 커질 수 있습니다.",
        "chain_core": ["AI 확산", "데이터센터 증설", "전력 수요 증가", "AI인프라"],
    },
    "원전": {
        "sector": "원전",
        "keywords": [
            "원전", "원자력", "smr", "소형모듈원전", "전력수급", "전력", "에너지",
            "원자로", "체코 원전", "한수원", "두산에너빌리티",
        ],
        "stocks": ["두산에너빌리티", "한전기술", "우진"],
        "cause": "전력 수요 증가와 원전 확대 검토 기대가 맞물렸습니다.",
        "effect": "원전 기자재·설계·정비 관련 종목의 모멘텀이 강화될 수 있습니다.",
        "chain_core": ["전력 수요 증가", "원전 정책 기대", "원전 밸류체인"],
    },
    "방산": {
        "sector": "방산",
        "keywords": [
            "방산", "방위산업", "수출", "무기", "미사일", "전차", "자주포", "k2", "k9",
            "폴란드", "중동", "국방", "안보", "한화에어로스페이스", "현대로템",
        ],
        "stocks": ["한화에어로스페이스", "현대로템", "LIG넥스원"],
        "cause": "지정학적 긴장과 방산 수출 기대가 부각되었습니다.",
        "effect": "방산 수주와 실적 개선 기대가 관련 종목의 강세 재료가 될 수 있습니다.",
        "chain_core": ["지정학 리스크", "방산 수요", "수출 기대", "방산"],
    },
    "조선": {
        "sector": "조선",
        "keywords": [
            "조선", "선박", "lng", "lng선", "탱커", "수주", "해운", "선가", "조선업",
            "hd한국조선해양", "삼성중공업", "한화오션",
        ],
        "stocks": ["HD한국조선해양", "삼성중공업", "한화오션"],
        "cause": "선박 수주와 고부가 선종 기대가 이어졌습니다.",
        "effect": "조선 업종의 실적 가시성과 수주 모멘텀이 부각될 수 있습니다.",
        "chain_core": ["선가 상승", "수주 기대", "실적 개선", "조선"],
    },
    "바이오": {
        "sector": "바이오",
        "keywords": [
            "바이오", "제약", "신약", "임상", "fda", "항암", "비만", "치료제", "셀트리온",
            "삼성바이오로직스", "알테오젠",
        ],
        "stocks": ["삼성바이오로직스", "셀트리온", "알테오젠"],
        "cause": "신약·임상·기술수출 관련 기대가 부각되었습니다.",
        "effect": "바이오 업종의 이벤트성 수급이 강화될 수 있습니다.",
        "chain_core": ["임상 이벤트", "기술수출 기대", "바이오"],
    },
    "2차전지": {
        "sector": "2차전지",
        "keywords": [
            "2차전지", "이차전지", "배터리", "전기차", "ev", "양극재", "음극재", "리튬",
            "테슬라", "lg에너지솔루션", "에코프로", "포스코퓨처엠",
        ],
        "stocks": ["LG에너지솔루션", "에코프로비엠", "포스코퓨처엠"],
        "cause": "전기차·배터리 수요와 소재 가격 흐름이 주목받았습니다.",
        "effect": "배터리 셀·소재 관련 종목의 반등 또는 변동성 확대 가능성이 있습니다.",
        "chain_core": ["전기차 수요", "배터리 밸류체인", "2차전지"],
    },
}


MONEY_FLOW_KEYWORDS: Dict[str, Dict[str, Any]] = {
    "nasdaq": {
        "keywords": ["나스닥", "nasdaq", "미국 기술주", "기술주", "빅테크"],
        "themes": ["반도체AI", "AI인프라"],
        "weight": 1.4,
        "label": "미국 기술주 흐름",
    },
    "nvidia": {
        "keywords": ["엔비디아", "nvidia", "gpu"],
        "themes": ["반도체AI", "AI인프라"],
        "weight": 1.8,
        "label": "엔비디아·GPU 모멘텀",
    },
    "microsoft": {
        "keywords": ["마이크로소프트", "microsoft", "ms", "azure"],
        "themes": ["반도체AI", "AI인프라"],
        "weight": 1.5,
        "label": "마이크로소프트 AI 투자 기대",
    },
    "oil": {
        "keywords": ["유가", "원유", "wti", "브렌트", "brent"],
        "themes": ["조선"],
        "weight": 0.7,
        "label": "국제유가 흐름",
    },
    "fx": {
        "keywords": ["환율", "달러", "원달러", "원/달러", "강달러"],
        "themes": ["반도체AI", "자동차", "조선"],
        "weight": 0.6,
        "label": "환율 흐름",
    },
    "power": {
        "keywords": ["전력", "전력망", "전력수급", "데이터센터 전력"],
        "themes": ["AI인프라", "원전"],
        "weight": 1.4,
        "label": "전력 수요 모멘텀",
    },
}


# ------------------------------------------------------------
# 2. 데이터 구조
# ------------------------------------------------------------

@dataclass
class ReasoningItem:
    rank: int
    theme: str
    sector: str
    stocks: List[str]
    cause: str
    effect: str
    chain: List[str]
    confidence: float
    score: float
    evidence: List[str]
    action_hint: str
    raw_factors: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# 3. 유틸리티
# ------------------------------------------------------------

def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize(text: Any) -> str:
    text = _safe_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_text_from_item(item: Any) -> str:
    """뉴스·공시·시간외 데이터 등 다양한 dict/list/string 입력에서 검색용 텍스트를 추출한다."""
    if item is None:
        return ""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        keys = [
            "title", "headline", "summary", "content", "body", "description", "text",
            "name", "stock", "sector", "theme", "reason", "memo", "source",
        ]
        parts: List[str] = []
        for key in keys:
            if key in item and item.get(key) is not None:
                parts.append(_safe_text(item.get(key)))
        # 지정 키가 없더라도 값 일부를 읽어 최소한의 단서 확보
        if not parts:
            for value in item.values():
                if isinstance(value, (str, int, float)):
                    parts.append(_safe_text(value))
        return " ".join(parts)
    if isinstance(item, (list, tuple, set)):
        return " ".join(_extract_text_from_item(x) for x in item)
    return _safe_text(item)


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _keyword_hits(text: str, keywords: Sequence[str]) -> List[str]:
    ntext = _normalize(text)
    hits: List[str] = []
    for kw in keywords:
        nkw = _normalize(kw)
        if nkw and nkw in ntext:
            hits.append(kw)
    return hits


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid_score(score: float) -> float:
    """원점수를 0~1 confidence로 부드럽게 변환한다."""
    return 1.0 / (1.0 + math.exp(-score / 4.5))


def _get_numeric(item: Dict[str, Any], keys: Sequence[str], default: float = 0.0) -> float:
    for key in keys:
        if key in item:
            try:
                return float(item.get(key) or 0.0)
            except Exception:
                continue
    return default


# ------------------------------------------------------------
# 4. 입력별 점수 계산
# ------------------------------------------------------------

def _score_theme_from_news(theme: str, news_items: Sequence[Any]) -> Tuple[float, List[str]]:
    config = THEME_SECTOR_MAP.get(theme, {})
    keywords = config.get("keywords", [])
    score = 0.0
    evidence: List[str] = []

    for item in news_items:
        text = _extract_text_from_item(item)
        hits = _keyword_hits(text, keywords)
        if not hits:
            continue

        # 한 기사에서 키워드가 여러 개 잡히면 가중치를 높이되 과도한 중복은 제한
        local_score = min(3.0, 0.9 + 0.35 * len(set(hits)))
        score += local_score

        title = ""
        if isinstance(item, dict):
            title = _safe_text(item.get("title") or item.get("headline") or item.get("summary") or "")
        if not title:
            title = text[:80]
        evidence.append(f"뉴스 단서: {title[:100]}")

    return score, evidence[:5]


def _score_theme_from_theme_graph(theme: str, theme_graph: Any) -> Tuple[float, List[str]]:
    """theme_graph가 dict/list 어느 형태여도 최대한 읽는다."""
    if not theme_graph:
        return 0.0, []

    score = 0.0
    evidence: List[str] = []
    config = THEME_SECTOR_MAP.get(theme, {})
    keywords = [theme] + config.get("keywords", [])

    if isinstance(theme_graph, dict):
        # 직접 theme 키가 있는 경우
        for key, value in theme_graph.items():
            key_text = _safe_text(key)
            value_text = _extract_text_from_item(value)
            joined = f"{key_text} {value_text}"
            hits = _keyword_hits(joined, keywords)
            if hits:
                numeric = 0.0
                if isinstance(value, dict):
                    numeric = _get_numeric(value, ["score", "weight", "count", "strength"], 1.0)
                elif isinstance(value, (int, float)):
                    numeric = float(value)
                else:
                    numeric = 1.0
                score += max(0.8, min(5.0, numeric))
                evidence.append(f"Theme Graph 단서: {key_text}")

    elif isinstance(theme_graph, list):
        for node in theme_graph:
            text = _extract_text_from_item(node)
            hits = _keyword_hits(text, keywords)
            if hits:
                numeric = 1.0
                if isinstance(node, dict):
                    numeric = _get_numeric(node, ["score", "weight", "count", "strength"], 1.0)
                score += max(0.8, min(5.0, numeric))
                evidence.append(f"Theme Graph 단서: {text[:80]}")

    return score, evidence[:5]


def _score_theme_from_sector(theme: str, sector_results: Sequence[Any]) -> Tuple[float, List[str], Optional[str]]:
    config = THEME_SECTOR_MAP.get(theme, {})
    target_sector = config.get("sector", theme)
    keywords = [theme, target_sector] + config.get("keywords", [])

    score = 0.0
    evidence: List[str] = []
    matched_sector: Optional[str] = None

    for item in sector_results:
        text = _extract_text_from_item(item)
        hits = _keyword_hits(text, keywords)
        if not hits:
            continue

        sector_name = target_sector
        if isinstance(item, dict):
            sector_name = _safe_text(item.get("sector") or item.get("name") or target_sector)
            numeric = _get_numeric(item, ["score", "total_score", "strength", "momentum"], 1.0)
        else:
            numeric = 1.0

        score += max(0.8, min(5.0, numeric))
        matched_sector = sector_name or target_sector
        evidence.append(f"섹터 단서: {sector_name}")

    return score, evidence[:5], matched_sector


def _score_theme_from_candidates(theme: str, candidate_scores: Sequence[Any]) -> Tuple[float, List[str], List[str]]:
    config = THEME_SECTOR_MAP.get(theme, {})
    keywords = [theme, config.get("sector", "")] + config.get("keywords", [])
    default_stocks = config.get("stocks", [])

    score = 0.0
    evidence: List[str] = []
    stocks: List[str] = []

    for item in candidate_scores:
        text = _extract_text_from_item(item)
        hits = _keyword_hits(text, keywords + default_stocks)
        if not hits:
            continue

        stock_name = ""
        if isinstance(item, dict):
            stock_name = _safe_text(
                item.get("stock")
                or item.get("name")
                or item.get("종목")
                or item.get("종목명")
                or item.get("ticker_name")
                or ""
            )
            numeric = _get_numeric(item, ["score", "final_score", "total_score", "candidate_score"], 1.0)
        else:
            stock_name = text[:30]
            numeric = 1.0

        if stock_name:
            stocks.append(stock_name)
        score += max(0.7, min(4.0, numeric / 20.0 if numeric > 10 else numeric))
        evidence.append(f"후보종목 단서: {stock_name or text[:60]}")

    # 후보 데이터에서 직접 못 찾았더라도 기본 대표주를 연결
    unique_stocks = _unique_preserve_order(stocks)[:5]
    return score, evidence[:5], unique_stocks


def _score_theme_from_money_flow(theme: str, after_hours_data: Any, indicators: Any, market_decision: Any) -> Tuple[float, List[str]]:
    texts: List[str] = []
    texts.append(_extract_text_from_item(after_hours_data))
    texts.append(_extract_text_from_item(indicators))
    texts.append(_extract_text_from_item(market_decision))
    joined = " ".join(texts)

    score = 0.0
    evidence: List[str] = []

    for flow_key, flow in MONEY_FLOW_KEYWORDS.items():
        hits = _keyword_hits(joined, flow.get("keywords", []))
        if not hits:
            continue
        if theme not in flow.get("themes", []):
            continue
        weight = float(flow.get("weight", 1.0))
        score += weight
        evidence.append(f"자금흐름 단서: {flow.get('label', flow_key)}")

    return score, evidence[:5]


# ------------------------------------------------------------
# 5. 추론 문장 생성
# ------------------------------------------------------------

def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for item in items:
        text = _safe_text(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _build_chain(theme: str, evidence: Sequence[str], stocks: Sequence[str]) -> List[str]:
    config = THEME_SECTOR_MAP.get(theme, {})
    chain = list(config.get("chain_core", []))

    # evidence에서 대표 원인을 하나 앞단에 추가
    if evidence:
        first = evidence[0]
        if "뉴스 단서:" in first:
            chain.insert(0, "관련 뉴스 부각")
        elif "자금흐름" in first:
            chain.insert(0, "글로벌 자금흐름")
        elif "Theme Graph" in first:
            chain.insert(0, "테마 집중도 상승")

    if stocks:
        chain.append(stocks[0])

    return _unique_preserve_order(chain)


def _build_action_hint(theme: str, sector: str) -> str:
    if theme in ("반도체AI", "AI인프라"):
        return "장 초반 거래대금, 외국인 수급, 미국 기술주 흐름이 이어지는지 확인할 필요가 있습니다."
    if theme == "원전":
        return "정책 발언의 후속 보도, 전력수급 이슈, 원전 기자재 종목의 거래량 지속 여부를 확인할 필요가 있습니다."
    if theme == "방산":
        return "수출 계약·지정학 뉴스의 추가성, 기관 수급, 방산 대형주의 동반 강세 여부를 확인할 필요가 있습니다."
    if theme == "조선":
        return "신규 수주 뉴스, 환율 흐름, 조선 대형주의 동반 강세 여부를 확인할 필요가 있습니다."
    if theme == "바이오":
        return "임상·허가 이벤트의 사실 여부와 장중 변동성 확대 여부를 확인할 필요가 있습니다."
    return f"{sector} 업종의 거래대금, 수급 지속성, 관련 뉴스의 추가 확산 여부를 확인할 필요가 있습니다."


def _make_reasoning_item(
    *,
    rank: int,
    theme: str,
    sector: str,
    stocks: List[str],
    raw_score: float,
    evidence: List[str],
    raw_factors: Dict[str, Any],
) -> ReasoningItem:
    config = THEME_SECTOR_MAP.get(theme, {})
    confidence = round(_clip(_sigmoid_score(raw_score), 0.05, 0.95), 2)
    score = round(confidence * 100, 1)
    final_stocks = _unique_preserve_order(stocks + config.get("stocks", []))[:5]

    return ReasoningItem(
        rank=rank,
        theme=theme,
        sector=sector or config.get("sector", theme),
        stocks=final_stocks,
        cause=config.get("cause", f"{theme} 관련 이슈가 부각되었습니다."),
        effect=config.get("effect", f"{sector or theme} 업종의 투자심리에 영향을 줄 수 있습니다."),
        chain=_build_chain(theme, evidence, final_stocks),
        confidence=confidence,
        score=score,
        evidence=_unique_preserve_order(evidence)[:8],
        action_hint=_build_action_hint(theme, sector or config.get("sector", theme)),
        raw_factors=raw_factors,
    )


# ------------------------------------------------------------
# 6. 외부 호출 함수
# ------------------------------------------------------------

def build_reasoning_layer(
    *,
    news_items: Optional[Sequence[Any]] = None,
    theme_graph: Any = None,
    sector_results: Optional[Sequence[Any]] = None,
    candidate_scores: Optional[Sequence[Any]] = None,
    after_hours_data: Any = None,
    indicators: Any = None,
    market_decision: Any = None,
    max_items: int = 5,
    min_confidence: float = 0.35,
) -> List[Dict[str, Any]]:
    """
    v2.2 핵심 함수.

    Parameters
    ----------
    news_items:
        뉴스 리스트. dict/string 모두 허용.
    theme_graph:
        Theme Graph 결과. dict/list 모두 허용.
    sector_results:
        섹터 분석 결과 리스트.
    candidate_scores:
        관심종목 점수 결과 리스트.
    after_hours_data:
        시간외 거래 또는 해외시장 데이터.
    indicators:
        환율·유가·미국시장 등 시장지표.
    market_decision:
        AI 투자전략 또는 시장판단 결과.
    max_items:
        반환할 추론 체인 개수.
    min_confidence:
        최소 confidence. 기본 0.35.

    Returns
    -------
    List[Dict[str, Any]]
        Story Engine과 Dashboard가 공통으로 사용할 표준 추론 객체.
    """
    news_list = _as_list(news_items)
    sector_list = _as_list(sector_results)
    candidate_list = _as_list(candidate_scores)

    items: List[ReasoningItem] = []

    for theme in THEME_SECTOR_MAP.keys():
        news_score, news_evidence = _score_theme_from_news(theme, news_list)
        graph_score, graph_evidence = _score_theme_from_theme_graph(theme, theme_graph)
        sector_score, sector_evidence, matched_sector = _score_theme_from_sector(theme, sector_list)
        candidate_score, candidate_evidence, candidate_stocks = _score_theme_from_candidates(theme, candidate_list)
        flow_score, flow_evidence = _score_theme_from_money_flow(
            theme,
            after_hours_data=after_hours_data,
            indicators=indicators,
            market_decision=market_decision,
        )

        # 가중치: 뉴스 35%, Theme Graph 25%, 섹터 20%, 후보종목 10%, 자금흐름 10%
        raw_score = (
            news_score * 0.35
            + graph_score * 0.25
            + sector_score * 0.20
            + candidate_score * 0.10
            + flow_score * 0.10
        )

        evidence = news_evidence + graph_evidence + sector_evidence + candidate_evidence + flow_evidence

        # 완전히 단서가 없으면 제외
        if raw_score <= 0 or not evidence:
            continue

        sector = matched_sector or THEME_SECTOR_MAP[theme].get("sector", theme)
        raw_factors = {
            "news_score": round(news_score, 3),
            "theme_graph_score": round(graph_score, 3),
            "sector_score": round(sector_score, 3),
            "candidate_score": round(candidate_score, 3),
            "money_flow_score": round(flow_score, 3),
            "raw_score": round(raw_score, 3),
        }

        item = _make_reasoning_item(
            rank=0,
            theme=theme,
            sector=sector,
            stocks=candidate_stocks,
            raw_score=raw_score,
            evidence=evidence,
            raw_factors=raw_factors,
        )

        if item.confidence >= min_confidence:
            items.append(item)

    # confidence 우선, 동률이면 raw_score 우선
    items.sort(key=lambda x: (x.confidence, x.raw_factors.get("raw_score", 0)), reverse=True)

    final_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(items[:max_items], start=1):
        item.rank = idx
        final_items.append(item.to_dict())

    return final_items


def build_reasoning_brief(reasonings: Sequence[Dict[str, Any]], max_sentences: int = 5) -> str:
    """
    Story Engine 연동 전이라도 바로 사용할 수 있는 간단 브리핑 생성기.
    market_story_engine.py에서는 이 함수를 호출하거나, reasonings를 직접 읽어 문장을 만들 수 있다.
    """
    if not reasonings:
        return "뚜렷한 주도 테마가 확인되지 않아 장 초반에는 지수 방향성과 거래대금 변화를 먼저 확인할 필요가 있습니다."

    sentences: List[str] = []
    top = reasonings[0]
    top_theme = top.get("theme", "주도 테마")
    top_sector = top.get("sector", "관련 업종")
    top_chain = " → ".join(top.get("chain", [])[:5])

    sentences.append(
        f"오늘 시장은 {top_theme} 테마를 중심으로 {top_sector} 업종의 투자심리가 먼저 형성될 가능성이 있습니다."
    )
    if top_chain:
        sentences.append(f"핵심 추론 흐름은 {top_chain}으로 정리됩니다.")
    sentences.append(_safe_text(top.get("effect", "관련 업종의 수급 변화를 확인할 필요가 있습니다.")))

    for item in reasonings[1:max_sentences - 1]:
        theme = item.get("theme", "테마")
        sector = item.get("sector", "업종")
        confidence = item.get("confidence", 0)
        sentences.append(
            f"보조 흐름으로는 {theme} 테마가 확인되며, {sector} 업종은 추론 신뢰도 {confidence:.2f} 수준에서 관찰 대상입니다."
        )

    sentences.append(_safe_text(top.get("action_hint", "장 초반 거래대금과 수급 지속 여부를 확인할 필요가 있습니다.")))

    return "\n".join(f"- {s}" for s in sentences[:max_sentences])


def get_top_reasoning(reasonings: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Dashboard나 Story Engine에서 최상위 추론만 간단히 가져오기 위한 헬퍼."""
    if not reasonings:
        return None
    return dict(reasonings[0])


# ------------------------------------------------------------
# 7. 단독 테스트용 예시
# ------------------------------------------------------------

if __name__ == "__main__":
    sample_news = [
        {"title": "마이크로소프트 AI 데이터센터 투자 확대 기대"},
        {"title": "전력수급 이슈에 원전·SMR 관련주 관심"},
        {"title": "엔비디아 강세에 HBM 수요 기대 부각"},
    ]
    sample_theme_graph = {
        "반도체AI": {"score": 4.2},
        "원전": {"score": 2.5},
    }
    sample_sector_results = [
        {"sector": "반도체", "score": 3.5},
        {"sector": "원전", "score": 2.1},
    ]
    sample_candidates = [
        {"stock": "삼성전자", "sector": "반도체", "score": 86},
        {"stock": "SK하이닉스", "sector": "반도체", "score": 91},
        {"stock": "두산에너빌리티", "sector": "원전", "score": 77},
    ]

    result = build_reasoning_layer(
        news_items=sample_news,
        theme_graph=sample_theme_graph,
        sector_results=sample_sector_results,
        candidate_scores=sample_candidates,
        indicators={"nasdaq": "미국 기술주 강세", "fx": "원달러 환율 안정"},
        max_items=3,
    )

    from pprint import pprint

    pprint(result)
    print(build_reasoning_brief(result))
