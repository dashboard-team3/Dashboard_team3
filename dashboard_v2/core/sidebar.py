import streamlit as st
from urllib.parse import quote

from sources import realtime


# v2: 사이드바 = 제목(맨 위) · 메뉴 · 그 페이지의 필터(세로). 본문은 핵심 요약과 그래프부터 (F 패턴).


def page_filters(label):
    """그 페이지 필터를 «본문 맨 위» 접이식 상자에 그린다 (기본은 접힘). (2026-09-30 사이드바 → 본문)
    조건을 바꾸는 곳이 보는 화면과 같은 자리에 있어야 눈이 덜 옮겨 다닌다.
    돌려준 상자에 위젯을 그리면 된다. 접혀 있어도 지금 조건이 보이게 filter_note() 로 한 줄 적는다."""
    return st.expander(f"필터 · {label}", expanded=False)


def filter_note(text):
    """접힌 필터 아래 '현재 조건' 한 줄."""
    st.markdown(f'<div class="filter-note">현재 · {text}</div>', unsafe_allow_html=True)


sidebar_filters = page_filters      # 예전 이름으로 부르던 곳을 위해 남겨 둔다


def menu():
    """사이드바 맨 위 제목 · 부제 · 메뉴. 고른 메뉴 이름을 돌려준다."""
    with st.sidebar:
        st.title("Conflict Risk & Arms Dashboard")
        st.caption("중동 지역 갈등 리스크와 무기 거래")   # 아래 구분선은 style2.css (.sb-foot 근처)

        # 홈 = 주소에 ?page= 가 없으면 여기로)
        MENU = ['홈', '리스크 모니터링', '무기 거래 추이', '리스크와 무기 거래', '종합 분석', '데이터 소개']   # '메뉴' 글자는 숨김 (collapsed)
        # 예전 메뉴 이름으로 된 주소·저장 상태도 새 이름으로 연다 (결론 · 분석 결과는 데이터 소개로)
        OLD = {'실시간 모니터링': '리스크 모니터링', '리스크 추이': '리스크 모니터링', '리스크 분석': '리스크 모니터링',   # (2026-10-01) 두 메뉴를 한 페이지로
               '개요': '리스크 모니터링', '분석 결과': '데이터 소개', '결론': '데이터 소개',
               '국가 카드': '리스크와 무기 거래'}   # 잠깐 썼던 이름 (2026-10-01)

        MENU_ICONS = {
            "홈": """
                <path d="M8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4.5a.5.5 0 0 0 .5-.5v-4h2v4a.5.5 0 0 0 .5.5H14a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM2.5 14V7.707l5.5-5.5 5.5 5.5V14H10v-4a.5.5 0 0 0-.5-.5h-3a.5.5 0 0 0-.5.5v4z"/>
            """,
            "리스크 모니터링": """
                <path d="M3.05 3.05a7 7 0 0 0 0 9.9.5.5 0 0 1-.707.707 8 8 0 0 1 0-11.314.5.5 0 0 1 .707.707m2.122 2.122a4 4 0 0 0 0 5.656.5.5 0 1 1-.708.708 5 5 0 0 1 0-7.072.5.5 0 0 1 .708.708m5.656-.708a.5.5 0 0 1 .708 0 5 5 0 0 1 0 7.072.5.5 0 1 1-.708-.708 4 4 0 0 0 0-5.656.5.5 0 0 1 0-.708m2.122-2.12a.5.5 0 0 1 .707 0 8 8 0 0 1 0 11.313.5.5 0 0 1-.707-.707 7 7 0 0 0 0-9.9.5.5 0 0 1 0-.707zM10 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0"/>
            """,
            "무기 거래 추이": """
                <path d="M11 2a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v12h.5a.5.5 0 0 1 0 1H.5a.5.5 0 0 1 0-1H1v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3h1V7a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v7h1zm1 12h2V2h-2zm-3 0V7H7v7zm-5 0v-3H2v3z"/>
            """,
            "리스크와 무기 거래": """
                <path fill-rule="evenodd" d="M0 0h1v15h15v1H0zm14.817 3.113a.5.5 0 0 1 .07.704l-4.5 5.5a.5.5 0 0 1-.74.037L7.06 6.767l-3.656 5.027a.5.5 0 0 1-.808-.588l4-5.5a.5.5 0 0 1 .758-.06l2.609 2.61 4.15-5.073a.5.5 0 0 1 .704-.07"/>
            """,
            "종합 분석": """
                <path d="M4 11a1 1 0 1 1 2 0v1a1 1 0 1 1-2 0zm6-4a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0zM7 9a1 1 0 0 1 2 0v3a1 1 0 0 1-2 0z"/>
                <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z"/>
                <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z"/>
            """,
            "데이터 소개": """
                <path d="M4.318 2.687C5.234 2.271 6.536 2 8 2s2.766.27 3.682.687C12.644 3.125 13 3.627 13 4c0 .374-.356.875-1.318 1.313C10.766 5.729 9.464 6 8 6s-2.766-.27-3.682-.687C3.356 4.875 3 4.373 3 4c0-.374.356-.875 1.318-1.313M13 5.698V7c0 .374-.356.875-1.318 1.313C10.766 8.729 9.464 9 8 9s-2.766-.27-3.682-.687C3.356 7.875 3 7.373 3 7V5.698c.271.202.58.378.904.525C4.978 6.711 6.427 7 8 7s3.022-.289 4.096-.777A5 5 0 0 0 13 5.698M14 4c0-1.007-.875-1.755-1.904-2.223C11.022 1.289 9.573 1 8 1s-3.022.289-4.096.777C2.875 2.245 2 2.993 2 4v9c0 1.007.875 1.755 1.904 2.223C4.978 15.71 6.427 16 8 16s3.022-.289 4.096-.777C13.125 14.755 14 14.007 14 13zm-1 4.698V10c0 .374-.356.875-1.318 1.313C10.766 11.729 9.464 12 8 12s-2.766-.27-3.682-.687C3.356 10.875 3 10.373 3 10V8.698c.271.202.58.378.904.525C4.978 9.71 6.427 10 8 10s3.022-.289 4.096-.777A5 5 0 0 0 13 8.698m0 3V13c0 .374-.356.875-1.318 1.313C10.766 14.729 9.464 15 8 15s-2.766-.27-3.682-.687C3.356 13.875 3 13.373 3 13v-1.302c.271.202.58.378.904.525C4.978 12.71 6.427 13 8 13s3.022-.289 4.096-.777c.324-.147.633-.323.904-.525"/>
            """,
        }

        icon_rules = []

        for name, paths in MENU_ICONS.items():
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 16 16" fill="black">{paths}</svg>'
            )
            icon_url = f"data:image/svg+xml,{quote(svg, safe='')}"
            index = MENU.index(name)

            icon_rules.append(f"""
                [data-testid="stSidebar"] .st-key-menu_page
                label[data-testid="stRadioOption"]:has(input[value="{index}"])
                [data-testid="stMarkdownContainer"] p::before {{
                    content: "";
                    -webkit-mask-image: url("{icon_url}");
                    mask-image: url("{icon_url}");
                }}
            """)

        st.markdown(
            "<style>" + "\n".join(icon_rules) + "</style>",
            unsafe_allow_html=True,
        )
        
        # 주소 뒤에 ?page=리스크 분석 처럼 붙이면 그 메뉴로 바로 열린다 (발표 자료 캡처·링크 공유용)
        start = st.query_params.get("page", MENU[0])
        if start in ("실시간 모니터링", "리스크 추이") and "mon_view" not in st.session_state:
            st.session_state["mon_view"] = start      # 예전 주소(?page=리스크 추이)는 리스크 모니터링의 그 버튼으로
        start = OLD.get(start, start)
        keep = st.session_state.get("page_keep", start)
        keep = OLD.get(keep, keep)
        if st.session_state.get("menu_page") not in (None, *MENU):
            st.session_state["menu_page"] = OLD.get(st.session_state["menu_page"], MENU[0])
        page = st.radio('메뉴', MENU, index=MENU.index(keep) if keep in MENU else 0, key="menu_page", label_visibility="collapsed",
                        format_func=lambda p: f"{p}")   # 보이는 이름에만 번호 (값 · 주소는 그대로)
        st.session_state["page_keep"] = page
        # 주소의 ?page= 도 지금 페이지로 맞춘다 (안 그러면 메뉴로 옮긴 뒤 새로고침·링크 공유 때 처음 페이지가 열린다)
        if st.query_params.get("page") != page:
            st.query_params["page"] = page
    return page


def sidebar_footer():
    """사이드바 맨 아래(화면 아래 끝, style2.css 가 붙임): 실시간 마지막 수집 시각 한 줄.
    자료 출처 · 대상은 데이터 소개 페이지에 있으므로 여기서는 뺐다 (2026-09-29)."""
    k = realtime.kpis()
    when = f"{k['slot_kst']} KST" if k.get("slot_kst") else "수집 상태 미확인"
    st.sidebar.markdown(
        f'<div class="sb-foot"><b>실시간 수집</b> · 최종 수집 {when}</div>',
        unsafe_allow_html=True)
