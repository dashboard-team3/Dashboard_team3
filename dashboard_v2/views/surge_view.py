"""리스크와 무기 거래 › 세부 분석 결과 탭 화면 (계산은 dashboard/surge.py). app2.py 가 page() 를 부른다.

2026-09-29 팀원의 급증과_무기거래/app.py 를 옮겼다 (원본은 unused_data/급증과_무기거래_원본/).
글 · 숫자 · 그래프 · 쪽 구성은 원본 그대로. 대시보드 안에서 돌도록 바꾼 것만:
  - st.set_page_config 뺌 (페이지 설정은 app2.py 한 곳)
  - CSS 는 이 탭 상자(.st-key-surge_app) 안에만 먹게 가둠. 페이지 전체를 바꾸던 규칙
    (.stApp 배경 · .block-container 폭 1500px · ⋮ 메뉴 숨김 · h1~h3 색) 은 뺌
  - 그래프는 theme.adapt 를 거쳐 내보냄 (글꼴 · 밝은 테마 색), use_container_width → width="stretch"
  - 맨 위 물음은 st.title → st.subheader (페이지 제목은 하나만)
  - 자료 계산(M · C · UP …)은 이 탭을 그릴 때 page() 안에서 (원본은 파일을 읽자마자)
  - 쪽 고르기 위젯: 빈 이름표 "" → "쪽 고르기"(숨김), 세션 키 "page" → "surge_page"
  밝은 테마 글 상자 색은 dashboard/style_light.css 맨 끝 "세부 분석 결과 탭" 규칙.

[원본 설명]
갈등 급증과 무기 수입 — 총량이 아니라 «시점»이 바뀐다.

한 가지 물음만 따라갑니다.
    갈등이 크게 튄 뒤 무기 수입은 어떻게 움직이는가.
답은 «늘지도 줄지도 않는다» 가 아니라 «일시에 집중적으로 구매한 후 수입을 중단한다» 입니다.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from sources import surge as A      # 원본: import analysis as A
from core import theme           # 그래프 글꼴 · 밝은 테마 색 (theme.adapt)
from core.ui import ctitle, tabbar

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
  .fc {{flex:1; background:{CARD}; border:1px solid {LINE}; border-radius:14px;
        padding:1.1rem 1.2rem; display:flex; flex-direction:column;}}
  .fc.dark {{background:#060c18; border-color:{GOLD};}}
  .fn {{font-size:14px; font-weight:700; color:{MUTE}; margin-bottom:.8rem;
        letter-spacing:.04em;}}
  .fbig {{font-family:Cambria,serif; font-size:28px; font-weight:700; line-height:1;
          color:{MUTE}; text-align:center; margin:.5rem 0 .3rem 0;}}
  .ft {{font-size:19px; font-weight:700; color:{INK}; text-align:center;}}
  .fs {{font-size:16px; color:{MUTE}; line-height:1.65; margin-top:.5rem;
        word-break:keep-all;}}
  .farr {{display:flex; align-items:center; justify-content:center; color:{GOLD};
          font-size:28px; font-weight:700; flex:0 0 auto; width:1.4rem; opacity:.75;}}
  .fbox {{border-radius:10px; padding:.75rem .9rem; margin-bottom:.55rem;
          background:#0d1526; border-left:4px solid {MUTE};}}
  .fbox.up {{border-left-color:{RED};}} .fbox.dn {{border-left-color:{BLUE};}}
  .fbox .tag {{font-size:14px; font-weight:700; margin-bottom:.25rem;}}
  .fbox .h {{font-size:16px; font-weight:700; color:{INK};}}
  .fbox .d {{font-size:14px; color:{MUTE}; margin-top:.25rem; line-height:1.55;
             word-break:keep-all;}}
  .fc.dark .ft {{color:{GOLD}; font-size:19px; margin-top:.4rem;}}
  @media (max-width:900px) {{
    .flow {{flex-direction:column;}} .farr {{display:none;}}
  }}

  /* 고른 사례 한 건의 «그 해 무슨 일이 있었나» 칸 (2026-10-01) */
  .case-x {{background:{CARD}; border:1px solid {LINE}; border-radius:14px;
            padding:1.1rem 1.3rem; height:100%;}}
  .case-h {{font-size:19px; font-weight:800; color:#fff; margin-bottom:.8rem;}}
  .case-r {{font-size:16px; color:#cbd5e1; padding-bottom:.8rem; border-bottom:1px solid {LINE};}}
  .case-r b {{font-size:21px; color:{GOLD}; font-variant-numeric:tabular-nums;}}
  .case-r span {{display:block; font-size:14px; color:{MUTE}; margin-top:.2rem;}}
  .case-p {{padding:.8rem 0; border-bottom:1px solid {LINE};}}
  .case-p span {{display:flex; align-items:center; gap:.55rem; font-size:16px;
                 color:{INK}; margin-bottom:.35rem;}}
  .case-p i {{font-style:normal; font-size:12px; font-weight:700; color:{BG};
              background:{MUTE}; border-radius:50%; width:1.2rem; height:1.2rem;
              display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto;}}
  .case-p b {{margin-left:auto; color:{RED}; font-variant-numeric:tabular-nums;}}
  .case-p em {{display:block; font-style:normal; font-size:14px; color:{MUTE}; margin-top:.3rem;}}
  .case-e {{margin-top:.8rem; display:inline-block; font-size:14px; font-weight:700;
            color:{BG}; background:{GOLD}; border-radius:6px; padding:.15rem .5rem;}}
  .case-w {{margin-top:.8rem; font-size:16px; color:#cbd5e1; line-height:1.65;
            word-break:keep-all;}}
  .case-w span {{display:block; font-size:13px; color:{MUTE}; margin-top:.35rem;}}
  .case-n {{margin-top:.9rem; padding-top:.8rem; border-top:1px solid {LINE};
            font-size:13px; color:{MUTE}; line-height:1.6; word-break:keep-all;}}

"""

