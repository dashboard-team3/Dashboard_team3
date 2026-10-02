"""리스크와 무기 거래 — 나라 하나를 골라 «지금 어떤 상태인가» 를 한 장으로 본다 (2026-10-01).

화면에서 부르던 이름이 «국가 카드» 였다가 «리스크와 무기 거래» 가 되었다 (파일 이름은 그대로 둔다).

다른 쪽은 지표마다 화면이 흩어져 있어, 한 나라를 알고 싶으면 네 쪽을 오가야 했다.
여기서는 한 나라의 리스크 · 상대국 · 무기 · 급증 이력을 한 화면에 모은다.

모든 값은 우리 자료에서 바로 뽑는다.
    리스크 · 상대국   country_monthly · risk_monthly
    무기 · 공급국     SIPRI_pre_1980_2025 (주문 연도 · TIV)
    급증 이력         sources/surge.py 의 급증 판정 (리스크와 무기 거래 쪽과 같은 기준)
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core import theme
from core.ui import C_ARMS, C_RISK, C_TEXT, CHART_CONFIG, DARK_LAYOUT, ctitle, info_icon, page_sub, term, section_head
from sources import relations, surge as A
from views import risk_arms_view

HOW = "12개월 이동평균"
WIN = 12                      # «최근» 의 길이 (달)

# SIPRI 의 품목 이름(영어)을 화면용 한글로. 나라별 상위 3위 안에 드는 20종만 옮기고,
# 표에 없는 이름은 영어 그대로 보여 준다 (144종을 다 옮기면 틀린 말이 섞일 수 있다).
WEAPON_KO = {
    "fighter/ground-attack aircraft": "전투·공격기",
    "fighter aircraft": "전투기",
    "combat helicopter": "공격헬기",
    "transport helicopter": "수송헬기",
    "helicopter": "헬기",
    "transport aircraft": "수송기",
    "heavy transport aircraft": "대형 수송기",
    "tank": "전차",
    "armoured personnel carrier": "병력수송 장갑차",
    "infantry fighting vehicle": "보병전투차",
    "armoured reconnaissance vehicle": "정찰 장갑차",
    "towed gun": "견인포",
    "submarine": "잠수함",
    "frigate": "호위함",
    "surface-to-air missile": "지대공 미사일",
    "surface-to-air missile system": "지대공 미사일 체계",
    "mobile surface-to-air missile system": "이동형 지대공 미사일 체계",
    "surface-to-surface missile": "지대지 미사일",
    "anti-ballistic missile missile": "요격 미사일",
    "anti-ballistic missile system": "미사일 방어 체계",
}


def _recent(df, last, win=WIN):
    """마지막 달에서 win 개월 치만 자른다."""
    return df[df["date"] > last - pd.DateOffset(months=win)]


@st.cache_data(show_spinner="국가별 요약 산출 중…")
def profile(code):
    """나라 하나의 요약값 묶음. 화면에서 쓰는 수는 전부 여기서 나온다."""
    c = relations.load_country()
    p = relations.load_risk()
    s = relations.load_sipri()
    last = c["date"].max()

    cy = _recent(c[c["country"] == code], last)
    out = _recent(p[p["Actor1CountryCode"] == code], last).groupby("Actor2CountryCode")["risk"].mean()
    inc = _recent(p[p["Actor2CountryCode"] == code], last).groupby("Actor1CountryCode")["risk"].mean()

    mine = s[s["code"] == code]
    tiv = float(mine["tiv_order"].sum())
    ly = int(s["year"].max())                      # SIPRI 는 «주문 연도» 라 달이 없다 — 가장 최근 해로 본다
    rec = mine[mine["year"] == ly]
    sup = mine.groupby("supplier_ko")["tiv_order"].sum().sort_values(ascending=False)
    wea = mine.groupby("weapon_desc")["tiv_order"].sum().sort_values(ascending=False)
    used = int((mine["status"] != "New").sum())

    ev = A.cases(A.panel())
    ev = ev[ev["country"] == code].sort_values("year")

    return dict(
        last=last,
        risk=float(cy["all_risk"].mean()), out=float(cy["out_risk"].mean()), inr=float(cy["in_risk"].mean()),
        series=c[c["country"] == code].set_index("date")["all_risk"],
        top_out=[(relations.COUNTRIES[k], v) for k, v in out.sort_values(ascending=False).head(3).items()],
        top_in=[(relations.COUNTRIES[k], v) for k, v in inc.sort_values(ascending=False).head(3).items()],
        n=len(mine), tiv=tiv, used=used,
        ly=ly, tiv_ly=float(rec["tiv_order"].sum()), n_ly=len(rec),
        suppliers=[(k, v, v / tiv * 100 if tiv else 0) for k, v in sup.head(3).items()],
        weapons=[(WEAPON_KO.get(k, k), v) for k, v in wea.head(3).items()],
        years=(int(mine["year"].min()), int(mine["year"].max())) if len(mine) else None,
        events=[(int(r["year"]), r["shape"], float(r["diff"])) for _, r in ev.iterrows()],
    )


def _stat(label, value, sub="", unit="", tone=""):
    """머리의 큰 숫자 한 칸. label 옆에 기준 기간을, 값 옆에 단위를 붙여 둔다 (2026-10-01)."""
    u = f'<span class="cs-u">{unit}</span>' if unit else ""
    return (f'<div class="cstat {tone}"><div class="cs-l">{label}</div>'
            f'<div class="cs-v">{value}{u}</div><div class="cs-s">{sub}</div></div>')


def _list_card(title, tip, rows):
    body = "".join(f'<li><span class="ci-n">{n}</span><b>{v}</b></li>' for n, v in rows) or '<li class="ci-e">자료 없음</li>'
    return f'<div class="ccard"><div class="cc-t">{title} {info_icon(tip)}</div><ul class="ci">{body}</ul></div>'


def page():
    names = relations.COUNTRIES
    st.title("리스크와 무기 거래")
    page_sub("선택 국가의 " + term("리스크") + "·주요 상대국·무기 거래·" + term("급증") + " 이력 통합 비교")

    code = st.selectbox("국가", list(names), format_func=names.get, key="card_country",
                        label_visibility="collapsed", width=260)      # 화면 끝까지 길던 상자 줄임 (2026-10-02)
    d = profile(code)
    g = relations.grade(d["risk"])
    col = relations.GRADE_COLORS[g] if g is not None else "#475569"
    txt = relations.GRADES[g] if g is not None else "자료 없음"
    period = f"{d['last'] - pd.DateOffset(months=WIN - 1):%Y-%m}–{d['last']:%Y-%m}"
    # 둘 중 큰 쪽에만 표를 단다 — «어느 쪽이 더 센가» 가 이 두 칸을 나란히 두는 이유다
    up_out = "<em>상대적으로 높음</em>" if d["out"] > d["inr"] else ""
    up_in = "<em>상대적으로 높음</em>" if d["inr"] > d["out"] else ""

    # ── 머리: 큰 숫자 네 칸. 칸마다 «무슨 기간인지» 를 제목 옆에 붙인다 (2026-10-01)
    st.markdown(
        f'<div class="chead"><div class="ch-l"><div class="ch-n">{names[code]}<span>{code}</span></div>'
        f'<div class="ch-s">리스크: <b>최근 12개월</b> ({period})<br>'
        f'무기 수입: <b>최근 1년</b> ({d["ly"]}년 주문)</div></div>'
        f'<div class="ch-r">'
        + _stat("종합 리스크 <small>최근 12개월</small>", f"{d['risk']:.3f}",
                f'<i style="background:{col}"></i>{txt}')
        + _stat("행위 주체 리스크 <small>최근 12개월</small>", f"{d['out']:.3f}",
                f"해당 국가가 행위 주체인 사건 {up_out}")
        + _stat("행위 대상 리스크 <small>최근 12개월</small>", f"{d['inr']:.3f}",
                f"해당 국가가 행위 대상인 사건 {up_in}")
        + _stat(f"무기 수입 <small>최근 1년</small>", f"{d['tiv_ly']:,.0f}", unit="TIV",
                sub=f"{d['ly']}년 주문 {d['n_ly']}건")
        + '</div></div>', unsafe_allow_html=True)

    # ── 세 칸: 상대국 · 품목 · 공급국 — 접이식(아코디언)으로 (2026-10-02 팀 피드백)
    acc = st.container(key="cty_acc").expander("요약 카드 · 리스크가 높은 상대국 · 많이 산 무기 · 주 공급국", expanded=False)
    c1, c2, c3 = acc.columns(3, gap="medium")
    with c1:
        st.markdown(_list_card(
            "상위 리스크 상대국 <small>최근 12개월</small>",
            f"{names[code]}가 행위 주체로 기록된 국가쌍의 월별 리스크 · 최근 12개월 평균 기준",
            [(n, f"{v:.2f}") for n, v in d["top_out"]]), unsafe_allow_html=True)
    with c2:
        st.markdown(_list_card(
            "주요 도입 무기 <small>누적 TIV</small>",
            "전 기간의 무기 종류별 주문 TIV 합계 · 계약 건수 제한으로 품목별 전후 비교 제외",
            [(n, f"{v:,.0f}") for n, v in d["weapons"]]), unsafe_allow_html=True)
    with c3:
        st.markdown(_list_card(
            "주요 공급국 <small>누적 TIV</small>",
            "해당 국가의 무기 공급국 · 괄호: 전체 주문 TIV 대비 공급국별 비중",
            [(n, f"{v:,.0f} ({q:.0f}%)") for n, v, q in d["suppliers"]]), unsafe_allow_html=True)

    # ── 리스크 추이 + 무기 수입 막대 + 급증한 해 (2026-10-01: 아래에 따로 있던 막대를 여기로 합침)
    m = relations.arms_panel()
    y0, y1 = int(m["year"].min()), int(m["year"].max())
    years = (max(y0, 1990), y1)
    g = m[(m["country"] == code) & m["year"].between(*years)].sort_values("year")

    section_head("01", "리스크 추이와 무기 수입",
                 "선: <b>월별 종합 리스크</b>의 12개월 이동평균(1980~) · 막대: <b>SIPRI 무기 수입</b>"
                 f"(주문 연도 TIV · {years[0]}~) · 금색 세로 점선: 리스크 급증 기준 연도(0년) · "
                 "리스크·TIV의 단위 차이에 따라 두 축의 높이 직접 비교 불가")
    # 토글은 그래프 오른쪽 위에 (그래프 제목과 같은 줄처럼 보이게) — 2026-10-01
    _, tog = st.columns([2.4, 1], vertical_alignment="center")
    with tog:
        with st.container(horizontal=True, horizontal_alignment="right", width="stretch"):
            show_ev = st.toggle(f"급증 기준 연도 표시 ({len(d['events'])}건)", value=True, key="card_surge",
                                help="해당 국가의 리스크 급증 기준 연도(0년)를 금색 세로 점선으로 표시")
    sm = relations.smooth(d["series"], HOW)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=[pd.Timestamp(int(y), 7, 1) for y in g["year"]], y=g["tiv"],
                         name="무기 수입 (주문 TIV)", marker_color=C_ARMS, opacity=0.75,
                         width=1000 * 60 * 60 * 24 * 300,          # 막대 폭 ≈ 300일 (연 단위라 한 해에 하나)
                         hovertemplate="%{x|%Y}년 · 수입 %{y:,.0f} TIV<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=sm.index, y=sm.values, mode="lines", name="종합 리스크 (12개월 이동평균)",
                             line=dict(color=C_RISK, width=3),
                             hovertemplate="%{x|%Y-%m} · 리스크 %{y:.3f}<extra></extra>"), secondary_y=True)
    if show_ev:
        for y, shape, diff in d["events"]:
            fig.add_vline(x=pd.Timestamp(y, 7, 1), line=dict(color="#f5c542", width=1.2, dash="dot"))
            fig.add_annotation(x=pd.Timestamp(y, 7, 1), y=1.0, yref="paper", yanchor="bottom",
                               text=f"{y}", showarrow=False, font=dict(size=12, color="#f5c542"))
    fig.update_layout(**DARK_LAYOUT, height=420, hovermode="x unified", bargap=0.1,
                      margin=dict(l=10, r=10, t=96, b=10),
                      title=dict(text=ctitle(f"{names[code]} 리스크와 무기 수입",
                                             f"1980-01–{d['last']:%Y-%m} · 선 = 12개월 이동평균 · "
                                             f"막대 = 주문 TIV({years[0]}~)" + (" · 점선 = 급증한 해" if show_ev else "")),
                                 font=dict(size=17, color=C_TEXT), x=0),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=14)))
    fig.update_xaxes(gridcolor="#1f2b44", tickformat="%Y", title_text="연도", title_font=dict(size=13))
    fig.update_yaxes(title_text="무기 수입 (TIV)", gridcolor="#1f2b44", secondary_y=False, tickfont=dict(size=14))
    fig.update_yaxes(title_text="리스크 (0~1)", range=[0, 1], showgrid=False, secondary_y=True, tickfont=dict(size=14))
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG)

    # ── 시차 상관 («리스크와 무기 거래» 쪽과 같은 함수. 막대 묶음은 위에 합쳤으므로 annual=False)
    if not g.empty:
        st.markdown(f'<div class="summary"><b>{names[code]}</b> {years[0]}–{years[1]}: 연간 리스크 평균 '
                    f'<b>{g["risk"].mean():.3f}</b> · 무기 수입 합 <b>{g["tiv"].sum():,.0f} TIV</b> '
                    f'(최대 주문 연도 {int(g.set_index("year")["tiv"].idxmax())}년)</div>', unsafe_allow_html=True)
    risk_arms_view.country_sections(code, years, no=2, annual=False)

    st.caption(f"리스크 · GDELT 1.0 국가별 월별 · 무기 · SIPRI 주문 연도 TIV (중고 {d['used']}건 포함) · "
               "상대국 분석 범위: 중동 16개국")
