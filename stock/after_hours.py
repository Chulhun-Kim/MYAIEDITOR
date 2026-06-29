# stock/after_hours.py

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

from stock.models import AfterHoursItem


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_AFTER_HOURS_CSV = BASE_DIR / "data" / "after_hours.csv"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _normalize_code(code: Any) -> str:
    return str(code or "").strip().zfill(6)


def classify_after_hours_signal(change_pct: float) -> str:
    """
    시간외 등락률 기준으로 신호를 자동 분류한다.
    CSV에 signal 값이 비어 있을 때 사용한다.
    """

    if change_pct >= 3:
        return "시간외 급등"
    if change_pct >= 1:
        return "시간외 상승"
    if change_pct <= -3:
        return "시간외 급락"
    if change_pct <= -1:
        return "시간외 약세"

    return "중립"


def load_after_hours_from_csv(
    file_path: str | Path = DEFAULT_AFTER_HOURS_CSV,
) -> List[AfterHoursItem]:
    """
    data/after_hours.csv에서 시간외 거래 데이터를 읽는다.
    """

    path = Path(file_path)

    if not path.exists():
        return []

    try:
        df = pd.read_csv(path, dtype={"code": str})
    except Exception:
        return []

    required_cols = [
        "date",
        "code",
        "name",
        "after_change_pct",
        "after_volume",
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return []

    items: List[AfterHoursItem] = []

    for _, row in df.iterrows():
        change_pct = _safe_float(row.get("after_change_pct"))
        signal = str(row.get("signal", "") or "").strip()

        if not signal:
            signal = classify_after_hours_signal(change_pct)

        item = AfterHoursItem(
            date=str(row.get("date", "") or "").strip(),
            code=_normalize_code(row.get("code")),
            name=str(row.get("name", "") or "").strip(),
            after_change_pct=change_pct,
            after_volume=_safe_int(row.get("after_volume")),
            signal=signal,
            reason=str(row.get("reason", "") or "").strip(),
        )

        items.append(item)

    return items


def get_after_hours_data(
    file_path: str | Path = DEFAULT_AFTER_HOURS_CSV,
) -> List[AfterHoursItem]:
    """
    시간외 거래 데이터를 반환한다.

    우선순위:
    1. data/after_hours.csv
    2. 없거나 읽기 실패하면 빈 리스트 반환
    """

    return load_after_hours_from_csv(file_path)


def _to_dict(item: Union[AfterHoursItem, Dict[str, Any]]) -> Dict[str, Any]:
    """
    AfterHoursItem 또는 기존 dict 데이터를 모두 dict로 변환한다.
    """

    if isinstance(item, AfterHoursItem):
        return item.to_dict()

    if isinstance(item, dict):
        return item

    return {}


def format_after_hours_for_prompt(
    data: List[Union[AfterHoursItem, Dict[str, Any]]]
) -> str:
    """
    GPT 프롬프트에 넣을 시간외 거래 요약문을 만든다.
    """

    if not data:
        return "[시간외 거래]\n- 특이 종목 없음"

    lines = ["[시간외 거래]"]

    for raw in data:
        item = _to_dict(raw)

        lines.append(
            f"- {item.get('name', '')}({item.get('code', '')}): "
            f"{item.get('signal', '')}, "
            f"등락률 {item.get('after_change_pct', '')}%, "
            f"거래량 {int(item.get('after_volume', 0)):,}주, "
            f"사유: {item.get('reason', '')}"
        )

    return "\n".join(lines)