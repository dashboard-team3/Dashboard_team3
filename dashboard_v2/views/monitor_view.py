"""리스크 모니터링 페이지 (2026-10-01): 제목 옆 버튼으로 «실시간 모니터링» · «리스크 추이» 를 바꿔 본다.

리스크 추이 = 실시간 모니터링처럼 [지도 | 오른쪽 칸].
- 지도: 중동 16개국 면을 최근 12개월 종합 리스크로 칠한다 (중동_스토리맵 01 지금과 같은 색 · 기준)
- 나라를 누르면 오른쪽 칸에 «그 나라 → 상대국 리스크» 그래프(최근 10년)와 상대국 카드 5장을 위아래로
- 오른쪽 칸의 «크게 보기» 를 누르면 지도 자리까지 넓혀 원래 리스크 추이 화면(1980년부터 · 필터)으로 본다
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
def recent_country_risk():
    """나라별 최근 12개월 종합 리스크 평균 (country_monthly 의 마지막 달부터 12개월, 스토리맵 01 과 같은 기준)."""
    c = relations.load_country()
    last = c["date"].max()
    r = c[c["date"] > last - pd.DateOffset(months=12)]
    return r.groupby("country")["all_risk"].mean().to_dict(), last


def _risk_map(sel):
    light = theme.is_light()
    names = relations.COUNTRIES
    val, last = recent_country_risk()
    kr_iso = {v: k for k, v in names.items()}
    iso = [c for c in names if c in val]
    z = [min(max((val[c] - 0.15) / 0.55, 0), 1) for c in iso]          # 0.15 ~ 0.7 을 색 막대 끝에서 끝으로
    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locations=iso, z=z, locationmode="ISO-3", showscale=False, zmin=0, zmax=1,
        colorscale=_scale(SEQ_LIGHT if light else SEQ_DARK),
        marker_line_color="#ffffff" if light else "#0f1116", marker_line_width=0.9,
        customdata=iso,                                                   # 클릭하면 이 값(ISO3)이 돌아온다
        hovertext=[f"<b>{names[c]}</b> 최근 12개월 종합 리스크 {val[c]:.2f}<br>누르면 오른쪽에 상대국 리스크" for c in iso],
        hovertemplate="%{hovertext}<extra></extra>"))
    if sel in iso:                                                        # 고른 나라: 굵은 테두리
        fig.add_trace(go.Choropleth(
            locations=[sel], z=[0], locationmode="ISO-3", showscale=False, hoverinfo="skip",
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_color="#4f46e5" if light else "#ffffff", marker_line_width=3))
    # 이름 + 값 (좁은 나라는 바깥으로 빼고 선으로 잇는다 — 실시간 지도와 같은 자리)
    rows = [(kr, COUNTRY_POS[kr], kr_iso.get(kr)) for kr in COUNTRY_POS]
    llat, llon = [], []
    for kr, (a_lat, a_lon, t_lat, t_lon) in LABEL_OUT.items():
        llat += [a_lat, t_lat, None]; llon += [a_lon, t_lon, None]
    fig.add_trace(go.Scattergeo(lat=llat, lon=llon, mode="lines", hoverinfo="skip",
                                line=dict(width=0.8, color="rgba(28,26,23,.45)" if light else "rgba(255,255,255,.45)")))
    pos = [LABEL_OUT[kr][2:] if kr in LABEL_OUT else p for kr, p, _ in rows]
    txt = [(f"<b>{SHORT_NAME.get(kr, kr)}</b> {val.get(c, 0):.2f}" if kr in LABEL_OUT
            else f"<b>{SHORT_NAME.get(kr, kr)}</b><br>{val.get(c, 0):.2f}") for kr, _, c in rows]
    fig.add_trace(go.Scattergeo(
        lat=[p[0] for p in pos], lon=[p[1] for p in pos], mode="text", hoverinfo="skip", text=txt,
        textposition=[("middle left" if kr in LEFT_SIDE else "middle right") if kr in LABEL_OUT else "middle center"
                      for kr, _, _ in rows],
        textfont=dict(size=13, color="#1c1a17" if light else "#ffffff", family="JetBrains Mono, Pretendard, sans-serif")))
    fig.update_layout(
        geo=dict(projection_type="mercator", fitbounds="locations", visible=True,
                 showland=True, landcolor="#dfe5ef" if light else "#1a1d25",
                 showcountries=True, countrycolor="#c9d2e0" if light else "#262a34", countrywidth=0.6,
                 showcoastlines=False, showocean=False, showlakes=False, showframe=False, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False, height=640, paper_bgcolor="rgba(0,0,0,0)",
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
    st.markdown(f"""
<div class="lv-lg">
  <div class="lv-lg-a">
    <div class="lv-lg-t">최근 12개월 종합 리스크</div>
    <div class="lv-grad" style="background:linear-gradient(90deg,{','.join(seq)})"></div>
    <div class="lv-ticks"><span>0.15</span><span>0.4</span><span>0.7+</span></div>
  </div>
  <div class="lv-lg-b">
    <div class="lv-note">0 = 협력 보도만, 1 = 갈등 보도만 (GDELT 보도량 가중) · {last - pd.DateOffset(months=11):%Y-%m}–{last:%Y-%m} 월평균</div>
    <div class="lv-note">나라를 누르면 오른쪽에 그 나라 → 상대국 리스크 (최근 {YEARS}년)</div>
    <div class="lv-note lv-src">출처 GDELT → country_monthly_1980_2026 (all_risk)</div>
  </div>
