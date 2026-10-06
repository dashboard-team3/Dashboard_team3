"""국가 간 관계 분석 페이지용 데이터: 월별 국가쌍 리스크 + SIPRI 무기 수입.

data/risk_monthly_1980_2026.csv  국가쌍(방향 있음) × 월 Conflict Risk (0~1)
data/SIPRI_pre_1980_2025.csv     중동 16개국이 수입한 무기 계약 (year = 주문 연도, tiv_order = 계약 규모 TIV)
data/country_monthly_1980_2026.csv  국가별(16개국) 월별 리스크: out(주어)·in(목적어)·all(합산)
data/region_monthly_1980_2026.csv   중동 16개국 전체를 한 줄로 낸 월별 리스크
"""
import math

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------- 경로 · 나라 이름

from core.paths import DATA_DIR                             # 원본 pjL/data/ 를 같이 씀 (core/paths.py)
RISK_FILE = DATA_DIR / "risk_monthly_1980_2026.csv"
SIPRI_FILE = DATA_DIR / "SIPRI_pre_1980_2025.csv"
COUNTRY_FILE = DATA_DIR / "country_monthly_1980_2026.csv"
REGION_FILE = DATA_DIR / "region_monthly_1980_2026.csv"

# 국가 코드 → 화면 이름. 리스크 파일은 코드, SIPRI 파일은 영문 이름을 쓴다.
COUNTRIES = {
    "SAU": "사우디아라비아", "ARE": "아랍에미리트", "QAT": "카타르", "KWT": "쿠웨이트",
    "BHR": "바레인", "OMN": "오만", "YEM": "예멘", "SYR": "시리아",
    "LBN": "레바논", "JOR": "요르단", "ISR": "이스라엘", "PSE": "팔레스타인",
    "IRQ": "이라크", "IRN": "이란", "EGY": "이집트", "TUR": "튀르키예",
}
SIPRI_CODE = {
    "Saudi Arabia": "SAU", "United Arab Emirates": "ARE", "Qatar": "QAT", "Kuwait": "KWT",
    "Bahrain": "BHR", "Oman": "OMN", "Yemen": "YEM", "Syria": "SYR",
    "Lebanon": "LBN", "Jordan": "JOR", "Israel": "ISR", "Palestine": "PSE",
    "Iraq": "IRQ", "Iran": "IRN", "Egypt": "EGY", "Turkiye": "TUR",
}


# GDELT 서버 자체에 일별 파일이 없는 달: (연, 월) → 실제 원본이 있는 날 수
KNOWN_RAW_DAYS = {(2014, 1): 28, (2014, 3): 30, (2025, 6): 13, (2025, 7): 30}


# ---------------------------------------------------------------- 데이터 읽기

@st.cache_data(show_spinner="국가쌍 리스크 불러오는 중…")
def load_risk():
    """모든 국가쌍 × 모든 달을 채운 월별 리스크. 파일에 없는 달(사건 없음)은 0."""
    df = pd.read_csv(RISK_FILE, encoding="utf-8-sig")
    # raw_days(그 달에 GDELT 원본 파일이 있던 날 수)는 파일 버전에 따라 없을 수 있다.
    # 없으면 알려진 서버 공백(2025-06: 18일 누락)만 반영한다.
    if "raw_days" not in df.columns:
        df["raw_days"] = df["days_in_month"] if "days_in_month" in df.columns else 31
        for (y, m), n in KNOWN_RAW_DAYS.items():
            df.loc[(df["year"] == y) & (df["month"] == m), "raw_days"] = n
    for c in ("conf", "coop"):          # 갈등·협력 가중합 (급증 유형 분류에 쓴다). 옛 파일에는 없을 수 있다
        if c not in df.columns:
            df[c] = float("nan")
    df = df[["Actor1CountryCode", "Actor2CountryCode", "year", "month", "risk", "active_days", "raw_days", "conf", "coop"]]
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    months = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
    grid = pd.MultiIndex.from_product(
        [list(COUNTRIES), list(COUNTRIES), months],
        names=["Actor1CountryCode", "Actor2CountryCode", "date"],
    ).to_frame(index=False)
    grid = grid[grid["Actor1CountryCode"] != grid["Actor2CountryCode"]]
    df = grid.merge(df.drop(columns=["year", "month"]), how="left",
                    on=["Actor1CountryCode", "Actor2CountryCode", "date"])
    df["risk"] = df["risk"].fillna(0.0)
    df["active_days"] = df["active_days"].fillna(0).astype(int)
    df["conf"] = df["conf"].fillna(0.0)
    df["coop"] = df["coop"].fillna(0.0)
    return df


