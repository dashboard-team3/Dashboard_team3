import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

from sources import surge as A      # 원본: import analysis as A
from core import theme           # 그래프 글꼴 · 밝은 테마 색 (theme.adapt)
from core.ui import ctitle, tabbar, INFO_SVG, info_icon

LIM = 0.3          # 흔히 «약한 상관» 의 경계로 쓰는 값. 통계적 유의성 기준이 아니다 (2026-10-01)
INK, RED, BLUE, GOLD, MUTE, GRID = "#e5eaf3", "#f87171", "#60a5fa", "#f5c542", "#8b98ad", "#16233c"
BG, CARD, LINE = "#0b1220", "#111a2e", "#1f2b44"

# 원본 CSS 에서 페이지 전체를 바꾸던 4줄(.stApp 배경 · .block-container 폭 · ⋮ 메뉴 숨김 · h1~h3 색)은 뺐다.
CSS = f"""
  .sec {{display:flex; gap:.9rem; align-items:center; background:{CARD};
         border-left:5px solid {RED}; border-radius:0 10px 10px 0;
         padding:.7rem 1.1rem; margin:1.6rem 0 .9rem 0;}}
  .sec-no {{font-family:Cambria,serif; font-size:28px; font-weight:700; color:{RED};
            min-width:2.6rem; flex:0 0 auto; white-space:nowrap; text-align:center;}}
  .sec-t {{font-size:19px; font-weight:700; color:{INK};}}
  .sec-s {{font-size:16px; color:{MUTE}; margin-top:.2rem; line-height:1.55;}}
  /* 그 쪽에서 말하려는 것 한 줄 — 맨 위에 크게 둔다 */
  .key {{background:{CARD}; border:1px solid {LINE}; border-radius:14px;
         padding:1.3rem 1.6rem; margin:.2rem 0 1.4rem 0;}}
  .key .n {{font-size:14px; font-weight:700; letter-spacing:.18em; margin-bottom:.55rem;}}
  .key .t {{font-size:19px; font-weight:800; color:#fff; line-height:1.5;
            word-break:keep-all; overflow-wrap:anywhere;}}
  .key .t em {{font-style:normal; padding:0 .12em;}}
  .key .s {{font-size:16px; color:{MUTE}; margin-top:.7rem; line-height:1.7;}}
  .key .s b {{color:#dbe3f0;}}
  .lead {{background:{CARD}; border:1px solid {LINE}; border-left:5px solid {GOLD};
          border-radius:0 12px 12px 0; padding:1.1rem 1.3rem; margin:.6rem 0 1rem 0;}}
  .lead b {{color:#fff;}}
  .lead .big {{font-size:19px; font-weight:700; color:{INK}; line-height:1.55;}}
  .lead .sub {{font-size:16px; color:{MUTE}; margin-top:.5rem; line-height:1.6;}}
  .note {{background:{CARD}; border:1px solid {LINE}; border-radius:12px;
          padding:.8rem 1.1rem; margin:.5rem 0; font-size:16px; color:#cbd5e1; line-height:1.65;}}
  .note b {{color:#fff;}}
  .note.red {{border-left:4px solid {RED};}} .note.blue {{border-left:4px solid {BLUE};}}
  .note.gold {{border-left:4px solid {GOLD};}}
  [data-testid="stDataFrame"] {{border:1px solid {LINE}; border-radius:10px;}}

  /* 결론 쪽 3단 흐름 — 착시 → 상반된 두 현상 → 시사점 */
  .flow {{display:flex; align-items:stretch; gap:.7rem; margin:.4rem 0 1.2rem 0;}}
    .fc {{
        flex: 1;
        min-width: 0;
        background: {CARD};
        border: 1px solid {LINE};
        border-radius: 14px;
        padding: 1.1rem 1.2rem;
        display: flex;
        flex-direction: column;
    }}

    /* 흐름의 마지막 카드만 투명 배경 적용 */
    .flow > .fc:last-child {{
        position: relative;
        background: transparent;
        border: none;
    }}

    /* 마지막 카드만 보라색·청록색 그라데이션 테두리 */
    .flow > .fc:last-child::before {{
        content: "";
        position: absolute;
        inset: 0;
        padding: 1.5px;
        border-radius: inherit;
        pointer-events: none;
        background: linear-gradient(
            135deg,
            var(--color-main-480),
            var(--color-accent-cyan)
        );
        -webkit-mask:
            linear-gradient(#fff 0 0) content-box,
            linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
    }}
  .fn {{font-size:14px; font-weight:700; color:{MUTE}; margin-bottom:.8rem;
        letter-spacing:.04em;}}
  .fbig {{font-family:Cambria,serif; font-size:28px; font-weight:700; line-height:1;
          color:{MUTE}; text-align:center; margin:.5rem 0 .3rem 0;}}
  .ft {{font-size:19px; font-weight:700; color:{INK}; text-align:center;}}
  .fs {{font-size:16px; color:{MUTE}; line-height:1.65; margin-top:.5rem;
        word-break:keep-all;}}
  .farr {{display:flex; align-items:center; justify-content:center; color:{GOLD};
          font-size:28px; font-weight:700; flex:0 0 auto; width:1.4rem; opacity:.75;}}
  .fbox {{background: color-mix(in srgb, var(--color-main-dark-820) 35%, transparent); border: 1px solid var(--color-main-dark-820); border-radius:10px; padding:.75rem .9rem; margin-bottom:.55rem;}}
  .fbox .tag {{font-size:14px; font-weight:700; margin-bottom:.25rem;}}
  .fbox .h {{font-size:16px; font-weight:700; color:{INK};}}
  .fbox .d {{font-size:14px; color:{MUTE}; margin-top:.25rem; line-height:1.55;
             word-break:keep-all;}}
  .fc.dark .ft {{color:{GOLD}; font-size:19px; margin-top:.4rem;}}
  @media (max-width:900px) {{
    .flow {{flex-direction:column;}} .farr {{display:none;}}
  }}


  /* 선택한 사례 한 건의 «그 해 무슨 일이 있었나» 칸 (2026-10-01) */
  .case-x {{background:{CARD}; border:1px solid {LINE}; border-radius:14px;
            padding:1.1rem 1.3rem; height:100%;}}
  .case-h {{font-size:19px; font-weight:800; color:#fff; margin-bottom:.8rem;}}
  .case-p span {{display:flex; align-items:center; gap:.55rem; font-size:16px;
                 color:{INK}; margin-bottom:.35rem;}}
  .case-p i {{font-style:normal; font-size:12px; font-weight:700; color:{BG};
              background:{MUTE}; border-radius:50%; width:1.2rem; height:1.2rem;
              display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto;}}
  .case-e {{margin-top:.8rem; display:inline-block; font-size:14px; font-weight:700;
            color:{BG}; background:{GOLD}; border-radius:6px; padding:.15rem .5rem;}}
  .case-w {{margin-top:.8rem; font-size:16px; color:#cbd5e1; line-height:1.65;
            word-break:keep-all;}}
  .case-w span {{display:block; font-size:13px; color:{MUTE}; margin-top:.35rem;}}
  .case-n {{margin-top:.9rem; padding-top:.8rem; border-top:1px solid {LINE};
            font-size:13px; color:{MUTE}; line-height:1.6; word-break:keep-all;}}
    /* 제목은 왼쪽, 수치는 오른쪽, 설명은 다음 줄 */
    .case-r {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: .3rem 1rem;
        font-size: 16px;
        padding-bottom: .8rem;
        border-bottom: 1px solid {LINE};
    }}

    .case-r b {{
        grid-column: 2;
        grid-row: 1 / 3;
        font-size: 32px;
        text-align: right;
        color: {GOLD}
    }}

    .case-r span {{
        grid-column: 1;
        font-size: 14px;
    }}    
    .case-p em {{
        display: block;
        font-style: normal;
        font-size: 15px;
        font-weight: 700;
        color: {MUTE};
        margin: .7rem 0;
    }}            
    /* 상대국별 배경 카드 */
    .case-peer {{
        display: flex;
        align-items: center;
        gap: .65rem;
        margin-bottom: .5rem;
        padding: .75rem .85rem;
        background: color-mix(
            in srgb, var(--color-main-dark-820) 35%, transparent
        );
        border: 1px solid var(--color-main-dark-820);
        border-radius: 12px;
    }}

    .case-peer-name {{
        flex: 1;
        min-width: 0;
        font-size: 16px;
        font-weight: 700;
        color: var(--color-main-40);
        word-break: keep-all;
    }}

    /* 리스크 0~1 기준의 작은 막대 */
    .case-peer-track {{
        flex: 0 1 90px;
        min-width: 30px;
        height: 7px;
        overflow: hidden;
        background: var(--color-main-dark-740);
        border-radius: 999px;
    }}

    .case-peer-fill {{
        height: 100%;
        background: {RED};
        border-radius: inherit;
    }}

    .case-peer b {{
        flex: 0 0 3.5ch;
        margin-left: 0;
        text-align: right;
        font-size: 15px;
        color: {RED};
        font-variant-numeric: tabular-nums;
    }}
"""

