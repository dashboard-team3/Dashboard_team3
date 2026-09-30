"""run_realtime.py 가 쌓는 GDELT 2.0 실시간 결과를 읽어 KPI 숫자로 바꾼다.

수집기(프로젝트 루트의 run_realtime.py)는 따로 켜 두고, 구간마다 결과를 두 곳에 쌓는다. 이 파일은 읽기만 한다.
- DB (먼저 읽는 곳): RDS MySQL pjl 의 GDELT2_중동_선택EventCode_필터링 표 · realtime_state 표
- 파일 (DB 가 안 될 때): pjL/data/realtime/YYYYMMDD/ (UTC 날짜별 폴더) · realtime_state.txt
"""

import time
from datetime import datetime, timedelta, timezone

import pandas as pd


# ---------------------------------------------------------------- 경로

from core.paths import PJL, REALTIME_DIR as _RT   # 원본 pjL 폴더 (core/paths.py)
COLLECTOR_DIR = PJL                 # 수집기 run_realtime.py 가 있는 곳 = pjL 루트 (여기서는 읽지 않음)
REALTIME_DIR = _RT   # pjL/data/realtime (수집기가 여기에 쌓는다)
STATE_FILE = REALTIME_DIR / "realtime_state.txt"


# ---------------------------------------------------------------- 읽기 · 시각

def today_utc():
    """수집기 폴더 이름과 같은 형식의 오늘 날짜 (UTC 기준, 예: '20260921')."""
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def load_day(day):
    """그날(UTC)의 이벤트 표 (값은 수집 CSV 와 같은 글자 형식). DB 를 먼저 읽고, 안 되면 파일. 없으면 빈 표."""
    try:
        start = datetime.strptime(day, "%Y%m%d")
        cols, rows = _db_query(f"SELECT * FROM `{DB_TABLE}` WHERE `TIMESTAMP` >= %s AND `TIMESTAMP` < %s "
                               "ORDER BY `TIMESTAMP`, GLOBALEVENTID", (start, start + timedelta(days=1)))
        return _as_csv_text(pd.DataFrame(list(rows), columns=cols))
    except Exception:
        pass                                               # DB 가 안 되면 아래 파일로
    path = REALTIME_DIR / day / f"GDELT2_{day}_중동_선택EventCode_필터링.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def last_slot():
    """수집기가 마지막으로 처리한 15분 구간 (예: '20260921033000'). DB 먼저, 안 되면 파일. 없으면 None."""
    try:
        _, rows = _db_query("SELECT last_slot FROM realtime_state WHERE id = 1")
        ts = rows[0][0] if rows else ""
    except Exception:
        ts = STATE_FILE.read_text(encoding="utf-8").strip() if STATE_FILE.exists() else ""
    return ts if len(ts) == 14 and ts.isdigit() else None


def recent_days(n=7):
    """자료가 있는 최근 n일 (UTC, 'YYYYMMDD', 오래된 날부터). KPI 첫 카드 추이선에 쓴다."""
    try:
        _, rows = _db_query(f"SELECT DISTINCT DATE_FORMAT(`TIMESTAMP`, '%Y%m%d') AS d FROM `{DB_TABLE}` "
                            f"ORDER BY d DESC LIMIT {int(n)}")
        return sorted(r[0] for r in rows)
    except Exception:
        return sorted(d.name for d in REALTIME_DIR.iterdir() if d.is_dir())[-n:] if REALTIME_DIR.exists() else []


def slot_to_kst(ts):
    """'20260921033000'(UTC) -> '12:30' (한국 시간)"""
    utc = datetime.strptime(ts, "%Y%m%d%H%M%S")
    return (utc + timedelta(hours=9)).strftime("%H:%M")


# ---------------------------------------------------------------- DB 읽기 (RDS MySQL pjl)
# 수집기가 구간마다 DB 에도 넣는다 (run_realtime.sync_db). 카드 · 지도 · 목록이 같은 날을 여러 번 읽으므로
# 같은 질의는 30초 동안 다시 묻지 않는다. DB 가 안 되면 60초 동안은 묻지 않고 곧바로 파일을 읽는다.

DB_TABLE = "GDELT2_중동_선택EventCode_필터링"
_CACHE_SEC, _RETRY_SEC = 30, 60
_cache = {}
_db_down_until = 0.0


