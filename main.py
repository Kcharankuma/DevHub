import json
import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response

@app.get("/robots.txt", response_class=Response)
def get_robots():
    content = """User-agent: *
Allow: /
Sitemap: https://yourdomain.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
def get_sitemap():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://yourdomain.com/</loc>
    <lastmod>2026-09-01</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=content, media_type="application/xml")

CATEGORY_NAMES = {
    "deployment": "☁️ Cloud & PaaS Deployment",
    "programming": "🚀 Compilers & Languages",
    "ide": "💻 Coding IDEs & Editors",
    "frontend": "🎨 Frontend Frameworks & UI",
    "backend": "⚙️ Backend Runtimes & Stacks",
    "database": "🗄️ Databases & GUI Clients",
    "devops": "🛠️ DevOps & Containers",
    "ai": "🤖 AI Runtimes & Local LLMs",
    "api": "📡 API Clients & Testing",
    "terminals": "⚡ Terminals, Shells & Git GUIs",
    "sysutils": "🔧 System, Network & Dev Utilities",
    "mobile": "📱 Mobile & Desktop SDKs",
    "design": "🖌️ UI/UX Design & 3D Modeling"
}

CATALOG_FILE = os.path.join("data", "catalog.json")
cached_catalog: List[Dict[str, Any]] = []
AUTO_SYNC_INTERVAL_SECONDS = 21600


def format_file_size(num_bytes: int) -> str:
    """Converts raw bytes into clean human-readable units (KB, MB, GB)."""
    if not num_bytes or num_bytes <= 0:
        return ""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def load_catalog() -> List[Dict[str, Any]]:
    if os.path.exists(CATALOG_FILE):
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_catalog():
    """Persist updated versions, URLs, and memory sizes to data/catalog.json."""
    try:
        with open(CATALOG_FILE, "w", encoding="utf-8") as f:
            json.dump(cached_catalog, f, indent=2)
    except Exception as e:
        print(f"Error persisting catalog to disk: {e}")


async def sync_github_releases():
    """Queries GitHub Releases API for dynamic repos, fetching latest assets and accurate byte sizes."""
    global cached_catalog
    headers = {"User-Agent": "DevHub-Universal-App"}

    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    has_changes = False

    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        for item in cached_catalog:
            repo = item.get("github_repo")
            pattern = item.get("asset_pattern")

            if repo:
                try:
                    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
                    res = await client.get(api_url)

                    if res.status_code == 200:
                        release_data = res.json()
                        new_version = release_data.get("tag_name", "Latest")

                        if item.get("version") != new_version:
                            item["version"] = new_version
                            has_changes = True

                        if pattern:
                            for asset in release_data.get("assets", []):
                                if pattern.lower() in asset.get("name", "").lower():
                                    new_url = asset.get("browser_download_url")
                                    raw_size = asset.get("size", 0)
                                    formatted_size = format_file_size(raw_size)

                                    if item.get("url") != new_url:
                                        item["url"] = new_url
                                        has_changes = True
                                    
                                    if item.get("size") != formatted_size:
                                        item["size"] = formatted_size
                                        has_changes = True
                                    break
                    elif res.status_code == 403:
                        print(f"GitHub rate limit reached while checking {repo}.")
                        break
                except Exception as e:
                    print(f"Error syncing {repo}: {e}")

    if has_changes:
        save_catalog()
        print("Catalog automatically updated with latest versions and memory sizes.")


async def periodic_sync_worker():
    await asyncio.sleep(5)
    while True:
        try:
            await sync_github_releases()
        except Exception as e:
            print(f"Auto-updater error: {e}")
        await asyncio.sleep(AUTO_SYNC_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global cached_catalog
    cached_catalog = load_catalog()
    sync_task = asyncio.create_task(periodic_sync_worker())
    yield
    sync_task.cancel()


app = FastAPI(title="DevHub Universal", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "categories": CATEGORY_NAMES,
            "catalog": cached_catalog,
        },
    )


@app.post("/api/sync")
async def trigger_sync():
    await sync_github_releases()
    return {"status": "success", "message": "Catalog synced with upstream releases and file sizes"}


@app.get("/download/{action}")
async def dynamic_download(action: str):
    file_map = {
        "docker_compose": (
            "version: '3.8'\n\nservices:\n  app:\n    build: .\n    ports:\n      - '3000:3000'\n    environment:\n      - NODE_ENV=development\n      - DATABASE_URL=postgres://postgres:password@db:5432/mydb\n    depends_on:\n      - db\n      - redis\n\n  db:\n    image: postgres:16-alpine\n    restart: always\n    environment:\n      POSTGRES_USER: postgres\n      POSTGRES_PASSWORD: password\n      POSTGRES_DB: mydb\n    ports:\n      - '5432:5432'\n    volumes:\n      - db_data:/var/lib/postgresql/data\n\n  redis:\n    image: redis:7-alpine\n    ports:\n      - '6379:6379'\n\nvolumes:\n  db_data:\n",
            "docker-compose.yml",
            "text/yaml",
        ),
        "html_boilerplate": (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n  <title>DevHub Project</title>\n  <style>\n    body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: grid; place-content: center; height: 100vh; margin: 0; }\n    h1 { color: #38bdf8; }\n  </style>\n</head>\n<body>\n  <h1>🚀 Your Frontend Project is Ready!</h1>\n</body>\n</html>',
            "index.html",
            "text/html",
        ),
        "tailwind_bundle": (
            "/** @type {import('tailwindcss').Config} */\nmodule.exports = {\n  content: ['./src/**/*.{html,js,jsx,ts,tsx}', './*.html'],\n  theme: {\n    extend: {},\n  },\n  plugins: [],\n};\n",
            "tailwind.config.js",
            "text/javascript",
        ),
        "svelte_starter": (
            "<script>\n  let count = 0;\n  function increment() {\n    count += 1;\n  }\n</script>\n\n<main>\n  <h1>Hello from Svelte 5!</h1>\n  <button on:click={increment}>\n    Clicks: {count}\n  </button>\n</main>\n\n<style>\n  main { text-align: center; padding: 2rem; font-family: sans-serif; }\n  button { padding: 0.5rem 1rem; font-size: 1rem; cursor: pointer; }\n</style>\n",
            "App.svelte",
            "text/plain",
        ),
        "alpine_starter": (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <title>Alpine.js Starter</title>\n  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>\n</head>\n<body style="font-family: sans-serif; padding: 2rem; text-align: center;">\n  <div x-data="{ count: 0 }">\n    <h1 x-text="\'Alpine Counter: \' + count"></h1>\n    <button @click="count++" style="padding: 0.5rem 1rem;">Increment</button>\n  </div>\n</body>\n</html>',
            "alpine-starter.html",
            "text/html",
        ),
        "normalize_css": (
            "/*! normalize.css v8.0.1 | MIT License | github.com/necolas/normalize.css */\nhtml{line-height:1.15;-webkit-text-size-adjust:100%}body{margin:0}main{display:block}h1{font-size:2em;margin:.67em 0}hr{box-sizing:content-box;height:0;overflow:visible}pre{font-family:monospace,monospace;font-size:1em}a{background-color:transparent}\n",
            "normalize.css",
            "text/css",
        ),
        "coolify_install": (
            "#!/bin/bash\n# Coolify 1-Click Free PaaS Installation Script\ncurl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash\n",
            "install-coolify.sh",
            "application/x-sh",
        ),
        "dokku_install": (
            "#!/bin/bash\n# Dokku Single Server PaaS Installation Script\nwget -nv -O - https://dokku.com/install/dokku.sh | DOKKU_TAG=v0.34.0 bash\n",
            "install-dokku.sh",
            "application/x-sh",
        ),
        "deployctl_script": (
            "# Run in PowerShell to install Deno Deploy CLI\nirm https://deno.land/install.ps1 | iex\ndeno install -A --global jsr:@deno/deployctl\n",
            "install-deployctl.ps1",
            "text/plain",
        ),
        "caprover_config": (
            '{\n  "schemaVersion": 2,\n  "template": "node/18-alpine"\n}\n',
            "captain-definition",
            "application/json",
        ),
        "kamal_config": (
            "service: my-app\nimage: username/my-app\nservers:\n  web:\n    - 192.168.0.1\nregistry:\n  username: username\n  password:\n    - KAMAL_REGISTRY_PASSWORD\nbuilder:\n  arch: amd64\n",
            "deploy.yml",
            "text/yaml",
        ),
        "wrangler_config": (
            'name = "my-cloudflare-worker"\nmain = "src/index.js"\ncompatibility_date = "2026-09-01"\n',
            "wrangler.toml",
            "text/plain",
        ),
        "render_config": (
            "services:\n  - type: web\n    name: api-service\n    env: python\n    plan: free\n    buildCommand: pip install -r requirements.txt\n    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT\n",
            "render.yaml",
            "text/yaml",
        ),
        "vercel_config": (
            '{\n  "version": 2,\n  "builds": [\n    { "src": "package.json", "use": "@vercel/node" }\n  ]\n}\n',
            "vercel.json",
            "application/json",
        ),
        "netlify_config": (
            '[build]\n  publish = "dist"\n  command = "npm run build"\n\n[[redirects]]\n  from = "/*"\n  to = "/index.html"\n  status = 200\n',
            "netlify.toml",
            "text/plain",
        ),
        "serverless_config": (
            "service: my-serverless-api\nframeworkVersion: '4'\nprovider:\n  name: aws\n  runtime: nodejs20.x\nfunctions:\n  api:\n    handler: index.handler\n    events:\n      - httpApi: '*'\n",
            "serverless.yml",
            "text/yaml",
        ),
        "surge_config": (
            "your-project-subdomain.surge.sh\n",
            "CNAME",
            "text/plain",
        ),
        "fastapi_starter": (
            "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'message': 'Hello FastAPI'}\n",
            "main.py",
            "text/x-python",
        ),
        "express_starter": (
            "const express = require('express');\nconst app = express();\nconst PORT = process.env.PORT || 3000;\n\napp.use(express.json());\napp.get('/', (req, res) => res.json({ status: 'ok' }));\napp.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n",
            "server.js",
            "text/javascript",
        ),
    }

    if action in file_map:
        content, filename, media_type = file_map[action]
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    return Response(content="Template not found", status_code=404)