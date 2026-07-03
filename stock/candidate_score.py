# stock/candidate_score.py
# ------------------------------------------------------------
# MYAIEDITOR 장전 후보 점수 엔진 v1.7
# - v1.7 핵심:
#   1) 강세점수(momentum_score)와 위험도(risk_score)를 분리
#   2) 관심 종목은 강세점수 기준으로 정렬
#   3) 위험도는 별도 컬럼/신호로 제공
#   4) AI 판단(action_label): 적극관찰 / 관찰 / 추격주의 / 눌림목 대기 / 제외검토
#   5) 100점 포화 방지와 순위 차별화 유지
#   6) AI 추천 근거(recommend_reasons)를 별도 생성
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass, field
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

    # v1.6 추가 필드
    momentum_score: float = 0.0
    risk_score: float = 0.0
    risk_stars: str = ""
    action_label: str = "관찰"
    risk_level: str = "보통"

    # v1.7 추가 필드: Dashboard/Workspace/장전 브리핑 공통 사용
    recommend_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def score_to_stars(score: float) -> str:
    if score >= 90:
        return "★★★★★"
    if score >= 82:
        return "★★★★☆"
    if score >= 74:
        return "★★★☆☆"
    if score >= 65:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def risk_to_stars(score: float) -> str:
    if score >= 80:
        return "★★★★★"
    if score >= 60:
        return "★★★★☆"
    if score >= 40:
        return "★★★☆☆"
    if score >= 20:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def risk_level_label(score: float) -> str:
    if score >= 80:
        return "매우 높음"
    if score >= 60:
        return "높음"
    if score >= 40:
        return "보통"
    if score >= 20:
        return "낮음"
    return "매우 낮음"


def decide_action(momentum_score: float, risk_score: float) -> str:
    """
    강세점수와 위험도를 분리해 최종 행동 라벨을 만든다.
    - 강세가 높고 위험이 낮으면 적극관찰
    - 강세가 높지만 위험도 높으면 추격주의/눌림목 대기
    - 강세가 약하면 제외검토
    """
    if momentum_score >= 88 and risk_score < 40:
        return "적극관찰"
    if momentum_score >= 82 and risk_score < 60:
        return "관찰"
    if momentum_score >= 78 and risk_score >= 60:
        return "추격주의"
    if momentum_score >= 70 and risk_score >= 55:
        return "눌림목 대기"
    if momentum_score >= 70:
        return "관찰"
    return "제외검토"


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


def _field(item: Any, key: str, default: Any = "") -> Any:
    if isinstance(item, dict):
        return item.get(key, default)

    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        try:
            return item.to_dict().get(key, default)
        except Exception:
            pass

    return getattr(item, key, default)


def _match_stock_name(text: str, name: str, ticker: str) -> bool:
    text = str(text or "")
    name = str(name or "")
    ticker = str(ticker or "")
    return bool(name and name in text) or bool(ticker and ticker in text)


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def _fmt_ratio(x: float) -> str:
    if x <= 0:
        return "-"
    return f"{x:.2f}배"


def _normalize_base_score(score: float) -> float:
    """
    app_stock.py의 기본 점수는 거래대금·급등률 때문에 100점을 쉽게 넘을 수 있다.
    v1.6에서는 강세점수의 원재료로 쓰기 위해 부드럽게 압축한다.
    """
    score = _safe_float(score)

    if score <= 70:
        return score

    compressed = 70.0 + (score - 70.0) * 0.45
    return min(compressed, 92.0)