CFG = {"displayModeBar": False}
SCOPE = ".st-key-surge_app"             # page() 가 이 이름표(key)를 단 상자 안에 그린다


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
    """그 쪽의 결론을 맨 위에 크게. 아래 그림은 이 문장의 근거다."""
    st.markdown(f'<div class="key" style="border-left:6px solid {color}">'
                f'<div class="n" style="color:{color}">{kicker}</div>'
                f'<div class="t">{big}</div><div class="s">{sub}</div></div>',
                unsafe_allow_html=True)


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
        textfont=dict(size=11, color="#ffffff", family="Malgun Gothic, sans-serif"),
        marker=dict(size=[15 + 11 * (abs(r["diff"]) - 1.0) for r in rows],
                    color=[col(r) for r in rows], line=dict(width=1.2, color=BG)),
        customdata=[[r["ko"], r["year"], A.SHAPES[r["shape"]][0], r["diff"]] for r in rows],
        hovertemplate="<b>%{customdata[0]} · %{customdata[1]}년</b><br>%{customdata[2]}"
                      "<br>변화폭 %{customdata[3]:+.2f} 칸<extra></extra>", showlegend=False))
    fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, height=60 + 34 * len(order),
                      font=dict(color=INK, size=13, family="Malgun Gothic, sans-serif"),
                      margin=dict(l=10, r=20, t=16, b=10), clickmode="event+select",
                      xaxis=dict(gridcolor=GRID, zeroline=False, dtick=5, tickformat="d",
                                 range=[min(r["year"] for r in rows) - 2, max(r["year"] for r in rows) + 2]),
                      yaxis=dict(categoryorder="array", categoryarray=order, gridcolor=GRID, zeroline=False))
    ev = st.plotly_chart(theme.adapt(fig), width="stretch", config=CFG, on_select="rerun", key=key)
    pts = (ev or {}).get("selection", {}).get("points", []) if isinstance(ev, dict) else []
    return pts[0].get("point_index") if pts else None


