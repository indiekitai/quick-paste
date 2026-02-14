# 📋 Quick Paste

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

Self-hosted pastebin with syntax highlighting.

自托管代码分享服务，支持语法高亮和阅后即焚。

## Features

- 🎨 语法高亮 (Pygments)
- 🔥 阅后即焚 (burn after read)
- ⏰ 自动过期
- 📝 支持任意文本/代码
- 💾 文件存储，零依赖数据库

## Quick Start

```bash
cd /root/source/side-projects/quick-paste

# Install
pip install fastapi uvicorn python-dotenv pygments

# Configure
cp .env.example .env

# Run
uvicorn src.main:app --port 8084
```

## Usage

### Create Paste

```bash
# Simple paste
curl -X POST http://localhost:8084/api/paste \
  -H "Content-Type: application/json" \
  -d '{"content": "print(\"Hello World\")", "language": "python"}'

# With options
curl -X POST http://localhost:8084/api/paste \
  -H "Content-Type: application/json" \
  -d '{
    "content": "SELECT * FROM users;",
    "language": "sql",
    "title": "User Query",
    "expires_in_hours": 24,
    "burn_after_read": true
  }'
```

### View Paste

- **Highlighted**: `http://localhost:8084/{id}`
- **Raw text**: `http://localhost:8084/{id}/raw`

### CLI Usage

```bash
# Pipe directly
cat script.py | curl -X POST http://localhost:8084/api/paste \
  -H "Content-Type: application/json" \
  -d @- --data-urlencode "content@-"

# Or use a simple function
paste() {
  curl -s -X POST http://localhost:8084/api/paste \
    -H "Content-Type: application/json" \
    -d "{\"content\": $(cat | jq -Rs .)}" | jq -r .url
}

echo "Hello" | paste
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/{id}` | GET | View with highlighting |
| `/{id}/raw` | GET | Raw content |
| `/api/paste` | POST | Create paste |
| `/api/pastes` | GET | List pastes |
| `/api/paste/{id}` | DELETE | Delete paste |

## Supported Languages

Python, JavaScript, TypeScript, Go, Rust, SQL, JSON, YAML, Markdown, Bash, and 500+ more via Pygments.

## Data Storage

```
data/
├── index.json        # Paste metadata
└── pastes/
    ├── abc12345      # Paste content files
    └── ...
```

## License

MIT