</div>""", unsafe_allow_html=True)


def _side_panel(code):
    """오른쪽 칸: 위 = 그 나라 → 상대국 리스크 (최근 10년), 아래 = 상대국 카드 5장."""
    names = relations.COUNTRIES
    risk = relations.load_risk()
    region = relations.load_region()
    series = relations.pair_series(risk, code, "out")
    p1 = series.index.max()
    p0 = p1 - pd.DateOffset(years=YEARS) + pd.offsets.MonthBegin(0)
    in_range = risk_view._in_period(series, p0, p1)
    avg = in_range.mean().sort_values(ascending=False)
    partners = list(avg.index[:risk_view.CARD_N])
    focus = partners[0]

    hd1, hd2 = st.columns([1.5, 1], vertical_alignment="center")
    hd1.markdown(f'<div class="chart-h">리스크 추이 {info_icon("선 = 국가쌍 월별 리스크의 12개월 이동평균 (0~1) · 점선 = 중동 전체 · 최근 10년 평균 상위 5곳 · 크게 보기를 누르면 1980년부터 · 필터")}</div>',
                 unsafe_allow_html=True)
    if hd2.button("크게 보기 ⤢", key="riskmap_expand", width="stretch"):
        st.session_state["riskmap_big"] = True
        st.rerun()

    fig = go.Figure()
    rs = risk_view._in_period(relations.smooth(region, risk_view.HOW), p0, p1)
    fig.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name="중동 전체",
                             line=dict(color="#94a3b8", width=1.4, dash="dot"),
                             hovertemplate="중동 전체 %{y:.3f}<extra></extra>"))
    pcol = risk_view._line_colors(partners, focus)
    for q in sorted(partners, key=lambda x: x == focus):
        sm = risk_view._in_period(relations.smooth(series[q], risk_view.HOW), p0, p1)
        fig.add_trace(go.Scatter(x=sm.index, y=sm.values, mode="lines", name=names[q],
                                 line=dict(color=pcol[q], width=3 if q == focus else 1.4),
                                 opacity=1 if q == focus else 0.5,
                                 hovertemplate=f"{names[code]} → {names[q]} %{{y:.3f}}<extra></extra>"))
    risk_view._gap_bands(fig, relations.gap_months(risk), p0, p1)
    fig.update_layout(**DARK_LAYOUT, height=340, hovermode="x unified",
                      margin=dict(l=6, r=6, t=10, b=6),
                      legend=dict(orientation="h", y=-0.12, yanchor="top", x=0, font=dict(size=12)))
    risk_view._time_axes(fig, p0, p1)
    fig.update_xaxes(dtick="M24", tickangle=0, tickfont=dict(size=12))   # 좁은 칸: 2년 간격 · 눕히지 않음
    fig.update_yaxes(tickfont=dict(size=12), dtick=0.2)
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG, key="riskmap_chart")

    last_m = in_range.index.max()
    ma = {q: risk_view._in_period(relations.smooth(series[q], risk_view.HOW), p0, p1).iloc[-1] for q in partners}
    with st.container(key="riskmap_cards"):
        risk_view.grade_pills([(q, names[q], in_range[q].iloc[-1], in_range[q].mean(), ma[q]) for q in partners],
                              relations.load_dists()["pair"], f"{names[code]} → 상대국", hi=focus, layer="국가쌍",
                              title_sub=f"{last_m:%Y-%m} 기준 · 평균 = 최근 {YEARS}년",
                              title_tip="큰 숫자 = 그 달 한 달의 리스크 · 평균 = 최근 10년 월별 평균 · 이 달 상위 % = 국가쌍 1980년 이후 모든 값과 견준 순위",
                              month=f"{last_m:%Y-%m}", period=risk_view._pstr(p0, p1))


def risk_map_page():
    sel = st.session_state.get("riskmap_sel", DEFAULT)
    if st.session_state.get("riskmap_big"):
        # 크게 보기: 지도 자리까지 넓혀 원래 리스크 추이 화면 (고른 나라를 행위 주체로)
        if st.button("← 지도로 돌아가기", key="riskmap_back"):
            st.session_state["riskmap_big"] = False
            st.rerun()
        f = st.session_state.setdefault("rel_f", {"country": sel, "partners": None, "partners_for": None, "focus": None})
        if st.session_state.get("riskmap_big_for") != sel:          # 지도에서 고른 나라로 맞춘다 (처음 한 번)
            f["country"] = sel
            st.session_state.pop("rel_country", None)       # 위젯 값을 지워야 f["country"] 로 다시 고른다
            st.session_state.pop("rel_view", None)          # 보기는 기본(국가쌍 리스크)으로
            st.session_state["riskmap_big_for"] = sel
        risk_view.page(show_title=False)
        return
    left, right = st.columns([2.3, 1], gap="medium")
    with left, st.container(border=True, key="riskmap_panel"):
        st.markdown('<div class="map-head" style="border:none;padding-bottom:0"><b>나라별 최근 12개월 종합 리스크</b> '
                    + info_icon("나라를 누르면 오른쪽에 그 나라 → 상대국 리스크가 나옵니다") + '</div>', unsafe_allow_html=True)
        _risk_map(sel)
    with right, st.container(border=True, key="riskmap_side"):
        _side_panel(sel)
