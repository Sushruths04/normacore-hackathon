# Next steps (updated 2026-11-21 16:35 — HANDOFF, read this first)

**Hardware owner:** Bart's Mac (both arms + camera `b309a703`), Station running there (`./restart_station.sh`, log `logs/station-latest.log`). Handing over to a colleague for **camera + follower calibration**.
Claim a task by writing your name next to it. Ask a human before any arm motion (AGENTS.md safety rules).

## Project (decided 16:25)
**Follower arm only, YOLO-based pick and place (a cup).** Leader not used.

## State right now (verified 16:30)
- **Follower `5B8E114691`: joint-calibrated and saved** on Bart's Mac (auto-cal 15:40). Spans m1 1972, m2 2012, m3 2322, m4 2326, m5 3836, m6 2050, m7 3874, m8 1610 = reference within ~1%. Backup `calibration/5B8E114691_follower_20261121_155309.json`. Torque OFF on all motors (arm limp, resting; joint 2 at its stop, norm 0.015).
- **Leader `5B79016336`: NOT SAVED, don't use** (ISSUE-111, ISSUE-112).
- **The follower calibration lives in THIS Mac's Station data** (`~/Downloads/station_data`). Moving the arm to another laptop loses it (ISSUE-109) - recalibrate there with `python3 tools/calibrate.py reset --bus follower` then `auto --bus follower` (156 s, worked first time). **Don't open the follower's web-UI calibration page** (it resets the bus). Station restart behaviour untested - run `python3 scripts/backup_calibration.py` first.
- Camera: only `b309a703` delivers frames (30 fps, 299x224 - ISSUE-105). Others black/missing (ISSUE-002, ISSUE-106).
- No motion has been sent to the follower by code yet.

## Handoff: what to do next (in order)
1. **Follower joint-direction check (ISSUE-107)** - human at the table, hand on the 12 V plug, mirroring off. Per joint, one at a time:
   `python3 scripts/first_motion.py --joint N --delta D --yes` with D ~= 50/span (j1 0.025, j2 0.025, j3 0.022, j4 0.021, j5 0.013, j6 0.024, j7 0.013, j8 0.031). Moves +~4 deg slowly and back; refuses >60 ticks or start/target outside 2-98 %. **Lift joint 2 ~10 deg by hand first** (it rests at 1.5 %). Torque stays ON on tested joints.
   Record per joint: which part moved and which way on "+" (e.g. "elbow up", "gripper closes") -> table in `docs/SETUP.md`; compare with the URDF signs assumed in `src/normakit/core.py` (`URDF_LIMITS`, `norm_to_rad`).
2. **Camera calibration** - mount the camera fixed, print `calibration/official/opencv_pattern_9x6_25mm_A4_PRINT.pdf` (check 25 mm squares), run `scripts/calibrate_camera.py` (lens) and `--table` (pixel -> table plane). Consider restarting Station for full-res frames (`run/station.yaml`, ISSUE-105) - back up calibration first.
3. **YOLO cup detection** - built (`src/normakit/detect.py`, `tools/detect_live.py`, branch `bart/yolo-detect`), tested on sample images + Mac webcam. Left: run on Station frames (`--source station`), then pixel (`bottom_px`) -> table XY via step 2. — Bart
4. **Pick and place**: `src/normakit/kin.py` (IK) + `arm.py` skills through `StationBackend`; first runs slow, over an empty table.

## Tasks
| # | Task | Exit check | Owner |
|---|---|---|---|
| 1 | Stabilise both cameras (cables / direct laptop ports; udev rule for 2c7f:4a60) | `snap_cams.py` returns a clear frame from both | open |
| 2 | Restart Station with `resize_target: 0` (already in `run/station.yaml`), `./norma backup` first | frames larger than 299x224 | open |
| 3 | Camera calibration with the official OpenCV board (`calibration/official/`) - `scripts/calibrate_camera.py` | rms < 1 px, `calibration/camera_<cam>.json` | open |
| 4 | Find which joints move opposite between leader and follower (incl. trigger vs gripper) - ISSUE-107 | table joint -> same/opposite | open |
| 5 | Custom teleop loop with per-joint invert, speed cap, home pose (replaces Station mirroring) | follower tracks leader, one writer on the bus | open |
| 6 | Redo leader joints 5 and 7 (manual sweep) - ISSUE-103 | spans >= ~3500 ticks | open |
| 7 | First motion test `scripts/first_motion.py --joint 8 --delta 0.03 --yes` (mirroring OFF, human present) | joint moves ~3% and returns | open |
| 8 | Table camera -> robot mapping (`calibrate_camera.py --table`), then Claude tool loop (`src/normakit/mcp_server.py`, `elrobot-real`) | pick a block by pixel | open |

## Notes
- 2026-11-21 15:40 — Bart's macOS repo merged in (tools/, start/restart scripts, ISSUE-001..015). Bart's repo `bpachniewsk1/normacore-hackathon` is superseded by this one.
- 2026-11-21 15:58 — **Bart's Mac has the arms** (both buses + 1 camera b309a703). Both arms NOT SAVED here (ISSUE-109) → recalibrating: follower auto, leader manual (`tools/calibrate.py`) — in progress, Bart + Claude.
- 2026-11-21 15:45 — Follower calibrated on Bart's Mac (all 8 saved, spans match reference; m1 now 1972 ≈ URDF 2021). **Leader manual calibration next** (needs a human sweeping every joint). Local link `vendor/norma-core-src -> ../repo/norma-core` makes Sushruth's scripts work on the Mac.
- 2026-11-21 15:52 — Leader manual sweep abandoned (hard to tell joints apart); team switching to **web-UI Auto Calibrate for the leader**. Watch for ISSUE-003 (erratic leader auto-cal earlier today).
- 2026-11-21 15:55 — Leader auto-cal done but joints 3/4/5 short (ISSUE-111). **Do not start mirroring.** Next: manual leader calibration.
- 2026-11-21 16:25 — **Decision: follower only, YOLO pick-and-place of a cup.** Leader m4 never re-swept after an accidental web-UI reset at 16:10:56 → leader NOT SAVED, don't use. Next for the follower: joint direction/angle check vs URDF (ISSUE-107), gripper open/close direction, camera calibration + camera→table mapping (one working camera b309a703, 299x224 frames ISSUE-105).
- 2026-11-21 17:35 — Vision side ready on Mac webcam (branch `bart/yolo-detect`): cup + bottle detected together (YOLO11n), team ArUco markers detected, **ID 6 zone C shows as DROP** (verified live). Left: same on the Station camera (`--source station`), measure corner marker positions -> `calibration/markers.json`, then teach-and-pick. — Bart
- 2026-11-21 18:05 — **Restart plan:** one table, follower clamped, table camera high + outside reach + taped, markers 0-3 at the work-area corners (inside reach), 6 = DROP; one Station laptop, follower auto-cal + backup; then `tools/teach_wizard.py` (guided, records hover/grasp joint angles at each marker) -> pick routine interpolates joint angles (avoids the 2-4 cm FK error, ISSUE-107). Leader optional. — Bart
