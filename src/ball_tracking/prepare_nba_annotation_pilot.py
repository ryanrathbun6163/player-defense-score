"""Extract approved native-PTS NBA frames and initialize prediction-free drafts.

The original source is decoded only around each approved interval. PNG pixels
are checked against SHA-256 records emitted from the same decoded RGB stream;
timestamps are compared with the previously audited original frame inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from src.ball_tracking import nba_annotations


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_new(path: Path, data: dict) -> None:
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write('\n')


def bound_path(root: Path, binding: dict) -> Path:
    path = (root / binding['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Binding outside repository or missing: {binding['path']}")
    if sha256(path) != binding['sha256']:
        raise ValueError(f"Binding changed: {binding['path']}")
    return path


def source_stat(path: Path) -> dict:
    stat = path.stat()
    return {'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def parse_framehash(path: Path) -> list[dict]:
    """Read FFmpeg's actual raw-RGB producer output, including its time base."""
    lines = path.read_text(encoding='utf-8').splitlines()
    if '#tb 0: 1/90000' not in lines or '#hash: SHA256' not in lines:
        raise ValueError('Expected native 90 kHz SHA256 framehash output')
    rows = []
    for line in lines:
        if not line.strip() or line.startswith('#'):
            continue
        fields = [part.strip() for part in line.split(',')]
        if len(fields) != 6 or fields[0] != '0':
            raise ValueError(f'Unexpected framehash row: {line}')
        rows.append({'pts': int(fields[2]), 'bytes': int(fields[4]), 'rgb_sha256': fields[5]})
    return rows


def extraction_command(ffmpeg: str, source: Path, directory: Path,
                       first_frame: int, first_pts: int, end_pts: int) -> list[str]:
    # No resizing, fps conversion, dropped frames or lossy intermediate.
    seek_seconds = max(0, first_pts / 90000 - 3)
    input_seconds = end_pts / 90000 - seek_seconds + 1
    return [ffmpeg, '-hide_banner', '-nostdin', '-loglevel', 'warning', '-xerror',
            '-n', '-ss', f'{seek_seconds:.9f}', '-t', f'{input_seconds:.9f}', '-copyts',
            '-noautorotate', '-hwaccel', 'none', '-threads', '4', '-i', str(source), '-filter_complex_threads', '1',
            '-filter_complex',
            f'[0:v:0]trim=start_pts={first_pts}:end_pts={end_pts},format=rgb24,split=2[png][hash]',
            '-map', '[png]', '-an', '-c:v', 'png', '-threads', '2',
            '-compression_level', '3', '-pix_fmt', 'rgb24', '-fps_mode', 'passthrough',
            '-enc_time_base', '1:90000', '-start_number', str(first_frame),
            str(directory / 'frames' / 'source_%06d.png'),
            '-map', '[hash]', '-an', '-c:v', 'rawvideo', '-threads', '1',
            '-pix_fmt', 'rgb24', '-fps_mode', 'passthrough', '-enc_time_base', '1:90000',
            '-f', 'framehash', '-hash', 'sha256', str(directory / 'source_rgb_framehash.txt')]


