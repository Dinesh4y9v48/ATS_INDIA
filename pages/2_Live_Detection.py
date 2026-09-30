import streamlit as st
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ats_core import DIRECTIONS, init_state, css, header, load_models

st.set_page_config(page_title="ATS_INDIA · Live Detection", page_icon="🚦", layout="wide", initial_sidebar_state="collapsed")
init_state(); css(); header()

if not st.session_state.configured:
    st.warning("System setup is required before live detection.")
    if st.button("← SYSTEM SETUP", use_container_width=True):
        st.switch_page("ATS_INDIA.py")
    st.stop()

try:
    load_models()
except Exception as exc:
    st.error("Model loading failed.")
    st.code(str(exc))
    st.stop()

a, b, c, d = st.columns(4, gap="small")
a.markdown('<div class="metric-card"><div class="metric-label">System</div><div class="metric-value" style="font-size:1.05rem">🟢 ONLINE</div><div class="metric-note">AI pipeline ready</div></div>', unsafe_allow_html=True)
b.markdown(f'<div class="metric-card"><div class="metric-label">Mode</div><div class="metric-value" style="font-size:1.05rem">{"🚨 EMERGENCY" if st.session_state.emergency_type else "🧠 ADAPTIVE"}</div><div class="metric-note">Priority logic active</div></div>', unsafe_allow_html=True)
c.markdown(f'<div class="metric-card"><div class="metric-label">Green direction</div><div class="metric-value" style="font-size:1.05rem">🟢 {st.session_state.green_direction}</div><div class="metric-note">{st.session_state.green_time}s allocation</div></div>', unsafe_allow_html=True)
d.markdown(f'<div class="metric-card"><div class="metric-label">Active CCTV</div><div class="metric-value" style="font-size:1.05rem">{len(st.session_state.sources)} / 4</div><div class="metric-note">Configured sources</div></div>', unsafe_allow_html=True)

x, y, z = st.columns([1, 1, 2], gap="small")
if x.button("▶ START", use_container_width=True):
    st.session_state.running = True
    st.rerun()
if y.button("■ STOP", use_container_width=True):
    st.session_state.running = False
    st.rerun()
if z.button("← BACK TO SETUP", use_container_width=True):
    st.session_state.running = False
    st.switch_page("ATS_INDIA.py")

st.markdown('<div class="section-head"><div><div class="section-title">Intersection Control</div><div class="section-sub">Adaptive signal state, emergency priority and current traffic demand.</div></div></div>', unsafe_allow_html=True)
sig, em, stat = st.columns([1.15, 1.35, 1], gap="medium")

with sig:
    st.markdown('<div class="panel"><div class="section-title" style="font-size:.95rem">🚦 Signal Status</div>', unsafe_allow_html=True)
    for direction in DIRECTIONS:
        active = direction == st.session_state.green_direction
        st.markdown(
            f'<div class="signal {"green" if active else "red"}"><span>{"🟢" if active else "🔴"} {direction}</span><span>{"GREEN" if active else "RED"}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="section-sub" style="margin-top:9px">Current green time: <b>{st.session_state.green_time}s</b></div></div>', unsafe_allow_html=True)

with em:
    st.markdown('<div class="panel"><div class="section-title" style="font-size:.95rem">🚨 Emergency Priority</div><div style="height:8px"></div>', unsafe_allow_html=True)
    if st.session_state.emergency_type:
        st.markdown(f'<div class="emergency-box"><b>{st.session_state.emergency_type.upper()}</b> DETECTED<br><br>Priority direction: <b>{st.session_state.emergency_direction}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="normal-box">🚑 Ambulance: <b>NO</b><br><br>🔥 Fire Truck: <b>NO</b></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with stat:
    st.markdown('<div class="panel"><div class="section-title" style="font-size:.95rem">📊 Traffic Statistics</div><div style="height:5px"></div>', unsafe_allow_html=True)
    for direction in DIRECTIONS:
        st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f1f5f9;font-size:.78rem"><span>{direction}</span><b>{st.session_state.counts.get(direction, 0)}</b></div>', unsafe_allow_html=True)
    maximum = max(st.session_state.counts.values()) if st.session_state.counts else 0
    level = "NO TRAFFIC" if maximum == 0 else "LOW" if maximum < 10 else "MEDIUM" if maximum < 25 else "HIGH"
    st.markdown(f'<div class="section-sub" style="margin-top:9px">Traffic level: <b>{level}</b></div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-head"><div><div class="section-title">📹 CCTV Monitoring</div><div class="section-sub">Open the dedicated 4-camera view for processed video feeds.</div></div></div>', unsafe_allow_html=True)
if st.button("OPEN 4 CCTV LIVE GRID  →", type="primary", use_container_width=True):
    st.switch_page("pages/3_CCTV_Grid.py")
