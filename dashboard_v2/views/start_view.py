"""홈 (미리보기안 3, 2026-10-01): 참고 사이트처럼 화면 전체를 쓰는 첫 화면.

page()  배경   = 어두운 남색 + 별 반짝임 + 밝은 선으로 그린 중동 지도(살짝 눕혀 원근감) + 16개국 불빛
        가운데 = 대시보드 제목 · 부제 (크게)
        아래   = 메뉴 카드 5장이 아래에서 위로 차례로 올라온다. 카드 자체를 누르면 그 메뉴로 들어간다.
홈에서는 (처음 들어왔을 때든, 메뉴에서 '홈'을 눌러 돌아왔을 때든) 왼쪽 메뉴를 접어 둔다(» 로 펼 수 있음).
카드를 누르면 그 페이지에서 메뉴를 다시 편다.
"""
import random

import plotly.graph_objects as go
import streamlit as st

from core import theme
from sources import arms

A_POS = arms.TARGET_POS

# (메뉴 이름, 설명) — 설명은 개조체 (2026-10-02 팀 요청)
MENU_CARDS = [
    ("리스크 모니터링", "GDELT 2.0 기반 중동 16개국 갈등 사건 · 15분마다 갱신"),
    ("리스크 추이", "1980년부터 국가쌍 · 국가별 월별 리스크 추이"),
    ("무기 거래 추이", "SIPRI 무기 계약 · UN Comtrade 교역 기록 기반 중동 16개국 무기 거래 흐름"),
    ("리스크와 무기 거래", "나라별 리스크와 무기 거래 연도별 비교"),
    ("종합 분석", "중동 16개국 전체 리스크 급증 해 전후 무기 주문 변화 사례 분석"),
]

