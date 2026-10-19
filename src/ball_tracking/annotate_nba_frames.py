"""Prediction-free local browser editor for timestamp-bound NBA annotation drafts.

The server exposes only configured drafts and their verified PNGs. Schema code
owns validation, revision conflicts, atomic replacement and prior snapshots;
this module never changes source metadata or records human review acceptance.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from src.ball_tracking import nba_annotations as schema
from src.ball_tracking.annotations import (
    ABSENCE_REASONS,
    ANNOTATION_STATUSES,
    DIFFICULTY_TAGS,
    IDENTITY_CERTAINTIES,
    VISIBILITY_STATES,
)

MAX_REQUEST_BYTES = 64 * 1024
HTML_PATH = Path(__file__).with_name("nba_annotation_editor.html")
EDITABLE_DOCUMENT_FIELDS = {"annotations", "revision", "updated_at_utc", "review"}


def _provenance(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items()
            if key not in EDITABLE_DOCUMENT_FIELDS}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number: {value}")


class NBAAnnotationServer(ThreadingHTTPServer):
    """Loopback-only server; callers own shutdown and server_close."""

    daemon_threads = True

    def __init__(
        self,
        annotation_paths: Sequence[Path],
        repository_root: Path,
        *,
        port: int = 0,
    ) -> None:
        self.repository_root = repository_root.resolve()
        self.annotation_paths = tuple(Path(p).resolve() for p in annotation_paths)
        if not self.annotation_paths or len(set(self.annotation_paths)) != len(
            self.annotation_paths
        ):
            raise ValueError("Supply one or more distinct annotation draft paths")
        self.token = secrets.token_urlsafe(32)
        self.editor_lock = threading.RLock()
        self.provenance = []
        # Verify every bound asset once before making the editor available.
        for path in self.annotation_paths:
            document, _ = schema.load_annotation_snapshot(
                path, repo_root=self.repository_root, verify_images=True
            )
            self.provenance.append(_provenance(document))
        super().__init__(("127.0.0.1", port), NBAAnnotationHandler)
        self.origin = f"http://127.0.0.1:{self.server_address[1]}"
        self.editor_url = f"{self.origin}/#token={self.token}"

    def snapshot(self, pilot: int) -> tuple[dict[str, Any], str]:
        if not 0 <= pilot < len(self.annotation_paths):
            raise LookupError("Unknown pilot")
        document, digest = schema.load_annotation_snapshot(self.annotation_paths[pilot])
        if _provenance(document) != self.provenance[pilot]:
            raise schema.AnnotationConflictError(
                "Source contract changed after editor startup. Nothing was served "
                "or saved; restart only after verifying the changed provenance."
            )
        return document, digest

    def frame_asset(self, document: dict[str, Any], frame_index: int) -> dict:
        matches = [
            row for row in document["frames"]
            if row["source_frame_index"] == frame_index
        ]
        if len(matches) != 1:
            raise LookupError("Frame is outside this pilot")
        return matches[0]


class NBAAnnotationHandler(BaseHTTPRequestHandler):
    server: NBAAnnotationServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        # Do not log tokens or personal annotation content.
        return

    def _reply(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' blob:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status: int, payload: Any) -> None:
        self._reply(
            status,
            json.dumps(payload, allow_nan=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _guard(self, *, api: bool, write: bool = False) -> bool:
        authority = self.server.origin.removeprefix("http://")
        if self.headers.get("Host") != authority:
            self._json(403, {"error": "Use the displayed loopback editor address"})
            return False
        origin = self.headers.get("Origin")
        if (write and origin != self.server.origin) or (
            origin is not None and origin != self.server.origin
        ):
            self._json(403, {"error": "Request origin is not this editor"})
            return False
        if api and not secrets.compare_digest(
            self.headers.get("X-NBA-Session-Token", "").encode("utf-8"),
            self.server.token.encode("ascii"),
        ):
            self._json(403, {"error": "Missing or invalid local session token"})
            return False
        return True

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if not self._guard(api=path != "/"):
            return
        try:
            if path == "/":
                self._reply(200, HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/session":
                pilots = []
                with self.server.editor_lock:
                    for index in range(len(self.server.annotation_paths)):
                        doc, _ = self.server.snapshot(index)
                        pilots.append({
                            "id": index,
                            "annotation_set_id": doc["annotation_set_id"],
                            "game_id": doc["game_id"],
                            "candidate_id": doc["candidate_id"],
                            "frame_count": len(doc["frames"]),
                        })
                self._json(200, {
                    "pilots": pilots,
                    "choices": {
                        "annotation_status": sorted(ANNOTATION_STATUSES),
                        "visibility": sorted(VISIBILITY_STATES),
                        "absence_reason": sorted(ABSENCE_REASONS),
                        "identity": sorted(IDENTITY_CERTAINTIES),
                        "difficulty_tags": sorted(DIFFICULTY_TAGS),
                    },
                })
            elif match := re.fullmatch(r"/api/pilots/(\d+)", path):
                with self.server.editor_lock:
                    doc, digest = self.server.snapshot(int(match[1]))
                self._json(200, {"document": doc, "sha256": digest})
            elif match := re.fullmatch(r"/api/pilots/(\d+)/images/(\d+)", path):
                with self.server.editor_lock:
                    doc, _ = self.server.snapshot(int(match[1]))
                    schema.verify_annotation_assets(
                        doc, self.server.repository_root, verify_images=False
                    )
                    frame = self.server.frame_asset(doc, int(match[2]))
                    png = schema.read_verified_png(
                        frame, doc["source_video"], self.server.repository_root
                    )
                self._reply(200, png, "image/png")
            else:
                self._json(404, {"error": "Unknown editor route"})
        except LookupError as error:
            self._json(404, {"error": str(error)})
        except (ValueError, OSError) as error:
            self._json(422, {"error": str(error)})

    def do_POST(self) -> None:
        # Close rejected requests so an unread request body cannot become a
        # second request on the same persistent connection.
        self.close_connection = True
        if not self._guard(api=True, write=True):
            return
        match = re.fullmatch(r"/api/pilots/(\d+)/save", urlsplit(self.path).path)
        if match is None:
            self._json(404, {"error": "Unknown editor route"})
            return
        try:
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Save requires application/json")
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Chunked save requests are not supported")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_REQUEST_BYTES:
                raise ValueError("Save body is empty or exceeds 64 KiB")
            raw = self.rfile.read(length)
            payload = json.loads(
                raw, object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
            fields = {
                "expected_revision", "expected_sha256", "annotator_id",
                "frame_annotation",
            }
            if not isinstance(payload, dict) or set(payload) != fields:
                raise ValueError("Save has missing or unknown fields")
            row = payload["frame_annotation"]
            if not isinstance(row, dict):
                raise ValueError("frame_annotation must be an object")
            index = row.get("frame_index")
            if isinstance(index, bool) or not isinstance(index, int):
                raise ValueError("frame_index must be an integer source frame")
            pilot = int(match[1])
            with self.server.editor_lock:
                doc, digest = self.server.snapshot(pilot)
                if (
                    payload["expected_revision"] != doc["revision"]
                    or isinstance(payload["expected_revision"], bool)
                    or not isinstance(payload["expected_revision"], int)
                    or payload["expected_sha256"] != digest
                ):
                    raise schema.AnnotationConflictError(
                        "Draft changed since this frame loaded. Nothing was saved; "
                        "keep your edits or explicitly reload the saved draft."
                    )
                frame = self.server.frame_asset(doc, index)
                schema.verify_annotation_assets(
                    doc, self.server.repository_root, verify_images=False
                )
                schema.read_verified_png(
                    frame, doc["source_video"], self.server.repository_root
                )
                annotations = copy.deepcopy(doc["annotations"])
                selected = [i for i, old in enumerate(annotations)
                            if old["frame_index"] == index]
                if len(selected) != 1:
                    raise ValueError("Frame is not exactly once in this draft")
                annotations[selected[0]] = row
                schema.save_annotations(
                    self.server.annotation_paths[pilot], annotations,
                    expected_revision=payload["expected_revision"],
                    expected_sha256=payload["expected_sha256"],
                    annotator_id=payload["annotator_id"],
                )
                updated, new_digest = self.server.snapshot(pilot)
            self._json(200, {"document": updated, "sha256": new_digest})
        except schema.AnnotationConflictError as error:
            self._json(409, {"error": str(error)})
        except LookupError as error:
            self._json(404, {"error": str(error)})
        except (ValueError, OSError) as error:
            self._json(422, {"error": str(error)})


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, nargs="+", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=0,
                        help="Local port; 0 selects an available port")
    args = parser.parse_args(argv)
    server = NBAAnnotationServer(
        args.annotations, args.repository_root, port=args.port
    )
    print(json.dumps({"url": server.editor_url, "pilots": len(args.annotations),
                      "status": "ready", "prediction_free": True}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
