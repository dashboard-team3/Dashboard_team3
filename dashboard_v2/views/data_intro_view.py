"""⑤ 데이터 소개 페이지 (원본 app2.py 의 8.). page() = 해석 안내 · 가공 방법 · 수집 대상 · 자료출처."""
import streamlit as st

from core.ui import page_sub, term
from core.ui import RISK_FORMULA


ME16 = ["사우디아라비아", "아랍에미리트", "카타르", "쿠웨이트", "바레인", "오만", "예멘", "시리아",
        "레바논", "요르단", "이스라엘", "팔레스타인", "이라크", "이란", "이집트", "튀르키예"]

SOURCES = [   # (기관, 이름, 자료 설명, 주소)
    ("The GDELT Project", "GDELT Event Database 1.0 / 2.0",
     "전 세계 뉴스에서 국가·기관·인물 등의 행위자와 사건 정보를 자동으로 추출해 구조화한 국제 뉴스 이벤트 데이터. "
     "1.0은 1979년부터 일별, 2.0은 2015년부터 15분 단위로 데이터 제공.", "https://www.gdeltproject.org"),
    ("유엔 통계국(UNSD)", "UN Comtrade",
     "UN이 제공하는 국가 간 상품 무역 통계 데이터베이스.", "https://comtradeplus.un.org"),
    ("스톡홀름 국제평화연구소", "SIPRI Arms Transfers Database",
     "국가 간 주요 재래식 무기 이전 정보를 제공하는 데이터베이스.", "https://armstransfers.sipri.org"),
]

GUIDE = [     # (제목, 설명)
    ("뉴스 기반", "GDELT는 보도된 사건만 담습니다. 보도량이 적은 나라·시기는 리스크가 실제보다 낮거나 들쭉날쭉할 수 있습니다. "
                "비율 지표라 뉴스량 증가의 영향은 줄였지만 없애지는 못합니다."),
    ("TIV ≠ 금액", "SIPRI의 TIV는 무기거래 추세를 나타내기 위해 무기의 생산 비용을 기반으로 산출한 보조지표로 금액을 의미하지 않습니다."),
    ("Comtrade 신고 누락", "나라·달마다 신고 데이터가 누락된 달은 '관측 없음'으로 두고, 실제 거래액이 0을 의미하지 않습니다."),
    ("인과 아님", "리스크와 무기 거래가 함께 움직여도 인과관계나 통계적 유의성을 뜻하지 않습니다."),
]


def page():
    st.title("데이터 소개")
    page_sub("대시보드의 숫자가 어디서 와서(" + term("GDELT") + " · " + term("SIPRI") + " · " + term("UN Comtrade") + ") 어떻게 계산되었는지 정리했습니다.")
    """데이터 소개 페이지: 한 페이지로 스크롤. 해석에 대한 안내 → 가공 방법 → 수집 대상 → 자료출처."""
    # ── 해석에 대한 안내 (맨 위, 2026-10-02 팀 요청으로 가공 방법 위로) ──
    st.markdown('<div class="di-h">해석에 대한 안내</div>', unsafe_allow_html=True)
    items = "".join(f'<li><b>{t}</b><br>{d}</li>' for t, d in GUIDE)
    st.markdown(f'<ul class="di-guide">{items}</ul>', unsafe_allow_html=True)

    # ── 가공 방법 ──
    st.markdown('<div class="di-h">가공 방법</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="di-sub">국가쌍 리스크</div>'
        f'<div class="di-formula">{RISK_FORMULA}</div>'
        '<ul class="di-list">'
        '<li>A→B와 B→A를 따로 계산 (Actor 순서 기준, 실제 공격 방향 아님)</li>'
        '<li>하루 단위로 계산한 뒤 달력 일수로 월평균 (사건 없는 날 = 0)</li>'
        '<li>GDELT 서버에 원본이 없는 날(2025.06.14–07.01 등)은 표시에서 회색 처리</li>'
        '<li>출처: Aizenman, Desbordes &amp; Saadaoui (2026), <i>Bilateral Conflict Risk and Trade</i>, NBER WP 35077</li>'
        '</ul>', unsafe_allow_html=True)

    # ── 수집 대상 ──
    st.markdown('<div class="di-h">수집 대상</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="di-block"><p><b>중동 16개국</b> (SIPRI Middle East 분류 기준)</p>'
        f'<p>{" · ".join(ME16)}</p>'
        '<p class="di-sub2">기간</p><ul class="di-list">'
        '<li>리스크 · 무기 계약: <b>1980년 ~ 현재</b> (이란–이라크 전쟁 발발 연도부터)</li>'
        '<li>Comtrade 교역액: 2002년 ~ 현재 (표시는 2010년부터)</li>'
        '<li>실시간 모니터링: 오늘(UTC)</li></ul></div>', unsafe_allow_html=True)

    # ── 자료출처 ──
    st.markdown('<div class="di-h">자료출처</div>', unsafe_allow_html=True)
    cards = "".join(
        f'<div class="di-card"><div class="di-org">{org}</div><div class="di-name">{name}</div>'
        f'<div class="di-desc">자료 설명 · {desc}</div><a class="di-url" href="{url}" target="_blank">{url}</a></div>'
        for org, name, desc, url in SOURCES)
    st.markdown(f'<div class="di-cards">{cards}</div>', unsafe_allow_html=True)
