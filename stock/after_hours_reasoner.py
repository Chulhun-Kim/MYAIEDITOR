# stock/after_hours_reasoner.py

from __future__ import annotations

from typing import Any, Dict, List


SECTOR_KEYWORDS = {
    "반도체·AI": [
        "반도체", "AI", "엔비디아", "HBM", "메모리", "파운드리",
        "삼성전자", "SK하이닉스", "마이크로소프트", "데이터센터",
    ],
    "2차전지": [
        "2차전지", "배터리", "전기차", "테슬라", "리튬", "양극재",
    ],
    "방산": [
        "방산", "무기", "국방", "수출", "현대로템", "한화에어로스페이스",
    ],
    "조선": [
        "조선", "선박", "LNG", "수주", "한화오션", "HD현대중공업",
    ],
    "원전": [
        "원전", "SMR", "원자력", "두산에너빌리티", "한전기술",
    ],
}


STOCK_SECTOR_MAP = {
    "삼성전자": "반도체·AI",
    "SK하이닉스": "반도체·AI",
    "한미반도체": "반도체·AI",
    "원익IPS": "반도체·AI",
    "ISC": "반도체·AI",
    "LG에너지솔루션": "2차전지",
    "삼성SDI": "2차전지",
    "에코프로비엠": "2차전지",
    "현대로템": "방산",
    "한화에어로스페이스": "방산",
    "LIG넥스원": "방산",
    "HD현대중공업": "조선",
    "삼성중공업": "조선",
    "한화오션": "조선",
    "두산에너빌리티": "원전",
    "한전기술": "원전",
}


def infer_sector(name: str) -> str:
    """
    종목명 기준 섹터 추정.
    """

    return STOCK_SECTOR_MAP.get(str(name).strip(), "기타")


def extract_news_keywords(
    news_items: List[Dict[str, Any]],
    sector: str,
    stock_name: str = "",
    max_keywords: int = 5,
) -> List[str]:
    """
    뉴스 목록에서 해당 섹터와 종목에 관련된 키워드를 추출한다.
    """

    if not news_items:
        return []

    keywords = SECTOR_KEYWORDS.get(sector, [])
    if stock_name:
        keywords = [stock_name] + keywords

    text = " ".join(
        [
            f"{n.get('title', '')} {n.get('description', '')} {n.get('content', '')}"
            for n in news_items
        ]
    )

    found = []

    for kw in keywords:
        count = text.count(kw)
        if count > 0:
            found.append((kw, count))

    found.sort(key=lambda x: x[1], reverse=True)

    return [kw for kw, _ in found[:max_keywords]]


def build_reason(
    name: str,
    change_pct: float,
    sector: str,
    news_keywords: List[str] | None = None,
    dart_hint: str = "",
) -> str:
    """
    시간외 등락 사유를 장전 분석용 문장으로 생성한다.
    """

    news_keywords = news_keywords or []
    keyword_text = ", ".join(news_keywords)

    if change_pct >= 3:
        if keyword_text:
            return (
                f"{sector} 관련 키워드({keyword_text})가 뉴스 흐름에서 감지된 가운데 "
                f"시간외 {change_pct:.2f}% 급등. 장 초반 갭 지속 여부와 거래량 동반 여부 확인 필요"
            )
        return (
            f"{sector} 섹터 관심 속 시간외 {change_pct:.2f}% 급등. "
            f"장 초반 갭 지속 여부와 거래량 동반 여부 확인 필요"
        )

    if change_pct >= 1:
        if keyword_text:
            return (
                f"{sector} 관련 뉴스 키워드({keyword_text})와 함께 시간외 {change_pct:.2f}% 상승. "
                f"장 초반 수급 지속 여부 확인 필요"
            )
        return (
            f"{sector} 섹터 내 시간외 {change_pct:.2f}% 상승. "
            f"장 초반 거래량 확대 여부 확인 필요"
        )

    if change_pct <= -3:
        if keyword_text:
            return (
                f"{sector} 관련 뉴스가 존재하나 시간외 {change_pct:.2f}% 급락. "
                f"악재성 공시·뉴스 여부와 장 초반 매도 지속 여부 확인 필요"
            )
        return (
            f"{sector} 섹터 내 시간외 {change_pct:.2f}% 급락. "
            f"악재성 뉴스·공시 여부 확인 필요"
        )

    if change_pct <= -1:
        if keyword_text:
            return (
                f"{sector} 관련 뉴스 흐름 속에서도 시간외 {change_pct:.2f}% 약세. "
                f"장 초반 반등 여부와 섹터 수급 확인 필요"
            )
        return (
            f"{sector} 섹터 내 시간외 {change_pct:.2f}% 약세. "
            f"장 초반 매도 지속 여부 확인 필요"
        )

    return (
        f"{sector} 섹터 내 시간외 변동은 제한적. "
        f"장 초반 거래량과 추가 뉴스 여부 확인 필요"
    )


def score_confidence(
    change_pct: float,
    news_keywords: List[str] | None = None,
    has_dart: bool = False,
) -> float:
    """
    reason 신뢰도 점수.
    0~1 사이 값.
    """

    score = 0.55

    if abs(change_pct) >= 3:
        score += 0.15
    elif abs(change_pct) >= 1:
        score += 0.08

    if news_keywords:
        score += min(len(news_keywords) * 0.05, 0.2)

    if has_dart:
        score += 0.1

    return round(min(score, 0.95), 2)


def reason_after_hours_row(
    row: Dict[str, Any],
    news_items: List[Dict[str, Any]] | None = None,
    dart_items: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    시간외 거래 1개 행에 대해 reason, sector, news_keyword, confidence를 생성한다.
    """

    news_items = news_items or []
    dart_items = dart_items or []

    name = str(row.get("name", "")).strip()
    change_pct = float(row.get("after_change_pct", 0) or 0)

    sector = str(row.get("sector", "") or "").strip() or infer_sector(name)

    news_keywords = extract_news_keywords(
        news_items=news_items,
        sector=sector,
        stock_name=name,
    )

    has_dart = any(
        name and name in str(d.get("name", "") or d.get("title", ""))
        for d in dart_items
    )

    reason = build_reason(
        name=name,
        change_pct=change_pct,
        sector=sector,
        news_keywords=news_keywords,
    )

    row["sector"] = sector
    row["reason"] = reason
    row["news_keyword"] = ",".join(news_keywords)
    row["confidence"] = score_confidence(
        change_pct=change_pct,
        news_keywords=news_keywords,
        has_dart=has_dart,
    )

    return row


def reason_after_hours_rows(
    rows: List[Dict[str, Any]],
    news_items: List[Dict[str, Any]] | None = None,
    dart_items: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    시간외 거래 여러 행에 reason을 일괄 생성한다.
    """

    return [
        reason_after_hours_row(
            row=dict(row),
            news_items=news_items,
            dart_items=dart_items,
        )
        for row in rows
    ]