CSS = """<style>
/* ── 화면 전체 배경 (밝은 테마여도 첫 화면은 밤하늘) */
.st-key-landing_bg {position: fixed !important; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background: radial-gradient(ellipse at 50% 18%, color-mix(in srgb, var(--color-main-dark-410) 22%, transparent), transparent 55%),
              radial-gradient(ellipse at 85% 75%, rgba(96,165,250,.10), transparent 50%), #0b1220 !important;}
.st-key-landing_bg::before, .st-key-landing_bg::after {content: ""; position: absolute; inset: 0;
  background-image: STARS_A; animation: twinkle 5s ease-in-out infinite;}
.st-key-landing_bg::after {background-image: STARS_B; animation-delay: 2.5s;}
@keyframes twinkle {0%, 100% {opacity: .25;} 50% {opacity: .9;}}
/* 지도: 화면 아래쪽에 깔고 살짝 눕힌다 (원근감) */
.st-key-landing_map {position: absolute !important; inset: 0 !important; width: 100vw !important; height: 100vh !important;
  display: flex !important; align-items: center !important; justify-content: center !important;
  opacity: 0; animation: mapIn 1.6s ease .2s forwards;}
.st-key-landing_map > div, .st-key-landing_map [data-testid="stElementContainer"],
.st-key-landing_map [data-testid="stFullScreenFrame"], .st-key-landing_map [data-testid="stPlotlyChart"] {
  width: 100vw !important; height: 130vh !important; flex: 0 0 auto !important;}   /* 창보다 크게 → 위아래가 살짝 잘림 */
@keyframes mapIn {to {opacity: 1;}}
.st-key-landing_map [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]) {background: transparent !important; border: 0 !important; padding: 0 !important;}
.st-key-landing_map svg {filter: drop-shadow(0 0 3px color-mix(in srgb, var(--color-main-350) 90%, transparent));}
.st-key-landing_map path.point {animation: glow 2.8s ease-in-out infinite;}
@keyframes glow {0%, 100% {stroke: rgba(254,243,199,0); stroke-width: 0;} 50% {stroke: rgba(254,243,199,.35); stroke-width: 14px;}}
/* ── 앞쪽 내용: 제목 · 카드 */
.st-key-landing {position: relative; z-index: 2; min-height: calc(100vh - 40px); padding-top: 14vh;}
.ld-k {text-align: center; font-size: 17px; font-weight: 600; letter-spacing: .32em; color: var(--color-main-dark-250) !important; opacity: 0;
  animation: fadeUp .9s ease .1s forwards;}
.ld-t {text-align: center; font-family: "A2Z", "Nanum Gothic", sans-serif !important; font-size: 50px; font-weight: 800; line-height: 1.15;
  color: var(--color-main-40) !important; margin: 14px 0 10px; text-shadow: 0 0 40px color-mix(in srgb, var(--color-main-350) 45%, transparent); opacity: 0;
  animation: fadeUp 1s ease .35s forwards;}
.ld-s {text-align: center; font-size: 30px; font-weight: 700; color: var(--color-main-130) !important; text-shadow: 0 2px 12px rgba(0,0,0,.55);
  opacity: 0; animation: fadeUp 1s ease .7s forwards;}   /* 소제목 키움 · 더 밝게 (2026-10-02) */
/* 제목 뒤 지도를 살짝 어둡게: 제목 둘레에 가장자리가 흐린 어두운 타원 */
.ld-head {position: relative; isolation: isolate;}
.ld-head::before {content: ""; position: absolute; left: 50%; top: 50%; width: min(1150px, 92vw); height: 300px;
  transform: translate(-50%, -50%); z-index: -1; pointer-events: none;
  background: radial-gradient(ellipse at center, rgba(11,18,32,.82) 0%, rgba(11,18,32,.6) 45%, rgba(11,18,32,0) 72%);}
@keyframes fadeUp {from {opacity: 0; transform: translateY(18px);} to {opacity: 1; transform: none;}}
@keyframes cardUp {from {opacity: 0; transform: translateY(80px);} to {opacity: 1; transform: none;}}
/* 카드: 흰색 50% · 흰 테두리. 카드 전체가 버튼 (위에 투명 버튼을 덮는다) */
.st-key-landing [data-testid="stHorizontalBlock"]:has([class*="st-key-ldcard_"]) {margin-top: 12vh; align-items: stretch !important;}
[class*="st-key-ldcard_"] {position: relative; height: 100%; opacity: 0; animation: cardUp .9s cubic-bezier(.2,.8,.2,1) forwards;}
.ld-card {height: 240px; box-sizing: border-box; background: rgba(0,0,0,.25); border: none; box-shadow: 0 10px 28px rgba(0,0,0,.45), 0 2px 6px rgba(0,0,0,.35);
  border-radius: 16px; padding: 22px 20px; backdrop-filter: blur(6px); transition: transform .2s ease, background .2s ease;
  display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;}   /* 내용 가운데 (2026-10-02) */
.ld-n {text-align: center; font-size: 22px; font-weight: 800; color: #ffffff !important; margin-bottom: 12px; word-break: keep-all; text-shadow: 0 1px 4px rgba(0,0,0,.6);}
.ld-d {font-size: 15px; line-height: 1.6; font-weight: 500; color: #ffffff !important; word-break: keep-all; text-shadow: 0 1px 3px rgba(0,0,0,.6);}
[class*="st-key-ldcard_"]:hover .ld-card {transform: translateY(-6px); background: rgba(0,0,0,.4);}
[class*="st-key-ldcard_"] [data-testid="stElementContainer"]:has(button) {position: absolute !important; inset: 0; z-index: 3; margin: 0 !important;
  width: 100% !important; height: 100% !important;}
[class*="st-key-ldcard_"] [data-testid="stElementContainer"]:has(button) > div,
[class*="st-key-ldcard_"] [data-testid="stButton"],
[class*="st-key-ldcard_"] [data-testid="stButton"] > div,
[class*="st-key-ldcard_"] [data-testid="stElementContainer"]:has(button) button {width: 100% !important; height: 100% !important; max-width: none !important;}
[class*="st-key-ldcard_"] button {opacity: 0 !important; cursor: pointer;}
[class*="st-key-ldcard_"] [data-testid="stMarkdownContainer"] {margin-bottom: 0 !important;}
@media (max-width: 1400px) {
  .ld-t {
    font-size: 42px;
  } 
  .ld-n {
    font-size: 19px;
  } 
  .ld-d {
    font-size: 14px;
  } 
}

@media (max-width: 1150px) {
  .ld-card {
    height: 280px;
  }
}

@media (max-width: 1032px) {
  .st-key-landing [data-testid="stHorizontalBlock"]:has([class*="st-key-ldcard_"]) {
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 16px !important;
  }

  .st-key-landing [data-testid="stHorizontalBlock"]:has([class*="st-key-ldcard_"])
  > [data-testid="stColumn"] {
    width: calc((100% - 16px) / 2) !important;
    min-width: 0 !important;
    flex: 0 0 calc((100% - 16px) / 2) !important;
  }

  .ld-card {
    height: 180px;
  }
}

@media (max-width: 640px) {
  .st-key-landing [data-testid="stHorizontalBlock"]:has([class*="st-key-ldcard_"]) {
    flex-direction: column !important;
  }
  .st-key-landing [data-testid="stHorizontalBlock"]:has([class*="st-key-ldcard_"])
  > [data-testid="stColumn"] {
    width: 100% !important;
    min-width: 100% !important;
    flex: 1 1 auto !important;
  }

  .ld-t {
    font-size: 34px;
  }
  .ld-s {
    font-size: 22px;
  }
  .ld-card {
    height: 180px;
  }
}
HIDE
</style>"""

