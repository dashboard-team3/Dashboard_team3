import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent          # db/ (pem 도 여기)
from core.paths import ENV_FILE          # 원본 pjL/.env (폴더를 옮겨도 core/paths.py 가 찾음)
load_dotenv(ENV_FILE)                    # 접속 정보는 원본 것을 읽음 (비밀번호를 복사하지 않음)


def get_connection():
    """RDS MySQL 연결 (SSL: global-bundle.pem)"""
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.getenv("DB_NAME") or None,
        charset="utf8mb4",
        ssl={"ca": str(BASE_DIR / "global-bundle.pem")},
        connect_timeout=10,
    )


if __name__ == "__main__":
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT VERSION(), DATABASE(), CURRENT_USER()")
        version, db, user = cur.fetchone()
        print(f"연결 성공 — MySQL {version} / DB: {db} / 사용자: {user}")
