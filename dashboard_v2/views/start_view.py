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
    ("실시간 모니터링", "①", "지금 중동에서 누가 누구와 부딪히고 있나?",
     "15분마다 들어오는 뉴스 사건 가운데 16개국끼리의 갈등만 모아 지도 · 네트워크 · 사건 목록으로"),
    ("리스크 분석", "②", "1980년부터 어느 나라 사이가 얼마나 험악했나?",
     "두 나라 사이(국가쌍) 또는 한 나라(국가별)의 월별 리스크 흐름과 지금 등급"),
    ("무기 거래 추이", "③", "누가 누구에게 무기를 얼마나 팔았나?",
     "SIPRI 무기 계약 · UN Comtrade 군용 품목 교역으로 본 공급국 → 중동 흐름"),
    ("리스크와 무기 거래", "④", "갈등이 커지면 무기를 더 사나?",
     "한 나라씩 연도별로 견주거나, 중동 전체에서 갈등이 급증한 뒤의 무기 주문 변화를 사례로"),
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
        '<div class="st-hero"><div class="h-q">중동 16개국 사이의 갈등이 커질 때, 무기 거래는 어떻게 움직일까?</div>'
        '<div class="h-s">뉴스로 나라 사이 갈등의 온도를 재고(GDELT), 무기 계약 · 교역 기록(SIPRI · UN Comtrade)과 '
        '나란히 놓아 보는 대시보드입니다. 처음이라면 아래 순서대로 읽어 보세요.</div></div>', unsafe_allow_html=True)

    # ── ② 리스크란?
    pair, quiet = _examples()
    st.markdown('<div class="st-h">리스크란?</div>', unsafe_allow_html=True)
    seg = "".join(f'<span style="background:{c}"></span>' for c in relations.GRADE_COLORS)
    marks = (f'<div class="rk-mark" style="left:{quiet * 100:.1f}%"><b>{quiet:.2f}</b><em>오만 (국가별 평균)</em></div>'
             f'<div class="rk-mark up" style="left:{pair * 100:.1f}%"><b>{pair:.2f}</b><em>이스라엘 → 팔레스타인</em></div>')
    st.markdown(
        '<div class="rk-card">'
        '<div class="rk-def">리스크 = 두 나라 사이에 오간 <b>뉴스 속 사건</b> 가운데 <b>갈등</b>이 차지하는 비중 (0 ~ 1)</div>'
        '<div class="rk-sub">갈등 = 공격 · 위협 · 비난 · 제재 &nbsp;/&nbsp; 협력 = 회담 · 지원 · 협정. '
        '사건이 셀수록, 기사에 많이 나올수록 더 무겁게 셉니다.</div>'
        f'<div class="rk-scale"><div class="rk-bar">{seg}</div>{marks}'
        '<div class="rk-ends"><span>0 · 협력 보도만</span><span>0.5 · 반반</span><span>1 · 갈등 보도만</span></div></div>'
        '<div class="rk-grades">' + "".join(
            f'<span><i style="background:{c}"></i>{g} <em>{d}</em></span>'
            for g, c, d in zip(relations.GRADES, relations.GRADE_COLORS, ["0 ~ 0.2", "0.2 ~ 0.4", "0.4 ~ 0.6", "0.6 ~ 0.8", "0.8 ~ 1"])) +
        '</div>'
        f'<div class="rk-ex">예: 이스라엘 → 팔레스타인의 1980년 이후 평균은 <b>{pair:.2f}</b> — 두 나라 사이 보도된 사건 무게의 '
        f'약 {pair * 100:.0f}%가 갈등이었다는 뜻입니다. 반대로 오만은 평균 <b>{quiet:.2f}</b>로 대부분 협력 쪽 보도였습니다.</div>'
        '<div class="rk-warn">※ 실제 전투의 세기가 아니라 <b>보도의 비중</b>입니다. 보도가 적은 나라 · 시기는 값이 들쭉날쭉할 수 있습니다.</div>'
        '</div>', unsafe_allow_html=True)

    # ── ③ 메뉴마다 알 수 있는 것
    st.markdown('<div class="st-h">무엇을 볼 수 있나</div>', unsafe_allow_html=True)
    cols = st.columns(len(MENU_CARDS), gap="small")
    for col, (name, no, q, d) in zip(cols, MENU_CARDS):
        with col:
            st.markdown(f'<div class="mn-card"><div class="mn-no">{no} {name}</div><div class="mn-q">{q}</div>'
                        f'<div class="mn-d">{d}</div></div>', unsafe_allow_html=True)
            st.button("바로 가기 ›", key=f"go_{name}", on_click=_go, args=(name,), width="stretch")

    # ── ④ 찾은 것 · 주의
    st.markdown('<div class="st-h">지금까지 찾은 것</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="st-find">전체로 보면 갈등과 무기 수입은 <b>따로 움직였습니다</b> (연 단위 상관 ≈ 0). '
        '그러나 갈등이 <b>급증한</b> 나라만 보면, 무기 주문이 늘어난 18건 중 14건이 <b>2년 안에</b> 정점에 이르렀습니다. '
        '갈등이 바꾸는 것은 “얼마나” 사느냐보다 <b>“언제”</b> 사느냐에 가깝습니다. → ④ 리스크와 무기 거래 · 중동 무기 거래 분석</div>',
        unsafe_allow_html=True)
    st.markdown(
        '<div class="st-h">읽을 때 주의</div><ul class="st-warn">'
        '<li><b>뉴스 기반</b> — 보도된 사건만 담깁니다. 보도가 적으면 리스크가 낮게 · 들쭉날쭉하게 나올 수 있습니다.</li>'
        '<li><b>TIV ≠ 달러</b> — SIPRI 의 무기 가치 지표입니다. 금액이 아니고, 연도는 주문 연도입니다.</li>'
        '<li><b>인과 아님</b> — 함께 움직여도 한쪽이 다른 쪽의 원인이라는 뜻은 아닙니다.</li></ul>',
        unsafe_allow_html=True)
