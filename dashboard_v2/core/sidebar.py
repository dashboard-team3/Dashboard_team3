"""사이드바: 제목 · 메뉴 · 그 페이지 필터 상자 · 맨 아래 실시간 수집 시각 (원본 app2.py 의 3. 사이드바 메뉴)."""
import streamlit as st

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
        st.caption("중동 지역 갈등 편중도와 무기 거래")   # 아래 구분선은 style2.css (.sb-foot 근처)

        # 홈 = 주소에 ?page= 가 없으면 여기로)
        MENU = ['홈', '실시간 모니터링', '리스크 분석', '무기 거래 추이', '리스크와 무기 거래', '데이터 소개']   # '메뉴' 글자는 숨김 (collapsed)
        # 예전 메뉴 이름으로 된 주소·저장 상태도 새 이름으로 연다 (결론 · 분석 결과는 데이터 소개로)
        OLD = {'개요': '실시간 모니터링', '분석 결과': '데이터 소개', '결론': '데이터 소개'}
        # 주소 뒤에 ?page=리스크 분석 처럼 붙이면 그 메뉴로 바로 열린다 (발표 자료 캡처·링크 공유용)
        start = st.query_params.get("page", MENU[0])
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
    when = f"{k['slot_kst']} KST" if k.get("slot_kst") else "수집기 꺼짐"
    st.sidebar.markdown(
        f'<div class="sb-foot"><b>실시간 수집</b> · 마지막 {when}</div>',
        unsafe_allow_html=True)