# 중동 전체 결과 새 레이아웃 (2026-10-01) — 어두운 테마 기본값. 밝은 테마는 style_light.css «종합 분석 새 레이아웃»
OV_CSS = """
         border-radius:0 12px 12px 0; padding:.9rem 1.2rem; margin:.2rem 0 1.2rem 0;}
            display:flex; align-items:center; justify-content:center; flex:0 0 auto;}
  .ov-key {background: linear-gradient(135deg,
        color-mix(in srgb, var(--color-main-dark-410) 15%, transparent) 0%,
        color-mix(in srgb, var(--color-main-dark-820) 45%, transparent) 100%); border:1px solid var(--color-main-dark-740); border-radius:14px;
        padding:1.2rem 1.5rem; margin:.4rem 0 1.4rem 0;}
  .ov-kick {display:flex; align-items:center; gap:.6rem; margin-bottom:.5rem;}
  .ov-badge {font-size:12px; font-weight:700; color: var(--color-main-350); background: color-mix(in srgb, var(--color-main-dark-550) 15%, transparent); border:1px solid var(--color-main-570); border-radius:5px; padding:.1rem .45rem;}
  .ov-mono {font-family:"JetBrains Mono", monospace; font-size:12px; color:#8b98ad;}
  .ov-big {font-size:24px; font-weight:800; color:#ffffff; line-height:1.45; word-break:keep-all;}
  .ov-body {font-size:16px; color:#aab4c5; line-height:1.75; margin-top:.6rem; word-break:keep-all;}
  .ov-num {font-family:"JetBrains Mono", monospace; color:#e5eaf3;}
  .ov-pos-t {color:#f87171;} .ov-neg-t {color:#60a5fa;}
  .ov-cb-h {display:flex; justify-content:space-between; font-size:13px; font-weight:600; color:#8b98ad; padding:2px 4px 0;}
  .ov-cb-h span:last-child {font-family:"JetBrains Mono", monospace; font-weight:500;}
  .ov-head {display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; margin-bottom:.8rem;}
  .ov-t {font-size:19px; font-weight:800; color:#e5eaf3;}
  .ov-no {color:var(--color-main-350); font-family:"JetBrains Mono", monospace; margin-right:.2rem;}
  .ov-s {font-size:14px; color:#8b98ad; margin-top:.25rem; line-height:1.6;}
  .ov-leg {display:flex; gap:.9rem; font-size:13px; color:#cbd5e1; white-space:nowrap;}
  .ov-leg.l {margin-top:.5rem;}
  .ov-leg i {display:inline-block; width:10px; height:10px; margin-right:.35rem; vertical-align:-1px;}
  .ov-leg i.sq.red, .ov-leg i.dot.red {background:#f87171;} .ov-leg i.sq.blue, .ov-leg i.dot.blue {background:#60a5fa;}
  .ov-leg i.dot {border-radius:50%;}
  .ov-note {border:1px solid var(--color-main-dark-820); border-radius:12px; padding:1rem 1.1rem; height:100%;}
  .ov-note-t {font-size:17px; font-weight:800; color:#e5eaf3; margin-bottom:.6rem;}
  .ov-note-b {font-size:15px; color:#aab4c5; line-height:1.75; word-break:keep-all;}
  .ov-info {margin-top:1.4rem; background: color-mix(in srgb, var(--color-main-870) 30%, transparent); border:1px solid var(--color-main-dark-740); border-radius:8px; padding:.7rem .85rem; font-size:13px; color:#aab4c5; line-height:1.65;}
  .ov-info-t {font-size:13px; font-weight:700; color:var(--color-main-350); margin-bottom:.3rem;}
  .ov-info b {color:#e5eaf3;}
  .ov-chip {display:inline-block; margin-top:.5rem; font-family:"JetBrains Mono", monospace; font-size:12px; color:#8b98ad;
            border:1px solid var(--color-main-dark-820); border-radius:6px; padding:.2rem .55rem; float:right;}
  .ov-tbl {margin-top:.9rem; border-top:1px solid var(--color-main-dark-820);}
  .ov-row {display:grid; grid-template-columns:minmax(150px, 1.2fr) 1.6fr 2px 1.6fr; align-items:center; gap:0 .8rem; padding:.42rem 0;}
  .ov-row.ov-h {font-family:"JetBrains Mono", monospace; font-size:12px; color:#8b98ad; padding:.6rem 0 .3rem;}
  .ov-row.ov-h .ov-neg {text-align:right;} .ov-row.ov-h .ov-mid {background:none; text-align:center; overflow:visible; font-weight:700;}
  .ov-name {font-size:15px; font-weight:600; color:#e5eaf3; display:flex; align-items:center; gap:.5rem;}
  .ov-dot {width:8px; height:8px; border-radius:50%; flex:0 0 auto; opacity:.5;}
  .ov-dot.pos {background:#f87171;} .ov-dot.neg {background:#60a5fa;} .ov-dot.strong {opacity:1;}
  .ov-neg, .ov-pos {display:flex; align-items:center; gap:.5rem; height:24px;}
  .ov-neg {flex-direction:row-reverse;}
  .ov-mid {width:2px; height:20px; background:var(--color-main-dark-740);}
  .ov-bar {display:block; height:22px; opacity:.45; flex:0 0 auto;}
  .ov-bar.pos {background:#f87171;} .ov-bar.neg {background:#60a5fa;} .ov-bar.strong {opacity:1;}
  .ov-v {font-family:"JetBrains Mono", monospace; font-size:13px; white-space:nowrap;}
  .ov-v.pos {color:#fca5a5;} .ov-v.neg {color:#93c5fd;}
  @media (max-width:900px) { .ov-head {flex-direction:column;} }
  /* (2026-10-02) 네 쪽 디자인 통일: 흐름 칸 · 사례 칸 = ov-note 처럼 테두리만, 칸 안 작은 상자 · 글 상자 = ov-info 처럼 */
  .fc {background:transparent; border:1px solid var(--color-main-dark-820); border-radius:12px;}
  .fc.dark {background:var(--color-main-870); border-color:var(--color-main-dark-820);}
  .case-x {background:transparent; border-color:var(--color-main-dark-820); border-radius:12px;}
  .note {background:var(--color-main-870); border-color:transparent;}
"""

