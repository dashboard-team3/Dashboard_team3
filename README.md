# Conflict Risk & Arms Dashboard

> 중동 지역 갈등 편중도와 무기 거래

중동 16개국을 대상으로 **국가 간 갈등·분쟁 변화와 무기 거래 흐름을 함께 탐색**하고, **GDELT 2.0 기반 최신 갈등 현황을 모니터링**할 수 있도록 구축한 Streamlit 대시보드.

과거·최근의 갈등 데이터와 SIPRI·UN Comtrade 무기 거래 데이터를 연계하여 국가별·국가쌍별 변화와 관계를 시각적으로 비교할 수 있도록 구성함.

---

## 주요 기능

### 1. 리스크 모니터링
- GDELT 2.0 기반 최신 중동 갈등 이벤트 모니터링
- 중동 16개국 지도 기반 최근 갈등 현황 시각화
- 국가별·국가쌍별 갈등 리스크 추이 확인
- 최근 리스크 상위 국가 및 주요 국가쌍 탐색

### 2. 무기 거래 추이
- SIPRI 주요 재래식 무기 이전 추이 분석
- UN Comtrade 무기·군용 관련 품목 교역 추이 분석
- 국가별·국가 간 거래 흐름 및 품목 구성 시각화

### 3. 리스크와 무기 거래
- 국가별 갈등 리스크와 무기 거래 변화 비교
- 기간별 추이 및 상관관계 탐색
- 갈등 변화와 무기 거래 흐름을 동일 화면에서 비교

### 4. 종합 분석
- 중동 전체 및 국가별 분석 결과 종합
- 갈등 리스크와 무기 거래의 관계 비교
- 주요 증가·감소 사례 및 분석 결과 제공

### 5. 데이터 소개
- 데이터 출처 및 수집 대상 안내
- 데이터 전처리·가공 방법 설명
- 리스크 계산 기준 및 데이터 해석 시 유의사항 제공

---

## 분석 대상

SIPRI의 Middle East 지역 분류를 기준으로 다음 **16개국**을 분석 대상으로 선정함.

`SAU` 사우디아라비아 · `UAE` 아랍에미리트 · `QAT` 카타르 · `KUW` 쿠웨이트  
`BHR` 바레인 · `OMA` 오만 · `YEM` 예멘 · `SYR` 시리아  
`LBN` 레바논 · `JOR` 요르단 · `ISR` 이스라엘 · `PSE` 팔레스타인  
`IRQ` 이라크 · `IRN` 이란 · `EGY` 이집트 · `TUR` 튀르키예

---

## 데이터

| 데이터 | 주요 용도 | 분석 범위 |
| --- | --- | --- |
| **GDELT 2.0 Events** | 최신 뉴스 기반 갈등 이벤트 모니터링 | 실시간/최신 |
| **GDELT 1.0 Events** | 국가·국가쌍별 갈등 이벤트 분석 | 2013.04~ |
| **COW MID** | 국가 간 군사분쟁 및 적대 수준 분석 | 1980~2014 |
| **SIPRI Arms Transfers** | 주요 재래식 무기 이전 분석 | 연간 자료 |
| **UN Comtrade** | 무기·군용 관련 선정 품목의 교역 분석 | 월별 자료 |

### GDELT 갈등 유형

공식 CAMEO Event Code를 바탕으로 프로젝트 분석 목적에 맞게 다음과 같이 분류함.

| 분석 유형 | Event Code |
| --- | --- |
| 위협 | 138, 1381~1385, 139 |
| 군사태세 | 152, 154 |
| 제재 | 163 |
| 무력 사용 | 190~196 |
| 대량살상무기 | 204, 2041, 2042 |

> 위 5개 유형은 GDELT의 공식 단계 구분이 아니라, CAMEO Event Code를 바탕으로 프로젝트에서 정의한 분석용 분류.

### UN Comtrade 분석 품목

무기·군용 관련 품목 분석을 위해 프로젝트에서 선정한 HS 코드를 사용함.

