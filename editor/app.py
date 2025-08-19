#!/usr/bin/env python3
"""
Hit By A Bus Plan - Live Editor
Web-based editor for content files with auto-rebuild
"""

import os
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from datetime import date

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yaml
import uvicorn
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
CONTENT_DIR = Path("/app/content")
SITE_DIR = Path("/app/site")
OUTPUT_DIR = Path("/app/output")
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Hit By A Bus Plan Editor", version="1.0.0")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Global state for rebuild management
rebuild_in_progress = False
rebuild_queue = asyncio.Queue()


class ContentFile:
    """Represents a content markdown file with structured data"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.section_number = int(filepath.stem.split('-')[0]) if '-' in filepath.stem else 99
        self.section_name = ' '.join(filepath.stem.split('-')[1:]).title()
        self._load_content()

    def _load_content(self):
        """Load and parse the markdown file"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split front matter and content
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 3:
                    self.front_matter = yaml.safe_load(parts[1]) or {}
                    self.body = parts[2].strip()
                else:
                    self.front_matter = {}
                    self.body = content
            else:
                self.front_matter = {}
                self.body = content

        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")
            self.front_matter = {}
            self.body = ""

    def save(self, title: str, summary: str, critical: bool, body: str):
        """Save updated content back to file"""
        # Update front matter
        self.front_matter.update({
            'title': title,
            'updated': date.today().strftime('%Y-%m-%d'),
            'summary': summary,
            'critical': critical
        })
        self.body = body

        # Write back to file
        content = "---\n"
        content += yaml.dump(self.front_matter, default_flow_style=False)
        content += "---\n\n"
        content += body

        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # Trigger rebuild
        asyncio.create_task(trigger_rebuild())

    @property
    def title(self) -> str:
        return self.front_matter.get('title', self.section_name)

    @property
    def summary(self) -> str:
        return self.front_matter.get('summary', '')

    @property
    def critical(self) -> bool:
        return self.front_matter.get('critical', False)

    @property
    def updated(self) -> str:
        return self.front_matter.get('updated', '')


