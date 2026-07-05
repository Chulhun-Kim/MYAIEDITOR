# stock/ai_prompt.py
# ------------------------------------------------------------
# MYAIEDITOR OpenAI 장전 프롬프트 모듈 v1.7
# - GPT 호출 및 프롬프트 생성 로직을 app_stock.py에서 분리
# - AI Strategy Engine 결과를 장전 브리핑 최상단에 반영
# - v1.7: candidate_score.py의 recommend_reasons를 AI 추천 근거로 우선 반영
# - v1.7: 오늘 매매 관심 종목 TOP5에 추천 이유 / 세부 근거 분리
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import datetime as dt
import os

import streamlit as st

from stock.dart_api import format_dart_section
from stock.premarket_ai import format_after_hours_section
from stock.sector_engine import build_news_keywords_summary

try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    OpenAI = None
    HAS_OPENAI = False


def _now_kst() -> dt.datetime:
    return dt.datetime.now(ZoneInfo("Asia/Seoul"))


def _today_str() -> str:
    return _now_kst().strftime("%Y-%m-%d")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _fmt_num(n: float) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n)


def _fmt_pct(x: float) -> str:
    return f"{x:+.2f}%"


def _fmt_ratio(x: float) -> str:
    if x <= 0:
        return "-"
    return f"{x:.2f}배"


def get_secret_or_env(key: str, default: str = "") -> str:
    try:
        value = st.secrets.get(key, "")
    except Exception:
        value = ""
    return str(value or os.getenv(key, default) or "").strip()


def _news_field(n: Any, key: str) -> str:
    if isinstance(n, dict):
        return str(n.get(key, "") or "")
    return str(getattr(n, key, "") or "")


def _obj_field(obj: Any, key: str, default: Any = "") -> Any:
    """
    dict, dataclass, 일반 객체를 모두 같은 방식으로 읽기 위한 안전 접근자.
    CandidateScore / StockPick / dict가 섞여 들어와도 프롬프트가 깨지지 않게 한다.
    """
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return obj.to_dict().get(key, default)
        except Exception:
            pass

    return getattr(obj, key, default)


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    return []


def _recommend_reasons(obj: Any) -> List[str]:
    """
    v1.7 핵심 필드.
    candidate_score.py에서 생성한 recommend_reasons를 우선 사용한다.
    없으면 기존 reasons를 fallback으로 사용해 하위 호환성을 유지한다.
    """
    reasons = _as_list(_obj_field(obj, "recommend_reasons", []))
    if not reasons:
        reasons = _as_list(_obj_field(obj, "ai_recommend_reasons", []))
    if not reasons:
        reasons = _as_list(_obj_field(obj, "recommendation_reasons", []))

    clean: List[str] = []
    for r in reasons:
        s = str(r or "").strip()
        if s and s not in clean:
            clean.append(s)

    return clean


def _detail_reasons(obj: Any) -> List[str]:
    reasons = _as_list(_obj_field(obj, "reasons", []))
    clean: List[str] = []
    for r in reasons:
        s = str(r or "").strip()
        if s and s not in clean:
            clean.append(s)
    return clean


def _format_reason_inline(items: List[str], limit: int = 5) -> str:
    items = [str(x).strip() for x in items if str(x or "").strip()]
    return "; ".join(items[:limit]) if items else "별도 추천 근거 없음"


def _decision_field(decision: Any, key: str, default: Any = "") -> Any:
    if decision is None:
        return default

    if isinstance(decision, dict):
        return decision.get(key, default)

    if hasattr(decision, "to_dict") and callable(getattr(decision, "to_dict")):
        try:
            return decision.to_dict().get(key, default)
        except Exception:
            pass

    return getattr(decision, key, default)


def _append_bullets(lines: List[str], title: str, items: List[Any], limit: int = 8) -> None:
    if not items:
        return

    lines.append(title)
    for item in items[:limit]:
        lines.append(f"  - {item}")


