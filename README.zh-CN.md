[English](README.md) | [中文](README.zh-CN.md)

# 📋 Quick Paste

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

自托管代码分享服务，支持语法高亮和阅后即焚。

## 功能

- 🎨 语法高亮（Pygments）
- 🔥 阅后即焚（burn after read）
- ⏰ 自动过期
- 📝 支持任意文本/代码
- 💾 文件存储，零依赖数据库

## 快速开始

```bash
cd /root/source/side-projects/quick-paste

# 安装依赖
pip install fastapi uvicorn python-dotenv pygments

# 配置
cp .env.example .env

# 运行
uvicorn src.main:app --port 8084
```

## 使用

### 创建代码片段

```bash
# 简单粘贴
curl -X POST http://localhost:8084/api/paste \
  -H "Content-Type: application/json" \
  -d '{"content": "print(\"Hello World\")", "language": "python"}'

# 带选项
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

### 查看代码片段

- **高亮显示**: `http://localhost:8084/{id}`
- **原始文本**: `http://localhost:8084/{id}/raw`

### 命令行使用

```bash
paste() {
  curl -s -X POST http://localhost:8084/api/paste \
    -H "Content-Type: application/json" \
    -d "{\"content\": $(cat | jq -Rs .)}" | jq -r .url
}

echo "Hello" | paste
```

## API

| 端点 | 方法 | 描述 |
|------|------|------|
| `/{id}` | GET | 高亮查看 |
| `/{id}/raw` | GET | 原始内容 |
| `/api/paste` | POST | 创建代码片段 |
| `/api/pastes` | GET | 列出所有片段 |
| `/api/paste/{id}` | DELETE | 删除片段 |

### 在线体验

```bash
# 创建代码片段
curl -X POST https://p.indiekit.ai/api/paste \
  -H "Content-Type: application/json" \
  -d '{"content": "print(\"Hello IndieKit!\")", "language": "python"}'

# 查看原始内容
curl https://p.indiekit.ai/{id}/raw
```

## 支持语言

Python、JavaScript、TypeScript、Go、Rust、SQL、JSON、YAML、Markdown、Bash 等 500+ 种语言（基于 Pygments）。

## 数据存储

```
data/
├── index.json        # 元数据索引
└── pastes/
    ├── abc12345      # 代码片段文件
    └── ...
```

## License

MIT
