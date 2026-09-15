"""
데이터 레이어.

지금은 레이아웃 확인용 샘플(placeholder) 데이터만 들어 있습니다.
실제 데이터(GDELT / SIPRI / UN Comtrade)가 준비되면 이 파일의 함수 본문만
교체하면 app.py / charts.py는 손대지 않아도 됩니다.

모든 함수는 pandas DataFrame 또는 dict를 돌려줍니다.
각 함수 docstring에 "기대하는 컬럼"을 적어 두었으니 그 형태만 맞춰 주세요.
"""

from __future__ import annotations

import pandas as pd

LAST_UPDATED = "2025-06-30"

# ── 필터 옵션 ────────────────────────────────────────────────────────────────
PERIOD_RANGE = (2020, 2025)
CONTINENTS = ["전체", "아시아", "유럽", "아프리카", "북아메리카", "남아메리카", "오세아니아"]
CAUSES = ["전체", "영토", "정치", "이념", "종교", "민족", "자원", "권력", "지정학"]
COUNTRIES = ["전체", "러시아", "우크라이나", "이스라엘", "팔레스타인", "수단", "미얀마", "미국", "이란"]
NAV_PAGES = ["개요", "국가 간 관계 분석", "분쟁 원인 분석", "무기 거래 추이", "데이터 소개"]


# ── KPI ──────────────────────────────────────────────────────────────────────
def get_kpis() -> list[dict]:
    """
    상단 KPI 카드 4개.
    keys: label, value, unit, delta, delta_note, icon, tone
    tone: 'blue' | 'cyan' | 'red' | 'green'
    """
    return [
        {"label": "진행 중인 주요 분쟁", "value": "34", "unit": "건", "delta": "▲ 6", "delta_note": "(전년 대비)", "icon": "🌐", "tone": "blue"},
        {"label": "분쟁 관련 국가 수", "value": "62", "unit": "개국", "delta": "▲ 4", "delta_note": "", "icon": "👥", "tone": "cyan"},
        {"label": "분쟁 이벤트 수 (GDELT)", "value": "210,842", "unit": "건", "delta": "▲ 18.7%", "delta_note": "", "icon": "⚠️", "tone": "red"},
        {"label": "관련 무기 거래 규모 (SIPRI, TIV)", "value": "98.3 B", "unit": "", "delta": "▲ 11.4%", "delta_note": "", "icon": "🪖", "tone": "green"},
    ]


# ── 세계 분쟁 현황 지도 ─────────────────────────────────────────────────────
def get_map_data() -> pd.DataFrame:
    """
    국가별 분쟁 강도 (choropleth).
    columns: iso3, country, intensity(0~4 정수: 없음~매우높음), events(int), cause(str)
    """
    rows = [
        ("RUS", "러시아", 4, 48271, "영토, 지정학"),
        ("UKR", "우크라이나", 4, 48271, "영토, 지정학"),
        ("ISR", "이스라엘", 4, 32417, "영토, 종교"),
        ("PSE", "팔레스타인", 4, 32417, "영토, 종교"),
        ("SDN", "수단", 3, 19884, "권력, 민족"),
        ("MMR", "미얀마", 3, 17662, "민족, 정치"),
        ("SYR", "시리아", 3, 12000, "정치, 종교"),
        ("YEM", "예멘", 3, 9500, "종교, 권력"),
        ("IRN", "이란", 2, 7000, "지정학"),
        ("USA", "미국", 2, 6500, "지정학"),
        ("CHN", "중국", 2, 6000, "영토"),
        ("TWN", "대만", 2, 5000, "영토"),
        ("ETH", "에티오피아", 2, 4800, "민족"),
        ("COD", "콩고민주공화국", 2, 4500, "자원"),
        ("SOM", "소말리아", 2, 4000, "정치"),
        ("MLI", "말리", 2, 3500, "종교"),
        ("PAK", "파키스탄", 1, 2500, "영토"),
        ("IND", "인도", 1, 2500, "영토"),
        ("AFG", "아프가니스탄", 1, 2300, "정치"),
        ("VEN", "베네수엘라", 1, 1800, "정치"),
        ("COL", "콜롬비아", 1, 1500, "정치"),
        ("MEX", "멕시코", 1, 1400, "권력"),
        ("HTI", "아이티", 1, 1200, "권력"),
    ]
    return pd.DataFrame(rows, columns=["iso3", "country", "intensity", "events", "cause"])


def get_map_markers() -> pd.DataFrame:
    """
    지도 위 주요 분쟁 마커.
    columns: name, lat, lon, causes
    """
    rows = [
        ("러시아 - 우크라이나", 49.0, 32.0, "영토, 지정학"),
        ("이스라엘 - 팔레스타인", 31.5, 34.8, "영토, 종교"),
        ("수단", 15.5, 32.5, "권력, 민족"),
        ("미얀마", 19.7, 96.1, "민족, 정치"),
    ]
    return pd.DataFrame(rows, columns=["name", "lat", "lon", "causes"])


