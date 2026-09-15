"""GDELT 1.0 중동 16개국 월 단위 분석.

사용법 (event 폴더에서):
    python run_month.py 2019 5

동작:
    1) data/2019.5_data/ 의 일별 원본 zip을 하루씩 읽어
    2) 중동 16개국 간(자국 내 제외) · 최근 7일 이내 사건 · 선택 EventCode 20개로 필터링하고
    3) 날짜별 결과 3개  → output/2019.5/20190501/ …
       월간 결과 4개    → output/2019.5/월간/
    에 저장합니다.

분석 기준은 노트북(GDELT_중동분석_최종.ipynb)의 1~8단계와 같습니다.
2013년 4월 이후(일별 파일이 있는 기간)만 지원합니다.
"""
import argparse
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

EVENT_DIR = Path(__file__).resolve().parent
GDELT_URL = "https://data.gdeltproject.org/events/"
MAX_LAG_DAYS = 7          # 파일 날짜 기준 며칠 전 사건까지 인정할지
FIRST_DAILY = date(2013, 4, 1)

HEADERS = [
    "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode", "Actor1EthnicCode",
    "Actor1Religion1Code", "Actor1Religion2Code", "Actor1Type1Code", "Actor1Type2Code", "Actor1Type3Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2KnownGroupCode", "Actor2EthnicCode",
    "Actor2Religion1Code", "Actor2Religion2Code", "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code",
    "IsRootEvent", "EventCode", "EventBaseCode", "EventRootCode", "QuadClass", "GoldsteinScale",
    "NumMentions", "NumSources", "NumArticles", "AvgTone",
    "Actor1Geo_Type", "Actor1Geo_FullName", "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code",
    "Actor1Geo_Lat", "Actor1Geo_Long", "Actor1Geo_FeatureID",
    "Actor2Geo_Type", "Actor2Geo_FullName", "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code",
    "Actor2Geo_Lat", "Actor2Geo_Long", "Actor2Geo_FeatureID",
    "ActionGeo_Type", "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_Lat", "ActionGeo_Long", "ActionGeo_FeatureID",
    "DATEADDED", "SOURCEURL",
]

MIDDLE_EAST = {
    "SAU": "사우디아라비아", "UAE": "아랍에미리트", "QAT": "카타르", "KUW": "쿠웨이트",
    "BHR": "바레인", "OMA": "오만", "YEM": "예멘", "SYR": "시리아",
    "LBN": "레바논", "JOR": "요르단", "ISR": "이스라엘", "PSE": "팔레스타인",
    "IRQ": "이라크", "IRN": "이란", "EGY": "이집트", "TUR": "튀르키예",
}

EVENT_CODES = {
    "138": "군사력 사용 위협", "1381": "봉쇄 위협", "1382": "점령 위협", "1383": "비정규 폭력 사용 위협",
    "1384": "재래식 군사 공격 위협", "1385": "대량살상무기 공격 위협", "139": "최후통첩",
    "152": "군 경계태세 강화", "154": "군 병력 동원·증강",
    "163": "금수·보이콧·제재 부과",
    "190": "재래식 군사력 사용", "191": "봉쇄·이동 제한", "192": "영토 점령",
    "193": "소형무기·경무기를 이용한 전투", "194": "포병·전차를 이용한 전투", "195": "공중무기 사용", "196": "휴전 위반",
    "204": "대량살상무기 사용", "2041": "화학·생물학·방사능 무기 사용", "2042": "핵무기 폭발",
}

