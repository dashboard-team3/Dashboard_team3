"""모듈 그래프(무기 거래 추이 · 사건 전후 비교)를 밝은 테마에 맞춘다.

이 모듈들의 그래프는 어두운 배경 기준 색으로 짜여 있다. app2.py 가 밝은 테마일 때
st.session_state["_light"] = True 를 넣어 주면, 그래프를 화면에 내보내기 직전에
어두운 배경용 색을 같은 역할의 밝은 배경용 색으로 바꾼다.
어두운 테마에서는 값이 False 라 색을 그대로 둔다.
"""
import plotly.io as pio
import streamlit as st

# 그래프 글자 글꼴: 화면 기본 글꼴(dashboard/style.css 의 나눔고딕)과 같게
FONT_FAMILY = '"Nanum Gothic", "NanumGothic", "Malgun Gothic", sans-serif'

# 보라 계열 색 (2026-10-02 정리 v2). 숫자 = 사람 눈 밝기(L*) 기준 어두운 정도 (0 흰색 → 1000 검정), 옅은 색 → 짙은 색.
#   main-N       = 라이트 · 다크 둘 다 쓰는 색      main-light-N = 라이트만      main-dark-N = 다크만      main-bg-N = 바탕색
# 화면 CSS 는 var(--color-main-…) (core/setup.py 가 :root 에 넣음), 그래프(Plotly)는 CSS 변수를 못 읽어서 C["main-…"] · color_rgba()
C = {
    # 공통
    "main-40": "#f5f3ff",          # 라이트: 옅은 칸 바탕 · 밝은 홈 바탕 끝 / 다크: 홈 큰 제목 · 지도 색 막대 시작
    "main-130": "#ddd6fe",         # 라이트: 테두리 · 구분선 · 그래프 격자 / 다크: 홈 지도 선 · 지도 색 막대
    "main-230": "#c4b5fd",         # 지도 색 막대 · 라이트 LIVE 막대 · 다크 홈 부제
    "main-350": "#a78bfa",         # 지도 색 막대 · 기준 달 점선 · 다크 강조 글자
    "main-480": "#8b5cf6",         # 그래프 선 · 종합 분석 고른 시차 띠 · 다크 강조 선 · 테두리
    "main-500": "#6366f1",         # 그래프 선 · 라이트 홈 빛 · 다크 배경 빛 번짐
    "main-570": "#7c3aed",         # 지도 색 막대 · 띠 고르기 그라데이션
    "main-740": "#4c1d95",         # 지도 색 막대 끝 (가장 진한 칸)
    "main-870": "#1e1b4b",         # 라이트: 밝은 홈 큰 제목 · 그림자 / 다크: 고른 탭 · 해석 상자 · 그래프 상자 바탕
    # 라이트만
    "main-light-70": "#ede9fe",    # 종합 분석 «핵심 분석» 뱃지 바탕
    "main-light-180": "#c7cbe0",   # 리스크 추이 지도 «기준» 나라 칸
    "main-light-380": "#818cf8",   # 밝은 홈 빛 번짐
    "main-light-650": "#4338ca",   # 강조색: 메뉴 선택 · 탭 · 소제목 번호 · 고른 버튼 · 기준 나라 테두리 (예전 #4f46e5)
    # 다크만
    "main-dark-250": "#a5b4fc",    # 홈 작은 제목
    "main-dark-410": "#8b7cf6",    # 홈 지도 면 · 별빛
    "main-dark-550": "#9333ea",    # 띠 고르기 그라데이션 끝
    "main-dark-740": "#3a3b5c",    # 리스크 추이 지도 «기준» 나라 칸 · 종합 분석 표 0선
    "main-dark-820": "#2a2a48",    # 칸 · 카드 테두리 · 지도 나라 경계선
    # 바탕색
    "main-bg-30": "#f6f7fb",       # 라이트: 페이지 · 사이드바 바탕 · 큰 칸 그라데이션 끝
    "main-bg-930": "#13142a",      # 다크: 카드 · 칸 · 지도 땅 기본 바탕
    "main-bg-940": "#10111f",      # 다크: 사이드바 · 무기 거래 수치 칸 · 묶음 바탕
    "main-bg-960": "#0b0c16",      # 다크: 화면 전체 바탕 · 밝은 칸 위 진한 글자
}
COLOR_CSS = ":root {" + " ".join(f"--color-{k}: {v};" for k, v in C.items()) + "}"


def color_rgba(name, a):
    """C[name] 에 투명도 a 를 준 rgba 글 (그래프용)."""
    h = C[name]
    return f"rgba({int(h[1:3], 16)},{int(h[3:5], 16)},{int(h[5:7], 16)},{a})"


# 어두운 테마 색 → 같은 역할의 밝은 테마 색
DARK_TO_LIGHT = {
    "#e5eaf3": "#1c1a17",   # 제목·강조 글자
    "#cbd5e1": "#4a443b",   # 기본 글자·축 글자
    "#aab4c5": "#3d3d3d",   # 보조 글자
    "#8b98ad": "#3d3d3d",   # 회색 설명
    "#94a3b8": "#3d3d3d",   # 회색 선
    "#1e293b": "#ffffff",   # 마우스 글 상자 배경
    "#334155": C["main-130"],   # 마우스 글 상자 테두리
    "#141d30": C["main-130"],   # 격자
    "#1f2b44": C["main-130"],   # 격자
    "#0b1220": "#ffffff",   # 점 테두리·바다
    "#24314f": C["main-130"],   # 지도 국경선
    "#16223f": C["main-40"],   # 지도 땅
    "#2a3a2e": "#f3ecd9",   # 지도 색 척도 시작
    "#2b3444": C["main-130"],   # 네트워크: 오늘 사건 없는 나라 점
    "#5b6578": "#a39a8c",   # 네트워크: 오늘 사건 없는 나라 이름
    "#9db4ff": "#3346a8",   # 보조 파랑 글자
    # 세부 분석 결과 탭(dashboard/surge_page.py)만 쓰는 색 — 배경 #0b1220 · 글자 #e5eaf3 · #8b98ad 는 위에 이미 있다
    "#16233c": C["main-130"],   # 격자
    "#bcbcbc": "#3d3d3d",   # 사례 칸의 작은 부제 글자
    "#9ca3af": "#000000",   # 무기 종류 «엔진» 막대 (Okabe-Ito 검정, sources/arms.py)
    "#f5c542": "#E69F00",   # 무기 거래 금색(C_ARMS · GOLD): 밝은 바탕에서 안 보여 Okabe-Ito 주황으로 (2026-10-02 팀 요청)
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
        h = fig.layout.height or 450         # 맨 위에서 24px 아래에 제목 윗선 (pad 는 안 먹어서 비율로)
        # 14px 로 두면 yanchor="top" 이 글자 윗선을 3px 밖으로 밀어 제목이 잘렸다 (2026-09-30)
        fig.update_layout(title_y=1 - 24 / h, title_yref="container", title_yanchor="top",
                          margin_t=max(fig.layout.margin.t or 0, 104))
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
