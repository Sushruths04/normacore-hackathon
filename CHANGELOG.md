# Changelog (newest first)

## [Unreleased]
### Added
- 2026-11-21 18:05 - `tools/teach_wizard.py`: guided camera<->arm calibration in the terminal. Picks the camera that sees most markers, checks the follower is calibrated, turns torque OFF after confirmation (only command it sends), then per marker (0-3 corners, 6 DROP, movable 7 for extra spots): camera reads the marker centre, you hold HOVER and GRASP poses, Enter records joint angles once the arm is still. Keys Enter/r/s/q, `--resume`. Output `calibration/teach_points.json`. Tested with a fake robot + synthetic marker image, NOT yet on hardware - Bart + Claude
- 2026-11-21 17:30 - `calibration/markers.json`: team marker sheet (DICT_4X4_50, 40 mm): IDs 0-3 corners FL/FR/BR/BL, 4/5/6 zones A/B/C, 7 bowl; **zone C (ID 6) = DROP**; corner table positions still to measure. `markers.py`: names from the file, `find_role(markers, 'drop'|'A')` - Bart + Claude
- 2026-11-21 17:20 - `src/normakit/markers.py`: ArUco/AprilTag detection with dictionary auto-detect, roles from `calibration/markers.json` (corners -> pixel->table homography, DROP, zones), `px_to_table`; `detect_live.py --markers` overlay + JSONL. Tested on synthetic DICT_4X4_50 and AprilTag 36h11 images - Bart + Claude
- 2026-11-21 17:15 - Prompt test on a tape-measure photo (`snapshots/tape_measure.png`): `measuring tape` alone 0.43, with `bottle` 0.11; `black device` + `bottle` 0.59. Lesson noted in `detect.py`: extra classes/synonyms lower scores, appearance phrases beat names - Claude
- 2026-11-21 17:05 - `detect.py`: whitelist with synonyms (`label=phrase1|phrase2`, deduped per label), `DEMO_OBJECTS` (duplo, can, bottle), `phrase` field; `detect_live.py --demo`. Note: a whitelist forces look-alikes into a class (sample photo with no can -> `can` 0.41), so keep `--conf` >= ~0.3 and check on the real scene - Bart + Claude
- 2026-11-21 16:50 - `src/normakit/detect.py`: YOLO detector, JPEG/ndarray -> JSON (`label, conf, box, center_px, bottom_px, area_frac`); COCO YOLO11n (`cup`, `bottle`) or open-vocabulary YOLO-World text prompts (`red bull can`); `find(img, label)` returns a readable error. Benchmarked on M3 Pro MPS @640x480: 17 ms (COCO), 24 ms (World) - Bart + Claude
- 2026-11-21 16:50 - `tools/detect_live.py`: live detection from Mac webcam / image files / Station camera (`--source station`), window with boxes, JSONL log in `logs/detections-*.jsonl`. Read-only, never moves the arm - Bart + Claude
- 2026-11-21 16:50 - Dependency `ultralytics` 8.4.216 (+ torch 2.9.0) in `.venv` (`python3 -m venv --system-site-packages .venv && .venv/bin/pip install ultralytics`) - why: YOLO detection on Apple MPS. On first YOLO-World run ultralytics auto-installs `clip` + `ftfy` and downloads CLIP ViT-B/32 (338 MB) to `~/.cache/clip`. Weights in `models/` (gitignored) - Claude
- 2026-11-21 16:35 - `docs/NEXT_STEPS.md`: handoff header (state, follower-only project, joint-check + camera steps with exact commands) - Bart + Claude
- 2026-11-21 15:58 - `tools/calibrate.py`: watch (read-only live spans vs reference) / reset / save (freeze) / auto / stop over TCP, no web UI needed - Claude [ISSUE-109]
- 2026-11-21 15:40 - Merged Bart's macOS work onto this repo: `tools/` (verify_station, estop, reset_calibration, speed_limit), `start_station.sh`, `restart_station.sh`, `patches/teleop-max-speed.patch`, `docs/CONCEPTS.md`; ISSUE-001..015 appended to `docs/ISSUES.md`; macOS section in `docs/SETUP.md`; tools now find upstream at `vendor/norma-core-src`; `.gitignore` += `repo/`, `snapshots/` - Bart + Claude
- 2026-11-21 - `scripts/twin_view.py`: renders both real arms from live joint data (`run/twin.png`), using the Station viewer's mapping
- 2026-11-21 - `scripts/identify_arm.py`, `set_home.py`, `dump_buses.py`, `monitor_calib.py`, `backup_calibration.py`, `mirror_state.py`; `./norma` shortcuts
- 2026-11-21 - `src/normakit/busread.py` read-only bus snapshot; `StationBackend` reads follower bus from `run/buses.json`
- 2026-11-21 - MCP server `elrobot-real` entry in `.mcp.json` (station backend, untested for motion)
- 2026-11-21 - `calibration/`: per-bus calibration files (min, max, midpoint, span, frozen)
### Fixed
- 2026-11-21 17:05 - `detect.annotate` drew into the caller's frame (saved frames had boxes baked in); labels hidden when a box touched the top edge. Now copies, colours per class, label inside the box at the edge; live view lists all detections at the bottom; `s` saves the raw frame - Claude
- 2026-11-21 15:50 - `tools/calibrate.py watch`: subscribe once (it re-subscribed every refresh and crashed with TimeoutError after a few minutes); shows `pos` and `<<< MOVING` on the joint being moved - Claude
- 2026-11-21 15:45 - `tools/verify_station.py`: saved motors use raw Present Position (offset was counted twice -> false `OUTSIDE`, wrong `--move-test` start) - Claude [ISSUE-110]
- 2026-11-21 - `StationBackend`: wrapped ranges (max < min) and positions just outside the range no longer break normalisation
- 2026-11-21 - `monitor_calib.py`: no longer crashes on short motor reads
### Hardware
- 2026-11-21 16:25 - Leader manual calibration abandoned (accidental web-UI reset 16:10:56, m4 not re-swept); leader left NOT SAVED. Team decision: follower only - Bart [ISSUE-112]
- 2026-11-21 15:52 - Leader `5B79016336` web-UI auto-calibrated on Bart's Mac: all 8 saved, but m3/m4/m5 spans short (1526/996/436) - backup `calibration/5B79016336_leader_*` is NOT usable for mirroring - Bart + Claude [ISSUE-111]
- 2026-11-21 15:40 - Follower `5B8E114691` reset + auto-calibrated on Bart's Mac (`tools/calibrate.py`, 32 steps, 156 s, all 8 saved; spans m1 1972, m2 2012, m3 2322, m4 2326, m5 3836, m6 2050, m7 3874, m8 1610; torque off afterwards). Backup `calibration/5B8E114691_follower_20261121_154324.json` - Bart + Claude [ISSUE-109]
- 2026-11-21 - Follower `5B8E114691` auto-calibrated and frozen. Leader `5B79016336` calibrated manually; joints 5 and 7 short (see ISSUE-103)
- 2026-11-21 - Roles confirmed by movement test: leader `5B79016336` (/dev/ttyACM0), follower `5B8E114691` (/dev/ttyACM1)

