from __future__ import annotations

from pathlib import Path

import streamlit as st

import charts
import data

st.set_page_config(
    page_title="Global Conflict & Relations Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 스타일 로드
st.markdown(f"<style>{Path(__file__).with_name('style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

PLOTLY_CFG = {"displayModeBar": False, "scrollZoom": False}


# 작은 HTML 헬퍼
def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def panel_head(icon: str, title: str, sub: str = "", right: str = "") -> None:
    right_html = f'<span class="panel-link">{right}</span>' if right else ""
    html(
        f'<div class="panel-head"><div class="panel-title"><span>{icon}</span>{title}</div>{right_html}</div>'
        + (f'<div class="panel-sub">{sub}</div>' if sub else "")
    )


def kpi_card(k: dict) -> str:
    unit = f"<small>{k['unit']}</small>" if k["unit"] else ""
    note = f'<span class="delta-note">{k["delta_note"]}</span>' if k["delta_note"] else ""
    return (
        f'<div class="kpi {k["tone"]}"><div class="ico">{k["icon"]}</div><div>'
        f'<div class="lbl">{k["label"]}</div>'
        f'<div class="val">{k["value"]}{unit}<span class="delta">{k["delta"]}</span>{note}</div>'
        f"</div></div>"
    )


def case_row(c: dict) -> str:
    tags = "".join(
        f'<span class="tag{" red" if t in ("종교", "민족") else ""}">{t}</span>' for t in c["tags"]
    )
    return (
        f'<div class="case"><div class="thumb">{c["emoji"]}</div>'
        f'<div><span class="name">{c["name"]}</span><span class="period">{c["period"]}</span>'
        f'<div class="tags">{tags}</div></div>'
        f'<div class="right"><div class="ev"><div class="l">이벤트 수</div><div class="v">{c["events"]:,}</div></div>'
        f'{charts.sparkline_svg(c["trend"])}</div></div>'
    )


# 사이드바
with st.sidebar:
    html(
        '<div class="sb-brand"><div class="icon">🌐</div><div>'
        '<div class="title">Global Conflict &amp;<br>Relations Dashboard</div>'
        '<div class="sub">데이터로 보는 세계의 관계</div></div></div>'
    )
    page = st.radio("메뉴", data.NAV_PAGES, label_visibility="collapsed")

    st.divider()
    html('<div class="sb-section">🔻 필터</div>')

    period = st.slider("기간", *data.PERIOD_RANGE, value=data.PERIOD_RANGE)
    continent = st.selectbox("대륙", data.CONTINENTS)
    cause_filter = st.selectbox("분쟁 원인", data.CAUSES)
    country_filter = st.selectbox("국가", data.COUNTRIES)

    st.write("")
    apply = st.button("🔍  적용하기", type="primary", width="stretch")

    html(
        '<div class="sb-quote">“데이터는 갈등을 이해하고,<br>더 평화로운 세계를 만드는<br>첫 걸음입니다.”'
        '<div class="en">Data for a More Peaceful World</div></div>'
        '<div class="sb-sources"><b>Data Sources</b><span>GDELT</span>|<span> SIPRI</span>|<span> UN Comtrade</span></div>'
        f'<div class="sb-updated">Last Updated &nbsp;{data.LAST_UPDATED}</div>'
    )

# 필터 값은 세션에 저장 (나중에 data 함수에 넘겨서 실제 필터링)
filters = {"period": period, "continent": continent, "cause": cause_filter, "country": country_filter}
st.session_state["filters"] = filters


# 헤더
h1, h2, h3 = st.columns([6, 1.6, 1.8])
with h1:
    html('<div class="hdr-title">분쟁의 원인과 국가 간 관계, 데이터로 보다</div>')
    html('<div class="hdr-sub">정치, 영토, 이념, 종교, 민족 등 다양한 이유로 발생하는 국제 분쟁을 분석하고, 관련 국가들의 무기 거래 추이까지 함께 살펴봅니다.</div>')
with h2:
    y, m, d = data.LAST_UPDATED.split("-")
    html(f'<div class="hdr-badge"><span style="font-size:20px">📅</span><div><div class="lbl">최근 데이터 기준</div><div class="val">{y}. {m}. {d}</div></div></div>')
with h3:
    html('<div class="hdr-tag">🌱 데이터가 만드는<br>더 평화로운 세상</div>')


# 페이지: 개요
def page_overview() -> None:
    # KPI
    cols = st.columns(4)
    for col, k in zip(cols, data.get_kpis()):
        with col:
            html(kpi_card(k))

    st.write("")
    left, right = st.columns([1.2, 1], gap="medium")

    # 왼쪽: 지도 + 네트워크
    with left:
        with st.container(border=True):
            t, s = st.columns([3, 1.2])
            with t:
                panel_head("🗺️", "세계 분쟁 현황 지도", "분쟁의 원인과 강도를 한눈에 확인할 수 있습니다.")
            with s:
                map_cause = st.selectbox("분쟁 원인", data.CAUSES, key="map_cause", label_visibility="collapsed")
            html(
                '<div class="legend"><span class="t">분쟁 강도 (GDELT 이벤트 수)</span>'
                + "".join(
                    f'<span><i style="background:{c}"></i>{l}</span>'
                    for c, l in zip(reversed(charts.INTENSITY_COLORS), ["매우 높음", "높음", "보통", "낮음", "데이터 없음"])
                )
                + "</div>"
            )
            st.plotly_chart(charts.world_map(data.get_map_data(), data.get_map_markers()), width="stretch", config=PLOTLY_CFG)

        with st.container(border=True):
            t, s = st.columns([3, 1.2])
            with t:
                panel_head("🔗", "분쟁 원인별 국가 간 관계 네트워크", "분쟁의 주요 원인에 따른 국가 간 관계를 네트워크로 보여줍니다.")
            with s:
                net_cause = st.selectbox("분쟁 원인", data.CAUSES[1:], index=data.CAUSES[1:].index("종교"), key="net_cause", label_visibility="collapsed")
            nodes, edges = data.get_network(net_cause)
            st.plotly_chart(charts.network_graph(nodes, edges), width="stretch", config=PLOTLY_CFG)

    # 오른쪽: 주요 분쟁 사례 + 상세 분석
    with right:
        with st.container(border=True):
            panel_head("💥", "주요 분쟁 사례", "분쟁의 원인과 국가 간 관계, 최근 동향을 확인할 수 있습니다.", right="전체 보기 →")
            html("".join(case_row(c) for c in data.get_major_conflicts()))

        with st.container(border=True):
            t, s = st.columns([2, 1.4])
            with t:
                panel_head("🔍", "선택한 분쟁의 상세 분석")
            with s:
                selected = st.selectbox("분쟁 선택", data.get_conflict_names(), key="sel_conflict", label_visibility="collapsed")

            a, b = st.columns([1, 1.3])
            with a:
                html('<div class="sub-title">분쟁 개요</div>')
                ov = data.get_conflict_overview(selected)
                html('<table class="kv">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in ov.items()) + "</table>")
            with b:
                html('<div class="sub-title">분쟁 이벤트 추이 <span style="color:#8b98ad;font-weight:500">(GDELT)</span></div>')
                st.plotly_chart(charts.events_line(data.get_conflict_events(selected)), width="stretch", config=PLOTLY_CFG)

            html('<div class="sub-title">관련 국가의 무기 거래량 추이 <span style="color:#8b98ad;font-weight:500">(SIPRI, TIV)</span></div>')
            st.plotly_chart(charts.arms_trade_lines(data.get_arms_trade(selected)), width="stretch", config=PLOTLY_CFG)


# 나머지 페이지 (뼈대만)
def page_placeholder(title: str, desc: str) -> None:
    with st.container(border=True):
        panel_head("🧩", title, desc)
        st.info("이 페이지는 아직 준비 중입니다. 데이터가 추가되면 여기에 분석 내용이 채워집니다.")


PAGES = {
    "개요": page_overview,
    "국가 간 관계 분석": lambda: page_placeholder("국가 간 관계 분석", "분쟁 당사국과 주변국의 우호·적대 관계를 심층 분석합니다."),
    "분쟁 원인 분석": lambda: page_placeholder("분쟁 원인 분석", "영토·정치·이념·종교·민족·자원 등 원인별 분쟁 분포와 추이를 분석합니다."),
    "무기 거래 추이": lambda: page_placeholder("무기 거래 추이", "SIPRI TIV 기준 무기 수출입 추이와 분쟁의 연관성을 살펴봅니다."),
    "데이터 소개": lambda: page_placeholder("데이터 소개", "GDELT, SIPRI, UN Comtrade 데이터의 출처·범위·전처리 방법을 설명합니다."),
}

PAGES[page]()