def shape_filter(cnt, key, small=False, none_is_all=True):
    """A·B·C 단추 한 줄 (2026-10-01). 단추가 곧 범례이자 거르개다 — 색은 그 유형의 그래프 색.

    누르면 «그 유형만» 켜진다. 켜진 것을 다시 누르면 원래대로 돌아간다.
    none_is_all=True  고른 것이 없으면 «전부 보기» (타임라인)
    none_is_all=False 고른 것이 없으면 «아무것도 안 보임» (아래 격자 — 눌러야 펼쳐진다)
    고른 유형 한 글자, 또는 None 을 돌려준다."""
    cur = st.session_state.get(key)
    cols = st.columns([1, 1, 1, 5] if small else [1, 1, 1], gap="small", vertical_alignment="center")
    for i, k in enumerate(("A", "B", "C")):
        short, desc = A.SHAPES[k]
        on = (none_is_all and cur is None) or cur == k
        with cols[i]:
            with st.container(key=f"shapebtn-{k}-{'sm' if small else 'big'}"):
                if st.button(f"{k}형 {cnt[k]}건" if small else f"{k}형 · {short} {cnt[k]}건",
                             key=f"btn_{key}_{k}", width="stretch",
                             type="primary" if on else "secondary", help=f"{k}형 — {desc}"):
                    st.session_state[key] = None if cur == k else k
                    st.rerun()
    return cur


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
            f'<div class="case-r">그 해 종합 리스크 <b>{risk:.3f}</b>'
            f'<span>0~1 · 그 해 모든 날의 평균</span></div>'
            + '<div class="case-p">' + "".join(
                f'<span><i>{i + 1}</i>{ko}<b>{v:.2f}</b></span>' for i, (_, ko, v) in enumerate(tops))
            + '<em>리스크가 가장 높았던 상대국</em></div>'
            + (f'<div class="case-e">{A.EMBARGO[(r["country"], int(r["year"]))]}</div>'
               if (r["country"], int(r["year"])) in A.EMBARGO else "")
            + (f'<div class="case-w">{A.EVENTS[(r["country"], int(r["year"]))]}</div>'
               if (r["country"], int(r["year"])) in A.EVENTS else "")
            + '<div class="case-n">상대국은 중동 16개국 사이만 셉니다. 미국·러시아 같은 역외 국가는 '
              '국가쌍 자료에 없어, 실제 교전 상대가 역외인 사례는 여기에 안 나옵니다.</div></div>',
            unsafe_allow_html=True)


def grid(rows, cols=5, bar_color=None, sub=None, height_per_row=290, mark_year=False):
    """사례를 작은 칸으로 늘어놓는다. rows = cases() 의 행 목록.

    막대는 그해 실제 주문 TIV.
    세로축은 칸마다 다르다 — 레바논은 최대 59, 이스라엘은 3,381 이라 같은 축에 두면 작은 쪽이 사라진다.
    """
    if not rows:
        st.info("해당하는 사례가 없습니다.")
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
                               rangemode="tozero", nticks=3)})

        label = sub(r) if callable(sub) else f"{r['diff']:+.2f} 칸"
        ann += [_ann(tx, ty, f"<b>{r['ko']} · {r['year']}</b>", 14, INK),
               _ann(tx, sy, label, 12, "#BCBCBC")]

    fig.update_layout(annotations=ann, paper_bgcolor=BG, plot_bgcolor=BG,
                      font=dict(color=INK, size=14, family="Malgun Gothic, sans-serif"),
                      margin=dict(l=10, r=10, t=30, b=34 if mark_year else 10), height=height_per_row * nrow)
    st.plotly_chart(theme.adapt(fig), width="stretch", config=CFG)


