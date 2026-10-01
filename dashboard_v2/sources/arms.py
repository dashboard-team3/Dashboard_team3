"""무기 거래 추이 페이지용 데이터. 자료 두 가지를 같은 모양(공급국 → 중동 수입국, 기간, 품목, 값)으로 맞춰 돌려준다.

Comtrade (data/comtrade_mirror_detail.csv): 월 × 수출국 × 수입국 × HS 품목, 값 = 교역액(USD, Mirror 기준)
SIPRI    (data/SIPRI_pre_1980_2025.csv):     계약 1건 = 1행, 값 = 주문 TIV, 주문 연도 기준
"""
import math

import pandas as pd
import streamlit as st

from sources.relations import COUNTRIES, DATA_DIR, SIPRI_CODE, SIPRI_FILE

COMTRADE_FILE = DATA_DIR / "comtrade_mirror_detail.csv"

# 2002–2009년은 신고 수출국이 연 8~11개국뿐이고 2010년부터 41개국 이상이라, 기본 표시는 2010년부터
FULL_START_YEAR = 2010

# HS 품목 6개 → 짧은 한글 이름과 색
HS_LABELS = {
    9306: "탄약·미사일·폭탄", 8710: "전차·장갑차", 9301: "군용 화기", 890610: "군함",
    880521: "비행 훈련장치", 930591: "군용 화기 부품",
}
HS_COLORS = {
    "탄약·미사일·폭탄": "#f87171", "전차·장갑차": "#4ade80", "군용 화기": "#f5c542", "군함": "#60a5fa",
    "비행 훈련장치": "#c084fc", "군용 화기 부품": "#fb923c",
}

# SIPRI weapon_desc(영문)를 키워드로 8가지로 묶는다. 앞 규칙이 먼저 적용된다.
WEAPON_RULES = [
    ("방공",     ("air-defence", "anti-aircraft", "surface-to-air missile system", "anti-ballistic missile system",
                  "coastal defence system")),
    ("센서",     ("radar", "sonar", "electro-optical", "signals intelligence", "air-search system", "satellite",
                  "reconnaissance system")),
    ("미사일",   ("missile", "torpedo", "guided", "loitering munition", "rocket launcher")),
    ("항공기",   ("aircraft", "helicopter", "drone")),
    ("함정",     ("ship", "boat", "craft", "submarine", "corvette", "destroyer", "frigate", "minehunter", "minesweeper")),
    ("장갑차량", ("tank", "armoured", "infantry fighting vehicle", "fire-support vehicle", "ugv")),
    ("포",       ("gun", "mortar", "howitzer")),
    ("엔진",     ("engine", "turbofan", "turbojet", "turboprop", "gas turbine", "air refuel")),
]
WEAPON_COLORS = {
    "항공기": "#f5c542", "미사일": "#f87171", "함정": "#60a5fa", "장갑차량": "#4ade80",
    "방공": "#c084fc", "센서": "#22d3ee", "포": "#fb923c", "엔진": "#94a3b8", "기타": "#64748b",
}


def weapon_category(desc):
    d = str(desc).lower()
    for name, keys in WEAPON_RULES:
        if any(k in d for k in keys):
            return name
    return "기타"


