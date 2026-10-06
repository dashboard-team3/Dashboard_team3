import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent          # db/ (pem 도 여기)
from core.paths import ENV_FILE          # 원본 pjL/.env (폴더를 옮겨도 core/paths.py 가 찾음)
load_dotenv(ENV_FILE)                    # 접속 정보는 원본 것을 읽음 (비밀번호를 복사하지 않음)


def _cfg(key, default=None):
    """접속 정보 한 항목. 환경변수(.env) → Streamlit secrets 순서.
    Streamlit Community Cloud 는 .env 대신 앱 설정의 Secrets(TOML) 로 값을 주므로, 거기에
    DB_HOST · DB_PORT · DB_USER · DB_PASSWORD · DB_NAME 을 적어 두면 그대로 읽는다 (2026-10-04)."""
    val = os.environ.get(key)
    if val is None:
        try:
            import streamlit as st
            val = st.secrets.get(key)             # secrets 파일이 없으면 여기서 예외 → None
        except Exception:
            val = None
    if val is None:
        if default is None:
            raise KeyError(key)
        return default
    return val


def _use_ssl(host):
    """RDS 는 SSL(global-bundle.pem) 로 붙고, 덤프를 복원한 로컬 MySQL(localhost) 은 SSL 없이 붙는다.
    DB_SSL=0 / 1 로 강제할 수도 있다 (2026-10-06, 백업 덤프로 실시간 화면 보는 경우)."""
    flag = str(_cfg("DB_SSL", "auto")).strip().lower()
    if flag in ("0", "false", "off", "no"):
        return False
    if flag in ("1", "true", "on", "yes"):
        return True
    return host not in ("localhost", "127.0.0.1", "::1")


def get_connection():
    """MySQL 연결. RDS 는 SSL(global-bundle.pem), 로컬(localhost) 은 SSL 없이."""
    host = _cfg("DB_HOST")
    kw = dict(
        host=host,
        port=int(_cfg("DB_PORT", 3306)),
        user=_cfg("DB_USER"),
        password=_cfg("DB_PASSWORD"),
        database=_cfg("DB_NAME", "") or None,
        charset="utf8mb4",
        connect_timeout=10,
    )
    if _use_ssl(host):
        kw["ssl"] = {"ca": str(BASE_DIR / "global-bundle.pem")}
    return pymysql.connect(**kw)


if __name__ == "__main__":
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT VERSION(), DATABASE(), CURRENT_USER()")
        version, db, user = cur.fetchone()
        print(f"연결 성공 — MySQL {version} / DB: {db} / 사용자: {user}")
