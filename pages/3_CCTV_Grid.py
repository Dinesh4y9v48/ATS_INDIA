import streamlit as st
from pathlib import Path
import sys, cv2, tempfile, time
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ats_core import DIRECTIONS, init_state, css, header, load_models, analyze_frame, choose_signal

st.set_page_config(page_title="ATS_INDIA · CCTV Grid", page_icon="📹", layout="wide", initial_sidebar_state="collapsed")
init_state(); css(); header()

if not st.session_state.configured or not st.session_state.sources:
    st.warning("System setup is required before opening the CCTV grid.")
    if st.button("← SYSTEM SETUP", use_container_width=True):
        st.switch_page("ATS_INDIA.py")
    st.stop()

try:
    traffic_model, emergency_model = load_models()
except Exception as exc:
    st.error("Model loading failed.")
    st.code(str(exc))
    st.stop()

nav = st.columns([1, 5])
with nav[0]:
    if st.button("← LIVE DETECTION", use_container_width=True):
        st.session_state.running = False
        st.switch_page("pages/2_Live_Detection.py")

st.markdown('<div class="section-head"><div><div class="section-title">4-Camera Live Grid</div><div class="section-sub">NORTH · EAST · SOUTH · WEST · YOLO + ByteTrack processing</div></div><div class="live-pill"><span class="live-dot"></span>LIVE PROCESSING</div></div>', unsafe_allow_html=True)

# Each Streamlit column owns its complete card, so heading, video and status always share one width.
row1 = st.columns(2, gap="medium")
row2 = st.columns(2, gap="medium")
slot = {"NORTH": row1[0], "EAST": row1[1], "SOUTH": row2[0], "WEST": row2[1]}

ph, status_ph = {}, {}
for direction in DIRECTIONS:
    with slot[direction]:
        st.markdown(
            f'<div class="cctv-card"><div class="cctv-head"><span class="cctv-name">📹 {direction} CCTV</span><span class="cctv-live">● LIVE</span></div></div>',
            unsafe_allow_html=True,
        )
        ph[direction] = st.empty()
        status_ph[direction] = st.empty()

caps, temps, snapshots = {}, {}, {}
try:
    for direction in DIRECTIONS:
        source = st.session_state.sources.get(direction)
        if not source:
            continue
        if source["type"] == "video":
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(source.get("name", "video.mp4")).suffix or ".mp4")
            tmp.write(source["data"])
            tmp.close()
            temps[direction] = Path(tmp.name)
            cap = cv2.VideoCapture(tmp.name)
            if cap.isOpened():
                caps[direction] = cap
        elif source["type"] == "rtsp":
            cap = cv2.VideoCapture(source["url"])
            if cap.isOpened():
                caps[direction] = cap
        elif source["type"] == "snapshot":
            array = np.frombuffer(source["data"], dtype=np.uint8)
            frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
            if frame is not None:
                snapshots[direction] = frame

    if not caps and not snapshots:
        st.error("No valid CCTV source is available.")
        st.stop()

    st.session_state.running = True
    while st.session_state.running:
        counts = {direction: 0 for direction in DIRECTIONS}
        emergency_type = None
        emergency_direction = None

        for direction in DIRECTIONS:
            cap = caps.get(direction)
            if cap is None:
                continue

            ok, frame = cap.read()
            if not ok and st.session_state.sources[direction]["type"] == "video":
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()

            if not ok or frame is None:
                with slot[direction]:
                    status_ph[direction].markdown('<div class="cctv-foot">⚠️ Unable to read frame</div>', unsafe_allow_html=True)
                continue

            output, number, detected = analyze_frame(
                traffic_model,
                emergency_model,
                frame,
                st.session_state.vehicle_conf,
                st.session_state.emergency_conf,
            )
            counts[direction] = number
            if detected and emergency_type is None:
                emergency_type, emergency_direction = detected, direction

            rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            with slot[direction]:
                ph[direction].image(rgb, channels="RGB", width="stretch")
                status_ph[direction].markdown(
                    f'<div class="cctv-foot">🟢 LIVE &nbsp;·&nbsp; 🚗 {number} vehicles'
                    + (f' &nbsp;·&nbsp; 🚨 {detected.upper()}' if detected else '')
                    + '</div>',
                    unsafe_allow_html=True,
                )

        for direction, frame in snapshots.items():
            output, number, detected = analyze_frame(
                traffic_model,
                emergency_model,
                frame,
                st.session_state.vehicle_conf,
                st.session_state.emergency_conf,
            )
            counts[direction] = number
            if detected and emergency_type is None:
                emergency_type, emergency_direction = detected, direction
            rgb = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            with slot[direction]:
                ph[direction].image(rgb, channels="RGB", width="stretch")
                status_ph[direction].markdown(
                    f'<div class="cctv-foot">📷 SNAPSHOT &nbsp;·&nbsp; 🚗 {number} vehicles'
                    + (f' &nbsp;·&nbsp; 🚨 {detected.upper()}' if detected else '')
                    + '</div>',
                    unsafe_allow_html=True,
                )

        green, seconds = choose_signal(counts, emergency_direction)
        st.session_state.counts = counts
        st.session_state.green_direction = green
        st.session_state.green_time = seconds
        st.session_state.emergency_type = emergency_type
        st.session_state.emergency_direction = emergency_direction

        if not caps:
            break
        time.sleep(0.06)
except Exception as exc:
    st.error("CCTV grid error.")
    st.exception(exc)
finally:
    for cap in caps.values():
        cap.release()
    for path in temps.values():
        try:
            path.unlink()
        except Exception:
            pass
