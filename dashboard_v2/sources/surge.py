"""리스크와 무기 거래 › 세부 분석 결과 탭의 계산 (화면은 dashboard/surge_page.py).

2026-09-29 팀원의 급증과_무기거래/analysis.py 를 그대로 옮겼다. 바꾼 것은 자료 위치 한 줄뿐
(그 폴더의 데이터/ 복사본 → 대시보드 data/ 의 같은 파일). 계산 · 기준 · 숫자는 원본과 같다.
원본 폴더는 unused_data/급증과_무기거래_원본/ 에 보관.

[원본 설명]
갈등 급증과 무기 수입 — 계산을 모아 둔 곳.

이 앱이 답하려는 것은 하나입니다.
    «갈등이 급증한 뒤 무기 수입은 어떻게 움직이는가»

필요한 파일은 두 개뿐입니다 (둘 다 대시보드 data/ 에 있다).
    data/country_monthly_1980_2026.csv   국가별 월별 리스크
    data/SIPRI_pre_1980_2025.csv         무기 수입 계약
"""
import math

import numpy as np
import pandas as pd
import streamlit as st

from core.paths import DATA_DIR as DATA   # 원본 pjL/data/ (core/paths.py)      # 대시보드 data/ (원본은 그 폴더의 데이터/)

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

# ── 급증 기준 ────────────────────────────────────────────────────────
# 직전 12개월 평균보다 표준편차 2배 이상, 그리고 0.1 이상 오르고, 리스크가 0.3 이상인 달.
# 세 조건을 함께 거는 이유 — 표준편차 조건만 쓰면 «0.02 에서 0.05 로» 같은 변화도 급증이 된다.
WIN, K, MIN_JUMP, FLOOR, SD_FLOOR = 12, 2.0, 0.1, 0.3, 0.05

# GDELT 서버에 원본이 절반 넘게 빠진 달. 이 달은 급증 판정에서 뺀다.
GAPS = {pd.Timestamp(2025, 6, 1)}

# 사건연도(0년) 가운데 «제재·내전으로 거래 자체가 끊긴» 경우.
# 수요가 준 것이 아니라 살 수 없게 된 것이라, 나머지와 섞어 읽으면 안 된다.
EMBARGO = {
    ("IRQ", 1990): "UN 제재", ("IRQ", 1991): "UN 제재",
    ("SYR", 1992): "국제 고립", ("SYR", 2010): "내전 직전", ("SYR", 2011): "내전·제재",
    ("IRN", 2006): "핵 제재", ("YEM", 1994): "내전", ("YEM", 2011): "내전·봉쇄",
}

SHAPES = {
    "A": ("이듬해 정점 후 감소", "급증 이듬해 주문 규모가 정점에 이른 뒤 감소"),
    "B": ("2년 뒤 정점", "급증 2년 뒤 주문 규모가 정점에 도달"),
    "C": ("3년 뒤 정점", "급증 3년 뒤 주문 규모가 정점에 도달"),
    "D": ("들쭉날쭉", "위 어디에도 맞지 않는다"),
}
SHAPE_COLOR = {"A": "#0072b2", "B": "#56b4e9", "C": "#009e73", "D": "#8b98ad"}


# ── 자료 읽기 ────────────────────────────────────────────────────────
@st.cache_data
def load_country():
    """국가별 월별 리스크 (country, date, all_risk, days_in_month)."""
    df = pd.read_csv(DATA / "country_monthly_1980_2026.csv", encoding="utf-8-sig")
    df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
    return df[["country", "date", "all_risk", "days_in_month"]]


@st.cache_data
def load_sipri():
    df = pd.read_csv(DATA / "SIPRI_pre_1980_2025.csv", encoding="utf-8-sig")
    df["code"] = df["importer"].map(SIPRI_CODE)
    return df.dropna(subset=["code"])


