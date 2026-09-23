from __future__ import annotations

import json
import shutil
import time
import uuid
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

from ..analysis import analyze_pdf
from ..config import settings
from ..removal import remove_watermarks

ROOT = Path(__file__).parent
TASKS: dict[str, dict] = {}


def _safe_filename(filename: str | None) -> str:
    name = (filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(char for char in name if char >= " " and char not in "\x7f")
    if not name or name in {".", ".."}:
        return "document.pdf"
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


def _cleanup_expired_tasks() -> None:
    now = time.time()
    for task_id, task in list(TASKS.items()):
        if now - task["created"] > settings.task_ttl_seconds:
            shutil.rmtree(task["dir"], ignore_errors=True)
            TASKS.pop(task_id, None)


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalPDFWatermarkTool/0.1"

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _is_local_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "")
        parsed = urlparse(origin)
        return (
            parsed.scheme == "http"
            and parsed.netloc == host
            and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        )

    def _upload_part(self, content_type: str, length: int):
        raw_body = self.rfile.read(length)
        envelope = (
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii")
            + raw_body
        )
        message = BytesParser(policy=policy.default).parsebytes(envelope)
        if not message.is_multipart():
            return None
        for part in message.iter_parts():
            if part.get_param("name", header="content-disposition") == "file":
                return _safe_filename(part.get_filename()), part.get_payload(decode=True) or b""
        return None

    def do_POST(self) -> None:
        _cleanup_expired_tasks()
        if not self._is_local_origin():
            return self._json(403, {"error": "仅允许从本地工具页面提交请求"})

        route = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._json(400, {"error": "请求长度无效"})
        if length <= 0:
            return self._json(400, {"error": "请求内容为空"})

        if route == "/api/analyze":
            if length > settings.max_bytes + 1024 * 1024:
                return self._json(413, {"error": "文件超过大小限制"})
            content_type = self.headers.get("Content-Type", "")
            if not content_type.lower().startswith("multipart/form-data;"):
                return self._json(400, {"error": "请以 multipart/form-data 上传 PDF"})
            try:
                upload = self._upload_part(content_type, length)
            except Exception:
                return self._json(400, {"error": "无法读取上传内容"})
            if not upload:
                return self._json(400, {"error": "请选择 PDF 文件"})
            filename, data = upload
            if len(data) > settings.max_bytes:
                return self._json(413, {"error": "文件超过大小限制"})
            if not data.startswith(b"%PDF-"):
                return self._json(400, {"error": "文件不是有效 PDF"})

            task_id = uuid.uuid4().hex
            task_dir = settings.temp_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            source = task_dir / filename
            source.write_bytes(data)
            try:
                result = analyze_pdf(source, max_pages=settings.max_pages)
            except ValueError as error:
                shutil.rmtree(task_dir, ignore_errors=True)
                return self._json(422, {"error": str(error)})
            except Exception:
                shutil.rmtree(task_dir, ignore_errors=True)
                return self._json(422, {"error": "PDF 无法解析或文件已损坏"})

            TASKS[task_id] = {
                "dir": task_dir,
                "source": source,
                "name": filename,
                "created": time.time(),
                "analysis": result,
            }
            return self._json(200, {"task_id": task_id, **result})

        if route == "/api/remove":
            if length > 1024 * 1024:
                return self._json(413, {"error": "请求内容超过限制"})
            try:
                body = json.loads(self.rfile.read(length))
                task_id = body["task_id"]
                selected = body.get("selected", [])
                if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
                    raise ValueError
            except Exception:
                return self._json(400, {"error": "请求参数无效"})
            task = TASKS.get(task_id)
            if not task:
                return self._json(404, {"error": "任务不存在或已过期，请重新导入 PDF"})
            allowed = {candidate["id"] for candidate in task["analysis"]["candidates"]}
            selected = [item for item in selected if item in allowed]
            output_name = Path(task["name"]).stem + "-去水印.pdf"
            output = task["dir"] / output_name
            try:
                removed, page_count = remove_watermarks(task["source"], output, selected)
            except Exception:
                return self._json(422, {"error": "PDF 处理失败，请确认源文件可读取"})
            task["output"] = output
            return self._json(
                200,
                {
                    "task_id": task_id,
                    "download": f"/api/download/{task_id}",
                    "removed": removed,
                    "pages": page_count,
                    "filename": output_name,
                },
            )

        self._json(404, {"error": "接口不存在"})

    def do_GET(self) -> None:
        _cleanup_expired_tasks()
        route = urlparse(self.path).path
        if route.startswith("/api/download/"):
            task = TASKS.get(route.rsplit("/", 1)[-1])
            if not task or not task.get("output") or not task["output"].exists():
                return self._json(404, {"error": "输出文件不存在或已过期"})
            data = task["output"].read_bytes()
            filename = quote(task["output"].name, safe="")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f"attachment; filename=download.pdf; filename*=UTF-8''{filename}")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return
        if route in {"/", "/index.html"}:
            data = (ROOT / "static" / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
            return
        self._json(404, {"error": "页面不存在"})

    def log_message(self, format: str, *args) -> None:
        print(format % args)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"PDF 去水印工具已启动：http://{host}:{port}")
    server.serve_forever()
