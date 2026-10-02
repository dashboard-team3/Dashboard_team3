"""리스크 모니터링 페이지 (2026-10-01): 제목 옆 버튼으로 «실시간 모니터링» · «리스크 추이» 를 바꿔 본다.

리스크 추이 = 실시간 모니터링처럼 [지도 | 오른쪽 칸].
- 지도 · 카드 · 그래프 점은 모두 «기준 달» 한 달 값 = 하루도 빠짐없이 모인 마지막 달 (2026-10-01: 수집 중인 달은 건너뜀)
- 나라를 누르면 오른쪽 칸에 «그 나라 → 상대국 리스크» 그래프(최근 10년)와 상대국 카드 5장을 위아래로
- 오른쪽 칸의 «크게 보기» 를 누르면 지도와 그래프 자리를 바꿔, 그래프(1980년부터)를 넓은 왼쪽에서 본다
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import page_sub, term, ctitle, info_icon, C_TEXT, CHART_CONFIG, DARK_LAYOUT
from core import theme
from sources import relations
from sources.realtime import COUNTRY_POS, SHORT_NAME
from views import realtime_view, risk_view
from views.realtime_view import LABEL_OUT, LEFT_SIDE, SEQ_DARK, SEQ_LIGHT, _scale

VIEWS = ["실시간 모니터링", "리스크 추이"]
YEARS = 10                       # 오른쪽 좁은 칸의 그래프 기간 (좁은 칸에 46년을 넣으면 선이 뭉개진다)
DEFAULT = "ISR"                  # 아직 아무 나라도 안 눌렀을 때


def page():
    h1, h2 = st.columns([1.6, 1], vertical_alignment="center", gap="large")   # 버튼 이름이 잘리지 않게
    with h1:
        st.title("리스크 모니터링")
        page_sub(term("GDELT 2.0") + " 뉴스 기반 갈등 지표로 중동 16개국의 " + term("실시간 갈등 뉴스") + "와 1980년부터의 "
                 + term("리스크") + " 추이를 봅니다.")
    with h2:
        # tabbar 와 같은 띠 모양. 홈 카드 · 예전 주소가 mon_view 를 미리 정해 두면 default 를 주지 않는다 (경고 방지)
        with st.container(key="tabbar-mon_view"):
            kw = {} if "mon_view" in st.session_state else {"default": VIEWS[0]}
            view = st.segmented_control("보기", VIEWS, key="mon_view", label_visibility="collapsed", **kw) or VIEWS[0]
    if view == "실시간 모니터링":
        realtime_view.page(show_title=False)
    else:
        risk_map_page()


# ---------------------------------------------------------------- 리스크 추이 (지도)

@st.cache_data
def base_month():
    """기준 달 = 하루도 빠짐없이 모인 마지막 달 (그달 가장 많이 모인 나라의 수집 일수 = 그달 일수).
    아직 모으는 중인 달(예: 2026-09 은 30일 중 21일)은 건너뛴다. 지도 · 카드 · 그래프 점이 모두 이 달 값이라
    세 곳 숫자가 같다. 다음 달이 다 차면 저절로 그 달로 넘어간다."""
    c = relations.load_country()
    full = (c["active_days"] >= c["days_in_month"]).groupby(c["date"]).any()
    return full[full].index.max()


@st.cache_data
def month_country_risk():
    """기준 달의 나라별 종합 리스크 (country_monthly · all_risk)."""
    c = relations.load_country()
    b = base_month()
    return c[c["date"] == b].set_index("country")["all_risk"].dropna().to_dict(), b


@st.cache_data
def month_pair_risk(code):
    """기준 달의 고른 나라 → 상대국 국가쌍 리스크 (risk_monthly). 그달 사건이 없던 쌍은 빠진다."""
    series = relations.pair_series(relations.load_risk(), code, "out")
    b = base_month()
    return (series.loc[b].dropna().to_dict() if b in series.index else {}), b


def _pos(kr):
    """화살표 시작 · 끝 위치: 좁은 나라는 실제 위치(LABEL_OUT 의 앞 두 값), 나머지는 이름 자리."""
    return LABEL_OUT[kr][:2] if kr in LABEL_OUT else COUNTRY_POS[kr]


def _arc(a, b, n=24, bend=0.18, end=0.84):
    """a → b 를 살짝 휜 곡선 점들로 (2차 베지어). 위도 · 경도 평면에서 진행 방향의 왼쪽으로 휜다.
    end < 1 이면 끝을 조금 남겨 화살촉이 상대국 이름 · 숫자를 가리지 않게 한다."""
    (y0, x0), (y1, x1) = a, b
    cx, cy = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    ts = [end * i / (n - 1) for i in range(n)]
    return ([(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1 for t in ts],
            [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1 for t in ts])


def _bearing(lat0, lon0, lat1, lon1):
    """화면(메르카토르)에서 (lat0, lon0) → (lat1, lon1) 방향. 위쪽 = 0°, 시계 방향 (marker.angle 과 같은 기준)."""
    import math
    m = lambda la: math.degrees(math.log(math.tan(math.pi / 4 + math.radians(la) / 2)))
    return math.degrees(math.atan2(lon1 - lon0, m(lat1) - m(lat0)))


ARROWS = 3          # 국가쌍 지도에서 고른 나라 → 리스크 큰 상대국 화살표 수


def _risk_map(sel, small=False):
    """중동 16개국 지도 (값은 모두 기준 달 한 달 값). 국가별 = 나라마다 종합 리스크로 칠한다.
    국가쌍 = 고른 나라 → 각 상대국의 국가쌍 리스크로 상대국을 칠하고, 리스크가 큰 3곳으로
    흐르는 화살표를 그린다 (점선이 흘러가는 애니메이션은 style2.css «국가쌍 화살표»).
    small=True 는 그래프를 크게 볼 때 오른쪽 좁은 칸에 들어가는 작은 지도."""
    light = theme.is_light()
    names = relations.COUNTRIES
    kr_iso = {v: k for k, v in names.items()}
    pair = _mode() == "국가쌍"
    if pair:
        val, last = month_pair_risk(sel)
        what = f"{names[sel]} → 상대국 리스크"
    else:
        val, last = month_country_risk()
        what = "종합 리스크"
    iso = [c for c in names if c in val and not (pair and c == sel)]
    z = [min(max((val[c] - 0.15) / 0.55, 0), 1) for c in iso]          # 0.15 ~ 0.7 을 색 막대 끝에서 끝으로
    if pair:
        hover = [f"<b>{names[sel]} → {names[c]}</b> {last:%Y-%m} 리스크 {val[c]:.2f}<br>누르면 그 나라 기준으로 바뀜" for c in iso]
    else:
        hover = [f"<b>{names[c]}</b> {last:%Y-%m} 종합 리스크 {val[c]:.2f}<br>누르면 오른쪽에 그 나라 리스크 추이" for c in iso]
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=iso, z=z, locationmode="ISO-3", showscale=False, zmin=0, zmax=1,
        colorscale=_scale(SEQ_LIGHT if light else SEQ_DARK),
        marker_line_color="#ffffff" if light else "#13142a", marker_line_width=0.9,
        customdata=iso,                                                   # 클릭하면 이 값(ISO3)이 돌아온다
        hovertext=hover, hovertemplate="%{hovertext}<extra></extra>"))
    # 고른 나라: 국가쌍이면 기준 나라라 색 대신 무채색 면 + 굵은 테두리, 국가별이면 굵은 테두리만
    base = ("#c7cbe0" if light else "#3a3b5c") if pair else "rgba(0,0,0,0)"
    fig.add_trace(go.Choropleth(
        locations=[sel], z=[0], locationmode="ISO-3", showscale=False,
        colorscale=[[0, base], [1, base]],
        marker_line_color="#4f46e5" if light else "#ffffff", marker_line_width=3,
        customdata=[sel], hovertext=[f"<b>{names[sel]}</b>" + (" (기준 나라)" if pair else "")],
        hovertemplate="%{hovertext}<extra></extra>"))
    # 국가쌍: 고른 나라 → 리스크가 큰 상대국 3곳으로 화살표 (점선 · 끝에 화살촉, 굵기 = 리스크). 이름 · 숫자보다 먼저 그려 글자 아래에 깔리게
    if pair and val:
        top = sorted((c for c in val if c != sel), key=lambda c: -val[c])[:ARROWS]
        col = "#4f46e5" if light else "#ffffff"
        for c in top:
            a, b = _pos(names[sel]), _pos(names[c])
            # 끝을 비율이 아니라 «거리»로 남긴다: 이름이 가운데 있는 나라는 이름 앞 1.4°, 이름을 바깥으로 뺀 좁은 나라는 0.3° 앞까지
            # (비율로 남기면 먼 나라일수록 일찍 끝나 옆 나라를 가리키는 것처럼 보였다)
            dist = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            gap = 0.3 if names[c] in LABEL_OUT else 1.4
            ys, xs = _arc(a, b, end=max(0.5, 1 - gap / dist) if dist else 1)
            # 점선은 화살촉 바로 앞에서 끝내고(점선 틈이 촉과 떨어져 보이지 않게), 촉은 마지막 점에 따로 그린다.
            # 촉 방향은 화면(메르카토르)에서 마지막 두 점을 잇는 방향 — angleref="previous" 는 점선 끝과 어긋나 보였다
            fig.add_trace(go.Scattergeo(
                lat=ys[:-1], lon=xs[:-1], mode="lines", hoverinfo="skip",
                line=dict(width=1.5 + 4 * val[c], color=col, dash="8px,4px"), opacity=0.95))
            fig.add_trace(go.Scattergeo(
                lat=[ys[-1]], lon=[xs[-1]], mode="markers", hoverinfo="skip",
                marker=dict(symbol="triangle-up", angleref="up", angle=_bearing(ys[-3], xs[-3], ys[-1], xs[-1]),
                            size=12 + 10 * val[c], color=col, line=dict(width=0)), opacity=0.95))
    # 이름 + 값 (좁은 나라는 바깥으로 빼고 선으로 잇는다 — 실시간 지도와 같은 자리)
    # 작은 지도에서는 좁은 나라(LABEL_OUT) 이름 · 이음선을 빼서 글자가 겹치지 않게 (마우스를 올리면 보임)
    rows = [(kr, COUNTRY_POS[kr], kr_iso.get(kr)) for kr in COUNTRY_POS if not (small and kr in LABEL_OUT)]
    llat, llon = [], []
    for kr, (a_lat, a_lon, t_lat, t_lon) in ({} if small else LABEL_OUT).items():
        llat += [a_lat, t_lat, None]; llon += [a_lon, t_lon, None]
    fig.add_trace(go.Scattergeo(lat=llat, lon=llon, mode="lines", hoverinfo="skip",
                                line=dict(width=0.8, color="rgba(28,26,23,.45)" if light else "rgba(255,255,255,.45)")))
    pos = [LABEL_OUT[kr][2:] if kr in LABEL_OUT else p for kr, p, _ in rows]

    def vtxt(c):
        if pair and c == sel:
            return "기준"
        return f"{val[c]:.2f}" if c in val else "–"

    txt = [(f"<b>{SHORT_NAME.get(kr, kr)}</b> {vtxt(c)}" if kr in LABEL_OUT
            else f"<b>{SHORT_NAME.get(kr, kr)}</b><br>{vtxt(c)}") for kr, _, c in rows]
    fig.add_trace(go.Scattergeo(
        lat=[p[0] for p in pos], lon=[p[1] for p in pos], mode="text", hoverinfo="skip", text=txt,
        textposition=[("middle left" if kr in LEFT_SIDE else "middle right") if kr in LABEL_OUT else "middle center"
                      for kr, _, _ in rows],
        textfont=dict(size=11 if small else 13, color="#1c1a17" if light else "#ffffff", family="JetBrains Mono, Pretendard, sans-serif")))
    fig.update_layout(
        geo=dict(projection_type="mercator", fitbounds="locations", visible=True,
                 showland=True, landcolor="#ffffff" if light else "#13142a",          # 주변 땅 = 지도 상자 바탕색 (그래프 상자처럼 한 색, 2026-10-02)
                 showcountries=True, countrycolor="#e5e7eb" if light else "#24254a", countrywidth=0.6,   # 주변 나라는 옅은 경계선만
                 showcoastlines=False, showocean=False, showlakes=False, showframe=False, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False, height=236 if small else 720, paper_bgcolor="rgba(0,0,0,0)",
        dragmode=False, clickmode="event+select",
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3", size=15)))
    ev = st.plotly_chart(fig, key="risk_map", width="stretch", on_select="rerun", selection_mode="points",
                         config={"displayModeBar": False, "scrollZoom": False})
    pts = (ev or {}).get("selection", {}).get("points", []) if isinstance(ev, dict) else getattr(getattr(ev, "selection", None), "points", [])
    for p in pts:
        code = p.get("location") or p.get("customdata")
        if isinstance(code, list):
            code = code[0]
        if code in names and code != st.session_state.get("riskmap_sel"):
            st.session_state["riskmap_sel"] = code
            st.rerun()
    seq = SEQ_LIGHT if light else SEQ_DARK
    if pair:
        note = f"화살표 = {names[sel]} 에서 리스크가 가장 큰 상대국 {ARROWS}곳 (굵을수록 큼) · 다른 나라를 누르면 그 나라 기준으로 바뀜"
        src = "risk_monthly_1980_2026 (국가쌍 리스크)"
    else:
        note = f"나라를 누르면 오른쪽에 그 나라의 리스크 추이 (최근 {YEARS}년)"
        src = "country_monthly_1980_2026 (all_risk)"
    st.markdown(f"""
