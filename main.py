import json
import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 1. Initialize FastAPI Application
app = FastAPI(
    title="DevHub Universal",
    description="Centralized Developer Tools & Binary Distribution Platform"
)

# 2. Mount Static Files and Configure Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "static")
templates_dir = os.path.join(BASE_DIR, "templates")
catalog_file = os.path.join(BASE_DIR, "data", "catalog.json")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=templates_dir)

# 3. Category Metadata Mapping
CATEGORIES = {
    "programming": "Programming Languages",
    "ide": "IDEs & Editors",
    "frontend": "Frontend Frameworks",
    "backend": "Backend Runtimes",
    "database": "Databases & Tools",
    "devops": "DevOps & Cloud",
    "deployment": "PaaS & Hosting",
    "ai": "AI & Local LLMs",
    "api": "API Clients",
    "terminals": "Terminals & Git",
    "sysutils": "System Utilities",
    "mobile": "Mobile Dev",
    "design": "Design & 3D"
}

def load_catalog():
    if os.path.exists(catalog_file):
        with open(catalog_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_catalog(data):
    os.makedirs(os.path.dirname(catalog_file), exist_ok=True)
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# 4. Search Engine Crawlability Routes (robots.txt & sitemap.xml)
@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots():
    content = "User-agent: *\nAllow: /\n"
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml", response_class=Response)
def get_sitemap(request: Request):
    base_url = str(request.base_url).rstrip("/")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
"""
    return Response(content=xml_content, media_type="application/xml")

# 5. Home Route (Web Dashboard)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    catalog = load_catalog()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "catalog": catalog,
            "categories": CATEGORIES
        }
    )

# 6. Background Release Sync API
@app.post("/api/sync")
def sync_github_releases():
    catalog = load_catalog()
    headers = {"User-Agent": "DevHub-Sync-Engine"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    updated = 0
    for item in catalog:
        repo = item.get("github_repo")
        asset_pattern = item.get("asset_pattern", "").lower()
        if not repo:
            continue

        try:
            res = requests.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers=headers,
                timeout=8
            )
            if res.status_code == 200:
                data = res.json()
                item["version"] = data.get("tag_name", item.get("version"))
                
                # Match download asset
                for asset in data.get("assets", []):
                    name = asset.get("name", "").lower()
                    if asset_pattern and asset_pattern in name:
                        item["url"] = asset.get("browser_download_url")
                        size_bytes = asset.get("size", 0)
                        if size_bytes > 0:
                            mb = size_bytes / (1024 * 1024)
                            item["size"] = f"{mb:.1f} MB" if mb < 1024 else f"{mb/1024:.2f} GB"
                        break
                updated += 1
        except Exception:
            continue

    save_catalog(catalog)
    return {"status": "ok", "updated_repositories": updated}

# 7. Starter Boilerplate Downloader Route
@app.get("/download/{template_key}")
def download_starter(template_key: str):
    templates_code = {
        "fastapi_starter": ("main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\ndef root():\n    return {'message': 'Hello from FastAPI!'}\n"),
        "docker_compose": ("docker-compose.yml", "version: '3.8'\nservices:\n  app:\n    image: node:22-alpine\n    ports:\n      - '3000:3000'\n"),
        "express_starter": ("index.js", "const express = require('express');\nconst app = express();\n\napp.get('/', (req, res) => res.send('Express running!'));\napp.listen(3000);\n"),
        "html_boilerplate": ("index.html", "<!DOCTYPE html>\n<html>\n<head><title>App</title></head>\n<body><h1>Hello World</h1></body>\n</html>\n")
    }
    
    filename, code = templates_code.get(template_key, ("snippet.txt", "Developer snippet"))
    return Response(
        content=code,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )