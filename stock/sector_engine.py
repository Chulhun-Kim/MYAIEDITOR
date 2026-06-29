# stock/sector_engine.py
# ------------------------------------------------------------
# MYAIEDITOR 섹터 분석 엔진
# - 뉴스 + 해외시장 참고지표를 바탕으로 강세 예상 섹터를 산출
# - app_stock.py에서 분리한 1단계 리팩터링 모듈
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Dict, List


SECTOR_MAP: Dict[str, Dict[str, Any]] = {
    "반도체·AI": {
        "keywords": ["반도체", "AI", "엔비디아", "HBM", "삼성전자", "SK하이닉스"],
        "stocks": ["삼성전자", "SK하이닉스", "한미반도체", "리노공업", "ISC", "원익IPS"],
    },
    "2차전지": {
        "keywords": ["2차전지", "배터리", "전기차", "테슬라", "리튬"],
        "stocks": ["LG에너지솔루션", "삼성SDI", "에코프로비엠", "에코프로", "포스코퓨처엠", "LG화학"],
    },
    "방산": {
        "keywords": ["방산", "국방", "무기", "수출", "NATO"],
        "stocks": ["한화에어로스페이스", "LIG넥스원", "현대로템"],
    },
    "조선": {
        "keywords": ["조선", "선박", "LNG", "수주"],
        "stocks": ["HD현대중공업", "삼성중공업", "HD한국조선해양"],
    },
    "원전": {
        "keywords": ["원전", "SMR", "원자력", "전력"],
        "stocks": ["두산에너빌리티", "한전기술"],
    },
    "자동차": {
        "keywords": ["자동차", "전기차", "현대차", "기아"],
        "stocks": ["현대차", "기아"],
    },
    "바이오": {
        "keywords": ["바이오", "의약품", "FDA", "임상"],
        "stocks": ["셀트리온", "삼성바이오로직스"],
    },
    "금융": {
        "keywords": ["금리", "은행", "금융", "배당"],
        "stocks": ["KB금융", "신한지주"],
    },
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _news_text(news_items: List[Any]) -> str:
    parts: List[str] = []
    for n in news_items or []:
        if isinstance(n, dict):
            parts.append(f"{n.get('title', '')} {n.get('description', '')} {n.get('content', '')}")
        else:
            parts.append(
                f"{getattr(n, 'title', '')} {getattr(n, 'description', '')} {getattr(n, 'content', '')}"
            )
    return " ".join(parts)


def analyze_sectors(
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
) -> List[Dict[str, Any]]:
    """
    뉴스 + 해외지표를 바탕으로 강세 예상 섹터를 추출한다.
    """

    text_parts: List[str] = [_news_text(news_items)]

    for it in indicators or []:
        text_parts.append(
            f"{it.get('name', '')} "
            f"{it.get('symbol', '')} "
            f"{it.get('memo', '')}"
        )

    text = " ".join(text_parts)
    results: List[Dict[str, Any]] = []

    for sector, info in SECTOR_MAP.items():
        score = 0.0
        matched: List[str] = []

        for kw in info.get("keywords", []):
            cnt = text.count(kw)
            if cnt > 0:
                score += cnt * 10
                matched.append(f"{kw}({cnt})")

        for it in indicators or []:
            name = str(it.get("name", ""))
            chg = _safe_float(it.get("change_rate"))

            if sector == "반도체·AI":
                if name in ["엔비디아", "나스닥", "마이크로소프트"] and chg > 0:
                    score += min(chg * 5, 20)

            elif sector == "2차전지":
                if name == "테슬라" and chg > 0:
                    score += min(chg * 5, 20)

            elif sector == "자동차":
                if name == "테슬라" and chg > 0:
                    score += min(chg * 3, 15)

            if name == "달러/원" and chg > 0:
                if sector in ["반도체·AI", "자동차", "조선"]:
                    score += min(chg * 5, 15)

            if name == "WTI유가" and chg > 0:
                if sector in ["조선", "방산"]:
                    score += min(chg * 3, 10)

        if score > 0:
            results.append(
                {
                    "sector": sector,
                    "score": round(score, 1),
                    "matched": matched[:8],
                    "stocks": info.get("stocks", []),
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


def build_news_keywords_summary(news_items: List[Any]) -> List[str]:
    keywords = [
        "반도체", "AI", "엔비디아", "HBM", "삼성전자", "SK하이닉스",
        "방산", "조선", "원전", "2차전지", "바이오", "환율", "금리", "코스피",
        "유가", "중동", "관세", "수출", "실적", "수주",
    ]
    text = _news_text(news_items)
    found = []
    for k in keywords:
        c = text.count(k)
        if c > 0:
            found.append((k, c))
    found.sort(key=lambda x: x[1], reverse=True)
    return [f"{k}({c})" for k, c in found[:10]]
