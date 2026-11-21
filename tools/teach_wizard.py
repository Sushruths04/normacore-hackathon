#!/usr/bin/env python3
"""
Guided camera <-> arm calibration ("teach wizard"). You guide the follower by hand, the wizard records.

  .venv/bin/python tools/teach_wizard.py                 # markers 0,1,2,3 (corners) + 6 (DROP) + 3 spots with marker 7
  .venv/bin/python tools/teach_wizard.py --resume        # continue where you stopped
  .venv/bin/python tools/teach_wizard.py --extra 5       # more free spots with the movable marker 7

Per point:  1) camera reads the marker centre (arm out of the way)
            2) you hold the gripper ~10 cm ABOVE the marker      -> Enter = HOVER pose
            3) you lower the fingertips onto the marker centre    -> Enter = GRASP pose
Keys at every prompt: Enter = do it, r = redo, s = skip this point, q = save + quit.
Output: calibration/teach_points.json  (pixel + hover/grasp joint angles per point; used by the pick routine).

Safety: the ONLY command this tool sends is torque OFF on the follower (after you confirm). It never moves the arm.
Needs: Station running, follower calibrated (8x saved), table camera fixed, markers taped down (calibration/markers.json).
"""
import argparse, json, statistics, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
OUT = REPO / "calibration" / "teach_points.json"


def rel(path):
    try:
        return str(Path(path).relative_to(REPO))
    except ValueError:
        return str(path)


def say(msg=""):
    print(msg, flush=True)


def ask(prompt):
    """Enter -> 'go', r/s/q -> that letter."""
    while True:
        k = input(f"   {prompt}  [Enter / r / s / q] > ").strip().lower()
        if k in ("", "r", "s", "q"):
            return k or "go"
        say("   (unknown key)")


# ------------------------------------------------------------------ hardware access
class Rig:
    def __init__(self, host, camera):
        from normakit.station_backend import StationBackend, REG_TORQUE
        self.REG_TORQUE = REG_TORQUE
        self.be = StationBackend(host)
        self.be.start()
        self.camera = camera

    def joints(self):
        return self.be.state().joints

    def frame(self, cam=None):
        from normakit.detect import to_rgb
        return to_rgb(self.be.frame_jpeg(cam or self.camera))

    def cameras(self):
        return [c for c in self.be.cameras() if c.startswith("cam")]

    def torque_off(self):
        self.be._sync(self.REG_TORQUE, {i: b"\x00" for i in self.joints()})


# ------------------------------------------------------------------ steps
def wait_still(rig, hold=1.0, tol=0.004, timeout=20):
    """Return joint snapshot once nothing moved more than tol (norm) for `hold` seconds."""
    hist, t0 = [], time.time()
    while time.time() - t0 < timeout:
        js = rig.joints()
        now = time.time()
        hist.append((now, {i: j.norm for i, j in js.items()}, js))
        hist = [h for h in hist if h[0] >= now - hold - 0.2]
        if now - hist[0][0] >= hold:
            spread = max(max(h[1][i] for h in hist) - min(h[1][i] for h in hist) for i in hist[-1][1])
            if spread <= tol:
                return {str(i): {"raw": j.raw, "norm": round(j.norm, 4)} for i, j in sorted(js.items())}
        time.sleep(0.1)
    return None


def marker_pixel(rig, md, mid, frames=10):
    pts = []
    for _ in range(frames * 3):
        for m in md.detect(rig.frame()):
            if m["id"] == mid:
                pts.append(m["center_px"])
        if len(pts) >= frames:
            break
        time.sleep(0.05)
    if len(pts) < frames // 2:
        return None, f"marker {mid} seen in only {len(pts)} frames - is it covered or out of view?"
    u = statistics.median(p[0] for p in pts); v = statistics.median(p[1] for p in pts)
    jitter = max(max(abs(p[0] - u), abs(p[1] - v)) for p in pts)
    return [round(u, 1), round(v, 1)], f"jitter {jitter:.1f} px over {len(pts)} frames"


def pick_camera(rig, md, want):
    say("\n[1/4] Camera")
    if rig.camera:
        cams = [rig.camera]
    else:
        t0 = time.time()
        while not rig.cameras() and time.time() - t0 < 10:
            time.sleep(0.5)
        cams = rig.cameras()
    best = (None, [])
    for c in cams:
        try:
            ids = sorted({m["id"] for m in md.detect(rig.frame(c))})
        except RuntimeError as e:
            say(f"   {c}: {e}"); continue
        say(f"   {c}: markers {ids}")
        if len(ids) > len(best[1]):
            best = (c, ids)
    if not best[0]:
        sys.exit("   no camera sees any marker - check camera, light, markers (white border!)")
    rig.camera = best[0]
    missing = [i for i in want if i not in best[1]]
    say(f"   -> using {best[0]}" + (f"   (NOT visible: {missing})" if missing else "   (all needed markers visible)"))
    try:
        import cv2
        from normakit.markers import draw
        img = rig.frame()[:, :, ::-1].copy()
        draw(img, md.detect(img[:, :, ::-1]), md)
        (REPO / "snapshots").mkdir(exist_ok=True)
        cv2.imwrite(str(REPO / "snapshots" / "teach_camera.jpg"), img)
        say("   snapshot: snapshots/teach_camera.jpg")
    except Exception:
        pass
    return missing