<div class="lv-lg">
  <div class="lv-lg-a">
    <div class="lv-lg-t lv-long">{last:%Y-%m} {what}</div>
    <div class="lv-grad" style="background:linear-gradient(90deg,{','.join(seq)})"></div>
    <div class="lv-ticks"><span>0.15</span><span>0.4</span><span>0.7+</span></div>
  </div>
  <div class="lv-lg-b">
    <div class="lv-note lv-long">0 = 협력 보도만, 1 = 갈등 보도만 (GDELT 보도량 가중) · {last:%Y-%m} 한 달 값 = 하루도 빠짐없이 모인 마지막 달 (카드 큰 숫자 · 그래프 점과 같음)</div>
    <div class="lv-note lv-long">{note}</div>
    <div class="lv-note lv-src lv-long">출처 GDELT → {src}</div>
  </div>
</div>""", unsafe_allow_html=True)


MODES = ["국가쌍", "국가별"]
FOCUS_KEY = "riskmap_focus"     # (고른 나라, 보기, 강조할 나라) — 카드를 누르면 바뀐다
MODE_KEY = "riskmap_mode"


def _mode():
    return st.session_state.get(MODE_KEY) or MODES[0]


def _mode_toggle():
    """국가쌍 · 국가별 고르기 (왼쪽 칸 머리글 오른쪽). 고른 보기에 따라 그래프 · 카드가 바뀐다 (2026-10-01)."""
    with st.container(key="riskmap_mode_box"):
        st.segmented_control("보기", MODES, default=MODES[0], key=MODE_KEY, label_visibility="collapsed",
                             help="국가쌍 = 고른 나라 → 상대국 리스크 · 국가별 = 나라마다의 종합 리스크")


@st.cache_data
def _country_matrix():
    return relations.load_country().pivot(index="date", columns="country", values="all_risk")


def _data(code, mode):
    """그래프 · 카드에 쓰는 값 (최근 10년 기준).
    국가쌍: 고른 나라 → 상대국 월별 리스크, 10년 평균 상위 5곳 (강조 = 1위)
    국가별: 나라별 종합 리스크, 10년 평균 상위 5곳 + 고른 나라 (강조 = 고른 나라)."""
    names = relations.COUNTRIES
    if mode == "국가별":
        mat = _country_matrix()
    else:
        mat = relations.pair_series(relations.load_risk(), code, "out")
    p1 = base_month()                                        # 기준 달까지만 (수집 중인 달은 뺀다)
    p0 = p1 - pd.DateOffset(years=YEARS) + pd.offsets.MonthBegin(0)
    in_range = risk_view._in_period(mat, p0, p1)
    cur = mat.loc[p1] if p1 in mat.index else pd.Series(dtype=float)   # 기준 달 값 — 카드 순서 · 지도 화살표와 같은 기준
    rank = cur.fillna(-1)
    if mode == "국가별":
        items = risk_view._card_items(list(cur.dropna().index), rank, code)
        items = sorted(items, key=lambda x: -rank.get(x, -1))
        focus = code
        d = dict(line=lambda q: names[q], dist="all_risk", layer="국가별", title="국가별 리스크",
                 head="국가별 종합 리스크",
                 tip="선 = 나라마다 그 나라가 낀 모든 관계로 낸 종합 리스크의 12개월 이동평균 (0~1) · 점선 = 중동 전체 · "
                     f"{p1:%Y-%m} 값 상위 5곳 (고른 나라는 늘 포함 · 굵은 선) · 점 = {p1:%Y-%m} 한 달 값")
    else:
        items = list(cur.dropna().sort_values(ascending=False).index[:risk_view.CARD_N])
        focus = items[0]
        d = dict(line=lambda q: f"{names[code]} → {names[q]}", dist="pair", layer="국가쌍", title=f"{names[code]} → 상대국",
                 head=f"{names[code]} → 상대국",
                 tip=f"선 = 국가쌍 월별 리스크의 12개월 이동평균 (0~1) · 점선 = 중동 전체 · {p1:%Y-%m} 값 상위 5곳 (굵은 선 = 1위) · "
                     f"점 = {p1:%Y-%m} 한 달 값 (지도 · 카드 숫자와 같음)")
    pick = st.session_state.get(FOCUS_KEY)                   # 카드를 눌러 고른 강조 (같은 나라 · 같은 보기일 때만)
    if pick and pick[0] == code and pick[1] == mode and pick[2] in items:
        focus = pick[2]
    d.update(mat=mat, in_range=in_range, items=items, focus=focus, p0=p0, p1=p1)
    return d


def _chart(code, big=False):
    """선 그래프. big=True 는 왼쪽 넓은 칸 · 1980년부터, 아니면 오른쪽 칸 · 최근 10년."""
    names = relations.COUNTRIES
    d = _data(code, _mode())
    mat, items, focus, p0, p1 = d["mat"], d["items"], d["focus"], d["p0"], d["p1"]
    if big:
        p0 = mat.index.min()
    fig = go.Figure()
    rs = risk_view._in_period(relations.smooth(relations.load_region(), risk_view.HOW), p0, p1)
    fig.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name="중동 전체",
                             line=dict(color="#94a3b8", width=1.4, dash="dot"),
                             hovertemplate="중동 전체 %{y:.3f}<extra></extra>"))
    pcol = risk_view._line_colors(items, focus)
    for q in sorted(items, key=lambda x: x == focus):
        sm = risk_view._in_period(relations.smooth(mat[q], risk_view.HOW), p0, p1)
        fig.add_trace(go.Scatter(x=sm.index, y=sm.values, mode="lines", name=names[q],
                                 line=dict(color=pcol[q], width=3.2 if q == focus else 1.4),
                                 opacity=1 if q == focus else 0.5,
                                 hovertemplate=f"{d['line'](q)} %{{y:.3f}}<extra></extra>"))
    # 기준 달 한 달 값을 점으로 — 선(12개월 이동평균) 끝과 다르지만 지도 · 카드 숫자와 같은 값
    for q in sorted(items, key=lambda x: x == focus):
        v = mat[q].get(p1)
        if v is not None and not pd.isna(v):
            fig.add_trace(go.Scatter(x=[p1], y=[v], mode="markers", showlegend=False,
                                     marker=dict(color=pcol[q], size=12 if q == focus else 8,
                                                 line=dict(width=1.5, color="#ffffff")),
                                     hovertemplate=f"{d['line'](q)} {p1:%Y-%m} 한 달 값 %{{y:.3f}}<extra></extra>"))
    fig.add_vline(x=p1, line=dict(color="#a78bfa", width=1, dash="dot"))
    fig.add_annotation(x=p1, y=1.0, yref="paper", text=f"기준 달 {p1:%Y-%m}", showarrow=False, xanchor="right",
                       yanchor="top", font=dict(size=11, color="#a78bfa"))
    risk_view._gap_bands(fig, relations.gap_months(relations.load_risk()), p0, p1)
    fig.update_layout(**DARK_LAYOUT, height=615 if big else 280, hovermode="x unified",
                      margin=dict(l=6, r=6, t=10, b=6),
                      legend=dict(orientation="h", y=-0.08 if big else -0.12, yanchor="top", x=0, font=dict(size=13 if big else 12)))
    risk_view._time_axes(fig, p0, p1)
    if not big:
        fig.update_xaxes(dtick="M24", tickangle=0, tickfont=dict(size=12))   # 좁은 칸: 2년 간격 · 눕히지 않음
        fig.update_yaxes(tickfont=dict(size=12), dtick=0.2)
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG, key="riskmap_chart")


def _side_panel(code, big):
    """오른쪽 칸: 머리글(크게 보기 단추) → 그래프(크게 볼 때는 그 자리에 작은 지도) → 카드 5장.
    단추 · 카드는 크게 보든 아니든 같은 자리에 둔다. 크게 볼 때 카드는 3장 높이로 줄이고 안에서 스크롤 (2026-10-01)."""
    names = relations.COUNTRIES
    d = _data(code, _mode())
    mat, in_range, items, p0, p1 = d["mat"], d["in_range"], d["items"], d["p0"], d["p1"]
    hd1, hd2 = st.columns([1.5, 1], vertical_alignment="top")
    if big:
        hd1.markdown(_head_html("지도", "나라를 누르면 왼쪽 그래프가 바뀜", "나라를 누르면 왼쪽 그래프가 그 나라로 바뀝니다"),
                     unsafe_allow_html=True)
    else:
        hd1.markdown(_head_html("리스크 추이", f"{d['head']} · 최근 {YEARS}년", d["tip"]), unsafe_allow_html=True)
    if hd2.button("지도 크게 보기 ⤢" if big else "크게 보기 ⤢", key="riskmap_swap", width="stretch",
                  help="왼쪽 넓은 칸에 그래프(1980년부터)와 지도를 바꿔 보여 줍니다"):
        st.session_state["riskmap_big"] = not big
        st.rerun()
    if big:
        _risk_map(code, small=True)
    else:
        _chart(code)
    last_m = in_range.index.max()
    ma = {q: risk_view._in_period(relations.smooth(mat[q], risk_view.HOW), p0, p1).iloc[-1] for q in items}
    dist = relations.load_dists()[d["dist"]]
    common = dict(layer=d["layer"], month=f"{last_m:%Y-%m}", period=risk_view._pstr(p0, p1))
    # 카드 묶음 제목 (2026-10-02 팀 요청): «리스크 상위 5개국» — 위 그래프(지도)와 떨어져 보이게 위 여백
    st.markdown('<div class="rm-cards-t">리스크 상위 5개국</div>', unsafe_allow_html=True)
    # 제목 줄은 스크롤 상자 밖에 둬서 카드만 움직이게 (2026-10-01)
    risk_view.grade_pills([], dist, d["title"], title_sub=f"{last_m:%Y-%m} 기준 (다 모인 마지막 달) · 평균 = 최근 {YEARS}년",
                          title_tip=f"큰 숫자 = 그 달 한 달의 리스크 · 평균 = 최근 {YEARS}년 월별 평균 · "
                                    f"이 달 상위 % = {d['layer']} 1980년 이후 모든 값과 견준 순위 · "
                                    "빨간 테두리 = 그래프에서 굵게 보이는 나라 · 카드를 누르면 그 나라를 굵게", **common)
    mode = _mode()
    with st.container(key="riskmap_cards", height=280 if big else "content", gap="small"):
        for i, q in enumerate(items):
            with st.container(key=f"rmcard_{i}"):           # 카드 한 장 + 그 위를 덮는 투명 단추
                risk_view.grade_pills([(q, names[q], in_range[q].iloc[-1], in_range[q].mean(), ma[q])], dist,
                                      hi=d["focus"], **common)
                st.button(f"{names[q]} 강조", key=f"rmcard_btn_{i}", on_click=st.session_state.__setitem__,
                          args=(FOCUS_KEY, (code, mode, q)), width="stretch")


def _head_html(title, sub, tip):
    """칸 머리글: 큰 제목 ⓘ / 그 밑 작은 줄(나라 · 달 · 기간). (2026-10-02 제목 키우고 옆 내용은 밑으로)"""
    return (f'<div class="rm-h"><div class="rm-t">{title} {info_icon(tip)}</div>'
            f'<div class="rm-s">{sub}</div></div>')


def _on_pick():
    st.session_state["riskmap_sel"] = st.session_state["riskmap_pick"]


def _left_head(title, sub, tip, sel=None):
    """왼쪽 칸 머리글: 큰 제목 ⓘ / 작은 줄 · 오른쪽 국가쌍/국가별 고르기.
    sel 을 주면 작은 줄 맨 앞(나라 이름 자리)에 나라 고르기 상자를 둔다 — 지도에서 작은 나라를 누르기 어려워서.
    지도에서 나라를 누르면 상자도 그 나라로 맞춘다 (상자를 그리기 전에 값만 바꿔 둠)."""
    names = relations.COUNTRIES
    h1, h2 = st.columns([2.2, 1], vertical_alignment="top")
    if sel is None:
        h1.markdown(_head_html(title, sub, tip), unsafe_allow_html=True)
    else:
        with h1:
            st.markdown(f'<div class="rm-h"><div class="rm-t">{title} {info_icon(tip)}</div></div>', unsafe_allow_html=True)
            with st.container(horizontal=True, vertical_alignment="center", gap="small", key="rm_sub"):
                if st.session_state.get("riskmap_pick") != sel:
                    st.session_state["riskmap_pick"] = sel
                st.selectbox("나라", list(names), key="riskmap_pick", format_func=names.get, on_change=_on_pick,
                             label_visibility="collapsed", width=150)
                st.markdown(f'<div class="rm-s" style="margin:0">{sub}</div>', unsafe_allow_html=True)
    with h2:
        _mode_toggle()


def risk_map_page():
    """[지도 | 오른쪽 칸]. 왼쪽 머리글의 국가쌍 · 국가별 고르기에 따라 그래프 · 카드가 바뀐다.
    오른쪽 «크게 보기» 를 누르면 왼쪽 넓은 칸에 그래프(1980년부터)만 크게 보이고,
    지도는 오른쪽 칸의 그래프 자리로 작게 옮긴다 (거기서도 나라를 고를 수 있음). 단추 · 카드 자리는 그대로.
    두 칸은 높이를 맞춘다 (style2.css «리스크 추이 두 칸»)."""
    names = relations.COUNTRIES
    sel = st.session_state.get("riskmap_sel", DEFAULT)
    big = st.session_state.get("riskmap_big", False)
    left, right = st.columns([2.3, 1], gap="medium")
    if big:
        with left, st.container(border=True, key="riskmap_bigchart"):
            d = _data(sel, _mode())
            _left_head("리스크 추이", ("→ 상대국" if _mode() == "국가쌍" else "강조 · 국가별 종합 리스크")
                       + f" · 1980년부터 · 기준 달 {base_month():%Y-%m}",
                       d["tip"].replace("최근 10년 평균", "1980년부터 · 최근 10년 평균"), sel=sel)
            _chart(sel, big=True)
    else:
        with left, st.container(border=True, key="riskmap_panel"):
            if _mode() == "국가쌍":
                _left_head("국가쌍 리스크", f"→ 상대국 · {base_month():%Y-%m} (다 모인 마지막 달)",
                           f"고른 나라(기준)에서 각 상대국으로의 {base_month():%Y-%m} 국가쌍 리스크로 칠함 (하루도 빠짐없이 모인 마지막 달) · "
                           "화살표 = 리스크가 가장 큰 3곳 (오른쪽 카드 1~3위와 같음) · 나라를 누르거나 왼쪽 상자에서 고르면 그 나라 기준", sel=sel)
            else:
                _left_head("나라별 종합 리스크", f"강조 · {base_month():%Y-%m} (다 모인 마지막 달)",
                           f"나라마다 그 나라가 낀 모든 관계로 낸 {base_month():%Y-%m} 종합 리스크 (하루도 빠짐없이 모인 마지막 달) · "
                           "나라를 누르거나 왼쪽 상자에서 고르면 오른쪽에 그 나라의 리스크 추이", sel=sel)
            _risk_map(sel)
    with right, st.container(border=True, key="riskmap_side"):
        _side_panel(sel, big)
