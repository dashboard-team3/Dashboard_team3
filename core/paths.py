"""경로를 한곳에. 자료 · 실시간 수집 결과 · DB 접속 정보는 원본 pjL 폴더 것을 같이 쓴다
(실시간 수집기 run_realtime.py 가 pjL/data/realtime 에 쌓으므로, 따로 복사하면 어긋난다)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # pjL_v2 (이 대시보드)


def _find_pjl():
    """원본 pjL 폴더 찾기. 환경변수 PJL_DIR → 바로 옆 pjL → 옆 pjA/pjL → 바탕화면/pjA/pjL 순서.
    이 폴더(pjL_v2)를 바탕화면 등 어디로 옮겨도 원본 자료를 찾는다."""
    import os
    cands = [Path(os.environ["PJL_DIR"])] if os.environ.get("PJL_DIR") else []
    cands += [ROOT.parent / "pjL", ROOT.parent / "pjA" / "pjL", Path.home() / "Desktop" / "pjA" / "pjL"]
    return next((c for c in cands if (c / "data").is_dir()), cands[0])


PJL = _find_pjl()                                       # 원본 프로젝트: 자료 · 수집기 · .env
_OWN = ROOT / "data"                                    # 이 폴더 안 data/ (GitHub 에서 받은 경우 CSV 가 여기 있음)
DATA_DIR = _OWN if (_OWN / "risk_monthly_1980_2026.csv").exists() else PJL / "data"   # CSV 5개
REALTIME_DIR = next((d for d in [_OWN / "realtime", PJL / "data" / "realtime"] if d.is_dir()),
                    _OWN / "realtime")                  # 수집기가 쌓는 곳 (없으면 DB 에서 읽음)
ENV_FILE = next((f for f in [ROOT / ".env", PJL / ".env"] if f.exists()), ROOT / ".env")
                                                        # DB 접속 정보 — 이 폴더 .env 우선, 없으면 원본 pjL/.env
STYLE_DIR = ROOT / "styles"                             # style.css · style_light.css