@st.cache_data(show_spinner="국가별 리스크 불러오는 중…")
def load_country():
    """국가별 월별 리스크 (열: country, date, out_risk, in_risk, all_risk).

    all = 그 나라가 낀 모든 국가쌍의 갈등·협력 가중합을 먼저 더한 뒤 나눈 값 (평균의 평균이 아님).
    """
    df = pd.read_csv(COUNTRY_FILE, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df[["country", "date", "out_risk", "in_risk", "all_risk", "active_days", "days_in_month"]]


@st.cache_data(show_spinner="중동 전체 리스크 불러오는 중…")
def load_region():
    """중동 16개국 전체 월별 리스크 (비교 기준선용)."""
    df = pd.read_csv(REGION_FILE, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df.set_index("date")["risk"]


@st.cache_data(show_spinner="SIPRI 무기 계약 불러오는 중…")
def load_sipri():
    df = pd.read_csv(SIPRI_FILE, encoding="utf-8-sig")
    df["code"] = df["importer"].map(SIPRI_CODE)
    return df


@st.cache_data(show_spinner="등급 분포 산출 중…")
def load_dists():
    """층별로 '지금까지 나온 값'을 정렬해 둔 것. 어떤 값이 그 층에서 상위 몇 %인지 재는 데 쓴다.

    국가쌍은 파일에 있는 달만(사건 없는 달을 0으로 채우기 전) 센다.
    """
    pair = pd.read_csv(RISK_FILE, encoding="utf-8-sig", usecols=["risk"])["risk"]
    country = pd.read_csv(COUNTRY_FILE, encoding="utf-8-sig", usecols=["out_risk", "in_risk", "all_risk"])
    return {
        "pair": sorted(pair.dropna().tolist()),
        "out_risk": sorted(country["out_risk"].dropna().tolist()),
        "in_risk": sorted(country["in_risk"].dropna().tolist()),
        "all_risk": sorted(country["all_risk"].dropna().tolist()),
        "region": sorted(load_region().dropna().tolist()),
    }


# ---------------------------------------------------------------- 등급 (리스크 분석 페이지 등급 카드)

# 상태 등급: 리스크는 '오간 보도 무게 중 갈등의 몫'이라 값 자체에 뜻이 있어 0.2 간격으로 자른다.
# (백분위로 매기면 조용한 쌍이 많아 0.1이 '높음'이 되어 버린다.) 몇 %인지는 따로 적는다.
GRADES = ["매우 낮음", "낮음", "보통", "높음", "매우 높음"]
GRADE_COLORS = ["#60a5fa", "#34d399", "#fbbf24", "#fb923c", "#f87171"]
GRADE_CUTS = [0.2, 0.4, 0.6, 0.8]
GRADE_DESC = ["갈등 20% 미만", "20~40%", "40~60%", "60~80%", "80% 이상"]


def grade(v):
    """0=매우 낮음(0.2 미만) … 4=매우 높음(0.8 이상). 값이 없으면 None."""
    if v is None or pd.isna(v):
        return None
    return sum(v >= c for c in GRADE_CUTS)


def pct_rank(v, dist):
    """그 층에서 v보다 작은 값의 비율(%). '상위 N%'로 보여 주려면 100에서 뺀다."""
    if v is None or pd.isna(v) or not dist:
        return None
    import bisect
    return bisect.bisect_left(dist, v) / len(dist) * 100


# ---------------------------------------------------------------- 리스크 분석 페이지

def pair_series(risk, country, direction):
    """country와 연결된 15개 국가쌍의 월별 리스크 (열 = 상대국 코드).

    direction: "both" 두 방향 평균 / "out" country → 상대 / "in" 상대 → country
    """
    out = risk[risk["Actor1CountryCode"] == country].pivot(
        index="date", columns="Actor2CountryCode", values="risk")
    inc = risk[risk["Actor2CountryCode"] == country].pivot(
        index="date", columns="Actor1CountryCode", values="risk")
    if direction == "out":
        return out
    if direction == "in":
        return inc
    return (out + inc) / 2


def smooth(series, how):
    """월별 값을 보기 좋게 다듬는다: 그대로 / 12개월 이동평균 / 연평균."""
    if how == "12개월 이동평균":
        return series.rolling(12, min_periods=1).mean()
    if how == "연평균":
        return series.groupby(series.index.year).mean().set_axis(
            pd.to_datetime(series.index.year.unique().astype(str) + "-07-01"))
    return series


def gap_months(risk, min_days=20):
    """GDELT 원본이 절반 넘게 빠진 달 (예: 2025-06 서버 공백)."""
    days = risk.groupby("date")["raw_days"].min()
    return set(days[days < min_days].index)


# ---------------------------------------------------------------- 리스크와 무기 거래 페이지 (연 리스크 × 무기 수입, 시차 상관)

@st.cache_data(show_spinner="연간 리스크·무기 수입 자료 통합 중…")
def arms_panel():
    """나라 × 연도 표: 연 리스크와 SIPRI 무기 수입을 한 줄에 놓는다 (리스크와 무기 거래 페이지용).

    risk  그 해 월별 종합 리스크(all_risk)를 그 달 일수로 가중해 평균한 값(= 그 해 모든 날의 평균). 12개월이 다 있는 해만.
          (단순 평균을 쓰면 2월과 7월이 같은 한 표가 되어 일별에서 낸 값과 어긋난다)
    tiv   주문 연도 기준 SIPRI TIV 합. 주문이 없던 해는 0
    ltiv  log(1 + tiv). 큰 계약 한 건에 덜 끌려가도록
    """
    c = load_country().copy()
    c["year"] = c["date"].dt.year
    c["w"] = c["all_risk"] * c["days_in_month"]
    ann = (c.groupby(["country", "year"]).agg(w=("w", "sum"), d=("days_in_month", "sum"), n=("all_risk", "size"))
           .reset_index())
    ann = ann[ann["n"] == 12]
    ann["risk"] = ann["w"] / ann["d"]
    sp = load_sipri()
    imp = sp.dropna(subset=["code"]).groupby(["code", "year"])["tiv_order"].sum()
    y0, y1 = 1980, int(sp["year"].max())
    grid = pd.MultiIndex.from_product([list(COUNTRIES), range(y0, y1 + 1)], names=["country", "year"]).to_frame(index=False)
    m = grid.merge(ann[["country", "year", "risk"]], on=["country", "year"], how="left")
    m["tiv"] = [float(imp.get((cc, yy), 0.0)) for cc, yy in zip(m["country"], m["year"])]
    m["ltiv"] = (m["tiv"] + 1.0).apply(math.log)
    return m.dropna(subset=["risk"]).reset_index(drop=True)


def lag_corr_all(m, k, years):
    """risk(t)와 log수입(t+k)의 피어슨 상관. 나라마다 규모가 달라 나라 안에서 표준화한 뒤 잰다.

    돌려주는 값: (16개국을 합쳐 잰 r, 나라별 r Series). 비교할 해가 5개 미만인 나라는 뺀다.
    """
    d = m.copy()
    # k년 뒤 수입은 '행 k칸 뒤'가 아니라 '연도 + k'로 찾는다 (연 리스크가 빠진 해가 있어도 짝이 밀리지 않게)
    look = dict(zip(zip(m["country"], m["year"]), m["ltiv"]))
    d["y"] = [look.get((cc, yy + k), float("nan")) for cc, yy in zip(d["country"], d["year"])]
    d = d[d["year"].between(*years)].dropna(subset=["risk", "y"])
    per, parts = {}, []
    for cc, g in d.groupby("country"):
        if len(g) < 5 or g["risk"].std() == 0 or g["y"].std() == 0:
            continue
        per[cc] = _pearson(g["risk"], g["y"])
        parts.append(pd.DataFrame({"xz": (g["risk"] - g["risk"].mean()) / g["risk"].std(),
                                   "yz": (g["y"] - g["y"].mean()) / g["y"].std()}))
    if not parts:
        return float("nan"), pd.Series(dtype=float)
    z = pd.concat(parts)
    return _pearson(z["xz"], z["yz"]), pd.Series(per)


def lag_table(exposure, imports, lags=(0, 1, 2, 3)):
    """시차별 상관을 네 가지 방식으로 나란히 (표본은 시차마다 따로 잡는다).

    Pearson      값 그대로의 상관. 큰 계약 한 건에 끌려갈 수 있다
    최대 주문 제외  그 시차에서 수입이 가장 컸던 해를 빼고 다시 잰 Pearson. Pearson과 크게 다르면 계약 한 건 효과
    변화량        전년 대비 변화끼리의 상관. 장기 추세를 걷어낸 값
    Spearman     순위 상관 (막대그래프와 같은 값)
    """
    rows = []
    # 연도 축을 빈틈없이 편 뒤 'k년 뒤'를 연도로 맞춘다 (행 기준으로 당기면 빠진 해에서 짝이 밀린다)
    yrs = range(int(min(exposure.index)), int(max(exposure.index)) + 1) if len(exposure) else range(0)
    e = exposure.reindex(yrs)
    for k in lags:
        imp_k = pd.Series(imports.reindex([y + k for y in yrs]).values, index=list(yrs))
        both = pd.DataFrame({"risk": e, "imp": imp_k})
        pair = both.dropna()
        ok = len(pair) >= 5
        keep = pair["imp"] != pair["imp"].max()
        delta = both.diff().dropna()          # 연속한 두 해가 다 있을 때만 변화량
        rows.append({
            "수입 시점": "같은 해" if k == 0 else f"{k}년 뒤",
            "Pearson": _pearson(pair["risk"], pair["imp"]) if ok else float("nan"),
            "최대 주문 제외": _pearson(pair.loc[keep, "risk"], pair.loc[keep, "imp"]) if ok else float("nan"),
            "변화량": _pearson(delta["risk"], delta["imp"]) if len(delta) >= 5 else float("nan"),
            "Spearman": _spearman(pair["risk"], pair["imp"]) if ok else float("nan"),
            "비교한 해": len(pair),
        })
    return pd.DataFrame(rows)


def _pearson(x, y):
    """피어슨 상관을 더하기·곱하기만으로 계산 (Series.corr는 이 PC의 myenv에서 프로세스를 죽인다)."""
    dx, dy = x - x.mean(), y - y.mean()
    denom = ((dx * dx).sum() * (dy * dy).sum()) ** 0.5
    return float((dx * dy).sum() / denom) if denom > 0 else float("nan")


def _spearman(x, y):
    """순위를 매긴 뒤 피어슨 상관을 직접 계산한다.

    이 PC의 myenv에서는 Series.corr / np.corrcoef가 행렬 계산 라이브러리(BLAS)를 부르다
    프로세스가 통째로 죽어서, 더하기·곱하기만으로 계산한다.
    """
    dx = x.rank() - x.rank().mean()
    dy = y.rank() - y.rank().mean()
    denom = ((dx * dx).sum() * (dy * dy).sum()) ** 0.5
    return float((dx * dy).sum() / denom) if denom > 0 else float("nan")


# ---------------------------------------------------------------- 급증 찾기 (지금 화면에서는 안 씀 · 나중에 세부 분석 결과용)

# 급증 기준: 직전 12개월 평균보다 표준편차 2배 이상, 그리고 0.1 이상 오르고, 리스크가 0.3 이상인 달
SPIKE_WINDOW, SPIKE_K, SPIKE_MIN_JUMP, SPIKE_FLOOR = 12, 2.0, 0.1, 0.3


def detect_spikes(series, gaps):
    """월별 국가쌍 리스크(열 = 상대국)에서 평소보다 크게 튄 달을 찾는다.

    평소 수준 = 그 달을 뺀 직전 12개월 평균. 원본이 빠진 달은 계산에서 뺀다.
    돌려주는 값: 상대국, date, risk, baseline, jump 열을 가진 표
    """
    s = series.copy()
    s.loc[s.index.isin(gaps)] = float("nan")
    past = s.shift(1).rolling(SPIKE_WINDOW, min_periods=6)
    base = past.mean()
    sd = past.std().clip(lower=0.05)          # 늘 조용한 관계는 표준편차가 0에 가까워 작은 변화도 튀어 보이므로 하한을 둔다
    hit = (s > base + SPIKE_K * sd) & (s >= SPIKE_FLOOR) & (s - base >= SPIKE_MIN_JUMP)
    idx = hit.stack()
    idx = idx[idx].index
    out = pd.DataFrame({"risk": s.stack()[idx], "baseline": base.stack()[idx]}).reset_index()
    out.columns = ["date", "partner", "risk", "baseline"]
    out["jump"] = out["risk"] - out["baseline"]
    return out


# ---------------------------------------------------------------- 문장 도우미

def jo(word, pair="이가"):
    """단어 뒤 조사를 받침에 맞게 고른다. pair = '이가' · '은는' · '을를' · '과와'.
    예) jo('이란') → '이', jo('이라크') → '가'. 한글이 아니면(UAE 등) 받침 없는 쪽."""
    ch = str(word).strip()[-1:]
    has_final = "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 != 0
    return pair[0] if has_final else pair[1]
