# stock/story_generator.py
from typing import Any, Dict, List

def generate_story(story_graph: Dict[str, Any]) -> Dict[str, Any]:
    primary = story_graph.get("primary_path", {}) or {}
    theme = primary.get("root_theme", "시장")
    sector = primary.get("sector", "")
    flow = primary.get("flow", [])
    stocks = primary.get("stocks", [])
    risks = primary.get("risks", [])
    checkpoints = primary.get("checkpoints", [])
    confidence = primary.get("confidence", 0)

    body = []

    body.append(f"오늘 시장은 {theme} 흐름을 중심으로 {sector} 업종의 투자심리가 형성될 가능성이 있습니다.")

    if flow:
        body.append("핵심 흐름은 " + " → ".join(flow[:5]) + " 구조입니다.")

    if stocks:
        body.append("대표 관심 종목은 " + ", ".join(stocks[:3]) + "입니다.")

    if risks:
        body.append("다만 " + risks[0])

    if checkpoints:
        body.append("장 시작 후에는 " + ", ".join(checkpoints[:3]) + "를 확인하십시오.")

    text="\n\n".join(body)

    return {
        "headline": f"{theme} 중심 시장 전략",
        "summary": text,
        "story": text,
        "confidence": confidence,
        "flow": flow,
        "top_stocks": stocks,
        "risks": risks,
        "checkpoints": checkpoints,
    }

def generate_market_brief(story_graph: Dict[str, Any]) -> str:
    return generate_story(story_graph)["summary"]