def check_arm(rig):
    say("\n[2/4] Follower")
    t0 = time.time()
    while not rig.joints() and time.time() - t0 < 10:
        time.sleep(0.3)
    js = rig.joints()
    bad = [i for i, j in js.items() if (j.hi - j.lo) % 4096 < 300]
    say(f"   {len(js)} joints" + (f", NOT calibrated: {bad}" if bad else ", all calibrated"))
    if len(js) < 8 or bad:
        sys.exit("   calibrate the follower first: python3 tools/calibrate.py auto --bus follower")
    say("   The wizard turns torque OFF so you can guide the arm by hand. It will go LIMP.")
    if ask("Hold the arm with one hand, then press Enter to switch torque OFF") != "go":
        sys.exit("   stopped (torque unchanged)")
    rig.torque_off()
    say("   torque OFF")


def plan(a, roles):
    names = roles.get("names", {})
    pts = [{"key": f"m{i}", "marker": i, "name": names.get(str(i), f"marker {i}")} for i in a.markers]
    spots = ["centre of the work area", "left-middle", "right-middle", "front-middle", "back-middle", "free spot"]
    for k in range(a.extra):
        pts.append({"key": f"m7_{k + 1}", "marker": 7, "name": f"spot {k + 1}: {spots[min(k, len(spots) - 1)]}", "move": True})
    return pts


def teach(rig, md, points, data):
    say(f"\n[3/4] Teach {len(points)} points  (Enter = record, r = redo, s = skip, q = save+quit)")
    for n, p in enumerate(points, 1):
        if p["key"] in data["points"]:
            say(f"\n-- {n}/{len(points)} {p['name']}: already recorded, skipping (delete it from the json to redo)")
            continue
        say(f"\n-- Point {n}/{len(points)}: {p['name']} (marker ID {p['marker']})")
        if p.get("move"):
            say(f"   Put the movable marker ID 7 at: {p['name'].split(': ', 1)[-1]} (inside reach, flat).")
        rec = {"marker": p["marker"], "name": p["name"]}
        steps = [("pixel", "Move the arm so it does NOT cover the marker. Enter = camera reads the marker"),
                 ("hover", "Hold the gripper ~10 cm ABOVE the marker centre, open, pointing down. Hold still, Enter"),
                 ("grasp", "Lower the fingertips onto the marker centre (grasp height). Hold still, Enter")]
        i = 0
        while i < len(steps):
            what, prompt = steps[i]
            k = ask(prompt)
            if k == "q":
                return False
            if k == "s":
                say("   skipped"); rec = None; break
            if k == "r":
                i = max(0, i - 1); continue
            if what == "pixel":
                px, info = marker_pixel(rig, md, p["marker"])
                if not px:
                    say(f"   ! {info}"); continue
                rec["pixel"] = px; say(f"   marker at pixel {px} ({info})")
            else:
                say("   hold still ...")
                pose = wait_still(rig)
                if not pose:
                    say("   ! arm kept moving for 20 s - hold it still and press Enter again"); continue
                rec[what] = pose
                say(f"   {what.upper()} recorded: " + " ".join(f"j{j}={v['norm']:.2f}" for j, v in pose.items()))
            i += 1
        if rec:
            rec["t"] = time.strftime("%H:%M:%S")
            data["points"][p["key"]] = rec
            OUT.write_text(json.dumps(data, indent=1))
            say(f"   saved ({len(data['points'])} points in {rel(OUT)})")
    return True


def summary(data):
    say("\n[4/4] Summary")
    pts = data["points"]
    for k, r in pts.items():
        say(f"   {k:6s} {r['name']:28s} pixel={r.get('pixel')}  hover={'ok' if 'hover' in r else '-'}  grasp={'ok' if 'grasp' in r else '-'}")
    full = sum(1 for r in pts.values() if all(x in r for x in ("pixel", "hover", "grasp")))
    say(f"   {full} complete points." + ("  Enough for the pick routine (>= 5 incl. DROP)." if full >= 5 and "m6" in pts
                                         else "  Need >= 5 complete points incl. DROP (marker 6)."))
    say(f"   File: {rel(OUT)}.  Camera, robot base and markers must not move from now on.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markers", type=lambda s: [int(x) for x in s.split(",")], default=[0, 1, 2, 3, 6],
                    help="fixed markers to teach (default 0,1,2,3,6)")
    ap.add_argument("--extra", type=int, default=3, help="extra free spots using movable marker 7 (default 3)")
    ap.add_argument("--camera", help="station camera (cam0/cam1); default: the one that sees most markers")
    ap.add_argument("--host", default="localhost:8888")
    ap.add_argument("--resume", action="store_true", help="keep points already in the json")
    a = ap.parse_args()

    from normakit.markers import MarkerDetector
    md = MarkerDetector()
    if not md.dictionary:
        sys.exit("calibration/markers.json missing or without 'dictionary'")
    say(__doc__.split("\n\n")[0].strip())
    rig = Rig(a.host, a.camera)
    time.sleep(1.5)
    pick_camera(rig, md, a.markers + ([7] if a.extra else []))
    check_arm(rig)
    data = json.loads(OUT.read_text()) if a.resume and OUT.exists() else {"points": {}}
    data.update({"camera": rig.camera, "bus": getattr(rig.be, "_bus", None), "dictionary": md.dictionary,
                 "started": data.get("started", time.strftime("%F %T"))})
    finished = teach(rig, md, plan(a, md.roles), data)
    OUT.write_text(json.dumps(data, indent=1))
    summary(data)
    if not finished:
        say("   stopped early - continue later with --resume")
    import os
    os._exit(0)


if __name__ == "__main__":
    main()
