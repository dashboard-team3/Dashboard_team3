"""여러 페이지가 함께 쓰는 화면 도우미 (원본 app2.py 의 2. 공통 도우미).
색 · 그래프 기본 설정 · 소제목 상자(section_head) · 리스크 계산식 · ⓘ 계산 기준 팝오버(info)."""
import html as _html
import re as _re

import streamlit as st

from core.theme import C


def _plain(text):
    """말풍선용: HTML 태그 · 마크다운 ** 를 걷어 낸 글자."""
    return _re.sub(r"<[^>]+>", "", str(text)).replace("**", "").strip()


def tip(label, text, cls="", style=""):
    """마우스를 올리면 설명(text)이 뜨는 글자 (CSS 말풍선 .tip). 화면에는 label 만 보인다.
    cls 에 \"r\" 를 넣으면 말풍선이 오른쪽 끝에 맞춰 뜬다 (화면 오른쪽 가장자리용)."""
    st_attr = f' style="{style}"' if style else ""
    return f'<span class="tip {cls}" data-tip="{_html.escape(_plain(text), quote=True)}"{st_attr}>{label}</span>'


# 정보 아이콘 (Bootstrap info-circle, 2026-10-02 팀 요청으로 ⓘ 글자 대신). 색은 .tipi 의 글자색을 따른다
INFO_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-info-circle" viewBox="0 0 16 16"><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14m0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16"/><path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0"/></svg>'


def info_icon(text, cls=""):
    """정보 아이콘 하나: 마우스를 올리면 설명. 긴 설명 글을 화면에서 빼고 여기 넣는다."""
    return tip(INFO_SVG, text, "tipi " + cls)


# 색 규칙: 뜻 하나에 색 하나 (그래프마다 같은 뜻은 같은 색)
C_RISK, C_COOP, C_ARMS, C_MUTE, C_TEXT = "#f87171", "#60a5fa", "#f5c542", "#475569", "#e5eaf3"

# 리스크 분석 선 색 — 고른 나라마다 다른 색 (최대 5곳이라 다섯이면 충분하다).
# «상태»(등급 뱃지·범례)는 신호등 색(파랑·초록·노랑·주황·빨강)을 쓰므로,
# «범주»(나라 구분)는 초록·노랑·주황을 피해 상태로 오해되지 않게 한다. 첫 색은 강조용. (2026-09-30)
# 밝은 테마에서도 읽히는 값이라 theme.adapt 의 색 치환 목록에 넣지 않는다.
LINE_COLORS = ["#e11d48", C["main-500"], "#06b6d4", C["main-480"], "#0ea5e9"]
CHART_CONFIG = {"displayModeBar": False}   # 지도 빼고는 카메라·줌 아이콘을 숨긴다


DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#cbd5e1", size=15),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e5eaf3", size=15)),
)


def section_head(no, title, sub):
    """탭 첫 줄: 번호 · 제목 · 한 줄 설명. 지금 어느 화면에서 무엇을 보는지 바로 알게 한다."""
    # v2: 한 줄 설명(sub)은 화면에서 빼고 제목 옆 ⓘ 말풍선으로 (마우스를 올리면 보임)
    st.markdown(f'<div class="sec"><div class="sec-no">{no}</div><div><div class="sec-t">{title} {info_icon(sub)}</div>'
                f'</div></div>', unsafe_allow_html=True)


# 리스크 계산식 (ⓘ 계산 기준에 그대로 보여 준다). 갈등 = 빨강, 협력 = 초록
RISK_FORMULA = (
    '<div class="formula"><span class="f-lhs">Risk =</span><span class="frac">'
    '<span class="num"><b class="f-h">Σ갈등</b>(|Goldstein| × 언급수)</span>'
    '<span class="den"><b class="f-h">Σ갈등</b>(|Goldstein| × 언급수) + <b class="f-c">Σ협력</b>(Goldstein × 언급수)</span>'
    '</span></div>'
    '<div class="f-note">산출 단위: <b>일별</b> · 협력 가중 합이 음수인 경우 0으로 처리 · '
    '<b>월 리스크 = 해당 월의 일별 리스크 평균</b>(사건 미발생일은 0으로 반영, 달력 일수 기준) · '
    '연 리스크 = 해당 연도의 일별 리스크 평균</div>')


