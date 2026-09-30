"""Conflict Risk & Arms Dashboard — v2 (교수님 의견 반영 · 페이지별 모듈).

    streamlit run app.py --server.port 8503

이 파일은 순서만 정한다. 실제 화면은 페이지마다 views/ 의 한 파일이 그린다.
  core/     공통 — paths(경로) · setup(페이지 설정 · CSS · 테마) · ui(색 · 소제목 · ⓘ) · sidebar(메뉴 · 필터 · 수집 시각) · theme(그래프 글꼴 · 색)
  views/    페이지 — realtime_view ① · risk_view ② · arms_view ③ · risk_arms_view ④ (+ surge_view 세부 분석) · data_intro_view ⑤
  sources/  자료 읽기 · 계산 — realtime · relations · arms · surge (자료는 원본 pjL/data 를 같이 씀)
  styles/   style2.css (기본 어두운) · style_light.css (밝은 테마)
원본 pjL/app2.py 와 화면 내용은 같고, 디자인(글자 크기 4가지 · 카드 · 2단 · 필터는 사이드바)만 다르다.
"""
from core import setup, sidebar, ui

LIGHT = setup.setup()                  # 1. 페이지 설정 · CSS · 밝은 테마 (맨 먼저)
page = sidebar.menu()                  # 2. 사이드바 제목 · 메뉴

from views import start_view, realtime_view, risk_view, arms_view, risk_arms_view, data_intro_view   # noqa: E402

PAGES = {                              # 3. 메뉴 이름 → 그 페이지를 그리는 함수
    "홈": start_view.page,         #    처음 보는 사람용 첫 화면 (리스크 풀이 · 메뉴 안내 · 찾은 것)
    "실시간 모니터링": realtime_view.page,
    "리스크 분석": risk_view.page,
    "무기 거래 추이": lambda: arms_view.page(filter_box=sidebar.sidebar_filters("무기 거래 추이"), compact=True),
    "리스크와 무기 거래": risk_arms_view.page,
    "데이터 소개": data_intro_view.page,
}
ui.brand()                             #    모든 페이지 맨 위: 대시보드 제목 · 부제
PAGES[page]()

sidebar.sidebar_footer()               #    사이드바 맨 아래 실시간 수집 시각 (필터까지 그린 뒤)
setup.theme_sync(LIGHT)                # 5. 테마 동기화 (맨 끝)