def format_market_decision_input(market_decision: Any) -> str:
    """
    market_decision.py의 AI Strategy Engine 결과를
    GPT 프롬프트 입력 자료로 변환한다.
    """

    if market_decision is None:
        return "[오늘 시장 판단]\n- 없음"

    score = _decision_field(market_decision, "score", "")
    stars = _decision_field(market_decision, "stars", "")
    sentiment = _decision_field(market_decision, "sentiment", "")
    strategy = _decision_field(market_decision, "strategy", "")
    strategy_comment = _decision_field(market_decision, "strategy_comment", "")
    cash_ratio = _decision_field(market_decision, "cash_ratio", "")
    buy_ratio = _decision_field(market_decision, "buy_ratio", "")
    sector_strategy = _decision_field(market_decision, "sector_strategy", "")
    summary = _decision_field(market_decision, "summary", "")
    reasons = _decision_field(market_decision, "reasons", []) or []
    strategy_reasons = _decision_field(market_decision, "strategy_reasons", []) or []

    # v1.4 추가
    positive_reasons = _decision_field(market_decision, "positive_reasons", []) or []
    risk_reasons = _decision_field(market_decision, "risk_reasons", []) or []
    check_points = _decision_field(market_decision, "check_points", []) or []

    lines = ["[오늘 시장 판단 / AI Strategy Engine]"]

    lines.append(f"- 시장판단: {sentiment}")
    lines.append(f"- 관심도: {stars}")
    lines.append(f"- 종합점수: {score}/100")

    if strategy:
        lines.append(f"- AI 전략: {strategy}")

    if strategy_comment:
        lines.append(f"- 전략 코멘트: {strategy_comment}")

    if cash_ratio != "":
        lines.append(f"- 권장 현금비중: {cash_ratio}%")

    if buy_ratio != "":
        lines.append(f"- 권장 매수비중: {buy_ratio}%")

    if sector_strategy:
        lines.append(f"- 섹터전략: {sector_strategy}")

    if summary:
        lines.append(f"- 요약: {summary}")

    if positive_reasons:
        _append_bullets(lines, "- 긍정요인:", positive_reasons, limit=8)

    if risk_reasons:
        _append_bullets(lines, "- 위험요인:", risk_reasons, limit=8)

    if check_points:
        _append_bullets(lines, "- 장 시작 후 확인:", check_points, limit=6)

    if strategy_reasons:
        _append_bullets(lines, "- 전략 근거:", strategy_reasons, limit=5)

    if reasons:
        _append_bullets(lines, "- 판단 근거:", reasons, limit=8)

    return "\n".join(lines)


