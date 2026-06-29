# premarket_ai.py

from typing import Dict, Any, List, Union
from stock.models import AfterHoursItem

def _after_hours_to_dict(
    item: Union[AfterHoursItem, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    AfterHoursItem 또는 기존 dict 데이터를 dict로 변환한다.
    """

    if isinstance(item, AfterHoursItem):
        return item.to_dict()

    if isinstance(item, dict):
        return item

    return {}


def format_after_hours_section(
    after_hours: List[Union[AfterHoursItem, Dict[str, Any]]]
) -> str:
    """
    시간외 거래 데이터를 GPT 프롬프트용 문장으로 변환한다.
    """

    if not after_hours:
        return "[시간외 거래]\n- 특이 종목 없음"

    lines = ["[시간외 거래]"]

    for raw in after_hours:
        item = _after_hours_to_dict(raw)

        lines.append(
            f"- {item.get('name', '')}({item.get('code', '')}): "
            f"{item.get('signal', '')}, "
            f"등락률 {item.get('after_change_pct', '')}%, "
            f"거래량 {int(item.get('after_volume', 0)):,}주, "
            f"사유: {item.get('reason', '')}"
        )

    return "\n".join(lines)

def format_dart_section_for_prompt(dart_items: List[Any]) -> str:
    """
    DART 공시 데이터를 GPT 프롬프트용 문장으로 변환한다.
    """

    if not dart_items:
        return "[DART 공시]\n- 주요 공시 없음"

    lines = ["[DART 공시 주요 항목]"]

    for raw in dart_items:
        if hasattr(raw, "to_dict"):
            item = raw.to_dict()
        elif isinstance(raw, dict):
            item = raw
        else:
            item = {}

        lines.append(
            f"- {item.get('name', '')}({item.get('code', '')}): "
            f"{item.get('title', '')} / "
            f"유형: {item.get('disclosure_type', '')} / "
            f"영향: {item.get('impact', '')} / "
            f"중요도: {item.get('importance', '')}/5 / "
            f"사유: {item.get('reason', '')}"
        )

    return "\n".join(lines)

def build_premarket_prompt(dataset: Dict[str, Any]) -> str:
    """
    장전 분석용 GPT 프롬프트를 생성한다.
    """

    after_hours_text = format_after_hours_section(
        dataset.get("after_hours", [])
    )

    prompt = f"""
너는 한국 주식시장 장전 브리핑을 작성하는 증권사 애널리스트다.

아래 데이터를 바탕으로 오늘 장전 관심 종목과 섹터를 정리하라.

{after_hours_text}

작성 형식:
- 핵심 요약
- 시간외 특징주
- 관련 섹터
- 장전 관심 종목
- 투자 유의점
"""

    return prompt.strip()