# ── 급증 찾기 ────────────────────────────────────────────────────────
def detect_spikes(mat):
    """월별 리스크(행 = 달, 열 = 나라)에서 평소보다 크게 튄 달을 찾는다.

    두 단계로 나눠 읽으면 된다.
        ① 나라 × 달마다 «그 달 값 · 평소 · 평소의 출렁임» 을 한 줄로 만든다
        ② 조건 세 개를 걸어 급증한 줄만 남긴다
    """
    s = mat.copy()
    s.loc[s.index.isin(GAPS)] = np.nan          # 원본이 빠진 달은 판정에서 뺀다

    # 평소 = 그 달을 뺀(shift) 직전 12개월. 여섯 달만 있어도 계산한다.
    past = s.shift(1).rolling(WIN, min_periods=6)

    # ① 세 값을 나란히 세워 «나라 × 달» 한 줄짜리 표로 눕힌다
    long = pd.DataFrame({
        "risk": s.stack(),                              # 그 달 값
        "base": past.mean().stack(),                    # 평소
        "sd": past.std().clip(lower=SD_FLOOR).stack(),  # 평소의 출렁임 (바닥값 0.05)
    }).reset_index()
    long.columns = ["date", "country", "risk", "base", "sd"]
    long["jump"] = long["risk"] - long["base"]          # 상승폭

    # ② 세 조건을 모두 만족해야 급증.
    #    표준편차 조건만 쓰면 «0.02 에서 0.05 로» 같은 변화도 급증이 되므로
    #    최소 수준(FLOOR)과 최소 상승폭(MIN_JUMP)을 함께 건다.
    is_spike = ((long["risk"] > long["base"] + K * long["sd"])
                & (long["risk"] >= FLOOR)
                & (long["jump"] >= MIN_JUMP))
    return long[is_spike][["date", "country", "risk", "base", "jump"]].reset_index(drop=True)


def _annual_risk():
    """월별 종합 리스크 → 나라 × 연도.

    그 달 일수로 가중해 평균한다. 단순 평균을 쓰면 2월(28일)과 7월(31일)이 같은 한 표가 되어
    일별에서 낸 값과 어긋난다. 12개월이 다 있는 해만 남긴다 (2026년은 9월까지라 빠진다).
    """
    c = load_country().copy()
    c["year"] = c["date"].dt.year
    c["w"] = c["all_risk"] * c["days_in_month"]          # 월 리스크 × 그 달 일수
    ann = (c.groupby(["country", "year"])
           .agg(w=("w", "sum"), d=("days_in_month", "sum"), n=("all_risk", "size"))
           .reset_index())
    ann = ann[ann["n"] == 12]                            # 12개월이 다 있는 해만
    ann["risk"] = ann["w"] / ann["d"]                    # ÷ 그해 총 일수
    return ann[["country", "year", "risk"]]


def _arms():
    """SIPRI 계약 → 나라 × 연도별 주문 TIV 합.

    16개국 × 전 기간 격자를 먼저 깔고 채운다. 그래야 «수입이 0이던 해» 가 행째로 사라지지 않는다.
    """
    sp = load_sipri()
    imp = (sp.groupby(["code", "year"])["tiv_order"].sum()
           .rename("tiv").reset_index().rename(columns={"code": "country"}))
    grid = pd.MultiIndex.from_product(
        [list(COUNTRIES), range(1980, int(sp["year"].max()) + 1)],
        names=["country", "year"]).to_frame(index=False)
    out = grid.merge(imp, on=["country", "year"], how="left")
    out["tiv"] = out["tiv"].fillna(0.0)
    # 로그를 씌워 큰 계약 한 건이 결과를 독차지하지 않게 한다. +1 은 0 인 해도 계산되게.
    out["ltiv"] = (out["tiv"] + 1.0).apply(math.log)
    return out


def _surge_score():
    """급증한 달 → 나라 × 연도별 «상승폭 합». 0년을 고르는 점수."""
    mat = load_country().pivot(index="date", columns="country", values="all_risk")
    sp = detect_spikes(mat)
    sp["year"] = sp["date"].dt.year
    return sp.groupby(["country", "year"])["jump"].sum().rename("surge_j").reset_index()