def _db_query(sql, args=None):
    global _db_down_until
    key = (sql, args)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _CACHE_SEC:
        return hit[1]
    if time.time() < _db_down_until:
        raise ConnectionError("DB 연결 잠시 쉼")
    try:
        from db.data import get_connection                 # pymysql · .env 가 없으면 여기서 실패 → 파일로
        con = get_connection()
        try:
            with con.cursor() as cur:
                cur.execute(sql, args)
                result = ([d[0] for d in cur.description], cur.fetchall())
        finally:
            con.close()
    except Exception:
        _db_down_until = time.time() + _RETRY_SEC
        raise
    _cache[key] = (time.time(), result)
    return result


def _as_csv_text(df):
    """DB 값을 수집 CSV 와 같은 글자 형식으로 ('YYYYMMDDHHMMSS' · 'YYYYMMDD' · 빈 값은 '')."""
    if df.empty:
        return pd.DataFrame()
    for c in ("TIMESTAMP", "DATEADDED_UTC"):
        df[c] = pd.to_datetime(df[c]).dt.strftime("%Y%m%d%H%M%S")
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"]).dt.strftime("%Y%m%d")
    return df.astype(object).where(df.notna(), "").astype(str)


# ---------------------------------------------------------------- KPI 카드 · 요약 한 줄

def top_country(df):
    """행위국·대상국 양쪽 등장을 합쳐 가장 많이 관여한 나라와 그 나라의 최다 상대국."""
    both = pd.concat([df["Actor1Country_KR"], df["Actor2Country_KR"]])
    counts = both.value_counts()
    name = counts.idxmax()

    rows = df[(df["Actor1Country_KR"] == name) | (df["Actor2Country_KR"] == name)]
    partner = rows["Actor1Country_KR"].where(rows["Actor1Country_KR"] != name, rows["Actor2Country_KR"])
    return name, int(counts.max()), partner.value_counts().idxmax()


def kpis():
    """대시보드 카드 3개에 들어갈 값을 한 번에 계산한다."""
    day = today_utc()
    df = load_day(day)
    slot = last_slot()

    result = {
        "total": len(df),
        "recent": 0,
        "top": None,              # (나라, 건수, 최다 상대국)
        "slot_kst": slot_to_kst(slot) if slot else None,
        "slot_utc": f"{slot[8:10]}:{slot[10:12]}" if slot else None,
    }
    if df.empty:
        return result

    # 마지막 처리 구간과 같은 TIMESTAMP만 센다. 직전 구간이 0건이면 0이 나온다.
    result["recent"] = int((df["TIMESTAMP"] == slot).sum()) if slot else 0
    result["top"] = top_country(df)
    return result


# ---------------------------------------------------------------- 지도용 국가별 집계

# 수집기가 감시하는 EventCode 20개를 지도 색 4가지로 묶는다.
CATEGORIES = {
    "무력사용": {"color": "#ef4444", "codes": {"190", "191", "192", "193", "194", "195", "196",
                                            "204", "2041", "2042"}},
    "위협·요구": {"color": "#60a5fa", "codes": {"138", "1381", "1382", "1383", "1384", "1385", "139"}},
    "군사태세": {"color": "#eab308", "codes": {"152", "154"}},
    "제재·단절": {"color": "#a855f7", "codes": {"163"}},
}
CATEGORY_OF_CODE = {code: name for name, c in CATEGORIES.items() for code in c["codes"]}

# 중동 16개국 표시 위치 (위도, 경도). 나라 중심이 아니라 이름이 겹치지 않는 자리로 잡았다.
COUNTRY_POS = {
    "튀르키예": (39.0, 35.0), "시리아": (35.4, 38.8), "레바논": (34.3, 35.6),
    "이스라엘": (31.0, 34.6), "팔레스타인": (32.4, 36.9), "요르단": (30.0, 37.6),
    "이라크": (33.0, 43.7), "이란": (32.5, 54.0), "쿠웨이트": (29.3, 47.6),
    "바레인": (26.1, 50.5), "카타르": (25.3, 51.2), "아랍에미리트": (23.9, 54.3),
    "오만": (21.0, 57.0), "사우디아라비아": (24.0, 45.0), "예멘": (15.6, 47.5),
    "이집트": (27.0, 30.5),
}
SHORT_NAME = {"아랍에미리트": "UAE"}