# 급증 판정 기준 (데이터 소개의 리스크 아래). 세 조건을 모두 만족한 달만 급증으로 본다
SURGE_FORMULA = (
    '<div class="di-cond">'
    '<div class="c-row"><span class="c-no">①</span>'
    '<span class="c-f">risk(t) &gt; 평소(t) + 2σ(t)</span>'
    '<span class="c-why">평상시 변동 범위 초과</span></div>'
    '<div class="c-row"><span class="c-no">②</span>'
    '<span class="c-f">risk(t) − 평소(t) ≥ 0.1</span>'
    '<span class="c-why">최소 상승폭</span></div>'
    '<div class="c-row"><span class="c-no">③</span>'
    '<span class="c-f">risk(t) ≥ 0.3</span>'
    '<span class="c-why">최소 수준 · 갈등 보도가 희박한 관계 제외</span></div>'
    '<div class="c-def">평소(t) = mean( risk(t−12) … risk(t−1) )'
    '&nbsp;&nbsp;·&nbsp;&nbsp;σ(t) = max( std( risk(t−12) … risk(t−1) ), 0.05 )</div>'
    '</div>')

# 시차 상관 (피어슨). 갈등이 오른 해와 0~3년 뒤 무기 주문의 동반 변화
PEARSON_FORMULA = (
    '<div class="formula"><span class="f-lhs">r =</span><span class="frac">'
    '<span class="num">Σ(x − m<sub>x</sub>)(y − m<sub>y</sub>)</span>'
    '<span class="den">√[ Σ(x − m<sub>x</sub>)² × Σ(y − m<sub>y</sub>)² ]</span>'
    '</span></div>'
    '<div class="c-def">x = 연 리스크(t)&nbsp;&nbsp;·&nbsp;&nbsp;y = log(1 + 주문 TIV)(t+k), k = 0~3년'
    '&nbsp;&nbsp;·&nbsp;&nbsp;m<sub>x</sub> · m<sub>y</sub> = 각각의 평균</div>')


def info(text, formula=False):
    """긴 계산 설명은 ⓘ 팝오버 안에 넣어 화면을 비운다. formula=True 면 맨 위에 리스크 계산식."""
    with st.popover("ⓘ 계산 기준", use_container_width=False):
        if formula:
            st.markdown(RISK_FORMULA, unsafe_allow_html=True)
        st.markdown(text)


# 주요 단어 풀이 (페이지 부제에서 마우스를 올리면 보임)
TERMS = {
    "GDELT 2.0": "전 세계 뉴스에서 행위 주체·대상·사건 정보를 추출한 데이터 · 15분 단위 갱신",
    "GDELT": "전 세계 뉴스에서 행위 주체·대상·사건 정보를 추출한 데이터 · 1.0: 1979년부터 일별 제공 · 2.0: 2015년부터 15분 단위 갱신",
    "실시간 갈등 뉴스": "선정 사건 코드 20개에 해당하는 갈등 사건 · 유형: 무력 사용·위협 및 요구·군사태세·제재 및 단절",
    "UTC": "협정세계시 · 한국 시간 = UTC + 9시간 · UTC 기준 0시 = 한국 시간 오전 9시",
    "리스크": "보도된 사건의 가중 합에서 갈등이 차지하는 비중(0~1) · 실제 교전 강도를 직접 나타내는 지표는 아님",
    "국가쌍별": "A→B: A가 행위 주체(Actor1), B가 행위 대상(Actor2)으로 기록된 사건 기준 · 기사에 기록된 행위 방향 구분 · 실제 선제공격 여부와는 구별",
    "국가별": "해당 국가가 관여한 15개 국가쌍의 갈등·협력 가중 합을 통합하여 산출한 리스크 · 개별 국가쌍 리스크의 단순 평균과는 구별",
    "12개월 이동평균": "해당 월을 포함한 최근 12개월의 평균 · 월별 변동을 완화하여 장기 추세 확인",
    "SIPRI": "스톡홀름 국제평화연구소의 주요 재래식 무기 이전 데이터 · 본 대시보드: 주문 연도 기준 TIV 활용",
    "UN Comtrade": "유엔의 국가 간 상품 무역 통계 · 본 대시보드: 군용 품목 6개의 교역액 활용 · 수출국 신고액 기준",
    "TIV": "SIPRI의 주요 재래식 무기 이전 규모 비교 지표 · 실제 거래 금액과는 구별 · 본 대시보드: 주문 연도 기준 집계",
    "급증": "직전 12개월 평균 대비 상승폭이 표준편차의 2배 초과·0.1 이상이고, 리스크가 0.3 이상인 월 · 세 조건 동시 충족",
}