# 홈에서는: 본문 위 여백을 없애고 화면 폭 전체로 (왼쪽 메뉴는 없애지 않고 접어 둔다 → 아래 COLLAPSE)
HIDE_SIDEBAR = """
header[data-testid="stHeader"] {background: transparent !important; backdrop-filter: none !important; -webkit-backdrop-filter: none !important; box-shadow: none !important;}
/* 밝은 테마여도 시작 화면은 밤하늘: 밝은 테마 CSS 가 칠하는 흰 바탕을 덮는다 */
html[data-theme="light"] .stApp, html[data-theme="light"] [data-testid="stAppViewContainer"], html[data-theme="light"] [data-testid="stMain"] {background: #0b1220 !important;}
html[data-theme="light"] header[data-testid="stHeader"] {background: transparent !important; border: 0 !important;}   /* 맨 위 띠가 지도를 가리지 않게 */
html[data-theme="light"] header[data-testid="stHeader"] * {color: #cbd5e1 !important;}
html[data-theme="light"] [data-testid="stMain"] .st-key-landing_map [data-testid="stElementContainer"]:has(> [data-testid="stFullScreenFrame"] > [data-testid="stPlotlyChart"]) {background: transparent !important; border: 0 !important;}
[data-testid="stMainBlockContainer"] {max-width: 1400px !important; padding-top: 0 !important;}
"""

