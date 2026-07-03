# stock/workspace_builder.py
# ------------------------------------------------------------
# MYAIEDITOR Workspace/Buffer 생성 모듈
# - app_stock.py에서 Workspace 작성 로직을 분리
# ------------------------------------------------------------

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import datetime as dt

from stock.dart_api import format_dart_section
from stock.premarket_ai import format_after_hours_section
from stock.sector_engine import build_news_keywords_summary


def _now_kst() -> dt.datetime:
    return dt.datetime.now(ZoneInfo("Asia/Seoul"))


def _now_iso() -> str:
    return _now_kst().strftime("%Y-%m-%d %H:%M:%S")


def _today_str() -> str:
    return _now_kst().strftime("%Y-%m-%d")


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


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if hasattr(item, "to_dict") and callable(getattr(item, "to_dict")):
        try:
            return item.to_dict()
        except Exception:
            pass
    if isinstance(item, dict):
        return item
    try:
        return asdict(item)
    except Exception:
        return {}


def _items_to_dicts(items: Optional[List[Any]]) -> List[Dict[str, Any]]:
    return [_item_to_dict(x) for x in (items or [])]


def build_market_brief(indicators: List[Dict[str, Any]]) -> str:
    if not indicators:
        return "- 해외시장 참고 지표를 가져오지 못했습니다."

    lines = []
    for it in indicators:
        memo = it.get("memo", "")
        line = (
            f"- {it['name']}({it['symbol']}): "
            f"{it['last']:.2f}, 전일 대비 {_fmt_pct(it['change_rate'])} "
            f"({it['date']})"
        )
        if memo:
            line += f" / 영향: {memo}"
        lines.append(line)
    return "\n".join(lines)


def build_news_brief(news_items: List[Any]) -> str:
    if not news_items:
        return "- NewsAPI 뉴스가 수집되지 않았습니다."

    lines = []
    keywords = build_news_keywords_summary(news_items)
    if keywords:
        lines.append(f"- 주요 반복 키워드: {', '.join(keywords)}")

    for i, n in enumerate(news_items[:10], start=1):
        title = getattr(n, "title", "") if not isinstance(n, dict) else n.get("title", "")
        source = getattr(n, "source", "") if not isinstance(n, dict) else n.get("source", "")
        published = getattr(n, "published", "") if not isinstance(n, dict) else n.get("published", "")
        description = getattr(n, "description", "") if not isinstance(n, dict) else n.get("description", "")
        url = getattr(n, "url", "") if not isinstance(n, dict) else n.get("url", "")
        lines.append(f"- {i}. {title} / {source} / {published}")
        if description:
            lines.append(f"  - {description}")
        if url:
            lines.append(f"  - 링크: {url}")
    return "\n".join(lines)




def format_market_decision_section(market_decision: Any) -> str:
    if market_decision is None:
        return "- 시장 판단 결과가 없습니다."
    if isinstance(market_decision, dict):
        score = market_decision.get("score", "")
        stars = market_decision.get("stars", "")
        sentiment = market_decision.get("sentiment", "")
        strategy = market_decision.get("strategy", "")
        summary = market_decision.get("summary", "")
        reasons = market_decision.get("reasons", []) or []
    else:
        score = getattr(market_decision, "score", "")
        stars = getattr(market_decision, "stars", "")
        sentiment = getattr(market_decision, "sentiment", "")
        strategy = getattr(market_decision, "strategy", "")
        summary = getattr(market_decision, "summary", "")
        reasons = getattr(market_decision, "reasons", []) or []

    lines = [
        f"- 시장판단: {sentiment} {stars}",
        f"- 종합점수: {score}/100",
        f"- 기본전략: {strategy}",
    ]
    if summary:
        lines.append(f"- 요약: {summary}")
    if reasons:
        lines.append("- 판단 근거:")
        for r in reasons[:8]:
            lines.append(f"  - {r}")
    return "\n".join(lines)

