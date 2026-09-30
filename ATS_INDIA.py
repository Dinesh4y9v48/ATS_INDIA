import streamlit as st
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ats_core import DIRECTIONS, init_state, css, header

st.set_page_config(
    page_title="ATS_INDIA",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed",
)
init_state()
css()
header()

st.markdown(
    '<div class="section-head"><div><div class="section-title">Configure Traffic Monitoring</div><div class="section-sub">Connect each direction to a video upload, browser camera, or continuous IP / RTSP CCTV source.</div></div></div>',
    unsafe_allow_html=True,
)

selected = {}
rows = [st.columns(2, gap="medium"), st.columns(2, gap="medium")]
cols = {"NORTH": rows[0][0], "EAST": rows[0][1], "SOUTH": rows[1][0], "WEST": rows[1][1]}

for direction in DIRECTIONS:
    with cols[direction]:
        st.markdown(
            f'<div class="panel"><div class="source-head"><span class="source-title">📹 {direction} CCTV</span><span class="source-badge">SOURCE {direction}</span></div>',
            unsafe_allow_html=True,
        )
        mode = st.radio(
            f"{direction} source",
            ["🎥 Video Upload", "📷 Browser Camera", "🌐 IP / RTSP CCTV"],
            horizontal=True,
            key=f"mode_{direction}",
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if mode == "🎥 Video Upload":
            file = st.file_uploader(
                f"{direction} traffic video",
                type=["mp4", "avi", "mov", "mkv"],
                key=f"upload_{direction}",
            )
            if file:
                selected[direction] = {"type": "video", "data": file.getvalue(), "name": file.name}
                st.success(file.name, icon="🎥")
            else:
                st.info("Choose a traffic video to continue.")
        elif mode == "📷 Browser Camera":
            camera = st.camera_input(f"{direction} camera", key=f"cam_{direction}")
            if camera:
                selected[direction] = {"type": "snapshot", "data": camera.getvalue(), "name": f"{direction}_camera.jpg"}
                st.success("Camera frame selected", icon="📷")
            else:
                st.info("Browser Camera works as a snapshot source.")
        else:
            url = st.text_input(
                f"{direction} RTSP / IP URL",
                placeholder="rtsp://user:password@192.168.1.101:554/stream",
                key=f"rtsp_{direction}",
            )
            if url.strip():
                selected[direction] = {"type": "rtsp", "url": url.strip(), "name": "RTSP CCTV"}
                st.success("RTSP source configured", icon="🌐")
            else:
                st.info("Paste the camera RTSP / IP stream URL.")

st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
config, summary = st.columns([2.2, 1], gap="medium")
with config:
    st.markdown(
        '<div class="section-title">AI Configuration</div><div class="section-sub">Detection confidence controls for the traffic and emergency models.</div>',
        unsafe_allow_html=True,
    )
    st.session_state.vehicle_conf = st.slider("Vehicle confidence", 0.20, 0.80, st.session_state.vehicle_conf, 0.05)
    st.session_state.emergency_conf = st.slider("Emergency confidence", 0.20, 0.90, st.session_state.emergency_conf, 0.05)
with summary:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">CCTV sources selected</div><div class="metric-value">{len(selected)} / 4</div><div class="metric-note">RTSP recommended for continuous physical CCTV.</div></div>',
        unsafe_allow_html=True,
    )

if st.button("🚀 COMPLETE SETUP  →  LIVE DETECTION", type="primary", use_container_width=True):
    if not selected:
        st.error("Select at least one CCTV source.")
    else:
        st.session_state.sources = selected
        st.session_state.configured = True
        st.session_state.running = True
        if (ROOT / "pages" / "2_Live_Detection.py").exists():
            st.switch_page("pages/2_Live_Detection.py")
        else:
            st.error("pages/2_Live_Detection.py is missing.")