# ══════════════════════════════════════════════════════════════════════
# 원본은 여기서 바로 자료를 계산하고 제목을 그렸다 → 맨 아래 page() 안으로 옮김 (M · C · UP · DOWN · EMB · NET · STREAK ·
# a_cnt · b_cnt 는 page() 가 채우는 모듈 변수, 아래 쪽 함수들은 원본처럼 이 이름을 그대로 쓴다)


    # ══ 2. 중동 전체 결과 ════════════════════════════════════════════════════

def page_1_corr():
        ks, pooled, med = [], [], []
        for k in range(4):
            pr, per = A.lag_corr(M, k)
            ks.append("같은 해" if k == 0 else f"{k}년 뒤")
            pooled.append(pr)
            med.append(float(per.median()))
        r1, per1 = A.lag_corr(M, 1)

        key("분석 1", "전체 국가의 연 단위 분석에서는 뚜렷한 공통 경향이 확인되지 않았습니다.",
            f"시차 0~3년의 전체 상관계수는 <b>{min(pooled):+.3f} ~ {max(pooled):+.3f}</b> 으로 0에 가까웠습니다."
            f"국가별 상관계수는 양(+)의 방향을 보인 국가 {int((per1 > 0).sum())}개국, 음(-)의 방향을 보인 국가 (−) {int((per1 < 0).sum())}개국으로 나뉘었습니다.</b>"
            "국가별 차이가 전체 집계 결과에 반영되지 않을 수 있으므로, <b>이 결과만으로 관계의 유무를 판단하기는 어렵습니다.</b>", GOLD)

        sec("01", "국가별 갈등 위험과 무기 수입의 상관관계",
            "국가별로 갈등 위험 지표와 무기 수입 간 피어슨 상관계수를 산출했습니다. 국가별 계수의 방향과 크기는 서로 다르게 나타나, 전체 국가의 연간 지표만으로는 세부적인 변화 양상을 파악하는 데 한계가 있습니다.", GOLD)

        c1, c2 = st.columns([1.3, 1], gap="medium")
        with c1:
            fig = go.Figure()
            for vals, name, col in [(pooled, "전체 국가 집계", RED), (med, "국가별 중앙값", BLUE)]:
                fig.add_trace(go.Bar(x=ks, y=vals, name=name, marker_color=col,
                                     text=[f"{v:+.3f}" for v in vals], textposition="outside",
                                     cliponaxis=False,
                                     hovertemplate=name + " · %{x} · r = %{y:+.3f}<extra></extra>"))
            fig.update_layout(paper_bgcolor=BG, plot_bgcolor=BG, barmode="group", height=380,
                              font=dict(color=INK, size=15, family="Malgun Gothic, sans-serif"),
                              margin=dict(l=10, r=10, t=86, b=10),   # v2: 제목(19px)과 범례가 겹치지 않게 위 여백을 늘림
                              title=dict(text=ctitle("시차별 상관계수 (피어슨 r)", "중동 16개국 · 연 단위 · 빨강 = 전체 국가 집계 · 파랑 = 국가별 중앙값"),
                                          font=dict(size=17, color=INK), x=0),
                              legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0, font=dict(size=14)))
            fig.update_xaxes(title="수입 시점", gridcolor=GRID)
            fig.update_yaxes(title="피어슨 r", range=[-0.35, 0.35], gridcolor=GRID,
                             zeroline=True, zerolinecolor=MUTE, zerolinewidth=1.5)
            st.plotly_chart(theme.adapt(fig), width="stretch", config=CFG)
        with c2:
            note("전체 국가를 집계한 결과, <b>0~3년의 시차에서 상관계수는 모두 0에 가까웠습니다.</b></br> 국가별 변화 방향과 시점이 달라 <b>전체 값에서는 공통된 경향이 뚜렷하게 나타나지 않습니다.</b>", "gold")
            note("<b>해석 시 고려사항</b></br>"
                 "- 국가별 차이 : 전체 상관계수만으로 개별 국가의 변화 양상을 판단하기 어렵습니다.<br>"
                 "- 시점 차이 : SIPRI의 주문 연도와 실제 인도 연도는 다를 수 있습니다.<br>"
                 "- 다른 영향 요인 : 국방 예산, 정책, 제재, 공급 여건도 무기 주문 규모에 영향을 줄 수 있습니다.")

        st.plotly_chart(theme.adapt(
            go.Figure(go.Bar(
                x=per1.values, y=[A.COUNTRIES[c] for c in per1.index], orientation="h",
                marker_color=[RED if v > 0 else BLUE for v in per1.values],
                text=[f"{v:+.2f}" for v in per1.values], textposition="outside", cliponaxis=False,
                hovertemplate="%{y} · r = %{x:+.3f}<extra></extra>")
            ).update_layout(
                paper_bgcolor=BG, plot_bgcolor=BG, height=520, showlegend=False,
                font=dict(color=INK, size=15, family="Malgun Gothic, sans-serif"),
                margin=dict(l=10, r=50, t=50, b=10),
                title=dict(text=ctitle("국가별 상관계수", "리스크와 1년 뒤 무기 수입 · 피어슨 r · 빨강 = 양(+) · 파랑 = 음(−)"), font=dict(size=17, color=INK), x=0)
            ).update_xaxes(range=[-0.55, 0.45], gridcolor=GRID, zeroline=True,
                           zerolinecolor=MUTE, zerolinewidth=1.5
            ).update_yaxes(autorange="reversed", gridcolor=GRID)),
            width="stretch", config=CFG)
        note("국가별 상관계수는 양(+)과 음(-)의 방향으로 나뉘며, 국가 간 차이도 확인됩니다. 전체 국가의 집계값만으로는 이러한 국가별 양상을 충분히 설명하기 어렵습니다.", "gold")


    # ══ 2. 증가 케이스 ════════════════════════════════════════════════════

