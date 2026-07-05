# stock/theme_graph.py
# ------------------------------------------------------------
# MYAIEDITOR v2.2 Theme Knowledge Graph Engine
# ------------------------------------------------------------
# 역할:
# - 단순 키워드 감지를 넘어 "뉴스 → 테마 → 산업 → 공급망 → 종목 → 리스크 → 매매 아이디어"
#   흐름을 구조화한다.
# - Theme Graph는 앞으로 Market Story, Candidate Score, Narrative Builder,
#   AI Prompt의 공통 지식 기반으로 사용된다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ------------------------------------------------------------
# Data Models
# ------------------------------------------------------------

@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompanyLink:
    name: str
    role: str
    sensitivity: float = 50.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThemeKnowledgeNode:
    theme: str
    score: float
    category: str = ""
    parent: str = ""
    children: List[str] = field(default_factory=list)
    industries: List[str] = field(default_factory=list)
    supply_chain: List[str] = field(default_factory=list)
    companies: List[Dict[str, Any]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    watch_points: List[str] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    story: str = ""
    money_flow: str = ""
    trading_idea: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# Knowledge Base
# ------------------------------------------------------------
# 구조:
# theme
#   category      : 대분류
#   parent        : 상위 테마
#   children      : 하위 테마
#   industries    : 연결 산업
#   supply_chain  : 공급망 단계
#   companies     : 관련 기업과 역할
#   keywords      : 감지 키워드
#   triggers      : 강세 트리거
#   risks         : 리스크
#   watch_points  : 장 시작 후 체크포인트
#   story         : 설명 문장
#   money_flow    : 자금 흐름 해석
#   trading_idea  : 장전 대응 아이디어

THEME_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "AI 데이터센터": {
        "category": "AI",
        "parent": "AI 인프라",
        "children": ["HBM", "GPU", "전력망", "냉각", "클라우드"],
        "industries": ["반도체", "전력기기", "전선", "클라우드"],
        "supply_chain": ["빅테크 투자", "AI 서버", "GPU", "HBM", "전력망", "전력기기"],
        "companies": [
            {"name": "삼성전자", "role": "메모리·HBM 대형주", "sensitivity": 88},
            {"name": "SK하이닉스", "role": "HBM 핵심 공급망", "sensitivity": 95},
            {"name": "한미반도체", "role": "HBM 후공정 장비", "sensitivity": 90},
            {"name": "LS ELECTRIC", "role": "전력기기·전력망", "sensitivity": 82},
            {"name": "대한전선", "role": "전선·전력망", "sensitivity": 72},
        ],
        "keywords": ["AI 데이터센터", "데이터센터", "AI 서버", "클라우드", "AI 인프라", "전력 수요", "전력망"],
        "triggers": ["빅테크 AI 투자 확대", "데이터센터 증설", "전력 인프라 투자"],
        "risks": ["전력 수급 부담", "빅테크 투자 속도 둔화", "AI 테마 과열"],
        "watch_points": ["미국 빅테크 주가", "전력기기·전선 동반 강세 여부", "반도체 대형주 수급"],
        "story": "AI 데이터센터 투자는 반도체와 전력 인프라를 동시에 자극하는 확장형 테마입니다.",
        "money_flow": "AI 소프트웨어에서 메모리·전력 인프라 쪽으로 자금이 확산될 수 있습니다.",
        "trading_idea": "반도체 대형주와 전력기기 종목이 동시에 움직이는지 확인합니다.",
    },
    "HBM": {
        "category": "AI",
        "parent": "AI 반도체",
        "children": ["AI 메모리", "후공정", "테스트소켓", "반도체 장비"],
        "industries": ["메모리", "반도체 장비", "후공정", "소부장"],
        "supply_chain": ["AI 서버", "GPU", "HBM", "후공정", "테스트", "소켓"],
        "companies": [
            {"name": "SK하이닉스", "role": "HBM 선도 메모리", "sensitivity": 96},
            {"name": "삼성전자", "role": "메모리·HBM 대형주", "sensitivity": 90},
            {"name": "한미반도체", "role": "TC본더·후공정 장비", "sensitivity": 92},
            {"name": "ISC", "role": "테스트소켓", "sensitivity": 84},
            {"name": "리노공업", "role": "검사용 소켓·핀", "sensitivity": 78},
            {"name": "원익IPS", "role": "반도체 장비", "sensitivity": 72},
        ],
        "keywords": ["HBM", "HBM3", "HBM3E", "HBM4", "고대역폭메모리", "AI 메모리", "엔비디아", "NVIDIA", "GPU"],
        "triggers": ["엔비디아 공급망 기대", "AI 서버 투자 증가", "메모리 가격 반등"],
        "risks": ["엔비디아 약세", "단기 급등에 따른 차익실현", "공급 경쟁 심화"],
        "watch_points": ["SK하이닉스·삼성전자 동반 강세", "후공정 장비주 확산 여부", "외국인 수급"],
        "story": "HBM은 AI 서버 투자와 가장 직접적으로 연결되는 국내 반도체 핵심 테마입니다.",
        "money_flow": "대형 메모리주에서 후공정·소부장으로 수급이 확산될 가능성이 있습니다.",
        "trading_idea": "대형주가 먼저 강하고 후공정 종목이 따라붙는 순환 흐름을 확인합니다.",
    },
    "반도체 장비": {
        "category": "반도체",
        "parent": "반도체·AI",
        "children": ["후공정", "증착", "식각", "테스트", "패키징"],
        "industries": ["반도체 장비", "소부장", "후공정"],
        "supply_chain": ["설비투자", "공정장비", "후공정", "검사", "소켓"],
        "companies": [
            {"name": "한미반도체", "role": "후공정 장비", "sensitivity": 90},
            {"name": "주성엔지니어링", "role": "증착 장비", "sensitivity": 80},
            {"name": "원익IPS", "role": "전공정 장비", "sensitivity": 78},
            {"name": "ISC", "role": "테스트소켓", "sensitivity": 78},
            {"name": "리노공업", "role": "검사용 부품", "sensitivity": 74},
        ],
        "keywords": ["반도체 장비", "후공정", "패키징", "TC본더", "테스트소켓", "증착", "식각", "소부장"],
        "triggers": ["반도체 설비투자 재개", "HBM 후공정 투자", "검사·패키징 수요 확대"],
        "risks": ["대형주 수급 약화", "장비 수주 지연", "소부장 단기 과열"],
        "watch_points": ["삼성전자·SK하이닉스 흐름", "장비주 거래량 증가", "후공정 종목 확산"],
        "story": "반도체 장비 테마는 대형 메모리주 강세 이후 후속 수급이 붙는 경우가 많습니다.",
        "money_flow": "대형주에서 장비·소부장으로 자금이 확산되는지 확인해야 합니다.",
        "trading_idea": "대형주보다 변동성이 크므로 장 초반 거래량 동반 여부가 중요합니다.",
    },
    "전력망": {
        "category": "전력",
        "parent": "AI 인프라",
        "children": ["변압기", "전선", "송전망", "해저케이블"],
        "industries": ["전력기기", "전선", "전력 인프라"],
        "supply_chain": ["전력 수요", "송전망", "변압기", "전선", "해저케이블"],
        "companies": [
            {"name": "LS ELECTRIC", "role": "전력기기", "sensitivity": 88},
            {"name": "LS", "role": "전력·전선 지주", "sensitivity": 78},
            {"name": "대한전선", "role": "전선", "sensitivity": 76},
            {"name": "LS에코에너지", "role": "전선·해저케이블", "sensitivity": 72},
            {"name": "HD현대일렉트릭", "role": "변압기", "sensitivity": 84},
        ],
        "keywords": ["전력망", "전선", "변압기", "송전망", "전력기기", "해저케이블", "전력 인프라", "데이터센터"],
        "triggers": ["AI 데이터센터 전력 수요", "전력망 투자 확대", "변압기 수주 증가"],
        "risks": ["구리 가격 상승", "수주 피크아웃 우려", "단기 급등 부담"],
        "watch_points": ["전력기기 대표주 수급", "구리 가격", "AI 데이터센터 뉴스 지속성"],
        "story": "전력망은 AI 데이터센터 확산과 함께 부각되는 인프라 테마입니다.",
        "money_flow": "AI 반도체에서 전력 인프라로 자금이 확산되는 국면에서 강해질 수 있습니다.",
        "trading_idea": "반도체와 전력기기가 동시에 강하면 AI 인프라 테마 확산으로 해석합니다.",
    },
    "SMR": {
        "category": "원전",
        "parent": "원전",
        "children": ["원전 수출", "발전설비", "전력망"],
        "industries": ["원전", "발전설비", "전력"],
        "supply_chain": ["정책", "원전 설계", "발전설비", "시공", "전력 공급"],
        "companies": [
            {"name": "두산에너빌리티", "role": "원전 기자재·터빈", "sensitivity": 88},
            {"name": "한전기술", "role": "원전 설계", "sensitivity": 82},
            {"name": "한국전력", "role": "전력 공기업", "sensitivity": 70},
        ],
        "keywords": ["SMR", "소형모듈원전", "원전", "원자력", "원전 수출", "체코 원전", "폴란드 원전"],
        "triggers": ["원전 정책 기대", "미국 원자력 규제 완화", "해외 원전 수주"],
        "risks": ["정책 지연", "수주 불확실성", "단기 테마 과열"],
        "watch_points": ["원전 정책 뉴스", "두산에너빌리티 거래량", "한전기술 동반 강세"],
        "story": "SMR은 원전 정책과 전력 수요 확대가 맞물릴 때 강하게 부각되는 정책 테마입니다.",
        "money_flow": "반도체·AI 이후 전력 수요 논리가 원전 테마로 확산될 수 있습니다.",
        "trading_idea": "정책 뉴스와 대표주 거래량이 함께 확인될 때만 강한 신호로 봅니다.",
    },
    "방산 수출": {
        "category": "방산",
        "parent": "방산",
        "children": ["K9", "K2", "유도무기", "항공우주"],
        "industries": ["방산", "항공우주", "기계"],
        "supply_chain": ["지정학 리스크", "국방 예산", "수출 계약", "실적"],
        "companies": [
            {"name": "한화에어로스페이스", "role": "방산 대형주", "sensitivity": 90},
            {"name": "LIG넥스원", "role": "유도무기", "sensitivity": 86},
            {"name": "현대로템", "role": "지상무기", "sensitivity": 82},
            {"name": "한국항공우주", "role": "항공기", "sensitivity": 78},
            {"name": "한화시스템", "role": "방산전자", "sensitivity": 74},
        ],
        "keywords": ["방산", "수출", "K9", "K2", "천무", "유도무기", "미사일", "폴란드", "NATO", "국방"],
        "triggers": ["해외 방산 수주", "지정학 리스크", "국방 예산 증가"],
        "risks": ["수주 기대 선반영", "정책·외교 변수", "단기 급등"],
        "watch_points": ["수주 뉴스", "대표 방산주 동반 강세", "거래대금 증가"],
        "story": "방산 수출 테마는 계약 뉴스와 지정학 리스크가 결합될 때 대형 방산주로 수급이 집중됩니다.",
        "money_flow": "시장 방어 심리가 커질수록 방산 대형주로 자금이 이동할 수 있습니다.",
        "trading_idea": "방산주는 뉴스 지속성과 거래대금 동반 여부를 함께 확인해야 합니다.",
    },
    "LNG선": {
        "category": "조선",
        "parent": "조선",
        "children": ["친환경선박", "수주잔고", "선가"],
        "industries": ["조선", "해양플랜트"],
        "supply_chain": ["해운 수요", "선가", "수주", "건조", "실적"],
        "companies": [
            {"name": "HD현대중공업", "role": "조선 대형주", "sensitivity": 86},
            {"name": "삼성중공업", "role": "LNG선·해양플랜트", "sensitivity": 84},
            {"name": "HD한국조선해양", "role": "조선 지주", "sensitivity": 82},
            {"name": "한화오션", "role": "조선·방산", "sensitivity": 78},
        ],
        "keywords": ["LNG", "LNG선", "조선", "수주", "선가", "친환경선박", "해양플랜트", "탱커"],
        "triggers": ["LNG선 수주", "선가 상승", "수주잔고 개선"],
        "risks": ["원가 부담", "수주 공백", "유가 급변"],
        "watch_points": ["조선 대형주 동반 강세", "수주 뉴스", "유가 흐름"],
        "story": "LNG선 테마는 수주와 선가 흐름이 조선 대형주의 실적 기대와 연결됩니다.",
        "money_flow": "경기민감주 내에서 조선으로 자금이 이동할 때 강하게 부각됩니다.",
        "trading_idea": "대형 조선주가 함께 움직이면 섹터 흐름으로 판단합니다.",
    },
    "2차전지": {
        "category": "2차전지",
        "parent": "전기차",
        "children": ["양극재", "음극재", "ESS", "전고체"],
        "industries": ["배터리", "소재", "전기차"],
        "supply_chain": ["전기차 수요", "배터리 셀", "양극재", "리튬", "ESS"],
        "companies": [
            {"name": "LG에너지솔루션", "role": "배터리 셀", "sensitivity": 82},
            {"name": "삼성SDI", "role": "배터리 셀", "sensitivity": 80},
            {"name": "에코프로비엠", "role": "양극재", "sensitivity": 86},
            {"name": "에코프로", "role": "2차전지 지주", "sensitivity": 84},
            {"name": "포스코퓨처엠", "role": "배터리 소재", "sensitivity": 82},
        ],
        "keywords": ["2차전지", "배터리", "전기차", "양극재", "음극재", "리튬", "ESS", "전고체", "테슬라"],
        "triggers": ["전기차 수요 회복", "ESS 투자", "소재 가격 안정"],
        "risks": ["테슬라 약세", "소재 가격 하락", "전기차 수요 둔화"],
        "watch_points": ["테슬라 주가", "배터리 소재주 거래량", "전기차 뉴스"],
        "story": "2차전지는 성장 기대가 크지만 테슬라와 소재 가격에 민감한 고변동성 테마입니다.",
        "money_flow": "성장주 선호가 회복될 때 반도체 다음 순환 후보가 될 수 있습니다.",
        "trading_idea": "테슬라 약세 구간에서는 추격보다 변동성 관리가 우선입니다.",
    },
    "바이오시밀러": {
        "category": "바이오",
        "parent": "바이오",
        "children": ["의약품 수출", "FDA", "CDMO", "기술수출"],
        "industries": ["바이오", "제약", "헬스케어"],
        "supply_chain": ["임상", "허가", "생산", "판매", "수출"],
        "companies": [
            {"name": "셀트리온", "role": "바이오시밀러", "sensitivity": 86},
            {"name": "삼성바이오로직스", "role": "CDMO", "sensitivity": 84},
            {"name": "알테오젠", "role": "기술수출", "sensitivity": 82},
            {"name": "휴젤", "role": "미용·바이오", "sensitivity": 72},
        ],
        "keywords": ["바이오", "바이오시밀러", "FDA", "임상", "허가", "CDMO", "기술수출", "의약품"],
        "triggers": ["FDA 허가", "기술수출", "CDMO 수주"],
        "risks": ["임상 실패", "허가 지연", "개별주 변동성"],
        "watch_points": ["허가·수주 뉴스", "대형 바이오주 수급", "개별 공시"],
        "story": "바이오는 허가·임상·기술수출 뉴스에 따라 개별 종목 중심으로 반응합니다.",
        "money_flow": "위험선호가 회복될 때 성장주 내 후순위 순환 후보가 될 수 있습니다.",
        "trading_idea": "뉴스와 공시가 없는 급등은 추격보다 확인이 필요합니다.",
    },
    "주주환원": {
        "category": "금융",
        "parent": "밸류업",
        "children": ["배당", "자사주", "은행"],
        "industries": ["금융", "은행", "보험"],
        "supply_chain": ["금리", "순이자마진", "이익", "배당", "자사주"],
        "companies": [
            {"name": "KB금융", "role": "은행 대형주", "sensitivity": 82},
            {"name": "신한지주", "role": "은행 대형주", "sensitivity": 80},
            {"name": "하나금융지주", "role": "은행 대형주", "sensitivity": 78},
            {"name": "우리금융지주", "role": "은행 대형주", "sensitivity": 76},
        ],
        "keywords": ["주주환원", "배당", "자사주", "은행", "금융", "밸류업", "금리", "NIM"],
        "triggers": ["배당 확대", "자사주 매입", "밸류업 정책"],
        "risks": ["금리 하락", "대출 규제", "경기 둔화"],
        "watch_points": ["외국인 수급", "배당주 강세", "금리 흐름"],
        "story": "주주환원 테마는 시장 변동성이 커질 때 방어적 자금이 유입될 수 있는 테마입니다.",
        "money_flow": "성장주가 흔들릴 때 금융·배당주로 자금이 이동할 수 있습니다.",
        "trading_idea": "방어적 장세에서는 금융주가 상대적으로 안정적인 후보가 됩니다.",
    },
}


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _item_to_text(item: Any) -> str:
    if isinstance(item, dict):
        keys = ["title", "description", "content", "summary", "source", "published", "memo"]
        return " ".join(str(item.get(k, "") or "") for k in keys)
    return " ".join(str(getattr(item, k, "") or "") for k in ["title", "description", "content", "summary", "source", "published", "memo"])


