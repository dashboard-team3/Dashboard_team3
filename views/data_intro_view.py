"""⑤ 데이터 소개 페이지 (원본 app2.py 의 8.). page() = 자료출처 · 수집 대상 · 가공 방법 · 해석 안내."""
import streamlit as st

from core.ui import page_sub, term
from core.ui import RISK_FORMULA, SURGE_FORMULA, PEARSON_FORMULA


ME16 = ["사우디아라비아", "아랍에미리트", "카타르", "쿠웨이트", "바레인", "오만", "예멘", "시리아",
        "레바논", "요르단", "이스라엘", "팔레스타인", "이라크", "이란", "이집트", "튀르키예"]

SOURCES = [   # (기관, 이름, 자료 설명, 주소)
    ("The GDELT Project", "GDELT Event Database 1.0 / 2.0",
     "전 세계 뉴스에서 국가·기관·인물 등 행위자와 사건 정보를 자동 추출한 국제 뉴스 사건 데이터 · "
     "1.0: 1979년부터 일별 제공 · 2.0: 2015년부터 15분 단위 갱신", "https://www.gdeltproject.org"),
    ("유엔 통계국(UNSD)", "UN Comtrade",
     "유엔의 국가 간 상품 무역 통계 데이터베이스", "https://comtradeplus.un.org"),
    ("스톡홀름 국제평화연구소", "SIPRI Arms Transfers Database",
     "국가 간 주요 재래식 무기 이전 데이터베이스", "https://armstransfers.sipri.org"),
]

GUIDE = [     # (제목, 설명)
    ("뉴스 기반 지표", "보도된 사건을 기준으로 산출 · 국가·시기별 보도량 차이에 따른 지표 변동 가능 · "
                "비율 지표를 통한 보도량 영향 완화에도 편향 잔존 가능"),
    ("TIV와 거래 금액의 구분", "SIPRI의 주요 재래식 무기 이전 규모 비교 지표 · 실제 거래 금액과는 구별 · 본 대시보드: 주문 연도 기준 집계"),
    ("UN Comtrade 신고 누락", "국가·월별 미신고 자료는 관측 없음으로 처리 · 실제 거래액 0과는 구별"),
    ("상관관계의 해석 범위", "리스크·무기 거래의 동반 변화만으로 인과관계 또는 통계적 유의성 판단 불가"),
]


