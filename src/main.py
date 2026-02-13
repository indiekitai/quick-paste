"""
Quick Paste - Self-hosted pastebin for code and text sharing
"""
import os
import json
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

load_dotenv()

# Config
DATA_DIR = Path(os.getenv("PASTE_DATA_DIR", "/root/source/side-projects/quick-paste/data"))
BASE_URL = os.getenv("PASTE_BASE_URL", "http://localhost:8084")
MAX_SIZE = int(os.getenv("PASTE_MAX_SIZE", 500_000))  # 500KB default
DEFAULT_EXPIRY_HOURS = 24 * 7  # 1 week

# In-memory index (content stored in files)
pastes: dict[str, dict] = {}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "pastes").mkdir(exist_ok=True)


def load_index():
    global pastes
    index_file = DATA_DIR / "index.json"
    if index_file.exists():
        pastes = json.loads(index_file.read_text())
        # Clean expired
        now = datetime.utcnow()
        expired = [k for k, v in pastes.items() 
                   if v.get("expires_at") and datetime.fromisoformat(v["expires_at"]) < now]
        for k in expired:
            del pastes[k]
            (DATA_DIR / "pastes" / k).unlink(missing_ok=True)
        if expired:
            save_index()


def save_index():
    ensure_dirs()
    index_file = DATA_DIR / "index.json"
    index_file.write_text(json.dumps(pastes, indent=2))


def generate_id(length: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    while True:
        paste_id = ''.join(secrets.choice(alphabet) for _ in range(length))
        if paste_id not in pastes:
            return paste_id


def save_content(paste_id: str, content: str):
    ensure_dirs()
    (DATA_DIR / "pastes" / paste_id).write_text(content)


def load_content(paste_id: str) -> str | None:
    paste_file = DATA_DIR / "pastes" / paste_id
    if paste_file.exists():
        return paste_file.read_text()
    return None


def highlight_code(content: str, language: str | None = None) -> str:
    """Syntax highlight code using Pygments."""
    if not HAS_PYGMENTS:
        return f"<pre><code>{content}</code></pre>"
    
    try:
        if language:
            lexer = get_lexer_by_name(language)
        else:
            lexer = guess_lexer(content)
    except:
        lexer = TextLexer()
    
    formatter = HtmlFormatter(linenos=True, cssclass="highlight")
    return highlight(content, lexer, formatter)


# FastAPI app
app = FastAPI(
    title="Quick Paste",
    description="Self-hosted pastebin",
    version="0.1.0",
)


@app.on_event("startup")
async def startup():
    ensure_dirs()
    load_index()
    print(f"📋 Quick Paste started with {len(pastes)} pastes")


class PasteCreate(BaseModel):
    content: str
    language: str | None = None
    title: str | None = None
    expires_in_hours: int | None = DEFAULT_EXPIRY_HOURS
    burn_after_read: bool = False


class PasteResponse(BaseModel):
    id: str
    url: str
    raw_url: str
    created_at: str
    expires_at: str | None
    language: str | None


@app.get("/")
async def root():
    return {
        "name": "Quick Paste",
        "total_pastes": len(pastes),
        "max_size_bytes": MAX_SIZE,
        "api": {
            "create": "POST /api/paste",
            "view": "GET /{id}",
            "raw": "GET /{id}/raw",
            "delete": "DELETE /api/paste/{id}",
        }
    }


@app.post("/api/paste", response_model=PasteResponse)
async def create_paste(data: PasteCreate):
    """Create a new paste."""
    if len(data.content) > MAX_SIZE:
        raise HTTPException(status_code=413, detail=f"Content too large (max {MAX_SIZE} bytes)")
    
    if not data.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    paste_id = generate_id()
    now = datetime.utcnow()
    
    expires_at = None
    if data.expires_in_hours and data.expires_in_hours > 0:
        expires_at = (now + timedelta(hours=data.expires_in_hours)).isoformat()
    
    pastes[paste_id] = {
        "title": data.title,
        "language": data.language,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "burn_after_read": data.burn_after_read,
        "size": len(data.content),
    }
    
    save_content(paste_id, data.content)
    save_index()
    
    return PasteResponse(
        id=paste_id,
        url=f"{BASE_URL}/{paste_id}",
        raw_url=f"{BASE_URL}/{paste_id}/raw",
        created_at=pastes[paste_id]["created_at"],
        expires_at=expires_at,
        language=data.language,
    )


@app.get("/api/pastes")
async def list_pastes(limit: int = 50):
    """List recent pastes (metadata only)."""
    result = []
    for paste_id, meta in list(pastes.items())[:limit]:
        result.append({
            "id": paste_id,
            "url": f"{BASE_URL}/{paste_id}",
            "title": meta.get("title"),
            "language": meta.get("language"),
            "size": meta.get("size"),
            "created_at": meta["created_at"],
            "expires_at": meta.get("expires_at"),
        })
    return {"pastes": result, "total": len(pastes)}


@app.get("/{paste_id}/raw", response_class=PlainTextResponse)
async def get_paste_raw(paste_id: str):
    """Get raw paste content."""
    if paste_id not in pastes:
        raise HTTPException(status_code=404, detail="Paste not found")
    
    content = load_content(paste_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Paste content not found")
    
    meta = pastes[paste_id]
    
    # Burn after read
    if meta.get("burn_after_read"):
        del pastes[paste_id]
        (DATA_DIR / "pastes" / paste_id).unlink(missing_ok=True)
        save_index()
    
    return content


@app.get("/{paste_id}", response_class=HTMLResponse)
async def get_paste_html(paste_id: str):
    """Get paste with syntax highlighting."""
    if paste_id not in pastes:
        raise HTTPException(status_code=404, detail="Paste not found")
    
    content = load_content(paste_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Paste content not found")
    
    meta = pastes[paste_id]
    title = meta.get("title") or paste_id
    language = meta.get("language")
    
    highlighted = highlight_code(content, language)
    
    # Burn after read
    if meta.get("burn_after_read"):
        del pastes[paste_id]
        (DATA_DIR / "pastes" / paste_id).unlink(missing_ok=True)
        save_index()
    
    css = ""
    if HAS_PYGMENTS:
        css = HtmlFormatter().get_style_defs('.highlight')
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title} - Quick Paste</title>
    <style>
        body {{ font-family: monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
        .header {{ margin-bottom: 20px; }}
        .header a {{ color: #569cd6; }}
        .meta {{ color: #808080; font-size: 0.9em; }}
        pre {{ background: #2d2d2d; padding: 15px; overflow-x: auto; }}
        {css}
    </style>
</head>
<body>
    <div class="header">
        <h2>{title}</h2>
        <div class="meta">
            Language: {language or 'auto'} | 
            Created: {meta['created_at'][:19]} |
            <a href="/{paste_id}/raw">Raw</a>
        </div>
    </div>
    {highlighted}
</body>
</html>"""
    
    return html


@app.delete("/api/paste/{paste_id}")
async def delete_paste(paste_id: str):
    """Delete a paste."""
    if paste_id not in pastes:
        raise HTTPException(status_code=404, detail="Paste not found")
    
    del pastes[paste_id]
    (DATA_DIR / "pastes" / paste_id).unlink(missing_ok=True)
    save_index()
    
    return {"ok": True, "deleted": paste_id}


@app.get("/health")
async def health():
    return {"status": "ok", "pastes": len(pastes)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
