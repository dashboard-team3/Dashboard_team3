"""여러 페이지가 함께 쓰는 화면 도우미 (원본 app2.py 의 2. 공통 도우미).
색 · 그래프 기본 설정 · 소제목 상자(section_head) · 리스크 계산식 · ⓘ 계산 기준 팝오버(info)."""
import html as _html
import re as _re

import streamlit as st


def _plain(text):
    """말풍선용: HTML 태그 · 마크다운 ** 를 걷어 낸 글자."""
    return _re.sub(r"<[^>]+>", "", str(text)).replace("**", "").strip()


def tip(label, text, cls="", style=""):
    """마우스를 올리면 설명(text)이 뜨는 글자 (CSS 말풍선 .tip). 화면에는 label 만 보인다.
    cls 에 \"r\" 를 넣으면 말풍선이 오른쪽 끝에 맞춰 뜬다 (화면 오른쪽 가장자리용)."""
    st_attr = f' style="{style}"' if style else ""
    return f'<span class="tip {cls}" data-tip="{_html.escape(_plain(text), quote=True)}"{st_attr}>{label}</span>'


def info_icon(text, cls=""):
    """ⓘ 하나: 마우스를 올리면 설명. 긴 설명 글을 화면에서 빼고 여기 넣는다."""
    return tip("ⓘ", text, "tipi " + cls)


# 색 규칙: 뜻 하나에 색 하나 (그래프마다 같은 뜻은 같은 색)
C_RISK, C_COOP, C_ARMS, C_MUTE, C_TEXT = "#f87171", "#60a5fa", "#f5c542", "#475569", "#e5eaf3"

# 리스크 분석 선 색 — 고른 나라마다 다른 색 (최대 5곳이라 다섯이면 충분하다).
# «상태»(등급 뱃지·범례)는 신호등 색(파랑·초록·노랑·주황·빨강)을 쓰므로,
# «범주»(나라 구분)는 초록·노랑·주황을 피해 상태로 오해되지 않게 한다. 첫 색은 강조용. (2026-09-30)
# 밝은 테마에서도 읽히는 값이라 theme.adapt 의 색 치환 목록에 넣지 않는다.
LINE_COLORS = ["#e11d48", "#6366f1", "#06b6d4", "#8b5cf6", "#0ea5e9"]
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
    '<div class="f-note">위 식은 <b>하루</b> 값입니다. 협력 합이 음수인 날은 0으로 자르고, '
    '<b>월 리스크 = 그 달 모든 날의 평균</b>(사건이 없는 날은 0으로 넣어 달력 일수로 나눔). '
    '연 리스크 = 그 해 모든 날의 평균.</div>')


def info(text, formula=False):
    """긴 계산 설명은 ⓘ 팝오버 안에 넣어 화면을 비운다. formula=True 면 맨 위에 리스크 계산식."""
    with st.popover("ⓘ 계산 기준", use_container_width=False):
        if formula:
            st.markdown(RISK_FORMULA, unsafe_allow_html=True)
        st.markdown(text)


# 주요 단어 풀이 (페이지 부제에서 마우스를 올리면 보임)
TERMS = {
    "GDELT 2.0": "GDELT 는 전 세계 뉴스를 15분마다 갱신해, 누가 누구에게 무엇을 했는지 사건 정보로 제공합니다.",
    "GDELT": "전 세계 뉴스에서 '누가 누구에게 무엇을 했는지' 자동으로 뽑은 사건 자료. 1.0 은 1979년부터 일별, 2.0 은 15분마다.",
    "실시간 갈등 뉴스": "사건 코드 20개 — 무력사용 · 위협·요구 · 군사태세 · 제재·단절 — 에 해당하는 사건만 모았습니다.",
    "UTC": "세계 표준시. 한국 시간 = UTC + 9시간 (UTC 오늘 0시 = 한국 오전 9시)",
    "리스크": "두 나라 사이 보도된 사건의 무게 가운데 갈등이 차지하는 비중 (0~1). 실제 전투 세기가 아니라 보도의 비중입니다.",
    "국가쌍별": "A → B는 기사에서 A가 Actor1, B가 Actor2로 기록된 사건을 집계합니다. 방향은 기사에서 표현된 행위의 주체와 대상을 구분하며, A가 먼저 공격했다는 의미는 아닙니다.",
    "국가별": "한 나라가 낀 15개 국가쌍의 갈등 · 협력을 먼저 모두 합친 뒤 나눈 값 (국가쌍 리스크의 평균이 아님).",
    "12개월 이동평균": "그 달을 포함한 지난 12개월 평균을 의미합니다. 달마다 튀는 값을 눌러 흐름만 보이게 합니다.",
    "SIPRI": "스톡홀름 국제평화연구소의 주요 재래식 무기 이전 기록. 계약마다 주문 연도와 TIV 가 있습니다.",
    "UN Comtrade": "UN 국가 간 무역 통계. 여기서는 군용 품목 6개의 교역액(달러, 수출국이 신고한 값).",
    "TIV": "SIPRI 의 무기 가치 지표. 달러 금액이 아니고, 연도는 주문 연도입니다 (실제 인도는 몇 해 뒤).",
    "급증": "평소(직전 12개월)보다 크게 튄 달: 표준편차 2배 넘게 · 0.1 이상 오르고 · 리스크 0.3 이상.",
}


def term(word, desc=None):
    """부제 속 주요 단어: 밑줄이 있고, 마우스를 올리면 풀이가 뜬다 (풀이는 TERMS 에서, 없으면 desc)."""
    return tip(word, desc or TERMS.get(word, ""), "term")


def brand():
    """모든 페이지 맨 위: 대시보드 제목 · 부제 (사이드바를 접어도 보이게)."""
    st.markdown('<div class="brand">Conflict Risk &amp; Arms Dashboard<span>중동 지역 갈등 편중도와 무기 거래</span></div>',
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
    모양은 style2.css 의 [class*="st-key-tabbar-"] 규칙이 맡는다 (상자 key 로 그 위젯만 고른다)."""
    first = default or list(options)[0]
    with st.container(key=f"tabbar-{key}"):
        return st.segmented_control(label, options, default=first, key=key,
                                    label_visibility="collapsed", **kw) or first

def page_backdrop(blur=10, dim=0.38):
    """(2026-10-02) 홈 화면 배경(중동 지도 · 별)을 어둡게 · 흐리게 해서 다른 페이지 뒤에 깐다.
    그림은 assets/home_bg.jpg (홈 배경을 카드 · 제목 없이 찍은 것). 밝은 테마에는 깔지 않는다."""
    import base64
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent / "assets" / "home_bg.jpg"
    if not f.exists():
        return
    data = base64.b64encode(f.read_bytes()).decode()
    st.markdown(f"""<style>
      html:not([data-theme="light"]) .stApp::before {{content: ""; position: fixed; inset: -40px; z-index: 0; pointer-events: none;
        background: url(data:image/jpeg;base64,{data}) center / cover no-repeat;
        filter: blur({blur}px) brightness({dim}) saturate(.9);}}
      html:not([data-theme="light"]) [data-testid="stAppViewContainer"] {{position: relative; z-index: 1; background: transparent !important;}}
      html:not([data-theme="light"]) [data-testid="stMain"], html:not([data-theme="light"]) [data-testid="stHeader"] {{background: transparent !important;}}
    </style>""", unsafe_allow_html=True)