NUMERIC_COLS = ["GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "AvgTone"]
SHOW_COLS = [
    "DATE", "GLOBALEVENTID", "SQLDATE", "Actor1Name", "Actor1CountryCode", "Actor2Name", "Actor2CountryCode",
    "EventCode", "EventCode_KR", "EventRootCode", "QuadClass",
    "GoldsteinScale", "NumMentions", "NumSources", "NumArticles", "AvgTone",
    "ActionGeo_FullName", "ActionGeo_CountryCode", "SOURCEURL",
]
PAIR_KEYS = ["Actor1CountryCode", "Actor1Country_KR", "Actor2CountryCode", "Actor2Country_KR"]


def month_label(year, month):
    return f"{year}.{month}"


def find_source(day, data_dir, use_server):
    for name in (f"{day}.export.CSV", f"{day}.export.CSV.zip"):
        if (data_dir / name).exists():
            return data_dir / name
    if use_server:
        return GDELT_URL + f"{day}.export.CSV.zip"
    return None


def filter_day(raw, day):
    min_date = (datetime.strptime(day, "%Y%m%d") - timedelta(days=MAX_LAG_DAYS)).strftime("%Y%m%d")
    mask = (
        raw["Actor1CountryCode"].isin(MIDDLE_EAST)
        & raw["Actor2CountryCode"].isin(MIDDLE_EAST)
        & (raw["Actor1CountryCode"] != raw["Actor2CountryCode"])   # 자국 내 사건 제외
        & raw["SQLDATE"].between(min_date, day)                     # 오래된 사건 제외
        & raw["EventCode"].isin(EVENT_CODES)
    )
    ev = raw[mask].copy()
    ev.insert(0, "DATE", day)
    ev["Actor1Country_KR"] = ev["Actor1CountryCode"].map(MIDDLE_EAST)
    ev["Actor2Country_KR"] = ev["Actor2CountryCode"].map(MIDDLE_EAST)
    ev["EventCode_KR"] = ev["EventCode"].map(EVENT_CODES)
    ev[NUMERIC_COLS] = ev[NUMERIC_COLS].apply(pd.to_numeric, errors="coerce")
    return ev


def make_tables(ev):
    pe = (
        ev.groupby(PAIR_KEYS + ["EventCode", "EventCode_KR"]).size()
        .reset_index(name="event_count")
        .sort_values("event_count", ascending=False).reset_index(drop=True)
    )
    pq = (
        ev.groupby(PAIR_KEYS + ["QuadClass"]).size()
        .unstack(fill_value=0).reindex(columns=["3", "4"], fill_value=0)
        .reset_index()
        .rename(columns={"3": "QuadClass_3_count", "4": "QuadClass_4_count"})
    )
    pq.columns.name = None
    pq["total_event_count"] = pq["QuadClass_3_count"] + pq["QuadClass_4_count"]
    pq = pq.sort_values("total_event_count", ascending=False).reset_index(drop=True)
    return pe, pq


def save_tables(folder, label, ev, pe, pq):
    folder.mkdir(parents=True, exist_ok=True)
    opts = dict(index=False, encoding="utf-8-sig")
    ev[[c for c in SHOW_COLS if c in ev.columns]].to_csv(folder / f"GDELT_{label}_중동_선택EventCode_필터링.csv", **opts)
    pe.to_csv(folder / f"GDELT_{label}_중동_국가쌍_EventCode별_이벤트수.csv", **opts)
    pq.to_csv(folder / f"GDELT_{label}_중동_국가쌍별_QuadClass.csv", **opts)


def run(year, month, use_server=False):
    if date(year, month, 1) < FIRST_DAILY:
        raise SystemExit("2013년 4월 이전은 일별 파일이 없어 지원하지 않습니다.")
    label = month_label(year, month)
    data_dir = EVENT_DIR / "data" / f"{label}_data"
    month_dir = EVENT_DIR / "output" / label
    days = [f"{year}{month:02d}{d:02d}" for d in range(1, monthrange(year, month)[1] + 1)]

    print(f"[{label}] 원본: {data_dir}")
    month_events, skipped = [], []
    for day in days:
        source = find_source(day, data_dir, use_server)
        if source is None:
            skipped.append(day)
            print(f"  {day}: 원본 없음 → 건너뜀")
            continue
        try:
            raw = pd.read_csv(source, sep="\t", header=None, names=HEADERS, dtype=str, compression="infer")
        except Exception as e:
            skipped.append(day)
            print(f"  {day}: 읽기 실패 ({e}) → 건너뜀")
            continue
        ev = filter_day(raw, day)
        del raw
        save_tables(month_dir / day, day, ev, *make_tables(ev))
        month_events.append(ev)
        print(f"  {day}: {len(ev):>5}건 저장")

    if not month_events:
        raise SystemExit("처리한 날짜가 없습니다. 먼저 download_gdelt_month.py로 원본을 받으세요.")

    monthly = pd.concat(month_events, ignore_index=True)
    before = len(monthly)
    monthly = monthly.drop_duplicates("GLOBALEVENTID")
    pe, pq = make_tables(monthly)
    out = month_dir / "월간"
    save_tables(out, f"{label}_월간", monthly, pe, pq)
    (
        monthly.groupby(["DATE"] + PAIR_KEYS).size().reset_index(name="event_count")
        .to_csv(out / f"GDELT_{label}_월간_중동_일별_국가쌍_이벤트수.csv", index=False, encoding="utf-8-sig")
    )

    print(f"\n완료: {len(days) - len(skipped)}/{len(days)}일 처리, 월간 이벤트 {len(monthly)}건 (중복 제거 {before - len(monthly)}건)")
    print(f"월간 결과: {out}")
    if skipped:
        print("건너뛴 날짜:", ", ".join(skipped))
    print("\n월간 국가쌍 상위 10:")
    print(pq.head(10)[["Actor1Country_KR", "Actor2Country_KR", "QuadClass_3_count", "QuadClass_4_count",
                       "total_event_count"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GDELT 중동 16개국 월 단위 분석")
    parser.add_argument("year", type=int, help="연도 (예: 2019)")
    parser.add_argument("month", type=int, help="월 (예: 5)")
    parser.add_argument("--server", action="store_true",
                        help="data 폴더에 없는 날짜는 GDELT 서버에서 직접 읽기 (원본은 저장하지 않음)")
    args = parser.parse_args()
    run(args.year, args.month, use_server=args.server)
