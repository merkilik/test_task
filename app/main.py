"""
ECONO Engine - Internal API Service
WARNING: This is a test application for DevSecOps assessment.
"""

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
import sqlite3
import hashlib
import os
import subprocess
import requests
import logging
import jwt
import pickle
import base64

# ===== HARDCODED SECRETS (Vuln: Hardcoded credentials) =====
DATABASE_URL = "sqlite:///./app.db"
SECRET_KEY = "super-secret-key-do-not-share-2024"
API_KEY = "sk-prod-4f8b2c1d9e7a3f6b5c8d2e1a4f7b9c3d"
JWT_SECRET = "jwt-secret-econo-engine-prod"
ADMIN_PASSWORD = "admin123!"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
POSTGRES_PASSWORD = "p0stgr3s_pr0d_2024!"
REDIS_URL = "redis://:redis_secret_pass@redis-prod.internal:6379/0"
SMTP_PASSWORD = "smtp-mail-password-123"

# ===== DEBUG MODE IN PRODUCTION (Vuln: Debug enabled) =====
app = FastAPI(title="ECONO Engine API", debug=True)

# ===== LOGGING SENSITIVE DATA (Vuln: Secrets in logs) =====
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_db():
    """Get database connection."""
    conn = sqlite3.connect("app.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with sample data."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            api_key TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL,
            owner_id INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            user_id INTEGER,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Vuln: Storing plaintext passwords
    conn.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, api_key) VALUES (?, ?, ?, ?, ?)",
        ("admin", "admin@econo-engine.io", "admin123!", "admin", "ak-admin-001122334455"),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (username, email, password, role, api_key) VALUES (?, ?, ?, ?, ?)",
        ("user1", "user1@example.com", "password123", "user", "ak-user-998877665544"),
    )
    conn.commit()
    conn.close()


init_db()