# 이름을 원의 어느 쪽에 붙일지. 레반트처럼 좁은 곳은 방향을 벌려 겹침을 줄인다. 없으면 아래쪽.
LABEL_SIDE = {
    "튀르키예": "middle left",    # 아래에 두면 시리아 이름과 부딪혀 지도가 시리아를 숨긴다 → 왼쪽(아나톨리아 서쪽)으로
    "아랍에미리트": "top center",    # 아래·오른쪽에 두면 카타르 이름과 부딪힌다 → 위(걸프 바다 쪽)로
    "레바논": "middle left",      # 이스라엘 위쪽 → 왼쪽 바다 쪽으로
    "이스라엘": "middle left",    # 왼쪽 바다 쪽으로
    "팔레스타인": "middle right",  # 오른쪽 요르단·이라크 방향 (이라크 이름은 위로 올려 비켜 줌)
    "시리아": "top center",        # 레바논·팔레스타인 이름과 떨어지게 위로
    "이라크": "top center",        # 팔레스타인 이름과 겹치지 않게 위로
    "쿠웨이트": "top center",
    "바레인": "middle left",
    "카타르": "bottom right",       # 바로 아래에 두면 사우디아라비아 이름과 부딪힌다
    "예멘": "middle right",         # 아래에 두면 지도 아래 끝에서 잘린다 → 오른쪽(아라비아해 쪽)으로
}


def country_stats(df):
    """나라별 오늘 이벤트 수, 유형별 수, 가장 많은 유형, 최다 상대국.

    한 사건은 행위국·대상국 양쪽에 한 번씩 센다 (최다 관여국 카드와 같은 기준).
    이벤트가 없는 나라도 0건으로 넣어서 지도에 이름은 보이게 한다.
    """
    rows = []
    if not df.empty:
        df = df.assign(category=df["EventCode"].map(CATEGORY_OF_CODE))
        long = pd.concat([
            df.rename(columns={"Actor1Country_KR": "country", "Actor2Country_KR": "partner"}),
            df.rename(columns={"Actor2Country_KR": "country", "Actor1Country_KR": "partner"}),
        ])[["country", "partner", "category"]]
    else:
        long = pd.DataFrame(columns=["country", "partner", "category"])

    for name, (lat, lon) in COUNTRY_POS.items():
        mine = long[long["country"] == name]
        by_cat = mine["category"].value_counts()
        rows.append({
            "country": name,
            "label": SHORT_NAME.get(name, name),
            "side": LABEL_SIDE.get(name, "bottom center"),
            "lat": lat, "lon": lon,
            "count": len(mine),
            "top_category": by_cat.idxmax() if len(by_cat) else None,
            "by_category": {cat: int(by_cat.get(cat, 0)) for cat in CATEGORIES},
            "top_partner": mine["partner"].value_counts().idxmax() if len(mine) else None,
        })
    return pd.DataFrame(rows)


def category_totals(df):
    """범례에 쓰는 유형별 오늘 이벤트 수 (사건 1건은 1번만 센다)."""
    if df.empty:
        return {cat: 0 for cat in CATEGORIES}
    counts = df["EventCode"].map(CATEGORY_OF_CODE).value_counts()
    return {cat: int(counts.get(cat, 0)) for cat in CATEGORIES}


# ---------------------------------------------------------------- 네트워크용 국가쌍 집계

def pair_stats(df, category=None):
    """오늘의 국가쌍(방향 무시) 목록. category를 주면 그 유형 사건만 센다.

    columns: a, b, count, a_to_b, b_to_a, top_category, by_category
    """
    cols = ["a", "b", "count", "a_to_b", "b_to_a", "top_category", "by_category"]
    if df.empty:
        return pd.DataFrame(columns=cols)

    df = df.assign(category=df["EventCode"].map(CATEGORY_OF_CODE))
    if category:
        df = df[df["category"] == category]
    if df.empty:
        return pd.DataFrame(columns=cols)

    src, dst = df["Actor1Country_KR"], df["Actor2Country_KR"]
    df = df.assign(a=src.where(src < dst, dst), b=dst.where(src < dst, src))   # (A,B)와 (B,A)를 한 쌍으로

    rows = []
    for (a, b), g in df.groupby(["a", "b"]):
        by_cat = g["category"].value_counts()
        rows.append({
            "a": a, "b": b, "count": len(g),
            "a_to_b": int((g["Actor1Country_KR"] == a).sum()),
            "b_to_a": int((g["Actor1Country_KR"] == b).sum()),
            "top_category": by_cat.idxmax(),
            "by_category": {cat: int(by_cat.get(cat, 0)) for cat in CATEGORIES},
        })
    return pd.DataFrame(rows, columns=cols).sort_values("count", ascending=False).reset_index(drop=True)


