"""모듈 그래프(무기 거래 추이 · 사건 전후 비교)를 밝은 테마에 맞춘다.

이 모듈들의 그래프는 어두운 배경 기준 색으로 짜여 있다. app2.py 가 밝은 테마일 때
st.session_state["_light"] = True 를 넣어 주면, 그래프를 화면에 내보내기 직전에
어두운 배경용 색을 같은 역할의 밝은 배경용 색으로 바꾼다.
어두운 테마에서는 값이 False 라 색을 그대로 둔다.
"""
import plotly.io as pio
import streamlit as st

# 그래프 글자 글꼴: 화면 기본 글꼴(dashboard/style2.css 의 나눔고딕)과 같게
FONT_FAMILY = '"Nanum Gothic", "NanumGothic", "Malgun Gothic", sans-serif'

# 어두운 테마 색 → 같은 역할의 밝은 테마 색
DARK_TO_LIGHT = {
    "#e5eaf3": "#1c1a17",   # 제목·강조 글자
    "#cbd5e1": "#4a443b",   # 기본 글자·축 글자
    "#aab4c5": "#6b6255",   # 보조 글자
    "#8b98ad": "#6b6255",   # 회색 설명
    "#94a3b8": "#8a8175",   # 회색 선
    "#1e293b": "#ffffff",   # 마우스 글 상자 배경
    "#334155": "#d8cfbd",   # 마우스 글 상자 테두리
    "#141d30": "#e5e0d5",   # 격자
    "#1f2b44": "#e5e0d5",   # 격자
    "#0b1220": "#ffffff",   # 점 테두리·바다
    "#24314f": "#d8cfbd",   # 지도 국경선
    "#16223f": "#efe9dd",   # 지도 땅
    "#2a3a2e": "#f3ecd9",   # 지도 색 척도 시작
    "#2b3444": "#d8cfbd",   # 네트워크: 오늘 사건 없는 나라 점
    "#5b6578": "#a39a8c",   # 네트워크: 오늘 사건 없는 나라 이름
    "#9db4ff": "#3346a8",   # 보조 파랑 글자
    # 세부 분석 결과 탭(dashboard/surge_page.py)만 쓰는 색 — 배경 #0b1220 · 글자 #e5eaf3 · #8b98ad 는 위에 이미 있다
    "#16233c": "#e5e0d5",   # 격자
    "#bcbcbc": "#6b6255",   # 사례 칸의 작은 부제 글자
}


def is_light():
    return bool(st.session_state.get("_light", False))


def adapt(fig):
    """그래프 글꼴을 나눔고딕으로 맞추고, 밝은 테마면 어두운 배경용 색을 바꾼 새 그림을, 아니면 그대로 돌려준다."""
    # 제목 · 범례는 Streamlit 그래프 테마가 자기 글꼴(Source Sans)을 따로 붙이므로 함께 덮는다
    fig.update_layout(font_family=FONT_FAMILY, legend_font_family=FONT_FAMILY, hoverlabel_font_family=FONT_FAMILY)
    if fig.layout.title.text: fig.update_layout(title_font_family=FONT_FAMILY)   # 제목 없는 그림에 넣으면 'undefined' 가 뜬다
    # v2: 그래프 글자도 네 단계 (제목 19 · 마우스 설명 16 · 축 숫자 · 범례 · 주석 14)
    fig.update_layout(font_size=14, legend_font_size=14, hoverlabel_font_size=16)
    if fig.layout.title.text: fig.update_layout(title_font_size=19)
    t = fig.layout.title.text or ""
    if "<br>" in t:                        # 두 줄 제목(ctitle): 맨 위에 붙이고 범례와 안 겹치게 위 여백 확보
        h = fig.layout.height or 450         # 맨 위에서 14px 아래에 제목 윗선 (pad 는 안 먹어서 비율로)
        fig.update_layout(title_y=1 - 14 / h, title_yref="container", title_yanchor="top",
                          margin_t=max(fig.layout.margin.t or 0, 96))
    fig.update_xaxes(tickfont_size=14, title_font_size=16)
    fig.update_yaxes(tickfont_size=14, title_font_size=16)
    for ann in fig.layout.annotations or []:
        ann.font.size = 16 if (ann.font.size or 14) >= 15 else 14
    if not is_light():
        return fig
    j = fig.to_json()
    for dark, light in DARK_TO_LIGHT.items():
        j = j.replace(dark, light).replace(dark.upper(), light)
    return pio.from_json(j)