def term(word, desc=None):
    """부제 속 주요 단어: 밑줄이 있고, 마우스를 올리면 풀이가 뜬다 (풀이는 TERMS 에서, 없으면 desc)."""
    return tip(word, desc or TERMS.get(word, ""), "term")


def brand():
    """모든 페이지 맨 위: 대시보드 제목 · 부제 (사이드바를 접어도 보이게)."""
    st.markdown('<div class="brand">Conflict Risk &amp; Arms Dashboard<span>중동 지역 갈등 리스크와 무기 거래</span></div>',
                unsafe_allow_html=True)


def page_sub(html):
    """페이지 제목 바로 아래 한 줄 부제. 주요 단어는 term() 으로 감싸 마우스 말풍선을 단다."""
    st.markdown(f'<div class="page-sub">{html}</div>', unsafe_allow_html=True)


def ctitle(main, sub=""):
    """차트 제목: 무엇을 나타내는지 짧게(main) + 둘째 줄 작은 글자로 필터 · 기간 · 읽는 법(sub).
    두 줄 제목의 위치 · 위 여백은 core/theme.py adapt 가 맞춘다."""
    return main + (f"<br><span style='font-size:14px;color:#8b98ad'>{sub}</span>" if sub else "")


def tabbar(label, options, key, default=None, **kw):
    """페이지 안 «세부 보기» 고르기: 화면 폭을 꽉 채운 띠 모양 (고른 칸만 진하게). (2026-09-30)
    작은 알약 여러 개보다, 지금 어느 쪽을 보고 있는지가 한눈에 들어온다.
    모양은 style.css 의 [class*="st-key-tabbar-"] 규칙이 맡는다 (상자 key 로 그 위젯만 고른다)."""
    first = default or list(options)[0]
    with st.container(key=f"tabbar-{key}"):
        return st.segmented_control(label, options, default=first, key=key,
                                    label_visibility="collapsed", **kw) or first

def page_backdrop(blur=10, dim=0.38, light_opacity=0.45):
    """(2026-10-02) 홈 화면 배경(중동 지도)을 흐리게 해서 다른 페이지 뒤에 깐다.
    어두운 테마 = assets/home_bg.jpg 를 어둡게 (밝기 dim), 밝은 테마 = assets/home_bg_light.jpg 를 옅게 (불투명도 light_opacity).
    그림은 홈 배경을 카드 · 제목 없이 찍은 것."""
    import base64
    from pathlib import Path
    a = Path(__file__).resolve().parent.parent / "assets"
    css = []
    if (a / "home_bg.jpg").exists():
        d = base64.b64encode((a / "home_bg.jpg").read_bytes()).decode()
        css.append(f"""html:not([data-theme="light"]) .stApp::before {{content: ""; position: fixed; inset: -40px; z-index: 0; pointer-events: none;
            background: url(data:image/jpeg;base64,{d}) center / cover no-repeat; filter: blur({blur}px) brightness({dim}) saturate(.9);}}""")
    if (a / "home_bg_light.jpg").exists():
        d = base64.b64encode((a / "home_bg_light.jpg").read_bytes()).decode()
        css.append(f"""html[data-theme="light"] .stApp::before {{content: ""; position: fixed; inset: -40px; z-index: 0; pointer-events: none;
            background: url(data:image/jpeg;base64,{d}) center / cover no-repeat; filter: blur({blur}px); opacity: {light_opacity};}}""")
    if not css:
        return
    # 밝은 테마 CSS 가 본문 · 위 띠를 흰색으로 칠해서(html[data-theme] 로 더 강함) 같은 세기로 투명하게 덮는다
    css.append("""html body [data-testid="stAppViewContainer"], html[data-theme] body [data-testid="stAppViewContainer"] {position: relative; z-index: 1; background: transparent !important;}
      html body [data-testid="stMain"], html[data-theme] body [data-testid="stMain"],
      html body header[data-testid="stHeader"], html[data-theme] body header[data-testid="stHeader"] {background: transparent !important;}""")
    st.markdown("<style>" + " ".join(css) + "</style>", unsafe_allow_html=True)