def _items_to_text(items: Optional[List[Any]]) -> str:
    return " ".join(_item_to_text(x) for x in (items or []))


def _dedupe(items: Iterable[str], limit: Optional[int] = None) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items or []:
        text = _clean(item)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if limit is not None and len(out) >= int(limit):
            break
    return out


def _keyword_count(text: str, keyword: str) -> int:
    return str(text or "").lower().count(str(keyword or "").lower())


def _matched_keywords(text: str, keywords: Iterable[str], limit: int = 10) -> List[str]:
    out: List[str] = []
    low = str(text or "").lower()
    for kw in keywords or []:
        k = str(kw or "").strip()
        if k and k.lower() in low and k not in out:
            out.append(k)
        if len(out) >= limit:
            break
    return out


def _score_theme(text: str, theme: str, rule: Dict[str, Any]) -> Tuple[float, List[str]]:
    matched = _matched_keywords(text, rule.get("keywords", []), limit=10)
    score = 0.0

    for kw in matched:
        cnt = _keyword_count(text, kw)
        score += 18.0 + min(max(cnt - 1, 0), 5) * 4.0

    if _keyword_count(text, theme) > 0 and theme not in matched:
        matched.append(theme)
        score += 22.0

    # 상위/하위/공급망 키워드가 같이 등장하면 그래프 연결 보너스
    for key in ["parent", "category"]:
        val = str(rule.get(key, "") or "")
        if val and _keyword_count(text, val) > 0:
            score += 6.0

    for child in rule.get("children", []) or []:
        if _keyword_count(text, child) > 0:
            score += 5.0

    for step in rule.get("supply_chain", []) or []:
        if _keyword_count(text, step) > 0:
            score += 4.0

    return min(score, 100.0), _dedupe(matched, limit=10)


