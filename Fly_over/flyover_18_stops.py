# %% [markdown]
# # 18-stop flyover -> Google Earth Studio (.esp) + KML tour
# Paste into Colab (each `# %%` block = a cell). Outputs:
#   flyover.esp  -> Earth Studio: open the project and render (Render > Advanced > mp4/jpg)
#   flyover.kml  -> Google Earth Pro: double-click the tour, then Tools > Movie Maker (guaranteed fallback)
#
# ESP is undocumented JSON. For the most reliable import, make a 1-keyframe project in
# Earth Studio, set your tilt/FOV/resolution, download it as `template.esp`, and upload it.
# The script then injects keyframes into YOUR schema version instead of building one from scratch.

# %%
import json, math, copy, os

STOPS = [
    ("Coeur d'Alene, ID",     47.6777, -116.7805),
    ("Deer Park, WA",         47.9543, -117.4769),
    ("Winlock, WA",           46.4910, -122.9379),
    ("Ellensburg, WA",        46.9965, -120.5478),
    ("Portland, OR",          45.5152, -122.6784),
    ("Cathlamet, WA",         46.2032, -123.3832),
    ("McKenzie Bridge, OR",   44.1754, -122.1606),
    ("Lyle, WA",              45.6962, -121.2862),
    ("Springfield, IL",       39.7817,  -89.6501),
    ("Santa Fe, NM",          35.6870, -105.9378),
    ("Fort Collins, CO",      40.5853, -105.0844),
    ("Huntsville, AL",        34.7304,  -86.5861),
    ("Bangkok, Thailand",     13.7563,  100.5018),
    ("Naypyidaw, Myanmar",    19.7633,   96.0785),
    ("Kathmandu, Nepal",      27.7172,   85.3240),
    ("Dhaka, Bangladesh",     23.8103,   90.4125),
    ("Thimphu, Bhutan",       27.4728,   89.6390),
    ("Enschede, Netherlands", 52.2215,    6.8937),
]

TOTAL_SEC   = 90      # whole video
FPS         = 30
HOLD_SEC    = 1.0     # dwell over each stop
STOP_ALT_M  = 8_000   # camera altitude over each city
MIN_APEX_M  = 25_000  # short hops (WA towns)
MAX_APEX_M  = 9_000_000  # intercontinental hops go to orbit
APEX_FACTOR = 0.9     # apex altitude ~ 0.9 x leg distance
WIDTH, HEIGHT = 1920, 1080
REORDER_ASIA = False  # True -> Bangkok>Naypyidaw>Dhaka>Thimphu>Kathmandu (shorter hops)

if REORDER_ASIA:
    order = ["Bangkok", "Naypyidaw", "Dhaka", "Thimphu", "Kathmandu"]
    asia = [next(s for s in STOPS if s[0].startswith(o)) for o in order]
    STOPS = [s for s in STOPS if s not in asia]
    i = [s[0] for s in STOPS].index("Enschede, Netherlands")
    STOPS = STOPS[:i] + asia + STOPS[i:]

# %%  timeline: holds + legs, leg time weighted by sqrt(distance)
def haversine_m(a, b):
    R = 6_371_000
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    dp, dl = p2 - p1, math.radians(b[2] - a[2])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

n = len(STOPS)
dists = [haversine_m(STOPS[i], STOPS[i+1]) for i in range(n-1)]
w = [math.sqrt(d) for d in dists]
leg_total = TOTAL_SEC - HOLD_SEC * n
assert leg_total > 0, "TOTAL_SEC too short for holds"
leg_sec = [leg_total * x / sum(w) for x in w]

# keyframes: (t_sec, lat, lon, alt_m)
kf, t = [], 0.0
for i, (name, lat, lon) in enumerate(STOPS):
    kf.append((t, lat, lon, STOP_ALT_M)); t += HOLD_SEC
    kf.append((t, lat, lon, STOP_ALT_M))
    if i < n - 1:
        nlat, nlon = STOPS[i+1][1], STOPS[i+1][2]
        apex = min(MAX_APEX_M, max(MIN_APEX_M, APEX_FACTOR * dists[i]))
        kf.append((t + leg_sec[i]/2, (lat+nlat)/2, (lon+nlon)/2, apex))
        t += leg_sec[i]

DURATION_FR = round(TOTAL_SEC * FPS)
for name, d, s in zip([s[0] for s in STOPS[1:]], dists, leg_sec):
    print(f"-> {name:24s} {d/1000:8.0f} km  {s:5.2f}s")