## [Unreleased] - 2026-11-21 afternoon
### Added
- `calibration/official/`: OpenCV's official 9x6 chessboard (`pattern.png`, unmodified, 25 mm squares) + A4 print PDF
- `scripts/calibrate_camera.py` (lens + table homography, `--ruler-mm` print-scale correction), `snap_cams.py`, `first_motion.py` (guarded, needs `--yes`), `make_checkerboard.py`, `make_aruco.py`
- `docs/NEXT_STEPS.md`, `docs/SETUP.md`; strategy docs 02, 03, 06, 07 added to the repo at the owner's request
### Fixed
- `StationBackend.send_goals`: goal wraps modulo 4096
### Changed
- `run/station.yaml`: `resolution: auto`, `resize_target: 0` (not applied until Station restart)

## [Unreleased] - 2026-11-21 evening (Sushruth's laptop)
### Added
- `vision.find_dark_object`: model-free black-object detector for the white table (cables removed by opening); tested live on the front camera: box (224,215)-(260,253), contact point (242,253)
- `scripts/autorun.py --vision dark|yolo`: the single-process loop now uses the dark-blob detector or Bart's `normakit.detect.Detector` (YOLO) on the Station front camera; `--table-calib` selects the pixel->robot mapping
- Merged teammates' work (YOLO detect, ArUco markers, tools/, calibration backups) from origin/main
- 2026-11-21 evening - Camera calibration finished: front lens (0.39 px), wrist lens v2 (0.44 px, v1 kept), table mapping from 4 hand-touched board corners (rigid model, honest residual 26 mm); `scripts/touch_capture.py`, `touch_fit.py`, `touch_register.py`; `calibration/table_front.json`, `touch_points_front.json`, `board_frame_front.jpg`.