def _pick_event_years(score):
    """상승폭 합이 큰 해부터 그 나라 해 수의 25% 를 사건연도로 고른다.

    «급증한 달 수» 로 끊지 않는 이유 — 달 수는 0·1·2 에 몰려 있어 상위 25% 경계가 1 에 깔리고,
    결국 «한 번이라도 급증한 해» 가 된다. 그러면 사건연도 비율이 나라마다 11%~57% 로 벌어진다.
    """
    has_surge = score[score > 0]
    if has_surge.empty:
        return score > 0                                  # 급증이 아예 없으면 전부 False
    n = min(max(1, round(len(score) * 0.25)), len(has_surge))   # 급증이 적으면 있는 만큼만
    return score.index.isin(has_surge.nlargest(n).index)


@st.cache_data
def panel():
    """나라 × 연도 표 — 연 리스크 · 무기 수입 · 급증 세기 · 사건연도(0년).

    위 네 조각(_annual_risk · _arms · _surge_score · _pick_event_years)을 붙이기만 한다.

    risk     연 리스크 (일수 가중 평균)
    tiv      그해 주문 TIV 합,  ltiv = log(1 + tiv)
    surge_j  그해 급증한 달들의 상승폭 합
    z_imp    ltiv 를 그 나라 안에서 표준화 (0 = 평소, +1 = 평소보다 한 칸 많이 산 해)
    ev       사건연도이면 True
    """
    m = (_arms()
         .merge(_annual_risk(), on=["country", "year"], how="left")
         .merge(_surge_score(), on=["country", "year"], how="left"))
    m["surge_j"] = m["surge_j"].fillna(0.0)

    # 나라마다 규모가 수십 배 다르므로, 각 나라를 «자기 평소» 와만 견주게 만든다.
    m["z_imp"] = m.groupby("country")["ltiv"].transform(
        lambda x: (x - x.mean()) / x.std() if x.std() > 0 else x * 0.0)
    m["ev"] = m.groupby("country")["surge_j"].transform(_pick_event_years)

    return m.dropna(subset=["risk"]).reset_index(drop=True)


# ── 사건 하나하나 ────────────────────────────────────────────────────
def _pearson(x, y):
    """피어슨 상관을 더하기·곱하기만으로 계산 (BLAS 를 부르지 않아 어디서나 안전하다)."""
    dx, dy = x - x.mean(), y - y.mean()
    den = ((dx * dx).sum() * (dy * dy).sum()) ** 0.5
    return float((dx * dy).sum() / den) if den > 0 else float("nan")


@st.cache_data
def lag_corr(m, k):
    """그해 연 Risk 와 <b>k년 뒤</b> 무기 수입(log)의 상관.

    나라마다 규모가 수십 배 달라, 각 나라를 자기 평소와만 견주도록 나라 안에서 표준화한 뒤
    16개국 데이터를 통합하여 분석한다. 그렇게 하지 않으면 «사우디가 바레인보다 둘 다 크다» 는
    나라 사이의 차이가 상관으로 잡힌다.

    돌려주는 값: (16개국을 합쳐 잰 r, 나라별 r Series)
    """
    d = m.copy()
    d["y"] = d.groupby("country")["ltiv"].shift(-k)
    d = d.dropna(subset=["risk", "y"])
    per, parts = {}, []
    for cc, g in d.groupby("country"):
        if len(g) < 5 or g["risk"].std() == 0 or g["y"].std() == 0:
            continue
        per[cc] = _pearson(g["risk"], g["y"])
        parts.append(pd.DataFrame({
            "xz": (g["risk"] - g["risk"].mean()) / g["risk"].std(),
            "yz": (g["y"] - g["y"].mean()) / g["y"].std()}))
    pool = pd.concat(parts)
    return _pearson(pool["xz"], pool["yz"]), pd.Series(per).sort_values(ascending=False)


def _shape(post):
    """뒤 3년의 모양. t+1 최고이면서 계단식으로 내려가면 A, t+2 최고면 B, t+3 최고면 C."""
    i = int(np.argmax(post))
    if i == 0 and post[0] > post[1] > post[2]:
        return "A"
    return {1: "B", 2: "C"}.get(i, "D")


