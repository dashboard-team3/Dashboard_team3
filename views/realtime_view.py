"""① 실시간 모니터링 페이지 (원본 app2.py 의 4.). page() = KPI 카드 · 지도/네트워크 · 최근 사건."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import tip, info_icon, page_sub, term
from core import theme
from sources import realtime


def spark_svg(values, color="#8b98ad", w=110, h=30):
    """작은 추이선(SVG). 값이 2개 미만이면 빈 문자열."""
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    pts = " ".join(f"{i * w / (len(vals) - 1):.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}" for i, v in enumerate(vals))
    lx, ly = pts.split()[-1].split(",")
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}"/>'
            f'<circle cx="{lx}" cy="{ly}" r="2.6" fill="{color}"/></svg>')


def live_card(label, value, sub, tone="", delta=None, spark="", label_tip=""):
    """KPI 카드: 라벨 / 큰 값(+전일 동시간대 대비) / 설명 한 줄 / 오른쪽 아래 작은 추이선."""
    d = ""
    if delta is not None:
        cls = "up" if delta > 0 else "down" if delta < 0 else "flat"
        d = tip(f'{"▲" if delta > 0 else "▼" if delta < 0 else "–"} {abs(delta):,}',
                "전일 동일 시각 대비 사건 건수 증감", f"delta {cls}")
    return f"""
<div class="kpi live {tone}">
  <div>
    <div class="lbl">{tip(label, label_tip) if label_tip else label}</div>
    <div class="val">{value}{d}</div>
    <div class="sub">{sub}</div>
  </div>{spark}
