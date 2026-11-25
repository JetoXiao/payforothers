# 资源下载页与 Cloudflare R2

前台资源下载页位于 `/downloads`。页面只读取公开的 `manifest.json`，文件本身由 R2 公共域名或 Cloudflare 自定义域名提供。R2 Access Key、Secret Access Key 和 S3 API Endpoint 不应出现在前端环境变量中。

## 1. R2 文件结构

可以按下面的结构上传对象：

```text
manifest.json
files/
  ai-starter-kit.zip
  prompt-library.pdf
  quick-start.md
```

`manifest.json` 示例：

```json
{
  "resources": [
    {
      "id": "ai-starter-kit",
      "title": {
        "zh-CN": "AI 使用入门包",
        "zh-TW": "AI 使用入門包",
        "en-US": "AI Starter Kit"
      },
      "description": {
        "zh-CN": "整理好的使用指南、快捷指令与常用检查清单。",
        "zh-TW": "整理好的使用指南、快捷指令與常用檢查清單。",
        "en-US": "Guides, prompts, and practical checklists for getting started."
      },
      "category": "工具包",
      "version": "v1.0",
      "size": "2.4 MB",
      "updated_at": "2026-11-25T00:00:00Z",
      "file_key": "files/ai-starter-kit.zip",
      "icon": "archive",
      "featured": true
    }
  ]
}
```

`url` 也可以直接写在资源项中；写了 `url` 时会优先使用它。否则页面用 `VITE_R2_PUBLIC_URL + file_key` 生成下载地址。

## 2. 前端环境变量

复制 `frontend/user/.env.example` 为 `.env.production`，填入 R2 的公开自定义域名：

```dotenv
VITE_R2_MANIFEST_URL=https://downloads.example.com/manifest.json
VITE_R2_PUBLIC_URL=https://downloads.example.com
```

环境变量会被编译进浏览器，所以只填写公开 URL。生产构建后重新发布前端：

```powershell
cd frontend/user
pnpm run build
```

如果不设置变量，页面默认请求当前站点的 `/downloads/manifest.json`，适合在 Cloudflare Worker 或 Nginx 中做同源反向代理。

## 3. R2 CORS

如果 manifest 和文件使用独立的 R2 自定义域名，在 R2 Bucket 的 CORS 设置中允许站点来源。下载使用普通 `<a>` 链接，CORS 主要用于浏览器读取 manifest：

```json
[
  {
    "AllowedOrigins": ["https://你的站点域名"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["Content-Length", "ETag", "Last-Modified"],
    "MaxAgeSeconds": 3600
  }
]
```

如果使用同源 Worker 代理，则把 `VITE_R2_MANIFEST_URL` 保持为 `/downloads/manifest.json`，并让 Worker 为响应增加 `Access-Control-Allow-Origin` 和 `Content-Type: application/json`。

## 4. 缓存建议

给 `manifest.json` 设置较短的浏览器/边缘缓存（例如 60 秒），文件对象可以设置较长缓存并使用带版本号的 key。更新文件时先上传新对象，再更新 manifest，避免用户拿到已删除的旧对象。
