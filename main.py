# backend/main.py   (有 DB 的版本)
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import traceback

# 資料庫配置 - 使用環境變數
DB_HOST = os.getenv("DB_HOST", "35.221.147.151")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "linebot_v2")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "@Aa123456")

app = FastAPI(
    title="Fact Check System API",
    description="事實查核系統後端 API",
    version="1.0.0"
)

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# 全局錯誤處理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"全局錯誤: {str(exc)}")
    logger.error(f"錯誤追蹤: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "內部服務器錯誤",
            "error": str(exc),
            "timestamp": "2024-01-01T00:00:00Z"
        }
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
        response_data = {
            "status": "ok",
            "session_id": session_id,
            "user_data": {
                "id": "user_123",
                "name": "測試用戶",
                "session_active": True
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        return response_data
    except Exception as e:
        # 確保錯誤響應也是有效的 JSON
        error_response = {
            "status": "error",
            "error": str(e),
            "session_id": session_id
        }
        raise HTTPException(status_code=500, detail=error_response)

@app.get("/local-api/get_user_by_session")
def get_user_by_session_local():
    """本地 session 查詢端點"""
    return {"status": "ok", "message": "Local session endpoint"}

# 添加 session 創建端點
@app.post("/api-proxy/apps/judge/users/user/sessions")
def create_user_session(session_data: dict = None):
    """創建用戶 session"""
    try:
        import uuid
        session_id = str(uuid.uuid4())
        
        response_data = {
            "status": "ok",
            "session_id": session_id,
            "message": "Session created successfully",
            "user_data": {
                "id": "user_123",
                "name": "測試用戶",
                "session_active": True
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        return response_data
    except Exception as e:
        error_response = {
            "status": "error",
            "error": str(e),
            "message": "Failed to create session"
        }
        raise HTTPException(status_code=500, detail=error_response)

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

# 添加多代理分析端點 - GET 方法
@app.get("/api/multi-agent-analysis")
def multi_agent_analysis_get():
    """多代理分析端點 - GET 方法"""
    try:
        logger.info("多代理分析請求 (GET)")
        
        # 模擬多代理分析結果
        response_data = {
            "status": "ok",
            "analysis_id": "analysis_123",
            "result": {
                "weight_calculation_json": {
                    "weights": [0.3, 0.4, 0.3],
                    "total_score": 0.75
                },
                "final_report_json": {
                    "summary": "分析完成",
                    "confidence": 0.8
                },
                "fact_check_result_json": {
                    "credibility": 0.8,
                    "source": "可信來源"
                },
                "classification_json": {
                    "category": "新聞",
                    "type": "真實"
                }
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        logger.info("多代理分析完成 (GET)")
        return response_data
    except Exception as e:
        logger.error(f"多代理分析錯誤 (GET): {str(e)}")
        error_response = {
            "status": "error",
            "error": str(e),
            "message": "Multi-agent analysis failed"
        }
        raise HTTPException(status_code=500, detail=error_response)

# 添加多代理分析端點 - POST 方法
@app.post("/api/multi-agent-analysis")
def multi_agent_analysis_post(analysis_data: dict = None):
    """多代理分析端點 - POST 方法"""
    try:
        logger.info("多代理分析請求 (POST)")
        
        # 模擬多代理分析結果
        response_data = {
            "status": "ok",
            "analysis_id": "analysis_123",
            "result": {
                "weight_calculation_json": {
                    "weights": [0.3, 0.4, 0.3],
                    "total_score": 0.75
                },
                "final_report_json": {
                    "summary": "分析完成",
                    "confidence": 0.8
                },
                "fact_check_result_json": {
                    "credibility": 0.8,
                    "source": "可信來源"
                },
                "classification_json": {
                    "category": "新聞",
                    "type": "真實"
                }
            },
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        logger.info("多代理分析完成 (POST)")
        return response_data
    except Exception as e:
        logger.error(f"多代理分析錯誤 (POST): {str(e)}")
        error_response = {
            "status": "error",
            "error": str(e),
            "message": "Multi-agent analysis failed"
        }
        raise HTTPException(status_code=500, detail=error_response)