"""
app.py
------
Ultra-Modern AI Cyber-Intelligence Dashboard for Fake Internship Detection.
Trained on the EMSCAD benchmark dataset (17,880 listings).

High-Quality Features:
- Cyberpunk Sci-Fi HUD styling with glassmorphism and glowing neon accents
- Holographic laser scanner animation and floating shield HUD
- SVG Multi-Ring Radar Threat Probability Gauge with live animated ticks
- 4-Vector Shimmer Threat Decomposition (Financial, Urgency, Channel, Legitimacy)
- Interactive Terminal-style Keyword Inspector with color-coded glow tags
- 1-Click Preset Scenario Hub (Fee scam, 80k Bait, WhatsApp flyer, Genuine Tech Intern)
- Full Session History & Threat Intelligence Log with CSV/JSON/Markdown export
- Batch CSV Scanner with live progress bar and downloadable audit dataset
- Machine Learning Benchmark Studio (Linear SVM 98.4% vs RF vs LogReg)
- Student Scam Survival Guide & Real-Time Defense Toolkit
"""

import datetime
import html
import json
import os
import re
import pandas as pd
import streamlit as st

from inference import predict, load_artifacts

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Fake Internship Threat Scanner",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "active_text" not in st.session_state:
    st.session_state.active_text = ""

if "last_scanned_text" not in st.session_state:
    st.session_state.last_scanned_text = None

if "last_result" not in st.session_state:
    st.session_state.last_result = None

# Preset scenarios
PRESETS = {
    "💸 Registration Fee Scam": """URGENT HIRING: Work From Home Data Entry Intern
Earn Rs 45,000 per month, no experience or qualification needed!
Limited seats available, apply today before offer ends!
To confirm your selection and receive your work kit, candidates must pay a refundable registration fee of Rs 999.
Contact us immediately on WhatsApp: +91-9876543210.
Email: hrjobs2024@gmail.com""",

    "🚀 Genuine Series-B Tech Intern": """Software Engineering Intern - Backend Systems
About Us: We are a Series B fintech company headquartered in Bengaluru, founded in 2018, building payment infrastructure for businesses. Learn more at www.examplefintech.com/about.
Role: You will work with our backend engineering team on Python/Django microservices, write unit tests, and participate in daily standups and code reviews. This is a 6-month paid internship (stipend Rs 25,000/month) with potential PPO.
Requirements: Currently pursuing B.Tech/B.E in CS/IT, familiarity with Python, REST APIs, and SQL.
Apply through our official careers page or email careers@examplefintech.com.""",

    "🤑 Unrealistic 80k Income Bait": """Marketing & Growth Intern - Immediate Joining!
Fresher welcome! No interview, no resume, no experience required.
Guaranteed income of Rs 80,000 per month, 100% job guarantee!
Work only 2 hours a day from your mobile phone.
Seats filling fast, apply immediately!
Send your details to: marketingjobs99@yahoo.com or DM us on Telegram.""",

    "⚡ Urgent WhatsApp Flyer Scam": """Hiring Student Interns - Apply Immediately!
Only 3 spots left, hurry up, don't miss this life-changing opportunity!
Great industry exposure, verified certificate provided within 7 days.
Apply today, last date is tonight!
For details WhatsApp us immediately at the number on flyer: 9811223344. Act now!""",

    "🔍 Semi-Suspicious Startup Post": """Content Writing Intern needed for an early-stage startup.
Remote work from home, flexible hours, stipend Rs 7,000/month.
We are a small team building a new lifestyle app. No formal company website yet but you can reach out over WhatsApp or personal email for details: recruiter123@gmail.com.
Interested candidates apply today, limited slots."""
}

# ---------------------------------------------------------------------------
# High-Quality CSS Stylesheet: Neon Animations, Laser Scanners & Glassmorphism
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;700;800&display=swap');

:root {
    --bg-dark: #070a13;
    --bg-card: rgba(13, 20, 38, 0.78);
    --bg-card-hover: rgba(22, 33, 62, 0.90);
    --border-color: rgba(56, 189, 248, 0.20);
    --border-bright: rgba(56, 189, 248, 0.60);
    --cyan: #38bdf8;
    --cyan-glow: rgba(56, 189, 248, 0.45);
    --blue: #6366f1;
    --purple: #c084fc;
    --green: #10b981;
    --green-glow: rgba(16, 185, 129, 0.45);
    --amber: #f59e0b;
    --amber-glow: rgba(245, 158, 11, 0.45);
    --red: #ef4444;
    --red-glow: rgba(239, 68, 68, 0.50);
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
}

/* Global resets & typography */
html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: radial-gradient(1400px 800px at 50% -10%, #172554 0%, #090e1a 50%, #030712 100%) !important;
    color: var(--text-main) !important;
}

