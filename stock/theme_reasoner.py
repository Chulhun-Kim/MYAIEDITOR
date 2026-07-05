# stock/theme_reasoner.py
# ------------------------------------------------------------
# MYAIEDITOR v2.0 Theme Intelligence Engine
# ------------------------------------------------------------
# 역할:
# - 장전 뉴스에서 HBM, AI 서버, SMR, 방산 수출, LNG선 등 핵심 테마를 감지한다.
# - 테마 → 섹터 → 관련 종목 → 추천 이유를 구조화한다.
# - sector_reasoner.py보다 한 단계 더 세밀한 '테마 레벨' 맥락을 제공한다.
# - candidate_score.py / ai_reason_builder.py / explain_engine.py에서 재사용할 수 있는
#   안정적인 Public API를 제공한다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ThemeRule:
    code: str
    name: str
    sector: str
    keywords: List[str]
    companies: List[str]
    reasons: List[str]
    watch_points: List[str]
    priority: float = 50.0


@dataclass
class ThemeResult:
    code: str
    theme: str
    sector: str
    score: float
    matched_keywords: List[str]
    companies: List[str]
    reasons: List[str]
    watch_points: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# Theme Rules
# ------------------------------------------------------------
# 테마는 섹터보다 더 좁은 개념이다.
# 예: 반도체·AI 섹터 안에 HBM, AI서버, 반도체후공정 테마가 존재한다.

