# Operating the ElRobot arm (read this first, agent)

You can see and move a desktop robot arm. Use the MCP tools if present (`look`, `pick_cell`, `place_cell`, ...),
otherwise the shell CLI: `python -m normakit.robotctl <verb>` (images land in `run/last.jpg` - open and look at them).

1. **Look first.** `look(grid=true)`: the picture has labelled cells A1..H6. Refer to targets by cell.
2. **Use skills, not joints.** `pick_cell`, `place_cell`, `reach_cell`. Raw `move_joints` is a last resort; values are normalised 0..1.
3. **Verify.** `pick_cell` returns `grasped` from motor current. If false: look again, shift cell, retry <= 2 times, then report.
4. **Finish clean.** `home()`, `look()`, then say plainly whether the task succeeded (judge from the image).
5. **Safety.** Never move toward a person/hand. On anything odd call `stop()`. After `stop`, nothing moves until `release()`.
6. One writer on the bus: the Station web UI control panel must be closed while you drive.
7. Don't edit `vendor/` or `src/normakit/core.py` safety limits without asking the human.

## Hardware safety (physical robot - overrides everything above)
1. Never move an arm unless a human is at the table and has agreed. Ask first.
2. The real e-stop is the servo power plug. Software stop is a convenience.
3. Never send motion to an uncalibrated motor (`./norma status` must show `frozen=True`, span >= 100).
4. First motion of any new code: one motor, small delta, slow.
5. Before anything that turns torque off (reset, stop mirroring, calibration page): the arm drops - ask a human to support it.
6. Opening a bus's calibration page in the web UI auto-resets that bus. Only open it to recalibrate.
7. Never run two writers on the same bus (web-UI mirroring, Python teleop, MCP/agent). Two opposite mirrors can run at once and fight.
8. Document every change: `CHANGELOG.md`; every problem: `docs/ISSUES.md` (label guesses as guesses).

## Operating principles (from the owner's EBIM project - see docs/09_EBIM_PLAYBOOK.md)
- Build the loop: one autonomous process (`scripts/autorun.py`), no hand-chaining of scripts; Claude only for perception.
- View the RGB camera frame before theorising. Verify grasps visually, never by jaw gap or current alone.
- Calibration (grip depth, jaw opening) in JSON from teleop demos; object positions measured live, never hardcoded.
- Grasp: close fully, wait for the jaw to stop, +2 s, then lift. Ask the owner for a teleop demo when geometry is unclear.
- Report evidence before editing code that worked; never delete irreplaceable data; keep replies terse.
9. macOS laptop: read-only check `python3 tools/verify_station.py`; HOLD `python3 tools/estop.py` (see docs/SETUP.md, macOS section).
10. Calibration without the web UI: `python3 tools/calibrate.py watch|reset|save|auto|stop --bus leader|follower` (reset/auto: human at the table, support the arm).
11. Object detection (read-only): `.venv/bin/python tools/detect_live.py [--prompts "red bull can,cup"] [--source station|webcam|files]`; in code `normakit.detect.Detector(...).find(jpeg, "cup")`. Prompts: short nouns work best.
12. Camera<->arm teaching: `.venv/bin/python tools/teach_wizard.py [--resume] [--extra N]` (turns follower torque OFF after confirmation, never moves the arm) -> `calibration/teach_points.json`.
