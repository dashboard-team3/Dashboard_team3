"""무기 거래 추이 페이지: Comtrade(교역액) 또는 SIPRI(주문 TIV)를 골라 지도·추이·순위·국가쌍으로 본다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sources import arms
from core.ui import page_sub, term
from core import theme
from core.sidebar import page_filters, filter_note
from core.ui import ctitle, info_icon, tabbar   # 밝은 테마일 때 그래프 색 바꾸기
from sources.relations import COUNTRIES, jo

GOLD = "#f5c542"
DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1", size=15),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3", size=15)),
    margin=dict(l=10, r=10, t=30, b=10),
)
GEO = dict(
    projection_type="natural earth", showframe=False, showcoastlines=False, showcountries=True,
    countrycolor="#24314f", landcolor="#16223f", oceancolor="#0b1220", showocean=True, showlakes=False,
    bgcolor="rgba(0,0,0,0)",
    lonaxis_range=[-135, 150], lataxis_range=[-42, 74],   # 공급국(미주~동아시아)과 중동이 들어가는 범위
)
# 중동 확대 범위: 이집트(서) ~ 이란(동), 예멘(남) ~ 튀르키예(북)가 다 들어가게
GEO_ME = dict(lonaxis_range=[22, 66], lataxis_range=[10, 44], projection_type="mercator")


def card(label, value, sub, tone=""):
    return (f'<div class="kpi live {tone}"><div><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div><div class="sub">{sub}</div></div></div>')


def strip(items, vertical=False):
    """카드 대신 한 줄 띠: [(label, value, sub, tone)] — 그래프가 위로 올라오도록 높이를 줄인 요약 (app2).
    vertical=True 면 세로로 쌓는다 (지도 옆 오른쪽 단, 리스크 분석의 등급 카드처럼 · 2026-10-01)."""
    cells = "".join(f'<div class="cell {tone}"><span class="l">{label}</span><span class="v">{value}</span>'
                    f'<span class="s">{sub}</span></div>' for label, value, sub, tone in items)
    return f'<div class="strip{" vstrip" if vertical else ""}">{cells}</div>'


def _axes(fig):
    """축은 조용하게: 세로 격자·축선 없이, 가로 격자만 옅게."""
    fig.update_xaxes(showgrid=False, showline=False, zeroline=False, ticks="outside", ticklen=4, tickcolor="#141d30")
    fig.update_yaxes(gridcolor="#141d30", showline=False, zeroline=False)


def _layout(fig, **kw):
    fig.update_layout(**{**DARK, **kw})


# ---------------------------------------------------------------- 지도

def draw_map(df, M, overlay, top_n, height=560):
    U = M["unit"]
    fig = go.Figure()
    fl = arms.flows(df)
    imp = df.groupby("target_iso3")["value"].sum()

    if overlay == "수입국별":
        fig.add_trace(go.Choropleth(
            locations=imp.index, z=imp.values, locationmode="ISO-3",
            colorscale=[[0, "#2a3a2e"], [1, GOLD]], marker_line_color="#0b1220", marker_line_width=0.5,
            colorbar=dict(title=U, thickness=10, len=0.5, tickfont=dict(color="#cbd5e1")),
            text=[COUNTRIES[c] for c in imp.index],
            hovertemplate=f"%{{text}}<br>%{{z:,.1f}} {U}<extra></extra>",
        ))
    else:
        shown = fl.head(top_n)
        top = shown["value"].max() if len(shown) else 1
        for r in shown.itertuples():
            a, b = arms.pos(r.exporter_iso3), arms.pos(r.target_iso3)
            if a is None or b is None:
                continue
            lats, lons = arms.great_circle(a[0], a[1], b[0], b[1])
            w = 1 + 7 * (r.value / top) ** 0.5
            # (2026-10-01) 호 가운데 동그라미는 뺐다 — 뜻이 안 보이고 지저분해서. 호 자체에 마우스를 올리면 상세가 뜬다
            txt = (f"<b>{r.exporter} → {r.target_name}</b><br>{r.value:,.1f} {U} · {M['obs_label']} {r.obs}"
                   f"<br>주요 {M['cat_label']} {r.top_cat}")
            fig.add_trace(go.Scattergeo(lat=lats, lon=lons, mode="lines", showlegend=False,
                                        line=dict(color=GOLD, width=w), opacity=0.55,
                                        text=[txt] * len(lats), hovertemplate="%{text}<extra></extra>"))
        sup = shown.groupby(["exporter_iso3", "exporter"])["value"].sum().reset_index()
        sup = sup[sup["exporter_iso3"].map(arms.pos).notna()]
        fig.add_trace(go.Scattergeo(
            lat=[arms.pos(c)[0] for c in sup["exporter_iso3"]], lon=[arms.pos(c)[1] for c in sup["exporter_iso3"]],
            mode="markers", showlegend=False, marker=dict(size=6, color=GOLD, line=dict(color="#0b1220", width=1)),
            text=[f"<b>{k}</b> ({M['role_label']})<br>{v:,.1f} {U}" for k, v in zip(sup["exporter"], sup["value"])],
            hovertemplate="%{text}<extra></extra>"))
    imp = imp.reindex([c for c in arms.TARGET_POS if c in imp.index])
    fig.add_trace(go.Scattergeo(
        lat=[arms.TARGET_POS[c][0] for c in imp.index], lon=[arms.TARGET_POS[c][1] for c in imp.index],
        mode="markers", showlegend=False,
        marker=dict(size=[6 + 14 * (v / imp.max()) ** 0.5 for v in imp.values], color="#f87171",
                    line=dict(color="#0b1220", width=1)),
        text=[f"<b>{COUNTRIES[c]}</b> (수입)<br>{v:,.1f} {U}" for c, v in imp.items()],
        hovertemplate="%{text}<extra></extra>"))
    # 수입국별은 중동 16개국만 칠하므로 중동으로 확대한다. 흐름(호) 보기는 공급국이 전 세계라 세계지도 그대로.
    geo = {**GEO, **GEO_ME} if overlay == "수입국별" else GEO
    # 제목 (2026-10-02 팀 피드백): 다른 그래프처럼 위에 제목 · 작은 줄. 글자 크기 · 자리는 추이 그래프 제목과 같다 (theme.adapt)
    name = "국가 간 교역액 흐름" if M["unit"] == "백만 달러" else "국가 간 무기 이전 흐름"
    how = f"호 굵기 = {M['value_label']}" if overlay != "수입국별" else f"색 = 수입국별 {M['value_label']}"
    _layout(fig, margin=dict(l=0, r=0, t=0, b=0), height=height, geo=geo, dragmode="pan",
            title=dict(text=ctitle(name, f"단위 {U} · {_per(df)} · {how}"), x=0),
            uirevision=f"arms-map-{overlay}")            # 보기마다 따로: 바꾸면 그 보기의 처음 범위로 열린다
    st.plotly_chart(theme.adapt(fig), width="stretch", key="arms_map_chart",
                    config={"displaylogo": False, "scrollZoom": False, "responsive": True,
                            "modeBarButtons": [["zoomInGeo", "zoomOutGeo", "resetGeo"]]})
    st.caption((f"호 굵기 = {M['value_label']} · 선에 마우스를 올리면 상세 정보 표시 · 상위 {min(top_n, len(fl))}개 / 전체 {len(fl)}개 흐름"
                if overlay != "수입국별" else f"색이 진할수록 {M['value_label']} 규모가 큼") + " · 위치: 국가 중심점 기준")


# ---------------------------------------------------------------- 추이

TOP_COLOR = "#D55E00"   # 쌓기 그래프에서 비율이 가장 큰 항목 색

def draw_trend(df, M, how, by, show_count=True):
    U = M["unit"]
    key = {M["cat_label"]: "cat", "수입국": "target_name", M["exporter_label"]: "exporter"}[by]
    t, months, need = arms.series(df, how, key)

    if key != "cat":                                  # 항목이 많으면 상위 8개 + 기타
        keep = t.sum().sort_values(ascending=False).index[:8]
        other = t.drop(columns=keep).sum(axis=1)
        t = t[keep]
        if other.sum() > 0:
            t["기타"] = other
    fig = go.Figure()
    # 비율이 가장 큰 항목은 가장 잘 보이는 Vermillion(#D55E00)으로 (2026-10-02 팀 요청, 원래 그 색이던 항목과 맞바꿈)
    colors = dict(M["colors"])
    if key == "cat" and len(t.columns) and t.sum().max() > 0:
        top = t.sum().idxmax()
        had = next((c for c, v in colors.items() if v.upper() == TOP_COLOR), None)
        if had and had != top:
            colors[had], colors[top] = colors.get(top), TOP_COLOR

    for col in t.columns:
        fig.add_trace(go.Bar(
            x=t.index, y=t[col], name=col, marker_color=colors.get(col) if key == "cat" else None,
            hovertemplate=f"{col} %{{y:,.1f}} {U}<extra></extra>"))
    monthly_source = M["periods"] != ["연간"]

    if monthly_source:                                  # 월 단위 자료만 관측 월 수를 툴팁에 실음
        fig.add_trace(go.Scatter(x=t.index, y=t.sum(axis=1), mode="lines", line=dict(width=0), showlegend=False,
                                 customdata=[f"{m}/{need}" for m in months],
                                 hovertemplate=f"합계 %{{y:,.1f}} {U} · 관측 %{{customdata}}개월<extra></extra>"))
    fmt = {"월별": "%Y-%m", "분기별": "%Y-%m", "연간": "%Y"}[how]
    _layout(fig, barmode="stack", height=460, hovermode="x unified", bargap=0.15,
            title=dict(text=ctitle(f"{how} {M['value_label']} 추이", f"단위 {U} · {_per(df)} · 구성 항목 = {by}"), x=0),
            legend=dict(orientation="h", y=-0.2, yanchor="top", x=0, font=dict(size=14)))
    _axes(fig)
    fig.update_xaxes(tickformat=fmt, hoverformat=fmt, title_text="연도" if how == "연간" else "연월", title_font=dict(size=13))
    fig.update_yaxes(title_text=f"{M['value_label']} ({U}, {how})")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})

    if monthly_source and how != "월별":
        short = int((months < need).sum())
        if short:
            st.caption(f"관측 월이 부족한 기간 {short}개 · 도움말의 관측 n/{need}개월 확인 · 신고 누락에 따른 합계 과소 집계 가능 · "
                       "미신고 월: 관측 없음으로 처리")
            
    if not monthly_source and show_count:               # SIPRI: 계약 건수 추이 (국가별 보기에서는 오른쪽 단에 따로)
        draw_count(df)


def _per(df):
    """그래프 부제에 붙이는 기간 (필터로 고른 범위의 첫 해–끝 해). 2026-10-02 팀 피드백: 모든 그래프에 기간 표기."""
    if df is None or df.empty or "year" not in df:
        return ""
    y0, y1 = int(df["year"].min()), int(df["year"].max())
    return f"{y0}–{y1}" if y0 != y1 else f"{y0}"


def draw_count(df, height=240, short=False):
    """SIPRI 연도별 계약 건수. short=True 면 제목 한 줄 (좁은 오른쪽 단에 쌓을 때)."""
    n = df.groupby("year")["obs"].nunique()
    fig2 = go.Figure(go.Scatter(x=n.index, y=n.values, mode="lines+markers", line=dict(color=GOLD, width=2),
                                marker=dict(size=5), hovertemplate="%{x}년 · 계약 %{y}건<extra></extra>"))
    title = "연도별 계약 건수" if short else ctitle("연도별 계약 건수", f"단위 건 · {_per(df)} · SIPRI 주문 연도 기준 · 필터 조건")
    _layout(fig2, height=height, title=dict(text=title, font=dict(size=16, color="#e5eaf3"), x=0),
            **({"margin": dict(l=10, r=10, t=44, b=10)} if short else {}))
    _axes(fig2)
    fig2.update_yaxes(title_text="계약 (건)", title_font=dict(size=13))
    fig2.update_xaxes(title_text="" if short else "연도", title_font=dict(size=13))
    st.plotly_chart(theme.adapt(fig2), width="stretch", config={"displaylogo": False})


# ---------------------------------------------------------------- 순위

def hbar(series, title, color, U, height=420):
    s = series.sort_values(ascending=True).tail(12)
    fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color=color,
                           text=[f"{v:,.0f}" for v in s.values], textposition="outside", cliponaxis=False,
                           hovertemplate=f"%{{y}}<br>%{{x:,.1f}} {U}<extra></extra>"))
    _layout(fig, margin=dict(l=10, r=70, t=40, b=10), height=height,
            title=dict(text=title, font=dict(size=16, color="#e5eaf3"), x=0))
    _axes(fig)
    fig.update_xaxes(range=[0, float(s.max()) * 1.18 if len(s) else 1],   # 가장 긴 막대 끝 숫자가 잘리지 않게 여유
                     title_text=U, title_font=dict(size=13))                                      # 단위 (2026-10-02)
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def target_cat_heatmap(df, M, highlight=None, title=None, height=None):
    """수입국(행) × 품목(열) 히트맵. highlight 나라는 맨 위로 올리고 이름에 ▶ 표시."""
    h = df.pivot_table(index="target_name", columns="cat", values="value", aggfunc="sum", fill_value=0)
    h = h.loc[h.sum(axis=1).sort_values(ascending=False).index]

    if highlight in h.index:
        h = pd.concat([h.loc[[highlight]], h.drop(index=highlight)])
    labels = [f"▶ {n}" if n == highlight else n for n in h.index]
    fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=labels, colorscale=[[0, "#111a2e"], [1, GOLD]],
                               hovertemplate=f"%{{y}} · %{{x}}<br>%{{z:,.1f}} {M['unit']}<extra></extra>",
                               colorbar=dict(title=dict(text=M["unit"], font=dict(size=12, color="#cbd5e1")), thickness=10, tickfont=dict(color="#cbd5e1"))))
    _layout(fig, height=height or max(320, 40 + 26 * len(h)),
            title=dict(text=title or ctitle(f"수입국 × {M['cat_label']}", f"단위 {M['unit']} · {_per(df)} · 색 농도 = 거래 규모 · 필터 조건"), font=dict(size=16, color="#e5eaf3"), x=0))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def draw_rank(df, M):
    U = M["unit"]
    c1, c2 = st.columns(2)

    with c1:
        hbar(df.groupby("exporter")["value"].sum(), ctitle(f"{M['exporter_label']} TOP 12", f"단위 {U} · {_per(df)} 합계 · 필터 조건"), GOLD, U)
    with c2:
        hbar(df.groupby("target_name")["value"].sum(), ctitle("수입국 상위 12개국", f"단위 {U} · {_per(df)} 합계 · 필터 조건"), "#f87171", U)
    c3, c4 = st.columns(2)
    # 품목별 막대와 옆 히트맵의 아래 끝을 맞춘다: 히트맵은 수입국 수만큼 길어지므로 둘 다 그 높이로 (2026-10-01)
    hh = max(420, 40 + 26 * df["target_name"].nunique())
    with c3:
        hbar(df.groupby("cat")["value"].sum(), ctitle(f"{M['cat_label']}별", f"단위 {U} · {_per(df)} 합계 · 필터 조건"), "#60a5fa", U, height=hh)
    with c4:
        target_cat_heatmap(df, M, height=hh)
    if "weapon" in df.columns:                          # SIPRI: 무기 모델 표
        w = (df.groupby(["weapon", "weapon_desc"]).agg(tiv=("value", "sum"), n=("obs", "nunique"), qty=("qty", "sum"))
               .reset_index().sort_values("tiv", ascending=False).head(15))
        st.markdown("**무기 모델 상위 15개 (주문 TIV)**")
        st.dataframe(w.rename(columns={"weapon": "모델", "weapon_desc": "종류", "tiv": "주문 TIV", "n": "계약", "qty": "수량"}).round(0),
                     hide_index=True, width="stretch", height=380)


# ---------------------------------------------------------------- 추이 탭 오른쪽 상자 (2026-10-01)



def _side_flow(df, M):
    """흐름 요약: 가장 많았던 해 · 최근 5년 vs 그 전 5년 · 최근 해. 월 자료(Comtrade)는 12달이 다 있는 해끼리만 견준다."""
    U = M["unit"]
    yt = df.groupby("year")["value"].sum()
    if M["periods"] != ["연간"]:                         # 월 자료: 12달이 다 찬 해만 '완결된 해'
        full = df.groupby("year")["period"].nunique()
        done = sorted(int(y) for y in full[full >= 12].index)
    else:
        done = sorted(int(y) for y in yt.index)
    y_last = int(yt.index.max())
    peak = int(yt.idxmax())
    part = ""
    if M["periods"] != ["연간"]:
        mm = df.loc[df["year"] == y_last, "period"].nunique()
        part = f" (1~{mm}월)" if mm < 12 else ""
    h = [f'<div class="ts-k">'
         f'<div class="ts-kc"><div class="ts-kl">최대 규모 연도</div><div class="ts-kv">{peak}년</div>'
         f'<div class="ts-ks">{yt.max():,.0f} {U}</div></div>']
    if len(done) >= 10:
        e = done[-1]
        r5 = yt.reindex(range(e - 4, e + 1)).fillna(0).sum()
        p5 = yt.reindex(range(e - 9, e - 4)).fillna(0).sum()
        ch = r5 / p5 - 1 if p5 else None
        cls = "" if ch is None else ("up" if ch > 0 else "down")
        h.append(f'<div class="ts-kc"><div class="ts-kl">최근 5년·직전 5년 비교</div>'
                 f'<div class="ts-kv {cls}">{"—" if ch is None else f"{ch:+.0%}"}</div>'
                 f'<div class="ts-ks">{e - 4}–{e} {r5:,.0f} · {e - 9}–{e - 5} {p5:,.0f}</div></div>')
    else:
        h.append('<div class="ts-kc"><div class="ts-kl">최근 5년·직전 5년 비교</div><div class="ts-kv">—</div>'
                 '<div class="ts-ks">선택 기간 10년 미만으로 비교 제외</div></div>')
    h.append(f'<div class="ts-kc"><div class="ts-kl">최신 연도 {y_last}{part}</div><div class="ts-kv">{yt.loc[y_last]:,.0f}</div>'
             f'<div class="ts-ks">{U}</div></div></div>')
    return "".join(h)


def trend_side(df, M, by, k):
    """추이 그래프 오른쪽 상자: 흐름 요약 (가장 많았던 해 · 최근 5년 vs 그 전 5년 · 최근 해).
    (2026-10-01) '상위 5' 쪽은 뺐다 — 쌓은 막대 · 범례와 겹쳐 굳이 필요 없다는 의견"""
    with st.container(key=f"trend_side_{k}"):
        st.markdown('<div class="ts-h">흐름 요약</div><div class="ts-s">선택 기간의 연간 합계 기준</div>' + _side_flow(df, M),
                    unsafe_allow_html=True)


# ---------------------------------------------------------------- 국가별 보기

def country_picker(df, key, width="stretch"):
    order = df.groupby("target_iso3")["value"].sum().sort_values(ascending=False).index.tolist()
    return st.selectbox("수입국", order, format_func=COUNTRIES.get, key=key, width=width)


def draw_country_compare(df, M, country, how, height=360, legend=True, short=False):
    """수입국별 비교 선 그래프. 고른 나라만 빨갛게. legend=False 면 범례 없이 (좁은 오른쪽 단 · 나라 이름은 마우스로).
    short=True 면 제목 한 줄 (오른쪽 단에 두 그래프를 쌓을 때)."""
    t, months, need = arms.series(df, how, "target_name")
    fig = go.Figure()
    name = COUNTRIES[country]

    for col in t.columns:
        me = col == name
        fig.add_trace(go.Scatter(
            x=t.index, y=t[col], mode="lines", name=col,
            line=dict(color="#f87171" if me else "#475569", width=3 if me else 1.2),
            opacity=1 if me else 0.7, hovertemplate=f"{col} %{{y:,.1f}} {M['unit']}<extra></extra>"))
    fmt = {"월별": "%Y-%m", "분기별": "%Y-%m", "연간": "%Y"}[how]
    _layout(fig, height=height, hovermode="x unified", showlegend=legend,
            title=dict(text=f"수입국별 비교 · {name} 강조" if short else
                       ctitle("수입국별 비교", f"단위 {M['unit']} · {how} · {_per(df)} · {name} 강조 · 회색 = 다른 수입국"), font=dict(size=16, color="#e5eaf3"), x=0),
            **({"margin": dict(l=10, r=10, t=44, b=10)} if short else {}),
            legend=dict(orientation="h", y=-0.25, yanchor="top", x=0, font=dict(size=13)))
    _axes(fig)
    fig.update_xaxes(tickformat=fmt, hoverformat=fmt, title_text="연도" if how == "연간" else "연월", title_font=dict(size=13))
    fig.update_yaxes(title_text=f"{M['value_label']} ({M['unit']})")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def draw_rank_country(df, M, country):
    U = M["unit"]
    one = df[df["target_iso3"] == country]
    name = COUNTRIES[country]
    total = one["value"].sum()
    # (2026-10-01) 그 나라 합계 줄은 위 '분석 대상국' 줄의 숫자 칩으로 옮겼다

    if one.empty:
        st.info("선택 국가의 자료 없음")
        return
    c1, c2 = st.columns(2)
    with c1:
        hbar(one.groupby("exporter")["value"].sum(), ctitle(f"{name} {M['exporter_label']} TOP 12", f"단위 {U} · {_per(one)} 합계"), GOLD, U)
    with c2:
        hbar(one.groupby("cat")["value"].sum(), ctitle(f"{name} {M['cat_label']}별", f"단위 {U} · {_per(one)} 합계"), "#60a5fa", U)
    target_cat_heatmap(df, M, highlight=name, title=ctitle(f"수입국 × {M['cat_label']}", f"단위 {M['unit']} · {_per(df)} · {name}(▶)를 상단에 표시하여 국가 간 비교"))
    share = df.groupby("target_name")["value"].sum().sort_values(ascending=False)
    rank = list(share.index).index(name) + 1
    st.caption(f"{name}{jo(name, '은는')} · 선택 기간 전체 대비 비중 {total / share.sum():.1%} ({rank}위 / {len(share)}개국)")


# ---------------------------------------------------------------- 국가쌍

def draw_pairs(df, M):
    U = M["unit"]
    fl = arms.flows(df)
    left, right = st.columns(2, gap="medium")           # [표 | 히트맵] 2열 (2026-10-02 팀 피드백)
    with left:
        st.markdown(f"**{M['exporter_label']} → 수입국 흐름 {len(fl)}개** ({M['value_label']} 내림차순 · 단위 {U})")
        cols = {"exporter": M["exporter_label"], "target_name": "수입국", "value": f"{M['value_label']} ({U})",
                "obs": M["obs_label"], "top_cat": f"주요 {M['cat_label']}"}
        st.dataframe(fl.rename(columns=cols)[list(cols.values())].round(1), hide_index=True, width="stretch", height=420)
    top_exp = df.groupby("exporter")["value"].sum().sort_values(ascending=False).index[:10]
    h = df[df["exporter"].isin(top_exp)].pivot_table(index="target_name", columns="exporter", values="value",
                                                     aggfunc="sum", fill_value=0).reindex(columns=top_exp)
    fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=h.index, colorscale=[[0, "#111a2e"], [1, GOLD]],
                               hovertemplate=f"%{{x}} → %{{y}}<br>%{{z:,.1f}} {U}<extra></extra>",
                               colorbar=dict(title=dict(text=U, font=dict(size=12, color="#cbd5e1")), thickness=10, tickfont=dict(color="#cbd5e1"))))
    _layout(fig, height=460, title=dict(text=ctitle(f"수입국 × 상위 10개 {M['exporter_label']}", f"단위 {U} · {_per(df)} 합계 · 색 농도 = 거래 규모"), font=dict(size=16, color="#e5eaf3"), x=0))
    with right:
        st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


# ---------------------------------------------------------------- 페이지

# ---------------------------------------------------------------- 필터 (본문 맨 위 접이식, 2026-10-01 새 모양)

# def _put(store, field, value, wkey):
#     """빠른 버튼 · 전체 선택: 보관한 값을 바꾸고 위젯 상태를 지워, 다음 실행 때 그 값으로 다시 그리게 한다."""
#     store[field] = value
#     st.session_state.pop(wkey, None)

def _put(store, field, value, wkey):
    """버튼 선택값을 저장하고 위젯에 반영한다."""
    if field in ("period", "years"):
        store[field] = tuple(value)

        # 다음 실행에서 슬라이더를 새 key로 생성
        base_key = wkey.rsplit("__", 1)[0]
        version_key = f"{base_key}_version"
        st.session_state[version_key] = (
            st.session_state.get(version_key, 0) + 1
        )
    else:
        selected = list(value)
        store[field] = selected
        st.session_state[wkey] = selected


def _reset(skey, keys):
    """필터 초기화: 보관한 값 · 위젯 상태를 지워 처음 값으로."""
    st.session_state.pop(skey, None)
    for key in keys:
        st.session_state.pop(key, None)


def _filters(box, f, M, k, y0, y1, cats_all, targets_all, exp_opts, exp_name, months=None):
    """필터 상자 안: 기간(+ 최근 5년 · 10년 · 전체 버튼) · 수출국 · 품목 · 수입국(+ 전체 선택). 바꾸면 바로 반영 (적용 버튼 없음).
    값은 st.session_state[f"arms_store_{k}"] 에 보관하고 위젯에는 value/default 로 넘긴다
    (위젯 key 에 직접 값을 넣으면 범위 슬라이더가 한 점짜리로 바뀌는 문제가 있어서)."""
    kp, ky, kc, kt, ke = (f"arms_period_{k}", f"arms_years_{k}", f"arms_cats_{k}", f"arms_targets_{k}", f"arms_exporters_{k}")
    
    kp = f"{kp}__{st.session_state.get(f'{kp}_version', 0)}"
    ky = f"{ky}__{st.session_state.get(f'{ky}_version', 0)}"
    
    skey = f"arms_store_{k}"
    opts = [d.strftime("%Y-%m") for d in months] if months is not None else None
    if skey not in st.session_state:
        st.session_state[skey] = {
            "period": (next((o for o in opts if o >= f"{M['default_start']}-01"), opts[0]), opts[-1]) if opts else None,
            "years": (max(y0, M["default_start"]), y1), "cats": cats_all, "targets": targets_all, "exporters": []}
    store = st.session_state[skey]
    with box:
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown('<div class="flt-h">필터 변경 사항 즉시 반영</div>', unsafe_allow_html=True)
            st.space("stretch")
            st.button("필터 초기화", key=f"arms_reset_{k}", on_click=_reset, args=(skey, [kp, ky, kc, kt, ke]), type="tertiary")
        c1, c2 = st.columns([1, 1], gap="large")

        with c1:
            if opts is not None:
                quick = {
                    "최근 5년": (opts[-60], opts[-1]),
                    "최근 10년": (opts[-120], opts[-1]),
                    "전체 기간": (opts[0], opts[-1]),
                }
                field, wkey = "period", kp
                period_label = "기간 (월)"
            else:
                quick = {
                    "최근 5년": (y1 - 4, y1),
                    "최근 10년": (y1 - 9, y1),
                    "전체 기간": (y0, y1),
                }
                field, wkey = "years", ky
                period_label = "기간"

            # 기간 라벨과 빠른 선택 버튼 묶음
            with st.container(
                horizontal=True,
                vertical_alignment="center",
                gap="small",
                key=f"flt_period_head_{k}",
            ):
                st.markdown(period_label)

                with st.container(
                    horizontal=True,
                    gap="xsmall",
                    width="content",
                    key=f"flt_quick_{k}",
                ):
                    for lbl, val in quick.items():
                        st.button(
                            lbl,
                            key=f"arms_q_{lbl}_{k}",
                            on_click=_put,
                            args=(store, field, val, wkey),
                            type=(
                                "primary"
                                if tuple(store[field]) == tuple(val)
                                else "secondary"
                            ),
                        )

            # 기본 라벨은 숨기고 슬라이더만 표시
            if opts is not None:
                store["period"] = tuple(
                    st.select_slider(
                        period_label,
                        options=opts,
                        value=store["period"],
                        key=kp,
                        label_visibility="collapsed",
                    )
                )
                f["period"] = store["period"]
                f["years"] = (
                    int(f["period"][0][:4]),
                    int(f["period"][1][:4]),
                )
            else:
                store["years"] = tuple(
                    st.slider(
                        period_label,
                        y0,
                        y1,
                        value=store["years"],
                        key=ky,
                        label_visibility="collapsed",
                    )
                )
                f["years"] = store["years"]

        with c2:
            st.markdown(f"{M['exporter_label']} 선택 (미선택 시 전체)")

            store["exporters"] = st.multiselect(
                f"{M['exporter_label']} 선택 (미선택 시 전체)",
                exp_opts,
                default=store["exporters"],
                format_func=exp_name.get,
                key=ke,
                placeholder=f"전체 {len(exp_opts)}개국",
                label_visibility="collapsed",
            )

         # 두 번째 줄: 품목 | 수입국 + 전체 선택
        c3, c4 = st.columns([1, 1], gap="large")

        with c3:
            st.markdown(f"{M['cat_label']} ({len(cats_all)}개 분야)")

            store["cats"] = st.pills(
                f"{M['cat_label']} ({len(cats_all)}개 분야)",
                cats_all,
                selection_mode="multi",
                default=store["cats"],
                key=kc,
                label_visibility="collapsed",
            ) or cats_all

        with c4:
        # 수입국 라벨과 전체 선택 버튼
            with st.container(
                horizontal=True,
                vertical_alignment="center",
                gap="small",
            ):
                st.markdown(
                    f"수입국 (중동 {len(targets_all)}개국)"
                )
                st.space("stretch")
                st.button(
                    "전체 선택",
                    key=f"arms_tall_{k}",
                    on_click=_put,
                    args=(store, "targets", targets_all, kt),
                    width="content",
                )

            # 라벨은 위에서 표시하므로 기본 라벨 숨김
            store["targets"] = st.multiselect(
                f"수입국 (중동 {len(targets_all)}개국 · 미선택 시 전체)",
                targets_all,
                default=store["targets"],
                format_func=COUNTRIES.get,
                key=kt,
                placeholder="전체",
                label_visibility="collapsed",
            ) or targets_all
    
    f["exporters"], f["cats"], f["targets"] = store["exporters"], store["cats"], store["targets"]


def _group(label, key):
    """탭 줄 오른쪽 작은 묶음: 왼쪽에 이름표, 오른쪽에 버튼 (이름표가 위가 아니라 옆이라 줄 높이가 낮다)."""
    g = st.container(horizontal=True, vertical_alignment="center", gap="xsmall", key=f"grp_{key}", width="content")
    g.markdown(f'<span class="grp-l">{label}</span>', unsafe_allow_html=True)
    return g


def _chips(items):
    """분석 대상국 줄 오른쪽 숫자 칩: [(이름, 값)]"""
    return "".join(f'<span class="chip">{a} <b>{b}</b></span>' for a, b in items)


def page(compact=True, show_title=True):
    """무기 거래 추이 (2026-10-01 새 모양):
    제목 | 자료 고르기(Comtrade · SIPRI) → 접이식 필터 → [보기 탭 | 그 탭의 조작] 한 줄 → (국가별이면 분석 대상국 줄) → 그래프."""
    if show_title:
        h1, h2 = st.columns([2.1, 1], vertical_alignment="center", gap="large")
        with h1:
            st.title("무기 거래 추이")
            page_sub(term("SIPRI") + "와 " + term("UN Comtrade") + " 기반 중동 16개국의 무기 이전 규모·교역액·주요 공급국·품목별 거래 현황 비교 · SIPRI 단위: " + term("TIV") + "")
        with h2:
            source = tabbar("자료", ["Comtrade", "SIPRI"], key="arms_source",
                            format_func=lambda s: s)   # 좁은 칸이라 이름만 (단위는 부제 · 말풍선에)
    else:
        source = tabbar("자료", ["Comtrade", "SIPRI"], key="arms_source")
    M = arms.SOURCES[source]
    U = M["unit"]
    df, missing = arms.load(source)
    st.markdown(f'<div class="src-note">자료 설명 {info_icon(M["desc"])}</div>', unsafe_allow_html=True)   # 자료 설명은 말풍선

    cats_all = [c for c in M["colors"] if c in set(df["cat"])]
    targets_all = [c for c in COUNTRIES if c in set(df["target_iso3"])]
    exp_opts = df.groupby("exporter_iso3")["value"].sum().sort_values(ascending=False).index.tolist()
    exp_name = df.drop_duplicates("exporter_iso3").set_index("exporter_iso3")["exporter"].to_dict()
    y0, y1 = int(df["year"].min()), int(df["year"].max())
    k = source                                          # 자료마다 위젯 상태를 따로 둔다
    f = {}
    months = pd.date_range(df["date"].min(), df["date"].max(), freq="MS") if source == "Comtrade" else None   # 월별 자료

    tab_slot = st.container()                           # 보기 탭 줄 자리 — 필터보다 위에 두려고 먼저 잡아 둔다 (2026-10-02 팀 피드백)
    _filters(page_filters("무기 거래 추이"), f, M, k, y0, y1, cats_all, targets_all, exp_opts, exp_name, months)
    years, cats, targets, exporters = f["years"], f["cats"], f["targets"], f["exporters"]
    per_txt = f"{f['period'][0]}–{f['period'][1]}" if months is not None else f"{years[0]}–{years[1]}"
    filter_note(f'{per_txt} · {M["cat_label"]} {len(cats)}/{len(cats_all)} · 수입국 {len(targets)}곳 · '
                f'{M["exporter_label"]} {"전체" if not exporters else str(len(exporters)) + "곳"}')

    if source == "Comtrade" and years[0] < arms.FULL_START_YEAR:
        st.warning(f"{arms.FULL_START_YEAR}년 이전 신고 수출국은 연 8~11개국(2010년부터 41개국 이상)으로 제한 · 교역액 과소 집계 가능 · "
                   "시기별 비교에 활용 시 주의 필요")
    sub = arms.apply_filters(df, years, cats, targets, exporters)
    if months is not None:                              # 월 단위로 고른 기간이면 달까지 자른다
        m0, m1 = pd.Timestamp(f["period"][0] + "-01"), pd.Timestamp(f["period"][1] + "-01")
        sub = sub[(sub["date"] >= m0) & (sub["date"] <= m1)]
    if sub.empty:
        st.warning("선택 조건에 해당하는 자료 없음")
        return

    total = sub["value"].sum()
    top_exp = sub.groupby("exporter")["value"].sum().sort_values(ascending=False)
    top_cat = sub.groupby("cat")["value"].sum().sort_values(ascending=False)
    items = [(f"{M['value_label']} 합계", f"{total:,.0f}", f"{U} · {per_txt}", "blue"),
             (f"최대 {M['exporter_label']}", top_exp.index[0], f"{top_exp.iloc[0] / total:.0%} · {top_exp.iloc[0]:,.0f} {U}", "red"),
             (f"최대 {M['cat_label']}", top_cat.index[0], f"{top_cat.iloc[0] / total:.0%} · {top_cat.iloc[0]:,.0f} {U}", "")]

    # ── 보기 탭 + 그 탭의 조작을 한 줄에.
    #    Streamlit 기본 탭(st.tabs) 줄에는 버튼을 넣을 수 없어서, 탭을 버튼 묶음(segmented_control)으로 만들었다.
    with tab_slot, st.container(horizontal=True, vertical_alignment="center", gap="small", key=f"tab_row_{k}"):
        tab = st.segmented_control("보기", ["지도", "추이", "순위", "국가쌍"], default="지도", key=f"arms_tab_{k}",
                                   label_visibility="collapsed") or "지도"
        st.space("stretch")
        if tab == "지도":
            arc = f"{M['role_label']} 흐름(호)"
            with _group("표시", f"map_ov_{k}"):
                overlay = st.segmented_control("표시", [arc, "수입국별"], default=arc, key=f"arms_overlay_{k}",
                                               label_visibility="collapsed") or arc
            with _group("흐름 수", f"map_n_{k}"):
                top_n = st.slider("흐름 수", 5, 100, 40, step=5, key=f"arms_topn_{k}", label_visibility="collapsed", width=200)
        elif tab == "추이":
            with _group("범위", f"tr_scope_{k}"):
                scope = st.segmented_control("범위", ["전체", "국가별"], default="전체", key=f"arms_trend_scope_{k}",
                                             label_visibility="collapsed") or "전체"
            with _group("집계", f"tr_how_{k}"):
                how = st.segmented_control("집계", M["periods"], default=M["default_period"], key=f"arms_how_{k}",
                                           label_visibility="collapsed") or M["default_period"]
            opts = [M["cat_label"], "수입국", M["exporter_label"]] if scope == "전체" else [M["cat_label"], M["exporter_label"]]
            with _group("구성 항목", f"tr_by_{k}"):
                by = st.segmented_control("구성 항목", opts, default=opts[0],
                                          key=f"arms_by_{k}" if scope == "전체" else f"arms_by_country_{k}",
                                          label_visibility="collapsed") or opts[0]
        elif tab == "순위":
            with _group("범위", f"rk_scope_{k}"):
                scope = st.segmented_control("범위", ["전체", "국가별"], default="전체", key=f"arms_rank_scope_{k}",
                                             label_visibility="collapsed") or "전체"

    def target_row(key):
        """국가별일 때만: '분석 대상국 (수입국)' 고르기 + 그 나라 숫자 칩 한 줄."""
        with st.container(horizontal=True, vertical_alignment="center", gap="medium", key=f"cty_row_{key}"):
            st.markdown('<span class="grp-l">분석 대상국 (수입국)</span>', unsafe_allow_html=True)
            order = sub.groupby("target_iso3")["value"].sum().sort_values(ascending=False).index.tolist()
            country = st.selectbox("분석 대상국", order, format_func=COUNTRIES.get, key=key,
                                   label_visibility="collapsed", width=220)
            one = sub[sub["target_iso3"] == country]
            st.space("stretch")
            tc = one.groupby("cat")["value"].sum().sort_values(ascending=False)
            n_lbl = "관측 개월" if months is not None else "계약"
            n_val = f"{one['period'].nunique()}개월" if months is not None else f"{one['obs'].nunique():,}건"
            st.markdown(_chips([(f"총 {M['value_label']}", f"{one['value'].sum():,.0f} {U}"), (n_lbl, n_val),
                                (f"최대 {M['cat_label']}", f"{tc.index[0]} ({tc.iloc[0] / tc.sum():.0%})" if len(tc) else "—")]),
                        unsafe_allow_html=True)
        return country, one

    if tab == "지도":
        # [지도 | 요약 카드 3개] 2:1, 둘 다 460px
        left, right = st.columns([2, 1], gap="medium")
        with left:
            draw_map(sub, M, overlay, top_n, height=460)
            if missing:
                st.caption(f"좌표 미확보로 지도 표시 제외된 {M['exporter_label']}: {', '.join(missing)}")
        with right, st.container(key=f"trend_side_map_{k}"):
            st.markdown(f'<div class="ts-h">요약 · {per_txt}</div>' + strip(items[:3], vertical=True), unsafe_allow_html=True)
    elif tab == "추이":
        # 전체 = [추이 | 흐름 요약 상자], 국가별 = 분석 대상국 줄 → [그 나라 추이 | 수입국별 비교] — 둘 다 2:1
        if scope == "전체":
            tl, tr = st.columns([2, 1], gap="medium")
            with tl:
                draw_trend(sub, M, how, by)
            with tr:
                trend_side(sub, M, by, k)
        else:
            country, one = target_row(f"arms_trend_country_{k}")
            tl, tr = st.columns([2, 1], gap="medium")
            with tl:
                draw_trend(one, M, how, by, show_count=False)
            with tr:
                if M["periods"] == ["연간"]:           # SIPRI: 비교 · 계약 건수 두 그래프를 위아래로 (합쳐서 왼쪽 그래프 높이 460)
                    draw_country_compare(sub, M, country, how, height=222, legend=False, short=True)
                    draw_count(one, height=222, short=True)
                else:
                    draw_country_compare(sub, M, country, how, height=460, legend=False)
    elif tab == "순위":
        if scope == "전체":
            draw_rank(sub, M)
        else:
            country, _ = target_row(f"arms_rank_country_{k}")
            draw_rank_country(sub, M, country)
    else:
        draw_pairs(sub, M)
    st.markdown(f'<div class="src-note">해석 시 유의사항 {info_icon(M["foot"] + " 지도 위치: 국가 중심점 기준 · 실제 운송 경로와는 구별")}</div>',
                unsafe_allow_html=True)
