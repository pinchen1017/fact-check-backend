# backend/main.py   (有 DB 的版本)
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

# 資料庫配置 - 使用環境變數
DB_HOST = os.getenv("DB_HOST", "35.221.147.151")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "linebot_v2")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "@Aa123456")

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://fact-check-system-static.onrender.com",
    "http://localhost:3000",  # 本地開發
    "http://localhost:5173",  # Vite 開發服務器
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageIn(BaseModel):
    user: str
    message: str

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )

@app.on_event("startup")
def startup():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        username TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.get("/")
def root():
    return {"message": "Fact Check System Backend API", "status": "running"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/db-test")
def test_database():
    """測試資料庫連接"""
    try:
        # 顯示環境變數狀態
        env_status = {
            "DB_HOST": DB_HOST,
            "DB_PORT": DB_PORT,
            "DB_NAME": DB_NAME,
            "DB_USER": DB_USER,
            "DB_PASS": "***" if DB_PASS else "NOT_SET"
        }
        
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1 as test")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {
            "status": "ok", 
            "database": "connected",
            "test_result": result[0],
            "environment_variables": env_status,
            "connection_info": f"Connected to {DB_HOST}:{DB_PORT}/{DB_NAME} as {DB_USER}"
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "connection_failed",
            "error": str(e),
            "error_type": type(e).__name__,
            "environment_variables": {
                "DB_HOST": DB_HOST,
                "DB_PORT": DB_PORT,
                "DB_NAME": DB_NAME,
                "DB_USER": DB_USER,
                "DB_PASS": "***" if DB_PASS else "NOT_SET"
            },
            "connection_string": f"postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        }

@app.post("/api/message")
def receive_message(payload: MessageIn):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO messages (username, message) VALUES (%s, %s) RETURNING id;",
                    (payload.user, payload.message))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"status":"ok", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/messages")
def list_messages(limit: int = 20):
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username, message, created_at FROM messages ORDER BY id DESC LIMIT %s;", (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"status":"ok", "messages": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 添加 session 相關端點
@app.get("/api-proxy/apps/judge/users/user/sessions/{session_id}")
def get_user_session(session_id: str):
    """獲取用戶 session 資料"""
    try:
        # 這裡可以根據 session_id 查詢用戶資料
        # 目前返回模擬資料
        return {
            "status": "ok",
            "session_id": session_id,
            "user_data": {
                "id": "user_123",
                "name": "測試用戶",
                "session_active": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/local-api/get_user_by_session")
def get_user_by_session_local():
    """本地 session 查詢端點"""
    return {"status": "ok", "message": "Local session endpoint"}

# 添加 Cofact API 代理端點
@app.get("/api/cofact/check")
def cofact_check(text: str):
    """Cofact API 查詢端點"""
    try:
        # 這裡可以整合 Cofact API
        # 目前返回模擬資料
        return {
            "status": "ok",
            "text": text,
            "result": {
                "credibility": 0.8,
                "source": "模擬資料",
                "analysis": "這是模擬的 Cofact 分析結果"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))