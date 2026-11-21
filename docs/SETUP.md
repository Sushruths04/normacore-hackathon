# Setup facts (verified on this rig unless marked)

- **Buses:** leader `5B79016336` = /dev/ttyACM0 (USB `1a86:55d3`), 7.5 V; follower `5B8E114691` = /dev/ttyACM1, 12 V. Both 8 ST3215 motors, ids 1-8. `run/buses.json` is the source of truth for our scripts.
- **Linux perms:** serial ports need `dialout`; Station opens cameras with libusb, so the USB device node must be writable (`sudo chmod 666 /dev/bus/usb/001/NNN`, or a udev rule for `2c7f:4a60`). Error in the log when not: `Failed to open device for camera ...: -3`.
- **Start Station:** `./norma start` (runs `bin/station --web --tcp --config run/station.yaml` in `run/`). Web UI http://localhost:8889 - use Firefox (WebGL is off in the Chrome here).
- **Calibration storage:** motors keep only the centring offset (EEPROM). Min/max ranges + frozen flag live in Station's `st3215/meta` queue under `run/station_data/`, and are restored from it at startup unless the last entry is a reset (read in `drivers/st3215/src/port_meta.rs`; restart NOT yet tested). Backups: `calibration/*.json` via `./norma backup`.
- **Opening a bus's calibration page resets that bus** and stops mirroring (torque off).
- **Mirroring** (`motors-mirroring`) copies leader % of range to follower %; it cannot invert a joint. A second start does not cancel an opposite one (two mirrors can fight).
- **Station torque defaults:** all motors max torque 500/1000, torque limit 1000, P16 I0 D0, protection current 500, overload torque 25 (ISSUE-101).
- **3D viewer mapping** (`station-viewer .../elrobot/config.ts`): joints 1-7 linear over URDF limits; gripper (motor 8) flipped.
- **Official board:** `calibration/official/opencv_pattern_9x6_25mm_A4_*` = OpenCV's `doc/pattern.png`, 9x6 inner corners, 25.00 mm squares (measured), A4 landscape.
- **Read-only tools:** `./norma status|identify|backup|smoke`, `scripts/dump_buses.py`, `monitor_calib.py`, `twin_view.py`, `snap_cams.py`. Moving tools: `first_motion.py` (needs `--yes`).
- **Camera format (Station beta.10):** set in `run/station.yaml` as `usb-video: formats: [ {format: "640x480@30fps,mjpeg"} ]` and `resize_target: 0`; restart Station. The `resolution:` key is ignored in this build. Default (empty list) opens MJPG 320x240 which gave washed-out pictures. Camera controls (exposure etc.) can be read/set with `scripts/uvc_ctl.py` only while Station is NOT holding the camera.
- **USB hub:** the shared hub dropped repeatedly (kernel `error -71`, 15 disconnects on one port in 3 h). Cameras plugged directly into laptop ports are stable so far. udev rule `/etc/udev/rules.d/99-norma.rules` makes the serial boards and cameras world-writable (applies on re-plug).
- **Camera calibration needs no arms and no hub:** `scripts/calibrate_camera.py` only reads frames from Station (`require_motors=False`).