# 밝은 테마 홈 (2026-10-02): 밤하늘 대신 밝은 인디고 톤. 지도 선 · 점 색은 _line_map(light=True) 가 바꾼다
LIGHT = """
html[data-theme="light"] .stApp, html[data-theme="light"] [data-testid="stAppViewContainer"], html[data-theme="light"] [data-testid="stMain"] {background: var(--color-main-bg-30) !important;}
html[data-theme="light"] header[data-testid="stHeader"] {background: transparent !important; border: 0 !important;}
html[data-theme="light"] [data-testid="stMain"] .st-key-landing_map [data-testid="stElementContainer"]:has(> [data-testid="stFullScreenFrame"] > [data-testid="stPlotlyChart"]) {background: transparent !important; border: 0 !important;}
.st-key-landing_bg {background: radial-gradient(ellipse at 50% 16%, color-mix(in srgb, var(--color-main-light-380) 28%, transparent), transparent 55%),
                                radial-gradient(ellipse at 85% 80%, color-mix(in srgb, var(--color-main-350) 20%, transparent), transparent 50%),
                                radial-gradient(ellipse at 10% 85%, rgba(96,165,250,.14), transparent 45%),
                                linear-gradient(180deg, #fbfbff 0%, var(--color-main-40) 100%) !important;}
.st-key-landing_map svg {filter: drop-shadow(0 0 3px color-mix(in srgb, var(--color-main-500) 35%, transparent));}
.st-key-landing_map path.point {animation: glowL 2.8s ease-in-out infinite;}
@keyframes glowL {0%, 100% {stroke: color-mix(in srgb, var(--color-main-500) 0%, transparent); stroke-width: 0;} 50% {stroke: color-mix(in srgb, var(--color-main-500) 25%, transparent); stroke-width: 14px;}}
.ld-k {color: var(--color-main-500) !important;}
.ld-t {color: var(--color-main-870) !important; text-shadow: 0 2px 24px rgba(255,255,255,.9);}
.ld-s {color: var(--color-main-light-650) !important; text-shadow: none;}
.ld-head::before {background: radial-gradient(ellipse at center, rgba(248,249,255,.9) 0%, rgba(248,249,255,.7) 45%, rgba(248,249,255,0) 72%);}
.ld-card {background: rgba(255,255,255,.72); box-shadow: 0 10px 28px color-mix(in srgb, var(--color-main-light-650) 14%, transparent), 0 2px 6px color-mix(in srgb, var(--color-main-870) 8%, transparent);}
.ld-n {color: var(--color-main-870) !important; text-shadow: none;}
.ld-d {color: #374151 !important; text-shadow: none;}
[class*="st-key-ldcard_"]:hover .ld-card {background: rgba(255,255,255,.92);}
"""


# 왼쪽 메뉴 접기 / 펴기: Streamlit 의 접기(«) · 펴기(») 버튼을 대신 눌러 준다 (메뉴가 다 그려질 때까지 0.1초마다 최대 4초 확인)
_TOGGLE = """<script>(() => {{ let n = 0; const t = setInterval(() => {{ n++;
  const sb = document.querySelector('section[data-testid="stSidebar"]');
  if (sb && sb.getAttribute('aria-expanded') === '{want_now}') {{
    const b = document.querySelector('{button}'); if (b) {{ b.click(); clearInterval(t); }} }}
  else if (sb) clearInterval(t);
  if (n > 40) clearInterval(t); }}, 100); }})(); /* {stamp} */</script>"""
COLLAPSE = dict(want_now="true", button='[data-testid="stSidebarCollapseButton"] button')
EXPAND = dict(want_now="false", button='[data-testid="stExpandSidebarButton"]')


def _toggle_sidebar(kind):
    import time
    st.html(_TOGGLE.format(stamp=time.time(), **kind), unsafe_allow_javascript=True)


def reopen_sidebar():
    """홈 카드로 들어온 페이지라면 접어 둔 왼쪽 메뉴를 다시 편다 (app.py 가 홈이 아닐 때 부른다)."""
    if st.session_state.pop("open_sidebar", False):
        _toggle_sidebar(EXPAND)


def _go(name):
    """카드를 누르면 그 메뉴로 간다 (그 페이지부터는 왼쪽 메뉴가 보인다).
    리스크 모니터링 · 리스크 추이 카드는 «리스크 모니터링» 페이지의 그 버튼으로 연다 (2026-10-01).
    «리스크 모니터링» 카드(예전 이름 «실시간 모니터링», 2026-10-02 hnaa0 이름 변경)는 늘 «실시간 모니터링» 버튼으로."""
    if name in ("리스크 모니터링", "실시간 모니터링", "리스크 추이"):
        st.session_state["mon_view"] = "리스크 추이" if name == "리스크 추이" else "실시간 모니터링"
        name = "리스크 모니터링"
    st.session_state["menu_page"] = name
    st.session_state["page_keep"] = name
    st.session_state["open_sidebar"] = True            # 그 페이지에서 접어 둔 왼쪽 메뉴를 다시 편다