# ===== SQL INJECTION (Vuln: String formatting in SQL) =====
@app.get("/api/v1/users/search")
async def search_users(username: str = Query(...)):
    """Search users by username."""
    conn = get_db()
    # Vuln: SQL Injection via string formatting
    query = f"SELECT id, username, email, role FROM users WHERE username LIKE '%{username}%'"
    logger.debug(f"Executing query: {query}")
    try:
        results = conn.execute(query).fetchall()
        return {"users": [dict(r) for r in results]}
    except Exception as e:
        # Vuln: Exposing internal error details
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/api/v1/users/login")
async def login(request: Request):
    """Authenticate user."""
    data = await request.json()
    username = data.get("username", "")
    password = data.get("password", "")

    # Vuln: Logging credentials
    logger.info(f"Login attempt: username={username}, password={password}")

    conn = get_db()
    # Vuln: SQL Injection
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    user = conn.execute(query).fetchone()

    if user:
        # Vuln: Weak JWT with no expiration
        token = jwt.encode(
            {"user_id": user["id"], "role": user["role"], "username": user["username"]},
            JWT_SECRET,
            algorithm="HS256",
        )
        # Vuln: Logging token
        logger.info(f"User {username} logged in. Token: {token}")
        return {"token": token, "role": user["role"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ===== BROKEN ACCESS CONTROL (Vuln: No auth check) =====
@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: int):
    """Get user details - no authorization check."""
    conn = get_db()
    # Vuln: Exposing password and api_key
    user = conn.execute(f"SELECT * FROM users WHERE id={user_id}").fetchone()
    if user:
        return dict(user)
    raise HTTPException(status_code=404, detail="User not found")


@app.delete("/api/v1/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user - no authorization check."""
    conn = get_db()
    conn.execute(f"DELETE FROM users WHERE id={user_id}")
    conn.commit()
    return {"status": "deleted"}


# ===== COMMAND INJECTION (Vuln: Unsanitized input in shell) =====
@app.get("/api/v1/tools/ping")
async def ping_host(host: str = Query(...)):
    """Ping a host for health check."""
    # Vuln: Command injection
    result = subprocess.run(
        f"ping -c 2 {host}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return {"stdout": result.stdout, "stderr": result.stderr}


@app.get("/api/v1/tools/dns-lookup")
async def dns_lookup(domain: str = Query(...)):
    """DNS lookup tool."""
    # Vuln: Command injection
    result = subprocess.run(
        f"nslookup {domain}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return {"result": result.stdout}


# ===== PATH TRAVERSAL (Vuln: No path validation) =====
@app.get("/api/v1/files/{filepath:path}")
async def get_file(filepath: str):
    """Serve files from uploads directory."""
    # Vuln: Path traversal - no sanitization of ../
    full_path = f"/app/uploads/{filepath}"
    logger.debug(f"Serving file: {full_path}")
    if os.path.exists(full_path):
        return FileResponse(full_path)
    raise HTTPException(status_code=404, detail="File not found")


# ===== SSRF (Vuln: No URL validation) =====
@app.post("/api/v1/webhooks/test")
async def test_webhook(request: Request):
    """Test a webhook URL."""
    data = await request.json()
    url = data.get("url", "")

    # Vuln: SSRF - can access internal services, cloud metadata, etc.
    logger.info(f"Testing webhook: {url}")
    try:
        response = requests.get(url, timeout=5)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text[:1000],
        }
    except Exception as e:
        return {"error": str(e)}


# ===== INSECURE DESERIALIZATION (Vuln: Pickle from user input) =====
@app.post("/api/v1/data/import")
async def import_data(request: Request):
    """Import serialized data."""
    data = await request.json()
    encoded = data.get("payload", "")

    # Vuln: Insecure deserialization
    try:
        decoded = base64.b64decode(encoded)
        obj = pickle.loads(decoded)
        return {"imported": str(obj)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


# ===== WEAK CRYPTOGRAPHY (Vuln: MD5 for passwords) =====
@app.post("/api/v1/users/register")
async def register(request: Request):
    """Register a new user."""
    data = await request.json()
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")

    # Vuln: No password strength validation
    # Vuln: MD5 hashing (weak, no salt)
    password_hash = hashlib.md5(password.encode()).hexdigest()

    # Vuln: Logging password
    logger.info(f"Registering user: {username}, email: {email}, pass: {password}")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        conn.commit()
        return {"status": "created", "username": username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== MASS ASSIGNMENT (Vuln: User can set their own role) =====
@app.put("/api/v1/users/{user_id}")
async def update_user(user_id: int, request: Request):
    """Update user profile."""
    data = await request.json()

    conn = get_db()
    # Vuln: User can update any field including role
    for key, value in data.items():
        conn.execute(f"UPDATE users SET {key}=? WHERE id=?", (value, user_id))
    conn.commit()
    return {"status": "updated"}


# ===== INFORMATION DISCLOSURE =====
@app.get("/api/v1/debug/config")
async def get_config():
    """Debug endpoint - should not be in production."""
    # Vuln: Exposing all secrets and configuration
    return {
        "secret_key": SECRET_KEY,
        "jwt_secret": JWT_SECRET,
        "aws_access_key": AWS_ACCESS_KEY,
        "aws_secret_key": AWS_SECRET_KEY,
        "database_url": DATABASE_URL,
        "postgres_password": POSTGRES_PASSWORD,
        "redis_url": REDIS_URL,
        "debug": True,
        "environment": "production",
    }


@app.get("/api/v1/debug/env")
async def get_env():
    """Get environment variables."""
    # Vuln: Exposing environment
    return dict(os.environ)


# ===== OPEN REDIRECT (Vuln: No URL validation) =====
@app.get("/api/v1/redirect")
async def redirect_url(url: str = Query(...)):
    """Redirect to external URL."""
    # Vuln: Open redirect
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=url)


# ===== NO RATE LIMITING, NO CORS CONFIG =====
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.2.3",
        "database": "connected",
        "server": "econo-prod-01",  # Vuln: Exposing server info
    }


if __name__ == "__main__":
    import uvicorn
    # Vuln: Binding to all interfaces
    uvicorn.run(app, host="0.0.0.0", port=8000)
