from pathlib import Path
import cv2
import streamlit as st

DIRECTIONS = ["NORTH", "EAST", "SOUTH", "WEST"]
BASE_DIR = Path(__file__).resolve().parent
MODEL_CANDIDATES = [BASE_DIR / "models", BASE_DIR.parent / "models"]


def find_model(filename):
    for folder in MODEL_CANDIDATES:
        p = folder / filename
        if p.exists():
            return p
    return MODEL_CANDIDATES[0] / filename


TRAFFIC_MODEL_PATH = find_model("traffic_yolo11n.pt")
EMERGENCY_MODEL_PATH = find_model("emergency_yolo11.pt")
VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@st.cache_resource
def load_models():
    from ultralytics import YOLO
    if not TRAFFIC_MODEL_PATH.exists():
        raise FileNotFoundError(f"Traffic model not found: {TRAFFIC_MODEL_PATH}")
    if not EMERGENCY_MODEL_PATH.exists():
        raise FileNotFoundError(f"Emergency model not found: {EMERGENCY_MODEL_PATH}")
    return YOLO(str(TRAFFIC_MODEL_PATH)), YOLO(str(EMERGENCY_MODEL_PATH))


def init_state():
    defaults = {
        "configured": False,
        "sources": {},
        "running": False,
        "vehicle_conf": 0.35,
        "emergency_conf": 0.40,
        "counts": {d: 0 for d in DIRECTIONS},
        "green_direction": "NORTH",
        "green_time": 20,
        "emergency_type": None,
        "emergency_direction": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def choose_signal(counts, emergency_direction=None):
    if emergency_direction:
        return emergency_direction, 45
    if not counts or max(counts.values()) == 0:
        return st.session_state.green_direction, 20
    direction = max(counts, key=counts.get)
    number = counts[direction]
    seconds = 60 if number >= 30 else 45 if number >= 20 else 30 if number >= 10 else 20
    return direction, seconds


def analyze_frame(traffic_model, emergency_model, frame, vehicle_conf, emergency_conf):
    results = traffic_model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        conf=vehicle_conf,
        verbose=False,
    )
    result = results[0]
    count = 0
    if result.boxes is not None and result.boxes.cls is not None:
        for cls in result.boxes.cls.detach().cpu().numpy().astype(int):
            if cls in VEHICLE_CLASSES:
                count += 1

    emergency_result = emergency_model.predict(frame, conf=emergency_conf, verbose=False)[0]
    emergency = None
    if emergency_result.boxes is not None and len(emergency_result.boxes):
        for cls in emergency_result.boxes.cls.detach().cpu().numpy().astype(int):
            name = emergency_result.names[int(cls)]
            if name in ("ambulance", "fire_truck"):
                emergency = name
                break

    output = result.plot()
    if emergency:
        cv2.putText(
            output,
            f"EMERGENCY: {emergency.upper()}",
            (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 0, 255),
            3,
        )
    return output, count, emergency


