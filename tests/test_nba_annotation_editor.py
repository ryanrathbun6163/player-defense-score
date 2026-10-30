"""Exercise actual local HTTP transport against producer-bound synthetic assets."""

from __future__ import annotations

import copy
import hashlib
import http.client
import json
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from src.ball_tracking import nba_annotations as schema
from src.ball_tracking.annotate_nba_frames import HTML_PATH, NBAAnnotationServer
from tests.test_nba_annotations import build_fixture, observed


class NBAAnnotationHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="nba_editor_http_")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path, self.initial = build_fixture(self.root)
        self.original_bytes = self.path.read_bytes()
        self.server = NBAAnnotationServer([self.path], self.root, port=0)
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01),
            daemon=True,
        )
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, route, payload=None, *, headers=None, token=True,
                origin=True):
        supplied = {}
        if token:
            supplied["X-NBA-Session-Token"] = self.server.token
        if origin:
            supplied["Origin"] = self.server.origin
        raw = payload
        if payload is not None:
            supplied["Content-Type"] = "application/json"
            if not isinstance(payload, bytes):
                raw = json.dumps(payload).encode("utf-8")
        supplied.update(headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_address[1], timeout=5
        )
        try:
            connection.request(method, route, body=raw, headers=supplied)
            response = connection.getresponse()
            body = response.read()
            result = (json.loads(body) if response.getheader("Content-Type", "")
                      .startswith("application/json") else body)
            return response.status, result, dict(response.getheaders())
        finally:
            connection.close()

    def snapshot(self):
        status, payload, _ = self.request("GET", "/api/pilots/0")
        self.assertEqual(status, 200, payload)
        return payload

    def save_payload(self, *, snapshot=None, row=None):
        loaded = snapshot or self.snapshot()
        return {
            "expected_revision": loaded["document"]["revision"],
            "expected_sha256": loaded["sha256"],
            "annotator_id": "Synthetic test annotator",
            "frame_annotation": row or observed(660),
        }

    def test_real_http_emission_image_and_atomic_save_roundtrip(self):
        status, session, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200)
        self.assertEqual(session["pilots"][0]["frame_count"], 3)
        loaded = self.snapshot()
        self.assertEqual(loaded["document"], self.initial)
        self.assertIsNone(loaded["document"]["review"]["annotator_id"])
        self.assertEqual(loaded["sha256"], hashlib.sha256(self.original_bytes).hexdigest())
        self.assertEqual(
            [f["source_pts_ticks"] for f in loaded["document"]["frames"]],
            [996362, 997802, 999332],
        )
        status, png, headers = self.request("GET", "/api/pilots/0/images/660")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(png, (self.root / self.initial["frames"][0]["png"]["path"]).read_bytes())
        self.assertEqual(hashlib.sha256(png).hexdigest(), self.initial["frames"][0]["png"]["sha256"])
        row = observed(660)
        row["geometry"]["center_xy_px"] = [5.25, 2.125]
        status, result, _ = self.request(
            "POST", "/api/pilots/0/save", self.save_payload(snapshot=loaded, row=row)
        )
        self.assertEqual(status, 200, result)
        saved = schema.load_annotations(self.path)
        self.assertEqual(saved, result["document"])
        self.assertEqual(saved["annotations"][0], row)
        self.assertEqual(saved["annotations"][1:], self.initial["annotations"][1:])
        self.assertEqual(saved["frames"], self.initial["frames"])
        self.assertEqual(saved["revision"], 1)
        self.assertEqual(saved["review"]["status"], "draft")
        self.assertIsNone(saved["review"]["reviewer_id"])
        self.assertIsNone(saved["review"]["reviewed_at_utc"])
        prior = list(self.path.with_name("draft.history").glob("*.json"))
        self.assertEqual(len(prior), 1)
        self.assertEqual(prior[0].read_bytes(), self.original_bytes)

    def test_stale_client_cannot_replace_new_saved_row(self):
        payload = self.save_payload()
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 200)
        after = self.path.read_bytes()
        payload["frame_annotation"]["geometry"]["center_xy_px"] = [1.0, 1.0]
        status, result, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 409, result)
        self.assertEqual(self.path.read_bytes(), after)

    def test_externally_modified_bytes_conflict_even_with_same_revision(self):
        payload = self.save_payload()
        changed = self.original_bytes + b"\n"
        self.path.write_bytes(changed)
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 409)
        self.assertEqual(self.path.read_bytes(), changed)

    def test_invalid_semantics_and_outside_frame_leave_draft_unchanged(self):
        row = observed(660)
        row.update(visibility="not_visible", absence_reason="occluded")
        status, _, _ = self.request("POST", "/api/pilots/0/save", self.save_payload(row=row))
        self.assertEqual(status, 422)
        row = observed(999)
        status, _, _ = self.request("POST", "/api/pilots/0/save", self.save_payload(row=row))
        self.assertEqual(status, 404)
        self.assertEqual(self.path.read_bytes(), self.original_bytes)
        self.assertFalse(self.path.with_name("draft.history").exists())

    def test_unknown_does_not_become_absence_and_exclusion_requires_reason(self):
        row = copy.deepcopy(self.initial["annotations"][0])
        row.update(annotation_status="labeled", visibility="indeterminate",
                   game_ball_identity_certainty="ambiguous", notes="Cannot distinguish candidate objects.")
        status, result, _ = self.request("POST", "/api/pilots/0/save", self.save_payload(row=row))
        self.assertEqual(status, 200, result)
        saved = result["document"]["annotations"][0]
        self.assertIsNone(saved["absence_reason"])
        self.assertIsNone(saved["geometry"])
        self.assertFalse(saved["localization_eligible"])
        excluded = copy.deepcopy(self.initial["annotations"][1])
        excluded["annotation_status"] = "excluded"
        status, _, _ = self.request("POST", "/api/pilots/0/save", self.save_payload(row=excluded))
        self.assertEqual(status, 422)
        excluded["notes"] = "Synthetic protocol exclusion for this test only."
        status, result, _ = self.request("POST", "/api/pilots/0/save", self.save_payload(row=excluded))
        self.assertEqual(status, 200, result)
        self.assertEqual(result["document"]["annotations"][1]["annotation_status"], "excluded")
        self.assertIsNone(result["document"]["review"]["reviewed_at_utc"])

    def test_changed_png_is_rejected_on_display_and_save(self):
        payload = self.save_payload()
        image = self.root / self.initial["frames"][0]["png"]["path"]
        image.write_bytes(image.read_bytes() + b"changed")
        status, _, _ = self.request("GET", "/api/pilots/0/images/660")
        self.assertEqual(status, 422)
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 422)
        self.assertEqual(self.path.read_bytes(), self.original_bytes)

    def test_session_png_allowlist_cannot_be_replaced_by_external_draft_edit(self):
        payload = self.save_payload()
        changed = copy.deepcopy(self.initial)
        original_png = self.root / changed["frames"][0]["png"]["path"]
        replacement = self.root / "another.png"
        replacement.write_bytes(original_png.read_bytes())
        changed["frames"][0]["png"]["path"] = "another.png"
        self.path.write_text(json.dumps(changed), encoding="utf-8")
        current = self.path.read_bytes()
        status, result, _ = self.request("GET", "/api/pilots/0/images/660")
        self.assertEqual(status, 422)
        self.assertIn("Source contract changed", result["error"])
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 409)
        self.assertEqual(self.path.read_bytes(), current)

    def test_changed_parent_source_is_rejected_without_reading_full_video(self):
        payload = self.save_payload()
        source = self.root / self.initial["source_video"]["path"]
        source.write_bytes(b"changed source bytes")
        status, result, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 422)
        self.assertIn("source stat changed", result["error"])
        self.assertEqual(self.path.read_bytes(), self.original_bytes)

    def test_origin_token_host_and_route_protections(self):
        payload = self.save_payload()
        for overrides in [
            {"token": False}, {"origin": False},
            {"headers": {"Origin": "https://example.invalid"}},
            {"headers": {"X-NBA-Session-Token": "wrong"}},
            {"headers": {"Host": "attacker.invalid"}},
        ]:
            with self.subTest(overrides=overrides):
                status, _, _ = self.request("POST", "/api/pilots/0/save", payload, **overrides)
                self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/api/session", token=False)
        self.assertEqual(status, 403)
        for route in ["/source.mp4", "/api/pilots/0/images/../source.mp4",
                      "/api/pilots/0/images/999", "/api/pilots/50"]:
            status, _, _ = self.request("GET", route)
            self.assertEqual(status, 404)
        self.assertEqual(self.path.read_bytes(), self.original_bytes)

    def test_save_rejects_metadata_injection_duplicate_keys_and_large_body(self):
        payload = self.save_payload()
        payload["review"] = {"status": "reviewed"}
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 422)
        for raw in [b'{"expected_revision":0,"expected_revision":1}', b" " * 65537]:
            status, _, _ = self.request("POST", "/api/pilots/0/save", raw)
            self.assertEqual(status, 422)
        self.assertEqual(self.path.read_bytes(), self.original_bytes)

    def test_recorded_annotator_cannot_silently_change(self):
        status, _, _ = self.request("POST", "/api/pilots/0/save", self.save_payload())
        self.assertEqual(status, 200)
        after = self.path.read_bytes()
        payload = self.save_payload(row=observed(661))
        payload["annotator_id"] = "A different person"
        status, _, _ = self.request("POST", "/api/pilots/0/save", payload)
        self.assertEqual(status, 409)
        self.assertEqual(self.path.read_bytes(), after)


class BrowserMappingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is needed to execute actual browser mapping JS")
    def test_actual_javascript_syntax_and_zoom_scroll_mapping(self):
        html = HTML_PATH.read_text(encoding="utf-8")
        script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
        mapping = re.search(r"function mapImagePoint\(.*?\n\}", script, re.S).group(0)
        code = (
            'const assert=require("node:assert/strict");\n'
            + "new Function(" + json.dumps(script) + ");\n"
            + mapping
            + "\nassert.deepEqual(mapImagePoint(1420,980,{left:-500,top:-100,width:3840,height:2160},1920,1080),[960,540]);"
            + "\nassert.deepEqual(mapImagePoint(74,62,{left:10,top:14,width:128,height:96},16,12),[8,6]);"
            + "\nfor(const p of [[9,14],[138,15],[11,110]])assert.throws(()=>mapImagePoint(p[0],p[1],{left:10,top:14,width:128,height:96},16,12));"
        )
        result = subprocess.run([shutil.which("node"), "-e", code], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
