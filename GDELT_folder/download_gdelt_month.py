"""GDELT 1.0 일별 원본(zip)을 월 단위로 내려받는다.

사용법:  python download_gdelt_month.py 2026 8
- 저장 위치: event/data/2026.8_data/
- 이미 있고 MD5가 맞는 파일은 건너뜀, 받은 파일은 서버 MD5로 검증
"""
import hashlib
import sys
import time
import urllib.request
from calendar import monthrange
from pathlib import Path

BASE = "https://data.gdeltproject.org/events/"
EVENT_DIR = Path(__file__).resolve().parent


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def server_md5s():
    text = urllib.request.urlopen(BASE + "md5sums", timeout=60).read().decode()
    return {name: md5 for md5, name in (line.split() for line in text.splitlines() if line.strip())}


def main(year, month):
    out_dir = EVENT_DIR / "data" / f"{year}.{month}_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    md5s = server_md5s()
    ok, skipped, failed = 0, 0, []
    for day in range(1, monthrange(year, month)[1] + 1):
        name = f"{year}{month:02d}{day:02d}.export.CSV.zip"
        path = out_dir / name
        expected = md5s.get(name)
        if expected is None:
            failed.append((name, "서버 목록에 없음"))
            continue
        if path.exists() and md5_of(path) == expected:
            skipped += 1
            continue
        for attempt in range(3):
            try:
                tmp = path.with_suffix(".part")
                urllib.request.urlretrieve(BASE + name, tmp)
                if md5_of(tmp) != expected:
                    raise ValueError("MD5 불일치")
                tmp.replace(path)
                ok += 1
                print(f"받음 {name} ({path.stat().st_size / 1e6:.1f}MB)", flush=True)
                break
            except Exception as e:
                print(f"  재시도 {attempt + 1}/3 {name}: {e}", flush=True)
                time.sleep(3)
        else:
            failed.append((name, "3회 실패"))
    print(f"\n완료: 새로 받음 {ok}개, 이미 있음 {skipped}개, 실패 {len(failed)}개 → {out_dir}")
    for name, why in failed:
        print("  실패:", name, why)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