# SIPRI 공급국 영문 이름 → ISO3 (좌표 찾기용). 옛 나라는 임시 코드로 두고 현재 위치에 찍는다.
SUPPLIER_ISO = {
    "United States": "USA", "France": "FRA", "Germany": "DEU", "United Kingdom": "GBR", "Russia": "RUS",
    "Italy": "ITA", "Soviet Union": "SUN", "China": "CHN", "Netherlands": "NLD", "Canada": "CAN", "Turkiye": "TUR",
    "Switzerland": "CHE", "South Africa": "ZAF", "Spain": "ESP", "Sweden": "SWE", "Ukraine": "UKR",
    "South Korea": "KOR", "United Arab Emirates": "ARE", "North Korea": "PRK", "Belgium": "BEL", "Brazil": "BRA",
    "Jordan": "JOR", "Israel": "ISR", "Austria": "AUT", "Czechia": "CZE", "Pakistan": "PAK", "Singapore": "SGP",
    "Egypt": "EGY", "Iran": "IRN", "Libya": "LBY", "Poland": "POL", "Norway": "NOR", "Bulgaria": "BGR",
    "Finland": "FIN", "Australia": "AUS", "Belarus": "BLR", "Saudi Arabia": "SAU", "Iraq": "IRQ", "Syria": "SYR",
    "Serbia": "SRB", "Denmark": "DNK", "Hungary": "HUN", "Romania": "ROU", "Yugoslavia": "YUG", "Slovakia": "SVK",
    "Czechoslovakia": "CSK", "Qatar": "QAT", "Montenegro": "MNE", "East Germany (GDR)": "DDR", "Ethiopia": "ETH",
    "Indonesia": "IDN", "Oman": "OMN", "Greece": "GRC", "Estonia": "EST", "Kuwait": "KWT", "Sudan": "SDN",
    "Taiwan": "TWN", "Aruba": "ABW", "Malta": "MLT", "Malaysia": "MYS", "New Zealand": "NZL", "Georgia": "GEO",
    "Slovenia": "SVN", "Croatia": "HRV", "Thailand": "THA",
}

# 수입국(중동 16개국, 파일에는 팔레스타인 없음): 개요 지도와 같은 좌표
TARGET_POS = {
    "TUR": (39.0, 35.0), "SYR": (35.4, 38.8), "LBN": (34.3, 35.6), "ISR": (31.0, 34.6),
    "PSE": (32.4, 36.9), "JOR": (30.0, 37.6), "IRQ": (33.0, 43.7), "IRN": (32.5, 54.0),
    "KWT": (29.3, 47.6), "BHR": (26.1, 50.5), "QAT": (25.3, 51.2), "ARE": (23.9, 54.3),
    "OMN": (21.0, 57.0), "SAU": (24.0, 45.0), "YEM": (15.6, 47.5), "EGY": (27.0, 30.5),
}
# 수출국(ISO3): 대략적인 나라 중심점. 중동 나라가 수출국이면 위 좌표를 그대로 쓴다
EXPORTER_POS = {
    "USA": (39.0, -98.0), "CAN": (56.0, -106.0), "KOR": (36.5, 127.8), "ESP": (40.2, -3.7), "ZAF": (-29.0, 25.0),
    "RUS": (60.0, 90.0), "BRA": (-10.0, -52.0), "CHE": (46.8, 8.2), "NOR": (62.0, 10.0), "SVK": (48.7, 19.7),
    "BIH": (44.0, 17.7), "FRA": (46.6, 2.3), "ITA": (42.5, 12.5), "GBR": (54.0, -2.5), "POL": (52.0, 19.4),
    "IND": (22.0, 79.0), "HRV": (45.1, 15.2), "ROU": (45.9, 25.0), "DEU": (51.0, 10.4), "AUS": (-25.0, 134.0),
    "NLD": (52.2, 5.3), "FIN": (64.0, 26.0), "CYP": (35.1, 33.4), "CZE": (49.8, 15.5), "BEL": (50.6, 4.5),
    "COL": (4.0, -73.0), "CIV": (7.5, -5.5), "PAK": (30.4, 69.3), "SRB": (44.0, 21.0), "DNK": (56.0, 10.0),
    "SWE": (62.0, 15.0), "THA": (15.9, 100.9), "MNE": (42.7, 19.4), "GRC": (39.0, 22.0), "GHA": (7.9, -1.0),
    "IDN": (-2.5, 118.0), "AUT": (47.6, 14.1), "LTU": (55.2, 23.9), "SVN": (46.1, 14.8), "COD": (-3.0, 23.0),
    "PRT": (39.5, -8.0), "IRL": (53.4, -8.0), "SGP": (1.35, 103.8), "MYS": (4.2, 102.0), "MEX": (23.6, -102.5),
    "CHN": (35.0, 104.0), "PHL": (12.9, 121.8), "EST": (58.6, 25.0), "LVA": (56.9, 24.6), "HUN": (47.2, 19.5),
    "NZL": (-41.0, 174.0), "CHL": (-33.0, -71.0), "MLT": (35.9, 14.4), "LUX": (49.8, 6.1), "KEN": (0.0, 37.9),
    "ARG": (-34.0, -64.0), "JPN": (36.2, 138.3), "SYC": (-4.7, 55.5), "HKG": (22.3, 114.2), "TZA": (-6.4, 35.0),
    "UKR": (48.5, 31.5), "BRN": (4.5, 114.7), "BFA": (12.4, -1.5), "BEN": (9.3, 2.3), "MDG": (-19.0, 47.0),
    "SEN": (14.5, -14.5), "ECU": (-1.8, -78.2),
    # SIPRI에만 나오는 공급국·옛 나라
    "SUN": (60.0, 90.0), "PRK": (40.0, 127.0), "LBY": (27.0, 17.0), "BGR": (42.7, 25.5), "BLR": (53.7, 27.9),
    "YUG": (44.0, 20.0), "CSK": (49.8, 15.5), "DDR": (52.5, 13.4), "ETH": (9.1, 40.5), "SDN": (15.5, 30.0),
    "TWN": (23.7, 121.0), "ABW": (12.5, -70.0), "GEO": (42.3, 43.4),
    **TARGET_POS,
}


