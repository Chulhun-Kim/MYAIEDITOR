# stock/reason_ranker.py
# ------------------------------------------------------------
# MYAIEDITOR 장전 후보 추천 근거 정렬 엔진 v1.9
# ------------------------------------------------------------
# 역할:
# - 시간외, 기업 프로파일, 섹터, 뉴스, 거래량, 전일 등락률 등에서 나온
#   추천 근거를 중요도 기준으로 정렬한다.
# - 중복/유사 근거를 제거한다.
# - 표/Dashboard에는 상위 3개 내외의 짧은 근거만 보낸다.
# - Workspace/AI 브리핑에서는 같은 결과를 자연어로 확장해 사용할 수 있다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class RankedReason:
    text: str
    weight: float
    category: str = "etc"


def _clean(text: Any) -> str:
    return " ".join(str(text or "").strip().split())


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    low = str(text or "").lower()
    return any(str(k).lower() in low for k in keywords)


def _reason_category(text: str) -> str:
    t = str(text or "")
    if "시간외" in t:
        return "after_hours"
    if any(k in t for k in ["HBM", "메모리", "파운드리", "TC본더", "테스트소켓", "후공정", "K2", "유도무기", "바이오시밀러", "LNG선"]):
        return "company"
    if "DART" in t or "공시" in t or "수주" in t or "계약" in t:
        return "disclosure"
    if "섹터" in t:
        return "sector"
    if "뉴스" in t or "직접 언급" in t:
        return "news"
    if "거래량" in t or "거래대금" in t or "유동성" in t:
        return "liquidity"
    if "전일" in t or "직전" in t:
        return "price"
    if "환율" in t or "수출" in t or "금리" in t:
        return "macro"
    return "etc"


def _base_weight(text: str, signals: Optional[Dict[str, Any]] = None) -> float:
    signals = signals or {}
    category = _reason_category(text)

    weight_map = {
        "after_hours": 92,
        "disclosure": 90,
        "company": 88,
        "sector": 78,
        "news": 74,
        "liquidity": 68,
        "price": 64,
        "macro": 58,
        "etc": 50,
    }
    weight = float(weight_map.get(category, 50))

    # 강한 표현 보정
    if _contains_any(text, ["+", "상승", "강세", "급등", "긍정", "수주", "계약"]):
        weight += 4
    if _contains_any(text, ["약세", "하락", "급락", "주의"]):
        # 약세 근거는 추천 이유로도 중요하지만, 긍정 근거보다 약간 낮게 둔다.
        weight -= 3
    if _contains_any(text, ["직접", "종목명"]):
        weight += 5
    if _contains_any(text, ["HBM", "AI 서버", "TC본더", "테스트소켓"]):
        weight += 4

    return max(0.0, min(weight, 100.0))


def _similar_key(text: str) -> str:
    """유사 근거 중복 제거용 키."""
    t = str(text or "")

    groups: List[Tuple[str, List[str]]] = [
        ("after_hours", ["시간외"]),
        ("hbm", ["HBM", "메모리", "AI 서버", "TC본더", "테스트소켓", "후공정"]),
        ("semiconductor_sector", ["반도체", "AI 섹터"]),
        ("bio", ["바이오", "의약"]),
        ("defense", ["방산", "유도무기", "K2", "미사일"]),
        ("shipbuilding", ["조선", "LNG", "선박"]),
        ("news", ["뉴스"]),
        ("liquidity", ["거래량", "거래대금", "유동성"]),
        ("price", ["전일", "직전"]),
        ("macro", ["환율", "수출", "금리"]),
    ]

    for key, keywords in groups:
        if any(k in t for k in keywords):
            return key

    return t[:18]


def rank_reasons(
    reasons: List[str],
    signals: Optional[Dict[str, Any]] = None,
    max_items: int = 5,
) -> List[str]:
    """
    추천 근거를 중요도 기준으로 정렬하고 중복을 제거한다.
    """
    ranked: List[RankedReason] = []
    seen_exact = set()

    for r in reasons or []:
        text = _clean(r)
        if not text or text in seen_exact:
            continue
        seen_exact.add(text)
        ranked.append(
            RankedReason(
                text=text,
                weight=_base_weight(text, signals),
                category=_reason_category(text),
            )
        )

    ranked.sort(key=lambda x: x.weight, reverse=True)

    selected: List[RankedReason] = []
    seen_similar = set()

    for item in ranked:
        key = _similar_key(item.text)
        if key in seen_similar:
            # 다만 시간외와 회사 고유 근거는 매우 중요하므로 완전 중복만 아니면 유지 가능
            if item.category not in {"after_hours", "company", "disclosure"}:
                continue
        seen_similar.add(key)
        selected.append(item)
        if len(selected) >= int(max_items):
            break

    return [x.text for x in selected]


def build_reason_sentence(reasons: List[str], max_items: int = 3) -> str:
    """
    Workspace/브리핑용 짧은 자연어 요약문.
    현재는 규칙 기반 문장 생성이며, 추후 LLM 기반으로 확장 가능하다.
    """
    selected = [_clean(x) for x in (reasons or []) if _clean(x)][:max_items]
    if not selected:
        return "기본 수급과 가격 흐름을 중심으로 장 초반 확인이 필요합니다."

    if len(selected) == 1:
        return f"{selected[0]}이 핵심 점검 요인입니다."

    first = selected[0]
    rest = selected[1:]
    return f"{first}이 핵심이며, {' · '.join(rest)}도 함께 확인됩니다."
