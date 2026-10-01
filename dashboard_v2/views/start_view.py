"""시작하기 (v2, 2026-09-30): 대시보드를 처음 보는 사람이 1분 안에 '아 그렇구나' 하게.

page()  ① 이 대시보드가 답하려는 질문 한 줄
        ② 리스크가 무엇인지 쉬운 말 + 0~1 눈금 위에 실제 예시 두 개 (자료에서 바로 계산)
        ③ 메뉴마다 '여기서 알 수 있는 것' 카드 + 바로 가기 버튼
        ④ 지금까지 찾은 것 한 줄 · 읽을 때 주의 세 가지
"""
import streamlit as st

from sources import relations

# 메뉴 카드: (메뉴 이름, 번호, 이 페이지가 답하는 질문, 한 줄 설명)
MENU_CARDS = [
    ("실시간 모니터링", "지금 중동에서 누가 누구와 부딪히고 있나?",
     "GDELT 2.0 데이터를 기반으로 중동 16개국 사이에서 일어난 갈등 사건을 15분마다 업데이트하여 보여 줍니다."),
    ("리스크 분석", "1980년부터 어느 나라 사이가 얼마나 험악했나?",
     "1980년부터 국가쌍 · 국가별 월별 리스크를 보여 줍니다."),
    ("무기 거래 추이", "누가 누구에게 무기를 얼마나 팔았나?",
     "무기 계약(SIPRI) · 교역 기록(UN Comtrade)을 바탕으로 중동 16개국의 무기 거래 흐름을 보여 줍니다."),
    ("리스크와 무기 거래", "갈등이 커지면 무기를 더 사나?",
     "리스크와 무기 거래의 연도별로 비교하여 두 지표를 비교할 수 있습니다."),
    ("중동 무기 거래 분석", "갈등이 급증한 뒤 무기 주문은 어떻게 바뀌었나?",
     "나라를 고르지 않고 중동 16개국 전체에서 리스크가 급증한 해 앞뒤로 무기 주문 변화를 사례로 봅니다."),
]


def _go(name):
    """바로 가기 버튼: 사이드바 메뉴를 그 페이지로 바꾼다 (다음 실행 때 반영)."""
    st.session_state["menu_page"] = name
    st.session_state["page_keep"] = name


@st.cache_data(ttl=3600)
def _examples():
    """눈금 위 예시 두 개 (1980년 이후 평균): 갈등이 많은 쌍 · 조용한 나라."""
    pair = relations.pair_series(relations.load_risk(), "ISR", "out")["PSE"].mean()
    quiet = relations.load_country().pivot(index="date", columns="country", values="all_risk")["OMN"].mean()
    return float(pair), float(quiet)


def page():
    st.title("시작하기")
    st.markdown(
        '<div class="page-sub">중동에서 발생한 뉴스(GDELT)를 기반으로 갈등을 파악하고, 무기 계약(SIPRI) · 교역 기록(UN Comtrade)에 대한 정보를 제공합니다.</div>', unsafe_allow_html=True)

    # ── ③ 메뉴마다 알 수 있는 것
    st.markdown('<div class="st-h">구성 페이지</div>', unsafe_allow_html=True)
    cols = st.columns(len(MENU_CARDS), gap="small")
    for col, (name, q, d) in zip(cols, MENU_CARDS):
        with col:
            st.markdown(f'<div class="mn-card"><div class="mn-no"> {name}</div><div class="mn-q">{q}</div>'
                        f'<div class="mn-d">{d}</div></div>', unsafe_allow_html=True)
            st.button("바로 가기 ›", key=f"go_{name}", on_click=_go, args=(name,), width="stretch")
