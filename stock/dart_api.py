# stock/dart_api.py

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

try:
    import requests
except Exception:
    requests = None

from stock.models import DartDisclosure


OPENDART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"


def classify_disclosure(title: str) -> Dict[str, Any]:
    """
    공시 제목을 바탕으로 장전 분석용 성격을 분류한다.
    """

    title = title or ""

    if "단일판매" in title or "공급계약" in title or "수주" in title:
        return {
            "disclosure_type": "수주",
            "impact": "긍정",
            "importance": 5,
            "reason": "수주·공급계약 공시는 매출 가시성과 섹터 모멘텀에 영향을 줄 수 있음",
        }

    if "잠정실적" in title or "영업실적" in title or "매출액" in title:
        return {
            "disclosure_type": "실적",
            "impact": "중립",
            "importance": 5,
            "reason": "실적 공시는 컨센서스 대비 여부에 따라 주가 영향이 커질 수 있음",
        }

    if "자기주식취득" in title or "자사주" in title:
        return {
            "disclosure_type": "자사주",
            "impact": "긍정",
            "importance": 4,
            "reason": "자사주 취득은 주주환원 신호로 해석될 수 있음",
        }

    if "전환사채" in title or "CB" in title:
        return {
            "disclosure_type": "CB",
            "impact": "부정",
            "importance": 4,
            "reason": "전환사채는 잠재적 주식 희석 요인으로 해석될 수 있음",
        }

    if "유상증자" in title:
        return {
            "disclosure_type": "유상증자",
            "impact": "부정",
            "importance": 5,
            "reason": "유상증자는 자금조달 목적과 조건에 따라 희석 우려가 커질 수 있음",
        }

    if "최대주주" in title:
        return {
            "disclosure_type": "최대주주",
            "impact": "중립",
            "importance": 4,
            "reason": "최대주주 관련 공시는 지배구조 변화 가능성 때문에 확인이 필요함",
        }

    return {
        "disclosure_type": "기타",
        "impact": "중립",
        "importance": 2,
        "reason": "장전 영향 여부 추가 확인 필요",
    }


def build_dart_url(rcp_no: str) -> str:
    """
    DART 공시 원문 URL.
    """

    if not rcp_no:
        return ""

    return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp_no}"


def fetch_dart_disclosures(
    api_key: str,
    days_back: int = 1,
    corp_cls: Optional[str] = None,
    max_items: int = 30,
) -> List[DartDisclosure]:
    """
    OpenDART 공시검색 API에서 최근 공시를 가져와 DartDisclosure 모델로 반환한다.
    """

    if requests is None:
        return []

    api_key = (api_key or "").strip()
    if not api_key:
        return []

    today = dt.datetime.now().date()
    start = today - dt.timedelta(days=int(days_back))

    params = {
        "crtfc_key": api_key,
        "bgn_de": start.strftime("%Y%m%d"),
        "end_de": today.strftime("%Y%m%d"),
        "last_reprt_at": "N",
        "sort": "date",
        "sort_mth": "desc",
        "page_no": 1,
        "page_count": int(max_items),
    }

    if corp_cls:
        params["corp_cls"] = corp_cls

    try:
        resp = requests.get(OPENDART_LIST_URL, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return []

    if payload.get("status") not in ("000", "013"):
        return []

    rows = payload.get("list") or []
    results: List[DartDisclosure] = []

    for row in rows[: int(max_items)]:
        title = row.get("report_nm", "")
        info = classify_disclosure(title)

        item = DartDisclosure(
            date=row.get("rcept_dt", ""),
            time="",
            code=row.get("stock_code", ""),
            name=row.get("corp_name", ""),
            title=title,
            disclosure_type=info["disclosure_type"],
            impact=info["impact"],
            importance=info["importance"],
            sector="",
            related_stocks=[],
            url=build_dart_url(row.get("rcept_no", "")),
            reason=info["reason"],
        )

        results.append(item)

    return results


def format_dart_section(items: List[DartDisclosure]) -> str:
    """
    GPT 프롬프트와 Workspace에 넣을 DART 공시 요약문.
    """

    if not items:
        return "[DART 공시]\n- 주요 공시 없음"

    lines = ["[DART 공시 주요 항목]"]

    for item in items:
        lines.append(
            f"- {item.name}({item.code}): {item.title} / "
            f"유형: {item.disclosure_type} / "
            f"영향: {item.impact} / "
            f"중요도: {item.importance}/5 / "
            f"사유: {item.reason}"
        )

    return "\n".join(lines)