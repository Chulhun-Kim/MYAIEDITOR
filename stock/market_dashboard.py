# stock/market_dashboard.py
# ------------------------------------------------------------
# MYAIEDITOR 장전 Dashboard v1.7
# - 시장 판단
# - 시장 점수 Progress Bar
# - 관심/주의 종목 요약
# - 시간외·DART·섹터 요약
# - v1.7: 관심 종목 TOP에 AI 추천 근거 표시
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
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

    if hasattr(item, "__dict__"):
        try:
            return dict(item.__dict__)
        except Exception:
            pass

    return {}


def _get_attr(obj: Any, key: str, default: Any = "") -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text_progress_bar(score: float, blocks: int = 10) -> str:
    """
    시장점수를 텍스트 Progress Bar로 변환한다.
    예: 75.4점 -> ████████░░
    """
    score = max(0.0, min(float(score or 0), 100.0))
    filled = round((score / 100.0) * blocks)
    empty = blocks - filled
    return "█" * filled + "░" * empty


def _format_recommend_reasons(item: Any, limit: int = 2) -> str:
    """
    v1.7 AI 추천 근거 요약.
    candidate_score.py의 recommend_reasons를 우선 사용한다.
    없을 경우 기존 reasons에서 화면용 근거를 보조 추출한다.
    """
    recommend_reasons = _get_attr(item, "recommend_reasons", []) or []

    if isinstance(recommend_reasons, str):
        recommend_reasons = [recommend_reasons]

    clean: List[str] = []
    for reason in recommend_reasons:
        text = str(reason or "").strip()
        if text and text not in clean:
            clean.append(text)

    if not clean:
        fallback_reasons = _get_attr(item, "reasons", []) or []
        if isinstance(fallback_reasons, str):
            fallback_reasons = [fallback_reasons]

        skip_keywords = [
            "기본점수",
            "압축",
            "100점 포화",
            "AI 판단",
            "위험도",
            "상한",
        ]

        for reason in fallback_reasons:
            text = str(reason or "").strip()
            if not text:
                continue
            if any(kw in text for kw in skip_keywords):
                continue
            if text not in clean:
                clean.append(text)
            if len(clean) >= limit:
                break

    return " · ".join(clean[:limit]) if clean else "-"


def _names_from_candidates(items: Optional[List[Any]], limit: int = 3) -> str:
    rows: List[str] = []
    numbers = ["①", "②", "③", "④", "⑤"]

    for idx, item in enumerate(items or []):
        if idx >= limit:
            break

        name = _get_attr(item, "name", "")
        ticker = _get_attr(item, "ticker", "")

        if name and ticker:
            rows.append(f"{numbers[idx]} {name} ({ticker})")
        elif name:
            rows.append(f"{numbers[idx]} {name}")

    return "\n\n".join(rows) if rows else "-"


def _names_with_reasons_from_candidates(items: Optional[List[Any]], limit: int = 3) -> str:
    """
    v1.7 Dashboard TOP용 표시.
    종목명 아래에 AI판단과 AI 추천 근거를 함께 보여준다.
    """
    rows: List[str] = []
    numbers = ["①", "②", "③", "④", "⑤"]

    for idx, item in enumerate(items or []):
        if idx >= limit:
            break

        name = _get_attr(item, "name", "")
        ticker = _get_attr(item, "ticker", "")
        stars = _get_attr(item, "stars", "")
        action_label = _get_attr(item, "action_label", "")
        reason_text = _format_recommend_reasons(item, limit=2)

        if name and ticker:
            title = f"{numbers[idx]} {name} ({ticker})"
        elif name:
            title = f"{numbers[idx]} {name}"
        else:
            continue

        sub_parts = []
        if stars:
            sub_parts.append(str(stars))
        if action_label:
            sub_parts.append(str(action_label))

        if sub_parts:
            rows.append(f"{title}  \n{' '.join(sub_parts)}  \n추천 근거: {reason_text}")
        else:
            rows.append(f"{title}  \n추천 근거: {reason_text}")

    return "\n\n".join(rows) if rows else "-"


