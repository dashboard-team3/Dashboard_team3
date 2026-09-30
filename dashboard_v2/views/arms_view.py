"""무기 거래 추이 페이지: Comtrade(교역액) 또는 SIPRI(주문 TIV)를 골라 지도·추이·순위·국가쌍으로 본다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sources import arms
from core.ui import page_sub, term
from core import theme
from core.ui import ctitle, info_icon          # 밝은 테마일 때 그래프 색 바꾸기
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


def strip(items):
    """카드 대신 한 줄 띠: [(label, value, sub, tone)] — 그래프가 위로 올라오도록 높이를 줄인 요약 (app2)."""
    cells = "".join(f'<div class="cell {tone}"><span class="l">{label}</span><span class="v">{value}</span>'
                    f'<span class="s">{sub}</span></div>' for label, value, sub, tone in items)
    return f'<div class="strip">{cells}</div>'


def _axes(fig):
    """축은 조용하게: 세로 격자·축선 없이, 가로 격자만 옅게."""
    fig.update_xaxes(showgrid=False, showline=False, zeroline=False, ticks="outside", ticklen=4, tickcolor="#141d30")
    fig.update_yaxes(gridcolor="#141d30", showline=False, zeroline=False)


def _layout(fig, **kw):
    fig.update_layout(**{**DARK, **kw})


# ---------------------------------------------------------------- 지도

def draw_map(df, M, overlay, top_n):
    U = M["unit"]
    fig = go.Figure()
    fl = arms.flows(df)
    imp = df.groupby("target_iso3")["value"].sum()

    if overlay == "대상국별 수입":
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
        mid_lat, mid_lon, mid_txt, mid_size = [], [], [], []
        for r in shown.itertuples():
            a, b = arms.pos(r.exporter_iso3), arms.pos(r.target_iso3)
            if a is None or b is None:
                continue
            lats, lons = arms.great_circle(a[0], a[1], b[0], b[1])
            w = 1 + 7 * (r.value / top) ** 0.5
            fig.add_trace(go.Scattergeo(lat=lats, lon=lons, mode="lines", hoverinfo="skip", showlegend=False,
                                        line=dict(color=GOLD, width=w), opacity=0.55))
            k = len(lats) // 2
            mid_lat.append(lats[k]); mid_lon.append(lons[k]); mid_size.append(max(6, w * 2))
            mid_txt.append(f"<b>{r.exporter} → {r.target_name}</b><br>{r.value:,.1f} {U} · {M['obs_label']} {r.obs}"
                           f"<br>주요 {M['cat_label']} {r.top_cat}")
        fig.add_trace(go.Scattergeo(lat=mid_lat, lon=mid_lon, mode="markers", showlegend=False,
                                    marker=dict(size=mid_size, color="rgba(0,0,0,0)"),
                                    text=mid_txt, hovertemplate="%{text}<extra></extra>"))
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
    # 대상국별 수입은 중동 16개국만 칠하므로 중동으로 확대한다. 흐름(호) 보기는 공급국이 전 세계라 세계지도 그대로.
    geo = {**GEO, **GEO_ME} if overlay == "대상국별 수입" else GEO
    _layout(fig, margin=dict(l=0, r=0, t=0, b=0), height=560, geo=geo, dragmode="pan",
            uirevision=f"arms-map-{overlay}")            # 보기마다 따로: 바꾸면 그 보기의 처음 범위로 열린다
    st.plotly_chart(theme.adapt(fig), width="stretch", key="arms_map_chart",
                    config={"displaylogo": False, "scrollZoom": False, "responsive": True,
                            "modeBarButtons": [["zoomInGeo", "zoomOutGeo", "resetGeo"]]})
    st.caption((f"호 굵기 = {M['value_label']} · 호 가운데에 마우스를 올리면 상세 · 상위 {min(top_n, len(fl))}개 / 전체 {len(fl)}개 흐름"
                if overlay != "대상국별 수입" else f"색이 진할수록 {M['value_label']} 규모가 큼") + " · 위치는 나라 중심점(대략)")


# ---------------------------------------------------------------- 추이

def draw_trend(df, M, how, by):
    U = M["unit"]
    key = {M["cat_label"]: "cat", "대상국": "target_name", M["exporter_label"]: "exporter"}[by]
    t, months, need = arms.series(df, how, key)

    if key != "cat":                                  # 항목이 많으면 상위 8개 + 기타
        keep = t.sum().sort_values(ascending=False).index[:8]
        other = t.drop(columns=keep).sum(axis=1)
        t = t[keep]
        if other.sum() > 0:
            t["기타"] = other
    fig = go.Figure()

    for col in t.columns:
        fig.add_trace(go.Bar(
            x=t.index, y=t[col], name=col, marker_color=M["colors"].get(col) if key == "cat" else None,
            hovertemplate=f"{col} %{{y:,.1f}} {U}<extra></extra>"))
    monthly_source = M["periods"] != ["연간"]

    if monthly_source:                                  # 월 단위 자료만 관측 월 수를 툴팁에 실음
        fig.add_trace(go.Scatter(x=t.index, y=t.sum(axis=1), mode="lines", line=dict(width=0), showlegend=False,
                                 customdata=[f"{m}/{need}" for m in months],
                                 hovertemplate=f"합계 %{{y:,.1f}} {U} · 관측 %{{customdata}}개월<extra></extra>"))
    fmt = {"월별": "%Y-%m", "분기별": "%Y-%m", "연간": "%Y"}[how]
    _layout(fig, barmode="stack", height=450, hovermode="x unified", bargap=0.15,
            title=dict(text=ctitle(f"{how} {M['value_label']} 추이", f"단위 {U} · 쌓기 기준 = {by}"), x=0),
            legend=dict(orientation="h", y=-0.2, yanchor="top", x=0, font=dict(size=14)))
    _axes(fig)
    fig.update_xaxes(tickformat=fmt, hoverformat=fmt)
    fig.update_yaxes(title_text=f"{M['value_label']} ({U}, {how})")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})

    if monthly_source and how != "월별":
        short = int((months < need).sum())
        if short:
            st.caption(f"관측 월이 부족한 기간 {short}개(툴팁의 '관측 n/{need}개월' 참고)는 합계가 실제보다 작을 수 있습니다. "
                       "신고가 없는 달은 0이 아니라 '관측 없음'입니다.")
            
    if not monthly_source:                              # SIPRI: 계약 건수 추이
        n = df.groupby("year")["obs"].nunique()
        fig2 = go.Figure(go.Scatter(x=n.index, y=n.values, mode="lines+markers", line=dict(color=GOLD, width=2),
                                    marker=dict(size=5), hovertemplate="%{x}년 · 계약 %{y}건<extra></extra>"))
        _layout(fig2, height=240, title=dict(text=ctitle("연도별 계약 건수", "SIPRI 주문 연도 기준 · 필터 조건"), font=dict(size=16, color="#e5eaf3"), x=0))
        _axes(fig2)
        st.plotly_chart(theme.adapt(fig2), width="stretch", config={"displaylogo": False})


# ---------------------------------------------------------------- 순위

def hbar(series, title, color, U):
    s = series.sort_values(ascending=True).tail(12)
    fig = go.Figure(go.Bar(x=s.values, y=s.index, orientation="h", marker_color=color,
                           text=[f"{v:,.0f}" for v in s.values], textposition="outside", cliponaxis=False,
                           hovertemplate=f"%{{y}}<br>%{{x:,.1f}} {U}<extra></extra>"))
    _layout(fig, margin=dict(l=10, r=70, t=40, b=10), height=420,
            title=dict(text=title, font=dict(size=16, color="#e5eaf3"), x=0))
    _axes(fig)
    fig.update_xaxes(range=[0, float(s.max()) * 1.18 if len(s) else 1])   # 가장 긴 막대 끝 숫자가 잘리지 않게 여유
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def target_cat_heatmap(df, M, highlight=None, title=None):
    """대상국(행) × 품목(열) 히트맵. highlight 나라는 맨 위로 올리고 이름에 ▶ 표시."""
    h = df.pivot_table(index="target_name", columns="cat", values="value", aggfunc="sum", fill_value=0)
    h = h.loc[h.sum(axis=1).sort_values(ascending=False).index]

    if highlight in h.index:
        h = pd.concat([h.loc[[highlight]], h.drop(index=highlight)])
    labels = [f"▶ {n}" if n == highlight else n for n in h.index]
    fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=labels, colorscale=[[0, "#111a2e"], [1, GOLD]],
                               hovertemplate=f"%{{y}} · %{{x}}<br>%{{z:,.1f}} {M['unit']}<extra></extra>",
                               colorbar=dict(thickness=10, tickfont=dict(color="#cbd5e1"))))
    _layout(fig, height=max(320, 40 + 26 * len(h)),
            title=dict(text=title or ctitle(f"대상국 × {M['cat_label']}", "칸 색이 진할수록 큼 · 필터 조건"), font=dict(size=16, color="#e5eaf3"), x=0))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def draw_rank(df, M):
    U = M["unit"]
    c1, c2 = st.columns(2)

    with c1:
        hbar(df.groupby("exporter")["value"].sum(), ctitle(f"{M['exporter_label']} TOP 12", f"단위 {U} · 필터 조건의 합계"), GOLD, U)
    with c2:
        hbar(df.groupby("target_name")["value"].sum(), ctitle("대상국 TOP 12", f"단위 {U} · 필터 조건의 합계"), "#f87171", U)
    c3, c4 = st.columns(2)
    with c3:
        hbar(df.groupby("cat")["value"].sum(), ctitle(f"{M['cat_label']}별", f"단위 {U} · 필터 조건의 합계"), "#60a5fa", U)
    with c4:
        target_cat_heatmap(df, M)
    if "weapon" in df.columns:                          # SIPRI: 무기 모델 표
        w = (df.groupby(["weapon", "weapon_desc"]).agg(tiv=("value", "sum"), n=("obs", "nunique"), qty=("qty", "sum"))
               .reset_index().sort_values("tiv", ascending=False).head(15))
        st.markdown("**무기 모델 TOP 15 (주문 TIV)**")
        st.dataframe(w.rename(columns={"weapon": "모델", "weapon_desc": "종류", "tiv": "주문 TIV", "n": "계약", "qty": "수량"}).round(0),
                     hide_index=True, width="stretch", height=380)


# ---------------------------------------------------------------- 국가별 보기

def country_picker(df, key):
    order = df.groupby("target_iso3")["value"].sum().sort_values(ascending=False).index.tolist()
    return st.selectbox("대상국", order, format_func=COUNTRIES.get, key=key)


def draw_country_compare(df, M, country, how):
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
    _layout(fig, height=360, hovermode="x unified",
            title=dict(text=ctitle("대상국별 비교", f"{how} · {name} 강조"), font=dict(size=16, color="#e5eaf3"), x=0),
            legend=dict(orientation="h", y=-0.25, yanchor="top", x=0, font=dict(size=13)))
    _axes(fig)
    fig.update_xaxes(tickformat=fmt, hoverformat=fmt)
    fig.update_yaxes(title_text=f"{M['value_label']} ({M['unit']})")
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


def draw_rank_country(df, M, country):
    U = M["unit"]
    one = df[df["target_iso3"] == country]
    name = COUNTRIES[country]
    total = one["value"].sum()
    st.markdown(f"**{name}** · {total:,.0f} {U} · {M['exporter_label']} {one['exporter_iso3'].nunique()}개국 · {M['obs_label']} {one['obs'].nunique()}")

    if one.empty:
        st.info("이 나라의 기록이 없습니다.")
        return
    c1, c2 = st.columns(2)
    with c1:
        hbar(one.groupby("exporter")["value"].sum(), ctitle(f"{name} {M['exporter_label']} TOP 12", f"단위 {U}"), GOLD, U)
    with c2:
        hbar(one.groupby("cat")["value"].sum(), ctitle(f"{name} {M['cat_label']}별", f"단위 {U}"), "#60a5fa", U)
    target_cat_heatmap(df, M, highlight=name, title=ctitle(f"대상국 × {M['cat_label']}", f"{name}(▶)을 맨 위에 두고 다른 나라와 비교"))
    share = df.groupby("target_name")["value"].sum().sort_values(ascending=False)
    rank = list(share.index).index(name) + 1
    st.caption(f"{name}{jo(name, '은는')} 필터 기간 전체의 {total / share.sum():.1%} ({rank}위 / {len(share)}개국).")


# ---------------------------------------------------------------- 국가쌍

def draw_pairs(df, M):
    U = M["unit"]
    fl = arms.flows(df)
    st.markdown(f"**{M['exporter_label']} → 대상국 흐름 {len(fl)}개** ({M['value_label']} 큰 순)")
    cols = {"exporter": M["exporter_label"], "target_name": "대상국", "value": f"{M['value_label']} ({U})",
            "obs": M["obs_label"], "top_cat": f"주요 {M['cat_label']}"}
    st.dataframe(fl.rename(columns=cols)[list(cols.values())].round(1), hide_index=True, width="stretch", height=420)
    top_exp = df.groupby("exporter")["value"].sum().sort_values(ascending=False).index[:10]
    h = df[df["exporter"].isin(top_exp)].pivot_table(index="target_name", columns="exporter", values="value",
                                                     aggfunc="sum", fill_value=0).reindex(columns=top_exp)
    fig = go.Figure(go.Heatmap(z=h.values, x=h.columns, y=h.index, colorscale=[[0, "#111a2e"], [1, GOLD]],
                               hovertemplate=f"%{{x}} → %{{y}}<br>%{{z:,.1f}} {U}<extra></extra>",
                               colorbar=dict(thickness=10, tickfont=dict(color="#cbd5e1"))))
    _layout(fig, height=460, title=dict(text=ctitle(f"대상국 × 상위 10개 {M['exporter_label']}", f"단위 {U} · 칸 색이 진할수록 큼"), font=dict(size=16, color="#e5eaf3"), x=0))
    st.plotly_chart(theme.adapt(fig), width="stretch", config={"displaylogo": False})


# ---------------------------------------------------------------- 페이지

def _filters(box, vertical, f, M, k, y0, y1, cats_all, targets_all, exp_opts, exp_name, months=None):
    """필터 위젯을 box 에 그린다. vertical=True 면 사이드바용으로 한 줄씩, 아니면 본문 상자에 가로로.
    months 가 있으면(월별 자료 = Comtrade) 기간을 월 단위로 고른다."""
    with box:
        if vertical:
            c1 = c2 = c3 = c4 = st
        else:
            c1, c2 = st.columns([1.2, 3])
            c3, c4 = st.columns(2)

        if months is not None:
            opts = [d.strftime("%Y-%m") for d in months]
            lo, hi = f.get("period", (f"{f['years'][0]}-01", opts[-1]))
            lo, hi = (lo if lo in opts else opts[0]), (hi if hi in opts else opts[-1])
            f["period"] = c1.select_slider("기간 (월)", options=opts, value=(lo, hi), key=f"arms_period_{k}")
            f["years"] = (int(f["period"][0][:4]), int(f["period"][1][:4]))
        else:
            f["years"] = c1.slider("기간", y0, y1, f["years"], key=f"arms_years_{k}")
        f["cats"] = c2.pills(M["cat_label"], cats_all, selection_mode="multi", default=f["cats"], key=f"arms_cats_{k}") or cats_all
        f["targets"] = c3.multiselect("대상국(수입)", targets_all, default=f["targets"], format_func=COUNTRIES.get,
                                      key=f"arms_targets_{k}", placeholder="전체") or targets_all
        f["exporters"] = c4.multiselect(f"{M['exporter_label']} (비우면 전체)", exp_opts, default=f["exporters"],
                                        format_func=exp_name.get, key=f"arms_exporters_{k}",
                                        placeholder=f"전체 {len(exp_opts)}개국")


def page(filter_box=None, on_open=None, compact=False, show_title=True):
    """filter_box·on_open 이 둘 다 없으면 본문 위 상자에 필터를 그린다.
    filter_box 가 있으면(app2 필터 모드) 그 사이드바 컨테이너에 세로로 그리고,
    on_open 만 있으면(app2 메뉴 모드) 마지막 값을 쓰고 '필터 열기' 버튼만 보여준다.
    compact=True 면 요약 카드 네 개 대신 한 줄 띠로 보여준다 (app2)."""
    if show_title:
        st.title("무기 거래 추이")
        page_sub(term("SIPRI") + " 무기 계약과 " + term("UN Comtrade") + " 군용 품목 교역으로, 중동 16개국이 어디서 무기를 사들였는지 보여 줍니다. SIPRI 값의 단위는 " + term("TIV") + "입니다.")
    source = st.segmented_control(
        "자료", ["Comtrade", "SIPRI"], default="Comtrade", key="arms_source",
        format_func=lambda s: {"Comtrade": "Comtrade · 교역액(달러) · 2002~", "SIPRI": "SIPRI · 주문 TIV · 1980~"}[s],
    ) or "Comtrade"
    M = arms.SOURCES[source]
    U = M["unit"]
    df, missing = arms.load(source)
    st.markdown(f'<div class="src-note">이 자료는? {info_icon(M["desc"])}</div>', unsafe_allow_html=True)   # 자료 설명은 말풍선

    cats_all = [c for c in M["colors"] if c in set(df["cat"])]
    targets_all = [c for c in COUNTRIES if c in set(df["target_iso3"])]
    exp_opts = df.groupby("exporter_iso3")["value"].sum().sort_values(ascending=False).index.tolist()
    exp_name = df.drop_duplicates("exporter_iso3").set_index("exporter_iso3")["exporter"].to_dict()
    y0, y1 = int(df["year"].min()), int(df["year"].max())
    k = source                                          # 자료마다 위젯 상태를 따로 둔다
    # 안 그린 위젯은 상태가 지워지므로 값을 사전에 따로 보관한다 (사이드바 필터 모드 ↔ 메뉴 모드 오갈 때)
    f = st.session_state.setdefault(f"arms_f_{k}", {"years": (max(y0, M["default_start"]), y1), "cats": cats_all,
                                                    "targets": targets_all, "exporters": []})
    months = pd.date_range(df["date"].min(), df["date"].max(), freq="MS") if source == "Comtrade" else None   # 월별 자료

    if filter_box is not None:
        _filters(filter_box, True, f, M, k, y0, y1, cats_all, targets_all, exp_opts, exp_name, months)
        # 접힌 필터 아래 '현재 조건' 한 줄 (리뷰 2순위)
        st.sidebar.markdown(f'<div class="side-note">현재 · {f["years"][0]}–{f["years"][1]} · {M["cat_label"]} {len(f["cats"])}/{len(cats_all)} · '
                            f'대상국 {len(f["targets"])}곳 · {M["exporter_label"]} {"전체" if not f["exporters"] else str(len(f["exporters"])) + "곳"}</div>',
                            unsafe_allow_html=True)
        
    elif on_open is None:
        _filters(st.container(border=True), False, f, M, k, y0, y1, cats_all, targets_all, exp_opts, exp_name, months)

    else:
        a, b = st.columns([5, 1])
        a.caption(f"현재 조건 · {f['years'][0]}–{f['years'][1]} · {M['cat_label']} {len(f['cats'])}/{len(cats_all)} · "
                  f"대상국 {len(f['targets'])}개 · {M['exporter_label']} {'전체' if not f['exporters'] else str(len(f['exporters'])) + '개'}")
        b.button("필터 열기 ▸", on_click=on_open, key=f"arms_open_{k}", use_container_width=True)
    years, cats, targets, exporters = f["years"], f["cats"], f["targets"], f["exporters"]

    if source == "Comtrade" and years[0] < arms.FULL_START_YEAR:
        st.warning(f"{arms.FULL_START_YEAR}년 이전은 신고 수출국이 연 8~11개국뿐이라(2010년부터 41개국 이상) 금액이 실제보다 훨씬 작게 잡힙니다. "
                   "시기 비교에는 쓰지 마세요.")
    sub = arms.apply_filters(df, years, cats, targets, exporters)
    per_txt = f"{years[0]}–{years[1]}"

    if months is not None and "period" in f:           # 월 단위로 고른 기간이면 달까지 자른다
        m0, m1 = pd.Timestamp(f["period"][0] + "-01"), pd.Timestamp(f["period"][1] + "-01")
        sub = sub[(sub["date"] >= m0) & (sub["date"] <= m1)]
        per_txt = f"{f['period'][0]}–{f['period'][1]}"

    if sub.empty:
        st.warning("조건에 맞는 기록이 없습니다.")
        return

    total = sub["value"].sum()
    top_exp = sub.groupby("exporter")["value"].sum().sort_values(ascending=False)
    top_cat = sub.groupby("cat")["value"].sum().sort_values(ascending=False)
    items = [(f"{M['value_label']} 합계", f"{total:,.0f}", f"{U} · {per_txt}", "blue"),
             (f"최대 {M['exporter_label']}", top_exp.index[0], f"{top_exp.iloc[0] / total:.0%} · {top_exp.iloc[0]:,.0f} {U}", "red"),
             (f"최대 {M['cat_label']}", top_cat.index[0], f"{top_cat.iloc[0] / total:.0%} · {top_cat.iloc[0]:,.0f} {U}", "")]
    
    if source == "Comtrade":
        if "period" in f:                               # 고른 달 수 (파일 끝보다 뒤는 셈에서 뺀다)
            m_end = min(pd.Timestamp(f["period"][1] + "-01"), df["date"].max())
            span = len(pd.date_range(pd.Timestamp(f["period"][0] + "-01"), m_end, freq="MS"))
        else:
            last_month = int(df.loc[df["year"] == y1, "date"].dt.month.max())
            span = (years[1] - years[0] + 1) * 12 - ((12 - last_month) if years[1] == y1 else 0)
        items.append(("관측 월", f"{sub['period'].nunique()}/{span}",
                      f"수출국 {sub['exporter_iso3'].nunique()}개국 · 흐름 {len(arms.flows(sub))}개", ""))
        
    else:
        items.append(("계약", f"{sub['obs'].nunique():,}건",
                      f"공급국 {sub['exporter_iso3'].nunique()}개국 · 흐름 {len(arms.flows(sub))}개", ""))
        
    if compact:
        st.markdown(strip(items), unsafe_allow_html=True)
        
    else:
        for col, (label, value, sub_, tone) in zip(st.columns(4), items):
            col.markdown(card(label, value, sub_, tone), unsafe_allow_html=True)

    t_map, t_trend, t_rank, t_pair = st.tabs(["지도", "추이", "순위", "국가쌍"])
    with t_map:
        m1, m2 = st.columns([1.5, 2])
        arc = f"{M['role_label']} 흐름(호)"
        overlay = m1.segmented_control("표시", [arc, "대상국별 수입"], default=arc, key=f"arms_overlay_{k}") or arc
        top_n = m2.slider(f"표시할 흐름 수 ({M['value_label']} 큰 순)", 5, 100, 40, step=5, key=f"arms_topn_{k}")
        draw_map(sub, M, overlay, top_n)
        if missing:
            st.caption(f"좌표가 없어 지도에 못 그린 {M['exporter_label']}: {', '.join(missing)}")
    with t_trend:
        a, b, c = st.columns([1.2, 1.4, 1.4])
        scope = a.segmented_control("범위", ["전체", "국가별"], default="전체", key=f"arms_trend_scope_{k}") or "전체"
        how = b.radio("집계", M["periods"], index=M["periods"].index(M["default_period"]), horizontal=True, key=f"arms_how_{k}")
        if scope == "전체":
            by = c.radio("쌓기 기준", [M["cat_label"], "대상국", M["exporter_label"]], horizontal=True, key=f"arms_by_{k}")
            draw_trend(sub, M, how, by)
        else:
            by = c.radio("쌓기 기준", [M["cat_label"], M["exporter_label"]], horizontal=True, key=f"arms_by_country_{k}")
            country = country_picker(sub, f"arms_trend_country_{k}")
            one = sub[sub["target_iso3"] == country]
            st.markdown(f"**{COUNTRIES[country]}** · {one['value'].sum():,.0f} {U} · {M['obs_label']} {one['obs'].nunique()}")
            draw_trend(one, M, how, by)
            draw_country_compare(sub, M, country, how)
    with t_rank:
        scope = st.segmented_control("범위", ["전체", "국가별"], default="전체", key=f"arms_rank_scope_{k}") or "전체"
        if scope == "전체":
            draw_rank(sub, M)
        else:
            draw_rank_country(sub, M, country_picker(sub, f"arms_rank_country_{k}"))
    with t_pair:
        draw_pairs(sub, M)
    st.markdown(f'<div class="src-note">읽을 때 주의 {info_icon(M["foot"] + " 지도 위치는 나라 중심점이며 실제 경로가 아닙니다.")}</div>',
                unsafe_allow_html=True)