def build_ai_input_text(
    latest_date: str,
    markets: List[str],
    candidates: List[Any],
    risks: List[Any],
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    sector_results: List[Dict[str, Any]],
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    candidate_scores: Optional[List[Any]] = None,
    market_decision: Optional[Any] = None,
    market_story: Optional[Dict[str, Any]] = None,
) -> str:
    parts: List[str] = []

    parts.append(f"[브리핑 기준시각] {_today_str()} 07:00")
    parts.append(f"[국내시장 가격 기준일] {latest_date}")
    parts.append(f"[분석 시장] {', '.join(markets) if markets else '사용자 입력'}")
    parts.append("")

    parts.append(format_market_decision_input(market_decision))
    parts.append("")

    if market_story:
        parts.append("[오늘 시장 스토리]")
        if market_story.get("headline"):
            parts.append(f"- 제목: {market_story['headline']}")
        if market_story.get("summary"):
            parts.append(f"- 요약: {market_story['summary']}")
        for x in market_story.get("flow", []):
            parts.append(f"  - {x}")
        if market_story.get("drivers"):
            parts.append("- 핵심 동인:")
            for x in market_story.get("drivers", [])[:5]:
                parts.append(f"  - {x}")
        if market_story.get("risks"):
            parts.append("- 리스크:")
            for x in market_story.get("risks", [])[:5]:
                parts.append(f"  - {x}")
        if market_story.get("watch_points"):
            parts.append("- 장 시작 체크포인트:")
            for x in market_story.get("watch_points", [])[:5]:
                parts.append(f"  - {x}")
        parts.append("")

    parts.append("[해외시장·거시지표]")
    if indicators:
        for it in indicators:
            name = it.get("name", "")
            symbol = it.get("symbol", "")
            last = _safe_float(it.get("last"))
            change_rate = _safe_float(it.get("change_rate"))
            date = it.get("date", "")
            memo = it.get("memo", "")

            parts.append(
                f"- {name}({symbol}): {last:.2f}, "
                f"전일 대비 {_fmt_pct(change_rate)} / 기준일 {date} / 영향 변수: {memo}"
            )
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[거시지표 해석 가이드]")
    parts.append("- 나스닥·S&P500 상승: 한국 성장주, 반도체, 인터넷, 2차전지 투자심리에 우호적일 수 있음")
    parts.append("- 엔비디아 상승: 반도체, AI, HBM, 반도체 장비·소재 종목 관심 확대 가능성")
    parts.append("- 테슬라 상승: 2차전지, 전기차, 자동차 밸류체인 관심 확대 가능성")
    parts.append("- 달러/원 상승: 수출주에는 일부 우호적일 수 있으나 외국인 수급에는 부담이 될 수 있음")
    parts.append("- 유가 상승: 정유·조선·에너지에는 우호적일 수 있고 항공·화학에는 비용 부담 요인이 될 수 있음")
    parts.append("- 미국 기술주 약세 또는 금리 부담: 성장주·바이오·2차전지에는 부담 요인이 될 수 있음")
    parts.append("")

    parts.append(format_after_hours_section(after_hours_data or []))
    parts.append("")

    parts.append(format_dart_section(dart_items or []))
    parts.append("")

    parts.append("[장전 주요 뉴스]")
    if news_items:
        for i, n in enumerate(news_items[:15], start=1):
            parts.append(
                f"- {i}. {_news_field(n, 'title')} / "
                f"{_news_field(n, 'source')} / "
                f"{_news_field(n, 'published')}"
            )
            desc = _news_field(n, "description")
            if desc:
                parts.append(f"  요약: {desc}")
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[강세 예상 섹터]")
    if sector_results:
        for s in sector_results:
            parts.append(
                f"- {s['sector']} / 점수 {s['score']} / "
                f"관련종목: {', '.join(s['stocks'])}"
            )
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[최종 관심도 엔진 결과 / v1.7 AI 추천 근거]")
    if candidate_scores:
        for i, p in enumerate(candidate_scores, start=1):
            name = _obj_field(p, "name", "")
            ticker = _obj_field(p, "ticker", "")
            market = _obj_field(p, "market", "")
            base_score = _obj_field(p, "base_score", "")
            total_score = _obj_field(p, "total_score", _obj_field(p, "momentum_score", ""))
            stars = _obj_field(p, "stars", "")
            action_label = _obj_field(p, "action_label", "관찰")
            risk_score = _obj_field(p, "risk_score", "")
            risk_level = _obj_field(p, "risk_level", "")
            recommend_reasons = _recommend_reasons(p)
            detail_reasons = _detail_reasons(p)

            parts.append(
                f"- {i}. {name}({ticker}) {market} / "
                f"기존점수 {base_score} / 최종점수 {total_score} / 관심도 {stars} / "
                f"AI판단 {action_label} / 위험도 {risk_score}({risk_level})"
            )
            parts.append(f"  AI추천근거: {_format_reason_inline(recommend_reasons, limit=5)}")
            narrative = _obj_field(p, "narrative_text", "")
            if narrative:
                parts.append(f"  AI종합분석: {narrative}")
            if detail_reasons:
                parts.append(f"  세부근거: {_format_reason_inline(detail_reasons, limit=7)}")
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[시스템 점수 기반 매매 관심 후보]")
    if candidates:
        for i, p in enumerate(candidates, start=1):
            parts.append(
                f"- {i}. {p.name}({p.ticker}) {p.market} / 점수 {p.score} / "
                f"직전 거래일 등락률 {_fmt_pct(p.change_rate)} / "
                f"거래량배율 {_fmt_ratio(p.volume_ratio)} / "
                f"추정거래대금 {_fmt_num(p.trading_value_est)}원 / "
                f"뉴스언급 {p.news_hits}건 / 근거: {'; '.join(p.reasons)}"
            )
    else:
        parts.append("- 없음")
    parts.append("")

    parts.append("[시스템 점수 기반 주의 후보]")
    if risks:
        for i, p in enumerate(risks, start=1):
            parts.append(
                f"- {i}. {p.name}({p.ticker}) {p.market} / 점수 {p.score} / "
                f"직전 거래일 등락률 {_fmt_pct(p.change_rate)} / "
                f"거래량배율 {_fmt_ratio(p.volume_ratio)} / "
                f"추정거래대금 {_fmt_num(p.trading_value_est)}원 / "
                f"근거: {'; '.join(p.reasons)}"
            )
    else:
        parts.append("- 없음")

    return "\n".join(parts).strip()