THEME_RULES: Dict[str, ThemeRule] = {
    # ========================================================
    # 반도체 · AI
    # ========================================================
    "hbm": ThemeRule(
        code="hbm",
        name="HBM",
        sector="반도체·AI",
        keywords=["HBM", "HBM3", "HBM4", "고대역폭메모리", "AI 서버", "엔비디아", "NVIDIA", "GPU", "메모리", "DRAM"],
        companies=["삼성전자", "SK하이닉스", "한미반도체", "ISC", "리노공업", "이오테크닉스"],
        reasons=["HBM 수요 확대", "AI 서버 투자 증가", "메모리 업황 개선 기대"],
        watch_points=["엔비디아·AI 서버 수요", "HBM 공급 확대", "메모리 가격 흐름"],
        priority=96,
    ),
    "ai_server": ThemeRule(
        code="ai_server",
        name="AI 서버",
        sector="반도체·AI",
        keywords=["AI 서버", "데이터센터", "GPU", "엔비디아", "NVIDIA", "마이크로소프트", "클라우드", "AI 인프라"],
        companies=["삼성전자", "SK하이닉스", "한미반도체", "LS ELECTRIC", "대한전선", "LS", "LS에코에너지"],
        reasons=["AI 서버 투자 확대", "데이터센터 인프라 수요 증가", "고성능 메모리·전력 인프라 수혜"],
        watch_points=["미국 빅테크 투자 흐름", "전력 인프라 수요", "AI 반도체 수급"],
        priority=92,
    ),
    "semiconductor_equipment": ThemeRule(
        code="semiconductor_equipment",
        name="반도체 장비·후공정",
        sector="반도체·AI",
        keywords=["반도체 장비", "후공정", "패키징", "TC본더", "테스트소켓", "증착", "식각", "ALD", "공정", "소부장"],
        companies=["한미반도체", "ISC", "리노공업", "주성엔지니어링", "원익IPS", "이오테크닉스", "원익QnC", "솔브레인"],
        reasons=["반도체 후공정 투자 확대", "HBM 장비·테스트 수요 증가", "소부장 공급망 모멘텀"],
        watch_points=["장비 수주", "후공정 투자", "반도체 가동률"],
        priority=88,
    ),

    # ========================================================
    # 방산
    # ========================================================
    "defense_export": ThemeRule(
        code="defense_export",
        name="방산 수출",
        sector="방산",
        keywords=["방산", "수출", "K9", "K2", "천무", "미사일", "유도무기", "폴란드", "루마니아", "중동", "NATO", "계약"],
        companies=["한화에어로스페이스", "LIG넥스원", "현대로템", "한화시스템", "한국항공우주"],
        reasons=["방산 수출 기대", "해외 무기체계 계약 모멘텀", "지정학 리스크에 따른 방산 관심"],
        watch_points=["수출 계약 뉴스", "해외 방산 예산", "지정학 리스크"],
        priority=90,
    ),

    # ========================================================
    # 조선
    # ========================================================
    "lng_ship": ThemeRule(
        code="lng_ship",
        name="LNG선·조선 수주",
        sector="조선",
        keywords=["조선", "LNG", "LNG선", "선박", "친환경선박", "수주", "선가", "수주잔고", "해양플랜트", "탱커"],
        companies=["HD현대중공업", "삼성중공업", "HD한국조선해양", "HD현대미포", "한화오션"],
        reasons=["LNG선·친환경선박 수주 기대", "선가와 수주잔고 개선", "조선 업황 회복 모멘텀"],
        watch_points=["신규 수주", "선가 흐름", "유가와 해양플랜트 투자"],
        priority=87,
    ),

    # ========================================================
    # 원전 · 전력망
    # ========================================================
    "smr_nuclear": ThemeRule(
        code="smr_nuclear",
        name="SMR·원전",
        sector="원전·전력",
        keywords=["원전", "SMR", "원자력", "체코", "폴란드", "원전 수출", "발전", "터빈", "원전 설계"],
        companies=["두산에너빌리티", "한전기술", "한국전력", "하이록코리아"],
        reasons=["원전·SMR 정책 모멘텀", "해외 원전 수주 기대", "발전설비 투자 확대"],
        watch_points=["원전 정책", "해외 수주", "SMR 투자 뉴스"],
        priority=86,
    ),
    "power_grid": ThemeRule(
        code="power_grid",
        name="전력망·전력기기",
        sector="원전·전력",
        keywords=["전력망", "송전망", "변압기", "전선", "해저케이블", "전력기기", "데이터센터", "전력 인프라"],
        companies=["LS ELECTRIC", "LS", "LS에코에너지", "대한전선", "한국전력"],
        reasons=["전력망 투자 확대", "AI 데이터센터 전력 수요 증가", "전력기기·전선 수주 기대"],
        watch_points=["전력망 투자", "데이터센터 수요", "구리 가격"],
        priority=84,
    ),

    # ========================================================
    # 2차전지
    # ========================================================
    "battery_material": ThemeRule(
        code="battery_material",
        name="2차전지 소재",
        sector="2차전지",
        keywords=["2차전지", "배터리", "양극재", "음극재", "리튬", "전고체", "ESS", "전기차", "테슬라"],
        companies=["LG에너지솔루션", "삼성SDI", "에코프로비엠", "에코프로", "포스코퓨처엠", "LG화학", "엘앤에프", "천보"],
        reasons=["전기차·ESS 배터리 수요 회복 기대", "배터리 소재 수급 모멘텀", "리튬·양극재 가격 흐름 연동"],
        watch_points=["전기차 판매", "테슬라 흐름", "배터리 소재 가격"],
        priority=80,
    ),

    # ========================================================
    # 바이오
    # ========================================================
    "bio_license": ThemeRule(
        code="bio_license",
        name="바이오 허가·수출",
        sector="바이오",
        keywords=["바이오", "FDA", "임상", "허가", "바이오시밀러", "CDMO", "기술수출", "의약품", "신약"],
        companies=["셀트리온", "삼성바이오로직스", "알테오젠", "휴젤", "클래시스"],
        reasons=["바이오 의약품 허가·판매 기대", "CDMO·기술수출 모멘텀", "임상·허가 이벤트 기대"],
        watch_points=["FDA 허가", "기술수출", "수주 공시"],
        priority=82,
    ),

    # ========================================================
    # 자동차 · 금융 · 로봇 · 화장품 · 엔터
    # ========================================================
    "auto_export": ThemeRule(
        code="auto_export",
        name="자동차 수출",
        sector="자동차",
        keywords=["자동차", "현대차", "기아", "전기차", "하이브리드", "수출", "환율", "미국 판매"],
        companies=["현대차", "기아", "현대모비스", "HL만도"],
        reasons=["자동차 수출·환율 수혜 기대", "하이브리드·전기차 판매 흐름", "글로벌 판매 회복 모멘텀"],
        watch_points=["환율", "미국 판매", "전기차 수요"],
        priority=78,
    ),
    "shareholder_return": ThemeRule(
        code="shareholder_return",
        name="금융·주주환원",
        sector="금융",
        keywords=["금융", "은행", "금리", "배당", "자사주", "주주환원", "순이자마진", "NIM"],
        companies=["KB금융", "신한지주", "하나금융지주", "우리금융지주"],
        reasons=["은행·배당주 관심", "주주환원 정책 기대", "금리 흐름에 따른 금융주 모멘텀"],
        watch_points=["금리", "외국인 수급", "배당·자사주 정책"],
        priority=76,
    ),
    "robotics": ThemeRule(
        code="robotics",
        name="로봇·자동화",
        sector="로봇",
        keywords=["로봇", "휴머노이드", "협동로봇", "자동화", "스마트팩토리"],
        companies=["두산로보틱스", "레인보우로보틱스", "로보스타"],
        reasons=["로봇·자동화 투자 기대", "휴머노이드 테마 모멘텀", "스마트팩토리 수요 연동"],
        watch_points=["로봇 테마 수급", "대기업 투자", "수주 뉴스"],
        priority=74,
    ),
    "k_beauty": ThemeRule(
        code="k_beauty",
        name="K뷰티",
        sector="화장품",
        keywords=["화장품", "K뷰티", "면세", "중국", "미용기기", "ODM", "뷰티디바이스", "수출"],
        companies=["아모레퍼시픽", "한국콜마", "에이피알"],
        reasons=["K뷰티 수출 모멘텀", "화장품 ODM 수요 기대", "미용기기 해외 판매 기대"],
        watch_points=["중국·면세 수요", "수출 데이터", "ODM 수주"],
        priority=72,
    ),
    "k_content": ThemeRule(
        code="k_content",
        name="K콘텐츠·엔터",
        sector="엔터",
        keywords=["엔터", "K팝", "공연", "팬덤", "아티스트", "컴백", "월드투어", "콘텐츠"],
        companies=["하이브", "와이지엔터테인먼트", "에스엠", "JYP Ent.", "넷마블", "크래프톤"],
        reasons=["K팝·공연 일정 모멘텀", "글로벌 팬덤 수요 기대", "콘텐츠 업종 관심"],
        watch_points=["컴백·공연 일정", "게임·콘텐츠 신작", "해외 매출"],
        priority=70,
    ),
}