## macOS laptop (Bart) — merged from bpachniewsk1/normacore-hackathon
- Serial ports appear as `/dev/cu.usbmodem<bus-serial>1` (leader `/dev/cu.usbmodem5B790163361`, follower `/dev/cu.usbmodem5B8E1146911`), not `/dev/ttyACM*`. `./norma` and `run/buses.json` assume Linux.
- Station binary (macOS arm64 zip) lives in `~/Downloads` by default: `./restart_station.sh` (background, log `logs/station-latest.log`), `./restart_station.sh stop`, `./start_station.sh` (foreground). Override with `STATION_DIR=/path`.
- `tools/` finds the upstream Python client at `vendor/norma-core-src`, else `repo/norma-core`, else `$NORMA_CORE`.
- Read-only: `python3 tools/verify_station.py [--watch]` (USB, Station, per-motor pos=raw+offset / torque / current / temp / voltage / range / saved flag / error status, cameras + black-frame check).
- Moving / torque: `tools/estop.py` (HOLD = stop mirroring + goal = current; `--limp` = torque off), `tools/reset_calibration.py --bus SN` (= web-UI Reset, torque off), `tools/speed_limit.py` (Goal Speed 0x2E + Acc 0x29; never applied on hardware).
- `patches/teleop-max-speed.patch`: adds `--max-speed`/`--max-accel` to upstream `st3215-remote-teleop-py` (apply with `git -C vendor/norma-core-src apply ../../patches/teleop-max-speed.patch`; untested on hardware).
- Auto-calibration (`elrobot.rs`): only for exactly 8 motors IDs 1–8; stall-sweeps each joint up to ~360° from the current pose at fixed speed 365 / accel 50 / torque limit 300 — clear the workspace. Mirroring max speed is hard-coded (3300) in `motors-mirroring/src/config.rs`.
- Calibration over TCP (`tools/calibrate.py`): `st3215.Command` has `reset_calibration` (14), `freeze_calibration` (15, freeze=True without arcs = web-UI Save), `auto_calibrate` (17), `stop_auto_calibrate` (18); progress in `BusState.auto_calibration` (`protobufs/drivers/st3215/st3215.proto`). Moving the arms to another laptop loses the saved ranges (ISSUE-109).
- **Table markers** (`calibration/markers.json`, sheet `aruco_markers_A4.pdf`): DICT_4X4_50, 40 mm. ID 0 corner front-left, 1 front-right, 2 back-right, 3 back-left, 4 zone A, 5 zone B, **6 zone C = DROP**, 7 bowl. Live check: `.venv/bin/python tools/detect_live.py --classes cup,bottle --markers`.

## Camera + table calibration state (2026-11-21 evening, Sushruth's laptop) - all files in `calibration/`
- **Cameras (Station numbering changes at every restart - identify by picture):** front = table overview, wrist = on the follower's gripper (its picture is rotated 90 deg). Station config `usb-video.formats: 640x480@30fps,mjpeg`, `resize_target: 0`.
- **Front lens:** `camera_front.json` (15 views, rms 0.39 px, fx 308 fy 320, ~92 deg HFOV). Valid for that physical camera at 640x480.
- **Wrist lens:** `camera_wrist.json` = v2 (22 of 30 views kept, rms 0.44 px, fx=fy=302, ~93 deg). `camera_wrist_v1_rms1p49.json` is the earlier fallback; `camera_wrist_v2_points.npz` the corner data.
- **Table mapping (front pixel -> robot x,y metres):** `table_front.json`, made by hand-touching the 4 inner corners of the printed OpenCV board with the follower's gripper tip (`scripts/touch_capture.py record <corner>` x4, then `scripts/touch_fit.py`). Raw touches: `touch_points_front.json`; the board picture used: `board_frame_front.jpg`.
  - Model: rigid, mirrored (robot x,y is a mirror of the board axes), scale fit 1.003.
  - **Honest accuracy: mean 26.4 mm, max 32.9 mm residual at the 4 corners** (the exact 4-point homography reported 0 mm, which is meaningless). Expect about +-3 cm. Fine for hovering above an object, NOT yet for a reliable grasp of a small object.
  - Forward kinematics gives EE z ~ 0.107 m when the tip is on the table (mean of the 4 touches), so the table reference for `Kin` targets is z = 0.107, not `TABLE_Z` = 0.02 in `arm.py`.
  - Measured corner spacing from the arm: top 20.4 cm (true 20), sides 8-10 cm (true 12.5), bottom 24.6 cm (true 20): hand placement / FK error of 2-4 cm.
- **Do not move the front camera or the robot base** after this; otherwise redo the touches. The board can be removed.
- **Ideas to tighten it:** more touch points (middle of the sheet), keep the gripper pointing straight down for every touch, and close the loop with the camera (see where the gripper is in the picture and correct the last centimetres).
- **Station restart keeps saved calibration (verified 2026-11-21 18:33 on Bart's Mac):** after `./restart_station.sh` the follower still showed 8x `calibrated (saved)` with identical ranges, torque state unchanged (tq=1 stayed on). Ranges are restored from `station_data` (`st3215/meta`).