CFG = {"displayModeBar": False}
SCOPE = ".st-key-surge_app"             # page() 가 이 이름표(key)를 단 상자 안에 그린다

# gif 파일 가져오기 용
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"

@st.cache_data
def _transparent_icon(filename):
    """흰 배경 GIF를 투명 배경의 흰색 애니메이션 아이콘으로 변환."""
    frames = []
    durations = []

    with Image.open(ASSETS_DIR / filename) as source:
        loop = source.info.get("loop", 0)
        default_duration = source.info.get("duration", 170)

        for frame in ImageSequence.Iterator(source):
            # 검은 부분은 불투명하게, 흰 부분은 투명하게 처리
            gray = ImageOps.grayscale(frame.convert("RGB"))
            alpha = ImageOps.invert(gray)

            # 아이콘 색은 흰색으로 설정하고 가장자리 투명도 유지
            icon = Image.new("RGBA", frame.size, "white")
            icon.putalpha(alpha)

            frames.append(icon)
            durations.append(
                frame.info.get("duration", default_duration)
            )

    # 반투명 가장자리와 애니메이션을 지원하는 WebP로 변환
    output = BytesIO()
    frames[0].save(
        output,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=loop,
        lossless=True,
    )

    return base64.b64encode(output.getvalue()).decode("ascii")


def gif_icon(filename, size=40):
    data = _transparent_icon(filename)

    return (
        f'<img class="flow-gif" '
        f'src="data:image/webp;base64,{data}" '
        f'width="{size}" height="{size}" alt="">'
    )

def _scoped_css(css):
    """규칙마다 선택자 앞에 SCOPE 를 붙인다 (@media 안쪽 규칙도). 대시보드의 같은 이름 .sec · .note 와 섞이지 않게."""
    import re
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)

    def rules(body):
        out = []
        for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
            sels = [f"{SCOPE} {x.strip()}" for x in m.group(1).split(",") if x.strip()]
            out.append(", ".join(sels) + " {" + m.group(2) + "}")
        return "\n".join(out)

    media = re.compile(r"(@media[^{]+)\{((?:[^{}]*\{[^{}]*\})*)\s*\}")
    parts = [f"{m.group(1)} {{ {rules(m.group(2))} }}" for m in media.finditer(css)]
    return rules(media.sub("", css)) + "\n" + "\n".join(parts)


def sec(no, title, sub, color=RED):
    st.markdown(f'<div class="sec" style="border-left-color:{color}">'
                f'<div class="sec-no" style="color:{color}">{no}</div><div>'
                f'<div class="sec-t">{title}</div><div class="sec-s">{sub}</div></div></div>',
                unsafe_allow_html=True)


def note(text, tone=""):
    st.markdown(f'<div class="note {tone}">{text}</div>', unsafe_allow_html=True)


def key(kicker, big, sub, color=RED):
    """그 쪽의 결론을 맨 위에 크게. 아래 그림은 이 문장의 근거다.
    (2026-10-02) «중동 전체 결과» 의 핵심 분석 상자(ov-key)와 같은 모양으로 — 네 쪽 디자인 통일."""
    st.markdown(f'<div class="ov-key"><div class="ov-kick"><span class="ov-badge">{kicker}</span></div>'
                f'<div class="ov-big">{big}</div><div class="ov-body">{sub}</div></div>',
                unsafe_allow_html=True)


def sec_card(no, title, sub):
    """(2026-10-02) 묶음 하나 = 테두리 카드 + «번호 제목 / 작은 줄» 머리글 («중동 전체 결과» 의 01 카드와 같은 모양).
    with sec_card(...): 안에 그 묶음 내용을 그린다."""
    box = st.container(border=True, key=f"ov_sec_{no}")
    box.markdown(f'<div class="ov-head"><div><div class="ov-t"><span class="ov-no">{no}</span> {title}</div>'
                 f'<div class="ov-s">{sub}</div></div></div>', unsafe_allow_html=True)
    return box


def _ann(x, y, text, size, color):
    """그래프 위에 글자 하나 — plotly 주석(annotation) 한 개를 만든다."""
    return dict(x=x, y=y, xref="paper", yref="paper", xanchor="left",
                showarrow=False, text=text, font=dict(size=size, color=color))


