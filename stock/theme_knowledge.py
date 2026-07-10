"""
theme_knowledge.py
---------------------------------------------------------
v2.4-1

시장 테마 지식 저장소

역할
- 뉴스·테마·자금흐름·섹터·종목을 연결하는 기본 지식 그래프 제공
- reasoning_engine.py, money_flow_engine.py, market_story_engine.py에서 공통 사용 가능
- 입력 키워드가 조금 달라도 canonical theme으로 매핑

Author : MYAIEDITOR
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set


# --------------------------------------------------------
# Core Knowledge Base
# --------------------------------------------------------

THEME_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "반도체AI": {
        "label": "반도체·AI",
        "sector": "반도체",
        "parents": ["AI", "클라우드", "데이터센터", "미국 기술주"],
        "children": ["HBM", "GPU", "DDR5", "CXL", "파운드리", "패키징", "검사장비"],
        "keywords": [
            "AI", "인공지능", "생성형AI", "데이터센터", "클라우드", "GPU", "HBM",
            "DDR5", "CXL", "반도체", "메모리", "파운드리", "패키징", "엔비디아",
            "마이크로소프트", "오픈AI", "브로드컴", "TSMC", "삼성전자", "SK하이닉스",
        ],
        "global_leaders": ["Microsoft", "NVIDIA", "AMD", "Broadcom", "TSMC", "Amazon", "Google"],
        "stocks": ["삼성전자", "SK하이닉스", "한미반도체", "ISC", "리노공업", "원익IPS", "HPSP", "이오테크닉스"],
        "chain": ["AI 투자 확대", "데이터센터 CAPEX", "GPU·가속기 수요", "HBM 수요", "반도체AI", "삼성전자·SK하이닉스"],
        "positive_triggers": ["AI 투자 확대", "클라우드 CAPEX 증가", "HBM 가격 상승", "엔비디아 강세", "미국 기술주 강세"],
        "negative_triggers": ["엔비디아 급락", "미국 기술주 약세", "메모리 가격 하락", "수출 규제", "CAPEX 축소"],
        "confidence": 0.95,
    },
    "AI": {
        "label": "AI",
        "sector": "AI·소프트웨어",
        "parents": ["클라우드", "빅테크", "데이터센터"],
        "children": ["LLM", "AI 에이전트", "MCP", "데이터센터", "GPU", "HBM", "로봇"],
        "keywords": ["AI", "인공지능", "생성형AI", "LLM", "AI 에이전트", "MCP", "챗봇", "클라우드", "데이터센터"],
        "global_leaders": ["Microsoft", "OpenAI", "Google", "Amazon", "Meta", "Anthropic", "NVIDIA"],
        "stocks": ["NAVER", "카카오", "솔트룩스", "마음AI", "폴라리스AI", "삼성전자", "SK하이닉스"],
        "chain": ["AI 서비스 확산", "클라우드 사용량 증가", "데이터센터 투자", "GPU·HBM 수요", "AI 인프라"],
        "positive_triggers": ["AI 서비스 출시", "빅테크 투자 확대", "정부 AI 정책", "클라우드 수요 증가"],
        "negative_triggers": ["AI 규제", "빅테크 투자 축소", "AI 수익성 논란"],
        "confidence": 0.92,
    },
    "데이터센터": {
        "label": "데이터센터",
        "sector": "AI 인프라",
        "parents": ["AI", "클라우드", "전력"],
        "children": ["전력", "냉각", "HBM", "GPU", "서버", "통신장비"],
        "keywords": ["데이터센터", "IDC", "클라우드", "서버", "전력", "냉각", "CAPEX", "AI 인프라"],
        "global_leaders": ["Microsoft", "Amazon", "Google", "Meta", "NVIDIA"],
        "stocks": ["삼성전자", "SK하이닉스", "LS ELECTRIC", "HD현대일렉트릭", "효성중공업", "대한전선", "가온전선"],
        "chain": ["AI 서비스 확산", "데이터센터 증설", "전력·서버 수요", "HBM·전력기기", "관련주 관심"],
        "positive_triggers": ["빅테크 CAPEX 증가", "AI 데이터센터 투자", "전력설비 수요 증가"],
        "negative_triggers": ["전력망 병목", "투자 지연", "빅테크 CAPEX 축소"],
        "confidence": 0.90,
    },
    "자동차": {
        "label": "자동차",
        "sector": "자동차",
        "parents": ["수출", "환율", "미국 판매", "전기차"],
        "children": ["완성차", "부품", "전기차", "하이브리드", "자율주행"],
        "keywords": ["자동차", "현대차", "기아", "수출", "환율", "전기차", "하이브리드", "미국 판매", "관세"],
        "global_leaders": ["Tesla", "Toyota", "GM", "Ford", "BYD", "Hyundai", "Kia"],
        "stocks": ["현대차", "기아", "현대모비스", "HL만도", "성우하이텍", "화신"],
        "chain": ["환율·수출 환경", "완성차 실적", "부품주 수급", "자동차 섹터"],
        "positive_triggers": ["환율 상승", "미국 판매 호조", "수출 증가", "관세 완화", "전기차 보조금"],
        "negative_triggers": ["관세 부담", "미국 판매 둔화", "전기차 수요 둔화", "원화 강세"],
        "confidence": 0.88,
    },
    "원전": {
        "label": "원전",
        "sector": "원전·전력",
        "parents": ["전력", "에너지 안보", "SMR", "정부 정책"],
        "children": ["SMR", "원전 기자재", "전력기기", "송배전", "원전 수출"],
        "keywords": ["원전", "SMR", "체코 원전", "원전 수출", "한수원", "전력", "송배전", "두산에너빌리티"],
        "global_leaders": ["Westinghouse", "EDF", "GE Hitachi", "KHNP"],
        "stocks": ["두산에너빌리티", "한전기술", "한전KPS", "우리기술", "비에이치아이", "LS ELECTRIC"],
        "chain": ["전력 수요 증가", "원전 정책 기대", "SMR·원전 수출", "기자재 수요", "원전주"],
        "positive_triggers": ["원전 수출", "SMR 정책", "전력 수요 증가", "정부 원전 확대"],
        "negative_triggers": ["정책 지연", "수주 불확실성", "안전 규제", "원전 반대 여론"],
        "confidence": 0.86,
    },
    "방산": {
        "label": "방산",
        "sector": "방위산업",
        "parents": ["지정학", "국방예산", "NATO", "중동", "우크라이나"],
        "children": ["미사일", "항공우주", "장갑차", "방공", "탄약"],
        "keywords": ["방산", "국방", "NATO", "중동", "우크라이나", "수출", "미사일", "장갑차", "K방산"],
        "global_leaders": ["Lockheed Martin", "RTX", "Northrop Grumman", "BAE Systems"],
        "stocks": ["한화에어로스페이스", "LIG넥스원", "현대로템", "한국항공우주", "풍산"],
        "chain": ["지정학 리스크", "국방예산 확대", "무기 수출", "방산주 수급"],
        "positive_triggers": ["수출 계약", "국방예산 증가", "지정학 리스크", "NATO 재무장"],
        "negative_triggers": ["수주 지연", "분쟁 완화", "정부 예산 축소"],
        "confidence": 0.88,
    },
    "조선": {
        "label": "조선",
        "sector": "조선",
        "parents": ["LNG", "해운", "친환경 선박", "방산"],
        "children": ["LNG선", "컨테이너선", "특수선", "엔진", "기자재"],
        "keywords": ["조선", "LNG", "LNG선", "선박", "해운", "친환경선박", "수주", "선가"],
        "global_leaders": ["HD Hyundai", "Hanwha Ocean", "Samsung Heavy Industries"],
        "stocks": ["HD현대중공업", "한화오션", "삼성중공업", "HD한국조선해양", "HSD엔진"],
        "chain": ["선가 상승", "수주 증가", "실적 개선", "조선주"],
        "positive_triggers": ["LNG선 수주", "선가 상승", "해운 운임 상승", "친환경 선박 발주"],
        "negative_triggers": ["수주 공백", "원가 상승", "환율 하락", "해운 경기 둔화"],
        "confidence": 0.87,
    },
    "2차전지": {
        "label": "2차전지",
        "sector": "2차전지",
        "parents": ["전기차", "리튬", "미국 IRA", "테슬라"],
        "children": ["셀", "양극재", "음극재", "전해액", "분리막", "리튬"],
        "keywords": ["2차전지", "배터리", "전기차", "양극재", "음극재", "리튬", "테슬라", "IRA", "ESS"],
        "global_leaders": ["Tesla", "CATL", "BYD", "LG Energy Solution", "Panasonic"],
        "stocks": ["LG에너지솔루션", "삼성SDI", "에코프로", "에코프로비엠", "포스코퓨처엠", "엘앤에프", "LG화학"],
        "chain": ["전기차 수요", "배터리 출하", "소재 가격", "2차전지주"],
        "positive_triggers": ["테슬라 강세", "전기차 판매 증가", "리튬 가격 안정", "ESS 수요 증가"],
        "negative_triggers": ["테슬라 급락", "전기차 수요 둔화", "리튬 가격 급변", "보조금 축소"],
        "confidence": 0.86,
    },
    "금융": {
        "label": "금융",
        "sector": "금융",
        "parents": ["금리", "환율", "주주환원", "배당"],
        "children": ["은행", "보험", "증권", "카드"],
        "keywords": ["금융", "은행", "보험", "증권", "금리", "배당", "주주환원", "자사주", "밸류업"],
        "global_leaders": ["JPMorgan", "Bank of America", "Goldman Sachs"],
        "stocks": ["KB금융", "신한지주", "하나금융지주", "우리금융지주", "메리츠금융지주", "삼성생명"],
        "chain": ["금리 환경", "순이자마진", "배당·자사주", "금융주"],
        "positive_triggers": ["금리 상승", "주주환원 확대", "배당 기대", "밸류업 정책"],
        "negative_triggers": ["금리 하락", "연체율 상승", "규제 강화", "부동산 PF 리스크"],
        "confidence": 0.84,
    },
    "바이오": {
        "label": "바이오",
        "sector": "바이오",
        "parents": ["FDA", "임상", "신약", "CDMO"],
        "children": ["신약", "임상", "항암제", "비만치료제", "CDMO", "바이오시밀러"],
        "keywords": ["바이오", "신약", "임상", "FDA", "CDMO", "바이오시밀러", "항암제", "비만치료제"],
        "global_leaders": ["Eli Lilly", "Novo Nordisk", "Pfizer", "Merck", "Roche"],
        "stocks": ["삼성바이오로직스", "셀트리온", "SK바이오팜", "유한양행", "알테오젠", "리가켐바이오"],
        "chain": ["임상·허가 이벤트", "기술수출 기대", "실적·파이프라인", "바이오주"],
        "positive_triggers": ["FDA 승인", "임상 성공", "기술수출", "CDMO 수주", "바이오시밀러 판매 확대"],
        "negative_triggers": ["임상 실패", "허가 지연", "기술수출 불확실성", "약가 규제"],
        "confidence": 0.82,
    },
    "로봇": {
        "label": "로봇",
        "sector": "로봇",
        "parents": ["AI", "자동화", "공장", "휴머노이드"],
        "children": ["산업용 로봇", "협동로봇", "휴머노이드", "감속기", "센서"],
        "keywords": ["로봇", "휴머노이드", "협동로봇", "자동화", "스마트팩토리", "감속기", "AI 로봇"],
        "global_leaders": ["Tesla", "Boston Dynamics", "Fanuc", "ABB", "NVIDIA"],
        "stocks": ["레인보우로보틱스", "두산로보틱스", "로보티즈", "에스피지", "뉴로메카", "유진로봇"],
        "chain": ["AI 고도화", "공장 자동화", "휴머노이드 기대", "로봇주"],
        "positive_triggers": ["휴머노이드 공개", "대기업 투자", "스마트팩토리 확대", "AI 로봇 정책"],
        "negative_triggers": ["상용화 지연", "실적 부진", "밸류에이션 부담"],
        "confidence": 0.80,
    },
    "전력기기": {
        "label": "전력기기",
        "sector": "전력기기",
        "parents": ["데이터센터", "전력망", "AI", "원전", "신재생"],
        "children": ["변압기", "전선", "송배전", "전력망", "ESS"],
        "keywords": ["전력기기", "변압기", "전선", "송배전", "전력망", "전력 수요", "데이터센터", "ESS"],
        "global_leaders": ["GE Vernova", "Siemens Energy", "Hitachi Energy", "Eaton"],
        "stocks": ["HD현대일렉트릭", "LS ELECTRIC", "효성중공업", "대한전선", "가온전선", "일진전기"],
        "chain": ["AI 데이터센터", "전력 수요 증가", "송배전 투자", "전력기기주"],
        "positive_triggers": ["전력망 투자", "변압기 수출", "데이터센터 증설", "전선 수요 증가"],
        "negative_triggers": ["수주 둔화", "원자재 가격 상승", "전력망 투자 지연"],
        "confidence": 0.88,
    },
    "정유": {
        "label": "정유",
        "sector": "에너지",
        "parents": ["유가", "정제마진", "중동 리스크"],
        "children": ["정제마진", "석유화학", "항공유", "윤활유"],
        "keywords": ["정유", "유가", "WTI", "브렌트", "정제마진", "중동", "석유", "에너지"],
        "global_leaders": ["ExxonMobil", "Chevron", "Shell", "Saudi Aramco"],
        "stocks": ["S-Oil", "SK이노베이션", "GS", "HD현대", "한국석유"],
        "chain": ["유가 변화", "정제마진", "에너지 수급", "정유주"],
        "positive_triggers": ["유가 상승", "정제마진 개선", "중동 리스크", "수요 회복"],
        "negative_triggers": ["유가 급락", "정제마진 악화", "수요 둔화"],
        "confidence": 0.82,
    },
}


# --------------------------------------------------------
# Alias map
# --------------------------------------------------------

THEME_ALIASES: Dict[str, str] = {
    "반도체": "반도체AI",
    "반도체 ai": "반도체AI",
    "ai반도체": "반도체AI",
    "hbm": "반도체AI",
    "gpu": "반도체AI",
    "메모리": "반도체AI",
    "삼성전자": "반도체AI",
    "sk하이닉스": "반도체AI",
    "엔비디아": "반도체AI",
    "nvidia": "반도체AI",
    "ms": "AI",
    "microsoft": "AI",
    "마이크로소프트": "AI",
    "openai": "AI",
    "오픈ai": "AI",
    "오픈AI": "AI",
    "클라우드": "데이터센터",
    "idc": "데이터센터",
    "전력": "전력기기",
    "전선": "전력기기",
    "변압기": "전력기기",
    "송배전": "전력기기",
    "현대차": "자동차",
    "기아": "자동차",
    "테슬라": "2차전지",
    "tesla": "2차전지",
    "전기차": "2차전지",
    "배터리": "2차전지",
    "리튬": "2차전지",
    "smr": "원전",
    "원자력": "원전",
    "두산에너빌리티": "원전",
    "k방산": "방산",
    "국방": "방산",
    "우주항공": "방산",
    "lng": "조선",
    "선박": "조선",
    "해운": "조선",
    "은행": "금융",
    "보험": "금융",
    "증권": "금융",
    "밸류업": "금융",
    "신약": "바이오",
    "임상": "바이오",
    "fda": "바이오",
    "cdmo": "바이오",
    "휴머노이드": "로봇",
    "자동화": "로봇",
    "wtI": "정유",
    "wti": "정유",
    "유가": "정유",
    "정제마진": "정유",
}


# --------------------------------------------------------
# Public API
# --------------------------------------------------------

def normalize_theme_name(value: Any) -> str:
    """입력 문자열을 canonical theme 이름으로 변환한다."""
    text = _clean_text(value)
    if not text:
        return ""

    if text in THEME_KNOWLEDGE:
        return text

    key = text.lower().replace("·", " ").replace("/", " ").strip()
    if key in THEME_ALIASES:
        return THEME_ALIASES[key]

    compact = key.replace(" ", "")
    if compact in THEME_ALIASES:
        return THEME_ALIASES[compact]

    for theme_name, info in THEME_KNOWLEDGE.items():
        candidates = [theme_name, info.get("label", "")]
        candidates.extend(info.get("keywords", []))
        candidates.extend(info.get("stocks", []))
        candidates.extend(info.get("global_leaders", []))
        for candidate in candidates:
            c = _clean_text(candidate)
            if not c:
                continue
            c_key = c.lower().replace(" ", "")
            if c_key and c_key in compact:
                return theme_name
            if compact and compact in c_key:
                return theme_name

    return text


def get_theme(theme_name: Any) -> Dict[str, Any]:
    """단일 테마 지식 객체를 반환한다. 없으면 빈 dict."""
    canonical = normalize_theme_name(theme_name)
    info = THEME_KNOWLEDGE.get(canonical)
    if not info:
        return {}
    result = dict(info)
    result["theme"] = canonical
    return result


def has_theme(theme_name: Any) -> bool:
    return bool(get_theme(theme_name))


def list_themes() -> List[str]:
    return list(THEME_KNOWLEDGE.keys())


def get_related_stocks(theme_name: Any, limit: int = 10) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("stocks", []))[:limit]


def get_children(theme_name: Any, limit: int = 10) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("children", []))[:limit]


def get_parents(theme_name: Any, limit: int = 10) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("parents", []))[:limit]


def get_keywords(theme_name: Any, limit: int = 30) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("keywords", []))[:limit]


def get_chain(theme_name: Any, limit: int = 8) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("chain", []))[:limit]


def get_positive_triggers(theme_name: Any, limit: int = 8) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("positive_triggers", []))[:limit]


def get_negative_triggers(theme_name: Any, limit: int = 8) -> List[str]:
    info = get_theme(theme_name)
    return _unique_texts(info.get("negative_triggers", []))[:limit]


def get_theme_confidence(theme_name: Any, default: float = 0.50) -> float:
    info = get_theme(theme_name)
    try:
        return float(info.get("confidence", default))
    except Exception:
        return default


def expand_keywords(theme_name: Any, limit: int = 50) -> List[str]:
    """테마 검색·매칭에 사용할 확장 키워드를 반환한다."""
    info = get_theme(theme_name)
    if not info:
        return []

    values: List[str] = []
    values.append(info.get("theme", ""))
    values.append(info.get("label", ""))
    values.append(info.get("sector", ""))
    values.extend(info.get("parents", []))
    values.extend(info.get("children", []))
    values.extend(info.get("keywords", []))
    values.extend(info.get("global_leaders", []))
    values.extend(info.get("stocks", []))
    return _unique_texts(values)[:limit]


def match_themes_from_text(text: Any, limit: int = 5) -> List[Dict[str, Any]]:
    """문장 또는 기사 제목에서 관련 테마를 점수화해 반환한다."""
    source = _clean_text(text)
    if not source:
        return []

    source_key = source.lower().replace(" ", "")
    matches: List[Dict[str, Any]] = []

    for theme_name, info in THEME_KNOWLEDGE.items():
        score = 0.0
        hits: List[str] = []

        candidates = expand_keywords(theme_name, limit=80)
        for keyword in candidates:
            key = keyword.lower().replace(" ", "")
            if not key:
                continue
            if key in source_key:
                weight = 4.0
                if keyword in info.get("stocks", []):
                    weight = 5.0
                elif keyword in info.get("global_leaders", []):
                    weight = 4.5
                elif keyword in info.get("children", []):
                    weight = 3.5
                score += weight
                hits.append(keyword)

        if score > 0:
            matches.append({
                "theme": theme_name,
                "label": info.get("label", theme_name),
                "sector": info.get("sector", ""),
                "score": round(score, 2),
                "confidence": get_theme_confidence(theme_name),
                "hits": _unique_texts(hits)[:8],
                "stocks": get_related_stocks(theme_name, limit=5),
                "chain": get_chain(theme_name, limit=6),
            })

    matches.sort(key=lambda x: (x.get("score", 0), x.get("confidence", 0)), reverse=True)
    return matches[:limit]


def enrich_theme_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """theme_graph node에 Knowledge Base 정보를 덧붙인다."""
    if not isinstance(node, dict):
        return {}

    theme = (
        node.get("theme")
        or node.get("name")
        or node.get("label")
        or node.get("keyword")
        or ""
    )
    info = get_theme(theme)

    enriched = dict(node)
    if not info:
        enriched.setdefault("knowledge_found", False)
        return enriched

    enriched.update({
        "knowledge_found": True,
        "canonical_theme": info.get("theme"),
        "knowledge_label": info.get("label"),
        "knowledge_sector": info.get("sector"),
        "knowledge_chain": get_chain(info.get("theme"), limit=8),
        "knowledge_stocks": get_related_stocks(info.get("theme"), limit=8),
        "knowledge_keywords": get_keywords(info.get("theme"), limit=20),
        "knowledge_confidence": get_theme_confidence(info.get("theme")),
    })
    return enriched


def enrich_theme_graph(theme_graph: Sequence[Dict[str, Any]], limit: int = 8) -> List[Dict[str, Any]]:
    return [enrich_theme_node(_as_dict(node)) for node in list(theme_graph or [])[:limit]]


def build_knowledge_chain_text(theme_name: Any, arrow: str = " → ") -> str:
    chain = get_chain(theme_name)
    return arrow.join(chain)


def suggest_theme_from_stock(stock_name: Any) -> str:
    text = _clean_text(stock_name)
    if not text:
        return ""
    for theme_name, info in THEME_KNOWLEDGE.items():
        if text in info.get("stocks", []):
            return theme_name
    return normalize_theme_name(text) if has_theme(text) else ""


# --------------------------------------------------------
# Utilities
# --------------------------------------------------------

def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    while "  " in text:
        text = text.replace("  ", " ")
    return text


def _unique_texts(items: Sequence[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for item in items or []:
        text = _clean_text(item)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


# --------------------------------------------------------
# Backward-compatible aliases
# --------------------------------------------------------

def get_theme_knowledge(theme_name: Any) -> Dict[str, Any]:
    return get_theme(theme_name)


def find_themes(text: Any, limit: int = 5) -> List[Dict[str, Any]]:
    return match_themes_from_text(text, limit=limit)