@st.cache_data
def cases(m, only_full=True):
    """0년 한 건이 한 줄. 나라별 평균이 아니라 «사건 단위» 다.

    pre/post  0년의 −2·−1년 / +1·+2·+3년 z_imp 평균
    diff      post − pre (그 나라 평소 대비 «칸»)
    full      앞 2년·뒤 3년이 모두 있으면 True.
              자료가 2025년까지라 최근 0년은 뒤가 한두 해뿐이고, 그러면 diff 가 부풀려진다.
    """
    rows = []
    for cc, g in m.groupby("country"):
        z = g.set_index("year")["z_imp"]
        t = g.set_index("year")["tiv"]
        for y in g.loc[g["ev"], "year"]:
            pre = [z.get(y - k, np.nan) for k in (2, 1)]
            post = [z.get(y + k, np.nan) for k in (1, 2, 3)]
            pre = [v for v in pre if pd.notna(v)]
            post = [v for v in post if pd.notna(v)]
            if not pre or not post:
                continue
            full = len(pre) == 2 and len(post) == 3
            if only_full and not full:
                continue
            yrs = [int(k) for k in range(y - 2, y + 4) if k in t.index]
            tiv = [float(t[k]) for k in yrs]
            post_tiv = [float(t.get(y + k, 0.0)) for k in (1, 2, 3)]
            rows.append({
                "country": cc, "ko": COUNTRIES[cc], "year": int(y),
                "pre": float(np.mean(pre)), "post": float(np.mean(post)),
                "diff": float(np.mean(post) - np.mean(pre)), "full": full,
                "years": yrs, "tiv": tiv,
                "shape": _shape(post_tiv),
                "embargo": EMBARGO.get((cc, int(y)), ""),
            })
    return pd.DataFrame(rows).sort_values("diff", ascending=False).reset_index(drop=True)


# ── 평균 회귀 검증 ───────────────────────────────────────────────────
@st.cache_data
def control(m):
    """급증한 해뿐 아니라 «모든 해» 를 같은 방식으로 계산해 비교군을 만든다.

    출발점(앞 수준)이 같은 것끼리 견주면, 급증이 그 위에 무엇을 더하는지 볼 수 있다.
    """
    rows = []
    for cc, g in m.groupby("country"):
        z = g.set_index("year")["z_imp"]
        for r in g.itertuples():
            y = r.year
            pre = [z.get(y - k, np.nan) for k in (2, 1)]
            post = [z.get(y + k, np.nan) for k in (1, 2, 3)]
            pre = [v for v in pre if pd.notna(v)]
            post = [v for v in post if pd.notna(v)]
            if len(pre) < 2 or len(post) < 3:
                continue
            rows.append({"country": cc, "year": int(y), "ev": bool(r.ev),
                         "pre": float(np.mean(pre)), "post": float(np.mean(post)),
                         "diff": float(np.mean(post) - np.mean(pre))})
    d = pd.DataFrame(rows)
    d["구간"] = pd.qcut(d["pre"], 5, labels=["매우 낮음", "낮음", "보통", "높음", "매우 높음"])
    t = d.pivot_table(index="구간", columns="ev", values="diff",
                      aggfunc=["mean", "size"], observed=True)
    t.columns = ["그 밖 변화", "급증 변화", "그 밖 n", "급증 n"]
    t["차이"] = t["급증 변화"] - t["그 밖 변화"]
    w = t["급증 n"] / t["급증 n"].sum()
    return d, t.reset_index(), float((t["차이"] * w).sum())


def streak_rate(m):
    """뒤 3년이 계단식 감소(t+1 > t+2 > t+3)인 비율 — 급증한 해 vs 그 밖의 해."""
    out = {}
    for lab, want in [("급증한 해", True), ("그 밖의 해", False)]:
        hit = tot = 0
        for cc, g in m.groupby("country"):
            t = g.set_index("year")["tiv"]
            for r in g.itertuples():
                if bool(r.ev) != want:
                    continue
                s = [t.get(r.year + k, np.nan) for k in (1, 2, 3)]
                if any(pd.isna(v) for v in s):
                    continue
                tot += 1
                hit += int(s[0] > s[1] > s[2])
        out[lab] = (hit, tot, hit / tot * 100 if tot else 0.0)
    return out