def _cell_box(i, cols, nrow):
    """칸 하나가 차지할 자리를 계산한다. plotly 는 0~1 비율(domain)로 위치를 받는다.

        x0            x0 + 너비
        ├─────────────┤
        │ 나라 · 0년  │  ← top − 높이×0.03    제목
        │ A형  +1.64  │  ← top − 높이×0.115   부제
        │  ┌────────┐ │  ← top − 높이×0.20    그래프 위
        │  │ 막대   │ │
        │  └────────┘ │  ← top − 높이×0.62    그래프 아래 (남는 자리는 x축 글자)
        └─────────────┘

    돌려주는 값: (가로 범위, 세로 범위, 제목 x, 제목 y, 부제 y)
    """
    w = 0.96 / cols                      # 칸 하나의 가로 몫
    h = 1.0 / nrow                       # 칸 하나의 세로 몫
    x0 = 0.02 + (i % cols) * w           # 이 칸의 왼쪽 끝
    top = 1.0 - (i // cols) * h          # 이 칸의 위쪽 끝
    # 오른쪽 20%는 «다음 칸과의 사이». 칸이 하나뿐이면 옆 칸이 없으므로 가로·세로를 다 쓴다 (2026-10-01)
    one = cols == 1
    gap = 1.0 if one else 0.80
    y_lo, y_hi = (0.80, 0.18) if one else (0.62, 0.20)   # 아래는 x축 글자 자리
    return ([x0, x0 + w * gap],
            [top - h * y_lo, top - h * y_hi],
            x0 - 0.012, top - h * 0.03, top - h * 0.115)


def _bar_colors(r, after):
    """막대 색 — 0년은 노랑, 그 앞은 회색, 그 뒤는 after 색."""
    return [GOLD if y == r["year"] else (MUTE if y < r["year"] else after) for y in r["years"]]


def timeline(rows, key="up_timeline", color_of=None, text_of=None):
    """0년 타임라인 (2026-10-01): x = 해 · y = 나라 · 색 = 변화 유형 · 점 크기 = 증가폭.

    사례가 나라×연도라 지도로는 한 나라의 여러 해를 가릴 수 없다. 시간 축으로 깔면
    18건이 한 화면에 다 남으면서 «시기가 뭉치는 것» 까지 보인다.
    점을 고르면 그 번호를 돌려준다 (아래 사례 카드가 그것을 그린다)."""
    d = pd.DataFrame(rows)
    order = d.groupby("ko")["year"].min().sort_values(ascending=False).index.tolist()
    col = color_of or (lambda r: A.SHAPE_COLOR[r["shape"]])
    txt = text_of or (lambda r: r["shape"])
    fig = go.Figure(go.Scatter(
        x=[r["year"] for r in rows], y=[r["ko"] for r in rows],
        mode="markers+text", text=[txt(r) for r in rows], textposition="middle center",
        textfont=dict(size=14, color="#ffffff", family="Malgun Gothic, sans-serif"),
        marker=dict(size=[24 + 13 * (abs(r["diff"]) - 1.0) for r in rows],
                    color=[col(r) for r in rows], line=dict(width=1.6, color=BG)),
        customdata=[[r["ko"], r["year"], A.SHAPES[r["shape"]][0], r["diff"]] for r in rows],
        hovertemplate="<b>%{customdata[0]} · %{customdata[1]}년</b><br>%{customdata[2]}"
                      "<br>표준화 주문 규모 변화 %{customdata[3]:+.2f} (표준편차 단위)<extra></extra>", showlegend=False))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", 
                      height=70 + 44 * len(order),
                      font=dict(color=INK, 
                                size=13, 
                                family="Malgun Gothic, sans-serif"
                                ),
                      margin=dict(l=10, r=20, t=16, b=10), 
                      clickmode="event+select",
                      xaxis=dict(gridcolor=GRID, 
                                 zeroline=False, 
                                 dtick=5, 
                                 tickformat="d",
                                 range=[min(r["year"] for r in rows) - 2, max(r["year"] for r in rows) + 2]
                                 ),
                      yaxis=dict(categoryorder="array", 
                                 categoryarray=order, 
                                 gridcolor=GRID, 
                                 zeroline=False
                                 )
                    )
    ev = st.plotly_chart(theme.adapt(fig), width="stretch", config=CFG, on_select="rerun", key=key)
    pts = (ev or {}).get("selection", {}).get("points", []) if isinstance(ev, dict) else []
    return pts[0].get("point_index") if pts else None


def lag_buttons(ks, key="corr_lag"):
    """시차(같은 해·1·2·3년 뒤) 고르기 단추 (2026-10-01).

    고른 시차는 위 그래프의 금색 강조 상자와 아래 국가별 그래프가 함께 따라간다 —
    «왜 하필 1년 뒤인가» 라는 의문이 생기지 않게 네 시점을 모두 열어 둔다."""
    cur = st.session_state.get(key, 1)
    cols = st.columns([1, 1, 1, 1, 4], gap="small", vertical_alignment="center")
    for i, name in enumerate(ks):
        with cols[i]:
            with st.container(key=f"lagbtn-{i}"):
                if st.button(name, key=f"btn_{key}_{i}", width="stretch",
                             type="primary" if i == cur else "secondary",
                             help=f"리스크 기준 연도와 «{name}» 무기 수입의 상관계수"):
                    st.session_state[key] = i
                    st.rerun()
    return cur

def shape_filter(cnt, key, small=False, none_is_all=True):
    """타임라인은 여러 유형을 선택하고, 상세 격자는 한 유형을 선택한다."""
    btn_types = ("A", "B", "C")
    save_value = st.session_state.get(key)

    if none_is_all:
        # 처음에는 전체 선택, 기존 단일 선택값도 변환
        if save_value is None:
            select_type = set(btn_types)
        elif isinstance(save_value, str):
            select_type = {save_value}
        else:
            select_type = set(save_value)
    else:
        select_type = {save_value} if save_value else set()

    # 버튼을 왼쪽부터 내용 너비에 맞춰 배치
    with st.container(horizontal=True, gap="small"):
        for k in btn_types:
            short, desc = A.SHAPES[k]
            on = k in select_type

            with st.container(
                key=f"shapebtn-{k}-{'sm' if small else 'big'}",
                width="content",
            ):
                if st.button(
                    f"{k}형 **{cnt[k]}건**"
                    if small else f"{k}형 · {short} **{cnt[k]}건**",
                    key=f"btn_{key}_{k}",
                    width="content",
                    type="primary" if on else "secondary",
                    help=f"{k}형 — {desc}",
                ):
                    if none_is_all:
                        # 누른 유형만 켜거나 끄고 다른 선택은 유지
                        change_type = select_type.copy()
                        if on:
                            change_type.remove(k)
                        else:
                            change_type.add(k)

                        st.session_state[key] = sorted(change_type)
                    else:
                        # 상세 격자는 한 유형만 선택
                        st.session_state[key] = None if on else k

                    st.rerun()

    # 버튼에 대한 안내 문구
    if small:
        st.markdown(
            '<div class="shape-filter-hint">'
            'A형·B형·C형 선택 시 해당 유형의 전체 사례 표시'
            '</div>',
            unsafe_allow_html=True,
        )

    return select_type if none_is_all else save_value


