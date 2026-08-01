#!/usr/bin/env python3
"""Local-only web interface for tailored CV and portfolio generation."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import generate as generator


HOST = "127.0.0.1"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
UI_DIR = Path(__file__).resolve().parent / "ui"
OUTPUT_DIR = generator.DEFAULT_OUTPUT_DIR.resolve()
STATIC_FILES = {
    "/": UI_DIR / "index.html",
    "/index.html": UI_DIR / "index.html",
    "/app.css": UI_DIR / "app.css",
    "/app.js": UI_DIR / "app.js",
}


def clean_string(value: Any, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")
    cleaned = value.strip()
    if len(cleaned) > max_length:
        raise ValueError(f"{field} is too long.")
    return cleaned


def clean_list(value: Any, field: str, max_items: int = 50) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError(f"{field} must be a short list.")
    return generator.dedupe(
        clean_string(item, field, 120) for item in value
    )


def validated_application(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("The request must contain an application object.")

    office = clean_string(payload.get("office", ""), "Office", 160)
    position = clean_string(payload.get("position", ""), "Position", 160)
    if not office or not position:
        raise ValueError("Office and position are required.")

    try:
        project_limit = int(payload.get("project_limit", 4))
        hobby_item_limit = int(payload.get("hobby_item_limit", 5))
    except (TypeError, ValueError) as exc:
        raise ValueError("Project and hobby limits must be numbers.") from exc

    if not 1 <= project_limit <= 12:
        raise ValueError("Choose between 1 and 12 projects.")
    if not 1 <= hobby_item_limit <= 12:
        raise ValueError("Choose between 1 and 12 hobby entries.")

    known_ids = set(generator.published_project_folders())
    include_projects = clean_list(payload.get("include_projects"), "Included projects")
    exclude_projects = clean_list(payload.get("exclude_projects"), "Excluded projects")
    overlap = set(include_projects) & set(exclude_projects)
    if overlap:
        raise ValueError(
            "A project cannot be both included and excluded: "
            + ", ".join(sorted(overlap))
        )
    unknown_ids = (set(include_projects) | set(exclude_projects)) - known_ids
    if unknown_ids:
        raise ValueError("Unknown project ID: " + ", ".join(sorted(unknown_ids)))

    include_hobbies = payload.get("include_hobbies", True)
    if not isinstance(include_hobbies, bool):
        raise ValueError("Include hobbies must be true or false.")

    return {
        "office": office,
        "position": position,
        "job_description": clean_string(
            payload.get("job_description", ""), "Job description", 100_000
        ),
        "software": clean_list(payload.get("software"), "Software"),
        "skills": clean_list(payload.get("skills"), "Skills"),
        "focus": clean_list(payload.get("focus"), "Focus"),
        "project_limit": project_limit,
        "include_projects": include_projects,
        "exclude_projects": exclude_projects,
        "include_hobbies": include_hobbies,
        "hobby_categories": clean_list(
            payload.get("hobby_categories"), "Hobby categories"
        ),
        "hobby_item_limit": hobby_item_limit,
    }


def project_preview(application: dict[str, Any]) -> dict[str, Any]:
    prepared, cv_data, _projects, ranked = generator.preview_application(application)
    limit = min(int(prepared["project_limit"]), len(ranked))
    inferred = prepared.get("inferred_from_job_text", {})
    hobby_categories = [
        item.get("name", "")
        for item in cv_data.get("hobbies", {}).get("categories", [])
        if item.get("name")
    ]
    return {
        "application": prepared,
        "inferred": inferred,
        "hobby_categories": hobby_categories,
        "projects": [
            {
                "id": item.project.project_id,
                "title": item.project.title,
                "year": item.project.year,
                "score": round(item.score, 2),
                "reasons": item.reasons,
                "software": item.project.software,
                "tags": item.project.tags,
                "selected": index < limit,
            }
            for index, item in enumerate(ranked)
        ],
    }


def relative_download(path_value: str) -> str:
    path = Path(path_value).resolve()
    try:
        relative = path.relative_to(OUTPUT_DIR)
    except ValueError as exc:
        raise ValueError("Generated file is outside the export directory.") from exc
    return "/download/" + "/".join(relative.parts)


class ApplicationHandler(BaseHTTPRequestHandler):
    server_version = "PortfolioApplicationGenerator/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {fmt % args}")

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'",
        )
        super().end_headers()

    def send_bytes(
        self,
        content: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        filename: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def send_error_json(self, message: str, status: HTTPStatus) -> None:
        self.send_json({"error": message}, status)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path in STATIC_FILES:
            file_path = STATIC_FILES[path]
            mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
            self.send_bytes(file_path.read_bytes(), mime)
            return
        if path.startswith("/download/"):
            self.serve_download(path.removeprefix("/download/"))
            return
        self.send_error_json("Not found.", HTTPStatus.NOT_FOUND)

    def serve_download(self, relative_value: str) -> None:
        relative_value = unquote(relative_value)
        candidate = (OUTPUT_DIR / relative_value).resolve()
        try:
            candidate.relative_to(OUTPUT_DIR)
        except ValueError:
            self.send_error_json("Unsafe download path.", HTTPStatus.BAD_REQUEST)
            return
        if not candidate.is_file() or candidate.suffix.lower() not in {".pdf", ".json"}:
            self.send_error_json("Generated file not found.", HTTPStatus.NOT_FOUND)
            return
        mime = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_bytes(candidate.read_bytes(), mime, filename=candidate.name)

    def read_json(self) -> Any:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            raise ValueError("Requests must use application/json.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length.") from exc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request is empty or too large.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/preview", "/api/generate"}:
            self.send_error_json("Not found.", HTTPStatus.NOT_FOUND)
            return
        try:
            application = validated_application(self.read_json())
            if path == "/api/preview":
                self.send_json(project_preview(application))
                return

            manifest = generator.generate_application(
                application,
                output_dir=OUTPUT_DIR,
                application_source="local application generator",
            )
            self.send_json({
                "message": "Application package generated.",
                "downloads": {
                    "portfolio": relative_download(manifest["outputs"]["portfolio"]),
                    "portfolio_html": relative_download(manifest["outputs"]["portfolio_html"]),
                    "cv": relative_download(manifest["outputs"]["cv"]),
                    "selection": relative_download(manifest["outputs"]["selection"]),
                    "application": relative_download(manifest["outputs"]["application"]),
                },
                "output_directory": str(
                    Path(manifest["outputs"]["portfolio"]).parent
                ),
                "selection": manifest["selection"],
            })
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            print(f"Generation failed: {exc}", file=sys.stderr)
            self.send_error_json(
                "Generation failed. Check the terminal for details.",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the private application generator.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1024 <= args.port <= 65535:
        print("Choose a port between 1024 and 65535.", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((HOST, args.port), ApplicationHandler)
    url = f"http://{HOST}:{args.port}/"
    print(f"Private application generator: {url}")
    print("Press Control-C to stop it.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping application generator.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
