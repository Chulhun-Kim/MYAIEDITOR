# stock/market_decision.py
# ------------------------------------------------------------
# MYAIEDITOR 시장 판단 엔진 v1.4-2
# AI Strategy Engine
# - 해외시장·환율·유가·뉴스·시간외·DART·섹터를 종합해
#   장전 시장 분위기, 투자전략, 현금비중, 섹터전략을 구조화한다.
# - v1.4: 전략 근거를 긍정요인 / 위험요인 / 장 시작 후 확인으로 분리
# - v1.4-2: 시장점수 과열 보정, 관심종목·주의종목 중복 위험 반영
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MarketDecision:
    score: float
    stars: str
    sentiment: str
    strategy: str
    strategy_comment: str
    cash_ratio: int
    buy_ratio: int
    sector_strategy: str
    summary: str

    reasons: List[str] = field(default_factory=list)
    strategy_reasons: List[str] = field(default_factory=list)
    positive_reasons: List[str] = field(default_factory=list)
    risk_reasons: List[str] = field(default_factory=list)
    check_points: List[str] = field(default_factory=list)

    signals: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
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


def _news_text(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(
            str(item.get(k, "") or "")
            for k in ["title", "description", "content", "summary"]
        )

    return " ".join(
        str(getattr(item, k, "") or "")
        for k in ["title", "description", "content", "summary"]
    )


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def score_to_stars(score: float) -> str:
    if score >= 95:
        return "★★★★★"
    if score >= 85:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    if score >= 55:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def classify_market(score: float) -> tuple[str, str]:
    if score >= 95:
        return "매우 강세", "🟢 매우 강세"
    if score >= 85:
        return "강세", "🟢 강세"
    if score >= 70:
        return "중립 우위", "🟡 중립 우위"
    if score >= 55:
        return "중립", "🟡 중립"
    if score >= 45:
        return "주의", "🔴 주의"
    return "위험", "🔴 위험"


def _get_signal_change(signals: Dict[str, Any], keyword: str) -> float:
    for key, value in signals.items():
        if keyword in str(key):
            return _safe_float(value)
    return 0.0


def _stock_key(item: Any) -> str:
    ticker = str(
        _field(item, "ticker", "")
        or _field(item, "code", "")
        or _field(item, "stock_code", "")
        or _field(item, "종목코드", "")
        or ""
    ).strip()

    name = str(
        _field(item, "name", "")
        or _field(item, "stock_name", "")
        or _field(item, "종목명", "")
        or ""
    ).strip()

    return ticker or name


def _stock_name(item: Any) -> str:
    name = str(
        _field(item, "name", "")
        or _field(item, "stock_name", "")
        or _field(item, "종목명", "")
        or ""
    ).strip()

    ticker = str(
        _field(item, "ticker", "")
        or _field(item, "code", "")
        or _field(item, "stock_code", "")
        or _field(item, "종목코드", "")
        or ""
    ).strip()

    if name and ticker:
        return f"{name}({ticker})"
    return name or ticker or "종목"


def _stock_score(item: Any) -> float:
    return _safe_float(
        _field(item, "total_score", None)
        or _field(item, "score", None)
        or _field(item, "base_score", None)
        or 0
    )


def _stock_change_rate(item: Any) -> float:
    return _safe_float(
        _field(item, "change_rate", None)
        or _field(item, "등락률", None)
        or _field(item, "rate", None)
        or 0
    )


def _stock_volume_ratio(item: Any) -> float:
    return _safe_float(
        _field(item, "volume_ratio", None)
        or _field(item, "거래량배율", None)
        or _field(item, "volume_multiple", None)
        or 0
    )


def _candidate_quality_score(candidate_scores: Optional[List[Any]], candidates: Optional[List[Any]]) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    관심종목의 품질을 시장 판단에 반영한다.
    candidate_scores가 있으면 이를 우선 사용하고, 없으면 candidates를 사용한다.
    """
    items = list(candidate_scores or candidates or [])

    if not items:
        return 0.0, [], {
            "candidate_count": 0,
            "candidate_avg_score": 0.0,
            "candidate_high_quality_count": 0,
            "candidate_overheated_count": 0,
        }

    top_items = items[:10]

    scores = [_stock_score(x) for x in top_items if _stock_score(x) > 0]
    changes = [_stock_change_rate(x) for x in top_items]
    volumes = [_stock_volume_ratio(x) for x in top_items]

    avg_score = sum(scores) / len(scores) if scores else 0.0
    high_quality_count = sum(1 for s in scores if s >= 85)
    overheated_count = sum(
        1 for item in top_items
        if _stock_change_rate(item) >= 8.0 or _stock_volume_ratio(item) >= 2.5
    )

    score = 0.0
    reasons: List[str] = []

    if avg_score >= 90 and high_quality_count >= 3:
        score += 5
        reasons.append(f"관심종목 평균 점수 {avg_score:.1f}점, 고품질 후보 {high_quality_count}개로 종목 풀의 질이 양호합니다.")
    elif avg_score >= 80:
        score += 3
        reasons.append(f"관심종목 평균 점수 {avg_score:.1f}점으로 선별 후보군이 형성됐습니다.")
    elif avg_score > 0 and avg_score < 70:
        score -= 3
        reasons.append(f"관심종목 평균 점수 {avg_score:.1f}점으로 후보군의 확신도가 높지 않습니다.")

    if overheated_count >= 5:
        score -= 5
        reasons.append(f"관심종목 중 과열 후보가 {overheated_count}개로 많아 추격 매수 위험이 있습니다.")
    elif overheated_count >= 3:
        score -= 3
        reasons.append(f"관심종목 중 과열 후보가 {overheated_count}개 확인돼 시초가 갭 확인이 필요합니다.")

    avg_change = sum(changes) / len(changes) if changes else 0.0
    avg_volume = sum(volumes) / len(volumes) if volumes else 0.0

    return score, reasons, {
        "candidate_count": len(top_items),
        "candidate_avg_score": round(avg_score, 1),
        "candidate_high_quality_count": high_quality_count,
        "candidate_overheated_count": overheated_count,
        "candidate_avg_change": round(avg_change, 2),
        "candidate_avg_volume_ratio": round(avg_volume, 2),
    }


def _risk_stock_score(risks: Optional[List[Any]]) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    주의종목의 과열·변동성 위험을 시장 판단에 반영한다.
    """
    items = list(risks or [])

    if not items:
        return 0.0, [], {
            "risk_stock_count": 0,
            "risk_overheated_count": 0,
            "risk_avg_change": 0.0,
            "risk_avg_volume_ratio": 0.0,
        }

    top_items = items[:10]

    overheated_count = sum(
        1 for item in top_items
        if _stock_change_rate(item) >= 8.0 or _stock_volume_ratio(item) >= 2.0
    )

    changes = [_stock_change_rate(x) for x in top_items]
    volumes = [_stock_volume_ratio(x) for x in top_items]

    avg_change = sum(changes) / len(changes) if changes else 0.0
    avg_volume = sum(volumes) / len(volumes) if volumes else 0.0

    score = 0.0
    reasons: List[str] = []

    if len(top_items) >= 8:
        score -= 4
        reasons.append(f"주의종목이 {len(top_items)}개로 많아 장 초반 변동성 관리가 필요합니다.")
    elif len(top_items) >= 5:
        score -= 2
        reasons.append(f"주의종목이 {len(top_items)}개 확인돼 선별 접근이 필요합니다.")

    if overheated_count >= 5:
        score -= 6
        reasons.append(f"주의종목 중 과열 후보가 {overheated_count}개로 많아 추격 매수 위험이 큽니다.")
    elif overheated_count >= 3:
        score -= 4
        reasons.append(f"주의종목 중 과열 후보가 {overheated_count}개 확인됐습니다.")

    return score, reasons, {
        "risk_stock_count": len(top_items),
        "risk_overheated_count": overheated_count,
        "risk_avg_change": round(avg_change, 2),
        "risk_avg_volume_ratio": round(avg_volume, 2),
    }


def _overlap_score(candidate_scores: Optional[List[Any]], candidates: Optional[List[Any]], risks: Optional[List[Any]]) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    관심종목과 주의종목이 겹치면 '강하지만 과열된 종목'이 많다는 뜻이므로
    시장 점수에는 감점하고 위험요인에 반영한다.
    """
    candidate_items = list(candidate_scores or candidates or [])
    risk_items = list(risks or [])

    candidate_keys = {_stock_key(x) for x in candidate_items[:10] if _stock_key(x)}
    risk_keys = {_stock_key(x) for x in risk_items[:10] if _stock_key(x)}

    overlap_keys = candidate_keys & risk_keys
    overlap_count = len(overlap_keys)

    names: List[str] = []
    if overlap_count:
        for item in candidate_items[:10]:
            if _stock_key(item) in overlap_keys:
                names.append(_stock_name(item))

    score = 0.0
    reasons: List[str] = []

    if overlap_count >= 5:
        score -= 6
        reasons.append(f"관심종목과 주의종목 중복이 {overlap_count}개로 많아 강세장 속 과열 위험이 큽니다.")
    elif overlap_count >= 3:
        score -= 4
        reasons.append(f"관심종목과 주의종목 중복이 {overlap_count}개 확인돼 추격 매수는 신중해야 합니다.")
    elif overlap_count >= 1:
        score -= 2
        reasons.append(f"관심종목과 주의종목이 {overlap_count}개 겹쳐 일부 종목은 과열 여부를 확인해야 합니다.")

    return score, reasons, {
        "overlap_count": overlap_count,
        "overlap_names": names[:5],
    }


def _apply_score_cap(total: float, signals: Dict[str, Any], reasons: List[str]) -> float:
    """
    위험 신호가 있는데도 점수가 100점까지 치솟는 것을 방지한다.
    """
    cap = 100.0

    negative_news = _safe_int(signals.get("negative_news_count"))
    after_down = _safe_int(signals.get("after_hours_down"))
    strong_down = _safe_int(signals.get("after_hours_strong_down"))
    negative_dart = _safe_int(signals.get("negative_dart_count"))
    risk_stock_count = _safe_int(signals.get("risk_stock_count"))
    risk_overheated_count = _safe_int(signals.get("risk_overheated_count"))
    overlap_count = _safe_int(signals.get("overlap_count"))

    if negative_news > 0:
        cap = min(cap, 97.0)

    if after_down > 0:
        cap = min(cap, 95.0)

    if strong_down > 0:
        cap = min(cap, 93.0)

    if negative_dart > 0:
        cap = min(cap, 94.0)

    if risk_stock_count >= 8:
        cap = min(cap, 92.0)

    if risk_overheated_count >= 5:
        cap = min(cap, 90.0)
    elif risk_overheated_count >= 3:
        cap = min(cap, 92.0)

    if overlap_count >= 5:
        cap = min(cap, 90.0)
    elif overlap_count >= 3:
        cap = min(cap, 92.0)
    elif overlap_count >= 1:
        cap = min(cap, 95.0)

    if total > cap:
        reasons.append(f"위험 신호가 확인돼 시장점수 상한을 {cap:.0f}점으로 보정했습니다.")
        total = cap

    return max(0.0, min(round(total, 1), 100.0))


def decide_ai_strategy(score: float, signals: Dict[str, Any]) -> tuple[str, str, int, int, List[str]]:
    negative_news = _safe_int(signals.get("negative_news_count"))
    positive_news = _safe_int(signals.get("positive_news_count"))
    after_down = _safe_int(signals.get("after_hours_down"))
    after_up = _safe_int(signals.get("after_hours_up"))
    negative_dart = _safe_int(signals.get("negative_dart_count"))
    risk_overheated_count = _safe_int(signals.get("risk_overheated_count"))
    overlap_count = _safe_int(signals.get("overlap_count"))
    top_sector = signals.get("top_sector")

    risk_penalty = 0
    strategy_reasons: List[str] = []

    if negative_news >= positive_news + 5:
        risk_penalty += 1
        strategy_reasons.append("부정 뉴스 키워드가 긍정 뉴스보다 많아 추격 매수는 신중해야 합니다.")

    if after_down > after_up:
        risk_penalty += 1
        strategy_reasons.append("시간외 하락 종목 수가 상승 종목보다 많아 장 초반 변동성 확인이 필요합니다.")

    if negative_dart >= 2:
        risk_penalty += 1
        strategy_reasons.append("주의 공시 키워드가 감지돼 개별 종목 리스크 관리가 필요합니다.")

    if risk_overheated_count >= 3:
        risk_penalty += 1
        strategy_reasons.append("과열·변동성 주의 종목이 많아 시초가 추격 매수는 제한해야 합니다.")

    if overlap_count >= 3:
        risk_penalty += 1
        strategy_reasons.append("관심종목과 주의종목 중복이 많아 강세 흐름 속 과열 위험을 함께 봐야 합니다.")

    if top_sector:
        strategy_reasons.append(f"핵심 섹터는 {top_sector}로 판단됩니다.")

    adjusted_score = score - risk_penalty * 5

    if adjusted_score >= 95:
        strategy = "▶ 적극 매수"
        comment = "시장 강도가 매우 높습니다. 다만 과열 신호가 있는 종목은 시초가와 거래량 확인 후 접근합니다."
        cash_ratio = 20
    elif adjusted_score >= 85:
        strategy = "▶ 선별 매수"
        comment = "시장 분위기는 우호적이지만 업종별 차별화와 과열 종목 변동성이 예상됩니다. 강한 섹터 중심으로 선별 접근합니다."
        cash_ratio = 30
    elif adjusted_score >= 70:
        strategy = "▶ 관망"
        comment = "방향성은 나쁘지 않지만 추격 매수보다 시초가·거래량·수급 확인 후 접근하는 것이 좋습니다."
        cash_ratio = 50
    elif adjusted_score >= 55:
        strategy = "▶ 현금비중 확대"
        comment = "시장 변동성이 커질 수 있는 구간입니다. 신규 매수보다 리스크 관리가 우선입니다."
        cash_ratio = 70
    else:
        strategy = "▶ 방어적 대응"
        comment = "시장 리스크가 높은 구간입니다. 현금 비중 유지와 손실 방어를 우선합니다."
        cash_ratio = 80

    buy_ratio = 100 - cash_ratio

    if not strategy_reasons:
        strategy_reasons.append("뚜렷한 위험 신호는 제한적이나 장 초반 가격과 거래량 확인이 필요합니다.")

    return strategy, comment, cash_ratio, buy_ratio, strategy_reasons[:6]


def build_strategy_details(signals: Dict[str, Any]) -> tuple[List[str], List[str], List[str]]:
    positive: List[str] = []
    risk: List[str] = []

    nasdaq = _get_signal_change(signals, "나스닥")
    sp500 = _get_signal_change(signals, "S&P500")
    nvidia = _get_signal_change(signals, "엔비디아")
    microsoft = _get_signal_change(signals, "마이크로소프트")
    tesla = _get_signal_change(signals, "테슬라")
    usdkrw = _get_signal_change(signals, "달러/원")
    wti = _get_signal_change(signals, "WTI유가")

    positive_news = _safe_int(signals.get("positive_news_count"))
    negative_news = _safe_int(signals.get("negative_news_count"))
    positive_dart = _safe_int(signals.get("positive_dart_count"))
    negative_dart = _safe_int(signals.get("negative_dart_count"))

    after_up = _safe_int(signals.get("after_hours_up"))
    after_down = _safe_int(signals.get("after_hours_down"))
    strong_up = _safe_int(signals.get("after_hours_strong_up"))
    strong_down = _safe_int(signals.get("after_hours_strong_down"))

    candidate_avg_score = _safe_float(signals.get("candidate_avg_score"))
    candidate_high_quality_count = _safe_int(signals.get("candidate_high_quality_count"))
    candidate_overheated_count = _safe_int(signals.get("candidate_overheated_count"))

    risk_stock_count = _safe_int(signals.get("risk_stock_count"))
    risk_overheated_count = _safe_int(signals.get("risk_overheated_count"))
    overlap_count = _safe_int(signals.get("overlap_count"))
    overlap_names = signals.get("overlap_names", []) or []

    top_sector = signals.get("top_sector")
    top_sector_score = _safe_float(signals.get("top_sector_score"))

    if nasdaq >= 1.0:
        positive.append(f"나스닥이 {_fmt_pct(nasdaq)} 상승하며 성장주·AI 투자심리에 우호적입니다.")
    elif nasdaq > 0:
        positive.append(f"나스닥이 {_fmt_pct(nasdaq)} 상승해 기술주 심리가 소폭 개선됐습니다.")

    if sp500 >= 0.7:
        positive.append(f"S&P500이 {_fmt_pct(sp500)} 상승하며 위험자산 선호가 개선됐습니다.")

    if nvidia >= 1.0:
        positive.append(f"엔비디아가 {_fmt_pct(nvidia)} 강세를 보이며 AI·반도체 투자심리에 긍정적입니다.")

    if microsoft >= 1.0:
        positive.append(f"마이크로소프트가 {_fmt_pct(microsoft)} 상승하며 대형 기술주 흐름에 힘을 보탰습니다.")

    if tesla >= 1.0:
        positive.append(f"테슬라가 {_fmt_pct(tesla)} 상승해 2차전지·전기차 관련 심리 개선 가능성이 있습니다.")

    if usdkrw <= -0.5:
        positive.append(f"달러/원이 {_fmt_pct(usdkrw)} 하락해 외국인 수급 여건 개선 가능성이 있습니다.")

    if positive_news >= 5:
        positive.append(f"긍정 뉴스 키워드가 {positive_news}건 감지돼 시장 심리에 우호적입니다.")
    elif positive_news > 0:
        positive.append(f"긍정 뉴스 키워드가 {positive_news}건 감지됐습니다.")

    if positive_dart > 0:
        positive.append(f"긍정 공시 키워드가 {positive_dart}건 감지돼 개별 종목 모멘텀이 확인됩니다.")

    if after_up > after_down and after_up > 0:
        positive.append(f"시간외 상승 종목이 {after_up}개로 하락 종목 {after_down}개보다 많습니다.")

    if strong_up > 0:
        positive.append(f"시간외 3% 이상 강세 종목이 {strong_up}개 확인됐습니다.")

    if candidate_avg_score >= 85:
        positive.append(f"관심종목 평균 점수가 {candidate_avg_score:.1f}점으로 후보군의 질이 양호합니다.")

    if candidate_high_quality_count >= 3:
        positive.append(f"85점 이상 고품질 관심 후보가 {candidate_high_quality_count}개 확인됐습니다.")

    if top_sector:
        if top_sector_score > 0:
            positive.append(f"{top_sector} 섹터가 상위 강세 섹터로 포착됐습니다. 점수는 {top_sector_score:.1f}점입니다.")
        else:
            positive.append(f"{top_sector} 섹터가 핵심 점검 섹터로 포착됐습니다.")

    if nasdaq <= -1.0:
        risk.append(f"나스닥이 {_fmt_pct(nasdaq)} 하락해 성장주·AI 투자심리에 부담입니다.")

    if sp500 <= -0.7:
        risk.append(f"S&P500이 {_fmt_pct(sp500)} 하락해 위험자산 선호가 약화됐습니다.")

    if nvidia <= -1.0:
        risk.append(f"엔비디아가 {_fmt_pct(nvidia)} 하락해 AI·반도체 투자심리에 부담입니다.")

    if microsoft <= -1.0:
        risk.append(f"마이크로소프트가 {_fmt_pct(microsoft)} 하락해 대형 기술주 흐름을 확인해야 합니다.")

    if tesla <= -1.0:
        risk.append(f"테슬라가 {_fmt_pct(tesla)} 하락해 2차전지·전기차 관련주 변동성에 주의가 필요합니다.")

    if usdkrw >= 0.7:
        risk.append(f"달러/원이 {_fmt_pct(usdkrw)} 상승해 외국인 수급 부담 가능성이 있습니다.")

    if wti >= 2.0:
        risk.append(f"WTI 유가가 {_fmt_pct(wti)} 상승해 비용 부담 업종에 주의가 필요합니다.")

    if negative_news >= positive_news + 3:
        risk.append(f"주의 뉴스 키워드가 {negative_news}건으로 긍정 뉴스보다 많습니다.")
    elif negative_news > 0:
        risk.append(f"주의 뉴스 키워드가 {negative_news}건 감지됐습니다.")

    if negative_dart >= 2:
        risk.append(f"주의 공시 키워드가 {negative_dart}건 감지돼 개별 종목 리스크 관리가 필요합니다.")
    elif negative_dart > 0:
        risk.append(f"주의 공시 키워드가 {negative_dart}건 감지됐습니다.")

    if after_down > after_up and after_down > 0:
        risk.append(f"시간외 하락 종목이 {after_down}개로 상승 종목 {after_up}개보다 많습니다.")

    if strong_down > 0:
        risk.append(f"시간외 3% 이상 약세 종목이 {strong_down}개 확인됐습니다.")

    if candidate_overheated_count >= 3:
        risk.append(f"관심종목 중 과열 후보가 {candidate_overheated_count}개 확인돼 시초가 추격 매수는 신중해야 합니다.")

    if risk_stock_count >= 5:
        risk.append(f"주의종목이 {risk_stock_count}개 확인돼 장 초반 변동성 관리가 필요합니다.")

    if risk_overheated_count >= 3:
        risk.append(f"주의종목 중 과열 후보가 {risk_overheated_count}개로 많아 단기 급등락에 주의가 필요합니다.")

    if overlap_count >= 1:
        overlap_text = ", ".join(overlap_names[:3]) if overlap_names else "일부 종목"
        risk.append(f"관심종목과 주의종목이 {overlap_count}개 겹칩니다. {overlap_text} 등은 강세와 과열을 함께 확인해야 합니다.")

    if not positive:
        positive.append("뚜렷한 강한 긍정 신호는 제한적입니다.")

    if not risk:
        risk.append("뚜렷한 위험 신호는 제한적입니다.")

    check_points = [
        "시초가 갭이 과도하게 벌어지는지 확인합니다.",
        "장 초반 거래량이 전일 평균 대비 유지되는지 확인합니다.",
        "외국인·기관 수급이 매수 우위로 전환되는지 확인합니다.",
    ]

    if top_sector:
        check_points.append(f"{top_sector} 섹터의 주도주가 장 초반에도 강세를 유지하는지 확인합니다.")

    if candidate_overheated_count >= 3 or risk_overheated_count >= 3:
        check_points.append("급등 종목은 시초가 이후 첫 10~30분 동안 거래량이 유지되는지 확인합니다.")

    if overlap_count >= 1:
        check_points.append("관심종목과 주의종목에 동시에 포함된 종목은 추격 매수보다 눌림·거래량 확인이 우선입니다.")

    if after_down > after_up:
        check_points.append("시간외 약세 종목이 정규장 초반에도 하락을 이어가는지 확인합니다.")

    if negative_dart > 0:
        check_points.append("주의 공시가 나온 종목은 장 초반 급등락 여부를 별도로 확인합니다.")

    return positive[:9], risk[:9], check_points[:7]


def build_sector_strategy(sector_results: Optional[List[Dict[str, Any]]]) -> str:
    if not sector_results:
        return "핵심 섹터 신호가 제한적입니다."

    names: List[str] = []

    for item in sector_results[:3]:
        sector = str(item.get("sector", "") or "")
        if sector:
            names.append(sector)

    if not names:
        return "핵심 섹터 신호가 제한적입니다."

    if len(names) == 1:
        return f"{names[0]} 중심으로 우선 점검합니다."

    return f"{' / '.join(names)} 순서로 우선 점검합니다."


def _indicator_score(indicators: List[Dict[str, Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    reasons: List[str] = []
    signals: Dict[str, Any] = {}

    for item in indicators or []:
        name = str(item.get("name", "") or "")
        symbol = str(item.get("symbol", "") or "")
        change = _safe_float(item.get("change_rate"))

        key = f"{name}({symbol})" if symbol else name
        signals[key] = change

        if name in ["나스닥", "엔비디아", "마이크로소프트"]:
            if change >= 1.0:
                score += 8
                reasons.append(f"{name} 강세({_fmt_pct(change)})로 성장주·AI 투자심리에 우호적")
            elif change <= -1.0:
                score -= 8
                reasons.append(f"{name} 약세({_fmt_pct(change)})로 성장주·AI 투자심리에 부담")
            elif change > 0:
                score += 3
            elif change < 0:
                score -= 3

        elif name == "S&P500":
            if change >= 0.7:
                score += 5
                reasons.append(f"S&P500 상승({_fmt_pct(change)})으로 위험자산 선호 개선")
            elif change <= -0.7:
                score -= 5
                reasons.append(f"S&P500 하락({_fmt_pct(change)})으로 위험자산 선호 약화")

        elif name == "달러/원":
            if change >= 0.7:
                score -= 5
                reasons.append(f"달러/원 상승({_fmt_pct(change)})으로 외국인 수급 부담 가능성")
            elif change <= -0.5:
                score += 4
                reasons.append(f"달러/원 하락({_fmt_pct(change)})으로 외국인 수급 여건 개선 가능성")

        elif name == "WTI유가":
            if change >= 2.0:
                score -= 3
                reasons.append(f"유가 상승({_fmt_pct(change)})으로 비용 부담 업종 주의")
            elif change <= -2.0:
                score += 2
                reasons.append(f"유가 하락({_fmt_pct(change)})으로 비용 부담 완화 가능성")

        elif name == "테슬라":
            if change >= 1.0:
                score += 4
                reasons.append(f"테슬라 강세({_fmt_pct(change)})로 2차전지·전기차 심리 개선 가능성")
            elif change <= -1.0:
                score -= 4
                reasons.append(f"테슬라 약세({_fmt_pct(change)})로 2차전지·전기차 심리 부담")

    return score, reasons[:8], signals


def _news_score(news_items: List[Any]) -> tuple[float, List[str], Dict[str, Any]]:
    positive_keywords = [
        "AI", "인공지능", "투자", "수주", "공급계약", "계약", "실적", "흑자", "증익",
        "반등", "상승", "호조", "수출", "완화", "확대", "협력", "엔비디아", "HBM",
    ]

    negative_keywords = [
        "관세", "분쟁", "전쟁", "금리", "인플레이션", "하락", "침체", "둔화",
        "규제", "적자", "손실", "소송", "리콜", "제재", "불확실성",
    ]

    pos = 0
    neg = 0

    for item in news_items or []:
        text = _news_text(item)

        if any(k in text for k in positive_keywords):
            pos += 1

        if any(k in text for k in negative_keywords):
            neg += 1

    score = min(pos * 1.2, 10) - min(neg * 1.2, 10)

    reasons: List[str] = []

    if pos:
        reasons.append(f"긍정 뉴스 키워드 {pos}건 감지")

    if neg:
        reasons.append(f"주의 뉴스 키워드 {neg}건 감지")

    return score, reasons, {
        "positive_news_count": pos,
        "negative_news_count": neg,
    }


def _after_hours_score(after_hours_data: Optional[List[Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    score = 0.0
    up = 0
    down = 0
    strong_up = 0
    strong_down = 0

    for item in after_hours_data or []:
        d = _item_to_dict(item)

        change = _safe_float(
            d.get("after_change_pct")
            or d.get("after_hours_change_rate")
            or d.get("change_rate")
            or d.get("after_change")
            or d.get("등락률")
            or 0
        )

        if change > 0:
            up += 1
            score += min(change * 0.8, 4)

            if change >= 3:
                strong_up += 1

        elif change < 0:
            down += 1
            score -= min(abs(change) * 0.8, 4)

            if change <= -3:
                strong_down += 1

    reasons: List[str] = []

    if up or down:
        reasons.append(f"시간외 상승 {up}개·하락 {down}개 감지")

    if strong_up:
        reasons.append(f"시간외 3% 이상 강세 종목 {strong_up}개")

    if strong_down:
        reasons.append(f"시간외 3% 이상 약세 종목 {strong_down}개")

    return score, reasons, {
        "after_hours_up": up,
        "after_hours_down": down,
        "after_hours_strong_up": strong_up,
        "after_hours_strong_down": strong_down,
    }


def _dart_score(dart_items: Optional[List[Any]]) -> tuple[float, List[str], Dict[str, Any]]:
    positive_keywords = [
        "공급계약", "수주", "자사주", "소각", "배당",
        "신규시설투자", "실적", "영업이익",
    ]

    negative_keywords = [
        "유상증자", "전환사채", "CB", "BW",
        "불성실공시", "소송", "적자", "영업손실",
    ]

    pos = 0
    neg = 0

    for item in dart_items or []:
        d = _item_to_dict(item)
        text = " ".join(str(v) for v in d.values())

        if any(k in text for k in positive_keywords):
            pos += 1

        if any(k in text for k in negative_keywords):
            neg += 1

    score = min(pos * 2.0, 6) - min(neg * 2.5, 8)

    reasons: List[str] = []

    if pos:
        reasons.append(f"긍정 공시 키워드 {pos}건 감지")

    if neg:
        reasons.append(f"주의 공시 키워드 {neg}건 감지")

    return score, reasons, {
        "positive_dart_count": pos,
        "negative_dart_count": neg,
    }


def _sector_score(sector_results: Optional[List[Dict[str, Any]]]) -> tuple[float, List[str], Dict[str, Any]]:
    if not sector_results:
        return 0.0, [], {"top_sector": None, "top_sector_score": 0.0}

    top = sector_results[0]
    top_score = _safe_float(top.get("score"))
    sector_name = str(top.get("sector", "") or "")

    score = min(top_score * 0.08, 8)

    reasons: List[str] = []

    if sector_name:
        reasons.append(f"강세 예상 섹터 상위: {sector_name}({top_score:.1f}점)")

    return score, reasons, {
        "top_sector": sector_name,
        "top_sector_score": top_score,
    }


def build_market_decision(
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
    candidate_scores: Optional[List[Any]] = None,
    candidates: Optional[List[Any]] = None,
    risks: Optional[List[Any]] = None,
) -> MarketDecision:
    base = 60.0
    total = base

    reasons: List[str] = []
    signals: Dict[str, Any] = {"base_score": base}

    score_blocks = [
        _indicator_score(indicators),
        _news_score(news_items),
        _after_hours_score(after_hours_data),
        _dart_score(dart_items),
        _sector_score(sector_results),
        _candidate_quality_score(candidate_scores, candidates),
        _risk_stock_score(risks),
        _overlap_score(candidate_scores, candidates, risks),
    ]

    for score_part, part_reasons, part_signals in score_blocks:
        total += score_part
        reasons.extend(part_reasons)
        signals.update(part_signals)

    total = _apply_score_cap(total, signals, reasons)

    stars = score_to_stars(total)
    sentiment, sentiment_badge = classify_market(total)

    strategy, strategy_comment, cash_ratio, buy_ratio, strategy_reasons = decide_ai_strategy(
        score=total,
        signals=signals,
    )

    positive_reasons, risk_reasons, check_points = build_strategy_details(signals)

    sector_strategy = build_sector_strategy(sector_results)

    top_sector = signals.get("top_sector")

    if top_sector:
        summary = (
            f"오늘 시장은 {sentiment}({stars})로 판단됩니다. "
            f"{top_sector} 중심의 흐름을 우선 점검하되, "
            f"과열 종목은 시초가와 거래량 확인 후 접근할 필요가 있습니다.\n\n"
            f"전략: {strategy}. {strategy_comment}"
        )
    else:
        summary = (
            f"오늘 시장은 {sentiment}({stars})로 판단됩니다. "
            f"장 초반 가격·거래량·수급 확인이 필요합니다.\n\n"
            f"전략: {strategy}. {strategy_comment}"
        )

    signals["sentiment_badge"] = sentiment_badge
    signals["cash_ratio"] = cash_ratio
    signals["buy_ratio"] = buy_ratio
    signals["sector_strategy"] = sector_strategy

    if not reasons:
        reasons.append("뚜렷한 방향성 신호가 제한적이어서 장 초반 확인이 필요합니다.")

    return MarketDecision(
        score=total,
        stars=stars,
        sentiment=sentiment,
        strategy=strategy,
        strategy_comment=strategy_comment,
        cash_ratio=cash_ratio,
        buy_ratio=buy_ratio,
        sector_strategy=sector_strategy,
        summary=summary,
        reasons=reasons[:12],
        strategy_reasons=strategy_reasons[:6],
        positive_reasons=positive_reasons[:9],
        risk_reasons=risk_reasons[:9],
        check_points=check_points[:7],
        signals=signals,
    )


def format_market_decision(decision: Optional[MarketDecision]) -> str:
    if decision is None:
        return "- 시장 판단 결과가 없습니다."

    lines = [
        f"### 오늘 시장 판단: {decision.sentiment} {decision.stars}",
        f"- 종합점수: {decision.score}/100",
        f"- 전략: {decision.strategy}",
        f"- 현금비중: {decision.cash_ratio}%",
        f"- 매수비중: {decision.buy_ratio}%",
        f"- 섹터전략: {decision.sector_strategy}",
        f"- 요약: {decision.summary}",
    ]

    if decision.positive_reasons:
        lines.append("")
        lines.append(f"- 긍정요인: {score_to_stars(decision.score)}")
        for r in decision.positive_reasons[:6]:
            lines.append(f"  - {r}")

    if decision.risk_reasons:
        lines.append("")
        lines.append("- 위험요인:")
        for r in decision.risk_reasons[:6]:
            lines.append(f"  - {r}")

    if decision.check_points:
        lines.append("")
        lines.append("- 장 시작 후 확인:")
        for r in decision.check_points[:6]:
            lines.append(f"  - {r}")

    if decision.strategy_reasons:
        lines.append("")
        lines.append("- 전략 근거:")
        for r in decision.strategy_reasons[:6]:
            lines.append(f"  - {r}")

    if decision.reasons:
        lines.append("")
        lines.append("- 주요 근거:")
        for r in decision.reasons[:8]:
            lines.append(f"  - {r}")

    return "\n".join(lines)