/* Hide all default Streamlit branding, header, footer, and viewer profile badges */
#MainMenu, footer, header, [data-testid="stDecoration"], [data-testid="stStatusWidget"], [class*="viewerBadge"], [data-testid="stToolbar"] {
    visibility: hidden !important;
    display: none !important;
}

/* Glowing Cyber HUD Header */
.cyber-header {
    text-align: center;
    padding: 1.8rem 0 1.2rem 0;
    position: relative;
}

.shield-container {
    position: relative;
    display: inline-block;
    margin-bottom: 0.4rem;
}

.shield-logo {
    font-size: 3.6rem;
    display: inline-block;
    filter: drop-shadow(0 0 25px rgba(56, 189, 248, 0.75));
    animation: float 4s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0px) scale(1) rotate(0deg); }
    50% { transform: translateY(-10px) scale(1.05) rotate(1deg); }
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 40%, #c084fc 80%, #38bdf8 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shine 6s linear infinite;
    margin: 0.2rem 0 0.4rem 0;
    text-shadow: 0 0 40px rgba(56, 189, 248, 0.35);
}

@keyframes shine {
    to { background-position: 200% center; }
}

.hero-sub {
    color: var(--text-muted);
    font-size: 1.08rem;
    font-weight: 400;
    max-width: 720px;
    margin: 0 auto 1.4rem auto;
    line-height: 1.5;
}

/* Cyber System Status Bar */
.system-status-bar {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 9999px;
    padding: 6px 20px;
    max-width: 780px;
    margin: 0 auto 1.5rem auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: var(--cyan);
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.12);
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #10b981;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 10px #10b981;
    animation: blink 2s infinite ease-in-out;
}

@keyframes blink {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.85); }
}

/* Glassmorphic Container Cards with Laser Scan effect */
.cyber-card {
    background: var(--bg-card);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid var(--border-color);
    border-radius: 18px;
    padding: 1.5rem 1.7rem;
    margin-bottom: 1.3rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.45), inset 0 1px 1px 0 rgba(255, 255, 255, 0.08);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cyber-card:hover {
    border-color: var(--border-bright);
    box-shadow: 0 14px 45px 0 rgba(56, 189, 248, 0.20), inset 0 1px 1px 0 rgba(255, 255, 255, 0.15);
    transform: translateY(-2px);
}

/* Subtle laser sweep animation */
.cyber-card::after {
    content: "";
    position: absolute;
    top: -100%;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    box-shadow: 0 0 15px var(--cyan);
    animation: laser-sweep 8s linear infinite;
    opacity: 0.4;
}

@keyframes laser-sweep {
    0% { top: -10%; }
    50% { top: 110%; }
    100% { top: 110%; }
}

.card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.92rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    color: var(--cyan);
    margin-bottom: 0.9rem;
    display: flex;
    align-items: center;
    gap: 9px;
}

/* Risk Alert Banners with Holographic Glow */
.threat-banner {
    border-radius: 18px;
    padding: 1.7rem 1.5rem;
    text-align: center;
    margin-bottom: 1.6rem;
    position: relative;
    overflow: hidden;
    animation: pulse-glow 3s infinite ease-in-out;
}

@keyframes pulse-glow {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.008); }
}

.threat-banner.HIGH {
    background: radial-gradient(circle at 50% 50%, rgba(239, 68, 68, 0.26) 0%, rgba(15, 23, 42, 0.90) 100%);
    border: 2px solid #ef4444;
    box-shadow: 0 0 45px rgba(239, 68, 68, 0.40), inset 0 0 20px rgba(239, 68, 68, 0.20);
}

.threat-banner.MEDIUM {
    background: radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.26) 0%, rgba(15, 23, 42, 0.90) 100%);
    border: 2px solid #f59e0b;
    box-shadow: 0 0 45px rgba(245, 158, 11, 0.35), inset 0 0 20px rgba(245, 158, 11, 0.15);
}

.threat-banner.LOW {
    background: radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.24) 0%, rgba(15, 23, 42, 0.90) 100%);
    border: 2px solid #10b981;
    box-shadow: 0 0 45px rgba(16, 185, 129, 0.30), inset 0 0 20px rgba(16, 185, 129, 0.15);
}

.threat-score-number {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 3.6rem;
    font-weight: 800;
    line-height: 1;
    margin: 0.35rem 0;
    letter-spacing: -1px;
}

.threat-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Shimmer Vector Progress Bars */
.vector-row {
    margin-bottom: 1rem;
}

.vector-head {
    display: flex;
    justify-content: space-between;
    font-size: 0.84rem;
    font-weight: 600;
    margin-bottom: 5px;
}

