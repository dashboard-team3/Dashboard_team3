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
    return ([x0, x0 + w * 0.80],                     # 가로: 오른쪽 20%는 다음 칸과의 사이
            [top - h * 0.62, top - h * 0.20],        # 세로: 위 20%는 제목 두 줄 자리
            x0 - 0.012, top - h * 0.03, top - h * 0.115)


def _bar_colors(r, after):
    """막대 색 — 0년은 노랑, 그 앞은 회색, 그 뒤는 after 색."""
    return [GOLD if y == r["year"] else (MUTE if y < r["year"] else after) for y in r["years"]]


def grid(rows, cols=5, bar_color=None, sub=None, height_per_row=290):
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

        fig.update_layout({
            "xaxis" + ax: dict(domain=xdom, anchor="y" + ax, showgrid=False,
                               linecolor=LINE, tickfont=dict(size=11), nticks=3),
            "yaxis" + ax: dict(domain=ydom, anchor="x" + ax, gridcolor=GRID,
                               zeroline=False, tickfont=dict(size=10),
                               rangemode="tozero", nticks=3)})

        label = sub(r) if callable(sub) else f"{r['diff']:+.2f} 칸"
        ann += [_ann(tx, ty, f"<b>{r['ko']} · {r['year']}</b>", 14, INK),
               _ann(tx, sy, label, 12, "#BCBCBC")]

    fig.update_layout(annotations=ann, paper_bgcolor=BG, plot_bgcolor=BG,
                      font=dict(color=INK, size=14, family="Malgun Gothic, sans-serif"),
                      margin=dict(l=10, r=10, t=30, b=10), height=height_per_row * nrow)
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

        # 모양으로 걸러 보기. D형(어디에도 맞지 않는 것)은 읽을 것이 없어 화면에서 뺀다.
        cnt = {k: sum(1 for r in UP if r["shape"] == k) for k in A.SHAPES}
        opts = {f"{k}형 ({cnt[k]})": k for k in ("A", "B", "C") if cnt[k]}
        pick = st.segmented_control("변화 유형별 사례 보기", list(opts), selection_mode="multi",
                                    default=list(opts), key="shape_pick")
        keep = {opts[t] for t in (pick or [])}

        grid(sorted([r for r in UP if r["shape"] in keep], key=lambda r: (r["shape"], -r["diff"])),
             bar_color=lambda r: A.SHAPE_COLOR[r["shape"]],
             sub=lambda r: f"{lab[r['shape']]}")
        g1, g2 = st.columns([1.25, 1])
        with g1:
            rows = [
                {"모양": f"{k}형 · {v[0]}", "건수": cnt[k], "뜻": v[1]}
                for k, v in A.SHAPES.items()
                if k != "D"
            ]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        with g2:
            # h1, t1_, p1 = STREAK["급증한 해"]
            # h2, t2_, p2 = STREAK["그 밖의 해"]
            note(f"<b>선정 사례에서는 증가 시점이 집중되는 양상이 나타났습니다.</b><br>선정된 18개 사례 중 8개(44%)는 갈등 위험 급증 이듬해에 주문 규모가 정점에 이르렀습니다. A형과 B형을 합치면 14개(78%)에서 2년 이내에 정점이 나타났습니다.</br>"
                 "다만 이는 <b>선정된 사례의 분포</b>이므로, 전체 국가에서 동일한 양상이 나타난다고 일반화하기는 어렵습니다.", "red")
        note(f"<b>국가별로 주문 규모가 정점에 이르는 시점이 달랐습니다.</b></br>"
             "이러한 시차를 고려해 다음 페이지에서 주문 규모가 감소한 사례도 살펴봅니다.", "red")


    # ══ 3. 감소 케이스 ══════════════════════════════════════════════════════

def page_3_down():
        key("분석 3",
            "무기 주문 규모가 감소한 사례의 변화 양상",
            "일부 국가별 사례에서는 갈등 위험이 급증한 뒤 무기 주문 규모가 크게 줄거나 0으로 나타났습니다. 제재와 내전 등 거래 여건의 변화도 함께 관찰되어, 주문 규모의 감소를 갈등 위험 변화만으로 설명하기는 어렵습니다.", BLUE)

        sec("03", "주문 규모 감소 사례의 국가별 비교",
            "갈등 위험 급증 이후 주문 규모가 감소한 시점과 이후의 변화 양상을 살펴봅니다.", BLUE)
        grid(EMB, cols=4, bar_color=BLUE,
             sub=lambda r: f"{r['embargo']}", height_per_row=310)
        zero = sum(1 for r in EMB if sum(r["tiv"][-3:]) == 0)
        note(f"8개 사례 중 3개에서는 이후 3년간 주문 연도 TIV가 0으로 나타났습니다. 차트에 제시된 제재·내전 등의 배경을 고려하면, 이 사례들의 감소를 갈등 위험 변화에 따른 수요 감소로 단정하기 어렵습니다.", "blue")
    

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
            '<div class="d">주문 규모가 증가한 17개 사례 중 14개는 갈등 위험 급증 후 2년 이내에 정점에 이르렀습니다.</div></div>'
            f'<div class="fbox dn"><div class="tag" style="color:{BLUE}">'
            f'감소 사례 ({len(EMB)}건 전체)</div>'
            '<div class="h">거래 전면 단절</div>'
            '<div class="d">감소 사례에서는 제재·내전 등 다른 여건도 함께 살펴봐야 합니다.</div></div>'
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
