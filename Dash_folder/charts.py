from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

# 공통 색상
BG = "rgba(0,0,0,0)"
GRID = "rgba(148,163,184,0.15)"
TEXT = "#cbd5e1"
MUTED = "#8b98ad"

INTENSITY_COLORS = ["#374151", "#f6d28b", "#f0a24a", "#ef4444", "#7f1d1d"]  # 없음~매우높음
ROLE_COLORS = {"conflict": "#ef4444", "related": "#3b82f6", "mediator": "#22c55e"}
RELATION_STYLE = {
    "hostile": {"color": "#ef4444", "dash": "solid"},
    "friendly": {"color": "#3b82f6", "dash": "solid"},
    "neutral": {"color": "#94a3b8", "dash": "dash"},
}
SERIES_COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#f59e0b", "#94a3b8", "#a78bfa", "#ec4899"]

FONT = dict(family="Pretendard, 'Noto Sans KR', sans-serif", color=TEXT, size=12)


def _base_layout(**kwargs) -> dict:
    layout = dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=FONT,
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3")),
    )
    layout.update(kwargs)
    return layout


# 세계 분쟁 현황 지도
def world_map(df: pd.DataFrame, markers: pd.DataFrame, height: int = 420) -> go.Figure:
    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            locations=df["iso3"],
            z=df["intensity"],
            zmin=0,
            zmax=4,
            colorscale=[[i / 4, c] for i, c in enumerate(INTENSITY_COLORS)],
            text=df["country"],
            customdata=df[["events", "cause"]],
            hovertemplate="<b>%{text}</b><br>이벤트 수: %{customdata[0]:,}<br>원인: %{customdata[1]}<extra></extra>",
            marker_line_color="#1e293b",
            marker_line_width=0.5,
            showscale=False,
        )
    )

    if markers is not None and not markers.empty:
        fig.add_trace(
            go.Scattergeo(
                lat=markers["lat"],
                lon=markers["lon"],
                text=markers["name"],
                customdata=markers["causes"],
                mode="markers+text",
                textposition="top center",
                textfont=dict(color="#ffffff", size=11),
                marker=dict(size=13, color="#ef4444", line=dict(color="#ffffff", width=2), opacity=0.95),
                hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
            )
        )

    fig.update_geos(
        showframe=False,
        showcoastlines=False,
        showcountries=True,
        countrycolor="#1e293b",
        showland=True,
        landcolor="#243247",
        showocean=True,
        oceancolor="#0f1a2e",
        showlakes=False,
        bgcolor=BG,
        projection_type="natural earth",
        lataxis_range=[-58, 85],
    )
    fig.update_layout(_base_layout(height=height, margin=dict(l=0, r=0, t=0, b=0)))
    return fig


# 분쟁 원인별 국가 간 관계 네트워크
def network_graph(nodes: list[dict], edges: list[dict], height: int = 360) -> go.Figure:
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"], role=n["role"])
    for e in edges:
        G.add_edge(e["source"], e["target"], relation=e["relation"])

    pos = nx.spring_layout(G, seed=7, k=1.4)

    fig = go.Figure()

    # 관계 유형별로 엣지 트레이스 분리 (범례용)
    labels = {"hostile": "적대 관계", "friendly": "우호 관계", "neutral": "중립/기타"}
    for rel, style in RELATION_STYLE.items():
        xs, ys = [], []
        for u, v, d in G.edges(data=True):
            if d["relation"] != rel:
                continue
            xs += [pos[u][0], pos[v][0], None]
            ys += [pos[u][1], pos[v][1], None]
        fig.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="lines",
                line=dict(color=style["color"], width=2, dash=style["dash"]),
                name=labels[rel], hoverinfo="skip",
            )
        )

    role_labels = {"conflict": "분쟁국", "related": "관련국", "mediator": "중재국"}
    for role, color in ROLE_COLORS.items():
        ids = [n for n, d in G.nodes(data=True) if d["role"] == role]
        if not ids:
            continue
        size = 34 if role == "conflict" else 24
        fig.add_trace(
            go.Scatter(
                x=[pos[i][0] for i in ids],
                y=[pos[i][1] for i in ids],
                mode="markers+text",
                text=ids,
                textposition="bottom center",
                textfont=dict(color="#e5eaf3", size=12),
                marker=dict(size=size, color=color, line=dict(color="#ffffff", width=2)),
                name=role_labels[role],
                hovertemplate="<b>%{text}</b><extra>" + role_labels[role] + "</extra>",
            )
        )

    fig.update_layout(
        _base_layout(
            height=height,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            legend=dict(
                orientation="v", x=1.02, y=1, xanchor="left",
                bgcolor="rgba(17,26,46,0.8)", bordercolor="#1f2b44", borderwidth=1,
            ),
            margin=dict(l=10, r=130, t=10, b=10),
        )
    )
    return fig


# 분쟁 이벤트 추이 (GDELT)
def events_line(df: pd.DataFrame, height: int = 180) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=df["date"], y=df["events"], mode="lines",
            line=dict(color="#ef4444", width=2),
            fill="tozeroy", fillcolor="rgba(239,68,68,0.15)",
            hovertemplate="%{x|%Y-%m}<br>이벤트 수: %{y:,}<extra></extra>",
        )
    )
    fig.update_layout(
        _base_layout(
            height=height,
            xaxis=dict(showgrid=False, tickfont=dict(color=MUTED)),
            yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED), tickformat=","),
            hovermode="x unified",
            margin=dict(l=10, r=10, t=10, b=10),
        )
    )
    return fig


# 관련 국가의 무기 거래량 추이 (SIPRI)
def arms_trade_lines(df: pd.DataFrame, height: int = 220) -> go.Figure:
    fig = go.Figure()
    for i, (country, g) in enumerate(df.groupby("country", sort=False)):
        color = SERIES_COLORS[i % len(SERIES_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=g["year"], y=g["tiv"], mode="lines+markers", name=country,
                line=dict(color=color, width=2),
                marker=dict(size=7, color=color, line=dict(color="#0b1220", width=1.5)),
                hovertemplate="%{x}년 · " + country + ": %{y:.1f}B<extra></extra>",
            )
        )
    fig.update_layout(
        _base_layout(
            height=height,
            xaxis=dict(showgrid=False, tickfont=dict(color=MUTED), dtick=1),
            yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED), title=dict(text="(billion TIV)", font=dict(color=MUTED, size=11))),
            hovermode="x unified",
            legend=dict(orientation="v", x=1.02, y=1, xanchor="left", bgcolor="rgba(17,26,46,0.8)", bordercolor="#1f2b44", borderwidth=1),
            margin=dict(l=10, r=110, t=10, b=10),
        )
    )
    return fig


# 스파크라인 (주요 분쟁 사례 카드용, SVG 문자열)
def sparkline_svg(values: list[float], width: int = 90, height: int = 32, color: str = "#ef4444") -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = i / (n - 1) * (width - 2) + 1 if n > 1 else width / 2
        y = height - 2 - (v - lo) / span * (height - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    path = " ".join(pts)
    area = f"M1,{height-1} L{path.replace(' ', ' L')} L{width-1},{height-1} Z"
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<path d="{area}" fill="{color}" opacity="0.18"/>'
        f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
        f"</svg>"
    )