def case_card(r, sub_text=None, bar_color=None):
    """고른 사례 하나: 왼쪽에 전후 3년 막대, 오른쪽에 «그 해 무슨 일이 있었나».

    상대국·리스크는 우리 자료에서 바로 뽑고, 배경 한 줄만 사람이 적은 것(A.EVENTS)이다.
    그 둘을 섞어 보이지 않게 배경 줄에는 «직접 적은 배경» 이라고 밝혀 둔다."""
    risk, tops = A.case_context(r["country"], int(r["year"]))
    # 두 칸은 CSS 로 같은 높이를 쓴다 (.st-key-casechart · .st-key-casecard). 사례마다 글 길이가
    # 달라 카드가 길어지므로, 고정 높이 대신 둘 다 그 줄에서 가장 높은 쪽에 맞춘다. (2026-10-01)
    c1, c2 = st.columns([1.25, 1], gap="medium")
    with c1:
        with st.container(key="casechart"):
            # 칸 제목 아래 한 줄은 «그 유형이 무슨 뜻인지» 로 (증가폭 숫자는 뺐다 — 2026-10-01)
            sub = sub_text or (lambda x: f"{x['shape']}형 — {A.SHAPES[x['shape']][1]}")
            grid([r], cols=1, bar_color=bar_color or A.SHAPE_COLOR[r["shape"]], mark_year=True,
                 sub=sub, height_per_row=360)
    with c2:
      with st.container(key="casecard"):
        st.markdown(
            f'<div class="case-x"><div class="case-h">{r["ko"]} · {int(r["year"])}년</div>'
            f'<div class="case-r">해당 연도 종합 리스크 <b>{risk:.3f}</b>'
            f'<span>0~1 · 해당 연도의 일별 평균</span></div>'
            # + '<div class="case-p">' + "".join(
            #     f'<span><i>{i + 1}</i>{ko}<b>{v:.2f}</b></span>' for i, (_, ko, v) in enumerate(tops))
            # + '<em>상위 리스크 상대국</em></div>'
            # 상대국별 배경 카드와 리스크 크기를 나타내는 막대 표시
            + '<div class="case-p"><em>상위 리스크 상대국</em>'
            + "".join(
                f'<div class="case-peer">'
                f'<i>{i + 1}</i>'
                f'<span class="case-peer-name">{ko}</span>'
                f'<div class="case-peer-track">'
                f'<div class="case-peer-fill" '
                f'style="width:{max(0, min(1, float(v))) * 100:.1f}%"></div>'
                f'</div>'
                f'<b>{v:.2f}</b>'
                f'</div>'
                for i, (_, ko, v) in enumerate(tops)
            )
            + '</div>'
            + (f'<div class="case-e">{A.EMBARGO[(r["country"], int(r["year"]))]}</div>'
               if (r["country"], int(r["year"])) in A.EMBARGO else "")
            + (f'<div class="case-w">{A.EVENTS[(r["country"], int(r["year"]))]}</div>'
               if (r["country"], int(r["year"])) in A.EVENTS else "")
            + '<div class="case-n">상대국 분석 범위: 중동 16개국 · 미국·러시아 등 역외 국가는 '
              '국가쌍 자료 범위에서 제외</div></div>',
            unsafe_allow_html=True)


def grid(rows, cols=5, bar_color=None, sub=None, height_per_row=290, mark_year=False):
    """사례를 작은 칸으로 늘어놓는다. rows = cases() 의 행 목록.

    막대는 그해 실제 주문 TIV.
    세로축은 칸마다 다르다 — 레바논은 최대 59, 이스라엘은 3,381 이라 같은 축에 두면 작은 쪽이 사라진다.
    """
    if not rows:
        st.info("선택 조건에 해당하는 사례 없음")
        return

    nrow = int(np.ceil(len(rows) / cols))
    fig = go.Figure()
    ann = []

    for i, r in enumerate(rows):
        ax = "" if i == 0 else str(i + 1)          # plotly 축 이름: x, x2, x3 …
        after = bar_color(r) if callable(bar_color) else (bar_color or RED)
        xdom, ydom, tx, ty, sy = _cell_box(i, cols, nrow)

        fig.add_trace(go.Bar(
            x=[str(y) for y in r["years"]], y=r["tiv"], xaxis="x" + ax, yaxis="y" + ax,
            marker_color=_bar_colors(r, after),
            text=[f"{v/1000:.1f}k" if v >= 1000 else f"{v:,.0f}" for v in r["tiv"]],
            textposition="outside", cliponaxis=False, textfont=dict(size=11),
            hovertemplate="%{x}년 · %{y:,.0f} TIV<extra></extra>", showlegend=False))

        xa = dict(domain=xdom, anchor="y" + ax, showgrid=False, linecolor=LINE, tickfont=dict(size=11))
        if mark_year:      # 사례 카드: 여섯 해를 다 적고, 급증한 해(0년)를 눈금에 못박는다 (2026-10-01)
            xa.update(tickmode="array", tickvals=[str(y) for y in r["years"]],
                      ticktext=[(f"<b>{y}</b><br>급증(0년)" if y == r["year"] else str(y)) for y in r["years"]])
        else:
            xa["nticks"] = 3
        fig.update_layout({
            "xaxis" + ax: xa,
            "yaxis" + ax: dict(domain=ydom, anchor="x" + ax, gridcolor=GRID,
                               zeroline=False, tickfont=dict(size=10),
                               rangemode="tozero", nticks=3,
                               title=dict(text="TIV", font=dict(size=11, color=MUTE), standoff=4))})   # 단위 (2026-10-02)

        label = sub(r) if callable(sub) else f"{r['diff']:+.2f} (표준편차 단위)"
        ann += [_ann(tx, ty, f"<b>{r['ko']} · {r['year']}</b>", 14, INK),
               _ann(tx, sy, label, 12, "#BCBCBC")]

    fig.update_layout(annotations=ann, paper_bgcolor=BG, plot_bgcolor=BG,
                      font=dict(color=INK, size=14, family="Malgun Gothic, sans-serif"),
                      margin=dict(l=10, r=10, t=30, b=34 if mark_year else 10), height=height_per_row * nrow)
    fig = theme.adapt(fig)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch", config=CFG)


# ══════════════════════════════════════════════════════════════════════
# 원본은 여기서 바로 자료를 계산하고 제목을 그렸다 → 맨 아래 page() 안으로 옮김 (M · C · UP · DOWN · EMB · NET · STREAK ·
# a_cnt · b_cnt 는 page() 가 채우는 모듈 변수, 아래 쪽 함수들은 원본처럼 이 이름을 그대로 쓴다)


    # ══ 2. 중동 전체 결과 ════════════════════════════════════════════════════

LAG_KEY = "corr_lag_seg"         # 시차 고르기 (아래 국가별 카드에 있지만 위 그래프 강조 · 핵심 문장도 따라간다)
LAG_DEFAULT = 1                   # 기본 = 1년 뒤 (SIPRI 는 주문 연도 → 1년 뒤가 계약이 잡히는 시점)