def page_2_up():
        key("분석 2",
            "갈등 위험 급증 이후 무기 주문 규모의 변화",
            f"갈등 위험이 급증한 뒤 무기 주문 규모가 증가한 사례를 선정해 전후 3년의 변화를 비교했습니다. 주문 규모가 정점에 이르는 시점과 이후의 흐름은 사례별로 다르게 나타났습니다.", RED)

        sec("02", "주문 규모 증가 사례의 국가별 비교",
            "갈등 위험 급증 이후 주문 규모가 증가한 사례를 국가별로 비교해, 증가 시점과 이후 변화 양상을 살펴봅니다.", RED)
        with st.expander("분석 대상과 급증 시점의 선정 기준"):
            d1, d2 = st.columns(2, vertical_alignment="top")
            with d1:
                note(f"<b>급증</b> = 직전 12개월 평균보다 표준편차 {A.K:.0f}배 이상, "
                     f"상승폭 {A.MIN_JUMP} 이상, 리스크 {A.FLOOR} 이상인 달.<br>"
                     "(0.02 에서 0.05로의 변화도 급증으로 분류되기 때문에 표준편차 사용)")
            with d2:
                note("<b>0년</b> = 그 해 급증한 달들의 <b>상승폭 합</b>이 큰 해부터 그 나라 해 수의 25%.<br>"
                     "(0·1·2 에 몰려 있어 상위 25%가 의도한 기준점대로 명확히 구분하기 위해 개월 수로 끊지 않음)")
        lab = {k: f"{k}형 {v[0]}" for k, v in A.SHAPES.items()}

        # (2026-10-01) 위 단추 = 타임라인 거르개. 누른 유형«만» 남는다 (안 누르면 전부).
        #   D형(어디에도 맞지 않는 것)은 읽을 것이 없어 두 곳 모두에서 뺀다.
        cnt = {k: sum(1 for r in UP if r["shape"] == k) for k in A.SHAPES}
        tl_pick = shape_filter(cnt, "up_shape_tl")
        keep = {"A", "B", "C"} if tl_pick is None else {tl_pick}
        ups = sorted([r for r in UP if r["shape"] in keep], key=lambda r: (r["year"], r["ko"]))

        # 거르개를 바꾸면 고른 점의 번호가 가리키는 사례가 달라지므로, 상자 이름에 넣어 선택을 비운다
        picked = timeline(ups, key="up_timeline_" + "".join(sorted(keep)))
        if picked is None or picked >= len(ups):
            picked = max(range(len(ups)), key=lambda i: ups[i]["diff"])   # 처음에는 증가폭이 가장 큰 사례
        case_card(ups[picked])
        st.write("")

        # 사례를 한꺼번에 늘어놓은 격자는 접어 둔다 — 단추를 눌러야 그 유형만 펼쳐진다
        sec("03", "유형별로 모아 보기", "같은 유형끼리 모아, 급증 뒤 주문 규모가 어떤 모양으로 움직였는지 한눈에 견줍니다.", RED)
        g_pick = shape_filter(cnt, "up_shape_grid", small=True, none_is_all=False)
        if g_pick is None:
            note("위 <b>A형 · B형 · C형</b> 단추를 누르면 그 유형의 사례가 모두 펼쳐집니다.")
        else:
            grid(sorted([r for r in UP if r["shape"] == g_pick], key=lambda r: -r["diff"]),
                 bar_color=A.SHAPE_COLOR[g_pick], mark_year=True, height_per_row=330,
                 sub=lambda r: f"{lab[r['shape']]}")
        # 맨 아래 정리 글 두 개는 뺐다 — «모양 · 건수 · 뜻» 표와 함께 단추·결론 쪽과 겹쳤다 (2026-10-01)


    # ══ 3. 감소 케이스 ══════════════════════════════════════════════════════

