# stock/narrative_builder.py
# ------------------------------------------------------------
# MYAIEDITOR v2.0 Narrative Builder
# ------------------------------------------------------------
# 역할:
# - CandidateScore / dict 형태의 관심 종목 데이터를 받아
#   사람이 읽기 쉬운 'AI 종합 분석 문단'을 생성한다.
# - 점수 계산은 하지 않는다.
# - candidate_score.py, reason_ranker.py, company_profile.py가 만든
#   recommend_reasons / signals / reasons를 설명 문장으로 재구성한다.
# - Dashboard, Workspace, 장전 브리핑에서 재사용할 수 있다.
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CandidateNarrative:
    """종목별 AI 설명 결과."""

    name: str
    ticker: str
    title: str
    summary: str
    strengths: List[str]
    risks: List[str]
    action: str
    watch_points: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------
# 기본 유틸
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


def _fmt_pct(value: Any) -> str:
    return f"{_safe_float(value):+.2f}%"


def _dedupe(items: List[str], limit: Optional[int] = None) -> List[str]:
    out: List[str] = []
    seen = set()

    for item in items or []:
        text = _clean(item)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if limit is not None and len(out) >= limit:
            break

    return out


def _contains_any(text: str, keywords: List[str]) -> bool:
    low = str(text or "").lower()
    return any(str(k).lower() in low for k in keywords)


# ------------------------------------------------------------
# 신호 추출
# ------------------------------------------------------------

def _get_signals(candidate: Any) -> Dict[str, Any]:
    signals = _field(candidate, "signals", {})
    return signals if isinstance(signals, dict) else {}


def _get_recommend_reasons(candidate: Any) -> List[str]:
    reasons = _field(candidate, "recommend_reasons", []) or []
    if not isinstance(reasons, list):
        return []
    return _dedupe([str(x) for x in reasons], limit=6)


def _get_detail_reasons(candidate: Any) -> List[str]:
    reasons = _field(candidate, "reasons", []) or []
    if not isinstance(reasons, list):
        return []
    return _dedupe([str(x) for x in reasons], limit=8)


def _split_strengths_and_risks(candidate: Any) -> Dict[str, List[str]]:
    """추천 근거와 세부 근거를 강점/위험/확인 포인트로 분류한다."""
    recommend_reasons = _get_recommend_reasons(candidate)
    detail_reasons = _get_detail_reasons(candidate)
    signals = _get_signals(candidate)

    strengths: List[str] = []
    risks: List[str] = []
    watch_points: List[str] = []

    risk_words = [
        "위험", "주의", "약세", "하락", "급락", "과열", "추격", "변동성", "조정", "부담",
    ]
    watch_words = [
        "확인", "점검", "관찰", "유지", "수급", "거래량", "시초가", "갭",
    ]

    for reason in recommend_reasons:
        if _contains_any(reason, risk_words):
            risks.append(reason)
        else:
            strengths.append(reason)

    for reason in detail_reasons:
        if _contains_any(reason, risk_words):
            risks.append(reason)
        elif _contains_any(reason, watch_words):
            watch_points.append(reason)

    company_watch = _clean(signals.get("company_watch", ""))
    if company_watch:
        watch_points.append(company_watch)

    risk_score = _safe_float(_field(candidate, "risk_score", 0))
    risk_level = _clean(_field(candidate, "risk_level", ""))
    if risk_score >= 40:
        risks.append(f"위험도 {risk_score:.1f}점({risk_level or '보통'})으로 장 초반 변동성 관리 필요")

    after_change = _safe_float(signals.get("after_hours_best_change", 0))
    if after_change > 0:
        watch_points.append("시간외 상승이 장 초반 거래량으로 이어지는지 확인")
    elif after_change < 0:
        watch_points.append("시간외 약세 이후 시초가 반등 여부 확인")

    action_label = _clean(_field(candidate, "action_label", "관찰"))
    if action_label in {"추격주의", "눌림목 대기"}:
        risks.append(f"AI판단이 {action_label}로 분류돼 추격 매수보다 가격 확인 우선")

    return {
        "strengths": _dedupe(strengths, limit=5),
        "risks": _dedupe(risks, limit=4),
        "watch_points": _dedupe(watch_points, limit=4),
    }


# ------------------------------------------------------------
# 문장 생성
# ------------------------------------------------------------

def _build_summary_sentence(candidate: Any, strengths: List[str], risks: List[str]) -> str:
    name = _clean(_field(candidate, "name", "")) or "해당 종목"
    action_label = _clean(_field(candidate, "action_label", "관찰")) or "관찰"
    momentum_score = _safe_float(_field(candidate, "momentum_score", _field(candidate, "total_score", 0)))
    risk_score = _safe_float(_field(candidate, "risk_score", 0))

    if strengths:
        main = strengths[0]
    else:
        main = "기본 수급과 가격 흐름"

    second = strengths[1] if len(strengths) >= 2 else "장 초반 수급 확인"

    if risk_score >= 40 or risks:
        return (
            f"{name}은 {main}이 핵심 모멘텀으로 확인되며, {second}도 함께 작용하고 있습니다. "
            f"다만 위험도 {risk_score:.1f}점으로 변동성 관리가 필요해 AI 판단은 '{action_label}'입니다."
        )

    if momentum_score >= 88:
        return (
            f"{name}은 {main}이 뚜렷하고 {second}까지 겹치며 장전 강세 후보로 부각됩니다. "
            f"강세점수 {momentum_score:.1f}점으로 AI 판단은 '{action_label}'입니다."
        )

    return (
        f"{name}은 {main}을 중심으로 관심권에 들어왔으며, {second}를 장 초반 함께 확인할 필요가 있습니다. "
        f"강세점수 {momentum_score:.1f}점 기준 AI 판단은 '{action_label}'입니다."
    )