# def _lag_opts(ks):
#     return [k + (" ★" if i == LAG_DEFAULT else "") for i, k in enumerate(ks)]
def _lag_opts(ks):
    return list(ks)


def _diverging(per, lim):
    """국가별 r 을 가운데 0 선을 기준으로 왼쪽(음) · 오른쪽(양) 막대로 (2026-10-01 새 모양)."""
    vmax = max(0.35, float(per.abs().max()))
    rows = []
    for c, v in per.sort_values(ascending=False).items():
        w = abs(v) / vmax * 100
        side = "pos" if v > 0 else "neg"
        strong = " strong" if abs(v) >= lim else ""
        bar = f'<i class="ov-bar {side}{strong}" style="width:{w:.0f}%"></i><span class="ov-v {side}">{v:+.2f}</span>'
        rows.append(f'<div class="ov-row"><div class="ov-name"><i class="ov-dot {side}{strong}"></i>{A.COUNTRIES[c]}</div>'
                    f'<div class="ov-neg">{bar if v < 0 else ""}</div><div class="ov-mid"></div>'
                    f'<div class="ov-pos">{bar if v > 0 else ""}</div></div>')
    return ('<div class="ov-tbl"><div class="ov-row ov-h"><div class="ov-name">국가</div>'
            '<div class="ov-neg">음(−)의 상관 (감소)</div><div class="ov-mid">0</div>'
            '<div class="ov-pos">양(+)의 상관 (증가)</div></div>' + "".join(rows) + "</div>")


def page_1_corr():
    """중동 전체 결과 (2026-10-01 새 레이아웃): 핵심 분석 상자 → 01 시차별 상관계수 카드 → 국가별 개별 상관계수 카드."""
    ks, pooled, med = [], [], []
    for k in range(4):
        pr, per = A.lag_corr(M, k)
        ks.append("같은 해" if k == 0 else f"{k}년 뒤")
        pooled.append(pr)
        med.append(float(per.median()))
    opts = _lag_opts(ks)
    cur = st.session_state.get(LAG_KEY)
    lag = opts.index(cur) if cur in opts else LAG_DEFAULT
    r1, per1 = A.lag_corr(M, lag)
    plus, minus = int((per1 > 0).sum()), int((per1 < 0).sum())
    strong = [A.COUNTRIES[c] for c, v in per1.items() if abs(v) >= LIM]

    # ── 핵심 분석
    st.markdown(
        '<div class="ov-key"><div class="ov-kick"><span class="ov-badge">핵심 분석</span></div>'
        '<div class="ov-big">전체 집계의 상관관계는 미약하나, 국가별 방향 차이 확인</div>'
        f'<div class="ov-body">시차 0~3년의 전체 상관계수: <b class="ov-num">{min(pooled):+.3f} ~ {max(pooled):+.3f}</b> · 0에 근접 · '
        f'{ks[lag]} 기준: <b class="ov-pos-t">양(+)의 상관 {plus}개국</b>과 '
        f'<b class="ov-neg-t">음(−)의 상관 {minus}개국</b> · 국가별 결과를 함께 검토할 필요</div></div>',
        unsafe_allow_html=True)

    # ── 01 시차별 상관계수
    with st.container(border=True, key="ov_card1"):
        st.markdown(
            '<div class="ov-head"><div><div class="ov-t"><span class="ov-no">01</span> 시차별 상관계수</div>'
            '<div class="ov-s">연간 리스크·0~3년 후 무기 주문(log(1+TIV))의 시차별 상관계수 비교</div></div>'
            '<div class="ov-leg"><span><i class="sq red"></i>전체 국가 집계</span><span><i class="sq blue"></i>국가별 중앙값</span></div></div>',
            unsafe_allow_html=True)
        c1, c2 = st.columns([1.9, 1], gap="medium")
        with c1, st.container(key="ov_chartbox"):
            st.markdown('<div class="ov-cb-h"><span>시차별 피어슨 상관계수 (r)</span><span>16개국 · 연 단위</span></div>',
                        unsafe_allow_html=True)
            fig = go.Figure()
            lt = theme.is_light()           # 밝은 테마는 아래 국가별 막대와 같은 진한 빨강 · 파랑
            for vals, name, col in [(pooled, "전체 국가 집계", "#9f1239" if lt else RED), (med, "국가별 중앙값", "#0369a1" if lt else BLUE)]:
                fig.add_trace(go.Bar(x=ks, y=vals, name=name, marker_color=col, width=0.32,
                                     text=[f"{v:+.3f}" for v in vals], textposition="outside",
                                     cliponaxis=False, textfont=dict(size=12, color=col),
                                     hovertemplate=name + " · %{x} · r = %{y:+.3f}<extra></extra>"))
            # 선택 시차
            fig.add_vrect(
                x0=lag - 0.5,
                x1=lag + 0.5,
                fillcolor=theme.color_rgba("main-480", 0.08),
                opacity=1,
                line=dict(
                    color=theme.color_rgba("main-480", 0.45),
                    width=1.2,
                ),
                layer="below",
            )

            # 선택 시점 텍스트박스
            fig.add_annotation(
                x=lag,
                y=0.97,
                yref="paper",
                text=f"<b>선택 시점 ({ks[lag]})</b>",
                showarrow=False,
                xanchor="center",
                yanchor="top",
                font=dict(
                    size=10,
                    color=theme.C["main-40"],
                ),
                bgcolor=theme.C["main-light-650"],
                borderpad=6,
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="group",
                              bargap=0.35, height=330, showlegend=False,
                              font=dict(color=INK, size=13, family="Malgun Gothic, sans-serif"),
                              margin=dict(l=6, r=6, t=28, b=6))
            fig.update_xaxes(title=None, showgrid=False, tickfont=dict(size=13))
            fig.update_yaxes(title=dict(text="상관계수 r", font=dict(size=12)), range=[-0.25, 0.25], dtick=0.2, tickformat="+.2f", gridcolor=GRID,
                             tickfont=dict(size=11), zeroline=True, zerolinecolor=MUTE, zerolinewidth=1)
            fig.add_hline(y=0, line=dict(color=MUTE, width=1, dash="dot"))
            st.plotly_chart(theme.adapt(fig), width="stretch", config=CFG)
        with c2:
            st.markdown(
                '<div class="ov-note"><div class="ov-note-t">국가별 분석 필요</div>'
                '<div class="ov-note-b">전체 집계값으로 국가별 변화 방향을 판단하기 어려움 · '
                '외교 관계·제재·국방 예산 등 '
                '국가별 여건을 고려한 분석 필요</div>'
                '<div class="ov-info"><div class="ov-info-t">' + INFO_SVG + ' 해석 시 고려사항</div>'
                '<b>국가별 차이</b> 전체 값으로 개별 국가를 판단할 수 없음<br>'
                '<b>시점 차이</b> 주문 연도 기준 집계 · 실제 인도 시점과 차이 가능<br>'
                '<b>추가 요인</b> 국방 예산 · 정책 · 제재 · 공급 여건도 주문에 영향</div></div>',
                unsafe_allow_html=True)

    # ── 국가별 개별 상관계수
    with st.container(border=True, key="ov_card2"):
        h1, h2 = st.columns([1.25, 1], vertical_alignment="top")
        with h1:
            st.markdown(
                '<div class="ov-t"><span class="ov-no">02</span> 국가별 상관계수</div>'
                '<div class="ov-s">피어슨 r: <b class="ov-pos-t">양(+): 리스크·주문 규모의 같은 방향 변화</b> · '
                '<b class="ov-neg-t">음(−): 리스크·주문 규모의 반대 방향 변화</b></div>'
                f'<div class="ov-leg l"><span><i class="dot red"></i>양(+)의 상관 {plus}개국</span>'
                f'<span><i class="dot blue"></i>음(−)의 상관 {minus}개국</span></div>', unsafe_allow_html=True)
        with h2:
            with st.container(key="ov_lag_box"):          # 작은 알약 단추 (띠 모양 tabbar 는 칸이 좁아 글자가 잘림)
                st.segmented_control("시차", opts, default=opts[LAG_DEFAULT], key=LAG_KEY,
                                     label_visibility="collapsed", width="stretch",
                                     help="연간 리스크·무기 주문의 비교 시차 선택")
            st.markdown(f'<div class="ov-chip" title="상관계수 크기 비교를 위한 참고 기준 · 통계적 유의성 기준과는 구별">'
                        f'상관계수 참고선 ±{LIM:.2f}</div>', unsafe_allow_html=True)
        st.markdown(_diverging(per1, LIM), unsafe_allow_html=True)
        설명 = (
            f"|r| ≥ {LIM:g} 국가: {' · '.join(strong) if strong else '없음'}"
            f" · ±{LIM:g}: 계수 크기 참고 기준"
            " · 통계적 유의성 또는 인과관계 판단 기준과는 구별"
        )

        st.markdown(
            f'<div class="src-note" style="margin-top: 16px;">'
            f'참고선 기준 국가별 비교 {info_icon(설명)}'
            f'</div>',
            unsafe_allow_html=True,
        )


    # ══ 2. 증가 케이스 ════════════════════════════════════════════════════