# ── 주요 분쟁 사례 ───────────────────────────────────────────────────────────
def get_major_conflicts() -> list[dict]:
    """
    우측 상단 카드 리스트.
    keys: name, period, tags(list[str]), events(int), trend(list[float]), emoji
    """
    return [
        {"name": "러시아 - 우크라이나", "period": "2022 - 현재", "tags": ["영토", "지정학", "이념"], "events": 48271, "trend": [1, 2, 3, 5, 6, 8, 9, 12, 14, 13, 16, 18], "emoji": "🪖"},
        {"name": "이스라엘 - 팔레스타인", "period": "1948 - 현재", "tags": ["영토", "종교", "민족"], "events": 32417, "trend": [2, 2, 3, 3, 4, 4, 5, 9, 12, 11, 13, 14], "emoji": "💥"},
        {"name": "수단", "period": "2023 - 현재", "tags": ["권력", "민족", "자원"], "events": 19884, "trend": [1, 1, 1, 2, 4, 6, 7, 8, 8, 9, 10, 11], "emoji": "🏴"},
        {"name": "미얀마", "period": "2021 - 현재", "tags": ["민족", "정치", "이념"], "events": 17662, "trend": [1, 2, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10], "emoji": "✊"},
    ]


# ── 분쟁 원인별 국가 간 관계 네트워크 ───────────────────────────────────────
def get_network(cause: str = "종교") -> tuple[list[dict], list[dict]]:
    """
    nodes: [{id, role}]  role: 'conflict' | 'related' | 'mediator'
    edges: [{source, target, relation}]  relation: 'hostile' | 'friendly' | 'neutral'
    """
    nodes = [
        {"id": "이스라엘", "role": "conflict"},
        {"id": "팔레스타인", "role": "conflict"},
        {"id": "이란", "role": "related"},
        {"id": "터키", "role": "related"},
        {"id": "미국", "role": "related"},
        {"id": "사우디아라비아", "role": "related"},
        {"id": "이집트", "role": "related"},
        {"id": "카타르", "role": "mediator"},
    ]
    edges = [
        {"source": "이스라엘", "target": "팔레스타인", "relation": "hostile"},
        {"source": "이스라엘", "target": "이란", "relation": "hostile"},
        {"source": "이스라엘", "target": "터키", "relation": "hostile"},
        {"source": "이스라엘", "target": "미국", "relation": "friendly"},
        {"source": "이스라엘", "target": "이집트", "relation": "friendly"},
        {"source": "팔레스타인", "target": "이란", "relation": "friendly"},
        {"source": "팔레스타인", "target": "사우디아라비아", "relation": "friendly"},
        {"source": "팔레스타인", "target": "카타르", "relation": "neutral"},
        {"source": "팔레스타인", "target": "이집트", "relation": "neutral"},
        {"source": "미국", "target": "사우디아라비아", "relation": "friendly"},
        {"source": "터키", "target": "이집트", "relation": "neutral"},
    ]
    return nodes, edges


# ── 선택한 분쟁의 상세 분석 ─────────────────────────────────────────────────
def get_conflict_names() -> list[str]:
    return [c["name"] for c in get_major_conflicts()]


def get_conflict_overview(name: str) -> dict:
    """keys: 기간, 주요 원인, 관련 국가, 최근 동향"""
    table = {
        "러시아 - 우크라이나": {"기간": "2022 - 현재", "주요 원인": "영토, 지정학, 이념", "관련 국가": "러시아, 우크라이나 (NATO, EU 등)", "최근 동향": "2024년 이후 전선 확대, 장기화 양상"},
        "이스라엘 - 팔레스타인": {"기간": "1948 - 현재", "주요 원인": "영토, 종교, 민족", "관련 국가": "이스라엘, 팔레스타인, 이란, 미국 등", "최근 동향": "2023년 10월 이후 격화"},
        "수단": {"기간": "2023 - 현재", "주요 원인": "권력, 민족, 자원", "관련 국가": "수단 (SAF, RSF)", "최근 동향": "내전 지속, 인도적 위기 심화"},
        "미얀마": {"기간": "2021 - 현재", "주요 원인": "민족, 정치, 이념", "관련 국가": "미얀마 (군부, 소수민족 무장단체)", "최근 동향": "저항세력 확대"},
    }
    return table.get(name, {"기간": "-", "주요 원인": "-", "관련 국가": "-", "최근 동향": "-"})


def get_conflict_events(name: str) -> pd.DataFrame:
    """
    분쟁 이벤트 추이 (GDELT, 월별).
    columns: date(datetime), events(int)
    """
    dates = pd.date_range("2020-01-01", "2025-06-01", freq="MS")
    n = len(dates)
    base = [200 + i * 20 for i in range(n)]
    # 2022년 이후 급증하는 모양 (샘플)
    events = [v if d.year < 2022 else v + (d.year - 2021) * 1500 + (i % 7) * 120 for i, (d, v) in enumerate(zip(dates, base))]
    return pd.DataFrame({"date": dates, "events": events})


def get_arms_trade(name: str) -> pd.DataFrame:
    """
    관련 국가의 무기 거래량 추이 (SIPRI, TIV, 연도별).
    columns: year(int), country(str), tiv(float, billion)
    """
    years = list(range(2020, 2026))
    series = {
        "러시아": [5.5, 4.8, 4.2, 4.0, 3.8, 3.5],
        "우크라이나": [5.0, 6.5, 12.0, 20.0, 27.0, 25.0],
        "미국": [8.0, 8.5, 9.0, 9.8, 10.5, 11.0],
        "독일": [3.0, 3.2, 3.5, 3.8, 4.0, 4.2],
        "기타 NATO": [3.2, 3.5, 3.8, 4.0, 4.3, 4.5],
    }
    rows = [(y, c, v) for c, vals in series.items() for y, v in zip(years, vals)]
    return pd.DataFrame(rows, columns=["year", "country", "tiv"])