def rule_based_ai_brief(
    candidates: List[Any],
    risks: List[Any],
    news_items: List[Any],
    market_decision: Optional[Any] = None,
    candidate_scores: Optional[List[Any]] = None,
) -> str:
    lines: List[str] = []

    if market_decision is not None:
        score = _decision_field(market_decision, "score", "")
        stars = _decision_field(market_decision, "stars", "")
        sentiment = _decision_field(market_decision, "sentiment", "")
        strategy = _decision_field(market_decision, "strategy", "")
        strategy_comment = _decision_field(market_decision, "strategy_comment", "")
        cash_ratio = _decision_field(market_decision, "cash_ratio", "")
        buy_ratio = _decision_field(market_decision, "buy_ratio", "")
        sector_strategy = _decision_field(market_decision, "sector_strategy", "")
        strategy_reasons = _decision_field(market_decision, "strategy_reasons", []) or []

        # v1.4 추가
        positive_reasons = _decision_field(market_decision, "positive_reasons", []) or []
        risk_reasons = _decision_field(market_decision, "risk_reasons", []) or []
        check_points = _decision_field(market_decision, "check_points", []) or []

        lines.append("## ① AI 투자 전략")
        lines.append("")
        lines.append(f"### {stars}")
        lines.append("")
        lines.append(f"### {strategy}")
        lines.append("")
        lines.append(f"- 시장 판단: {sentiment}")
        lines.append(f"- 시장 점수: {score}/100")

        if cash_ratio != "":
            lines.append(f"- 현금 비중: {cash_ratio}%")

        if buy_ratio != "":
            lines.append(f"- 매수 비중: {buy_ratio}%")

        if sector_strategy:
            lines.append(f"- 핵심 섹터 전략: {sector_strategy}")

        if strategy_comment:
            lines.append(f"- 전략 코멘트: {strategy_comment}")

        if positive_reasons:
            lines.append("")
            lines.append("### 긍정요인")
            for r in positive_reasons[:8]:
                lines.append(f"- {r}")

        if risk_reasons:
            lines.append("")
            lines.append("### 위험요인")
            for r in risk_reasons[:8]:
                lines.append(f"- {r}")

        if check_points:
            lines.append("")
            lines.append("### 장 시작 후 확인")
            for r in check_points[:6]:
                lines.append(f"- {r}")

        if strategy_reasons:
            lines.append("")
            lines.append("### 전략 근거")
            for r in strategy_reasons[:5]:
                lines.append(f"- {r}")

        lines.append("")

    lines.append("## ② 장전 한 줄 결론")
    lines.append("")
    lines.append("- OpenAI 분석을 사용할 수 없어 규칙 기반 요약으로 대체했습니다.")

    keywords = build_news_keywords_summary(news_items)
    if keywords:
        lines.append(f"- 장전 뉴스에서 반복된 키워드는 {', '.join(keywords[:6])}입니다.")

    final_candidates = candidate_scores or candidates

    if final_candidates:
        top_names = ", ".join([
            f"{_obj_field(p, 'name', '')}({_obj_field(p, 'ticker', '')})"
            for p in final_candidates[:5]
        ])
        lines.append(f"- 최종 관심도 엔진 기준 매매 관심 상위 후보는 {top_names}입니다.")

        for p in final_candidates[:5]:
            recommend_reasons = _recommend_reasons(p)
            if recommend_reasons:
                lines.append(
                    f"  - {_obj_field(p, 'name', '')} 추천 이유: "
                    f"{_format_reason_inline(recommend_reasons, limit=3)}"
                )

        lines.append("- 장 시작 직후에는 시초가 갭, 첫 10~30분 거래량, 전일 고점 돌파 여부를 확인하는 방식이 안전합니다.")
    else:
        lines.append("- 시스템 점수 기준 매매 관심 후보가 뚜렷하지 않습니다.")

    if risks:
        risk_names = ", ".join([f"{p.name}({p.ticker})" for p in risks[:5]])
        lines.append(f"- 변동성 주의 후보는 {risk_names}입니다.")

    lines.append("- 이 내용은 투자 권유가 아니라 공개 데이터 기반 장전 체크리스트입니다.")

    return "\n".join(lines)