def _build_edges(theme: str, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    edges: List[GraphEdge] = []

    parent = rule.get("parent", "")
    if parent:
        edges.append(GraphEdge(source=parent, target=theme, relation="parent_to_theme", weight=1.0))

    last = theme
    for child in rule.get("children", []) or []:
        edges.append(GraphEdge(source=theme, target=child, relation="theme_to_child", weight=0.8))

    chain = rule.get("supply_chain", []) or []
    for i in range(len(chain) - 1):
        edges.append(GraphEdge(source=chain[i], target=chain[i + 1], relation="supply_chain", weight=0.9))

    for company in rule.get("companies", []) or []:
        cname = company.get("name", "") if isinstance(company, dict) else str(company)
        if cname:
            edges.append(GraphEdge(source=theme, target=cname, relation="theme_to_company", weight=float(company.get("sensitivity", 50)) / 100 if isinstance(company, dict) else 0.5))

    return [e.to_dict() for e in edges]


def _build_node(theme: str, score: float, matched: List[str], rule: Dict[str, Any]) -> ThemeKnowledgeNode:
    return ThemeKnowledgeNode(
        theme=theme,
        score=round(score, 1),
        category=str(rule.get("category", "") or ""),
        parent=str(rule.get("parent", "") or ""),
        children=_dedupe(rule.get("children", []) or [], limit=10),
        industries=_dedupe(rule.get("industries", []) or [], limit=10),
        supply_chain=_dedupe(rule.get("supply_chain", []) or [], limit=12),
        companies=[dict(c) if isinstance(c, dict) else {"name": str(c), "role": "", "sensitivity": 50} for c in (rule.get("companies", []) or [])],
        keywords=_dedupe(rule.get("keywords", []) or [], limit=20),
        matched_keywords=matched,
        triggers=_dedupe(rule.get("triggers", []) or [], limit=8),
        risks=_dedupe(rule.get("risks", []) or [], limit=8),
        watch_points=_dedupe(rule.get("watch_points", []) or [], limit=8),
        edges=_build_edges(theme, rule),
        story=str(rule.get("story", "") or ""),
        money_flow=str(rule.get("money_flow", "") or ""),
        trading_idea=str(rule.get("trading_idea", "") or ""),
    )


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def build_theme_graph(
    news_items: Optional[List[Any]] = None,
    indicators: Optional[List[Dict[str, Any]]] = None,
    extra_text: str = "",
    min_score: float = 18.0,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """
    뉴스/지표/추가 텍스트를 Theme Knowledge Graph 결과로 변환한다.
    """
    text = " ".join([
        _items_to_text(news_items),
        _items_to_text(indicators),
        str(extra_text or ""),
    ])

    nodes: List[ThemeKnowledgeNode] = []

    for theme, rule in THEME_KNOWLEDGE.items():
        score, matched = _score_theme(text, theme, rule)
        if score < float(min_score):
            continue
        nodes.append(_build_node(theme, score, matched, rule))

    nodes.sort(key=lambda n: n.score, reverse=True)
    return [n.to_dict() for n in nodes[: int(limit)]]


def build_knowledge_graph(
    news_items: Optional[List[Any]] = None,
    indicators: Optional[List[Dict[str, Any]]] = None,
    extra_text: str = "",
    min_score: float = 18.0,
    limit: int = 8,
) -> Dict[str, Any]:
    """
    노드와 엣지를 분리한 실제 그래프 구조를 반환한다.
    Dashboard나 Graph UI를 만들 때 사용한다.
    """
    theme_nodes = build_theme_graph(
        news_items=news_items,
        indicators=indicators,
        extra_text=extra_text,
        min_score=min_score,
        limit=limit,
    )

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    for t in theme_nodes:
        theme = t.get("theme", "")
        if theme:
            nodes[theme] = {"id": theme, "type": "theme", "score": t.get("score", 0)}

        for parent in [t.get("parent", ""), t.get("category", "")]:
            if parent and parent not in nodes:
                nodes[parent] = {"id": parent, "type": "category", "score": 0}

        for child in t.get("children", []) or []:
            nodes.setdefault(child, {"id": child, "type": "sub_theme", "score": 0})

        for step in t.get("supply_chain", []) or []:
            nodes.setdefault(step, {"id": step, "type": "supply_chain", "score": 0})

        for company in t.get("companies", []) or []:
            cname = company.get("name", "")
            if cname:
                nodes.setdefault(cname, {"id": cname, "type": "company", "score": company.get("sensitivity", 50)})

        edges.extend(t.get("edges", []) or [])

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "themes": theme_nodes,
    }


def find_themes_for_company(company_name: str, limit: int = 8) -> List[Dict[str, Any]]:
    company_name = _clean(company_name)
    if not company_name:
        return []

    out: List[Dict[str, Any]] = []
    for theme, rule in THEME_KNOWLEDGE.items():
        for c in rule.get("companies", []) or []:
            cname = c.get("name", "") if isinstance(c, dict) else str(c)
            if cname != company_name:
                continue
            out.append({
                "theme": theme,
                "category": rule.get("category", ""),
                "parent": rule.get("parent", ""),
                "role": c.get("role", "") if isinstance(c, dict) else "",
                "sensitivity": c.get("sensitivity", 50) if isinstance(c, dict) else 50,
                "supply_chain": rule.get("supply_chain", []) or [],
                "triggers": rule.get("triggers", []) or [],
                "risks": rule.get("risks", []) or [],
                "story": rule.get("story", ""),
                "money_flow": rule.get("money_flow", ""),
                "trading_idea": rule.get("trading_idea", ""),
            })
            break

    out.sort(key=lambda x: x.get("sensitivity", 0), reverse=True)
    return out[: int(limit)]


def build_company_theme_story(company_name: str) -> str:
    themes = find_themes_for_company(company_name, limit=3)
    if not themes:
        return ""

    parts: List[str] = []
    for t in themes:
        chain = " → ".join(t.get("supply_chain", [])[:5])
        if chain:
            parts.append(f"{t.get('theme')}: {chain}")
        elif t.get("story"):
            parts.append(f"{t.get('theme')}: {t.get('story')}")
    return " / ".join(parts)


def summarize_theme_graph(theme_nodes: List[Dict[str, Any]], limit: int = 3) -> str:
    if not theme_nodes:
        return "뚜렷하게 부각된 테마 그래프가 감지되지 않았습니다."

    parts: List[str] = []
    for node in theme_nodes[: int(limit)]:
        theme = node.get("theme", "")
        parent = node.get("parent", "")
        companies = node.get("companies", []) or []
        company_names = [c.get("name", "") for c in companies if isinstance(c, dict) and c.get("name")]
        supply = " → ".join(node.get("supply_chain", [])[:4])
        head = f"{theme}"
        if parent:
            head += f"({parent} 계열)"
        if supply:
            head += f": {supply}"
        if company_names:
            head += f" → {', '.join(company_names[:3])}"
        parts.append(head)

    return " / ".join(parts)


def theme_graph_to_markdown(theme_nodes: List[Dict[str, Any]], limit: int = 5) -> str:
    if not theme_nodes:
        return "- 감지된 핵심 테마가 없습니다."

    lines: List[str] = []
    for i, node in enumerate(theme_nodes[: int(limit)], start=1):
        lines.append(f"### {i}. {node.get('theme')} / {node.get('score')}점")

        if node.get("parent"):
            lines.append(f"- 상위 테마: {node.get('parent')}")
        if node.get("supply_chain"):
            lines.append(f"- 공급망 흐름: {' → '.join(node.get('supply_chain', [])[:8])}")
        if node.get("industries"):
            lines.append(f"- 연결 산업: {', '.join(node.get('industries', [])[:6])}")

        companies = node.get("companies", []) or []
        if companies:
            company_text = []
            for c in companies[:8]:
                if isinstance(c, dict):
                    name = c.get("name", "")
                    role = c.get("role", "")
                    if role:
                        company_text.append(f"{name}({role})")
                    else:
                        company_text.append(name)
            lines.append(f"- 관련 종목: {', '.join(company_text)}")

        if node.get("matched_keywords"):
            lines.append(f"- 감지 키워드: {', '.join(node.get('matched_keywords', [])[:8])}")
        if node.get("triggers"):
            lines.append(f"- 강세 트리거: {', '.join(node.get('triggers', [])[:5])}")
        if node.get("risks"):
            lines.append(f"- 리스크: {', '.join(node.get('risks', [])[:4])}")
        if node.get("money_flow"):
            lines.append(f"- 자금 흐름: {node.get('money_flow')}")
        if node.get("trading_idea"):
            lines.append(f"- 장전 대응: {node.get('trading_idea')}")
        lines.append("")

    return "\n".join(lines).strip()


def build_money_flow_story(theme_nodes: List[Dict[str, Any]], limit: int = 4) -> str:
    if not theme_nodes:
        return "뚜렷한 테마 자금 흐름은 아직 확인되지 않았습니다."

    flows = []
    for node in theme_nodes[: int(limit)]:
        theme = node.get("theme", "")
        money_flow = node.get("money_flow", "")
        if theme and money_flow:
            flows.append(f"{theme}: {money_flow}")
    return " / ".join(flows) if flows else "테마 간 자금 이동은 장 초반 거래량 확인이 필요합니다."


def build_trading_idea(theme_nodes: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    ideas: List[str] = []
    for node in (theme_nodes or [])[: int(limit)]:
        idea = _clean(node.get("trading_idea", ""))
        if idea and idea not in ideas:
            ideas.append(idea)
    if not ideas:
        ideas.append("시초가 갭과 거래량을 확인한 뒤 주도 테마 여부를 판단합니다.")
    return ideas


def get_theme_rule(theme: str) -> Dict[str, Any]:
    return dict(THEME_KNOWLEDGE.get(str(theme or "").strip(), {}) or {})


# 하위 호환
THEME_GRAPH = THEME_KNOWLEDGE


if __name__ == "__main__":
    sample_news = [
        {"title": "AI 데이터센터 투자 확대와 HBM 수요 증가", "description": "엔비디아 GPU와 HBM4 공급망 관심"},
        {"title": "전력망 투자 확대", "description": "AI 데이터센터 전력 수요 증가"},
    ]
    graph = build_theme_graph(sample_news)
    print(theme_graph_to_markdown(graph))