`9301`, `9306`, `930591`, `8710`, `8802`, `8807`, `880521`, `890610`, `880510`

> 일부 HS 코드는 민간 용도를 포함할 수 있으므로, 개별 거래를 모두 군수품 거래로 해석하지 않음.

---

## 기술 스택

- **Language**: Python
- **Dashboard**: Streamlit
- **Data Processing**: pandas, NumPy
- **Visualization**: Plotly
- **Database**: MySQL / AWS RDS
- **Data Format**: CSV, PyArrow
- **Version Control**: Git, GitHub

---

## 프로젝트 구조

```text
.
├── app.py                  # Streamlit 진입점
├── core/                   # 공통 설정, UI, 테마, 사이드바
├── views/                  # 페이지별 화면 구성
├── sources/                # 데이터 로드 및 분석 로직
├── db/                     # RDS 연결
├── data/                   # 분석용 데이터
├── styles/                 # Streamlit CSS
├── assets/                 # 정적 자원
├── requirements.txt
└── README.md
```

---

## 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/uuii006/Dashboard_team3.git
cd Dashboard_team3
```

### 2. 가상환경 생성 및 활성화

Conda를 사용하는 경우:

```bash
conda create -n dashboard python=3.12
conda activate dashboard
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 필요한 DB 접속 정보를 설정함.

```env
DB_HOST=
DB_PORT=
DB_USER=
DB_PASSWORD=
DB_NAME=
```

> `.env`는 Git 커밋에서 제외.

### 5. 대시보드 실행

```bash
streamlit run app.py
```

특정 포트로 실행하려면:

```bash
streamlit run app.py --server.port 8503
```

---

## 데이터 로딩

대시보드는 프로젝트의 `data/` 디렉터리에 저장된 분석용 파일을 우선 사용.

```text
data/
├── risk_monthly_1980_2026.csv
├── country_monthly_1980_2026.csv
├── region_monthly_1980_2026.csv
├── SIPRI_pre_1980_2025.csv
└── comtrade_mirror_detail.csv
```

실시간 모니터링 데이터는 로컬 데이터 또는 설정된 RDS에서 불러오도록 구성되어 있음.

---

## 분석 시 유의사항

- 본 대시보드는 **갈등과 무기 거래 간 인과관계를 증명하기 위한 서비스가 아니라 두 지표의 변화와 관계를 탐색하기 위한 분석 도구**.
- GDELT의 `Actor1`은 기사에 기록된 행위 주체를 의미하며, 먼저 공격한 국가를 의미하지 않음.
- SIPRI의 **TIV(Trend-Indicator Value)**는 실제 거래금액이 아니라 주요 재래식 무기 이전 규모를 비교하기 위한 지표.
- UN Comtrade는 국가별 신고 자료이므로 국가·시기별 신고 여부 및 통계 차이 존재 가능.
- 실시간 GDELT 데이터는 뉴스 보도량과 수집 시점의 영향을 받을 수 있음.

---

## 팀 구성

| 이름 | 주요 역할 |
| --- | --- |
| 김관우 | 데이터 수집 자동화 및 데이터 통합 구조 설계 |
| 김주리 | 무기 거래 데이터 수집 및 관련 자료 조사 |
| 임소망 | 데이터 시각화 기획 및 대시보드 화면 설계 |
| 황나영 | 국제 갈등 뉴스 데이터 수집 및 전처리 |

데이터 분석·시각화 및 대시보드 구현은 팀원 전체가 공동으로 수행.

---

## 데이터 출처

- [GDELT Project](https://www.gdeltproject.org/)
- [Correlates of War: Militarized Interstate Disputes](https://correlatesofwar.org/data-sets/mids/)
- [SIPRI Arms Transfers Database](https://armstransfers.sipri.org/)
- [UN Comtrade Database](https://comtradeplus.un.org/)

각 데이터의 저작권 및 이용 조건은 해당 제공 기관의 정책을 따릅니다.