def _build_action_sentence(candidate: Any, risks: List[str], watch_points: List[str]) -> str:
    action_label = _clean(_field(candidate, "action_label", "관찰")) or "관찰"
    risk_score = _safe_float(_field(candidate, "risk_score", 0))

    if action_label == "적극관찰" and risk_score < 40:
        return "장 시작 직후 시초가 갭이 과도하지 않고 거래량이 유지되는지 확인한 뒤 관심권에서 점검합니다."

    if action_label == "관찰":
        return "시초가와 첫 10~30분 거래량을 확인하면서 섹터 흐름이 유지되는지 점검합니다."

    if action_label == "추격주의":
        return "강세는 인정되지만 과열 위험이 있어 추격보다는 눌림 여부와 거래량 안정성을 먼저 확인합니다."

    if action_label == "눌림목 대기":
        return "단기 변동성이 커진 구간이므로 가격이 진정된 뒤 거래량과 수급 회복 여부를 확인하는 접근이 적절합니다."

    return "현재는 우선 관찰 대상으로 두고, 장 초반 수급과 가격 흐름을 확인한 뒤 판단합니다."


# ------------------------------------------------------------
# Public API
# ------------------------------------------------------------

def build_candidate_narrative(candidate: Any, max_items: int = 4) -> CandidateNarrative:
    """
    CandidateScore 또는 dict를 받아 AI 종합 분석 문단을 만든다.

    Parameters
    ----------
    candidate:
        CandidateScore dataclass 또는 dict.
    max_items:
        strengths/risks/watch_points 최대 표시 개수.

    Returns
    -------
    CandidateNarrative
    """
    name = _clean(_field(candidate, "name", ""))
    ticker = _clean(_field(candidate, "ticker", ""))

    classified = _split_strengths_and_risks(candidate)
    strengths = classified["strengths"][:max_items]
    risks = classified["risks"][:max_items]
    watch_points = classified["watch_points"][:max_items]

    summary = _build_summary_sentence(candidate, strengths, risks)
    action = _build_action_sentence(candidate, risks, watch_points)

    title_name = name or "관심 종목"
    title = f"{title_name} AI 종합 분석"

    return CandidateNarrative(
        name=name,
        ticker=ticker,
        title=title,
        summary=summary,
        strengths=strengths,
        risks=risks,
        action=action,
        watch_points=watch_points,
    )


def build_candidate_story_text(candidate: Any, max_items: int = 4) -> str:
    """Workspace/브리핑에 바로 넣기 좋은 Markdown 문자열을 만든다."""
    narrative = build_candidate_narrative(candidate, max_items=max_items)

    lines: List[str] = []
    lines.append(f"### {narrative.title}")
    lines.append("")
    lines.append(narrative.summary)
    lines.append("")

    if narrative.strengths:
        lines.append("**강점**")
        for item in narrative.strengths:
            lines.append(f"- {item}")
        lines.append("")

    if narrative.risks:
        lines.append("**리스크**")
        for item in narrative.risks:
            lines.append(f"- {item}")
        lines.append("")

    if narrative.watch_points:
        lines.append("**장 시작 후 확인**")
        for item in narrative.watch_points:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("**대응 기준**")
    lines.append(f"- {narrative.action}")

    return "\n".join(lines).strip()


def build_top_candidate_stories(candidates: List[Any], limit: int = 5) -> List[Dict[str, Any]]:
    """상위 후보 여러 개에 대한 narrative dict 목록을 반환한다."""
    out: List[Dict[str, Any]] = []

    for item in (candidates or [])[: int(limit)]:
        try:
            out.append(build_candidate_narrative(item).to_dict())
        except Exception:
            continue

    return out


if __name__ == "__main__":
    # 간단한 로컬 테스트용 샘플
    sample = {
        "ticker": "005930",
        "name": "삼성전자",
        "momentum_score": 96.0,
        "risk_score": 23.0,
        "risk_level": "낮음",
        "action_label": "적극관찰",
        "recommend_reasons": [
            "시간외 +3.05% 상승",
            "반도체·AI 섹터 강세",
            "전일 +8.22% 상승",
        ],
        "reasons": [
            "거래대금 대형주급 유동성",
            "시간외 상승이 장 초반 거래량으로 이어지는지 확인",
        ],
        "signals": {
            "after_hours_best_change": 3.05,
            "company_watch": "HBM·메모리 업황과 외국인 수급 확인",
        },
    }

    print(build_candidate_story_text(sample))


# ------------------------------------------------------------
# Backward compatibility (v2.0)
# ------------------------------------------------------------
def build_narrative(
    candidate_name: str = "",
    recommend_reasons=None,
    signals=None,
    candidate=None,
) -> str:
    """
    Legacy wrapper used by workspace_builder.py / ai_prompt.py.
    Returns a plain narrative string.
    """
    if candidate is not None:
        try:
            return build_candidate_narrative(candidate).summary
        except Exception:
            pass

    recommend_reasons = recommend_reasons or []
    signals = signals or {}

    parts=[]
    if candidate_name:
        parts.append(f"{candidate_name}은")
    if recommend_reasons:
        parts.append(" / ".join(recommend_reasons[:2]))
    ah = signals.get("after_hours_best_change")
    try:
        if ah is not None:
            parts.append(f"시간외 {float(ah):+.2f}%")
    except Exception:
        pass
    if not parts:
        return "장 초반 거래량과 수급을 함께 확인하는 전략이 적절합니다."
    return " ".join(parts) + "을 중심으로 장 초반 거래량과 수급 확인이 필요합니다."