# ------------------------------------------------------------
# Utility
# ------------------------------------------------------------

def _clean(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


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


def news_item_text(item: Any) -> str:
    d = _item_to_dict(item)
    if d:
        return " ".join(str(d.get(k, "") or "") for k in ["title", "description", "content", "summary", "source", "published"])
    return " ".join(str(getattr(item, k, "") or "") for k in ["title", "description", "content", "summary", "source", "published"])


def build_news_text(news_items: Optional[List[Any]] = None) -> str:
    return " ".join(news_item_text(x) for x in (news_items or []))


def count_keywords(text: str, keywords: Iterable[str]) -> int:
    low = str(text or "").lower()
    return sum(low.count(str(k).lower()) for k in keywords if str(k).strip())


def matched_keywords(text: str, keywords: Iterable[str], max_items: int = 8) -> List[str]:
    low = str(text or "").lower()
    out: List[str] = []
    for kw in keywords:
        clean = str(kw or "").strip()
        if clean and clean.lower() in low and clean not in out:
            out.append(clean)
        if len(out) >= max_items:
            break
    return out


def _score_theme(rule: ThemeRule, text: str, candidate_name: str = "") -> float:
    hit_count = count_keywords(text, rule.keywords)
    if hit_count <= 0:
        return 0.0

    score = min(hit_count * 8.0, 48.0) + rule.priority * 0.45

    if candidate_name and candidate_name in rule.companies:
        score += 18

    # 핵심 키워드 보정
    key_hits = matched_keywords(text, rule.keywords, max_items=10)
    if len(key_hits) >= 3:
        score += 8
    elif len(key_hits) >= 2:
        score += 5

    return round(max(0.0, min(score, 100.0)), 1)


def _top_reasons(rule: ThemeRule, max_items: int = 3) -> List[str]:
    return list(rule.reasons or [])[:max_items]


def _top_watch_points(rule: ThemeRule, max_items: int = 3) -> List[str]:
    return list(rule.watch_points or [])[:max_items]


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def analyze_themes(
    news_items: Optional[List[Any]] = None,
    candidate_name: str = "",
    candidate_sector: str = "",
    max_results: int = 5,
) -> List[ThemeResult]:
    """
    뉴스 전체에서 핵심 테마를 분석한다.

    Parameters
    ----------
    news_items:
        NewsItem dataclass 또는 dict 목록.

    candidate_name:
        특정 종목 기준 분석이 필요할 때 사용한다.
        해당 종목이 테마 관련 기업 목록에 있으면 점수 보정을 한다.

    candidate_sector:
        특정 종목의 섹터. 지정하면 해당 섹터 테마를 우선한다.

    max_results:
        반환할 테마 최대 개수.
    """
    text = build_news_text(news_items)
    if not text.strip():
        return []

    candidate_name = str(candidate_name or "").strip()
    candidate_sector = str(candidate_sector or "").strip()

    results: List[ThemeResult] = []

    for rule in THEME_RULES.values():
        score = _score_theme(rule, text, candidate_name=candidate_name)
        if score <= 0:
            continue

        if candidate_sector and candidate_sector in rule.sector:
            score = min(score + 8, 100)
        elif candidate_sector and rule.sector in candidate_sector:
            score = min(score + 8, 100)

        keywords = matched_keywords(text, rule.keywords, max_items=8)
        if not keywords:
            continue

        results.append(
            ThemeResult(
                code=rule.code,
                theme=rule.name,
                sector=rule.sector,
                score=score,
                matched_keywords=keywords,
                companies=list(rule.companies),
                reasons=_top_reasons(rule),
                watch_points=_top_watch_points(rule),
            )
        )

    results.sort(key=lambda x: x.score, reverse=True)
    return results[: int(max_results)]


def analyze_candidate_themes(
    name: str,
    ticker: str = "",
    sector: str = "",
    news_items: Optional[List[Any]] = None,
    max_results: int = 3,
) -> List[ThemeResult]:
    """
    특정 종목 기준으로 관련 테마를 분석한다.
    """
    return analyze_themes(
        news_items=news_items,
        candidate_name=name,
        candidate_sector=sector,
        max_results=max_results,
    )


def get_theme_reason_for_company(
    name: str,
    sector: str = "",
    news_items: Optional[List[Any]] = None,
) -> str:
    """
    특정 종목에 대해 표/Dashboard에 넣을 짧은 테마 근거를 반환한다.
    """
    results = analyze_candidate_themes(
        name=name,
        sector=sector,
        news_items=news_items,
        max_results=1,
    )
    if not results:
        return ""

    top = results[0]
    if top.reasons:
        return top.reasons[0]
    return f"{top.theme} 테마 모멘텀"


def build_theme_signals_for_company(
    name: str,
    ticker: str = "",
    sector: str = "",
    news_items: Optional[List[Any]] = None,
    max_results: int = 3,
) -> Dict[str, Any]:
    """
    candidate_score.py에서 signals에 병합하기 좋은 dict 형태로 반환한다.
    """
    results = analyze_candidate_themes(
        name=name,
        ticker=ticker,
        sector=sector,
        news_items=news_items,
        max_results=max_results,
    )

    return {
        "theme_results": [r.to_dict() for r in results],
        "theme_codes": [r.code for r in results],
        "theme_names": [r.theme for r in results],
        "theme_reasons": [reason for r in results for reason in r.reasons[:2]],
        "theme_watch_points": [wp for r in results for wp in r.watch_points[:2]],
        "top_theme": results[0].theme if results else "",
        "top_theme_score": results[0].score if results else 0.0,
    }


def build_theme_reasons_for_company(
    name: str,
    ticker: str = "",
    sector: str = "",
    news_items: Optional[List[Any]] = None,
    max_items: int = 3,
) -> List[str]:
    """
    추천 근거 리스트에 바로 붙일 수 있는 테마 이유 목록을 만든다.
    """
    signals = build_theme_signals_for_company(
        name=name,
        ticker=ticker,
        sector=sector,
        news_items=news_items,
        max_results=max_items,
    )

    out: List[str] = []
    for reason in signals.get("theme_reasons", []) or []:
        text = _clean(reason)
        if text and text not in out:
            out.append(text)
        if len(out) >= max_items:
            break

    if not out and signals.get("top_theme"):
        out.append(f"{signals.get('top_theme')} 테마 모멘텀")

    return out[:max_items]


def summarize_theme_results(results: List[ThemeResult], max_items: int = 3) -> str:
    """
    Workspace/브리핑용 짧은 테마 요약문을 만든다.
    """
    selected = list(results or [])[:max_items]
    if not selected:
        return "뚜렷하게 감지된 핵심 테마는 없습니다."

    parts: List[str] = []
    for r in selected:
        kws = ", ".join(r.matched_keywords[:3]) if r.matched_keywords else "관련 키워드"
        parts.append(f"{r.theme}({kws})")

    return " · ".join(parts)


if __name__ == "__main__":
    sample_news = [
        {"title": "엔비디아 강세에 HBM 수요 확대 기대", "description": "AI 서버 투자 증가와 고대역폭메모리 수요 확대"},
        {"title": "데이터센터 전력망 투자 확대", "description": "전력기기와 변압기 수요 증가"},
    ]
    for item in analyze_themes(sample_news):
        print(item.to_dict())
