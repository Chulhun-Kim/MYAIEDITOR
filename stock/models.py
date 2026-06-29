# stock/models.py

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


# ============================================================
# 시간외 거래
# ============================================================

@dataclass
class AfterHoursItem:
    """
    시간외 거래 주요 종목
    """

    date: str
    code: str
    name: str
    after_change_pct: float
    after_volume: int
    signal: str
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# DART 공시
# ============================================================

@dataclass
class DartDisclosure:
    """
    DART 공시 주요 항목 모델.
    장전 분석에서는 단순 공시 목록이 아니라
    공시의 성격, 영향 방향, 중요도, 관련 섹터까지 함께 본다.
    """

    date: str = ""
    time: str = ""
    code: str = ""
    name: str = ""

    title: str = ""
    disclosure_type: str = ""      # 수주 / 실적 / 자사주 / CB / 유상증자 / 최대주주 등
    impact: str = "중립"            # 긍정 / 부정 / 중립
    importance: int = 0             # 1~5
    sector: str = ""
    related_stocks: List[str] = field(default_factory=list)

    url: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ============================================================
# ETF 흐름 (v0.6)
# ============================================================

@dataclass
class ETFFlow:
    etf_name: str = ""
    sector: str = ""
    change_pct: float = 0.0
    related_stocks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 장전 분석 전체 Dataset
# ============================================================

@dataclass
class PremarketData:
    """
    장전 분석 시스템의 공통 데이터 컨테이너

    모든 데이터는 이 모델에 모은 뒤
    AI / Workspace / Buffer 로 전달한다.
    """

    # 메타 정보
    meta: Dict[str, Any] = field(default_factory=dict)

    # 현재 사용
    global_market: List[Dict[str, Any]] = field(default_factory=list)
    news: List[Dict[str, Any]] = field(default_factory=list)
    sectors: List[Dict[str, Any]] = field(default_factory=list)
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[Dict[str, Any]] = field(default_factory=list)

    # 모델 기반
    after_hours: List[AfterHoursItem] = field(default_factory=list)
    dart: List[DartDisclosure] = field(default_factory=list)
    etf_flow: List[ETFFlow] = field(default_factory=list)

    # KRX_TEST 성공 후 연결
    foreign_flow: List[Dict[str, Any]] = field(default_factory=list)
    institution_flow: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON / Streamlit / Buffer 저장용
        """

        return {
            "meta": self.meta,
            "global_market": self.global_market,
            "news": self.news,
            "sectors": self.sectors,
            "candidates": self.candidates,
            "risks": self.risks,
            "after_hours": [x.to_dict() for x in self.after_hours],
            "dart": [x.to_dict() for x in self.dart],
            "etf_flow": [x.to_dict() for x in self.etf_flow],
            "foreign_flow": self.foreign_flow,
            "institution_flow": self.institution_flow,
        }