def generate_ai_preopen_brief(
    latest_date: str,
    markets: List[str],
    candidates: List[Any],
    risks: List[Any],
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    sector_results: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.2,
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    candidate_scores: Optional[List[Any]] = None,
    market_decision: Optional[Any] = None,
    market_story: Optional[Dict[str, Any]] = None,
) -> str:
    api_key = get_secret_or_env("OPENAI_API_KEY")

    if not HAS_OPENAI or not api_key:
        return rule_based_ai_brief(
            candidates=candidates,
            risks=risks,
            news_items=news_items,
            market_decision=market_decision,
            candidate_scores=candidate_scores,
        )

    client = OpenAI(api_key=api_key)

    input_text = build_ai_input_text(
        latest_date=latest_date,
        markets=markets,
        candidates=candidates,
        risks=risks,
        indicators=indicators,
        news_items=news_items,
        sector_results=sector_results,
        after_hours_data=after_hours_data,
        dart_items=dart_items,
        candidate_scores=candidate_scores,
        market_decision=market_decision,
        market_story=market_story,
    )

    ranking_guard = """
[중요 작성 원칙]

1. '오늘 매매 관심 종목 TOP5'는 반드시 최종 관심도 엔진(candidate_scores)의 순서와 내용을 따른다. candidate_scores가 없을 때만 candidates 목록을 따른다.
2. AI가 임의로 종목 순위를 바꾸거나 새로운 종목을 TOP5에 추가하지 않는다.
3. 시간외 거래 종목은 별도의 참고 정보로만 설명한다.
4. 시간외 상승·하락 종목이 candidate_scores 또는 candidates 목록에 없으면 TOP5에 넣지 않는다.
5. '장 시작 후 체크포인트' 항목은 별도로 만들지 않는다.
6. '최종 유의사항' 항목도 작성하지 않는다.
7. 장 시작 후 체크포인트와 최종 유의사항은 화면 하단의 고정 템플릿에서 별도로 출력된다.
8. 투자 권유처럼 쓰지 말고, '관심', '점검', '확인', '주의' 표현을 사용한다.
9. 'AI 투자 전략'의 strategy, cash_ratio, buy_ratio, sector_strategy는 market_decision 값을 그대로 사용한다.
10. market_decision의 positive_reasons, risk_reasons, check_points는 제공된 항목을 우선 사용한다.
11. candidate_scores의 AI추천근거(recommend_reasons)를 오늘 매매 관심 종목 TOP5의 '추천 이유'에 우선 사용한다.
12. 기존 reasons는 '세부 근거' 또는 보조 설명으로만 사용하고, 추천 이유보다 앞세우지 않는다.
"""

    output_format = """
[출력 형식]

## ① AI 투자 전략

- market_decision의 stars를 그대로 출력한다.
- market_decision의 strategy를 그대로 출력한다.
- market_decision의 sentiment를 그대로 출력한다.
- market_decision의 score를 그대로 출력한다.
- market_decision의 cash_ratio를 활용해 현금 비중을 제시한다.
- market_decision의 buy_ratio를 활용해 매수 비중을 제시한다.
- market_decision의 sector_strategy를 활용해 오늘 우선 점검할 섹터를 설명한다.
- market_decision의 strategy_comment를 1문장으로 정리한다.
- market_decision의 positive_reasons를 활용해 '긍정요인'을 3~8개 bullet로 작성한다.
- market_decision의 risk_reasons를 활용해 '위험요인'을 1~8개 bullet로 작성한다.
- market_decision의 check_points를 활용해 '장 시작 후 확인'을 3~6개 bullet로 작성한다.
- market_decision의 strategy_reasons는 필요할 경우 '전략 근거'에 보조적으로 반영한다.
- 제공된 근거를 우선 사용하고, 데이터에 없는 사실을 임의로 추가하지 않는다.

## ② 장전 한 줄 결론

- 오늘 시장 판단 결과를 한 문장으로 요약한다.
- market_decision의 sentiment, stars, strategy를 반드시 반영한다.

## ③ 오늘 시장환경

- 오늘 시장 판단: sentiment / score / stars / strategy
- 해외시장 요약
- 환율·유가 영향
- 뉴스 흐름
- 한국시장 예상 분위기

## ④ 시간외 거래 특징

- 시간외 급등 종목
- 시간외 약세 종목
- 다음 장에서 확인할 조건
- 단, 시간외 종목을 임의로 TOP5에 넣지 않는다.

## ⑤ DART 공시 체크

- 주요 공시
- 긍정/부정/중립 판단
- 장전 영향도
- 주요 공시가 없으면 '별도 주요 공시 없음'이라고 쓴다.

## ⑥ 강세 예상 섹터 TOP5

1. 섹터명
   - 강세 예상 이유
   - 연결 데이터
   - 관련 종목

## ⑦ 오늘 매매 관심 종목 TOP5

1. 종목명(종목코드)
   - 최종점수 / 관심도 / AI판단 / 위험도
   - 추천 이유: candidate_scores의 AI추천근거를 2~5개 bullet로 작성한다.
   - 세부 근거: 기존 reasons는 필요할 때만 1~3개 보조 bullet로 정리한다.
   - 장 시작 후 확인 조건

## ⑧ 오늘 주의 종목

- 종목명
- 주의 이유
- 대응 기준
"""

    system_prompt = f"""
당신은 한국 주식시장 장전 브리핑을 작성하는 데이터 분석가다.

반드시 제공된 데이터 안에서만 판단하고, 확인되지 않은 사실은 단정하지 않는다.
투자 권유처럼 쓰지 말고, 장전 체크리스트와 매매 후보 검토 자료로 작성한다.

가장 먼저 'AI 투자 전략'을 제시한다.
그 다음 시장환경, 시간외 거래, DART 공시, 섹터, 종목 순서로 설명한다.

단순히 시스템 점수가 높은 종목을 나열하지 말고, 해외시장·환율·유가·뉴스 흐름과 연결해 설명한다.
다만 '오늘 매매 관심 종목 TOP5'의 종목과 순서는 반드시 최종 관심도 엔진(candidate_scores)을 따른다.

{ranking_guard}
"""

    user_prompt = f"""
아래 데이터를 바탕으로 한국시간 오전 7시 기준 한국 주식시장 장전 브리핑을 작성하라.

역할:
- 너는 증권사 리서치센터의 장전 전략 애널리스트다.
- 투자 권유가 아니라 장전 체크리스트를 작성한다.
- 제공된 데이터 안에서만 판단한다.
- 확인되지 않은 사실은 추정하지 않는다.

분석 원칙:
- 가장 먼저 '① AI 투자 전략'을 작성한다.
- market_decision의 strategy를 그대로 사용한다.
- market_decision의 cash_ratio와 buy_ratio를 그대로 사용한다.
- market_decision의 sector_strategy를 그대로 사용한다.
- market_decision의 strategy_comment와 strategy_reasons를 반영한다.
- market_decision의 positive_reasons, risk_reasons, check_points를 그대로 활용한다.
- 긍정요인과 위험요인을 반드시 구분해서 작성한다.
- 장 시작 후 확인 항목은 market_decision의 check_points를 우선 사용한다.
- 그 다음 '② 장전 한 줄 결론'을 작성한다.
- 시장판단 → 해외시장 → 환율·유가 → 뉴스 → 시간외 거래 → DART 공시 → 섹터 → 종목 순서로 연결한다.
- 단순히 상승률이나 점수가 높은 종목을 나열하지 말고, 왜 오늘 아침에 봐야 하는지 설명한다.
- 시간외 급등·급락은 반드시 다음 날 시초가 갭, 거래량, 뉴스·공시 지속성을 함께 확인하라고 쓴다.
- 공시는 긍정·부정·중립을 구분하되, 실제 주가 영향은 장 시작 후 수급 확인이 필요하다고 쓴다.
- 최종 관심도 엔진(candidate_scores)의 종목 순서와 TOP5 구성을 절대 바꾸지 않는다.
- candidate_scores의 AI추천근거는 각 종목의 추천 이유에 반드시 우선 반영한다.
- 기존 reasons는 세부 근거로만 사용하고, AI추천근거와 섞어서 길게 늘어놓지 않는다.
- candidate_scores가 없을 때만 candidates 목록을 따른다.
- risks 목록은 주의 종목 항목에서만 사용한다.
- '⑨ 장 시작 후 체크포인트'와 '⑩ 최종 유의사항'은 작성하지 않는다.

{output_format}

[데이터]

{input_text}
"""

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=float(temperature),
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
        )

        return (response.choices[0].message.content or "").strip()

    except Exception as e:
        return (
            f"- OpenAI 분석 생성에 실패해 규칙 기반 요약으로 대체했습니다. 오류: {e}\n"
            + rule_based_ai_brief(
                candidates=candidates,
                risks=risks,
                news_items=news_items,
                market_decision=market_decision,
                candidate_scores=candidate_scores,
            )
        )