def pos(iso3):
    return EXPORTER_POS.get(iso3)


# ---------------------------------------------------------------- 로딩

SOURCES = {
    "Comtrade": dict(
        unit="백만 달러", value_label="교역액", obs_label="관측 월", cat_label="품목",
        periods=["월별", "분기별", "연간"], default_period="연간", default_start=FULL_START_YEAR,
        colors=HS_COLORS, exporter_label="수출국", role_label="수출",
        desc="UN Comtrade 군용 품목 6개(HS 8710 · 9301 · 9306 · 880521 · 890610 · 930591)의 월별 교역액. "
             "수출국이 신고한 Mirror 기준으로 중동 국가가 받은 금액이며, 단위는 백만 달러입니다.",
        foot="Mirror 값 = 수출국이 신고한 대중동 수출액. 수입국이 직접 신고한 수입액이 아닙니다. 신고가 없는 달은 0이 아니라 '관측 없음'이며, "
             "월별 기록이 있어도 모든 품목·수출국의 신고가 완전하다는 뜻은 아닙니다.",
    ),
    "SIPRI": dict(
        unit="TIV", value_label="주문 TIV", obs_label="계약", cat_label="무기 종류",
        periods=["연간"], default_period="연간", default_start=1980,
        colors=WEAPON_COLORS, exporter_label="공급국", role_label="공급",
        desc="SIPRI 무기 이전 기록 중 중동 16개국이 수입한 계약. 값은 주문 연도 기준 SIPRI TIV(무기의 군사적 가치를 나타내는 지표)이며 "
             "달러 금액이 아닙니다. 실제 인도는 보통 주문 몇 년 뒤입니다.",
        foot="TIV는 무기 가치 지표라 달러와 다르고, 연도는 주문 연도입니다. 무기 종류는 SIPRI 무기 설명(weapon_desc)을 키워드로 묶은 것입니다. "
             "소련·유고슬라비아 등 옛 나라는 당시 이름 그대로 두고 현재 위치에 찍었습니다.",
    ),
}


