from core import setup, sidebar, ui

LIGHT = setup.setup()                  # 1. 페이지 설정 · CSS · 밝은 테마 (맨 먼저)
page = sidebar.menu()                  # 2. 사이드바 제목 · 메뉴

from views import start_view, monitor_view, country_view, arms_view, risk_arms_view, data_intro_view   # noqa: E402

PAGES = {                              # 3. 메뉴 이름 → 그 페이지를 그리는 함수
    "홈": start_view.page,              # 시작 화면: 중동 지도 배경 · 큰 제목 · 메뉴 카드 (왼쪽 메뉴는 접어 둠)
    "리스크 모니터링": monitor_view.page,   #    실시간 모니터링 · 리스크 추이(지도)를 버튼으로 (views/monitor_view.py, 2026-10-01)
    "무기 거래 추이": lambda: arms_view.page(compact=True),   # 필터 상자는 제목 아래에서 직접 만듬
    "리스크와 무기 거래": country_view.page,   #    나라 하나를 한 장으로 (views/country_view.py, 2026-10-01)
    "종합 분석": risk_arms_view.region_page,   #    중동 16개국 전체 (급증 전후, views/surge_view.py)
    "데이터 소개": data_intro_view.page,
}
if page != "홈":                        #    홈은 첫 화면이 제목을 크게 보여 주므로 위 제목 줄은 뺌
    ui.brand()                         #    모든 페이지 맨 위: 대시보드 제목 · 부제
    start_view.reopen_sidebar()        #    홈 카드로 들어왔으면 접어 둔 왼쪽 메뉴를 다시 폄
    ui.page_backdrop()                 #    (2026-10-02) 홈 배경 지도를 어둡게 · 흐리게 깔기 (어두운 테마만)
PAGES[page]()

sidebar.sidebar_footer()               #    사이드바 맨 아래 실시간 수집 시각 (필터까지 그린 뒤)
setup.theme_sync(LIGHT)                # 5. 테마 동기화 (맨 끝)
