# stock/after_hours_collector.py

from __future__ import annotations
from stock.after_hours_reasoner import reason_after_hours_rows
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AFTER_HOURS_CSV = DATA_DIR / "after_hours.csv"


def classify_after_hours_signal(change_pct: float) -> str:
    if change_pct >= 3:
        return "시간외 급등"
    if change_pct >= 1:
        return "시간외 상승"
    if change_pct <= -3:
        return "시간외 급락"
    if change_pct <= -1:
        return "시간외 약세"
    return "중립"

def build_after_hours_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    입력 데이터를 after_hours.csv 저장용 표준 행으로 변환한다.
    reason/sector/news_keyword/confidence는 reasoner에서 자동 생성한다.
    """

    rows: List[Dict[str, Any]] = []

    for row in raw_rows:
        date = str(row.get("date", "")).strip()
        code = str(row.get("code", "")).strip().zfill(6)
        name = str(row.get("name", "")).strip()
        change_pct = float(row.get("after_change_pct", 0) or 0)
        volume = int(float(row.get("after_volume", 0) or 0))

        signal = str(row.get("signal", "") or "").strip()
        if not signal:
            signal = classify_after_hours_signal(change_pct)

        rows.append(
            {
                "date": date,
                "code": code,
                "name": name,
                "after_change_pct": change_pct,
                "after_volume": volume,
                "signal": signal,
                "sector": str(row.get("sector", "") or "").strip(),
                "source": str(row.get("source", "manual") or "manual").strip(),
            }
        )

    return rows

def save_after_hours_csv(rows: List[Dict[str, Any]]) -> Path:
    """
    표준 시간외 CSV를 저장한다.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(rows)

    columns = [
        "date",
        "code",
        "name",
        "after_change_pct",
        "after_volume",
        "signal",
        "reason",
        "sector",
        "news_keyword",
        "confidence",
        "source",
    ]

    df = df[columns]
    df.to_csv(AFTER_HOURS_CSV, index=False, encoding="utf-8-sig")

    return AFTER_HOURS_CSV


def collect_after_hours_sample(
    news_items: List[Dict[str, Any]] | None = None,
    dart_items: List[Dict[str, Any]] | None = None,
) -> Path:
    
    """
    1차 테스트용 샘플 수집 함수.
    나중에 네이버/증권사 수집 함수로 교체한다.
    """
    raw_rows = [
        {
            "date": "2026-06-26",
            "code": "005930",
            "name": "삼성전자",
            "after_change_pct": 3.05,
            "after_volume": 1250000,
            "reason": "반도체·AI 관심 속 시간외 급등. 장 초반 갭 지속 여부 확인 필요",
            "news_keyword": "반도체,AI,HBM",
            "confidence": 0.85,
            "source": "manual_sample",
        },
        {
            "date": "2026-06-26",
            "code": "000660",
            "name": "SK하이닉스",
            "after_change_pct": -2.88,
            "after_volume": 890000,
            "reason": "시간외 약세. 장 초반 매도 지속 여부와 반도체 섹터 수급 확인 필요",
            "news_keyword": "반도체,HBM",
            "confidence": 0.75,
            "source": "manual_sample",
        },
    ]

    rows = build_after_hours_rows(raw_rows)

    if news_items is None:
        news_items = [
            {
                "title": "AI 반도체 투자 확대와 HBM 수요 기대감 지속",
                "description": "엔비디아와 데이터센터 투자 확대가 국내 반도체주에 영향을 줄 수 있다는 분석",
                "content": "삼성전자 SK하이닉스 HBM 반도체 AI 엔비디아 데이터센터",
            },
            {
                "title": "미국 기술주 변동성 확대 속 반도체주 선별 움직임",
                "description": "AI 관련 대형주 흐름은 유지되지만 일부 종목은 차익실현 압력을 받고 있음",
                "content": "반도체 AI SK하이닉스 삼성전자",
            },
        ]

    if dart_items is None:
        dart_items = []

    reasoned_rows = reason_after_hours_rows(
        rows=rows,
        news_items=news_items,
        dart_items=dart_items,
    )

    return save_after_hours_csv(reasoned_rows)

if __name__ == "__main__":
    saved_path = collect_after_hours_sample()
    print(f"after_hours.csv saved: {saved_path}")
    