def page():
    st.title("데이터 소개")
    page_sub("대시보드 활용 자료(" + term("GDELT") + " · " + term("SIPRI") + " · " + term("UN Comtrade") + ")의 출처·수집 범위·산출 방법 안내")
    """데이터 소개 페이지: 한 페이지로 스크롤. 자료출처 → 수집 대상 → 가공 방법 → 해석에 대한 안내."""
    # ── 자료출처 (맨 위, 2026-10-02 팀 요청으로 순서를 뒤집음) ──
    st.markdown('<div class="di-h">자료 출처</div>', unsafe_allow_html=True)
    cards = "".join(
        f'<div class="di-card"><div class="di-org">{org}</div><div class="di-name">{name}</div>'
        f'<div class="di-desc">자료 설명 · {desc}</div><a class="di-url" href="{url}" target="_blank">{url}</a></div>'
        for org, name, desc, url in SOURCES)
    st.markdown(f'<div class="di-cards">{cards}</div>', unsafe_allow_html=True)

    # ── 수집 대상 ──
    st.markdown('<div class="di-h">수집 대상</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="di-sec"><div class="di-block"><p><b>중동 16개국</b> (SIPRI Middle East 분류 기준)</p>'
        f'<p>{" · ".join(ME16)}</p>'
        '<p class="di-sub2">기간</p><ul class="di-list">'
        '<li>리스크 · 무기 계약: <b>1980년 ~ 현재</b> (이란–이라크 전쟁 발발 연도부터)</li>'
        '<li>Comtrade 교역액: 2002년 ~ 현재 (표시는 2010년부터)</li>'
        '<li>실시간 모니터링: 당일(UTC 기준)</li></ul></div></div>', unsafe_allow_html=True)

    # ── 가공 방법 (리스크 → 급증 판정 → 시차 상관, 한 칸 안에) ──
    st.markdown('<div class="di-h">지표 산출 방법</div>', unsafe_allow_html=True)
    with st.container(key="info_accordion"):    
        # 국가쌍 리스크
        with st.expander("국가쌍 리스크", expanded=False):
            st.markdown(
                f'<div class="di-formula">{RISK_FORMULA}</div>'
                '<ul class="di-list">'
                '<li>A→B와 B→A를 구분하여 산출 · 기사에 기록된 행위 주체·대상 기준</li>'
                '<li>일별 리스크 산출 후 달력 일수 기준 월평균 계산 · 사건 미발생일은 0으로 반영</li>'
                '<li>GDELT 원자료 미확보 기간(2025.06.14–07.01 등)의 회색 표시</li>'
                '<li>출처: Aizenman, Desbordes &amp; Saadaoui (2026), '
                '<i>Bilateral Conflict Risk and Trade</i>, NBER WP 35077</li>'
                '</ul>',
                unsafe_allow_html=True,
            )

        # 급증 판정
        with st.expander("급증 판정", expanded=False):
            st.markdown(
                f'<div class="di-formula">{SURGE_FORMULA}</div>'
                '<ul class="di-list">'
                '<li>리스크의 절대 수준이 아닌 <b>해당 관계의 평소 대비 상승</b>으로 정의 · 세 조건 동시 충족</li>'
                '<li>비교 구간은 판정 대상 월을 제외한 <b>직전 12개월</b> · '
                '12개월 미충족 시 6개월 이상이면 산출, 6개월 미만은 판정 제외</li>'
                '<li>σ 하한 0.05 적용 · 보도가 희박한 관계의 표준편차가 0에 근접하여 '
                '미세 변동이 급증으로 판정되는 문제 방지</li>'
                '<li>판정 결과: 1980년 9월 ~ 2026년 7월 · 16개국 <b>403건</b> · '
                '원자료 미확보 월(2025.06)은 판정 제외</li>'
                '<li>기준 연도(0년): 해당 연도 급증 월의 <b>상승폭 합</b> 상위 25% · '
                '급증 월 수 기준은 미채택(국가별 선정 비율 편차 과대)</li>'
                '</ul>',
                unsafe_allow_html=True,
            )

        # 시차 상관
        with st.expander("시차 상관 (피어슨)", expanded=False):
            st.markdown(
                f'<div class="di-formula">{PEARSON_FORMULA}</div>'
                '<ul class="di-list">'
                '<li>연 리스크와 <b>0~3년 뒤</b> 무기 주문의 동반 변화 정도를 −1 ~ +1로 측정</li>'
                '<li>주문 TIV는 <b>log(1 + TIV)</b> 변환 · '
                '대형 계약 1건에 의한 결과 왜곡 완화 · 주문 미발생 연도는 0</li>'
                '<li>국가별 규모 차이를 제거하기 위해 <b>국가 내 표준화</b>'
                '(평균 0 · 표준편차 1) 후 16개국 통합</li>'
                '<li>통합 결과는 네 시차 모두 0 근방(±0.02 이내) · '
                '국가별 상관의 <b>부호가 반대</b>여서 상쇄</li>'
                '<li>동반 변화의 측정값이며 '
                '<b>인과관계 또는 통계적 유의성을 나타내지 않음</b></li>'
                '</ul>',
                unsafe_allow_html=True,
            )

    # ── 해석에 대한 안내 (맨 아래) ──
    st.markdown('<div class="di-h">해석 시 유의사항</div>', unsafe_allow_html=True)
    items = "".join(f'<li><b>{t}</b><br>{d}</li>' for t, d in GUIDE)
    st.markdown(f'<div class="di-sec"><ul class="di-guide">{items}</ul></div>', unsafe_allow_html=True)