</div>
"""


@st.cache_data(ttl=300)
def daily_totals(n=7):
    """최근 n일의 하루 총 사건 수 (실시간 폴더 기준, 오래된 날부터)."""
    days = realtime.recent_days(n)                       # 자료가 있는 최근 n일 (DB, 안 되면 파일 폴더)
    return days, [len(realtime.load_day(d)) for d in days]


@st.cache_data(ttl=60)
def yesterday_same_time(slot):
    """어제 00:00(UTC)부터 오늘 마지막 수집 시각과 같은 시각까지의 건수, 어제 하루 전체 건수.
    오늘은 하루가 다 차지 않았으므로 어제 하루 전체가 아니라 같은 시각까지와 견줘야 공정하다."""
    from datetime import datetime, timedelta
    if not slot:
        return None, None
    y = (datetime.strptime(slot[:8], "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
    df = realtime.load_day(y)
    if df.empty:
        return None, None
    upto = int((df["TIMESTAMP"].str[8:14] <= slot[8:14]).sum())      # 시·분·초가 오늘 마지막 수집 시각 이하
    return upto, len(df)


@st.fragment(run_every="60s")
def live_kpis():
    """run_realtime.py 결과로 카드 3개를 그린다. 이 부분만 60초마다 다시 실행된다."""
    k = realtime.kpis()

    days, totals = daily_totals()
    slot = realtime.last_slot()
    y_same, y_all = yesterday_same_time(slot)

    if y_same is not None:
        sub = (f"전일 동일 시각({slot[8:10]}:{slot[10:12]} UTC)까지 {y_same:,}건 · 전일 전체 {y_all:,}건 · "
               f"최근 {len(totals)}일 추이")
    else:
        sub = f"중동 국가 간 · 최근 {len(totals)}일 추이"
    c1, c2, c3 = st.columns(3)
    c1.markdown(live_card("당일 누적 사건 (UTC)", f"{k['total']:,}", sub, "blue",
                          label_tip="UTC 기준 오늘 0시(한국 오전 9시)부터 들어온 중동 16개국끼리의 갈등 사건 수. "
                                    "오른쪽 작은 선 = 최근 7일 하루 건수",
                          delta=(k["total"] - y_same) if y_same is not None else None,   # 전일 동시간대 대비
                          spark=spark_svg(totals, "#93c5fd")),
                unsafe_allow_html=True)
    c2.markdown(live_card("최근 수신", f"+{k['recent']}", "최신 15분 수집 구간",
                          label_tip="최신 15분 구간에 수집된 사건 수 · GDELT 자료 15분 단위 수집"),
                unsafe_allow_html=True)
    
    if k["top"]:
        name, count, partner = k["top"]
        c3.markdown(live_card("최다 관여국", name, f"{count}건 · 최다 상대국 {partner}", "red",
                              label_tip="당일 사건의 행위 주체·대상으로 가장 많이 기록된 국가 및 최다 상대국"),
                    unsafe_allow_html=True)
    else:
        c3.markdown(live_card("최다 관여국", "-", "당일 수집 사건 없음", "red"),
                    unsafe_allow_html=True)

    if k["slot_kst"]:
        st.caption(f"마지막 수신 구간 {k['slot_kst']} KST (UTC {k['slot_utc']}) · 60초마다 자동 갱신")
    else:
        st.caption(":exclamation: 실시간 수집 상태 미확인")


MAP_CENTER = dict(lat=27.2, lon=44.0)   # 튀르키예(북)와 예멘(남) 사이 가운데
MAP_ZOOM = 4.15  # 처음 그릴 때의 배율. 실제 시작 배율은 FIT_SCRIPT가 패널 크기를 재서 다시 맞춘다


LABEL_FONT = 19   # 지도 나라 이름 글자 크기(px)


def _label_placement(radius, side):
    """이름을 원 바깥에 붙이기 위한 (글자 기준점, 가로·세로 거리[em]).

    브라우저 스크립트(FIT_SCRIPT)가 이 값을 지도 레이어의 text-anchor / text-offset 으로 넣는다.
    거리는 글자 크기 단위(em)인데 원 반지름(px)으로 계산하므로, 화면 배율과 상관없이
    이름이 항상 원 바로 바깥에 붙는다.
    """
    gap = (radius + 6) / LABEL_FONT
    if side == "middle left":
        return "right", [-gap, 0]
    if side == "middle right":
        return "left", [gap, 0]
    if side == "top center":
        return "bottom", [0, -gap]
    if side == "bottom right":
        d = (radius * 0.75 + 2) / LABEL_FONT
        return "top-left", [d, d]
    return "top", [0, gap]                     # bottom center (기본)


# 패널 높이는 style.css에서 화면 높이(100vh)에 맞춰 정하고, 차트는 그 안의 남은 높이를 채운다.


# (2026-10-01) 중동_스토리맵의 지도 모양 · LIVE 패널 · 범례 상자를 가져왔다.
# 나라 면을 오늘 사건 수로 주황 한 색의 밝기로 칠하고, 이름 · 숫자를 나라 위에 적는다.
# 보라 (2026-10-02 팀 요청, 예전 주황 — 밝은 테마 #f4ede7 → #a8481f · 어두운 테마 #262a33 → #f6b98d 스토리맵 주황).
# 어두운 테마도 같은 색. 칸 안 이름은 칸 색에 따라: 진한 칸(LABEL_DARK 이상)은 흰 글씨, 옅은 칸은 검은 글씨
SEQ_LIGHT = [theme.C[k] for k in ("main-40", "main-130", "main-230", "main-350", "main-570", "main-740")]
SEQ_DARK = SEQ_LIGHT
LABEL_DARK = 0.7


# 나라: (실제 위치 위도, 경도, 이름 위도, 경도)
# 레반트 3곳은 지중해 쪽 왼편, 걸프 3곳은 바다 쪽 오른편에 한 줄로 적는다.
LABEL_OUT = {
    "레바논": (33.9, 35.8, 35.0, 33.4), "이스라엘": (31.6, 34.85, 33.6, 32.8), "팔레스타인": (31.9, 35.25, 32.2, 32.3),
    "쿠웨이트": (29.3, 47.7, 29.7, 49.2), "바레인": (26.05, 50.55, 27.0, 51.6), "카타르": (25.3, 51.2, 25.7, 52.3),
}
LEFT_SIDE = {"레바논", "이스라엘", "팔레스타인"}


def _scale(colors):
    return [[i / (len(colors) - 1), c] for i, c in enumerate(colors)]


def draw_map():
    """오늘(UTC) 나라별 사건 수로 중동 16개국 면을 칠한다. 이웃 땅은 흐리게 깔고,
    최근 1시간 안에 사건이 난 나라는 빨간 점이 깜빡인다. 범례는 왼쪽 범례 상자(live_legend)."""
    from sources.relations import COUNTRIES as ISO_KR
    kr_iso = {v: k for k, v in ISO_KR.items()}
    light = theme.is_light()
    df = realtime.load_day(realtime.today_utc())
    stats = realtime.country_stats(df)
    stats["iso"] = stats["country"].map(kr_iso)
    stats["hover"] = stats.apply(lambda r: (
        f"<b>{r['country']}</b> 오늘 {r['count']}건<br>"
        + "<br>".join(f"{cat} {n}" for cat, n in r["by_category"].items() if n)
        + (f"<br>최다 상대국 {r['top_partner']}" if r["top_partner"] else "")
    ) if r["count"] else f"<b>{r['country']}</b> 오늘 0건", axis=1)
    poly = stats.dropna(subset=["iso"])
    zmax = max(1.0, float(poly["count"].max()) ** 0.5)

    fig = go.Figure()
    # 1) 나라 면: 사건 수의 제곱근으로 칠한다 (54건과 2건이 둘 다 구분되게)
    fig.add_trace(go.Choropleth(
        locations=poly["iso"], z=poly["count"] ** 0.5, locationmode="ISO-3", showscale=False,
        colorscale=_scale(SEQ_LIGHT if light else SEQ_DARK), zmin=0, zmax=zmax,
        marker_line_color="#ffffff" if light else theme.C["main-bg-930"], marker_line_width=0.9,
        customdata=poly["hover"], hovertemplate="%{customdata}<extra></extra>"))
    # 2) 이름 + 숫자. 좁은 나라(LABEL_OUT)는 이름을 바깥으로 빼고 가는 선으로 잇는다
    name_col = "#1c1a17" if light else "#ffffff"
    frac = {c: (n ** 0.5) / zmax for c, n in zip(stats["country"], stats["count"])}     # 색 막대에서의 자리 (0~1)

    def col(c):   # 칸 안 이름: 진한 보라 칸은 흰 글씨 · 옅은 칸은 검은 글씨. 바깥으로 뺀 이름은 땅 위라 테마 글자색
        if c in LABEL_OUT:
            return name_col
        return "#ffffff" if frac.get(c, 0) >= LABEL_DARK else "#1c1a17"
    pos = {r.country: (LABEL_OUT[r.country][2:] if r.country in LABEL_OUT else (r.lat, r.lon)) for r in stats.itertuples()}
    llat, llon = [], []
    for name, (a_lat, a_lon, t_lat, t_lon) in LABEL_OUT.items():
        llat += [a_lat, t_lat, None]; llon += [a_lon, t_lon, None]
    fig.add_trace(go.Scattergeo(lat=llat, lon=llon, mode="lines", hoverinfo="skip",
                                line=dict(width=0.8, color="rgba(28,26,23,.45)" if light else "rgba(255,255,255,.45)")))
    fig.add_trace(go.Scattergeo(
        lat=[pos[c][0] for c in stats["country"]], lon=[pos[c][1] for c in stats["country"]],
        mode="text", hoverinfo="skip",
        text=[(f"<b>{lb}</b> {n}" if c in LABEL_OUT else f"<b>{lb}</b><br>{n}")
              for c, lb, n in zip(stats["country"], stats["label"], stats["count"])],
        textposition=[("middle left" if c in LEFT_SIDE else "middle right") if c in LABEL_OUT else "middle center"
                      for c in stats["country"]],
        textfont=dict(size=13, color=[col(c) for c in stats["country"]], family="JetBrains Mono, Pretendard, sans-serif")))
    # 3) 최근 1시간 안에 사건이 난 나라: 빨간 점 (CSS 로 깜빡임)
    hot = live_side_data(realtime.last_slot() or "")["active"]
    act = stats[stats["country"].isin(hot)]
    if len(act):
        fig.add_trace(go.Scattergeo(
            lat=[LABEL_OUT[c][0] if c in LABEL_OUT else la - 1.0 for c, la in zip(act["country"], act["lat"])],
            lon=[LABEL_OUT[c][1] if c in LABEL_OUT else lo for c, lo in zip(act["country"], act["lon"])],
            mode="markers", hoverinfo="skip",
            marker=dict(size=9, color="#e66767", line=dict(width=0))))
    fig.update_layout(
        geo=dict(projection_type="mercator", fitbounds="locations", visible=True,
                 showland=True, landcolor="#ffffff" if light else theme.C["main-bg-930"],          # 주변 땅 = 지도 상자 바탕색 (리스크 추이와 같게, 2026-10-02)
                 showcountries=light, countrycolor="#e5e7eb" if light else theme.C["main-dark-820"], countrywidth=0.6,   # 다크: 중동 밖 경계선 없음 (2026-10-02)
                 showcoastlines=False, showocean=False, showlakes=False, showframe=False,
                 bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False, autosize=True,
        paper_bgcolor="rgba(0,0,0,0)", dragmode="pan",
        uirevision="live-geo",   # 1분마다 다시 그려도 사용자가 옮긴 확대·위치를 유지
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3", size=15)))
    st.markdown("""<style>
      .st-key-live_map_chart .js-plotly-plot {opacity: 1 !important; animation: none !important;}   /* 타일 지도용 '준비될 때까지 숨김' 끔 */
      .st-key-main_panel, .st-key-feed_panel {min-height: 932px !important;}   /* (2026-10-02) 지도 크기를 리스크 추이 지도와 같게 (720px) → 지도도 같은 크기 */
      [data-testid="stHorizontalBlock"]:has(.st-key-feed_panel) > [data-testid="stColumn"]:last-child {flex: 0 0 max(340px, 29.3%) !important;}   /* 칸 폭도 리스크 추이(2.3 : 1)와 같게 */

      /* (2026-10-02) 가장자리 흐림(mask)은 뺐다 — 지도는 그래프처럼 상자 안 */
      .st-key-live_map_chart .scattergeo path.point {animation: lvping 1.6s ease-in-out infinite;}
      @keyframes lvping {0%, 100% {opacity: 1;} 50% {opacity: .15;}}
      .st-key-main_panel:has(.st-key-live_map_chart) {background: var(--color-main-bg-930) !important;}   /* 리스크 추이 칸 · 다른 카드와 같은 바탕 */
      /* (2026-10-02 hnaa0) 밝은 테마 연한 하늘색 바탕은 뺌 — 카드 모양(style_light.css)을 따름 */
    </style>""", unsafe_allow_html=True)

    # 마우스를 올리면 오른쪽 위에 확대(+)·축소(−)·처음 위치 버튼만 보인다. 휠 확대는 스크롤과 충돌해서 끈다.
    st.plotly_chart(fig, key="live_map_chart", width="stretch", height="stretch",
                    config={"responsive": True, "scrollZoom": False, "displaylogo": False,
                            "modeBarButtons": [["zoomInGeo", "zoomOutGeo", "resetGeo"]]})
    return int(poly["count"].max()) if len(poly) else 0


@st.cache_data(ttl=60)
def live_side_data(slot):
    """LIVE 패널 숫자 (스토리맵 build_live 와 같은 기준).
    최근 24시간 건수 · 최근 14일 하루 건수(한국 날짜, 오늘은 진행 중) · 오늘을 뺀 7일 평균 ·
    24시간 최다 국가쌍 3개 · 최근 1시간 안에 사건이 난 나라."""
    empty = {"slot_kst": None, "mins": None, "n24": 0, "daily": [], "avg7": 0.0, "pairs": [], "active": []}
    if not slot:
        return empty
    last = pd.to_datetime(slot, format="%Y%m%d%H%M%S")
    days = [(last - pd.Timedelta(days=i)).strftime("%Y%m%d") for i in range(15, -1, -1)]
    frames = [f for f in (realtime.load_day(d) for d in days) if not f.empty]
    if not frames:
        return empty
    ev = pd.concat(frames, ignore_index=True)
    ev["ts"] = pd.to_datetime(ev["TIMESTAMP"], format="%Y%m%d%H%M%S")
    ev = ev[ev["ts"] <= last]
    day = ev[ev["ts"] > last - pd.Timedelta(hours=24)]

    kst_day = (ev["ts"] + pd.Timedelta(hours=9)).dt.normalize()
    today = (last + pd.Timedelta(hours=9)).normalize()
    per_day = kst_day.value_counts()
    daily = [{"d": f"{d:%m.%d}", "n": int(per_day.get(d, 0)), "today": bool(d == today)}
             for d in pd.date_range(today - pd.Timedelta(days=13), today, freq="D")]
    avg7 = float(sum(x["n"] for x in daily[-8:-1]) / 7)

    pairs = (day.groupby(["Actor1Country_KR", "Actor2Country_KR"]).size()
             .sort_values(ascending=False).head(3))
    hot = day[day["ts"] > last - pd.Timedelta(hours=1)]
    now = pd.Timestamp.now(tz="UTC").tz_localize(None)
    return {
        "slot_kst": (last + pd.Timedelta(hours=9)).strftime("%H:%M"),
        "mins": max(0, int((now - last).total_seconds() // 60)),
        "n24": int(len(day)), "daily": daily, "avg7": round(avg7, 1),
        "pairs": [(a, b, int(n)) for (a, b), n in pairs.items()],
        "active": sorted(set(hot["Actor1Country_KR"]) | set(hot["Actor2Country_KR"])),
    }


def live_panel():
    """왼쪽 LIVE 패널: 최종 수집 · 최근 24시간 건수(7일 평균 대비) · 14일 막대 · 최다 국가쌍."""
    L = live_side_data(realtime.last_slot() or "")
    if not L["slot_kst"]:
        st.markdown('<div class="lv"><div class="lv-hd"><span class="lv-dot off"></span>LIVE</div>'
                    '<div class="lv-when stale">실시간 수집 상태 미확인</div></div>',
                    unsafe_allow_html=True)
        return
    m = L["mins"]
    ago = f"{m}분 전" if m < 60 else f"{m // 60}시간 {m % 60}분 전"
    when = (f'<div class="lv-when stale">⚠ 최종 수집 {L["slot_kst"]} KST · {ago} (수집 지연)</div>' if m > 45
            else f'<div class="lv-when">최종 수집 {L["slot_kst"]} KST · {ago}</div>')
    delta = ""
    if L["avg7"]:
        diff = round((L["n24"] - L["avg7"]) / L["avg7"] * 100)
        delta = (f'<span class="lv-delta {"up" if diff > 0 else "down"}">'
                 f'{"▲" if diff > 0 else "▼"}{abs(diff)}%</span>')
    top = max([x["n"] for x in L["daily"]] + [L["avg7"], 1])
    bars = "".join(f'<i class="{"today" if x["today"] else ""}" style="height:{max(4, x["n"] / top * 100):.0f}%" '
                   f'title="{x["d"]} {x["n"]}건{" (진행 중)" if x["today"] else ""}"></i>' for x in L["daily"])
    pairs = "".join(f'<div class="lv-pair"><span>{a} → {b}</span><b>{n}</b></div>' for a, b, n in L["pairs"]) \
        or '<div class="lv-pair"><span>최근 24시간 사건 없음</span></div>'
    st.markdown(f"""