class SecurityScanner:
    """Handles comprehensive security scanning using detect-secrets and generic scanner"""

    @staticmethod
    async def scan():
        """Run comprehensive security scan for secrets and financial data"""
        print("🔍 Running comprehensive security scan...")

        scan_passed = True

        # 1. detect-secrets scan
        try:
            # Check if detect-secrets is available
            check_process = await asyncio.create_subprocess_exec(
                'which', 'detect-secrets',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await check_process.communicate()

            if check_process.returncode == 0:
                # Run security scan
                process = await asyncio.create_subprocess_exec(
                    'detect-secrets', 'scan', '--all-files',
                    cwd='/app',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                scan_result = stdout.decode()

                # Check if any secrets were found
                if '"results": {}' in scan_result:
                    print("✅ detect-secrets: no secrets detected")
                else:
                    print("🚨 detect-secrets found issues!")
                    scan_passed = False
            else:
                print("⚠️  detect-secrets not installed")

        except Exception as e:
            print(f"⚠️  detect-secrets error: {e}")
            scan_passed = False

        # 2. Generic secrets scan (credit cards, IBANs, etc)
        try:
            scanner_path = Path('/app/scripts/scan_generic_secrets.py')
            if scanner_path.exists():
                process = await asyncio.create_subprocess_exec(
                    'python3', str(scanner_path), '/app/content', '--json',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    result = json.loads(stdout.decode())
                    if result:
                        print(f"🚨 Generic scan found {len(result)} financial data items!")
                        scan_passed = False
                    else:
                        print("✅ Generic scan: no financial data detected")
                else:
                    print(f"⚠️  Generic scan failed: {stderr.decode()}")
            else:
                print("⚠️  Generic scanner not found")

        except Exception as e:
            print(f"⚠️  Generic scan error: {e}")

        if scan_passed:
            print("✅ Comprehensive security scan passed")
        else:
            print("🚨 SECURITY ALERT: Issues detected!")
            print("❌ Please remove sensitive data and store only references")
            print("💡 Example: 'Account details in 1Password vault' instead of actual numbers")

        return scan_passed


class MkDocsRebuilder:
    """Handles MkDocs rebuilds with security scanning"""

    @staticmethod
    async def rebuild():
        """Rebuild the MkDocs site with security check"""
        global rebuild_in_progress

        if rebuild_in_progress:
            return

        rebuild_in_progress = True
        try:
            print("🔄 Starting site rebuild with security check...")

            # Run security scan first
            scan_passed = await SecurityScanner.scan()
            if not scan_passed:
                print("⚠️  Build proceeding despite security warnings - please review content")

            # Run mkdocs build
            print("📚 Building MkDocs site...")
            process = await asyncio.create_subprocess_exec(
                'mkdocs', 'build', '--clean',
                cwd=str(SITE_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                print("✅ MkDocs rebuild successful")
            else:
                print(f"❌ MkDocs rebuild failed: {stderr.decode()}")

        except Exception as e:
            print(f"❌ Rebuild error: {e}")
        finally:
            rebuild_in_progress = False


async def trigger_rebuild():
    """Queue a rebuild"""
    try:
        rebuild_queue.put_nowait("rebuild")
    except asyncio.QueueFull:
        pass  # Already queued


async def rebuild_worker():
    """Background worker to process rebuild queue"""
    while True:
        try:
            await rebuild_queue.get()
            await asyncio.sleep(1)  # Debounce multiple rapid changes
            await MkDocsRebuilder.rebuild()
            rebuild_queue.task_done()
        except Exception as e:
            print(f"Rebuild worker error: {e}")


def get_content_files() -> List[ContentFile]:
    """Get all content files sorted by section number"""
    files = []
    for filepath in CONTENT_DIR.glob("*.md"):
        if filepath.name.startswith('.'):
            continue
        files.append(ContentFile(filepath))

    return sorted(files, key=lambda f: f.section_number)


@app.on_event("startup")
async def startup_event():
    """Start background rebuild worker and run initial security scan"""
    asyncio.create_task(rebuild_worker())

    # Run initial security scan
    print("🚀 Starting Hit By A Bus Plan Editor...")
    await SecurityScanner.scan()


@app.get("/", response_class=HTMLResponse)
async def editor_home(request: Request):
    """Main editor interface"""
    content_files = get_content_files()
    return templates.TemplateResponse("editor.html", {
        "request": request,
        "content_files": content_files,
        "title": "Hit By A Bus Plan - Editor"
    })


@app.get("/edit/{filename}", response_class=HTMLResponse)
async def edit_file(request: Request, filename: str):
    """Edit a specific content file"""
    filepath = CONTENT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content_file = ContentFile(filepath)
    return templates.TemplateResponse("edit_file.html", {
        "request": request,
        "file": content_file,
        "title": f"Edit {content_file.title}"
    })


@app.post("/save/{filename}")
async def save_file(
    filename: str,
    title: str = Form(...),
    summary: str = Form(...),
    critical: bool = Form(False),
    body: str = Form(...)
):
    """Save changes to a content file with security scanning"""
    filepath = CONTENT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    content_file = ContentFile(filepath)
    content_file.save(title, summary, critical, body)

    return RedirectResponse(url="/", status_code=303)


@app.get("/preview", response_class=HTMLResponse)
async def preview_site(request: Request):
    """Preview the generated site"""
    return templates.TemplateResponse("preview.html", {
        "request": request,
        "title": "Site Preview"
    })


@app.get("/api/rebuild")
async def api_rebuild():
    """Manual rebuild trigger"""
    await trigger_rebuild()
    return {"status": "rebuild_queued"}


@app.get("/api/status")
async def api_status():
    """Get current status"""
    return {
        "rebuild_in_progress": rebuild_in_progress,
        "content_files": len(get_content_files()),
        "site_built": (OUTPUT_DIR / "site" / "index.html").exists(),
        "pdf_exists": (OUTPUT_DIR / "site" / "Hit-By-A-Bus-Plan.pdf").exists(),
        "security_scanner_available": await check_security_scanner()
    }


async def check_security_scanner():
    """Check if detect-secrets is available"""
    try:
        process = await asyncio.create_subprocess_exec(
            'which', 'detect-secrets',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except:
        return False


@app.get("/api/security-scan")
async def api_security_scan():
    """Manual security scan trigger"""
    scan_passed = await SecurityScanner.scan()
    return {
        "scan_passed": scan_passed,
        "message": "Security scan completed" if scan_passed else "Security scan detected potential issues"
    }


if __name__ == "__main__":
    # Ensure directories exist
    CONTENT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