def page_2_up():
        key("핵심 분석",
            "리스크 급증 이후 무기 주문 증가 양상",
            f"주문 증가 사례의 급증 기준 연도 전후 3년 비교 · 정점 도달 시기·이후 추세의 사례별 차이 확인", RED)

        card = sec_card("01", "주문 규모 증가 사례의 국가별 비교",
                        "급증 기준 연도 전후 3년의 주문 TIV·정점 시기 비교")
        with card:
            with st.container(key="info_accordion"):
                with st.expander("분석 대상과 급증 시점의 선정 기준"):
                    d1, d2 = st.columns(2, vertical_alignment="top")

                    with d1:
                        note(
                            f"<b>급증</b>: 직전 12개월 평균 대비 상승폭이 "
                            f"표준편차의 {A.K:.0f}배 초과·"
                            f"{A.MIN_JUMP} 이상이고, 리스크가 {A.FLOOR} 이상인 월 "
                            "· 세 조건 동시 충족<br>"
                            "최소 상승폭·리스크 수준 조건으로 소규모 변동의 과대 분류 방지"
                        )

                    with d2:
                        note(
                            "<b>0년</b>: 급증 월의 연간 <b>상승폭 합</b>을 기준으로 "
                            "선정한 상위 25% 연도<br>"
                            "국가별로 선정 · 급증 발생 연도가 부족한 경우 해당 연도만 포함"
                        )
        lab = {k: f"{k}형 {v[0]}" for k, v in A.SHAPES.items()}
        cnt = {k: sum(1 for r in UP if r["shape"] == k) for k in A.SHAPES}
        with card:
            keep = shape_filter(cnt, "up_shape_tl")

            ups = sorted(
                [r for r in UP if r["shape"] in keep],
                key=lambda r: (r["year"], r["ko"]),
            )

            if ups:
                picked = timeline(
                    ups,
                    key="up_timeline_" + "".join(sorted(keep)),
                )
                if picked is None or picked >= len(ups):
                    picked = max(range(len(ups)), key=lambda i: ups[i]["diff"])

                case_card(ups[picked])
            else:
                st.info("표시할 유형을 하나 이상 선택해 주세요.")

        # 사례그래프는 디폴트로 접어두고, 버튼 클릭 시 해당 유형 펼쳐짐
        with sec_card("02", "유형별 사례 비교", "급증 이후 주문 규모의 변화 양상에 따른 유형별 비교"):
            g_pick = shape_filter(cnt, "up_shape_grid", small=True, none_is_all=False)
            
            if g_pick is not None:
                grid(
                    sorted(
                        [r for r in UP if r["shape"] == g_pick],
                        key=lambda r: -r["diff"],
                    ),
                    cols=4,
                    bar_color=A.SHAPE_COLOR[g_pick],
                    mark_year=True,
                    height_per_row=330,
                    sub=lambda r: f"{lab[r['shape']]}",
                )


    # ══ 3. 감소 케이스 ══════════════════════════════════════════════════════

def page_3_down():
        key("핵심 분석",
            "리스크 급증 이후 무기 주문 감소 양상",
            "주문 감소·미발생 사례 확인 · 제재·내전 등 거래 여건을 고려한 해석 필요", BLUE)

        card = sec_card("01", "주문 규모 감소 사례의 국가별 비교",
                        "급증 기준 연도 전후 3년의 주문 TIV·감소 시기 비교")

        # (2026-10-01) 증가 쪽과 같은 틀 — 타임라인에서 점을 고르면 그 사례 카드가 나온다.
        #   여기서는 «제재 · 내전으로 거래가 끊긴» 8건만 다룬다. 그 밖의 감소는 사정이 제각각이라 뺐다.
        downs = sorted(EMB, key=lambda r: (r["year"], r["ko"]))
        with card:
            picked = timeline(downs, key="down_timeline", color_of=lambda r: GOLD, text_of=lambda r: "")
            if picked is None or picked >= len(downs):
                picked = min(range(len(downs)), key=lambda i: downs[i]["diff"])   # 가장 많이 줄어든 사례
            r = downs[picked]
            case_card(r, bar_color=GOLD,
                      sub_text=lambda x: f"제재·내전: {x['embargo']} · 표준화 규모 변화 {x['diff']:+.2f} (표준편차 단위)")

        with sec_card("02", "제재·내전 관련 감소 사례 비교", "제재·내전 관련 사례의 주문 감소 양상 비교"):
            if st.button(f"제재 · 내전 {len(EMB)}건 펼치기", key="down_grid_btn",
                         type="primary" if st.session_state.get("down_grid") else "secondary",
                         help="제재·내전 관련 사례의 급증 기준 연도 전후 3년 비교"):
                st.session_state["down_grid"] = not st.session_state.get("down_grid")
                st.rerun()
            if st.session_state.get("down_grid"):
                grid(EMB, cols=4, bar_color=BLUE, mark_year=True,
                     sub=lambda r: f"{r['embargo']}", height_per_row=330)
    

    # ══ 4. 결론 ═══════════════════════════════════════════════════════════

