# stock/importance_engine.py
# ------------------------------------------------------------
# MYAIEDITOR v2.1 Importance Engine
# ------------------------------------------------------------
# 역할:
# - 추천 근거, 리스크, 체크포인트의 중요도를 계산한다.
# - Narrative Builder가 가장 중요한 이유부터 문장을 만들 수 있도록
#   정렬된 ReasonItem 목록을 제공한다.
# - 점수 계산 자체는 하지 않고, 설명 우선순위만 판단한다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class ImportanceReason:
    text: str
    score: float
    category: str = "etc"
    polarity: str = "neutral"  # positive / negative / neutral / watch

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# 유틸
# ------------------------------------------------------------

def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    low = str(text or "").lower()
    return any(str(k).lower() in low for k in keywords)


def _dedupe(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items or []:
        text = _clean(item)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


# ------------------------------------------------------------
# 분류 규칙
# ------------------------------------------------------------

POSITIVE_WORDS = [
    "상승", "강세", "긍정", "수주", "계약", "모멘텀", "확대", "개선", "우수", "풍부", "유동성",
]
NEGATIVE_WORDS = [
    "약세", "하락", "급락", "위험", "주의", "과열", "부담", "조정", "변동성", "추격",
]
WATCH_WORDS = [
    "확인", "점검", "관찰", "유지", "시초가", "거래량", "수급", "갭", "대응", "체크",
]

CATEGORY_RULES: List[Tuple[str, List[str], float]] = [
    ("after_hours", ["시간외"], 96),
    ("disclosure", ["DART", "공시", "수주", "공급계약", "계약"], 92),
    ("company", ["HBM", "메모리", "파운드리", "AI 서버", "TC본더", "테스트소켓", "후공정", "K2", "천궁", "유도무기", "LNG선", "바이오시밀러", "CDMO"], 88),
    ("sector", ["섹터"], 82),
    ("theme", ["AI", "원전", "SMR", "조선", "방산", "2차전지", "바이오", "데이터센터", "전력망"], 78),
    ("news", ["뉴스", "직접 언급", "종목명"], 74),
    ("liquidity", ["거래량", "거래대금", "유동성"], 72),
    ("price", ["전일", "직전", "%", "등락"], 68),
    ("macro", ["환율", "달러", "유가", "금리", "외국인", "수출"], 62),
    ("watch", ["확인", "점검", "시초가", "거래량", "수급"], 58),
]


def classify_reason(text: str) -> str:
    text = _clean(text)
    for category, keywords, _ in CATEGORY_RULES:
        if _contains_any(text, keywords):
            return category
    return "etc"


def classify_polarity(text: str) -> str:
    text = _clean(text)
    if _contains_any(text, NEGATIVE_WORDS):
        return "negative"
    if _contains_any(text, WATCH_WORDS):
        return "watch"
    if _contains_any(text, POSITIVE_WORDS):
        return "positive"
    return "neutral"


def _base_score(category: str) -> float:
    for c, _, score in CATEGORY_RULES:
        if c == category:
            return float(score)
    return 50.0


def _similar_key(text: str) -> str:
    t = _clean(text)
    groups: List[Tuple[str, List[str]]] = [
        ("after_hours", ["시간외"]),
        ("hbm_memory", ["HBM", "메모리", "AI 서버", "고대역폭", "DRAM"]),
        ("semiconductor", ["반도체", "파운드리", "후공정", "테스트소켓", "TC본더"]),
        ("sector", ["섹터"]),
        ("disclosure", ["DART", "공시", "계약", "수주"]),
        ("liquidity", ["거래량", "거래대금", "유동성"]),
        ("price", ["전일", "직전"]),
        ("macro", ["환율", "유가", "금리", "외국인", "수출"]),
        ("risk", ["위험", "주의", "과열", "변동성", "약세", "하락"]),
        ("watch", ["확인", "점검", "시초가", "수급"]),
        ("news", ["뉴스", "직접 언급"]),
    ]
    for key, keywords in groups:
        if any(k in t for k in keywords):
            return key
    return t[:18]


# ------------------------------------------------------------
# 중요도 계산
# ------------------------------------------------------------

def score_reason(
    text: str,
    signals: Optional[Dict[str, Any]] = None,
    candidate: Optional[Any] = None,
) -> ImportanceReason:
    """단일 근거의 중요도를 계산한다."""
    text = _clean(text)
    signals = signals or {}

    category = classify_reason(text)
    polarity = classify_polarity(text)
    score = _base_score(category)

    # 문장 자체의 강도 보정
    if _contains_any(text, ["+", "상승", "강세", "수주", "계약", "확대", "개선"]):
        score += 4
    if _contains_any(text, ["급등", "급락", "매우", "대형주", "풍부"]):
        score += 3
    if _contains_any(text, ["직접", "종목명", "오늘 뉴스"]):
        score += 5
    if _contains_any(text, ["약세", "하락", "과열", "주의", "위험"]):
        score -= 2

    # signals 기반 보정
    after_change = _safe_float(signals.get("after_hours_best_change", 0))
    risk_score = _safe_float(signals.get("risk_score", 0))
    sector_score = _safe_float(signals.get("sector_score", 0))
    trading_value = _safe_float(signals.get("trading_value_est", 0))

    if category == "after_hours" and abs(after_change) >= 1:
        score += min(abs(after_change) * 1.5, 8)
    if category == "sector" and sector_score > 0:
        score += min(sector_score * 0.4, 6)
    if category in {"liquidity", "price"} and trading_value >= 300_000_000_000:
        score += 3
    if polarity == "negative" and risk_score >= 40:
        # 위험이 높으면 부정 근거도 설명상 중요하다.
        score += 5
    if category == "watch":
        # 체크포인트는 본문 핵심보다는 뒤에 배치한다.
        score -= 8

    return ImportanceReason(
        text=text,
        score=max(0.0, min(round(score, 1), 100.0)),
        category=category,
        polarity=polarity,
    )


def rank_importance(
    reasons: List[str],
    signals: Optional[Dict[str, Any]] = None,
    candidate: Optional[Any] = None,
    max_items: int = 5,
    allow_similar_categories: Optional[Iterable[str]] = None,
) -> List[ImportanceReason]:
    """근거 목록을 중요도순으로 정렬하고 유사 중복을 제거한다."""
    allow_similar_categories = set(allow_similar_categories or {"after_hours", "disclosure", "company"})

    scored: List[ImportanceReason] = []
    seen_exact = set()
    for r in reasons or []:
        text = _clean(r)
        if not text or text in seen_exact:
            continue
        seen_exact.add(text)
        scored.append(score_reason(text, signals=signals, candidate=candidate))

    scored.sort(key=lambda x: x.score, reverse=True)

    selected: List[ImportanceReason] = []
    seen_similar = set()
    for item in scored:
        key = _similar_key(item.text)
        if key in seen_similar and item.category not in allow_similar_categories:
            continue
        seen_similar.add(key)
        selected.append(item)
        if len(selected) >= int(max_items):
            break

    return selected


def rank_texts(
    reasons: List[str],
    signals: Optional[Dict[str, Any]] = None,
    candidate: Optional[Any] = None,
    max_items: int = 5,
) -> List[str]:
    """문자열 목록만 필요한 곳에서 사용하는 간편 API."""
    return [x.text for x in rank_importance(reasons, signals=signals, candidate=candidate, max_items=max_items)]


def split_by_importance(
    reasons: List[str],
    signals: Optional[Dict[str, Any]] = None,
    candidate: Optional[Any] = None,
    max_strengths: int = 4,
    max_risks: int = 3,
    max_watch: int = 3,
) -> Dict[str, List[str]]:
    """근거를 강점/리스크/체크포인트로 나누고 각각 중요도순 정렬한다."""
    scored = rank_importance(
        reasons=reasons,
        signals=signals,
        candidate=candidate,
        max_items=max(len(reasons or []), max_strengths + max_risks + max_watch),
        allow_similar_categories={"after_hours", "company", "disclosure", "watch"},
    )

    strengths: List[str] = []
    risks: List[str] = []
    watch: List[str] = []

    for item in scored:
        if item.polarity == "negative":
            risks.append(item.text)
        elif item.polarity == "watch" or item.category == "watch":
            watch.append(item.text)
        else:
            strengths.append(item.text)

    return {
        "strengths": _dedupe(strengths)[:max_strengths],
        "risks": _dedupe(risks)[:max_risks],
        "watch_points": _dedupe(watch)[:max_watch],
    }


def build_importance_summary(
    reasons: List[str],
    signals: Optional[Dict[str, Any]] = None,
    candidate: Optional[Any] = None,
    max_items: int = 3,
) -> str:
    """중요도 상위 근거를 한 문장으로 요약한다."""
    selected = rank_importance(reasons, signals=signals, candidate=candidate, max_items=max_items)
    if not selected:
        return "기본 수급과 가격 흐름을 중심으로 장 초반 확인이 필요합니다."

    texts = [x.text for x in selected]
    if len(texts) == 1:
        return f"{texts[0]}이 핵심 판단 근거입니다."

    return f"{texts[0]}이 가장 중요한 근거이며, {' · '.join(texts[1:])}도 함께 확인됩니다."


if __name__ == "__main__":
    sample = [
        "반도체·AI 섹터 강세",
        "시간외 +3.05% 상승",
        "전일 +8.22% 상승",
        "거래대금 대형주급 유동성",
        "시초가 갭 확인",
    ]
    for item in rank_importance(sample, signals={"after_hours_best_change": 3.05, "risk_score": 23}):
        print(item)