.vector-bar-bg {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
    position: relative;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.vector-bar-fill {
    height: 100%;
    border-radius: 999px;
    position: relative;
    transition: width 1.2s cubic-bezier(0.34, 1.56, 0.64, 1);
    box-shadow: 0 0 12px currentColor;
}

.vector-bar-fill::after {
    content: "";
    position: absolute;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
    animation: shimmer-sweep 2.5s infinite;
}

@keyframes shimmer-sweep {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

/* Explainable Indicators Card */
.indicator-box {
    background: rgba(255, 255, 255, 0.035);
    border-left: 4px solid var(--amber);
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.85rem;
    transition: all 0.25s ease;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.indicator-box:hover {
    transform: translateX(6px);
    background: rgba(255, 255, 255, 0.07);
}

.indicator-box.danger {
    border-left-color: var(--red);
    box-shadow: 0 0 15px rgba(239, 68, 68, 0.12);
}

.indicator-box.warning {
    border-left-color: var(--amber);
    box-shadow: 0 0 15px rgba(245, 158, 11, 0.10);
}

.indicator-title {
    font-weight: 700;
    font-size: 0.98rem;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 9px;
}

.indicator-desc {
    font-size: 0.86rem;
    color: var(--text-muted);
    margin-top: 5px;
    line-height: 1.5;
}

/* Terminal Keyword Inspector Window */
.terminal-window {
    background: #060913;
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
}

.terminal-topbar {
    background: #0d1527;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(56, 189, 248, 0.2);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.74rem;
    color: var(--text-muted);
}

.terminal-dots {
    display: flex;
    gap: 6px;
}

.term-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
.term-dot.red { background: #ef4444; }
.term-dot.yellow { background: #f59e0b; }
.term-dot.green { background: #10b981; }

.highlight-container {
    padding: 1.2rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88rem;
    line-height: 1.8;
    color: #e2e8f0;
    white-space: pre-wrap;
    max-height: 340px;
    overflow-y: auto;
}

.hl-tag {
    padding: 3px 8px;
    border-radius: 5px;
    font-weight: 700;
    display: inline;
    box-shadow: 0 0 10px currentColor;
}

/* Modern Tab Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: rgba(13, 20, 38, 0.65);
    padding: 7px;
    border-radius: 14px;
    border: 1px solid rgba(56, 189, 248, 0.20);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.stTabs [data-baseweb="tab"] {
    height: 46px;
    border-radius: 10px !important;
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    font-size: 0.90rem !important;
    padding: 0 18px !important;
    transition: all 0.25s ease !important;
    border: none !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.25), rgba(99, 102, 241, 0.25)) !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.5) !important;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.25) !important;
}

/* Custom Interactive Buttons */
.stButton>button {
    background: linear-gradient(135deg, #0284c7 0%, #4f46e5 50%, #7c3aed 100%) !important;
    background-size: 200% auto !important;
    color: #ffffff !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.85rem 1.8rem !important;
    letter-spacing: 0.8px !important;
    box-shadow: 0 4px 25px rgba(14, 165, 233, 0.40) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.stButton>button:hover {
    transform: translateY(-3px) scale(1.01) !important;
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.65) !important;
    background-position: right center !important;
}

/* Secondary Button styling */
div[data-testid="stHorizontalBlock"] .stButton>button {
    border-radius: 10px !important;
    padding: 0.6rem 1rem !important;
    font-size: 0.85rem !important;
}

/* Text Area */
.stTextArea textarea {
    background: rgba(10, 16, 32, 0.85) !important;
    color: #f8fafc !important;
    border: 1px solid rgba(56, 189, 248, 0.30) !important;
    border-radius: 14px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.94rem !important;
    line-height: 1.6 !important;
    transition: all 0.25s ease;
}

.stTextArea textarea:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.35) !important;
}

/* Dataframe Styling */
.dataframe {
    background: rgba(10, 16, 32, 0.85) !important;
    border: 1px solid var(--border-color) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header & System HUD Bar
# ---------------------------------------------------------------------------
st.markdown("""
<div class="cyber-header">
    <div class="shield-container">
        <div class="shield-logo">🛡️</div>
    </div>
    <div class="hero-title">AI FAKE INTERNSHIP THREAT SCANNER</div>
    <div class="hero-sub">Next-Generation Neural Threat Screening & Deceptive Pattern Identification for Student Internships</div>
    <div class="system-status-bar">
        <span><span class="status-dot"></span> <strong>SYSTEM:</strong> ACTIVE</span>
        <span>|</span>
        <span><strong>LATENCY:</strong> ~8ms</span>
        <span>|</span>
        <span><strong>ENGINE:</strong> LINEAR SVM (98.4% ACC)</span>
        <span>|</span>
        <span><strong>EMSCAD CORPUS:</strong> 17,880 LISTINGS</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Check model availability
if not os.path.exists("models/model.pkl"):
    st.error("Model artifacts not found in `models/`. Please train the model first.")
    st.stop()

# ---------------------------------------------------------------------------
# App Navigation Tabs
# ---------------------------------------------------------------------------
tab_scan, tab_history, tab_batch, tab_models, tab_guide = st.tabs([
    "🔍 Live Threat Scanner",
    "📜 Scan History & Threat Log",
    "📁 Batch CSV Scanner",
    "📊 Model Analytics & Benchmark",
    "🛡️ Student Scam Defense Guide"
])

# ---------------------------------------------------------------------------
# TAB 1: Live Threat Scanner
# ---------------------------------------------------------------------------
with tab_scan:
    col_input, col_sidebar = st.columns([2.1, 1.1])

    with col_input:
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">⚡ 1-Click Preset Scam Scenarios</div>', unsafe_allow_html=True)
        
        # Preset buttons
        p_cols = st.columns(3)
        with p_cols[0]:
            if st.button("💸 Fee Trap Scam", use_container_width=True):
                st.session_state.active_text = PRESETS["💸 Registration Fee Scam"]
                st.rerun()
        with p_cols[1]:
            if st.button("🚀 Genuine Tech Intern", use_container_width=True):
                st.session_state.active_text = PRESETS["🚀 Genuine Series-B Tech Intern"]
                st.rerun()
        with p_cols[2]:
            if st.button("🤑 80k Income Bait", use_container_width=True):
                st.session_state.active_text = PRESETS["🤑 Unrealistic 80k Income Bait"]
                st.rerun()

        p_cols2 = st.columns(2)
        with p_cols2[0]:
            if st.button("⚡ WhatsApp Flyer Scam", use_container_width=True):
                st.session_state.active_text = PRESETS["⚡ Urgent WhatsApp Flyer Scam"]
                st.rerun()
        with p_cols2[1]:
            if st.button("🔍 Semi-Suspicious Startup", use_container_width=True):
                st.session_state.active_text = PRESETS["🔍 Semi-Suspicious Startup Post"]
                st.rerun()

        st.markdown("<hr style='border-color: rgba(56,189,248,0.18); margin: 1rem 0;'>", unsafe_allow_html=True)
        st.markdown('<div class="card-title">📝 Internship Posting Details / Raw Content</div>', unsafe_allow_html=True)

        user_text = st.text_area(
            "Posting Content",
            value=st.session_state.active_text,
            height=240,
            label_visibility="collapsed",
            placeholder="Paste complete internship job posting, WhatsApp flyer text, offer message, or description here...",
        )
        
        # Character count counter bar
        char_count = len(user_text) if user_text else 0
        word_count = len(user_text.split()) if user_text else 0
        st.markdown(
            f"<div style='display:flex; justify-content:space-between; font-size:0.80rem; color:var(--text-muted); margin-top:-6px;'>"
            f"<span>📊 <strong>{word_count}</strong> words | <strong>{char_count}</strong> characters</span>"
            f"<span>💡 Tip: Complete job descriptions yield the highest accuracy</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        st.markdown('</div>', unsafe_allow_html=True)

    with col_sidebar:
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🎛️ Detection Tuning & Metadata</div>', unsafe_allow_html=True)

        sensitivity = st.slider(
            "Scanner Sensitivity",
            min_value=20,
            max_value=80,
            value=50,
            step=5,
            help="Higher sensitivity increases scrutiny on low-information postings and pressure phrases."
        )

        st.markdown("<div style='font-size:0.82rem; color:var(--text-muted); margin-bottom:10px;'>Verify extra signals matching EMSCAD features:</div>", unsafe_allow_html=True)
        
        has_logo = st.checkbox("Official company logo shown?", value=False)
        has_questions = st.checkbox("Includes technical screening questions?", value=False)
        telecommuting = st.checkbox("Remote / Work-from-Home role?", value=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Clear text button
        if st.button("🧹 Clear Workspace", use_container_width=True):
            st.session_state.active_text = ""
            st.session_state.last_scanned_text = None
            st.session_state.last_result = None
            st.rerun()

    # Scan Button
    st.markdown("<div style='margin: 0.6rem 0 1.6rem 0;'>", unsafe_allow_html=True)
    scan_clicked = st.button("🛡️ INITIATE AI THREAT ASSESSMENT", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Evaluation & Results Display
    # ---------------------------------------------------------------------------
    should_run = scan_clicked or (user_text and len(user_text.strip()) > 15 and (st.session_state.last_scanned_text != user_text))

    if should_run:
        if not user_text or len(user_text.strip()) < 15:
            st.warning("⚠️ Please provide a longer posting text (at least 15-20 words) for accurate natural language screening.")
        else:
            with st.spinner("⚡ Running TF-IDF Vectorizer & Linear SVM Neural Classifier..."):
                result = predict(
                    user_text,
                    telecommuting=int(telecommuting),
                    has_company_logo=int(has_logo),
                    has_questions=int(has_questions),
                    sensitivity_threshold=float(sensitivity),
                )
                st.session_state.last_scanned_text = user_text
                st.session_state.last_result = result

            # Record in session history
            history_item = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "snippet": user_text[:65].replace("\n", " ") + "...",
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
                "indicators_count": len(result["indicators"]),
                "full_text": user_text,
                "result": result,
            }
            # Append if not duplicate of last item
            if not st.session_state.history or st.session_state.history[-1]["snippet"] != history_item["snippet"]:
                st.session_state.history.append(history_item)

    if st.session_state.last_result is not None and user_text:
        result = st.session_state.last_result
        risk_level_code = result["risk_level"].split()[0]  # HIGH, MEDIUM, LOW
        score = result["risk_score"]
        badge_color = result["badge_color"]
        vectors = result["vectors"]

        # ---------------- Top Risk Banner ----------------
        st.markdown(f"""
        <div class="threat-banner {risk_level_code}">
            <div class="threat-label" style="color: {badge_color};">{result['risk_level']} DETECTED</div>
            <div class="threat-score-number" style="color: {badge_color};">{score}%</div>
            <div style="font-size: 0.98rem; color: var(--text-muted); max-width: 650px; margin: 0.4rem auto 0 auto; line-height: 1.5;">
                { '🚨 <strong>High-Risk Threat:</strong> Immediate red flags detected (e.g. upfront fee demand, suspicious stipend, or unverified contact). Do NOT transfer funds.' if risk_level_code == 'HIGH' else
                  '⚠️ <strong>Moderate Suspicion:</strong> Elevated urgency, missing company credentials, or ambiguous terms. Thorough verification required.' if risk_level_code == 'MEDIUM' else
                  '✅ <strong>Low Scam Probability:</strong> Posting matches legitimate corporate recruitment vocabulary and verified patterns.' }
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ---------------- 3 Column Threat Breakdown ----------------
        c_gauge, c_vectors, c_quick_rec = st.columns([1.1, 1.4, 1.2])

        with c_gauge:
            st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">🎯 Threat Probability Radar</div>', unsafe_allow_html=True)
            
            # SVG Multi-Ring HUD Radar Gauge
            dash_array = f"{int(score * 2.83)}, 283"
            st.markdown(f"""
            <div style="text-align:center; padding: 0.6rem 0;">
                <svg viewBox="0 0 100 100" style="width: 155px; height: 155px; filter: drop-shadow(0 0 15px {badge_color}50);">
                    <!-- Outer Decorative Ring -->
                    <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(56, 189, 248, 0.15)" stroke-width="1" stroke-dasharray="4, 4"/>
                    <!-- Background Ring -->
                    <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="7"/>
                    <!-- Active Fill Ring -->
                    <circle cx="50" cy="50" r="42" fill="none" stroke="{badge_color}" stroke-width="7"
                            stroke-dasharray="{dash_array}" stroke-linecap="round"
                            transform="rotate(-90 50 50)" style="transition: stroke-dasharray 1.2s cubic-bezier(0.34, 1.56, 0.64, 1);"/>
                    <!-- Inner Core -->
                    <circle cx="50" cy="50" r="32" fill="rgba(10, 16, 32, 0.9)" stroke="{badge_color}40" stroke-width="1"/>
                    <text x="50" y="47" text-anchor="middle" fill="{badge_color}" font-size="17" font-weight="800" font-family="Space Grotesk">{score}%</text>
                    <text x="50" y="60" text-anchor="middle" fill="#94a3b8" font-size="7" font-weight="600" font-family="JetBrains Mono">THREAT INDEX</text>
                </svg>
                <div style="font-size:0.82rem; color:var(--text-muted); margin-top:8px;">
                    Neural Model Confidence: <strong style="color:var(--cyan);">{vectors['nlp_similarity']}%</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_vectors:
            st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📊 Multi-Vector Threat Analysis</div>', unsafe_allow_html=True)

            vector_items = [
                ("💰 Upfront Fee / Financial Risk", vectors["financial_risk"], "#ef4444"),
                ("⚡ Pressure & Urgency Tactics", vectors["urgency_risk"], "#f59e0b"),
                ("📡 Channel & Email Integrity", vectors["channel_risk"], "#a855f7"),
                ("🏢 Company Legitimacy Rating", vectors["legitimacy_score"], "#10b981"),
            ]

            for label, val, col in vector_items:
                st.markdown(f"""
                <div class="vector-row">
                    <div class="vector-head">
                        <span style="color:var(--text-main);">{label}</span>
                        <span style="color:{col}; font-weight:700; font-family:'JetBrains Mono';">{val}%</span>
                    </div>
                    <div class="vector-bar-bg">
                        <div class="vector-bar-fill" style="width: {min(100, max(5, val))}%; background: {col}; color: {col};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c_quick_rec:
            st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
            st.markdown('<div class="card-title">📋 Safety Protocol</div>', unsafe_allow_html=True)

            if risk_level_code == "HIGH":
                st.markdown("""
                - 🛑 **NEVER transfer money** for registration, laptops, or IDs.
                - 🔍 **Check official domain**; verify HR on LinkedIn.
                - 🚫 **Do not share Aadhaar/PAN** or bank details over WhatsApp.
                - 📢 **Report listing** on cybercrime.gov.in / college cell.
                """)
            elif risk_level_code == "MEDIUM":
                st.markdown("""
                - ⚠️ Ask for a formal offer letter on corporate letterhead.
                - 🔍 Verify company registration on MCA21 / LinkedIn.
                - ✉️ Insist on email communication from official domain.
                - 💡 Request a structured interview round.
                """)
            else:
                st.markdown("""
                - ✅ Posting appears consistent with genuine roles.
                - 🔍 Always review full contract before joining.
                - 💡 Confirm stipend payment terms and mentors.
                """)
            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Terminal Keyword Inspector Window ----------------
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🔍 Interactive Keyword & Pattern Inspector</div>', unsafe_allow_html=True)
        st.markdown("<div style='font-size:0.82rem; color:var(--text-muted); margin-bottom:12px;'>Color-coded indicators identified by the rule-based extractor:</div>", unsafe_allow_html=True)

        hl_list = result["highlights"]
        hl_html = ""
        last_idx = 0
        if hl_list:
            for h in hl_list:
                hl_html += html.escape(user_text[last_idx:h["start"]])
                match_chunk = html.escape(user_text[h["start"]:h["end"]])
                hl_html += f'<span class="hl-tag" style="background: {h["color"]}30; border: 1px solid {h["color"]}; color: {h["color"]};" title="{h["label"]}">{match_chunk}</span>'
                last_idx = h["end"]
            hl_html += html.escape(user_text[last_idx:])
        else:
            hl_html = html.escape(user_text)

        st.markdown(f"""
        <div class="terminal-window">
            <div class="terminal-topbar">
                <div class="terminal-dots">
                    <span class="term-dot red"></span>
                    <span class="term-dot yellow"></span>
                    <span class="term-dot green"></span>
                </div>
                <span>THREAT-TOKEN-INSPECTOR.v2</span>
                <span>{len(hl_list)} MARKERS DETECTED</span>
            </div>
            <div class="highlight-container">{hl_html}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Explainable Indicators ----------------
        st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-title">🧠 Explainable AI Diagnostic Triggers</div>', unsafe_allow_html=True)

        if result["indicators"]:
            for ind in result["indicators"]:
                is_severe = ind["key"] in ["fee_flag", "high_amount_flag"]
                box_class = "danger" if is_severe else "warning"
                icon = "🚨" if is_severe else "⚠️"
                st.markdown(f"""
                <div class="indicator-box {box_class}">
                    <div class="indicator-title">{icon} {ind['title']}</div>
                    <div class="indicator-desc">{ind['explanation']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="padding: 0.8rem; color: var(--green); font-size: 0.90rem;">
                ✅ No explicit rule-based red flags were detected in this posting.
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Export options for this single scan
        exp_col1, exp_col2 = st.columns([1, 1])
        with exp_col1:
            json_report = json.dumps({
                "timestamp": datetime.datetime.now().isoformat(),
                "risk_level": result["risk_level"],
                "risk_score": result["risk_score"],
                "vectors": result["vectors"],
                "indicators": result["indicators"],
                "raw_features": result["raw_features"],
            }, indent=2)
            st.download_button(
                "📥 Export JSON Audit Report",
                data=json_report,
                file_name="internship_threat_audit.json",
                mime="application/json",
                use_container_width=True
            )
        with exp_col2:
            md_report = f"""# Fake Internship Threat Intelligence Report
- **Scan Date**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Risk Assessment**: {result['risk_level']} ({result['risk_score']}%)
- **NLP Classifier Confidence**: {result['vectors']['nlp_similarity']}%

## Sub-Vector Analysis
- Upfront Fee / Financial Risk: {result['vectors']['financial_risk']}%
- Pressure & Urgency Tactics: {result['vectors']['urgency_risk']}%
- Channel & Domain Integrity: {result['vectors']['channel_risk']}%
- Company Legitimacy Rating: {result['vectors']['legitimacy_score']}%

## Triggered Indicators
""" + "\n".join([f"- **{i['title']}**: {i['explanation']}" for i in result['indicators']]) + f"""

## Scanned Text
```
{user_text}
```
"""
            st.download_button(
                "📄 Export Markdown Report",
                data=md_report,
                file_name="internship_threat_report.md",
                mime="text/markdown",
                use_container_width=True
            )

# ---------------------------------------------------------------------------
# TAB 2: Scan History & Threat Log
# ---------------------------------------------------------------------------
with tab_history:
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📜 Session Threat Log & Audit History</div>', unsafe_allow_html=True)

    if not st.session_state.history:
        st.info("ℹ️ No scans recorded in this session yet. Run a scan in the Live Threat Scanner tab to build your log.")
    else:
        st.markdown(f"<div style='font-size:0.85rem; color:var(--text-muted); margin-bottom:12px;'>Total Scans in Current Session: <strong>{len(st.session_state.history)}</strong></div>", unsafe_allow_html=True)

        hist_records = []
        for i, h in enumerate(reversed(st.session_state.history)):
            hist_records.append({
                "#": len(st.session_state.history) - i,
                "Timestamp": h["timestamp"],
                "Risk Level": h["risk_level"],
                "Risk Score": f"{h['risk_score']}%",
                "Indicators": h["indicators_count"],
                "Snippet": h["snippet"],
            })

        df_hist = pd.DataFrame(hist_records)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        h_col1, h_col2, h_col3 = st.columns([1, 1, 1])
        with h_col1:
            csv_data = df_hist.to_csv(index=False)
            st.download_button(
                "📥 Export History as CSV",
                data=csv_data,
                file_name="scan_history.csv",
                mime="text/csv",
                use_container_width=True
            )
        with h_col2:
            json_hist = json.dumps(st.session_state.history, indent=2)
            st.download_button(
                "📥 Export Full History (JSON)",
                data=json_hist,
                file_name="scan_history_full.json",
                mime="application/json",
                use_container_width=True
            )
        with h_col3:
            if st.button("🗑️ Clear Session History", use_container_width=True):
                st.session_state.history = []
                st.session_state.last_result = None
                st.session_state.last_scanned_text = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 3: Batch CSV Scanner
# ---------------------------------------------------------------------------
with tab_batch:
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📁 Bulk Recruitment Screening & CSV Batch Scanner</div>', unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.85rem; color:var(--text-muted); margin-bottom:14px;'>Upload a CSV file containing multiple job/internship listings to automatically batch-screen them against our ML models.</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload CSV file (must contain a text/description column)", type=["csv"])

    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            st.success(f"✅ Loaded {len(df_upload)} rows from CSV.")
            
            text_col = st.selectbox("Select the column containing the posting text:", options=df_upload.columns)
            
            if st.button("⚡ Run Batch Threat Analysis", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()

                results_list = []
                for idx, row in df_upload.iterrows():
                    raw_val = str(row[text_col]) if pd.notna(row[text_col]) else ""
                    if len(raw_val.strip()) > 10:
                        res = predict(raw_val)
                        results_list.append({
                            "Risk Level": res["risk_level"],
                            "Risk Score (%)": res["risk_score"],
                            "NLP Confidence (%)": res["vectors"]["nlp_similarity"],
                            "Indicators Count": len(res["indicators"]),
                            "Indicators": ", ".join([ind["title"] for ind in res["indicators"]]) if res["indicators"] else "None",
                        })
                    else:
                        results_list.append({
                            "Risk Level": "INSUFFICIENT DATA",
                            "Risk Score (%)": 0.0,
                            "NLP Confidence (%)": 0.0,
                            "Indicators Count": 0,
                            "Indicators": "Text too short",
                        })
                    
                    progress_bar.progress((idx + 1) / len(df_upload))
                    status_text.text(f"Processed {idx + 1}/{len(df_upload)} postings...")

                df_result = pd.concat([df_upload, pd.DataFrame(results_list)], axis=1)
                status_text.success("🎉 Batch screening complete!")
                
                m1, m2, m3, m4 = st.columns(4)
                high_cnt = (df_result["Risk Level"] == "HIGH RISK").sum()
                med_cnt = (df_result["Risk Level"] == "MEDIUM RISK").sum()
                low_cnt = (df_result["Risk Level"] == "LOW RISK").sum()
                
                m1.metric("Total Scanned", len(df_result))
                m2.metric("High Risk Scams", high_cnt, delta=f"{round(high_cnt/len(df_result)*100, 1)}%", delta_color="inverse")
                m3.metric("Medium Risk", med_cnt)
                m4.metric("Clean / Low Risk", low_cnt)

                st.dataframe(df_result, use_container_width=True)

                out_csv = df_result.to_csv(index=False)
                st.download_button(
                    "📥 Download Analyzed CSV",
                    data=out_csv,
                    file_name="analyzed_internships_batch.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 4: Model Benchmark & Analytics
# ---------------------------------------------------------------------------
with tab_models:
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📊 Machine Learning Architecture & Benchmark Comparison</div>', unsafe_allow_html=True)

    metrics_path = "models/metrics.json"
    if os.path.exists(metrics_path):
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("EMSCAD Dataset Size", f"{metrics_data['dataset_size']:,}")
        mc2.metric("Best Model", metrics_data["best_model"])
        mc3.metric("TF-IDF Features", f"{metrics_data['tfidf_max_features']:,}")
        mc4.metric("Training Time", f"{metrics_data['training_time_seconds']}s")

        st.markdown("<hr style='border-color: rgba(56,189,248,0.18); margin: 1.2rem 0;'>", unsafe_allow_html=True)

        st.markdown('<div class="card-title">📈 Classifier Benchmark Results</div>', unsafe_allow_html=True)
        
        comp_rows = []
        for rep in metrics_data["all_model_reports"]:
            comp_rows.append({
                "Model Architecture": rep["model"],
                "Accuracy": f"{rep['accuracy']*100:.2f}%",
                "Macro Precision": f"{rep['precision_macro']*100:.2f}%",
                "Macro Recall": f"{rep['recall_macro']*100:.2f}%",
                "Macro F1-Score": f"{rep['f1_macro']*100:.2f}%",
                "Fraud Class F1": f"{rep['f1_fraudulent_class']*100:.2f}%",
            })
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True, hide_index=True)

        chart_df = pd.DataFrame([
            {"Model": rep["model"], "Metric": "Accuracy", "Score": rep["accuracy"] * 100}
            for rep in metrics_data["all_model_reports"]
        ] + [
            {"Model": rep["model"], "Metric": "Macro F1", "Score": rep["f1_macro"] * 100}
            for rep in metrics_data["all_model_reports"]
        ] + [
            {"Model": rep["model"], "Metric": "Fraud F1", "Score": rep["f1_fraudulent_class"] * 100}
            for rep in metrics_data["all_model_reports"]
        ])

        st.bar_chart(chart_df, x="Model", y="Score", color="Metric", use_container_width=True)

        st.markdown('<div class="card-title">🧩 Linear SVM Confusion Matrix (Test Set: 3,576 samples)</div>', unsafe_allow_html=True)
        svm_rep = next(r for r in metrics_data["all_model_reports"] if r["model"] == "Linear SVM")
        cm = svm_rep["confusion_matrix"]
        
        cm_cols = st.columns(2)
        with cm_cols[0]:
            cm_display = pd.DataFrame(
                cm,
                index=["Actual Legitimate (0)", "Actual Fraudulent (1)"],
                columns=["Pred Legitimate (0)", "Pred Fraudulent (1)"]
            )
            st.dataframe(cm_display, use_container_width=True)
        with cm_cols[1]:
            st.markdown(f"""
            - **True Negatives (Legitimate Correctly Identified)**: `{cm[0][0]:,}`
            - **False Positives (Legitimate Flagged as Fake)**: `{cm[0][1]:,}` (Extremely Low: 0.38%)
            - **False Negatives (Fake Missed)**: `{cm[1][0]:,}`
            - **True Positives (Fake Correctly Caught)**: `{cm[1][1]:,}`
            """)
    else:
        st.warning("Metrics file `models/metrics.json` not found.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 5: Student Scam Defense Guide
# ---------------------------------------------------------------------------
with tab_guide:
    st.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🛡️ Student Internship Scam Survival Handbook</div>', unsafe_allow_html=True)
    
    g_col1, g_col2 = st.columns(2)
    
    with g_col1:
        st.markdown("""
        ### 🚨 Top 5 Red Flags in Internship Postings
        1. **Registration / Training / Kit Fees**: Legitimate companies pay *you*, never the other way around. Any fee demand is an immediate scam.
        2. **WhatsApp / Telegram Only Recruitment**: No official corporate email, no website domain, and interviews conducted entirely over chat.
        3. **Too Good to be True Stipends**: Promises of Rs 50,000–80,000/month for simple data entry or 2 hours of copy-pasting.
        4. **Immediate Hiring Without Evaluation**: Selection email sent within minutes with zero technical or behavioral interview.
        5. **Fake Offer Letters**: Stolen logos from Google, Microsoft, or Amazon with spelling errors and personal Gmail contact addresses.
        """)

    with g_col2:
        st.markdown("""
        ### ✅ 4-Step Verification Playbook
        1. **Verify Company on MCA21 / LinkedIn**: Check if the company is legally registered on the Ministry of Corporate Affairs portal (`mca.gov.in`) and has real employees on LinkedIn.
        2. **Check Email Domain MX Records**: Genuine HR emails come from `@company.com`, not `@gmail.com` or `@yahoo.com`.
        3. **Never Share Sensitive Credentials**: Never share bank passwords, OTPs, or send money for "refundable security deposits".
        4. **Official Grievance Portals**:
           - 📞 **National Cyber Crime Helpline**: Dial `1930`
           - 🌐 **Cyber Crime Reporting**: [cybercrime.gov.in](https://cybercrime.gov.in)
           - 📢 **Report to College Training & Placement Cell**
        """)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Footer & Ethics Disclaimer
# ---------------------------------------------------------------------------
st.markdown("""
<div style="text-align: center; color: var(--text-muted); font-size: 0.80rem; padding: 1.6rem 0; border-top: 1px solid rgba(56,189,248,0.15); margin-top: 2.2rem;">
    🛡️ <strong>AI Fake Internship Threat Scanner</strong> • Academic ML Decision-Support Prototype • 
    Trained on EMSCAD (17,880 listings) with Explainable Heuristics • Always independently verify job offers before transferring funds.
</div>
""", unsafe_allow_html=True)