def page_3_down():
        key("분석 3",
            "무기 주문 규모가 감소한 사례의 변화 양상",
            "일부 국가별 사례에서는 갈등 위험이 급증한 뒤 무기 주문 규모가 크게 줄거나 0으로 나타났습니다. 제재와 내전 등 거래 여건의 변화도 함께 관찰되어, 주문 규모의 감소를 갈등 위험 변화만으로 설명하기는 어렵습니다.", BLUE)

        sec("03", "주문 규모 감소 사례의 국가별 비교",
            "갈등 위험 급증 이후 주문 규모가 감소한 시점과 이후의 변화 양상을 살펴봅니다.", BLUE)

        # (2026-10-01) 증가 쪽과 같은 틀 — 타임라인에서 점을 고르면 그 사례 카드가 나온다.
        #   여기서는 «제재 · 내전으로 거래가 끊긴» 8건만 다룬다. 그 밖의 감소는 사정이 제각각이라 뺐다.
        zero = sum(1 for r in EMB if sum(r["tiv"][-3:]) == 0)
        downs = sorted(EMB, key=lambda r: (r["year"], r["ko"]))
        picked = timeline(downs, key="down_timeline", color_of=lambda r: GOLD, text_of=lambda r: "")
        if picked is None or picked >= len(downs):
            picked = min(range(len(downs)), key=lambda i: downs[i]["diff"])   # 가장 많이 줄어든 사례
        r = downs[picked]
        case_card(r, bar_color=GOLD,
                  sub_text=lambda x: f"제재 · 내전 — {x['embargo']} · 변화폭 {x['diff']:+.2f} 칸")
        st.write("")

        sec("04", "제재 · 내전으로 끊긴 사례 모아 보기",
            "거래가 막혀 줄어든 경우를 따로 모아, 수요가 줄어든 것과 섞어 읽지 않도록 합니다.", BLUE)
        if st.button(f"제재 · 내전 {len(EMB)}건 펼치기", key="down_grid_btn",
                     type="primary" if st.session_state.get("down_grid") else "secondary",
                     help="제재 · 내전으로 거래가 끊긴 사례만 모아 전후 3년을 나란히 봅니다"):
            st.session_state["down_grid"] = not st.session_state.get("down_grid")
            st.rerun()
        if st.session_state.get("down_grid"):
            grid(EMB, cols=4, bar_color=BLUE, mark_year=True,
                 sub=lambda r: f"{r['embargo']}", height_per_row=330)
        note(f"주문 규모가 줄어든 {len(DOWN)}건 가운데 <b>제재 · 내전으로 거래가 끊긴 {len(EMB)}건</b>만 여기에서 다룹니다. "
             f"그중 {zero}개 사례는 이후 3년간 주문 연도 TIV 가 0 이었습니다. "
             "거래 자체가 막힌 경우라, 이 감소를 갈등 위험 변화에 따른 수요 감소로 읽으면 안 됩니다.", "blue")
    

    # ══ 4. 결론 ═══════════════════════════════════════════════════════════