def build_workspace_text(
    latest_date: str,
    markets: List[str],
    target_count: int,
    candidates: List[Any],
    risks: List[Any],
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    news_query: str,
    ai_brief: str = "",
    sector_results: Optional[List[Dict[str, Any]]] = None,
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    candidate_scores: Optional[List[Any]] = None,
    market_decision: Optional[Any] = None,
) -> str:
    today = _today_str()
    final_candidates = candidate_scores or candidates

    lines: List[str] = []
    lines.append("# 장전 주식 분석")
    lines.append(f"- 브리핑 기준시각: {today} 07:00")
    lines.append(f"- 국내시장 가격 기준일: {latest_date}")
    lines.append(f"- 실제 분석시각: {_now_iso()}")
    lines.append(f"- 분석 시장: {', '.join(markets) if markets else '사용자 입력'}")
    lines.append(f"- 분석할 후보 종목 수: {target_count}개")
    lines.append("- 데이터 소스: FinanceDataReader + NewsAPI + after_hours.py + DART")
    lines.append(f"- 뉴스 검색어: {news_query}")
    lines.append("")

    lines.append("## ① 오늘 시장 판단")
    lines.append(format_market_decision_section(market_decision))
    lines.append("")

    lines.append("## ② 오늘 시장 환경")
    lines.append(build_market_brief(indicators))
    lines.append("")

    lines.append("## ③ 시간외 거래")
    lines.append(format_after_hours_section(after_hours_data or []))
    lines.append("")

    lines.append("## ④ DART 주요 공시")
    lines.append(format_dart_section(dart_items or []))
    lines.append("")

    lines.append("## ⑤ 장전 주요 뉴스")
    lines.append(build_news_brief(news_items))
    lines.append("")

    lines.append("## ⑥ 강세 예상 섹터 TOP5")
    if not sector_results:
        lines.append("- 뚜렷하게 감지된 강세 예상 섹터가 없습니다.")
    else:
        for i, s in enumerate(sector_results, start=1):
            lines.append(f"### {i}. {s.get('sector')} / {s.get('score')}점")
            matched = s.get("matched") or []
            stocks = s.get("stocks") or []
            if matched:
                lines.append(f"- 감지 키워드: {', '.join(matched)}")
            if stocks:
                lines.append(f"- 관련 종목: {', '.join(stocks)}")
            lines.append("")

    lines.append("## ⑦ 오늘 매매 관심 종목 TOP")
    if not final_candidates:
        lines.append("- 조건에 맞는 매매 관심 종목이 없습니다.")
    else:
        for i, p in enumerate(final_candidates, start=1):
            name = getattr(p, "name", "")
            ticker = getattr(p, "ticker", "")
            market = getattr(p, "market", "")
            total_score = getattr(p, "total_score", getattr(p, "score", 0))
            base_score = getattr(p, "base_score", getattr(p, "score", 0))
            stars = getattr(p, "stars", "")

            reasons = getattr(p, "reasons", []) or []
            recommend_reasons = getattr(p, "recommend_reasons", []) or []

            lines.append(
                f"### {i}. {name}({ticker}) / {market} / 최종 {total_score}점 {stars}"
            )

            if base_score != total_score:
                lines.append(f"- 기존점수: {base_score}점")

            # ===== AI 추천 근거 =====
            if recommend_reasons:
                lines.append("- AI 추천 근거")
                for r in recommend_reasons[:5]:
                    lines.append(f"  ✓ {r}")

            # ===== 세부 분석 =====
            if reasons:
                lines.append("- 세부 분석")
                for r in reasons[:7]:
                    lines.append(f"  - {r}")

            lines.append("")
            
    lines.append("## ⑧ 오늘 주의 종목 TOP")
    if not risks:
        lines.append("- 조건에 맞는 주의 종목이 없습니다.")
    else:
        for i, p in enumerate(risks, start=1):
            lines.append(f"### {i}. {p.name}({p.ticker}) / {p.market} / {p.score}점")
            lines.append(f"- 종가: {_fmt_num(p.close)}원")
            lines.append(f"- 직전 거래일 등락률: {_fmt_pct(p.change_rate)}")
            lines.append(f"- 거래량 배율: {_fmt_ratio(p.volume_ratio)}")
            lines.append(f"- 추정 거래대금: {_fmt_num(p.trading_value_est)}원")
            for r in p.reasons:
                lines.append(f"- {r}")
            lines.append("")

    lines.append("## ⑨ AI 장전 판단")
    if ai_brief.strip():
        lines.append(ai_brief.strip())
    else:
        lines.append("- OpenAI 장전 판단을 사용하지 않았습니다.")
    lines.append("")

    lines.append("## ⑩ 해석상 유의사항")
    lines.append("- 이 자료는 공개 주가·거래량·뉴스 흐름을 바탕으로 한 장전 참고자료입니다.")
    lines.append("- 투자 권유나 매매 추천이 아니며, 실제 매매 판단은 사용자가 별도로 검토해야 합니다.")
    lines.append("- 현재 버전은 외국인·기관 수급과 실시간 호가를 반영하지 않습니다. 시간외 거래는 after_hours.py 입력 데이터 기준입니다.")

    return "\n".join(lines).strip() + "\n"


def build_buffer_items(
    ws_text: str,
    latest_date: str,
    markets: List[str],
    candidates: List[Any],
    risks: List[Any],
    indicators: List[Dict[str, Any]],
    news_items: List[Any],
    ai_brief: str = "",
    after_hours_data: Optional[List[Any]] = None,
    dart_items: Optional[List[Any]] = None,
    sector_results: Optional[List[Dict[str, Any]]] = None,
    candidate_scores: Optional[List[Any]] = None,
    market_decision: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    return [
        {
            "type": "stock_preopen_analysis",
            "title": f"장전 주식 분석 {latest_date}",
            "text": ws_text,
            "meta": {
                "source": "FinanceDataReader + NewsAPI + after_hours.py + DART",
                "published": latest_date,
                "fetched_at": _now_iso(),
                "markets": markets,
                "candidate_count": len(candidate_scores or candidates),
                "risk_count": len(risks),
                "indicators": indicators,
                "news_count": len(news_items),
                "after_hours_count": len(after_hours_data or []),
                "dart_count": len(dart_items or []),
                "sector_count": len(sector_results or []),
                "ai_brief": ai_brief,
                "market_decision": _item_to_dict(market_decision),
                "raw": {
                    "candidates": [_item_to_dict(p) for p in candidates],
                    "candidate_scores": [_item_to_dict(p) for p in (candidate_scores or [])],
                    "risks": [_item_to_dict(p) for p in risks],
                    "news": [_item_to_dict(n) for n in news_items],
                    "after_hours": _items_to_dicts(after_hours_data),
                    "dart": _items_to_dicts(dart_items),
                    "sectors": sector_results or [],
                },
            },
        }
    ]
