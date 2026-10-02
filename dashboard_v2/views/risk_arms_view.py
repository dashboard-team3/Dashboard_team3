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
    f["country"] = c1.selectbox("국가", list(names), index=list(names).index(f["country"]),
                                format_func=names.get, key="ra_country")
    f["years"] = c2.slider("기간", y0, y1, f["years"], key="ra_years")
    filter_note(f"{names[f['country']]} · {f['years'][0]}–{f['years'][1]}")
    return f["country"], f["years"]


def page():
    """리스크와 무기 거래: 나라 하나를 골라 연 리스크와 무기 수입을 본다.
    (중동 전체 분석은 2026-09-30 부터 사이드바 메뉴 '중동 무기 거래 분석' 으로 따로 뺐다 → region_page)"""
    st.title("리스크와 무기 거래")
    page_sub("선택 국가의 연간 " + term("리스크") + "와 SIPRI 무기 수입의 1980년 이후 추이·"
             "시차별 상관관계 비교")
    _country()


def region_page():
    """중동 무기 거래 분석 (사이드바 메뉴): 나라 선택 없이 중동 16개국 전체, 갈등 급증 전후 무기 주문.
    화면 = views/surge_view.py, 계산 = sources/surge.py (팀원의 급증과_무기거래 앱을 옮긴 것)."""
    st.title("종합 분석")
    page_sub("중동 16개국의 " + term("리스크") + " " + term("급증") + " 기준 연도 전후 "
             "무기 주문(" + term("TIV") + ") 변화와 국가별 상관관계 분석")
    surge_view.page()


def _country():
    """국가별 리스크와 무기 거래: 나라 하나를 골라 연 리스크와 SIPRI 무기 수입을 나란히 놓고, 시차 상관으로 견준다.
    이 보기에서만 사이드바에 나라 · 기간 필터가 나온다."""
    names = relations.COUNTRIES
    m = relations.arms_panel()
    y0, y1 = int(m["year"].min()), int(m["year"].max())
    country, years = _ra_filters(names, y0, y1)
    country_sections(country, years)


def country_sections(country, years, no=1, annual=True):
    """연 리스크 × 무기 수입 그래프와 시차 상관 두 묶음. 필터 없이 «그리기만» 한다.

    국가 카드(views/country_view.py)에서도 같은 내용을 쓰려고 떼어 냈다 (2026-10-01).
    no      = 첫 소제목 번호 — 카드 쪽은 앞에 다른 묶음이 있어 2부터 시작한다.
    annual  = False 면 «연 리스크 × 무기 수입» 묶음을 건너뛰고 시차 상관만 그린다
              (카드 쪽은 그 막대를 맨 위 그래프에 합쳐 두어 여기서 또 그리면 겹친다)
    """
    names = relations.COUNTRIES
    m = relations.arms_panel()
    g = m[(m["country"] == country) & m["year"].between(*years)].sort_values("year")
    if g.empty:
        st.info("선택 기간의 자료 없음")
        return
    if not annual:
        _lag_section(country, years, m, g, no, extras=False)
        return
    gy = g.set_index("year")
    st.markdown(f'<div class="summary"><b>{names[country]}</b> {years[0]}–{years[1]}: 연간 리스크 평균 <b>{g["risk"].mean():.3f}</b> '
                f'(최고 리스크 연도 {int(gy["risk"].idxmax())}년 {gy["risk"].max():.3f}) · 무기 수입 합 <b>{g["tiv"].sum():,.0f} TIV</b> '
                f'(최대 주문 연도 {int(gy["tiv"].idxmax())}년 {gy["tiv"].max():,.0f})</div>', unsafe_allow_html=True)
    span = years[1] - years[0]
    step = 1 if span <= 12 else 2 if span <= 25 else 5

    section_head(f"{no:02d}", f"연 리스크와 무기 수입 · {names[country]}",
                 "선: <b>연간 종합 리스크</b>(월별 값을 달력 일수로 가중 평균) · 막대: <b>SIPRI 무기 수입</b>(주문 연도 기준 TIV) · "
                 "리스크·TIV의 단위 차이에 따라 두 축의 높이 직접 비교 불가")
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
    fig.update_yaxes(title_text="리스크 (0~1)", range=[0, max(0.3, g["risk"].max() * 1.15)], showgrid=False, secondary_y=True)
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG)
    info("**연간 리스크** = 해당 국가의 월별 종합 리스크를 달력 일수로 가중 평균한 값 · "
          "12개월 자료가 확보된 연도만 산출\n\n"
          "**무기 수입** = SIPRI 계약의 주문 연도 기준 TIV 합계 · 실제 거래 금액과는 구별 · 주문·인도 시점 차이 고려 · "
          "주문 미발생 연도는 0으로 반영", formula=True)
    with st.expander("상세 수치"):
        st.dataframe(g[["year", "risk", "tiv"]].rename(columns={"year": "연도", "risk": "연 리스크", "tiv": "무기 수입 (TIV)"}).round(3),
                     hide_index=True, width="stretch")

    _lag_section(country, years, m, g, no + 1)


