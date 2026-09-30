"""② 리스크 분석 페이지 (원본 app2.py 의 5.). page() = 국가쌍 · 국가별 보기, 필터는 사이드바."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import ctitle, tip, info_icon, page_sub, term
from core import theme
from core.sidebar import page_filters, filter_note
from core.ui import C_RISK, C_MUTE, C_TEXT, LINE_COLORS, CHART_CONFIG, DARK_LAYOUT, section_head, info, tabbar
from sources import relations


def grade_pills(items, dist, title="", hi=None, layer="이 층", title_tip="", month="", period=""):
    """등급 카드 (가로형): 왼쪽 = 이름 · 평균 · 상위 %, 오른쪽 = 등급 배지 · 큰 값. 설명은 모두 마우스 말풍선.
    items = [(코드, 이름, 마지막 달 값, 기간 평균)], dist = 그 층의 값 분포, layer = 층 이름,
    month = 마지막 달('2026-09'), period = 기간 글자."""
    h = [f'<div class="pill-t">{title} {info_icon(title_tip)}</div>'] if title else []
    h.append('<div class="pills">')
    for code, name, v, avg in items:
        g = relations.grade(v)
        pc = relations.pct_rank(v, dist)
        col = relations.GRADE_COLORS[g] if g is not None else C_MUTE
        txt = relations.GRADES[g] if g is not None else "자료 없음"
        val = "—" if v is None or pd.isna(v) else f"{v:.3f}"
        sub = [tip(f"평균 {avg:.3f}", f"{period} 기간의 월별 리스크 평균")] if avg is not None and not pd.isna(avg) else []
        if pc is not None:
            top = max(100 - pc, 0.1)
            sub.append(tip(f"상위 {top:.0f}%", f"{layer} 1980년 이후 모든 달 가운데 상위 {top:.0f}% — "
                                                f"이 값보다 높았던 달이 {top:.0f}% 뿐이라는 뜻"))
        g_tip = (f"{txt} 등급 ({relations.GRADE_DESC[g]}) — 보도된 사건 무게 가운데 갈등의 비중으로 매긴 5단계, 모든 층 같은 잣대"
                 if g is not None else "자료가 없는 달")
        v_tip = f"{month} 한 달의 리스크 (그 달 하루하루 값의 평균, 0~1). 1에 가까울수록 갈등 보도 비중이 큼"
        h.append(f'<div class="pill{" hi" if code == hi else ""}">'
                 f'<div class="pl"><div class="pill-n">{name}</div><div class="pill-s">{" · ".join(sub)}</div></div>'
                 f'<div class="pr">{tip(txt, g_tip, "pill-g r", f"background:{col}")}{tip(val, v_tip, "pill-v r")}</div></div>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)


def grade_legend():
    """등급 색 5칸. 등급 뜻은 카드의 등급 배지에 마우스를 올리면 보인다."""
    h = ['<div class="glegend">']
    for g, c, d in zip(relations.GRADES, relations.GRADE_COLORS, relations.GRADE_DESC):
        h.append(f'<span><i style="background:{c}"></i>{g}<em>{d}</em></span>')
    h.append('</div>')
    st.markdown("".join(h), unsafe_allow_html=True)


HOW = "12개월 이동평균"          # 선은 12개월 이동평균으로 고정 (월별 원값·연평균 옵션은 뺐다)


def _line_colors(items, focus):
    """나라마다 다른 선 색. 강조한 나라가 첫 색(로즈)을 쓰고, 나머지는 뒤 색을 차례로 돌려 쓴다."""
    rest = LINE_COLORS[1:]
    out, i = {}, 0
    for it in items:
        if it == focus:
            out[it] = LINE_COLORS[0]
        else:
            out[it] = rest[i % len(rest)]
            i += 1
    return out


def _month_range(col, label, months, value, key):
    """월 단위 기간 슬라이더. months = 고를 수 있는 달(1일) 목록, value = ('YYYY-MM', 'YYYY-MM'). 돌려주는 값 = (시작일, 끝일)."""
    opts = [d.strftime("%Y-%m") for d in months]
    lo, hi = value
    lo = lo if lo in opts else opts[0]
    hi = hi if hi in opts else opts[-1]
    v = col.select_slider(label, options=opts, value=(lo, hi), key=key)
    return pd.Timestamp(v[0] + "-01"), pd.Timestamp(v[1] + "-01")


def _in_period(obj, p0, p1):
    """날짜 색인을 가진 Series·DataFrame 을 [p0, p1] 달로 자른다."""
    return obj[(obj.index >= p0) & (obj.index <= p1)]


def _pstr(p0, p1):
    return f"{p0:%Y-%m}–{p1:%Y-%m}"


def _time_axes(fig, p0, p1):
    """시간 축 · 0~1 리스크 축을 같은 모양으로."""
    years = p1.year - p0.year
    step = 1 if years <= 12 else 2 if years <= 25 else 5
    fig.update_xaxes(gridcolor="#1f2b44", tickformat="%Y", dtick=f"M{12 * step}", ticklabelmode="period",
                     hoverformat="%Y-%m", minor=dict(dtick="M12", ticklen=3, showgrid=False), tickfont=dict(size=14))
    fig.update_yaxes(gridcolor="#1f2b44", zerolinecolor="#1f2b44", range=[0, 1], tickfont=dict(size=14))


def _gap_bands(fig, gaps, p0, p1):
    """GDELT 원본이 절반 넘게 빠진 달을 회색 띠로."""
    for d in gaps:
        if p0 <= d <= p1:
            fig.add_vrect(x0=d, x1=d + pd.offsets.MonthBegin(1), fillcolor="#64748b", opacity=0.25, line_width=0)


def _pair_filters(risk, names, months):
    """국가쌍 탭 필터: [행위 주체][상대국][강조할 상대국][기간(월)]. 값은 session_state['rel_f']에 보관."""
    f = st.session_state.setdefault("rel_f", {"country": "ISR", "partners": None, "partners_for": None, "focus": None})
    f.setdefault("period", (months[0].strftime("%Y-%m"), months[-1].strftime("%Y-%m")))
    box = page_filters("국가쌍 리스크")                       # v2: 본문 맨 위 접이식
    r1, r2 = box.columns(2, gap="medium"), box.columns(2, gap="medium")   # 한 줄씩이면 상자가 너무 길어진다 → 2 x 2
    (c1, c2), (c3, c4) = r1, r2
    f["country"] = c1.selectbox("행위 주체", list(names), index=list(names).index(f["country"]),
                                format_func=names.get, key="rel_country")
    country = f["country"]
    series = relations.pair_series(risk, country, "out")
    # 상대국 목록과 기본 선택은 기간과 무관하게 전 구간 평균 순 (기간을 바꿔도 선택이 안 바뀌게)
    rank_all = series.mean().sort_values(ascending=False)
    kept = [q for q in (f["partners"] or []) if q in rank_all.index] if f["partners_for"] == country else []
    # 선이 5개를 넘으면 회색끼리 뒤엉켜 강조한 선을 못 따라간다 → 최대 5곳 (2026-09-30)
    f["partners"] = c2.multiselect("상대국", list(rank_all.index), default=(kept or list(rank_all.index[:5]))[:5],
                                   format_func=names.get, key=f"rel_partners_{country}", max_selections=5)
    f["partners_for"] = country
    opts = f["partners"] or list(rank_all.index)
    # 강조: 고른 상대국만 진하게, 나머지는 회색 (선이 색으로 뒤엉키지 않게)
    f["focus"] = c3.selectbox("강조할 상대국", opts, index=opts.index(f["focus"]) if f["focus"] in opts else 0,
                              format_func=names.get, key=f"rel_focus_{country}") if f["partners"] else None
    p0, p1 = _month_range(c4, "기간 (월)", months, f["period"], key="rel_period")
    f["period"] = (f"{p0:%Y-%m}", f"{p1:%Y-%m}")
    filter_note(f"{names[country]} → 상대국 {len(f['partners'] or [])}곳 · {p0:%Y-%m}–{p1:%Y-%m}")
    return country, f["partners"], f["focus"], series, p0, p1


def _country_filters(cmat_full, names, months):
    """국가별 탭 필터: [나라][강조할 나라][기간(월)]. 값은 session_state['cty_f']에 보관."""
    rank = cmat_full.mean().sort_values(ascending=False)
    f = st.session_state.setdefault("cty_f", {"countries": list(rank.index[:5]), "focus": None})
    f.setdefault("period", (months[0].strftime("%Y-%m"), months[-1].strftime("%Y-%m")))
    box = page_filters("국가별 리스크")                   # v2: 본문 맨 위 접이식
    c1, c2 = box.columns(2, gap="medium")                 # 나라 · 강조는 한 줄에 둘, 기간만 아래 한 줄
    c3 = box.container()
    f["countries"] = c1.multiselect("나라", list(rank.index), default=[c for c in f["countries"] if c in rank.index][:5],
                                    format_func=names.get, key="cty_countries", max_selections=5)
    opts = f["countries"] or list(rank.index)
    f["focus"] = c2.selectbox("강조할 나라", opts, index=opts.index(f["focus"]) if f["focus"] in opts else 0,
                              format_func=names.get, key="cty_focus") if f["countries"] else None
    p0, p1 = _month_range(c3, "기간 (월)", months, f["period"], key="cty_period")
    f["period"] = (f"{p0:%Y-%m}", f"{p1:%Y-%m}")
    filter_note(f"나라 {len(f['countries'] or [])}곳 · {p0:%Y-%m}–{p1:%Y-%m}")
    return f["countries"], f["focus"], p0, p1


def page():
    risk = relations.load_risk()
    names = relations.COUNTRIES
    months = pd.date_range(risk["date"].min(), risk["date"].max(), freq="MS")
    gaps = relations.gap_months(risk)
    dists = relations.load_dists()
    region = relations.load_region()
    how = HOW

    st.title('리스크 분석')
    page_sub("1980년부터 " + term("국가쌍") + " · " + term("국가별") + " 월별 " + term("리스크") + "를 " + term("12개월 이동평균") + "으로 보여 줍니다. 선이 높을수록 그 시기 갈등 쪽 보도가 많았다는 뜻입니다.")
    # v2: 탭 대신 보기 버튼. 고른 보기만 그려서 사이드바 필터도 그 보기 것만 나온다
    view = tabbar("보기", ["국가쌍 리스크", "국가별 리스크"], key="rel_view")

    # ---------------------------------------------------------------- 탭 1: 국가쌍 리스크
    # 그래프 위를 가볍게 (2026-09-29 팀 의견): 소제목 · 한 줄 설명 → 필터 → 토글 → 그래프(제목 두 줄) → 요약 한 줄
    if view == "국가쌍 리스크":
        section_head("01", "국가쌍 리스크", "행위주체국이 주어로 기록된 사건을 바탕으로 계산한 상대국과의 월간 리스크(0~1).")
        country, partners, focus, series, p0, p1 = _pair_filters(risk, names, months)
        if not partners:
            st.info("왼쪽 필터에서 상대국을 한 곳 이상 골라 주세요.")
        else:
            in_range = _in_period(series, p0, p1)
            ranking = in_range.mean().sort_values(ascending=False)
            top = ranking.index[0]
            peak = in_range[top].idxmax()
            # v2: [그래프 | 등급 카드] 2단 · 핵심 요약(결론)은 그래프 바로 아래에 (2026-09-30)
            left, right = st.columns([2.3, 1], gap="medium")
            with left:
                show_region = st.toggle("중동 전체 기준선", value=True, key="pair_region")
                fig = go.Figure()
                if show_region:
                    rs = _in_period(relations.smooth(region, how), p0, p1)   # 전체로 먼저 이동평균, 그다음 자르기
                    fig.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name="중동 전체",
                                             line=dict(color="#94a3b8", width=1.6, dash="dot"),
                                             hovertemplate="중동 전체 %{y:.3f}<extra></extra>"))
                pcol = _line_colors(partners, focus)                           # 강조는 첫 색, 나머지는 돌려 쓴다
                for q in sorted(partners, key=lambda x: x == focus):           # 강조 선을 맨 위에
                    sm = _in_period(relations.smooth(series[q], how), p0, p1)
                    fig.add_trace(go.Scatter(
                        x=sm.index, y=sm.values, mode="lines", name=names[q],
                        line=dict(color=pcol[q], width=3.4 if q == focus else 1.4),
                        opacity=1 if q == focus else 0.45,
                        hovertemplate=f"{names[country]} → {names[q]} %{{y:.3f}}<extra></extra>"))
                _gap_bands(fig, gaps, p0, p1)
                fig.update_layout(**DARK_LAYOUT, height=440, hovermode="x unified",
                                  # 제목 두 줄: 무엇을 보나 / 어떻게 읽나 (예전 소제목의 '빨간 선 · 점선' 설명이 여기로)
                                  title=dict(text=ctitle(f"{names[country]} ➜ 상대국 리스크 (0~1)",
                                                    f"{names[focus]} 강조" + (" / 점선 = 중동 전체" if show_region else "")
                                                    + f" · {_pstr(p0, p1)} · 12개월 이동평균"),
                                             font=dict(size=17, color=C_TEXT), x=0, y=0.95, yanchor="top"),   # 맨 위에 붙여 범례와 안 겹치게
                                  margin=dict(l=10, r=10, t=90, b=10),
                                  legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=14)))
                _time_axes(fig, p0, p1)
                st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG)
                st.markdown(f'<div class="summary"><b>{names[country]}</b> → 상대국 리스크는 <b>{names[top]}</b>{relations.jo(names[top])} 가장 높습니다 '
                            f'(기간 평균 {ranking.iloc[0]:.2f}, 최고 {peak:%Y년 %m월}) · {_pstr(p0, p1)}</div>', unsafe_allow_html=True)

            with right:
                last_m = in_range.index.max()
                # 카드마다 같은 내용(마지막 달 · 기간 · 순위 기준)은 소제목에 한 번만, 카드에는 평균 · 상위 %만
                grade_pills([(q, names[q], in_range[q].iloc[-1], in_range[q].mean()) for q in partners],
                            dists["pair"], f"{names[country]} → 상대국 · {last_m:%Y-%m} 기준", hi=focus, layer="국가쌍",
                            title_tip=f"마지막 달 {last_m:%Y-%m}의 상태 · 평균 = {_pstr(p0, p1)} 평균 · "
                                      "상위 % = 국가쌍 1980년 이후 모든 달 중 순위 · 빨간 테두리 = 강조한 상대국",
                            month=f"{last_m:%Y-%m}", period=_pstr(p0, p1))
                grade_legend()
            # (v2, 2026-09-30) 국가쌍 아래 '계산 기준' 팝오버 · 평균/최고 리스크 표는 뺐다
            #  — 평균 · 최신 값은 등급 카드와 그래프에, 계산식은 데이터 소개에 있다

    # ---------------------------------------------------------------- 탭 2: 국가별 리스크
    if view == "국가별 리스크":
        ccol = "all_risk"          # 국가별은 그 나라가 낀 모든 관계를 합친 종합 값
        cmat_full = relations.load_country().pivot(index="date", columns="country", values=ccol)
        # 국가쌍 탭과 같은 순서: 소제목 · 한 줄 설명 → 필터 → 토글 → 그래프(제목 두 줄)
        section_head("02", "국가별 종합 리스크", "국가쌍이 아니라 나라 하나가 낀 모든 관계를 합쳐 계산한 월간 리스크(0~1).")
        clist, cfocus, q0, q1 = _country_filters(cmat_full, names, months)
        if not clist:
            st.info("왼쪽 필터에서 나라를 한 곳 이상 골라 주세요.")
        else:
            cmat = _in_period(cmat_full, q0, q1)
            reg = _in_period(region, q0, q1)
            # v2: 국가쌍 탭과 같은 모양 — [그래프 | 등급 카드] 2단
            #     기간 평균 막대는 선 그래프 아래로 내려 왼쪽 단에 함께 둔다
            left, right = st.columns([2.3, 1], gap="medium")
            with left:
                c_region = st.toggle("중동 전체 기준선", value=True, key="country_region")
                fig_c = go.Figure()
                if c_region:
                    rs = _in_period(relations.smooth(region, how), q0, q1)
                    fig_c.add_trace(go.Scatter(x=rs.index, y=rs.values, mode="lines", name="중동 전체",
                                               line=dict(color="#94a3b8", width=1.6, dash="dot"),
                                               hovertemplate="중동 전체 %{y:.3f}<extra></extra>"))
                ccol_map = _line_colors(clist, cfocus)                          # 강조는 첫 색, 나머지는 돌려 쓴다
                for c in sorted(clist, key=lambda x: x == cfocus):             # 강조 나라를 맨 위에
                    sm = _in_period(relations.smooth(cmat_full[c], how), q0, q1)
                    fig_c.add_trace(go.Scatter(x=sm.index, y=sm.values, mode="lines", name=names[c],
                                               line=dict(color=ccol_map[c], width=3.4 if c == cfocus else 1.4),
                                               opacity=1 if c == cfocus else 0.45,
                                               hovertemplate=f"{names[c]} %{{y:.3f}}<extra></extra>"))
                _gap_bands(fig_c, gaps, q0, q1)
                fig_c.update_layout(**DARK_LAYOUT, height=440, hovermode="x unified",
                                    title=dict(text=ctitle("국가별 종합 리스크 (0~1)",
                                                      f"{names[cfocus]} 강조" + (" / 점선 = 중동 전체" if c_region else "")
                                                      + f" · {_pstr(q0, q1)} · 12개월 이동평균"), font=dict(size=17, color=C_TEXT),
                                               x=0, y=0.95, yanchor="top"),
                                    margin=dict(l=10, r=10, t=90, b=10),
                                    legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=14)))
                _time_axes(fig_c, q0, q1)
                st.plotly_chart(theme.adapt(fig_c), width="stretch", config=CHART_CONFIG)

            with right:
                last_c = cmat.index.max()
                grade_pills([(c, names[c], cmat[c].iloc[-1], cmat[c].mean()) for c in clist],
                            dists[ccol], f"국가별 리스크 · {last_c:%Y-%m} 기준", hi=cfocus, layer="국가별",
                            title_tip=f"마지막 달 {last_c:%Y-%m}의 상태 · 평균 = {_pstr(q0, q1)} 평균 · "
                                      "상위 % = 같은 층(국가별·중동 전체) 1980년 이후 모든 달 중 순위 · 빨간 테두리 = 강조한 나라",
                            month=f"{last_c:%Y-%m}", period=_pstr(q0, q1))
                grade_pills([("__region__", "중동 전체", reg.iloc[-1], reg.mean())], dists["region"], layer="중동 전체",
                            month=f"{last_c:%Y-%m}", period=_pstr(q0, q1))
                grade_legend()

            info("**국가별 종합 리스크** = 위 식의 하루 갈등·협력 합을 그 나라가 낀 15개 국가쌍 전체(주어·목적어 모두)로 "
                  "먼저 더한 뒤 나눈 값의 월평균 (국가쌍 리스크의 평균이 아님).\n\n"
                  "**중동 전체**(점선) = 16개국 사이 모든 사건으로 낸 값. 비교 기준선으로 씁니다.\n\n"
                  "**등급** = 0.2 간격 (매우 낮음 < 0.2 ≤ 낮음 < 0.4 ≤ 보통 < 0.6 ≤ 높음 < 0.8 ≤ 매우 높음). "
                  "'상위 N%'는 그 층(국가별·국가쌍·전체)이 1980년부터 기록한 모든 달 가운데 순위.", formula=True)