def _stars(n, seed, rgb="255,255,255"):
    """배경 별: 작은 점 n개 (같은 seed 면 늘 같은 자리). 밝은 테마는 인디고 점 (rgb)."""
    rnd = random.Random(seed)
    return ", ".join(f"radial-gradient(1.{rnd.randint(0, 9)}px 1.{rnd.randint(0, 9)}px at {rnd.uniform(0, 100):.1f}% "
                     f"{rnd.uniform(0, 100):.1f}%, rgba({rgb},{rnd.uniform(.35, .9):.2f}), transparent)" for _ in range(n))


def _line_map(light=False):
    """밝은 선으로 그린 중동 16개국 경계만 (다른 나라 · 바다 · 해안선은 그리지 않음) + 16개국 불빛.
    fitbounds='locations' 로 16개국이 그림을 꽉 채우게 한다."""
    codes = list(A_POS)
    fig = go.Figure(go.Choropleth(
        locations=codes, z=[1] * len(codes), locationmode="ISO-3", showscale=False, hoverinfo="skip",
        colorscale=[[0, theme.color_rgba("main-500", .10) if light else theme.color_rgba("main-dark-410", .10)], [1, theme.color_rgba("main-500", .10) if light else theme.color_rgba("main-dark-410", .10)]],
        marker_line_color=theme.color_rgba("main-light-650", .75) if light else theme.color_rgba("main-130", .95), marker_line_width=1.6))
    fig.add_trace(go.Scattergeo(
        lat=[A_POS[c][0] for c in codes], lon=[A_POS[c][1] for c in codes], mode="markers", hoverinfo="skip",
        marker=dict(size=9, color=theme.C["main-light-650"] if light else "#fef3c7", line=dict(width=0)), showlegend=False))
    fig.update_layout(autosize=True, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", dragmode=False,
                      geo=dict(projection_type="mercator", fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)"))
    return fig


def page():
    light = theme.is_light()
    # 밝은 테마: 밤하늘로 덮던 규칙 대신 밝은 홈 (2026-10-02). 위 여백 · 폭 규칙은 그대로 쓴다
    hide = (HIDE_SIDEBAR.split("/* 밝은 테마여도")[0] + LIGHT
            + '[data-testid="stMainBlockContainer"] {max-width: 1400px !important; padding-top: 0 !important;}') if light else HIDE_SIDEBAR
    star = "79,70,229" if light else "255,255,255"
    _toggle_sidebar(COLLAPSE)                              # 홈은 언제 와도 왼쪽 메뉴를 접은 채로
    st.markdown(CSS.replace("STARS_A", _stars(50, 1, star)).replace("STARS_B", _stars(50, 2, star)).replace("HIDE", hide),
                unsafe_allow_html=True)
    with st.container(key="landing_bg"):                     # 화면 전체 배경 (뒤에 고정)
        with st.container(key="landing_map"):
            st.plotly_chart(_line_map(light), width="stretch", height="stretch",      # 화면(브라우저 창) 크기에 맞춰 늘어난다
                            config={"displayModeBar": False, "staticPlot": True, "responsive": True})
    with st.container(key="landing"):                        # 앞쪽 내용
        st.markdown('<div class="ld-head"><div class="ld-k">DATA · 1980–2026 · MIDDLE EAST 16</div>'
                    '<div class="ld-t">Conflict Risk &amp; Arms Dashboard</div>'
                    '<div class="ld-s">중동 지역 갈등 편중도와 무기 거래</div></div>', unsafe_allow_html=True)
        cols = st.columns(len(MENU_CARDS), gap="medium")
        for i, (col, (name, desc)) in enumerate(zip(cols, MENU_CARDS)):
            with col, st.container(key=f"ldcard_{i}"):
                st.markdown(f'<style>.st-key-ldcard_{i} {{animation-delay: {1.0 + 0.15 * i:.2f}s;}}</style>'
                            f'<div class="ld-card"><div class="ld-n">{name}</div><div class="ld-d">{desc}</div></div>',
                            unsafe_allow_html=True)
                st.button(name, key=f"go_{name}", on_click=_go, args=(name,))
