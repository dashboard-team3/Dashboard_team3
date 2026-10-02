"""② 리스크 분석 페이지 (원본 app2.py 의 5.). page() = 국가쌍 · 국가별 보기, 필터는 사이드바."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.ui import ctitle, tip, info_icon, page_sub, term
from core import theme
from core.sidebar import page_filters, filter_note
from core.ui import C_RISK, C_MUTE, C_TEXT, LINE_COLORS, CHART_CONFIG, DARK_LAYOUT, section_head, info, tabbar
from sources import relations


def grade_pills(items, dist, title="", hi=None, layer="해당 집계 단위", title_tip="", month="", period="", title_sub=""):
    """등급 카드 (가로형): 왼쪽 = 이름 · 평균 · 이 달 상위 %, 오른쪽 = 등급 배지 · 큰 값.
    items = [(코드, 이름, 마지막 달 값, 기간 평균[, 12개월 이동평균])], dist = 그 층의 값 분포,
    layer = 층 이름, month = 마지막 달('2026-09'), period = 기간 글자, title_sub = 제목 아래 작은 줄('2026-09 기준').

    큰 숫자는 그 달 하나의 값이라 그래프 선(12개월 이동평균)의 끝점과 다르다. 한 줄이 길어져 화면에는
    안 쓰고, 큰 숫자에 마우스를 올리면 그 선 끝점 값을 함께 보여 준다 (ma). (2026-10-01)
    «상위 %» 는 평균이 아니라 «큰 숫자(그 달 값)» 의 순위다 — 평균이 같아도 그 달 값이 다르면 달라진다.
    제목은 늘 두 줄(제목 / 작은 줄)이라 나라 이름 길이와 화면 폭에 따라 줄 수가 바뀌지 않는다 → 옆 그래프와 높이를 맞출 수 있다 (2026-10-01)"""
    tsub = f'<span class="pill-ts">{title_sub}</span>' if title_sub else ""
    h = [f'<div class="pill-t">{title} {info_icon(title_tip)}{tsub}</div>'] if title else []
    h.append('<div class="pills">')
    for it in items:
        code, name, v, avg = it[:4]
        ma = it[4] if len(it) > 4 else None
        g = relations.grade(v)
        pc = relations.pct_rank(v, dist)
        col = relations.GRADE_COLORS[g] if g is not None else C_MUTE
        txt = relations.GRADES[g] if g is not None else "자료 없음"
        val = "—" if v is None or pd.isna(v) else f"{v:.3f}"
        sub = [tip(f"평균 {avg:.3f}", f"{period} 기간의 월별 리스크 평균")] if avg is not None and not pd.isna(avg) else []
        if pc is not None:
            top = max(100 - pc, 0.1)
            sub.append(tip(f"해당 월 상위 {top:.0f}%", f"표시값({val})를 {layer} 1980년 이후 전체 대상·전체 월의 관측값과 "
                                                f"비교한 순위 · 해당 값보다 높은 관측값의 비중 {top:.0f}% · "
                                                f"{month} 월별 값 기준 · 기간 평균 순위와 구별"))
        g_tip = (f"{txt} 등급 ({relations.GRADE_DESC[g]}) · 보도된 사건의 가중 합 대비 갈등 비중 기준 5단계 · 집계 단위별 동일 기준 적용"
                 if g is not None else "자료 미확보 월")
        v_tip = f"{month} 월별 리스크(일별 값의 평균, 0~1) · 값이 높을수록 갈등 보도 비중 증가"
        if ma is not None and not pd.isna(ma):   # 한 줄이 길어져 화면에서는 빼고 말풍선에만 둔다 (2026-10-01)
            v_tip += f" · 그래프의 마지막 값(12개월 이동평균): {ma:.3f} · 카드의 월별 값과 구별"
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


CARD_N = 5                        # 등급 카드는 5장 고정 (상대국 · 나라는 몇 곳이든 고를 수 있음)


def _card_items(items, avg, focus):
    """카드에 올릴 5곳: 고른 것 가운데 기간 평균 높은 순 5곳. 강조한 곳은 5위 밖이어도 마지막 자리에 넣는다."""
    top = sorted(items, key=lambda x: -avg[x])[:CARD_N]
    if focus in items and focus not in top:
        top = top[:CARD_N - 1] + [focus]
    return top


def _chart_head(key, tip_text):
    """그래프 위 한 줄: 왼쪽 '리스크 추이 ⓘ' · 오른쪽 '중동 전체 기준선' 토글 (2026-10-01). 토글 값을 돌려준다."""
    h1, h2 = st.columns([1, 1], vertical_alignment="center")
    h1.markdown(f'<div class="chart-h">리스크 추이 {info_icon(tip_text)}</div>', unsafe_allow_html=True)
    with h2:
        return st.toggle("중동 전체 기준선", value=True, key=key)


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
    fig.update_yaxes(gridcolor="#1f2b44", zerolinecolor="#1f2b44", range=[0, 1], tickfont=dict(size=14),
                     title_text="리스크 (0~1)", title_font=dict(size=13))                         # 단위 (2026-10-02)


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
    # 기본은 평균 상위 5곳, 선택 수 제한은 없음 (등급 카드만 5장 고정 — _card_items)
    f["partners"] = c2.multiselect("상대국", list(rank_all.index), default=kept or list(rank_all.index[:5]),
                                   format_func=names.get, key=f"rel_partners_{country}")
    f["partners_for"] = country
    opts = f["partners"] or list(rank_all.index)
    # 강조: 고른 상대국만 진하게, 나머지는 회색 (선이 색으로 뒤엉키지 않게)
    f["focus"] = c3.selectbox("강조 대상 상대국", opts, index=opts.index(f["focus"]) if f["focus"] in opts else 0,
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
    f["countries"] = c1.multiselect("국가", list(rank.index), default=[c for c in f["countries"] if c in rank.index],
                                    format_func=names.get, key="cty_countries")   # 선택 수 제한 없음 (카드만 5장)
    opts = f["countries"] or list(rank.index)
    f["focus"] = c2.selectbox("강조 대상 국가", opts, index=opts.index(f["focus"]) if f["focus"] in opts else 0,
                              format_func=names.get, key="cty_focus") if f["countries"] else None
    p0, p1 = _month_range(c3, "기간 (월)", months, f["period"], key="cty_period")
    f["period"] = (f"{p0:%Y-%m}", f"{p1:%Y-%m}")
    filter_note(f"국가 {len(f['countries'] or [])}곳 · {p0:%Y-%m}–{p1:%Y-%m}")
    return f["countries"], f["focus"], p0, p1


def page(show_title=True):
    risk = relations.load_risk()
    names = relations.COUNTRIES
    months = pd.date_range(risk["date"].min(), risk["date"].max(), freq="MS")
    gaps = relations.gap_months(risk)
    dists = relations.load_dists()
    region = relations.load_region()
    how = HOW

    if show_title:
        st.title('리스크 추이')
        page_sub("뉴스 기반 갈등 지표를 통해 중동 " + term("국가쌍별") + " · " + term("국가별") + " " +term("리스크") + "의 장기 추세·시기별 변화 비교")
    # page_sub("1980년부터 " + term("국가쌍") + " · " + term("국가별") + " 월별 " + term("리스크") + "를 " + term("12개월 이동평균") + "으로 보여 줍니다. 선이 높을수록 그 시기 갈등 쪽 보도가 많았다는 뜻입니다.")
    # v2: 탭 대신 보기 버튼. 고른 보기만 그려서 사이드바 필터도 그 보기 것만 나온다
    view = tabbar("보기", ["국가쌍 리스크", "국가별 리스크"], key="rel_view")

    # ---------------------------------------------------------------- 탭 1: 국가쌍 리스크
    # 그래프 위를 가볍게 (2026-09-29 팀 의견): 소제목 · 한 줄 설명 → 필터 → 토글 → 그래프(제목 두 줄) → 요약 한 줄
    if view == "국가쌍 리스크":
        section_head("01", "국가쌍 리스크", "행위 주체국→상대국 방향으로 기록된 사건의 월별 리스크(0~1)")
        country, partners, focus, series, p0, p1 = _pair_filters(risk, names, months)
        if not partners:
            st.info("필터에서 상대국 1개국 이상 선택 필요")
        else:
            in_range = _in_period(series, p0, p1)
            ranking = in_range.mean().sort_values(ascending=False)
            top = ranking.index[0]
            peak = in_range[top].idxmax()
            # v2: [그래프 | 등급 카드] 2단 · 핵심 요약(결론)은 그래프 바로 아래에 (2026-09-30)
            left, right = st.columns([2, 1], gap="medium")   # (2026-10-01) 2.3:1 → 2:1, 카드 상자 안 글자가 안 잘리게
            with left:
                show_region = _chart_head("pair_region", "선 = 국가쌍 월별 리스크의 12개월 이동평균 (0~1). 굵은 선 = 선택 상대국 · "
                                                         "점선 = 중동 전체 기준선 · 범례 선택 시 해당 선 표시·숨김 전환")
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
                # 오른쪽 카드 묶음(상대국 최대 5장)과 아래 끝을 맞추도록 카드 수에 따라 높이를 정한다 (2026-10-01)
                n_cards = min(len(partners), CARD_N)
                fig.update_layout(**DARK_LAYOUT, height=max(440, 103 * n_cards + 79), hovermode="x unified",
                                  # 제목 두 줄: 무엇을 보나 / 어떻게 읽나 (예전 소제목의 '빨간 선 · 점선' 설명이 여기로)
                                  title=dict(text=ctitle(f"{names[country]} ➜ 상대국 리스크 (0~1)",
                                                    f"{names[focus]} 강조" + (" / 점선 = 중동 전체" if show_region else "")
                                                    + f" · {_pstr(p0, p1)} · 12개월 이동평균"),
                                             font=dict(size=17, color=C_TEXT), x=0, y=0.95, yanchor="top"),   # 맨 위에 붙여 범례와 안 겹치게
                                  margin=dict(l=10, r=10, t=90, b=10),
                                  legend=dict(orientation="h", y=-0.1, yanchor="top", x=0, font=dict(size=14)))   # 범례는 x축 아래 (좁은 화면에서 두 줄이 돼도 제목과 안 겹치게, 2026-10-01)
                _time_axes(fig, p0, p1)
                st.plotly_chart(theme.adapt(fig), width="stretch", config=CHART_CONFIG)
                st.markdown(f'<div class="summary"><b>{names[country]}</b> → 상대국 중 <b>{names[top]}</b>{relations.jo(names[top])} 기간 평균 리스크 최고 기록 '
                            f'(기간 평균 {ranking.iloc[0]:.2f}, 최고 {peak:%Y년 %m월}) · {_pstr(p0, p1)}</div>', unsafe_allow_html=True)

            with right:
                last_m = in_range.index.max()
                # 카드마다 같은 내용(마지막 달 · 기간 · 순위 기준)은 소제목에 한 번만, 카드에는 평균 · 상위 %만
                # 그래프와 같은 식으로 다듬은 선의 마지막 점 (카드 큰 숫자는 그 달 값이라 둘을 함께 보여 준다)
                ma_pair = {q: _in_period(relations.smooth(series[q], how), p0, p1).iloc[-1] for q in partners}
                with st.container(key="pair_cards"):          # 제목 ~ 카드를 한 상자로 (그래프 카드와 위아래 끝을 맞춤)
                    grade_pills([(q, names[q], in_range[q].iloc[-1], in_range[q].mean(), ma_pair[q])
                                 for q in _card_items(partners, in_range.mean(), focus)],
                                dists["pair"], f"{names[country]} → 상대국", hi=focus, layer="국가쌍", title_sub=f"{last_m:%Y-%m} 기준",
                                title_tip=f"표시값 = {last_m:%Y-%m} 한 달의 리스크 · 평균 = {_pstr(p0, p1)} 월별 평균 · "
                                          "표시값에 마우스를 올리면 12개월 이동평균의 마지막 값 표시 · "
                                          f"해당 월 상위 % = 국가쌍의 1980년 이후 전체 월별 관측값 대비 표시값의 순위 "
                                          "(평균의 순위가 아님) · 빨간 테두리 = 선택 상대국 · "
                                          "카드: 선택 상대국 중 기간 평균 상위 5개국",
                                month=f"{last_m:%Y-%m}", period=_pstr(p0, p1))
                grade_legend()
            # (v2, 2026-09-30) 국가쌍 아래 '계산 기준' 팝오버 · 평균/최고 리스크 표는 뺐다
            #  — 평균 · 최신 값은 등급 카드와 그래프에, 계산식은 데이터 소개에 있다

    # ---------------------------------------------------------------- 탭 2: 국가별 리스크
    if view == "국가별 리스크":
        ccol = "all_risk"          # 국가별은 그 나라가 낀 모든 관계를 합친 종합 값
        cmat_full = relations.load_country().pivot(index="date", columns="country", values=ccol)
        # 국가쌍 탭과 같은 순서: 소제목 · 한 줄 설명 → 필터 → 토글 → 그래프(제목 두 줄)
        section_head("02", "국가별 종합 리스크", "해당 국가가 관여한 모든 관계의 갈등·협력 가중 합을 통합하여 산출한 월별 리스크(0~1)")
        clist, cfocus, q0, q1 = _country_filters(cmat_full, names, months)
        if not clist:
            st.info("필터에서 국가 1개국 이상 선택 필요")
        else:
            cmat = _in_period(cmat_full, q0, q1)
            # v2: 국가쌍 탭과 같은 모양 — [그래프 | 등급 카드] 2단
            #     기간 평균 막대는 선 그래프 아래로 내려 왼쪽 단에 함께 둔다
            left, right = st.columns([2, 1], gap="medium")   # (2026-10-01) 2.3:1 → 2:1, 카드 상자 안 글자가 안 잘리게
            with left:
                c_region = _chart_head("country_region", "선 = 국가별 종합 리스크의 12개월 이동평균 (0~1). 굵은 선 = 선택 국가 · "
                                                         "점선 = 중동 전체 기준선 · 범례 선택 시 해당 선 표시·숨김 전환")
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
                # 오른쪽 카드 묶음(나라 최대 5장)과 아래 끝을 맞추도록 카드 수에 따라 높이를 정한다 (2026-10-01)
                n_cards = min(len(clist), CARD_N)
                fig_c.update_layout(**DARK_LAYOUT, height=max(440, 103 * n_cards + 79), hovermode="x unified",
                                    title=dict(text=ctitle("국가별 종합 리스크 (0~1)",
                                                      f"{names[cfocus]} 강조" + (" / 점선 = 중동 전체" if c_region else "")
                                                      + f" · {_pstr(q0, q1)} · 12개월 이동평균"), font=dict(size=17, color=C_TEXT),
                                               x=0, y=0.95, yanchor="top"),
                                    margin=dict(l=10, r=10, t=90, b=10),
                                    legend=dict(orientation="h", y=-0.1, yanchor="top", x=0, font=dict(size=14)))   # 범례는 x축 아래 (좁은 화면에서 두 줄이 돼도 제목과 안 겹치게, 2026-10-01)
                _time_axes(fig_c, q0, q1)
                st.plotly_chart(theme.adapt(fig_c), width="stretch", config=CHART_CONFIG)

            with right:
                last_c = cmat.index.max()
                ma_cty = {c: _in_period(relations.smooth(cmat_full[c], how), q0, q1).iloc[-1] for c in clist}
                with st.container(key="cty_cards"):           # 제목 ~ 카드를 한 상자로 (그래프 카드와 위아래 끝을 맞춤)
                    grade_pills([(c, names[c], cmat[c].iloc[-1], cmat[c].mean(), ma_cty[c])
                                 for c in _card_items(clist, cmat.mean(), cfocus)],
                                dists[ccol], "국가별 리스크", hi=cfocus, layer="국가별", title_sub=f"{last_c:%Y-%m} 기준",
                                title_tip=f"표시값 = {last_c:%Y-%m} 한 달의 리스크 · 평균 = {_pstr(q0, q1)} 월별 평균 · "
                                          "표시값에 마우스를 올리면 12개월 이동평균의 마지막 값 표시 · "
                                          "해당 월 상위 % = 국가별 1980년 이후 전체 월별 관측값 대비 표시값의 순위 "
                                          "(평균의 순위가 아님) · 빨간 테두리 = 선택 국가 · "
                                          "카드: 선택 국가 중 기간 평균 상위 5개국",
                                month=f"{last_c:%Y-%m}", period=_pstr(q0, q1))
                # (2026-10-01) 오른쪽 '중동 전체' 카드는 뺐다 — 중동 전체는 그래프의 점선으로 본다
                grade_legend()

            info("**국가별 종합 리스크** = 해당 국가가 행위 주체·대상으로 관여한 15개 국가쌍의 일별 갈등·협력 가중 합을 "
                  "통합한 후 산출한 일별 리스크의 월평균 · 개별 국가쌍 리스크의 단순 평균과는 구별\n\n"
                  "**중동 전체**(점선) = 중동 16개국 간 전체 사건으로 산출한 리스크 · 비교 기준선으로 활용\n\n"
                  "**등급** = 0.2 간격의 5단계(매우 낮음 < 0.2 ≤ 낮음 < 0.4 ≤ 보통 < 0.6 ≤ 높음 < 0.8 ≤ 매우 높음) · "
                  "**해당 월 상위 N%** = 카드의 월별 표시값을 해당 집계 단위의 1980년 이후 "
                  "전체 월별 관측값과 비교한 순위(국가별 8,972개·국가쌍 109,472개 값) · "
                  "기간 평균과 별도 산출 · 월별 값 차이에 따라 상위 비중 차이 발생 · "
                  "동일 값은 가장 낮은 순위 기준 적용\n\n"
                  "**그래프·카드의 산출 기준** = 선: 12개월 이동평균 · 카드: 해당 월의 월별 리스크 · 카드 표시값에 마우스를 올리면 이동평균의 마지막 값 확인 가능",
                 formula=True)