<div class="lv">
  <div class="lv-hd"><span class="lv-dot"></span>LIVE<span class="lv-mono">GDELT · 15분</span></div>
  {when}
  <div class="lv-cnt">최근 24시간 <b>{L["n24"]:,}</b>건{delta}</div>
  <div class="lv-sub">최근 7일 일평균 {L["avg7"]:,.0f}건 대비</div>
  <div class="lv-spark" title="최근 14일 하루 사건 수 (한국 날짜)">{bars}
    <b class="lv-avg" style="bottom:{L["avg7"] / top * 100:.0f}%" title="7일 평균 {L["avg7"]}건"></b></div>
  <div class="lv-ax"><span>{L["daily"][0]["d"]}</span><span>점선: 7일 평균</span><span>오늘</span></div>
  <div class="lv-sec">최다 발생 국가쌍 (24시간)</div>
  {pairs}
</div>""", unsafe_allow_html=True)


def live_legend():
    """지도 칸 아래 범례 상자: 왼쪽 색 막대 · 눈금, 오른쪽 뜻 · 유형별 건수 · 출처."""
    light = theme.is_light()
    seq = SEQ_LIGHT if light else SEQ_DARK
    df = realtime.load_day(realtime.today_utc())
    totals = realtime.category_totals(df)
    max_count = int(realtime.country_stats(df)["count"].max())
    mid = round((max_count ** 0.5 / 2) ** 2)          # 색 막대 가운데 = 제곱근 척도의 절반
    cats = "".join(f'<span><i style="background:{c["color"]}"></i>{cat} {totals[cat]}</span>'
                   for cat, c in realtime.CATEGORIES.items())
    slot = realtime.last_slot()
    upd = f"{realtime.slot_to_kst(slot)} KST" if slot else ""
    st.markdown(f"""