def page_4_conclusion():
        key("결 론",
            "전체 집계에서는 뚜렷하지 않았던 변화가 국가별 사례에서 나타났습니다.",
            "전체 국가의 연 단위 상관계수는 0에 가까웠습니다. </br>그러나 갈등 위험 급증 시점을 기준으로 국가별 사례를 살펴보면, 무기 주문 규모가 증가하거나 감소하는 서로 다른 양상이 확인됩니다. 따라서 전체 집계 결과와 국가별 변화를 함께 살펴볼 필요가 있습니다.", GOLD)

        # 3단 흐름 — 왜 0으로 보였나 → 안에서 무슨 일이 있었나 → 그래서 무엇인가
        st.markdown(
            '<div class="flow">'

            '<div class="fc">'
            '<div class="fn">1. 전체 집계</div>'
            '<div class="fbig">0</div>'
            '<div class="ft">뚜렷한 상관관계 미확인</div>'
            '<div class="fs">0~3년의 시차에서 전체 국가의 상관계수는 0에 가까웠습니다.</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc">'
            '<div class="fn">2. 국가별 사례</div>'
            f'<div class="fbox up"><div class="tag" style="color:{RED}">'
            f'증가 사례 ({len(UP)}건 중 {a_cnt + b_cnt}건)</div>'
            '<div class="h">일시적 집중 구매 후 감소</div>'
            f'<div class="d">주문 규모가 증가한 {len(UP)}개 사례 중 {a_cnt + b_cnt}개(78%)는 갈등 위험 급증 후 2년 이내에 정점에 이르렀습니다.</div></div>'
            f'<div class="fbox dn"><div class="tag" style="color:{BLUE}">'
            f'감소 사례 중 제재 · 내전 {len(EMB)}건</div>'
            '<div class="h">거래 전면 단절</div>'
            f'<div class="d">제재 · 내전으로 거래가 끊긴 {len(EMB)}건은 수요가 준 것이 아니라 «살 수 없게 된» 경우라, '
            '나머지 감소와 섞어 읽으면 안 됩니다.</div></div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc dark">'
            '<div class="fn" style="color:#8b98ad">3. 종합 해석</div>'
            '<div class="fbig" style="color:#f5c542; font-size:28px">&#9679;</div>'
            '<div class="ft">국가별 시점과 여건 고려</div>'
            f'<div class="fs">전체 집계값만으로는 국가별 변화 시점과 방향을 파악하기 어렵습니다. 갈등 위험과 무기 주문 규모의 관계는 <b>사례별로 해석해야 합니다.</b></div>'
            '</div>'

            '</div>', unsafe_allow_html=True)

        # ── 이 분석을 어디에 쓰나 — 실시간 모니터링으로 잇는 부분 ──────────
        sec("🔎", "대시보드 활용 방안",
            "갈등 위험의 변화를 지속적으로 확인하고, 급증 시점을 기준으로 국가별 무기 주문 규모의 전후 양상을 비교합니다.", BLUE)

        st.markdown(
            '<div class="flow">'

            '<div class="fc">'
            f'<div class="fn" style="color:{BLUE}">1. 실시간 감시</div>'
            '<div class="fbig" style="font-size:28px">📈</div>'
            '<div class="ft">갈등 리스크 지속적 갱신</div>'
            '<div class="fs">GDELT를 매일 갱신하고 중동 16개국의 월별 리스크를 이어서, 갈등 관계가 어떻게 변하는지 확인합니다.</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc">'
            f'<div class="fn" style="color:{BLUE}">2. 갈등 징후 확인</div>'
            '<div class="fbig" style="font-size:28px">✔️</div>'
            '<div class="ft">갈등 사건의 증가와</br>발생 국가 확인</div>'
            '<div class="fs">실시간 사건 건수와 유형, 참여 국가를 살펴보며 갈등이 높아지는 국가와 국가쌍을 파악합니다.</div>'
            '</div>'

            '<div class="farr">&rsaquo;</div>'

            '<div class="fc dark" style="border-color:#60a5fa">'
            f'<div class="fn" style="color:{BLUE}">3. 무기 거래 시점 분석</div>'
            '<div class="fbig" style="color:#60a5fa; font-size:28px">&#128197;</div>'
            '<div class="ft" style="color:#60a5fa">무기 거래 시점 예측을 위한</br>자료 제공</div>'
            f'<div class="fs">리스크가 높아진 시점과 과거 무기 주문 규모의 변화를 연결해, 이후 거래가 집중될 가능성이 있는 시기를 살펴봅니다.'
            '</div>'
            '</div>'

            '</div>', unsafe_allow_html=True)

        note("<b>이 대시보드는 무기 거래를 예측하기보다, 갈등 위험이 급증한 시점과 무기 주문 규모의 변화를 함께 탐색하는 도구입니다.</b><br>"
             "결과를 해석할 때에는 제재, 정책, 공급 여건 등 국가별 배경을 함께 고려해야 합니다.", "blue")