def prepare_pilot(root: Path, approval_path: Path, pilot: dict,
                  output_root: Path, ffmpeg: str) -> dict:
    candidate_id = pilot['candidate_id']
    if not isinstance(candidate_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', candidate_id):
        raise ValueError('Candidate ID must be a contained lowercase identifier')
    directory = (output_root / candidate_id).resolve()
    if not directory.is_relative_to(output_root.resolve()):
        raise ValueError('Candidate output escapes requested output root')
    completed = directory / 'preparation_receipt.json'
    if completed.exists():
        receipt = json.loads(completed.read_text())
        if receipt.get('status') != 'complete_unlabeled' or receipt.get('candidate_id') != candidate_id:
            raise ValueError('Existing preparation receipt is not a completed candidate')
        existing_path = (root / receipt['annotation_path']).resolve()
        if not existing_path.is_relative_to(directory):
            raise ValueError('Existing annotation path escapes candidate output')
        draft = nba_annotations.load_annotations(existing_path,
                                                  repo_root=root, verify_images=True)
        if (draft['annotation_set_id'] != pilot['annotation_set_id'] or
                draft['approval'] != {'path': approval_path.relative_to(root).as_posix(),
                                      'sha256': sha256(approval_path)}):
            raise ValueError('Existing output belongs to another pilot')
        if any(draft[field] != pilot[field] for field in ('candidate_id', 'game_id', 'source_video', 'approved_role')):
            raise ValueError('Existing source or allocation differs from requested pilot')
        if [draft['frames'][0]['source_frame_index'], draft['frames'][-1]['source_frame_index']] != pilot['source_frame_range_inclusive']:
            raise ValueError('Existing source range differs from requested pilot')
        return {'candidate_id': pilot['candidate_id'], 'status': 'existing_verified',
                'annotation_path': receipt['annotation_path']}
    if directory.exists():
        raise FileExistsError(f'Partial attempt preserved at {directory}; use a new output root')

    source = (root / pilot['source_video']['path']).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError('Source path missing or outside repository')
    verification = pilot['source_verification']
    audit = json.loads(bound_path(root, verification['audit']).read_text())
    before = source_stat(source)
    if (audit[verification['hash_field']] != pilot['source_video']['sha256'] or
            audit[verification['stat_field']] != verification['source_stat'] or
            before != verification['source_stat']):
        raise ValueError('Completed source audit or current source stat no longer agrees')
    frame_map_path = bound_path(root, pilot['frame_map'])
    frame_map = [json.loads(line) for line in frame_map_path.read_text().splitlines()]
    first, last = pilot['source_frame_range_inclusive']
    rows = [row for row in frame_map if first <= row['source_frame_index'] <= last]
    next_rows = [row for row in frame_map if row['source_frame_index'] == last + 1]
    if ([row['source_frame_index'] for row in rows] != list(range(first, last + 1)) or
            len(next_rows) != 1 or
            [rows[0]['source_pts_ticks'], rows[-1]['source_pts_ticks']] != pilot['source_pts_ticks_inclusive'] or
            any(row['time_base'] != '1/90000' for row in rows + next_rows)):
        raise ValueError('Approved pilot and original source frame map differ')

    directory.mkdir(parents=True)
    (directory / 'frames').mkdir()
    started = time.monotonic()
    command = extraction_command(ffmpeg, source, directory, first,
                                 rows[0]['source_pts_ticks'], next_rows[0]['source_pts_ticks'])
    start_record = {'status': 'started', 'started_at_utc': utc_now(),
                    'candidate_id': pilot['candidate_id'], 'command': command,
                    'source_stat_before': before, 'source_hash_recomputed': False,
                    'source_hash_reuse': verification,
                    'approval_sha256': sha256(approval_path),
                    'code_sha256': sha256(Path(__file__)), 'expected_frames': len(rows)}
    write_new(directory / 'preparation_started.json', start_record)
    try:
        with (directory / 'ffmpeg.stdout.txt').open('xb') as stdout, (directory / 'ffmpeg.stderr.txt').open('xb') as stderr:
            result = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
        if result.returncode != 0:
            raise RuntimeError(f'FFmpeg failed with exit {result.returncode}; retained stderr')
        hashes = parse_framehash(directory / 'source_rgb_framehash.txt')
        if [row['pts'] for row in hashes] != [row['source_pts_ticks'] for row in rows]:
            raise ValueError('Decoded source PTS differ from approved original frame inventory')
        images = sorted((directory / 'frames').glob('*.png'))
        if len(images) != len(rows):
            raise ValueError('PNG count differs from approved frame count')
        frames = []
        width, height = pilot['source_video']['width_px'], pilot['source_video']['height_px']
        for row, rgb_record in zip(rows, hashes):
            image_path = directory / 'frames' / f"source_{row['source_frame_index']:06d}.png"
            with Image.open(image_path) as image:
                if image.size != (width, height) or image.mode != 'RGB':
                    raise ValueError('PNG shape or color mode differs from original RGB decode')
                rgb_sha = hashlib.sha256(image.tobytes()).hexdigest()
            if rgb_sha != rgb_record['rgb_sha256'] or rgb_record['bytes'] != width * height * 3:
                raise ValueError('PNG pixels differ from direct original decoded RGB pixels')
            frames.append({'source_frame_index': row['source_frame_index'],
                           'source_pts_ticks': row['source_pts_ticks'],
                           'png': {'path': image_path.relative_to(root).as_posix(),
                                   'sha256': sha256(image_path), 'rgb_sha256': rgb_sha}})
        if source_stat(source) != before:
            raise ValueError('Source changed during extraction')
        now = utc_now()
        draft = {'schema_version': 'nba_ball_annotations/v0.1',
                 'annotation_set_id': pilot['annotation_set_id'], 'game_id': pilot['game_id'],
                 'candidate_id': pilot['candidate_id'], 'approved_role': pilot['approved_role'],
                 'approval': {'path': approval_path.relative_to(root).as_posix(), 'sha256': sha256(approval_path)},
                 'source_video': pilot['source_video'], 'time_base': '1/90000',
                 'coordinate_system': {'pixel_origin': 'top_left', 'x_axis_direction': 'right',
                                       'y_axis_direction': 'down', 'center_definition': 'complete_ball_center'},
                 'frames': frames, 'annotations': [
                     {'frame_index': row['source_frame_index'], 'annotation_status': 'unlabeled',
                      'visibility': None, 'absence_reason': None, 'game_ball_identity_certainty': None,
                      'geometry': None, 'localization_eligible': False, 'difficulty_tags': [], 'notes': None}
                     for row in rows], 'revision': 0, 'created_at_utc': now, 'updated_at_utc': now,
                 'review': {'status': 'draft', 'annotator_id': None, 'reviewer_id': None, 'reviewed_at_utc': None}}
        annotation_path = directory / 'annotations.json'
        asset_check = nba_annotations.verify_annotation_assets(draft, root)
        nba_annotations.initialize_annotations(annotation_path, draft)
        receipt = {'status': 'complete_unlabeled', 'candidate_id': pilot['candidate_id'],
                   'annotation_path': annotation_path.relative_to(root).as_posix(),
                   'initial_annotation_sha256': sha256(annotation_path), 'frame_count': len(rows),
                   'png_bytes': sum(path.stat().st_size for path in images),
                   'decoded_pts_match_original_map': True, 'png_rgb_matches_direct_decode': True,
                   'asset_check': asset_check, 'source_stat_after': source_stat(source),
                   'ffmpeg_stderr_bytes': (directory / 'ffmpeg.stderr.txt').stat().st_size,
                   'elapsed_seconds': round(time.monotonic() - started, 3),
                   'completed_at_utc': utc_now(), 'human_labels_created': 0,
                   'model_calls': 0, 'human_label_review': 'pending'}
        write_new(completed, receipt)
        return receipt
    except Exception as exc:
        write_new(directory / 'preparation_failed.json',
                  {'status': 'failed_preserved', 'failed_at_utc': utc_now(),
                   'elapsed_seconds': round(time.monotonic() - started, 3),
                   'error_type': type(exc).__name__, 'error': str(exc)})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approval', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--repository-root', default=Path.cwd(), type=Path)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = parser.parse_args()
    root = args.repository_root.resolve()
    approval_path = (root / args.approval).resolve()
    output_root = (root / args.output_root).resolve()
    if not approval_path.is_relative_to(root) or not output_root.is_relative_to(root / 'data/outputs'):
        raise ValueError('Approval must be inside repository; generated output must be under data/outputs')
    if not args.ffmpeg:
        parser.error('FFmpeg not found; pass --ffmpeg with the installed executable path')
    approval = json.loads(approval_path.read_text(encoding='utf-8-sig'))
    if approval['schema_version'] != 'nba_development_selection_approval/v0.1' or approval['status'] != 'approved':
        raise ValueError('Expected approved NBA pilot record')
    bound_path(root, approval['proposal'])
    for pilot in approval['annotation_pilots']:
        receipt = prepare_pilot(root, approval_path, pilot, output_root, args.ffmpeg)
        print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