<div class="lv-lg">
  <div class="lv-lg-a">
    <div class="lv-lg-t">당일 국가별 사건 수 (UTC)</div>
    <div class="lv-grad" style="background:linear-gradient(90deg,{','.join(seq)})"></div>
    <div class="lv-ticks"><span>0</span><span>{mid}</span><span>{max_count}건</span></div>
  </div>
  <div class="lv-lg-b">
    <div class="lv-cats">{cats}</div>
    <div class="lv-note">단일 사건은 행위 주체·대상 국가에 각각 집계 · <span class="lv-dot sm"></span> 최근 1시간 내 사건 발생</div>
    <div class="lv-note lv-src">Last updated : {upd}</div>
  </div>
</div>""", unsafe_allow_html=True)


def draw_network(choice):
    """오늘(UTC) 국가쌍 관계를 한 줄 아크 그림으로 그린다 (2026-10-02, 타원 네트워크 대신). choice는 '전체' 또는 사건 유형.
    나라를 지리 순서(이집트 → 걸프 → 이란 → 레반트)로 가로 한 줄에 놓고, 관계는 위로 솟는 반원으로 잇는다.
    반원 굵기 · 진하기 = 건수, 색 = 그 쌍에서 가장 많은 사건 유형. 선끼리 덜 엉켜서 많이 얽힌 나라가 한눈에 보인다."""
    import math
    df = realtime.load_day(realtime.today_utc())
    pairs = realtime.pair_stats(df, None if choice == "전체" else choice)
    pos = realtime.network_positions()                # 순서만 쓴다 (타원 둘레 순서 = 지리 방향)

    if pairs.empty:
        st.info(f"오늘(UTC) '{choice}' 유형에 해당하는 국가쌍 없음")
        return

    light = theme.is_light()
    top = pairs["count"].max()
    involved = pd.concat([
        pairs[["a", "count"]].rename(columns={"a": "n"}),
        pairs[["b", "count"]].rename(columns={"b": "n"}),
    ]).groupby("n")["count"].sum()
    order = sorted(pos, key=lambda n: math.atan2(pos[n][1], pos[n][0] / 2.0))
    X = {n: i for i, n in enumerate(order)}
    ink = "#1c1a17" if light else "#e5eaf3"                # 오늘 사건이 있는 나라 이름 · 점
    dim = "#9ca3af" if light else "#4b5563"                # 오늘 사건 없는 나라
    fig = go.Figure()

    # 1) 국가쌍마다 반원 하나 (굵은 선이 위에 오게 건수 순으로). 높이는 두 나라 사이 거리에 비례
    mids = []
    for r in pairs.sort_values("count").itertuples():
        x0, x1 = sorted((X[r.a], X[r.b]))
        c, rad = (x0 + x1) / 2, (x1 - x0) / 2
        ts = [math.pi * i / 40 for i in range(41)]
        xs = [c - rad * math.cos(t) for t in ts]
        ys = [rad * 0.55 * math.sin(t) for t in ts]
        w = r.count / top
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", hoverinfo="skip",
                                 line=dict(color=realtime.CATEGORIES[r.top_category]["color"], width=1 + 6 * w),
                                 opacity=0.3 + 0.65 * w))
        mids.append((xs[20], ys[20], r))
    # 반원 꼭대기에 보이지 않는 점을 두어 마우스를 올리면 상세가 뜨게 한다
    fig.add_trace(go.Scatter(
        x=[m[0] for m in mids], y=[m[1] for m in mids],
        mode="markers", marker=dict(size=18, color="rgba(0,0,0,0)"),
        customdata=[
            f"<b>{r.a} – {r.b}</b> 오늘 {r.count}건<br>"
            f"{r.a} → {r.b}: {r.a_to_b}건<br>{r.b} → {r.a}: {r.b_to_a}건<br>"
            + " · ".join(f"{c} {n}" for c, n in r.by_category.items() if n)
            for _, _, r in mids],
        hovertemplate="%{customdata}<extra></extra>",
    ))

    # 2) 나라 점: 오늘 연결된 나라는 진하게(크기 = 관여 건수), 나머지는 작고 흐리게
    fig.add_trace(go.Scatter(
        x=[X[n] for n in order], y=[0] * len(order), mode="markers",
        marker=dict(size=[9 + 3 * involved[n] ** 0.5 if n in involved else 6 for n in order],
                    color=[(theme.C["main-light-650"] if light else ink) if n in involved
                           else (theme.C["main-130"] if light else theme.C["main-dark-820"]) for n in order],
                    line=dict(width=0), opacity=1),     # 크기가 목록이면 Plotly 기본 투명도가 0.7 이라 1 로
        customdata=[f"<b>{n}</b> 오늘 {int(involved.get(n, 0))}건" for n in order],
        hovertemplate="%{customdata}<extra></extra>",
    ))
    # 3) 나라 이름: 점 아래 비스듬히 (16개국이 한 줄이라 가로로 쓰면 겹친다)
    for n in order:
        name = realtime.SHORT_NAME.get(n, n)
        fig.add_annotation(x=X[n], y=-0.35, text=f"<b>{name}</b>" if n in involved else name, showarrow=False,
                           textangle=-40, xanchor="right", yanchor="top",
                           font=dict(size=13, color=ink if n in involved else dim))

    fig.update_layout(
        showlegend=False, autosize=True, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False, range=[-1.2, len(order) - 0.3]),
        yaxis=dict(visible=False, range=[-2.3, 4.4]),     # 아래 = 비스듬한 이름 자리, 위 = 가장 큰 반원 높이
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3", size=15)))
    st.plotly_chart(theme.adapt(fig), key="live_network_chart", width="stretch", height="stretch",
                    config={"displayModeBar": False, "responsive": True})

    legend = "".join(
        f'<span><i style="background:{c["color"]}"></i>{cat}</span>'
        for cat, c in realtime.CATEGORIES.items())
    st.markdown(
        f'<div class="map-legend">{legend}'
        f'<em>오늘 연결 {len(pairs)}쌍 · 반원 굵기 = 사건 수 · 색 = 그 쌍에서 가장 많은 사건 유형 · '
        f'흐린 점 = 오늘 사건 없음</em></div>',
        unsafe_allow_html=True)


FIT_SCRIPT = """
(() => {
  const w = window.parent, d = w.document;
  // 패널 윗변 위치를 재서, 화면 아래 끝(여백 24px)까지 남은 높이를 패널 높이로 쓴다.
  // 화면 크기·브라우저 확대 비율이 달라도 항상 아래 빈 공간 없이 맞는다.
  const fit = () => {
    const panel = d.querySelector('.st-key-main_panel');
    const main = d.querySelector('[data-testid="stMain"]');
    if (!panel || !main) return;
    const top = panel.getBoundingClientRect().top + main.scrollTop;
    const h = Math.max(560, w.innerHeight - top - 24) + 'px';
    if (d.documentElement.style.getPropertyValue('--panel-h') === h) return;   // 그대로면 다시 그리지 않는다 (떨림 방지)
    d.documentElement.style.setProperty('--panel-h', h);
    w.dispatchEvent(new Event('resize'));   // Plotly가 새 높이에 맞춰 다시 그리게 한다
  };
  if (!w.__panelFitBound) {                 // 창 크기가 바뀔 때도 다시 맞춘다 (한 번만 등록)
    w.__panelFitBound = true;
    w.addEventListener('resize', () => {
      clearTimeout(w.__panelFitTimer);
      w.__panelFitTimer = setTimeout(() => {
        const panel = d.querySelector('.st-key-main_panel');
        const main = d.querySelector('[data-testid="stMain"]');
        if (!panel || !main) return;
        const top = panel.getBoundingClientRect().top + main.scrollTop;
        const h = Math.max(560, w.innerHeight - top - 24) + 'px';
        if (d.documentElement.style.getPropertyValue('--panel-h') !== h) {
          d.documentElement.style.setProperty('--panel-h', h);
          w.dispatchEvent(new Event('resize'));
        }
      }, 150);
    });
  }
  // 지도 시작 배율: 패널 크기를 재서 이집트~오만(경도 약 30도), 튀르키예~예멘(위도 약 26도)이
  // 딱 들어오는 배율로 맞춘다. 사용자가 직접 확대 · 이동한 뒤에는 건드리지 않는다.
  // 돌려주는 값: 배율이 맞춰졌거나 사용자가 옮겼으면 true (= 더 바뀔 일 없음)
  const fitMap = (gd, map) => {
    // 사용자가 직접 확대·축소·이동하면(버튼·드래그 모두 plotly_relayout 발생) 그 뒤로는 자동 맞춤을 멈춘다
    if (!gd.__mapWatch) {
      gd.__mapWatch = true;
      gd.on('plotly_relayout', () => {
        if (w.__mapSelf) return;
        // '배율 초기화' 버튼은 서버 배율(layout.map.zoom)로 되돌린다 → 사용자 조작이 아니라 다시 자동 맞춤
        const z0 = gd.layout && gd.layout.map && gd.layout.map.zoom;
        if (z0 != null && Math.abs(map.getZoom() - z0) < 0.001) { w.__mapUserMoved = false; setTimeout(tune, 50); return; }
        w.__mapUserMoved = true;
      });
    }
    if (w.__mapUserMoved) return true;
    const cw = gd.clientWidth, ch = gd.clientHeight;
    if (!cw || !ch) return false;                                  // 아직 크기가 안 잡힘
    const pxPerDeg = Math.min(cw / 30, ch / (26 * 1.12));        // 메르카토르라 위도 1도가 약 1.12배 길다
    const zoom = Math.max(2.5, Math.min(4.6, Math.log2(pxPerDeg * 360 / 512)));
    if (Math.abs(map.getZoom() - zoom) < 0.01) return true;       // 이미 맞춰져 있음
    // 1분마다 다시 그릴 때 Streamlit이 서버 배율로 되돌리므로, 그때마다 다시 맞춘다
    w.__mapSelf = true;
    map.jumpTo({zoom: zoom, center: [44.0, 27.2]}, {originalEvent: true});
    setTimeout(() => { w.__mapSelf = false; }, 300);
    return true;
  };
  // 지도 국가 이름: layout.meta.labels(이름 · 위치 · 방향 · 거리 · 색)로 지도 엔진에 '우리' 이름표 레이어를 올린다.
  // Plotly 트레이스가 아니라서 Plotly 가 다시 그려도 초기화되지 않는다 → 로딩 중 이름이 튀거나 떨리지 않는다.
  // 지도가 좁으면 글자를 줄이고(19px 그대로면 지도 엔진이 겹치는 이름을 숨긴다), 줄인 만큼 em 거리를 키워 원과의 px 거리는 그대로 둔다.
  const placeLabels = (gd, map) => {
    // 원 안 숫자(Plotly 레이어): 원 한가운데라 이름과 겹칠 일이 없으므로, 이름표 자리 다툼에서 뺀다
    gd._fullData.forEach((tr, i) => {
      const id = 'plotly-trace-layer-' + tr.uid + '-symbol';
      const mode = gd.data[i] && gd.data[i].mode;                  // _fullData 에는 mode 가 비어 있어 입력값에서 읽는다
      if (mode === 'text' && map.getLayer(id) && map.getLayoutProperty(id, 'text-allow-overlap') !== true) {
        map.setLayoutProperty(id, 'text-allow-overlap', true);
        map.setLayoutProperty(id, 'text-ignore-placement', true);
      }
    });
    const meta = gd.layout && gd.layout.meta && gd.layout.meta.labels;
    if (!meta || !map.style) return false;                         // 타일 · 아이콘이 덜 받아져도 레이어는 올릴 수 있다
    const BASE = meta.base || 19;                                  // 파이썬 LABEL_FONT
    const size = Math.round(Math.max(13, Math.min(BASE, gd.clientWidth / 32)));   // 소수 크기면 글자가 아예 안 그려진다
    const data = {type: 'FeatureCollection', features: meta.names.map((n) => ({
      type: 'Feature', geometry: {type: 'Point', coordinates: [n.lon, n.lat]},
      properties: {name: n.name, anchor: n.anchor, offset: [n.offset[0] * BASE / size, n.offset[1] * BASE / size]}}))};
    const key = JSON.stringify(data) + size + meta.color;          // 바뀐 게 없으면 아무것도 안 한다
    const src = map.getSource('ctry-names');
    if (!src) {
      try {
        map.addSource('ctry-names', {type: 'geojson', data: data});
        map.addLayer({id: 'ctry-names', type: 'symbol', source: 'ctry-names',
                      layout: {'text-field': ['get', 'name'], 'text-font': ['Open Sans Regular'], 'text-size': size,
                               'text-anchor': ['get', 'anchor'], 'text-offset': ['get', 'offset'], 'text-padding': 0},
                      paint: {'text-color': meta.color}});
      } catch (e) { return false; }                                // 스타일이 아직 없으면 다음 확인 때 다시
    } else if (map.__labelKey !== key) {
      src.setData(data);
      map.setLayoutProperty('ctry-names', 'text-size', size);
      map.setPaintProperty('ctry-names', 'text-color', meta.color);
    }
    if (map.getLayer('ctry-names')) map.moveLayer('ctry-names');   // 늘 맨 위 (Plotly 가 레이어를 다시 만들어도 이름이 원에 가리지 않게)
    map.__labelKey = key;
    return true;
  };
  // 지도를 보일지: 배율 · 이름 위치가 다 맞고 글꼴 · 타일까지 받은 뒤에 한 번에 보인다 (CSS 가 그 전까지 숨긴다).
  // 받는 게 늦어도 새 지도가 나타난 뒤 2초가 지나면 보인다.
  const reveal = (on) => { if (d.documentElement.dataset.mapReady !== (on ? '1' : '0')) d.documentElement.dataset.mapReady = on ? '1' : '0'; };
  const tune = () => {
    if (w.__mapTuning) return;                                     // 아래 설정이 styledata 를 다시 부르므로 겹쳐 돌지 않게
    const gd = d.querySelector('.st-key-live_map_chart .js-plotly-plot');
    const sub = gd && gd._fullLayout && gd._fullLayout.map && gd._fullLayout.map._subplot;
    if (!sub || !sub.map || !gd._fullData) return;
    const map = sub.map;
    w.__mapTuning = true;
    try {
      if (!map.__tuned) {                                          // 새 지도 객체: 한 번만 연결
        map.__tuned = true;
        map.__born = Date.now();
        reveal(false);                                             // 새 지도는 준비될 때까지 숨긴다
        map._fadeDuration = 0;                                     // 이름 위치가 바뀔 때 0.3초 흐려졌다 나타나는 효과 끄기
        map.on('styledata', tune);                                 // Plotly 가 이름표를 초기화하는 순간 바로 다시 적용
        map.on('idle', tune);                                      // 그리기 · 글꼴 · 타일이 끝났을 때 다시 확인 (여기서 보이게 된다)
        setTimeout(tune, 2100);                                    // 늦어도 2초 뒤엔 보이게
      }
      if (!gd.__tuneHook) { gd.__tuneHook = true; gd.on('plotly_afterplot', () => setTimeout(tune, 0)); }
      const fitted = fitMap(gd, map);
      const placed = placeLabels(gd, map);
      // 배율 · 이름 위치가 다 맞았을 때만 보인다 (이름 레이어가 생기기 전에 보이면 원 한가운데 이름이 잠깐 나온다)
      if (fitted && placed && (map.loaded() || Date.now() - map.__born > 2000)) reveal(true);
    } finally {
      w.__mapTuning = false;
    }
  };
  [0, 300, 900].forEach((ms) => setTimeout(tune, ms));             // 지도가 생기는 시점이 들쭉날쭉해 몇 번 확인 (이미 맞으면 아무것도 안 함)
  setTimeout(fit, 300);
  setTimeout(fit, 1500);
})();
"""


def fit_charts_to_panel():
    """패널을 화면 아래 끝까지 채우고, 차트를 그 높이에 다시 맞춘다.

    Plotly는 처음 그릴 때 기본 높이(450px)로 그려서, 그린 직후 높이를 재고 다시 그리게 한다.
    매번 다른 값(시각)을 넣어야 Streamlit이 같은 내용이라고 건너뛰지 않고 스크립트를 다시 실행한다.
    """
    import time
    with st.container(key="resize_nudge"):
        st.html(f"<script>/* {time.time()} */{FIT_SCRIPT}</script>", unsafe_allow_javascript=True)


VIEWS = {
    "지도": ("국가별 사건 발생 현황", "원 안 숫자 = 당일 사건 수 · 마우스를 올리면 상세 정보 표시"),
    "네트워크": ("사건 유형별 국가 간 관계 네트워크", "선에 마우스를 올리면 행위 방향별 사건 건수 표시"),
}


@st.fragment(run_every="60s")
def live_main_panel():
    """왼쪽 큰 패널. 지도와 네트워크를 버튼으로 바꿔 본다. 60초마다 이 패널만 다시 그린다."""
    view = st.session_state.get("main_view") or "지도"
    with st.container(border=True, key="main_panel"):
        title, hint = VIEWS[view]
        choice = "전체"
        # 제목과 버튼을 한 줄에 두되, 폭이 모자라면 버튼 묶음이 제목 아래 줄로 내려간다 (잘리지 않게).
        sub = (f"오늘(UTC) {realtime.today_utc()[:4]}-{realtime.today_utc()[4:6]}-{realtime.today_utc()[6:]} · 국가별 사건 수 · 15분 단위 갱신"
               if view == "지도" else "당일(UTC) · 사건 유형별 국가쌍 관계 · 선 굵기 = 사건 수")
        with st.container(horizontal=True, wrap=True, vertical_alignment="top", gap="small"):
            # (2026-10-02) 리스크 추이와 같은 머리글: 큰 제목 ⓘ / 그 밑 작은 줄
            st.markdown(f'<div class="rm-h"><div class="rm-t">{title} {info_icon(hint)}</div>'
                        f'<div class="rm-s">{sub}</div></div>', unsafe_allow_html=True, width="stretch")
            # 버튼 묶음. 네트워크일 때만 그 왼쪽에 분쟁 원인 선택 상자를 둔다.
            with st.container(horizontal=True, horizontal_alignment="right",
                              vertical_alignment="top", gap="small", width="content"):
                if view == "네트워크":
                    choice = st.selectbox("사건 유형", ["전체"] + list(realtime.CATEGORIES),
                                          key="net_category", label_visibility="collapsed",
                                          width=160)
                st.segmented_control("보기", list(VIEWS), default="지도", key="main_view",
                                     label_visibility="collapsed")

        if view == "네트워크":
            draw_network(choice)
        else:
            draw_map()
            live_legend()   # 지도 칸 아래 범례 상자 (스토리맵)
        fit_charts_to_panel()


@st.fragment(run_every="60s")
def live_feed():
    """오늘(UTC) 사건을 최신순으로 보여준다. 일시정지하면 그 순간 목록을 붙잡아 둔다."""
    import html as html_lib

    paused = st.session_state.get("feed_paused", False)

    with st.container(border=True, key="feed_panel"):
        live_panel()   # (2026-10-01) 위: 스토리맵 LIVE 패널 · 아래: 최근 사건
        # 제목은 남는 폭을 쓰고, 버튼은 글자 폭만큼 확보한다. 좁은 화면에서도 버튼이 잘리지 않는다.
        with st.container(horizontal=True, vertical_alignment="top", gap="small"):
            st.markdown('<div class="rm-h"><div class="rm-t">최근 사건 '
                        + info_icon('오늘(UTC) 사건을 최신순으로 · 시각은 한국 시간 · 보도량 = 그 사건을 다룬 기사 수 '
                                    '(적음 1–2 · 보통 3–7 · 많음 8건+) · 동일 기사 N건 = 한 기사에서 나온 사건 묶음')
                        + '</div><div class="rm-s">당일(UTC) 최신순 · 시각: 한국 시간</div></div>', unsafe_allow_html=True, width="stretch")
            clicked = st.button("갱신 재개" if paused else "일시정지", key="feed_toggle", width="content")
        if clicked:
            st.session_state["feed_paused"] = not paused
            if not paused:   # 방금 멈췄다 → 지금 목록을 저장
                st.session_state["feed_snapshot"] = realtime.recent_events(
                    realtime.load_day(realtime.today_utc()))
            st.rerun(scope="fragment")

        if paused and "feed_snapshot" in st.session_state:
            items = st.session_state["feed_snapshot"]
        else:
            items = realtime.recent_events(realtime.load_day(realtime.today_utc()))

        with st.container(border=False, key="feed_list"):   # 남은 높이를 채우고, 넘치면 이 안에서만 스크롤
            if not items:
                st.caption("당일(UTC) 수집 사건 없음")
            rows = []
            for it in items:
                esc = html_lib.escape
                link = (f'<a href="{esc(it["url"])}" target="_blank">기사 링크</a> · {esc(it["domain"])}'
                        if it["url"] else "출처 없음")
                rows.append(
                    f'<div class="feed-item">'
                    f'<div class="feed-time">{it["time_kst"]}</div>'
                    f'<div class="feed-body">'
                    f'<div class="feed-pair">{esc(it["src"])} <span>→</span> {esc(it["dst"])}</div>'
                    f'<div class="feed-tags">'
                    f'<span class="feed-badge" style="color:{it["color"]};border-color:{it["color"]}66;'
                    f'background:{it["color"]}1f">{it["root"]} {it["category"] or "기타"}</span>'
                    + (f'<span class="feed-group">동일 기사 {it["count"]}건</span>'
                       if it["count"] > 1 else "")
                    + (f'<span class="feed-late">{it["days_before"]}일 전 사건</span>'
                       if it["days_before"] else "")
                    + f'</div>'
                    f'<div class="feed-what">{esc(", ".join(it["whats"]))} · <em>{esc(it["where"])}</em></div>'
                    f'<div class="feed-link">{link}</div>'
                    f'</div>'
                    f'<div class="feed-side {it["grade_class"]}">'
                    f'<b>{it["grade"]} <i class="dots">{"●●●" if it["grade_class"] == "hot" else "●●○" if it["grade_class"] == "warm" else "●○○"}</i></b><span>기사 {it["articles"]}건</span>'
                    f'</div></div>')
            st.markdown("".join(rows), unsafe_allow_html=True)
        if paused:
            st.caption("갱신 일시정지 중 · 갱신 재개 선택 시 신규 사건 표시")


def page(show_title=True):
    if show_title:
        st.title('실시간 모니터링')
        page_sub(term("GDELT 2.0") + " 기반 중동 16개국 간 " + term("실시간 갈등 뉴스") + " 현황 제공 · 날짜 기준: " + term("UTC") + " 당일")
    k = realtime.kpis()
    if k["top"]:
        name, count, partner = k["top"]
        st.markdown(f'<div class="summary">오늘(UTC) 중동 국가 간 갈등 사건 <b>{k["total"]:,}건</b> · '
                    f'최다 관여국: <b>{name}</b>({count}건, 최다 상대국 {partner})</div>', unsafe_allow_html=True)

    # (2026-10-01) KPI 카드 3개(live_kpis)는 빼고, 같은 내용을 오른쪽 위 LIVE 패널로

    left, right = st.columns([2.3, 1], gap="medium")   # 왼쪽(지도·네트워크)을 더 넓게 (2026-10-01: 1.8 → 2.3)

    with left:
        live_main_panel()

    with right:
        live_feed()