def _lag_section(country, years, m, g, no, extras=True):
    """시차 상관 묶음만 (위 묶음과 떼어 두어 국가 카드가 이것만 부를 수 있게).

    extras=False 면 맨 아래 «같은 상관을 네 방식으로» 표를 뺀다 (국가 카드는 한 장으로 짧게 본다).
    """
    names = relations.COUNTRIES
    gy = g.set_index("year")      # 아래 «네 방식» 표가 쓴다 (위 묶음을 건너뛰면 여기서 만들어야 한다)
    # ── 시차 상관 (같은 화면 아래에) ──
    section_head(f"{no:02d}", "리스크·무기 수입의 시차별 상관관계",
                 "연간 리스크와 <b>k년 후</b> 무기 수입(log)의 피어슨 상관계수 · 왼쪽: 선택 국가의 연도별 값 · 오른쪽: 국가 내 표준화 후 16개국 "
                 "전체 집계값·국가별 상관계수 중앙값 · 상관계수만으로 인과관계 또는 통계적 유의성 판단 불가")
    lag = st.slider("무기 수입 비교 시차 (년)", 0, 3, 1, key="ra_lag", width=420)   # 화면 끝까지 길던 막대 줄임 (2026-10-02)

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
                                               f"{names[country]} · {years[0]}–{years[1]} · 가로 = 연 리스크(0~1) · 세로 = log(1+TIV) · 점 = 한 해 · 점선 = 추세 · "
                                               + (f"r = {r_one:+.2f}" if pd.notna(r_one) else "비교 가능 연도 5개 미만")),
                                       font=dict(size=17, color=C_TEXT), x=0),
                            margin=dict(l=10, r=10, t=70, b=10))
        fig_s.update_xaxes(title_text="연 리스크 (t, 0~1)", gridcolor="#1f2b44", tickfont=dict(size=14))
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
        for vals, name, col in [(pooled, "16개국 전체", C_RISK), (med, "국가별 중앙값", C_COOP), (mine, names[country], C_ARMS)]:
            fig_b.add_trace(go.Bar(x=ks, y=vals, name=name, marker_color=col,
                                   text=[f"{v:+.2f}" if pd.notna(v) else "-" for v in vals], textposition="outside", cliponaxis=False,
                                   hovertemplate=name + " · %{x} · r = %{y:+.3f}<extra></extra>"))
        lo = min([-0.35] + [v - 0.1 for v in pooled + med + mine if pd.notna(v)])
        hi = max([0.35] + [v + 0.1 for v in pooled + med + mine if pd.notna(v)])
        fig_b.update_layout(**DARK_LAYOUT, height=400, barmode="group",
                            title=dict(text=ctitle("시차별 상관계수 (피어슨 r)", f"{years[0]}–{years[1]} · 16개국 전체 · 국가별 중앙값 · {names[country]}"), font=dict(size=17, color=C_TEXT), x=0),
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
        st.info(f"**시차 {lag}년 · {years[0]}–{years[1]}년** · {lag}년 후 주문 기준 비교 가능 연도 5개 미만으로 "
                "상관계수 미산출 · 분석 기간 확대 또는 시차 축소 필요")
    else:
        st.info(f"**시차 {lag}년 · 16개국 전체 r = {pr0:+.3f} · 국가별 중앙값 {per0.median():+.3f} · 양(+)의 상관 국가 {n_pos}/{len(per0)}** — "
                f"{'뚜렷한 선형 상관관계 미확인 · 모든 형태의 관계가 없음을 의미하지는 않음' if abs(pr0) < 0.3 else '선형 상관관계 확인 · 인과관계 또는 통계적 유의성과는 구별'} "
                f"주문·인도 시점 차이와 국방 예산·정책·공급 여건 등 추가 요인 고려")

    if extras:
        st.markdown(f'<div class="pill-t">{names[country]} · 상관관계의 산출 방식별 비교 '
                    + info_icon("피어슨·최대 주문 제외·변화량·스피어만 상관계수의 방향·크기 비교 · "
                                "최대 주문 제외 시 계수 감소: 대규모 계약 영향 가능 · 변화량 기준 계수 감소: 장기 추세 영향 가능 · "
                                "비교 가능 연도 5개 미만은 미산출") + "</div>", unsafe_allow_html=True)
        lt = relations.lag_table(gy["risk"], gy["tiv"])
        st.dataframe(lt.style.format({c: "{:+.2f}" for c in ["Pearson", "최대 주문 제외", "변화량", "Spearman"]}, na_rep="-"),
                     hide_index=True, width="stretch")
    info("**16개국 전체** = 국가 내 리스크·log 수입을 평균·표준편차로 표준화한 후 전체 관측값으로 산출한 피어슨 상관계수 · "
          "국가 간 규모 차이 조정\n\n"
          "**국가별 중앙값** = 국가별 피어슨 상관계수의 중앙값 · 일부 국가의 전체 집계 영향 검토\n\n"
          "**표본** = 선택 기간 내 리스크(t)·수입(t+k)이 모두 확보된 연도 · 비교 가능 연도 5개 미만 국가는 제외")