print(f"total {t:.1f}s, {len(kf)} keyframes, {DURATION_FR} frames")

# %%  ESP
RANGES = {"longitude": (-180, 180), "latitude": (-89.9999, 89.9999), "altitude": (1, 65_117_481)}
COL    = {"latitude": 1, "longitude": 2, "altitude": 3}

def norm(kind, v):
    lo, hi = RANGES[kind]; return (v - lo) / (hi - lo)

def make_kfs(kind, proto=None, frames_mode=False):
    out = []
    for row in kf:
        k = copy.deepcopy(proto) if proto else {}
        k["time"]  = round(row[0] * FPS) if frames_mode else row[0] / TOTAL_SEC
        k["value"] = norm(kind, row[COL[kind]])
        out.append(k)
    return out

def build_esp_from_scratch():
    def attr(kind):
        lo, hi = RANGES[kind]
        return {"type": kind, "value": {"minValueRange": lo, "maxValueRange": hi},
                "keyframes": make_kfs(kind)}
    return {
        "modelVersion": 16,
        "settings": {"name": "18-stop flyover", "frameRate": FPS,
                     "dimensions": {"width": WIDTH, "height": HEIGHT},
                     "duration": DURATION_FR, "timeFormat": "frames"},
        "scenes": [{
            "animationModel": {"roving": False, "logarithmic": False, "groupedPosition": True},
            "duration": DURATION_FR,
            "attributes": [{"type": "cameraGroup", "attributes": [
                {"type": "cameraPositionGroup", "attributes": [
                    {"type": "position", "attributes": [attr("longitude"), attr("latitude"), attr("altitude")]}
                ]}
            ]}],
        }],
        "playbackManager": {"range": {"start": 0, "end": DURATION_FR}},
    }

def inject_into_template(esp):
    hits = []
    def walk(o):
        if isinstance(o, dict):
            if o.get("type") in RANGES and "keyframes" in o:
                old = o["keyframes"]
                proto = {k: v for k, v in old[0].items() if k not in ("time", "value")} if old else None
                frames_mode = any(k.get("time", 0) > 1.0 for k in old)
                o["keyframes"] = make_kfs(o["type"], proto, frames_mode)
                hits.append(o["type"])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(esp)
    assert {"latitude", "longitude", "altitude"} <= set(hits), f"template missing position keyframes: {hits}"
    esp.setdefault("settings", {}).update(duration=DURATION_FR, frameRate=FPS)
    for sc in esp.get("scenes", []): sc["duration"] = DURATION_FR
    esp.setdefault("playbackManager", {})["range"] = {"start": 0, "end": DURATION_FR}
    return esp

# Optional: upload template.esp exported from Earth Studio
try:
    from google.colab import files
    if not os.path.exists("template.esp"):
        print("Upload template.esp (or cancel to build from scratch)")
        try: files.upload()
        except Exception: pass
except ImportError:
    files = None

if os.path.exists("template.esp"):
    esp = inject_into_template(json.load(open("template.esp")))
    print("built from template.esp")
else:
    esp = build_esp_from_scratch()
    print("built from scratch")
json.dump(esp, open("flyover.esp", "w"))

# %%  KML tour (Google Earth Pro fallback; well-documented format)
def lookat(lat, lon, alt, tilt=0, heading=0):
    return (f"<LookAt><longitude>{lon}</longitude><latitude>{lat}</latitude><altitude>0</altitude>"
            f"<heading>{heading}</heading><tilt>{tilt}</tilt><range>{alt}</range>"
            f"<altitudeMode>relativeToGround</altitudeMode></LookAt>")

steps = []
prev = 0.0
for (ts, lat, lon, alt) in kf:
    dur = max(ts - prev, 0.05); prev = ts
    steps.append(f"<gx:FlyTo><gx:duration>{dur:.3f}</gx:duration>"
                 f"<gx:flyToMode>smooth</gx:flyToMode>{lookat(lat, lon, alt)}</gx:FlyTo>")
pins = "".join(f"<Placemark><name>{nm.replace('&','&amp;')}</name><Point><coordinates>{lo},{la},0</coordinates></Point></Placemark>"
               for nm, la, lo in STOPS)
kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
<Document><name>18-stop flyover</name>{pins}
<gx:Tour><name>Flyover tour</name><gx:Playlist>{''.join(steps)}</gx:Playlist></gx:Tour>
</Document></kml>"""
open("flyover.kml", "w").write(kml)

if files:
    files.download("flyover.esp"); files.download("flyover.kml")