def page_4_conclusion():
        key("결론",
            "전체 집계와 국가별 사례의 병행 분석 필요",
            "전체 상관계수는 0에 근접</br>국가별 사례에서 주문 증가·감소 양상 확인 · 급증 시점·거래 여건을 고려한 해석 필요", GOLD)

        # 3단 흐름 — 왜 0으로 보였나 → 안에서 무슨 일이 있었나 → 그래서 무엇인가
        sec_card("01", "결론 흐름", "전체 집계 → 국가별 사례 → 종합 해석").markdown(
            '<div class="flow">'

            '<div class="fc">'
            '<div class="fn">1. 전체 집계</div>'
            '<div class="fbig">0</div>'
            '<div class="ft">뚜렷한 상관관계 미확인</div>'
            '<div class="fs">시차 0~3년의 전체 상관계수는 0에 근접</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc">'
            '<div class="fn">2. 국가별 사례</div>'
            f'<div class="fbox up"><div class="tag" style="color:{RED}">'
            f'증가 사례 ({len(ABC)}건 중 {a_cnt + b_cnt}건)</div>'
            '<div class="h">급증 이후 2년 이내 주문 정점</div>'
            f'<div class="d">증가 {len(ABC)}건 중 {a_cnt + b_cnt}건'
            f'({(a_cnt + b_cnt) / len(ABC) * 100:.0f}%)에서 급증 후 2년 이내 주문 정점 확인</div></div>'
            f'<div class="fbox dn"><div class="tag" style="color:{BLUE}">'
            f'감소 사례 중 제재 · 내전 {len(EMB)}건</div>'
            '<div class="h">제재·내전과 거래 제약 고려</div>'
            f'<div class="d">제재·내전 관련 감소 사례 {len(EMB)}건 · '
            '거래 제약과 수요 변화를 구분하여 해석</div></div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc dark">'
            '<div class="fn" style="color:#8b98ad">3. 종합 해석</div>'
            f'<div class="fbig">{gif_icon("think.gif")}</div>'
            '<div class="ft">국가별 시점과 여건 고려</div>'
            f'<div class="fs">국가별 급증 시점·주문 변화·거래 여건을 종합한 <b>사례별 해석 필요</b></div>'
            '</div>'

            '</div>', unsafe_allow_html=True)

        # ── 이 분석을 어디에 쓰나 — 실시간 모니터링으로 잇는 부분 ──────────
        sec_card("02", "대시보드 활용 방안",
                 "리스크 변화 모니터링·급증 전후 국가별 무기 주문 비교").markdown(
            '<div class="flow">'

            '<div class="fc">'
            f'<div class="fn" style="color:{BLUE}">1. 실시간 모니터링</div>'
            f'<div class="fbig">{gif_icon("update.gif")}</div>'
            '<div class="ft">갈등 리스크 지속적 갱신</div>'
            '<div class="fs">실시간 갈등 사건·월별 리스크를 통한 중동 16개국의 갈등 변화 확인</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc">'
            f'<div class="fn" style="color:{BLUE}">2. 갈등 징후 확인</div>'
            f'<div class="fbig">{gif_icon("check.gif")}</div>'
            '<div class="ft">갈등 사건의 증가와</br>발생 국가 확인</div>'
            '<div class="fs">실시간 사건 건수·유형·관여 국가를 통한 국가별·국가쌍별 갈등 징후 파악</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc dark" style="border-color:#60a5fa">'
            f'<div class="fn" style="color:{BLUE}">3. 무기 거래 시점 분석</div>'
            f'<div class="fbig">{gif_icon("calendar.gif")}</div>'
            '<div class="ft" style="color:#60a5fa">무기 거래 시점 분석을 위한</br>자료 제공</div>'
            f'<div class="fs">리스크 급증 시점·과거 주문 변화의 연계 비교를 통한 거래 집중 시기 탐색'
            '</div>'
            '</div>'

            '</div>', unsafe_allow_html=True)

# ══ 쪽 고르기 ════════════════════════════════════════════════════════
PAGES = {
    "중동 전체 결과": page_1_corr,
    "증가 사례": page_2_up,
    "감소 사례": page_3_down,
    "종합 결론": page_4_conclusion,
}


def page():
    """세부 분석 결과 탭 전체. app2.py 의 세부 분석 결과 탭에서 부른다."""
    global M, C, UP, DOWN, EMB, ABC, NET, STREAK, a_cnt, b_cnt
    M = A.panel()
    C = A.cases(M)
    UP = C[C["diff"] > 1].to_dict("records")
    DOWN = C[C["diff"] < -1].to_dict("records")
    EMB = [r for r in DOWN if r["embargo"]]
    ABC = [r for r in UP if r["shape"] in ("A", "B", "C")]   # 타임라인·결론이 세는 증가 사례 (D형 제외)
    NET = A.control(M)[2]          # 출발점을 맞춘 뒤 남는 순효과 — 결론의 «넘지 못한 선» 에서 쓴다
    STREAK = A.streak_rate(M)
    a_cnt = sum(1 for r in ABC if r["shape"] == "A")
    b_cnt = sum(1 for r in ABC if r["shape"] == "B")

    with st.container(key="surge_app"):    # CSS · 밝은 테마 규칙이 이 상자(.st-key-surge_app)만 골라 칠한다
        st.markdown(f"<style>{_scoped_css(CSS + OV_CSS)}</style>", unsafe_allow_html=True)
        # (2026-10-01) 맨 위 물음(원본 st.title)은 뺐다 — 페이지 제목 · 부제로 충분
        if st.session_state.get("surge_page") == "결론":       # 예전 이름으로 저장된 상태
            st.session_state["surge_page"] = "종합 결론"
        _, mid, _ = st.columns([0.6, 3, 0.6])
        with mid:
            choice = tabbar("분석 항목", list(PAGES), key="surge_page")
        PAGES[choice or list(PAGES)[0]]()          # 고른 쪽만 그린다

        st.caption("자료 · GDELT 1.0 (국가별 월별 리스크) × SIPRI Arms Transfers (주문 연도 TIV) · 중동 16개국 · 1980~2025")