def _sector_names(sector_results: Optional[List[Dict[str, Any]]], limit: int = 3) -> str:
    names: List[str] = []

    for item in sector_results or []:
        sector = item.get("sector", "")
        if sector:
            names.append(str(sector))

        if len(names) >= limit:
            break

    return " / ".join(names) if names else "-"


def _after_hours_summary(after_hours_data: Optional[List[Any]]) -> str:
    up = 0
    down = 0

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
        elif change < 0:
            down += 1

    return f"▲ {up} / ▼ {down}"


def _sentiment_badge(sentiment: str) -> str:
    sentiment = str(sentiment or "")

    if "매우 강세" in sentiment:
        return "🟢 매우 강세"
    if "강세" in sentiment:
        return "🟢 강세"
    if "중립" in sentiment:
        return "🟡 중립"
    if "약세" in sentiment:
        return "🔴 약세"

    return sentiment or "🟡 중립"


def render_market_dashboard(
    market_decision: Any,
    candidate_scores: Optional[List[Any]] = None,
    risks: Optional[List[Any]] = None,
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
    news_items: Optional[List[Any]] = None,
) -> None:
    """
    장전 분석 결과 상단 Dashboard를 출력한다.
    """

    score = _safe_float(_get_attr(market_decision, "score", 0))
    progress_value = max(0.0, min(score / 100.0, 1.0))

    sentiment = _get_attr(market_decision, "sentiment", "중립")
    stars = _get_attr(market_decision, "stars", "")
    strategy = _get_attr(market_decision, "strategy", "")
    summary = _get_attr(market_decision, "summary", "")
    reasons = _get_attr(market_decision, "reasons", []) or []

    candidate_count = len(candidate_scores or [])
    risk_count = len(risks or [])
    dart_count = len(dart_items or [])
    news_count = len(news_items or [])

    st.markdown("## 🧭 장전 Dashboard")

    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1])

    with c1:
        st.caption("시장 판단")
        st.markdown(f"### {_sentiment_badge(sentiment)}")

    with c2:
        st.markdown(f"### {score:.1f} / 100")
        st.progress(progress_value)
        st.caption(f"{score:.1f}%")

    with c3:
        st.caption("관심 종목")
        st.markdown(f"### {candidate_count}")

    with c4:
        st.caption("주의 종목")
        st.markdown(f"### {risk_count}")

    with c5:
        st.caption("시간외")
        st.markdown(f"### {_after_hours_summary(after_hours_data)}")

    st.markdown(f"**관심도:** {stars}")

    if summary or strategy:
        st.info(
            f"{summary}\n\n"
            f"전략: {strategy}"
        )

    c6, c7, c8 = st.columns(3)

    with c6:
        st.markdown("**핵심 섹터**")
        st.write(_sector_names(sector_results))

    with c7:
        st.markdown("**관심 종목 TOP**")
        st.markdown(_names_with_reasons_from_candidates(candidate_scores), unsafe_allow_html=False)

    with c8:
        st.markdown("**주의 종목 TOP**")
        st.markdown(_names_from_candidates(risks))

    with st.expander("Dashboard 상세 요약", expanded=False):
        st.markdown(f"- 시장 판단: {_sentiment_badge(sentiment)}")
        st.markdown(f"- 시장 점수: {score:.1f}/100")
        st.markdown(f"- 관심 종목 수: {candidate_count}")
        st.markdown(f"- 주의 종목 수: {risk_count}")
        st.markdown(f"- 시간외: {_after_hours_summary(after_hours_data)}")
        st.markdown(f"- DART 공시: {dart_count}건")
        st.markdown(f"- 수집 뉴스: {news_count}건")

        if candidate_scores:
            st.markdown("#### 관심 종목 AI 추천 근거")
            for item in candidate_scores[:5]:
                name = _get_attr(item, "name", "")
                ticker = _get_attr(item, "ticker", "")
                reason_text = _format_recommend_reasons(item, limit=3)

                if name and ticker:
                    st.markdown(f"- **{name}({ticker})**: {reason_text}")
                elif name:
                    st.markdown(f"- **{name}**: {reason_text}")

        if reasons:
            st.markdown("#### 판단 근거")
            for reason in reasons:
                st.markdown(f"- {reason}")