def calc_after_hours_score(
    name: str,
    ticker: str,
    after_hours_data: Optional[List[Any]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []
    best_change = 0.0

    for item in after_hours_data or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())

        if not _match_stock_name(text, name, ticker):
            continue

        change_rate = _safe_float(
            d.get("after_change_pct")
            or d.get("change_rate")
            or d.get("등락률")
            or d.get("after_hours_change_rate")
            or d.get("rate")
            or 0
        )

        reason = d.get("reason") or d.get("사유") or d.get("news_reason") or ""

        if change_rate > 0:
            add = min(change_rate * 1.5, 8)
            score += add
            reasons.append(f"시간외 상승 {_fmt_pct(change_rate)} 반영")
        elif change_rate < 0:
            minus = min(abs(change_rate) * 2.0, 10)
            score -= minus
            reasons.append(f"시간외 약세 {_fmt_pct(change_rate)} 반영")

        if abs(change_rate) > abs(best_change):
            best_change = change_rate

        if reason:
            reasons.append(f"시간외 사유: {reason}")

        matched.append(d)

    return score, reasons[:3], {
        "matched_after_hours": matched[:3],
        "after_hours_best_change": round(best_change, 2),
    }


def calc_dart_score(
    name: str,
    ticker: str,
    dart_items: Optional[List[Any]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []

    positive_keywords = [
        "공급계약", "수주", "계약체결", "자사주", "소각", "배당",
        "신규시설투자", "영업이익", "실적개선",
    ]

    negative_keywords = [
        "유상증자", "전환사채", "CB", "BW", "불성실공시", "소송",
        "적자", "영업손실", "감사의견",
    ]

    positive_hits: List[str] = []
    negative_hits: List[str] = []

    for item in dart_items or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())

        if not _match_stock_name(text, name, ticker):
            continue

        matched.append(d)

        hit_positive = [kw for kw in positive_keywords if kw in text]
        hit_negative = [kw for kw in negative_keywords if kw in text]

        positive_hits.extend(hit_positive)
        negative_hits.extend(hit_negative)

        if hit_positive:
            score += 7
            reasons.append(f"DART 긍정 공시 감지: {', '.join(hit_positive[:3])}")

        if hit_negative:
            score -= 10
            reasons.append(f"DART 주의 공시 감지: {', '.join(hit_negative[:3])}")

        if not hit_positive and not hit_negative:
            score += 1
            reasons.append("DART 공시 확인 필요")

    return score, reasons[:3], {
        "matched_dart": matched[:3],
        "dart_positive_hits": sorted(set(positive_hits))[:5],
        "dart_negative_hits": sorted(set(negative_hits))[:5],
    }


def calc_sector_score(
    name: str,
    sector_results: Optional[List[Dict[str, Any]]],
) -> Tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    matched: List[Dict[str, Any]] = []

    for rank, sector in enumerate(sector_results or [], start=1):
        stocks = sector.get("stocks") or []
        sector_name = sector.get("sector", "")
        sector_score = _safe_float(sector.get("score"))

        if name not in stocks:
            continue

        rank_bonus = max(0.0, 4.0 - (rank - 1) * 0.8)
        add = min(sector_score * 0.08 + rank_bonus, 9)
        score += add
        reasons.append(f"강세 예상 섹터({sector_name}) 관련 종목")
        matched.append(sector)

    return score, reasons[:3], {"matched_sectors": matched[:3]}


def calc_risk_score(candidate: Any, after_hours_best_change: float = 0.0, dart_negative_hits: Optional[List[str]] = None) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    v1.6 위험도 전용 점수.
    이 값은 관심 후보에서 제외하기 위한 점수가 아니라, 추격매수 위험을 분리 표시하기 위한 점수다.
    """
    change_rate = _safe_float(_field(candidate, "change_rate", 0))
    volume_ratio = _safe_float(_field(candidate, "volume_ratio", 0))
    trading_value = _safe_float(_field(candidate, "trading_value_est", 0))

    risk = 0.0
    reasons: List[str] = []
    flags: List[str] = []

    if change_rate >= 20:
        risk += 38
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 급등으로 단기 과열 위험 높음")
        flags.append("price_extreme")
    elif change_rate >= 15:
        risk += 30
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 급등으로 추격매수 위험")
        flags.append("price_overheated")
    elif change_rate >= 10:
        risk += 22
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 상승으로 단기 과열 가능성")
        flags.append("price_hot")
    elif change_rate >= 8:
        risk += 15
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 상승으로 변동성 확인 필요")
        flags.append("price_watch")
    elif change_rate <= -8:
        risk += 26
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 하락으로 반등 확인 필요")
        flags.append("sharp_drop")
    elif change_rate <= -5:
        risk += 16
        reasons.append(f"직전 거래일 {_fmt_pct(change_rate)} 조정으로 수급 확인 필요")
        flags.append("pullback")

    if volume_ratio >= 3.0:
        risk += 28
        reasons.append(f"거래량이 {_fmt_ratio(volume_ratio)}로 과열되어 장중 급등락 가능성")
        flags.append("volume_extreme")
    elif volume_ratio >= 2.5:
        risk += 22
        reasons.append(f"거래량이 {_fmt_ratio(volume_ratio)}로 급증해 변동성 확대 가능성")
        flags.append("volume_hot")
    elif volume_ratio >= 2.0:
        risk += 14
        reasons.append(f"거래량이 {_fmt_ratio(volume_ratio)}로 증가해 시초가 확인 필요")
        flags.append("volume_watch")

    if trading_value >= 1_000_000_000_000:
        risk += 8
        reasons.append("거래대금이 매우 커 장중 변동성 확대 가능성")
        flags.append("large_trading_value")

    if after_hours_best_change < 0:
        risk += min(abs(after_hours_best_change) * 5.0, 18)
        reasons.append(f"시간외 약세 {_fmt_pct(after_hours_best_change)}로 장 초반 확인 필요")
        flags.append("after_hours_down")

    if dart_negative_hits:
        risk += 20
        reasons.append(f"DART 주의 공시 키워드 감지: {', '.join(dart_negative_hits[:3])}")
        flags.append("negative_dart")

    risk = max(0.0, min(round(risk, 1), 100.0))

    return risk, reasons[:5], {
        "change_rate": round(change_rate, 2),
        "volume_ratio": round(volume_ratio, 2),
        "trading_value_est": round(trading_value, 0),
        "risk_flags": flags,
    }



def _extract_sector_name(sector: Dict[str, Any]) -> str:
    """섹터 결과 딕셔너리에서 표시용 섹터명을 안전하게 추출한다."""
    return str(
        sector.get("sector")
        or sector.get("sector_name")
        or sector.get("name")
        or "관련 섹터"
    ).strip()


def build_recommend_reasons(
    candidate: Any,
    signals: Dict[str, Any],
    max_items: int = 5,
) -> List[str]:
    """
    v1.7 AI 추천 근거 생성 엔진.

    기존 reasons는 점수 압축, 위험도, 디버깅성 설명까지 포함한다.
    recommend_reasons는 Dashboard/Workspace/장전 브리핑에 바로 노출할
    짧고 사용성 높은 추천 근거만 별도로 만든다.
    """
    reasons: List[str] = []

    def add(text: str) -> None:
        text = str(text or "").strip()
        if text and text not in reasons:
            reasons.append(text)

    change_rate = _safe_float(_field(candidate, "change_rate", 0))
    volume_ratio = _safe_float(_field(candidate, "volume_ratio", 0))
    trading_value = _safe_float(_field(candidate, "trading_value_est", 0))

    after_hours_best_change = _safe_float(signals.get("after_hours_best_change", 0))
    if after_hours_best_change > 0:
        add(f"시간외 {_fmt_pct(after_hours_best_change)} 상승")
    elif after_hours_best_change < 0:
        add(f"시간외 {_fmt_pct(after_hours_best_change)} 약세")

    matched_sectors = signals.get("matched_sectors", []) or []
    if matched_sectors:
        sector = matched_sectors[0]
        if isinstance(sector, dict):
            sector_name = _extract_sector_name(sector)
            sector_score = _safe_float(sector.get("score", 0))
            if sector_score > 0:
                add(f"{sector_name} 섹터 강세")
            else:
                add(f"{sector_name} 섹터 관련")
        else:
            add("강세 섹터 관련")

    dart_positive_hits = signals.get("dart_positive_hits", []) or []
    if dart_positive_hits:
        add(f"DART 긍정 공시({', '.join(dart_positive_hits[:2])})")

    if volume_ratio >= 3.0:
        add(f"거래량 {_fmt_ratio(volume_ratio)} 급증")
    elif volume_ratio >= 2.0:
        add(f"거래량 {_fmt_ratio(volume_ratio)} 증가")
    elif volume_ratio >= 1.5:
        add("거래량 증가")

    if change_rate >= 10:
        add(f"전일 {_fmt_pct(change_rate)} 강세")
    elif change_rate >= 5:
        add(f"전일 {_fmt_pct(change_rate)} 상승")
    elif -5 <= change_rate < 2 and after_hours_best_change >= 1:
        add("전일 과열 낮고 시간외 강세")

    if trading_value >= 1_000_000_000_000:
        add("거래대금 대형주급 유동성")
    elif trading_value >= 300_000_000_000:
        add("거래대금 풍부")

    after_hours_score = _safe_float(signals.get("after_hours_score", 0))
    sector_score = _safe_float(signals.get("sector_score", 0))
    dart_score = _safe_float(signals.get("dart_score", 0))

    if not reasons:
        if after_hours_score > 0:
            add("시간외 흐름 양호")
        if sector_score > 0:
            add("섹터 모멘텀 반영")
        if dart_score > 0:
            add("공시 모멘텀 반영")

    if not reasons:
        add("기본 수급·가격 모멘텀 양호")

    return reasons[:max_items]

def _apply_momentum_ceiling(raw_score: float, risk_score: float) -> float:
    """
    강세점수는 유지하되, 위험도가 지나치게 높으면 만점권만 제한한다.
    v1.5처럼 큰 감점으로 강한 종목을 하위권으로 밀어내지 않는다.
    """
    cap = 96.0

    if risk_score >= 85:
        cap = 88.0
    elif risk_score >= 70:
        cap = 91.0
    elif risk_score >= 55:
        cap = 93.0
    elif risk_score >= 40:
        cap = 95.0

    return min(raw_score, cap)


def _rerank_scores(results: List[CandidateScore]) -> List[CandidateScore]:
    """
    관심 후보는 강세점수 기준으로 정렬한다.
    동점이 많을 경우 위험도가 낮은 종목을 약간 우선한다.
    """
    if not results:
        return []

    def sort_key(item: CandidateScore) -> Tuple[float, float, float]:
        return (item.momentum_score, -item.risk_score, item.base_score)

    results.sort(key=sort_key, reverse=True)

    adjusted: List[CandidateScore] = []
    previous_score: Optional[float] = None

    for rank, item in enumerate(results, start=1):
        rank_gap = (rank - 1) * 0.7
        new_score = max(0.0, round(item.momentum_score - rank_gap, 1))

        if previous_score is not None and new_score >= previous_score:
            new_score = max(0.0, round(previous_score - 0.3, 1))

        item.momentum_score = new_score
        item.total_score = new_score
        item.stars = score_to_stars(new_score)
        item.action_label = decide_action(item.momentum_score, item.risk_score)
        item.signals["rank"] = rank
        item.signals["rank_adjustment"] = round(-rank_gap, 1)
        previous_score = new_score
        adjusted.append(item)

    return adjusted


def build_candidate_scores(
    candidates: List[Any],
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
) -> List[CandidateScore]:
    results: List[CandidateScore] = []

    for p in candidates:
        ticker = str(_field(p, "ticker", ""))
        name = str(_field(p, "name", ""))
        market = str(_field(p, "market", ""))
        original_base_score = _safe_float(_field(p, "score", 0))
        base_score = _normalize_base_score(original_base_score)
        base_reasons = list(_field(p, "reasons", []) or [])

        momentum = base_score
        reasons: List[str] = []
        signals: Dict[str, Any] = {
            "original_base_score": round(original_base_score, 1),
            "compressed_base_score": round(base_score, 1),
        }

        reasons.extend(base_reasons[:3])

        if original_base_score != base_score:
            reasons.append(f"기본점수 {original_base_score:.1f}점을 {base_score:.1f}점으로 압축해 100점 포화를 방지")

        ah_score, ah_reasons, ah_signals = calc_after_hours_score(
            name=name,
            ticker=ticker,
            after_hours_data=after_hours_data,
        )
        momentum += ah_score
        reasons.extend(ah_reasons)
        signals.update(ah_signals)
        signals["after_hours_score"] = round(ah_score, 1)

        dart_score, dart_reasons, dart_signals = calc_dart_score(
            name=name,
            ticker=ticker,
            dart_items=dart_items,
        )
        momentum += dart_score
        reasons.extend(dart_reasons)
        signals.update(dart_signals)
        signals["dart_score"] = round(dart_score, 1)

        sector_score, sector_reasons, sector_signals = calc_sector_score(
            name=name,
            sector_results=sector_results,
        )
        momentum += sector_score
        reasons.extend(sector_reasons)
        signals.update(sector_signals)
        signals["sector_score"] = round(sector_score, 1)

        risk_score, risk_reasons, risk_signals = calc_risk_score(
            candidate=p,
            after_hours_best_change=_safe_float(signals.get("after_hours_best_change")),
            dart_negative_hits=signals.get("dart_negative_hits", []) or [],
        )
        signals.update(risk_signals)
        signals["risk_score"] = risk_score

        capped_momentum = _apply_momentum_ceiling(momentum, risk_score)
        if capped_momentum < momentum:
            reasons.append(f"위험도 {risk_score:.1f}점으로 강세점수 상한 {capped_momentum:.1f}점 적용")

        momentum = max(0.0, min(round(capped_momentum, 1), 96.0))

        risk_level = risk_level_label(risk_score)
        action_label = decide_action(momentum, risk_score)

        # 위험도는 별도 판단으로 유지한다.
        if risk_reasons:
            reasons.append(f"위험도 {risk_score:.1f}점({risk_level}): {risk_reasons[0]}")
        reasons.append(f"AI 판단: {action_label}")

        deduped_reasons: List[str] = []
        for r in reasons:
            if r and r not in deduped_reasons:
                deduped_reasons.append(r)

        recommend_reasons = build_recommend_reasons(
            candidate=p,
            signals=signals,
            max_items=5,
        )

        signals["recommend_reasons"] = recommend_reasons

        results.append(
            CandidateScore(
                ticker=ticker,
                name=name,
                market=market,
                base_score=round(original_base_score, 1),
                total_score=momentum,
                stars=score_to_stars(momentum),
                reasons=deduped_reasons[:9],
                signals=signals,
                momentum_score=momentum,
                risk_score=risk_score,
                risk_stars=risk_to_stars(risk_score),
                action_label=action_label,
                risk_level=risk_level,
                recommend_reasons=recommend_reasons,
            )
        )

    return _rerank_scores(results)