def network_positions(x_scale=2.0):
    """16개국을 타원 둘레에 고정 배치한다. 순서는 실제 지리 방향을 따른다.

    x_scale=2.0 이면 가로:세로 2:1 타원. 넓은 패널을 채우고 이름 사이 간격이 벌어진다.

    데이터가 바뀌어도 나라 위치가 그대로라 1분마다 다시 그려도 화면이 흔들리지 않는다.
    """
    import math
    lat0, lon0 = 28.0, 43.0                       # 중동 한가운데쯤
    angles = {n: math.atan2(lat - lat0, lon - lon0) for n, (lat, lon) in COUNTRY_POS.items()}
    order = sorted(angles, key=angles.get)
    step = 2 * math.pi / len(order)
    # 서쪽(이집트)에서 시작해 남 → 동 → 북으로 돈다. 실제 방위와 같은 방향이다.
    return {n: (x_scale * math.cos(-math.pi + i * step), math.sin(-math.pi + i * step))
            for i, n in enumerate(order)}


# ---------------------------------------------------------------- 최근 사건 피드

def coverage_grade(articles):
    """기사 수(NumArticles)를 보도량 3단계로 바꾼다. 수집된 사건의 약 절반이 1~2건, 약 10%가 8건 이상이다."""
    if articles >= 8:
        return "보도 많음", "hot"
    if articles >= 3:
        return "보도 보통", "warm"
    return "보도 적음", "calm"


def days_before(event_yyyymmdd, added_yyyymmddhhmmss):
    """사건이 실제로 일어난 날이 수집된 날보다 며칠 앞인지. 형식이 깨졌으면 0."""
    try:
        event = datetime.strptime(event_yyyymmdd, "%Y%m%d").date()
        added = datetime.strptime(added_yyyymmddhhmmss[:8], "%Y%m%d").date()
    except (TypeError, ValueError):
        return 0
    return max((added - event).days, 0)


def recent_events(df, limit=100):
    """오늘 사건을 최신순으로 정리한다. 피드 한 줄에 필요한 값만 담는다.

    GDELT는 기사 하나에서 사건을 여러 개 뽑기 때문에, 같은 기사 + 같은 국가쌍(행위국→대상국)은
    한 줄로 묶는다. 묶인 줄은 사건 종류를 모두 보여주고 'count'에 몇 건이 묶였는지 담는다.
    """
    from urllib.parse import urlparse

    if df.empty:
        return []
    df = df.sort_values(["DATEADDED_UTC", "GLOBALEVENTID"], ascending=False)

    items, index = [], {}
    for r in df.itertuples():
        url = r.SOURCEURL or ""
        key = (url or r.GLOBALEVENTID, r.Actor1Country_KR, r.Actor2Country_KR)
        try:
            articles = int(float(r.NumArticles))
        except (TypeError, ValueError):
            articles = 0

        if key in index:                       # 이미 있는 줄에 합친다 (최신 사건이 먼저 들어가 있음)
            it = items[index[key]]
            it["count"] += 1
            if r.EventCode_KR not in it["whats"]:
                it["whats"].append(r.EventCode_KR)
            if articles > it["articles"]:
                it["articles"] = articles
                it["grade"], it["grade_class"] = coverage_grade(articles)
            it["days_before"] = max(it["days_before"], days_before(r.SQLDATE, r.DATEADDED_UTC))
            continue

        if len(items) >= limit:
            continue
        category = CATEGORY_OF_CODE.get(r.EventCode)
        grade, grade_class = coverage_grade(articles)
        domain = urlparse(url).netloc.removeprefix("www.") if url.startswith("http") else ""
        index[key] = len(items)
        items.append({
            "time_kst": slot_to_kst(r.DATEADDED_UTC) if len(r.DATEADDED_UTC) == 14 else "",
            "src": r.Actor1Country_KR,
            "dst": r.Actor2Country_KR,
            "root": r.EventRootCode,
            "category": category,
            "color": CATEGORIES[category]["color"] if category else "#8b98ad",
            "whats": [r.EventCode_KR],
            "where": r.ActionGeo_FullName,
            "url": url,
            "domain": domain,
            "articles": articles,
            "grade": grade,
            "grade_class": grade_class,
            "days_before": days_before(r.SQLDATE, r.DATEADDED_UTC),
            "count": 1,
        })
    return items


# ---------------------------------------------------------------- 직접 실행해 확인

if __name__ == "__main__":
    print(kpis())