@st.cache_data
def load(source="Comtrade"):
    """공통 열: date, year, period, exporter_iso3, exporter, target_iso3, target_name, cat, value, obs"""
    if source == "Comtrade":
        df = pd.read_csv(COMTRADE_FILE, usecols=["period", "year", "month", "exporter_iso3", "exporter_name",
                                                 "target_iso3", "hs_code", "primary_value"])
        df["date"] = pd.to_datetime(df["period"].astype(str), format="%Y%m")
        df["value"] = df["primary_value"] / 1e6
        df["cat"] = df["hs_code"].map(HS_LABELS)
        # 수출국 이름: 중동 나라는 한글, 나머지는 파일의 영문 이름
        df["exporter"] = df["exporter_iso3"].map(COUNTRIES).fillna(df["exporter_name"])
        df["obs"] = df["period"]                       # 관측 단위 = 월
    else:
        df = pd.read_csv(SIPRI_FILE, encoding="utf-8-sig")
        df["target_iso3"] = df["importer"].map(SIPRI_CODE)
        df["exporter_iso3"] = df["supplier"].map(SUPPLIER_ISO).fillna(df["supplier"])
        df["exporter"] = df["supplier_ko"]
        df["date"] = pd.to_datetime(df["year"].astype(str) + "-01-01")
        df["period"] = df["year"] * 100 + 1
        df["value"] = df["tiv_order"]
        df["cat"] = df["weapon_desc"].map(weapon_category)
        df["obs"] = df["contract_id"]                  # 관측 단위 = 계약
    df["target_name"] = df["target_iso3"].map(COUNTRIES)
    keep = ["date", "year", "period", "exporter_iso3", "exporter", "target_iso3", "target_name", "cat", "value", "obs"]
    if source == "SIPRI":
        keep += ["weapon", "weapon_desc", "qty"]
    missing = sorted(set(df["exporter_iso3"]) - set(EXPORTER_POS))
    return df[keep], missing


def apply_filters(df, years, cats, targets, exporters):
    m = df["year"].between(*years) & df["cat"].isin(cats) & df["target_iso3"].isin(targets)
    if exporters:
        m &= df["exporter_iso3"].isin(exporters)
    return df[m]


# ---------------------------------------------------------------- 집계

def flows(df):
    """공급국 → 수입국 흐름별 값 합, 관측 수(월 또는 계약), 최다 품목."""
    g = (df.groupby(["exporter_iso3", "exporter", "target_iso3", "target_name"])
           .agg(value=("value", "sum"), obs=("obs", "nunique"),
                top_cat=("cat", lambda s: s.value_counts().index[0]))
           .reset_index().sort_values("value", ascending=False))
    return g


def series(df, how, by=None):
    """기간별 금액 표 (행 = 기간, 열 = by 항목). 관측 월 수도 함께 돌려준다.

    월별은 그대로, 분기·연간은 관측된 달만 합산한다 (신고가 없는 달은 0이 아니라 '관측 없음').
    """
    freq = {"월별": "MS", "분기별": "QS", "연간": "YS"}[how]
    key = pd.Grouper(key="date", freq=freq)
    if by is None:
        t = df.groupby(key)["value"].sum().to_frame("전체")
    else:
        t = df.pivot_table(index=key, columns=by, values="value", aggfunc="sum", fill_value=0.0)
    months = df.groupby(key)["period"].nunique().reindex(t.index).fillna(0).astype(int)
    need = {"월별": 1, "분기별": 3, "연간": 12}[how]
    return t, months, need


def great_circle(lat1, lon1, lat2, lon2, n=40):
    """두 점을 잇는 대권 위의 점 n개 (지도의 호)."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    d = 2 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin((l2 - l1) / 2) ** 2))
    if d < 1e-9:
        return [lat1, lat2], [lon1, lon2]
    lats, lons = [], []
    for i in range(n + 1):
        f = i / n
        a, b = math.sin((1 - f) * d) / math.sin(d), math.sin(f * d) / math.sin(d)
        x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
        y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
        z = a * math.sin(p1) + b * math.sin(p2)
        lats.append(math.degrees(math.atan2(z, math.sqrt(x * x + y * y))))
        lons.append(math.degrees(math.atan2(y, x)))
    return lats, lons