def css():
    st.markdown(
        """
        <style>
        :root {
            --navy:#0f172a;
            --muted:#64748b;
            --line:#e2e8f0;
            --bg:#f8fafc;
            --blue:#2563eb;
        }
        .stApp { background:var(--bg); }
        [data-testid="stHeader"] {
            background:rgba(248,250,252,.96) !important;
            border-bottom:1px solid var(--line) !important;
        }
        .block-container {
            max-width:1500px;
            padding-top:4.15rem !important;
            padding-bottom:2rem !important;
        }
        footer { visibility:hidden; }

        .app-header {
            position:fixed;
            top:0;
            left:68px;
            right:112px;
            height:3.55rem;
            box-sizing:border-box;
            background:transparent;
            border:0;
            border-radius:0;
            padding:0 8px;
            margin:0;
            display:flex;
            align-items:center;
            gap:12px;
            z-index:999999;
            pointer-events:none;
            box-shadow:none;
        }
        .brand {
            display:flex;
            align-items:center;
            gap:8px;
            flex:0 0 auto;
        }
        .brand-icon {
            width:32px;
            height:32px;
            border-radius:9px;
            display:grid;
            place-items:center;
            background:#eef2ff;
            font-size:18px;
        }
        .brand-name {
            color:var(--navy);
            font-size:1.18rem;
            font-weight:900;
            letter-spacing:-.45px;
            line-height:1;
        }
        .brand-sub {
            color:var(--muted);
            font-size:.73rem;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
            flex:1;
        }
        .section-title { color:var(--navy); font-size:1.1rem; font-weight:850; margin:0; }
        .section-sub { color:var(--muted); font-size:.74rem; margin:3px 0 0; }

        .panel {
            background:#fff;
            border:1px solid var(--line);
            border-radius:14px;
            padding:13px;
            box-shadow:0 3px 14px rgba(15,23,42,.035);
        }
        .source-head {
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom:8px;
        }
        .source-title { color:var(--navy); font-weight:850; font-size:.9rem; }
        .source-badge {
            font-size:.6rem;
            font-weight:800;
            color:#475569;
            background:#f1f5f9;
            padding:4px 7px;
            border-radius:999px;
        }
        .metric-card {
            background:#fff;
            border:1px solid var(--line);
            border-radius:14px;
            padding:12px 14px;
            min-height:76px;
            box-shadow:0 3px 14px rgba(15,23,42,.035);
        }
        .metric-label {
            color:var(--muted);
            font-size:.66rem;
            font-weight:750;
            text-transform:uppercase;
            letter-spacing:.04em;
        }
        .metric-value { color:var(--navy); font-size:1.28rem; font-weight:900; margin-top:4px; }
        .metric-note { color:#94a3b8; font-size:.66rem; margin-top:2px; }

        .signal {
            border-radius:9px;
            padding:8px 10px;
            margin:5px 0;
            font-size:.78rem;
            font-weight:850;
            display:flex;
            justify-content:space-between;
            align-items:center;
        }
        .signal.green { background:#ecfdf5; border:1px solid #bbf7d0; color:#166534; }
        .signal.red { background:#fef2f2; border:1px solid #fecaca; color:#991b1b; }
        .emergency-box { background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; border-radius:11px; padding:12px; }
        .normal-box { background:#f0fdf4; border:1px solid #bbf7d0; color:#166534; border-radius:11px; padding:12px; }

        .cctv-card {
            background:#fff;
            border:1px solid var(--line);
            border-radius:14px;
            overflow:hidden;
            box-shadow:0 4px 16px rgba(15,23,42,.045);
        }
        .cctv-head {
            min-height:40px;
            padding:0 12px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            border-bottom:1px solid var(--line);
            background:#fff;
        }
        .cctv-name { color:var(--navy); font-size:.84rem; font-weight:850; }
        .cctv-live {
            color:#166534;
            background:#ecfdf5;
            border:1px solid #bbf7d0;
            padding:3px 7px;
            border-radius:999px;
            font-size:.59rem;
            font-weight:850;
        }
        .cctv-foot {
            padding:7px 11px;
            color:#64748b;
            font-size:.68rem;
            border-top:1px solid var(--line);
            background:#fff;
        }
        .cctv-card + div { margin-top:0 !important; }

        @media (max-width:900px) {
            .brand-sub { display:none; }
            .app-header { left:52px; right:92px; height:3.25rem; padding:0 5px; }
            .block-container { padding-left:.75rem !important; padding-right:.75rem !important; padding-top:3.8rem !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def header():
    st.markdown(
        """
        <div class="app-header">
            <div class="brand">
                <div class="brand-icon">🚦</div>
                <div class="brand-name">ATS_INDIA</div>
            </div>
            <div class="brand-sub">Smart Adaptive Traffic System India · Live AI Traffic Monitoring & Emergency Priority</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
