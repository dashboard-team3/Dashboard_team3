"""리스크와 무기 거래 · 중동 무기 거래 분석 (원본 app2.py 의 7. 을 v2 에서 나눔).

page()         메뉴 '리스크와 무기 거래' — 나라 하나를 골라 연 리스크 · 무기 수입 · 시차 상관 (_country)
region_page()  메뉴 '중동 무기 거래 분석' — 나라 선택 없이 중동 16개국 전체, 갈등 급증 전후 무기 주문 (views/surge_view.py)
2026-09-30: 한 페이지 안 개요 카드 + 버튼으로 고르던 것을 사이드바 메뉴 두 개로 나눴다."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.ui import page_sub, term
from core import theme
from core.sidebar import page_filters, filter_note
from core.ui import ctitle, info_icon, C_RISK, C_COOP, C_ARMS, C_TEXT, CHART_CONFIG, DARK_LAYOUT, section_head, info
from sources import relations
from views import surge_view


def _ra_filters(names, y0, y1):
    """리스크와 무기 거래 페이지 필터: 제목 아래 상자 한 줄에 [나라][기간]. 값은 session_state['ra_f']에 보관."""
    f = st.session_state.setdefault("ra_f", {"country": "SAU", "years": (max(y0, 1990), y1)})
    box = page_filters("리스크와 무기 거래")              # v2: 본문 맨 위 접이식
    c1, c2 = box.columns(2, gap="medium")                 # 나라 · 기간을 한 줄에 둘
    f["country"] = c1.selectbox("나라", list(names), index=list(names).index(f["country"]),
                                format_func=names.get, key="ra_country")
    f["years"] = c2.slider("기간", y0, y1, f["years"], key="ra_years")
    filter_note(f"{names[f['country']]} · {f['years'][0]}–{f['years'][1]}")
    return f["country"], f["years"]


def page():
    """리스크와 무기 거래: 나라 하나를 골라 연 리스크와 무기 수입을 본다.
    (중동 전체 분석은 2026-09-30 부터 사이드바 메뉴 '중동 무기 거래 분석' 으로 따로 뺐다 → region_page)"""
    st.title("리스크와 무기 거래")
    page_sub("나라 하나를 골라 연 " + term("리스크") + "와 SIPRI 무기 수입을 1980년부터 나란히 보고, "
             "리스크가 오른 뒤 몇 해 안에 수입이 늘었는지 시차 상관으로 견줍니다.")
    _country()


def region_page():
    """중동 무기 거래 분석 (사이드바 메뉴): 나라 선택 없이 중동 16개국 전체, 갈등 급증 전후 무기 주문.
    화면 = views/surge_view.py, 계산 = sources/surge.py (팀원의 급증과_무기거래 앱을 옮긴 것)."""
    st.title("중동 무기 거래 분석")
    page_sub("나라를 고르지 않고 중동 16개국 전체에서 " + term("리스크") + "가 " + term("급증") + "한 해를 찾아, "
             "그 앞뒤로 무기 주문이 어떻게 바뀌었는지 사례로 봅니다.")
    surge_view.page()


def _country():
    """국가별 리스크와 무기 거래: 나라 하나를 골라 연 리스크와 SIPRI 무기 수입을 나란히 놓고, 시차 상관으로 견준다.
    이 보기에서만 사이드바에 나라 · 기간 필터가 나온다."""
    names = relations.COUNTRIES
    m = relations.arms_panel()
    y0, y1 = int(m["year"].min()), int(m["year"].max())

    country, years = _ra_filters(names, y0, y1)

    g = m[(m["country"] == country) & m["year"].between(*years)].sort_values("year")
    if g.empty:
        st.info("이 기간에는 자료가 없습니다.")
        return
    gy = g.set_index("year")
    st.markdown(f'<div class="summary"><b>{names[country]}</b> {years[0]}–{years[1]}: 연 리스크 평균 <b>{g["risk"].mean():.3f}</b> '
                f'(가장 높았던 해 {int(gy["risk"].idxmax())}년 {gy["risk"].max():.3f}) · 무기 수입 합 <b>{g["tiv"].sum():,.0f} TIV</b> '
                f'(가장 많이 산 해 {int(gy["tiv"].idxmax())}년 {gy["tiv"].max():,.0f})</div>', unsafe_allow_html=True)
    span = years[1] - years[0]
    step = 1 if span <= 12 else 2 if span <= 25 else 5

    section_head("01", f"연 리스크와 무기 수입 · {names[country]}",
                 "선이 그 나라의 <b>연 종합 리스크</b>(월별 값을 그 달 일수로 가중 평균 = 그 해 모든 날의 평균), 막대가 <b>SIPRI 무기 수입</b>(주문 연도 기준 TIV). "
                 "두 축의 단위가 달라 높이를 직접 비교하지는 않습니다.")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=g["year"], y=g["tiv"], name="무기 수입 (주문 TIV)", marker_color=C_ARMS, opacity=0.75,
                         hovertemplate="%{x}년 · 수입 %{y:,.0f} TIV<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=g["year"], y=g["risk"], name="연 리스크", mode="lines+markers",
                             line=dict(color=C_RISK, width=3), marker=dict(size=6),
                             hovertemplate="%{x}년 · 리스크 %{y:.3f}<extra></extra>"), secondary_y=True)
    fig.update_layout(**DARK_LAYOUT, height=440, hovermode="x unified", bargap=0.15,
                      title=dict(text=ctitle(f"{names[country]} 연 리스크와 무기 수입",
                                          f"{years[0]}–{years[1]} · 선 = 연 리스크 · 막대 = SIPRI 무기 수입(주문 TIV)"),
                                 font=dict(size=17, color=C_TEXT), x=0),
                      margin=dict(l=10, r=10, t=70, b=10),
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=14)))
    fig.update_xaxes(gridcolor="#1f2b44", dtick=step, title_text="연도", tickfont=dict(size=14))
    fig.update_yaxes(title_text="무기 수입 (TIV)", gridcolor="#1f2b44", secondary_y=False, tickfont=dict(size=14))
    fig.update_yaxes(title_text="리스크", range=[0, max(0.3, g["risk"].max() * 1.15)], showgrid=False, secondary_y=True)
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG)
    info("**연 리스크** = 그 나라의 월별 종합 리스크를 그 달 일수로 가중해 평균한 값(= 그 해 모든 날의 평균). "
          "12개월이 모두 있는 해만 계산.\n\n"
          "**무기 수입** = SIPRI 계약의 주문 연도 기준 TIV 합. 실제 인도는 보통 몇 년 뒤이고, TIV는 달러 금액이 아닙니다. "
          "주문이 없던 해는 0.", formula=True)
    with st.expander("숫자로 보기"):
        st.dataframe(g[["year", "risk", "tiv"]].rename(columns={"year": "연도", "risk": "연 리스크", "tiv": "무기 수입 (TIV)"}).round(3),
                     hide_index=True, width="stretch")

    # ── 시차 상관 (같은 화면 아래에) ──
    section_head("02", "리스크가 오른 뒤 무기 수입이 늘었나 · 시차 상관",
                 "올해 리스크와 <b>k년 뒤</b> 수입(log)의 피어슨 상관. 왼쪽은 고른 나라의 점, 오른쪽은 16개국을 나라 안에서 표준화해 "
                 "합친 값과 나라별 상관의 중앙값. 함께 움직여도 인과관계나 통계적 유의성을 뜻하지 않습니다.")
    lag = st.slider("시차 — 리스크가 오른 해로부터 몇 해 뒤의 수입을 볼까", 0, 3, 1, key="ra_lag")

    # 고른 나라: 연 리스크(t) vs log 수입(t+k)
    gg = g.copy()
    # lag년 뒤 수입은 연도로 찾는다 (행 기준으로 당기면 연 리스크가 빠진 해에서 짝이 밀린다)
    _full = m[m["country"] == country].set_index("year")["ltiv"]
    gg["y"] = [_full.get(y + lag, float("nan")) for y in gg["year"]]
    gg = gg.dropna(subset=["y"])
    r_one = relations._pearson(gg["risk"], gg["y"]) if len(gg) >= 5 else float("nan")

    # 연도 글자는 겹치지 않는 것만: 최근 해부터 적고, 이미 적은 글자와 가까우면 건너뛴다 (나머지는 마우스로)
    xr = (gg["risk"].max() - gg["risk"].min()) or 1
    yr = (gg["y"].max() - gg["y"].min()) or 1
    order_ = sorted(gg.index, key=lambda i: -int(gg.at[i, "year"]))
    shown, labs = [], {}
    for i in order_:
        px, py = (gg.at[i, "risk"] - gg["risk"].min()) / xr, (gg.at[i, "y"] - gg["y"].min()) / yr
        if all(abs(px - qx) > 0.09 or abs(py - qy) > 0.07 for qx, qy in shown):
            shown.append((px, py)); labs[i] = str(int(gg.at[i, "year"]))
    gg["lab"] = [labs.get(i, "") for i in gg.index]

    left, right = st.columns([1.2, 1], gap="medium")
    with left:
        fig_s = go.Figure(go.Scatter(
            x=gg["risk"], y=gg["y"], mode="markers+text", text=gg["lab"], textposition="top center",
            customdata=gg["year"], textfont=dict(size=12, color="#8b98ad"), marker=dict(color=C_RISK, size=9, opacity=0.8),
            hovertemplate="%{customdata}년 리스크 %{x:.3f}<br>" + f"{lag}년 뒤" + " log 수입 %{y:.2f}<extra></extra>", name="연도"))
        if len(gg) >= 3 and gg["risk"].std() > 0:
            # 추세선: 기울기 = 공분산 ÷ 분산 (더하기·곱하기만)
            dx = gg["risk"] - gg["risk"].mean(); dy = gg["y"] - gg["y"].mean()
            slope = (dx * dy).sum() / (dx * dx).sum(); icpt = gg["y"].mean() - slope * gg["risk"].mean()
            xs = [gg["risk"].min(), gg["risk"].max()]
            fig_s.add_trace(go.Scatter(x=xs, y=[icpt + slope * x for x in xs], mode="lines", name="선형 추세",
                                       line=dict(color=C_ARMS, width=2, dash="dot"), hoverinfo="skip"))
        fig_s.update_layout(**DARK_LAYOUT, height=400, showlegend=False,
                            title=dict(text=ctitle(f"리스크와 {'같은 해' if lag == 0 else f'{lag}년 뒤'} 무기 수입",
                                               f"{names[country]} · 점 = 한 해 · 점선 = 추세 · "
                                               + (f"r = {r_one:+.2f}" if pd.notna(r_one) else "비교할 해가 5개 미만")),
                                       font=dict(size=17, color=C_TEXT), x=0),
                            margin=dict(l=10, r=10, t=70, b=10))
        fig_s.update_xaxes(title_text="연 리스크 (t)", gridcolor="#1f2b44", tickfont=dict(size=14))
        fig_s.update_yaxes(title_text=f"log(1 + 무기 수입 TIV) (t+{lag})", gridcolor="#1f2b44", tickfont=dict(size=14))
        st.plotly_chart(theme.adapt(fig_s), width="stretch", config=CHART_CONFIG)
    with right:
        ks, pooled, med, mine = [], [], [], []
        for k in range(4):
            pr, per = relations.lag_corr_all(m, k, years)
            ks.append("같은 해" if k == 0 else f"{k}년 뒤")
            pooled.append(pr); med.append(per.median() if len(per) else float("nan"))
            mine.append(per.get(country, float("nan")))
        fig_b = go.Figure()
        for vals, name, col in [(pooled, "16개국 전체", C_RISK), (med, "나라별 중앙값", C_COOP), (mine, names[country], C_ARMS)]:
            fig_b.add_trace(go.Bar(x=ks, y=vals, name=name, marker_color=col,
                                   text=[f"{v:+.2f}" if pd.notna(v) else "-" for v in vals], textposition="outside", cliponaxis=False,
                                   hovertemplate=name + " · %{x} · r = %{y:+.3f}<extra></extra>"))
        lo = min([-0.35] + [v - 0.1 for v in pooled + med + mine if pd.notna(v)])
        hi = max([0.35] + [v + 0.1 for v in pooled + med + mine if pd.notna(v)])
        fig_b.update_layout(**DARK_LAYOUT, height=400, barmode="group",
                            title=dict(text=ctitle("시차별 상관계수 (피어슨 r)", f"{years[0]}–{years[1]} · 16개국 전체 · 나라별 중앙값 · {names[country]}"), font=dict(size=17, color=C_TEXT), x=0),
                            # 반쪽 폭이라 범례가 두 줄이 되면 제목과 겹친다 → 그래프 아래로
                            margin=dict(l=10, r=10, t=50, b=80),
                            legend=dict(orientation="h", y=-0.25, yanchor="top", x=0, font=dict(size=14)))
        fig_b.update_xaxes(title_text="수입 시점", gridcolor="#1f2b44", tickfont=dict(size=14))
        fig_b.update_yaxes(title_text="피어슨 r", range=[lo, hi], gridcolor="#1f2b44", zeroline=True, zerolinecolor="#94a3b8")
        st.plotly_chart(theme.adapt(fig_b), width="stretch", config=CHART_CONFIG)

    pr0, per0 = relations.lag_corr_all(m, lag, years)
    n_pos = int((per0 > 0).sum())
    if pd.isna(pr0) or not len(per0):
        # 기간이 짧아 시차를 두면 비교할 해가 5개 미만 → r 을 못 구한다 (nan 을 '약하지 않은 상관'으로 읽지 않게)
        st.info(f"**시차 {lag}년** — {years[0]}–{years[1]}년은 시차 {lag}년을 두면 나라마다 비교할 해가 5개보다 적어 "
                "상관계수를 계산하지 않았습니다. 기간을 넓히거나 시차를 줄여 보세요.")
    else:
        st.info(f"**시차 {lag}년 · 16개국 전체 r = {pr0:+.3f} · 나라별 중앙값 {per0.median():+.3f} · 양(+)인 나라 {n_pos}/{len(per0)}** — "
                f"{'리스크가 오른 해에 수입도 늘었다고 보기 어렵습니다. 상관이 0 근처라는 것은 둘이 따로 움직인다는 뜻이지 관계가 없다는 증명은 아닙니다.' if abs(pr0) < 0.3 else '약하지 않은 상관입니다. 다만 인과관계나 유의성을 뜻하지는 않습니다.'} "
                f"SIPRI는 계약 연도 기준이라 실제 인도는 몇 해 뒤이고, 수입은 예산·정권·공급국 사정처럼 갈등과 무관한 요인에도 크게 좌우됩니다.")

    st.markdown(f'<div class="pill-t">{names[country]} · 같은 상관을 네 방식으로 '
                + info_icon("큰 계약 한 건이나 장기 추세 때문인지 가려 봅니다. 네 값이 같은 방향으로 크면 믿을 만한 관계. "
                            "Pearson 만 크고 최대 주문 제외에서 꺼지면 계약 한 건 효과, 변화량에서 꺼지면 둘 다 오르는 장기 추세 효과. "
                            "비교한 해가 5개 미만이면 계산하지 않습니다.") + "</div>", unsafe_allow_html=True)
    lt = relations.lag_table(gy["risk"], gy["tiv"])
    st.dataframe(lt.style.format({c: "{:+.2f}" for c in ["Pearson", "최대 주문 제외", "변화량", "Spearman"]}, na_rep="-"),
                 hide_index=True, width="stretch")
    info("**16개국 전체** = 나라마다 리스크와 log 수입을 그 나라 평균·표준편차로 표준화한 뒤 16개국 점을 모두 모아 잰 피어슨 r. "
          "나라 간 규모 차이를 걷어낸 값.\n\n"
          "**나라별 중앙값** = 나라마다 따로 잰 r의 중앙값. 몇 나라가 결과를 끌고 가는지 보는 용도.\n\n"
          "**표본** = 고른 기간 안에서 리스크(t)와 수입(t+k)이 모두 있는 해. 비교할 해가 5개 미만인 나라는 뺍니다.")