# ══ 쪽 고르기 ════════════════════════════════════════════════════════
PAGES = {
    "중동 전체 결과": page_1_corr,
    "증가 케이스": page_2_up,
    "감소 케이스": page_3_down,
    "결론": page_4_conclusion,
}


def page():
    """세부 분석 결과 탭 전체. app2.py 의 세부 분석 결과 탭에서 부른다."""
    global M, C, UP, DOWN, EMB, NET, STREAK, a_cnt, b_cnt
    M = A.panel()
    C = A.cases(M)
    UP = C[C["diff"] > 1].to_dict("records")
    DOWN = C[C["diff"] < -1].to_dict("records")
    EMB = [r for r in DOWN if r["embargo"]]
    NET = A.control(M)[2]          # 출발점을 맞춘 뒤 남는 순효과 — 결론의 «넘지 못한 선» 에서 쓴다
    STREAK = A.streak_rate(M)
    a_cnt = sum(1 for r in UP if r["shape"] == "A")
    b_cnt = sum(1 for r in UP if r["shape"] == "B")

    with st.container(key="surge_app"):    # CSS · 밝은 테마 규칙이 이 상자(.st-key-surge_app)만 골라 칠한다
        st.markdown(f"<style>{_scoped_css(CSS)}</style>", unsafe_allow_html=True)
        st.subheader("리스크의 변화와 무기 수입은 어떤 관계를 보이는가?")   # 원본: st.title
        choice = tabbar("쪽 고르기", list(PAGES), key="surge_page")
        st.write("")
        PAGES[choice or list(PAGES)[0]]()          # 고른 쪽만 그린다

        st.caption("자료 · GDELT 1.0 (국가별 월별 리스크) × SIPRI Arms Transfers (주문 연도 TIV) · 중동 16개국 · 1980~2025")
