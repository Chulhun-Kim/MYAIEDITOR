# stock/candidate_score.py
# ------------------------------------------------------------
# MYAIEDITOR 장전 후보 점수 엔진
# - 기존 가격/거래량 점수에 시간외 거래, DART 공시, 섹터 신호를 더해
#   최종 관심도 점수와 별점(★★★★★)을 계산한다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CandidateScore:
    ticker: str
    name: str
    market: str
    base_score: float
    total_score: float
    stars: str
    reasons: List[str]
    signals: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def score_to_stars(score: float) -> str:
    if score >= 90:
        return "★★★★★"
    if score >= 80:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    if score >= 60:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


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


def _match_stock_name(text: str, name: str, ticker: str) -> bool:
    text = str(text or "")
    name = str(name or "")
    ticker = str(ticker or "")
    return bool(name and name in text) or bool(ticker and ticker in text)


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def calc_after_hours_score(
    name: str,
    ticker: str,
    after_hours_data: Optional[List[Any]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []

    for item in after_hours_data or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())

        if not _match_stock_name(text, name, ticker):
            continue

        change_rate = _safe_float(
            d.get("change_rate")
            or d.get("등락률")
            or d.get("after_hours_change_rate")
            or d.get("rate")
            or 0
        )

        reason = d.get("reason") or d.get("사유") or d.get("news_reason") or ""

        if change_rate > 0:
            add = min(change_rate * 2.5, 18)
            score += add
            reasons.append(f"시간외 상승 {_fmt_pct(change_rate)} 반영")
        elif change_rate < 0:
            minus = min(abs(change_rate) * 2.5, 18)
            score -= minus
            reasons.append(f"시간외 약세 {_fmt_pct(change_rate)} 반영")

        if reason:
            reasons.append(f"시간외 사유: {reason}")

        matched.append(d)

    return score, reasons[:3], {"matched_after_hours": matched[:3]}


def calc_dart_score(
    name: str,
    ticker: str,
    dart_items: Optional[List[Any]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []

    positive_keywords = [
        "공급계약",
        "수주",
        "계약체결",
        "자사주",
        "소각",
        "배당",
        "신규시설투자",
        "영업이익",
        "실적개선",
    ]

    negative_keywords = [
        "유상증자",
        "전환사채",
        "CB",
        "BW",
        "불성실공시",
        "소송",
        "적자",
        "영업손실",
        "감사의견",
    ]

    for item in dart_items or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())

        if not _match_stock_name(text, name, ticker):
            continue

        matched.append(d)

        hit_positive = [kw for kw in positive_keywords if kw in text]
        hit_negative = [kw for kw in negative_keywords if kw in text]

        if hit_positive:
            score += 10
            reasons.append(f"DART 긍정 공시 감지: {', '.join(hit_positive[:3])}")

        if hit_negative:
            score -= 12
            reasons.append(f"DART 주의 공시 감지: {', '.join(hit_negative[:3])}")

        if not hit_positive and not hit_negative:
            score += 2
            reasons.append("DART 공시 확인 필요")

    return score, reasons[:3], {"matched_dart": matched[:3]}


def calc_sector_score(
    name: str,
    sector_results: Optional[List[Dict[str, Any]]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []

    for sector in sector_results or []:
        stocks = sector.get("stocks") or []
        sector_name = sector.get("sector", "")
        sector_score = _safe_float(sector.get("score"))

        if name not in stocks:
            continue

        add = min(sector_score * 0.25, 15)
        score += add
        reasons.append(f"강세 예상 섹터({sector_name}) 관련 종목")
        matched.append(sector)

    return score, reasons[:3], {"matched_sectors": matched[:3]}


def build_candidate_scores(
    candidates: List[Any],
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
) -> List[CandidateScore]:
    results: List[CandidateScore] = []

    for p in candidates:
        ticker = str(getattr(p, "ticker", ""))
        name = str(getattr(p, "name", ""))
        market = str(getattr(p, "market", ""))
        base_score = _safe_float(getattr(p, "score", 0))
        base_reasons = list(getattr(p, "reasons", []) or [])

        total = base_score
        reasons: List[str] = list(base_reasons[:4])
        signals: Dict[str, Any] = {}

        ah_score, ah_reasons, ah_signals = calc_after_hours_score(
            name=name,
            ticker=ticker,
            after_hours_data=after_hours_data,
        )
        total += ah_score
        reasons.extend(ah_reasons)
        signals.update(ah_signals)

        dart_score, dart_reasons, dart_signals = calc_dart_score(
            name=name,
            ticker=ticker,
            dart_items=dart_items,
        )
        total += dart_score
        reasons.extend(dart_reasons)
        signals.update(dart_signals)

        sector_score, sector_reasons, sector_signals = calc_sector_score(
            name=name,
            sector_results=sector_results,
        )
        total += sector_score
        reasons.extend(sector_reasons)
        signals.update(sector_signals)

        total = max(0, min(round(total, 1), 100))

        results.append(
            CandidateScore(
                ticker=ticker,
                name=name,
                market=market,
                base_score=round(base_score, 1),
                total_score=total,
                stars=score_to_stars(total),
                reasons=reasons[:7],
                signals=signals,
            )
        )

    results.sort(key=lambda x: x.total_score, reverse=True)
    return results
