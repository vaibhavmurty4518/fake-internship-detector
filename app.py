"""
app.py
------
AI Fake Internship Threat Scanner - Review 3 Stage 2 Upgrade
Premium Warm AI Security Dashboard
Theme: Cream + Espresso Brown + Deep Maroon + Muted Gold + Glassmorphism
"""

import datetime
import html
import json
import os
import re
import pandas as pd
import streamlit as st

from inference import predict, load_artifacts, extract_text_from_file

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
    "🚨 Upfront Registration Fee Scam": """URGENT HIRING: Work From Home Data Entry Intern
Earn Rs 45,000 per month, no experience or qualification needed!
Limited seats available, apply today before offer ends!
To confirm your selection and receive your work kit, candidates must pay a refundable registration fee of Rs 999.
Contact us immediately on WhatsApp: +91-9876543210.
Email: hrjobs2024@gmail.com""",

    "🚀 Genuine Tech Company Posting": """Software Engineering Intern - Backend Systems
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

    "⚡ Urgent WhatsApp Contact Flyer": """Hiring Student Interns - Apply Immediately!
Only 3 spots left, hurry up, don't miss this life-changing opportunity!
Great industry exposure, verified certificate provided within 7 days.
Apply today, last date is tonight!
For details WhatsApp us immediately at the number on flyer: 9811223344. Act now!""",

    "🔍 Informal Early-Stage Startup Post": """Content Writing Intern needed for an early-stage startup.
Remote work from home, flexible hours, stipend Rs 7,000/month.
We are a small team building a new lifestyle app. No formal company website yet but you can reach out over WhatsApp or personal email for details: recruiter123@blogspot.com.
Interested candidates apply today, limited slots."""
}

# ---------------------------------------------------------------------------
# Design System: Premium Warm Cream & Espresso Glassmorphism CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --bg-cream: #F8F4EC;
    --bg-surface: rgba(255, 253, 248, 0.75);
    --bg-card: rgba(255, 255, 255, 0.82);
    --border-warm: #E6DCCF;
    --border-accent: #C19A62;
    --espresso-dark: #241812;
    --espresso-medium: #452A1D;
    --brown-muted: #7C7067;
    --maroon-primary: #6B1F2B;
    --maroon-hover: #521620;
    --gold-accent: #B08D57;
    
    --green-bg: rgba(34, 197, 94, 0.08);
    --green-border: rgba(34, 197, 94, 0.30);
    --green-text: #15803D;

    --amber-bg: rgba(245, 158, 11, 0.09);
    --amber-border: rgba(245, 158, 11, 0.30);
    --amber-text: #B45309;

    --red-bg: rgba(107, 31, 43, 0.09);
    --red-border: rgba(107, 31, 43, 0.32);
    --red-text: #6B1F2B;
}

/* Smooth Scrolling & Body Background */
html {
    scroll-behavior: smooth;
}

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: var(--bg-cream) !important;
    background-image: 
        radial-gradient(at 15% 15%, rgba(193, 154, 98, 0.08) 0px, transparent 50%),
        radial-gradient(at 85% 85%, rgba(107, 31, 43, 0.05) 0px, transparent 50%) !important;
    background-attachment: fixed !important;
    color: var(--espresso-dark) !important;
}

/* Hide Default Streamlit Elements */
#MainMenu, footer, header, [data-testid="stDecoration"], [data-testid="stStatusWidget"], [class*="viewerBadge"], [data-testid="stToolbar"] {
    visibility: hidden !important;
    display: none !important;
}

/* Container constraints */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    max-width: 1240px !important;
}

/* Micro-Interaction Keyframes */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(14px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInScale {
    from {
        opacity: 0;
        transform: scale(0.97);
    }
    to {
        opacity: 1;
        transform: scale(1);
    }
}

.animate-fade {
    animation: fadeInUp 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-scale {
    animation: fadeInScale 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Header Navbar Glassmorphism */
.app-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border-warm);
    border-radius: 16px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(58, 36, 24, 0.04);
    animation: fadeInUp 0.5s ease-out;
}

.brand-container {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-icon {
    font-size: 2.3rem;
    background: #FAF5EE;
    border-radius: 12px;
    padding: 6px 12px;
    border: 1px solid #E8DEC8;
    box-shadow: 0 2px 8px rgba(176, 141, 87, 0.15);
}

.brand-title {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--espresso-dark);
    margin: 0;
    line-height: 1.2;
    letter-spacing: -0.2px;
}

.brand-subtitle {
    font-size: 0.86rem;
    color: var(--brown-muted);
    margin-top: 3px;
    font-weight: 500;
}

.status-badge-ready {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(34, 197, 94, 0.09);
    border: 1px solid rgba(34, 197, 94, 0.28);
    color: var(--green-text);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
}

.status-dot-green {
    width: 8px;
    height: 8px;
    background: #16A34A;
    border-radius: 50%;
    box-shadow: 0 0 6px #16A34A;
}

.model-tag {
    background: #FAF5EE;
    border: 1px solid var(--border-warm);
    color: var(--espresso-medium);
    padding: 6px 14px;
    border-radius: 10px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* Metric Cards Grid */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.1rem;
    margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
    .metrics-row {
        grid-template-columns: repeat(2, 1fr);
    }
}

.metric-card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-warm);
    border-radius: 14px;
    padding: 1.15rem 1.3rem;
    box-shadow: 0 4px 16px rgba(58, 36, 24, 0.03);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(58, 36, 24, 0.07);
    border-color: var(--border-accent);
}

.metric-label {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--brown-muted);
    margin-bottom: 0.35rem;
}

.metric-value {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--espresso-dark);
    line-height: 1.1;
}

.metric-sub {
    font-size: 0.78rem;
    color: var(--gold-accent);
    font-weight: 600;
    margin-top: 0.3rem;
}

/* Section Cards & Panels */
.warm-glass-card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-warm);
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 4px 20px rgba(58, 36, 24, 0.04);
    margin-bottom: 1.5rem;
    transition: all 0.25s ease;
}

.card-heading {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--espresso-dark);
    margin-bottom: 0.3rem;
}

.card-desc {
    font-size: 0.88rem;
    color: var(--brown-muted);
    margin-bottom: 1.1rem;
}

/* Dynamic Adaptive Risk Glass Panels */
.risk-panel-idle {
    background: rgba(255, 255, 255, 0.70);
    backdrop-filter: blur(12px);
    border: 1px dashed var(--border-accent);
    border-radius: 16px;
    padding: 3rem 1.8rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(58, 36, 24, 0.03);
}

.risk-panel-low {
    background: var(--green-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--green-border);
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 6px 24px rgba(34, 197, 94, 0.06);
    animation: fadeInScale 0.4s ease-out;
}

.risk-panel-medium {
    background: var(--amber-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--amber-border);
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 6px 24px rgba(245, 158, 11, 0.07);
    animation: fadeInScale 0.4s ease-out;
}

.risk-panel-high {
    background: var(--red-bg);
    backdrop-filter: blur(12px);
    border: 1px solid var(--red-border);
    border-radius: 16px;
    padding: 1.6rem;
    box-shadow: 0 6px 24px rgba(107, 31, 43, 0.09);
    animation: fadeInScale 0.4s ease-out;
}

/* Badges */
.badge-low {
    background: rgba(34, 197, 94, 0.15);
    color: var(--green-text);
    border: 1px solid rgba(34, 197, 94, 0.35);
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.badge-medium {
    background: rgba(245, 158, 11, 0.15);
    color: var(--amber-text);
    border: 1px solid rgba(245, 158, 11, 0.35);
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.badge-high {
    background: rgba(107, 31, 43, 0.15);
    color: var(--red-text);
    border: 1px solid rgba(107, 31, 43, 0.35);
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 0.88rem;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.score-display-number {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 3.4rem;
    font-weight: 700;
    line-height: 1;
}

/* Processing Stepper Box */
.processing-box {
    background: rgba(255, 253, 248, 0.9);
    border: 1px solid var(--border-warm);
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 1.2rem;
    animation: fadeInUp 0.4s ease-out;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.86rem;
    color: var(--espresso-medium);
    padding: 3px 0;
}

.step-check {
    color: var(--maroon-primary);
    font-weight: 700;
}

/* Indicator Badges Grid */
.indicator-chip-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 0.75rem;
}

.indicator-chip {
    background: #FFFDF9;
    border: 1px solid var(--border-accent);
    color: var(--espresso-medium);
    padding: 6px 13px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.indicator-chip-danger {
    background: #FFF5F5;
    border: 1px solid rgba(107, 31, 43, 0.3);
    color: var(--maroon-primary);
    padding: 6px 13px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.indicator-chip-clean {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    color: #166534;
    padding: 6px 13px;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
}

/* Checklist Styling */
.checklist-box {
    background: #FFFDF9;
    border: 1px solid var(--border-warm);
    border-radius: 12px;
    padding: 1.1rem;
    margin-top: 1.1rem;
}

.checklist-item {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 0.85rem;
    color: var(--espresso-dark);
    padding: 4px 0;
}

/* Vector Table */
.vector-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.75rem;
    font-size: 0.88rem;
}

.vector-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border-warm);
}

.vector-table td:last-child {
    text-align: right;
    font-weight: 700;
}

/* Streamlit Button Overrides with Smooth Click Micro-Interactions */
.stButton button {
    background: linear-gradient(135deg, #6B1F2B 0%, #521620 100%) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    border: none !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: 0 4px 12px rgba(107, 31, 43, 0.20) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.stButton button:hover {
    transform: translateY(-2px) scale(1.01) !important;
    box-shadow: 0 6px 18px rgba(107, 31, 43, 0.32) !important;
}

.stButton button:active {
    transform: translateY(1px) scale(0.98) !important;
    box-shadow: 0 2px 6px rgba(107, 31, 43, 0.20) !important;
}

/* Navigation Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: var(--bg-surface);
    backdrop-filter: blur(10px);
    padding: 6px 10px;
    border-radius: 12px;
    border: 1px solid var(--border-warm);
    margin-bottom: 1.3rem;
}

.stTabs [data-baseweb="tab"] {
    font-weight: 600;
    color: var(--brown-muted);
    border-radius: 8px;
    padding: 8px 16px;
    transition: all 0.2s ease;
}

.stTabs [aria-selected="true"] {
    background-color: #FAF5EE !important;
    color: var(--maroon-primary) !important;
    border: 1px solid var(--border-accent) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header & Navigation Banner
# ---------------------------------------------------------------------------
st.markdown("""
<div class="app-header animate-fade">
    <div class="brand-container">
        <div class="brand-icon">🛡️</div>
        <div>
            <div class="brand-title">AI Fake Internship Threat Scanner</div>
            <div class="brand-subtitle">AI-powered screening for suspicious job and internship postings</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span class="status-badge-ready"><span class="status-dot-green"></span> System Ready</span>
        <span class="model-tag">Model: Linear SVM (98.41%)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top Dashboard Metrics (4 Cards)
# ---------------------------------------------------------------------------
st.markdown("""
<div class="metrics-row animate-fade">
    <div class="metric-card">
        <div class="metric-label">Dataset Listings</div>
        <div class="metric-value">17,880</div>
        <div class="metric-sub">EMSCAD Benchmark</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Model Accuracy</div>
        <div class="metric-value">98.41%</div>
        <div class="metric-sub">Test-Set Verified</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Active Model</div>
        <div class="metric-value">Linear SVM</div>
        <div class="metric-sub">Calibrated Classifier</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Risk Indicators</div>
        <div class="metric-value">17</div>
        <div class="metric-sub">Explainable Signals</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------------------------
tab_scan, tab_presets, tab_batch, tab_history, tab_benchmarks, tab_guide = st.tabs([
    "🔍 Analyze Posting",
    "💡 Preset Hub",
    "📁 Batch Scan",
    "📋 Scan History",
    "📊 Model Performance",
    "📖 Defense Guide"
])

# ===========================================================================
# TAB 1: Main Analysis Workspace (2-Column Layout with Demo Mode)
# ===========================================================================
with tab_scan:
    # Viva Demo Mode Bar
    with st.expander("🎬 Live Presentation Demo Mode (Quick Scenario Selectors)", expanded=False):
        st.caption("Select a prepared test case for rapid faculty demonstration:")
        demo_cols = st.columns(3)
        with demo_cols[0]:
            if st.button("1️⃣ Clearly Suspicious Scam", use_container_width=True):
                st.session_state.active_text = PRESETS["🚨 Upfront Registration Fee Scam"]
                st.session_state.last_result = None
                st.rerun()
        with demo_cols[1]:
            if st.button("2️⃣ Genuine Company Offer", use_container_width=True):
                st.session_state.active_text = PRESETS["🚀 Genuine Tech Company Posting"]
                st.session_state.last_result = None
                st.rerun()
        with demo_cols[2]:
            if st.button("3️⃣ Ambiguous High-Pay Post", use_container_width=True):
                st.session_state.active_text = PRESETS["🤑 Unrealistic 80k Income Bait"]
                st.session_state.last_result = None
                st.rerun()

    col_left, col_right = st.columns([1, 1], gap="large")

    # LEFT COLUMN: Posting Input Workspace
    with col_left:
        st.markdown("""
        <div class="warm-glass-card animate-fade">
            <div class="card-heading">Analyze a Job or Internship Posting</div>
            <div class="card-desc">Paste the job or internship description below to screen it for suspicious characteristics.</div>
        """, unsafe_allow_html=True)

        user_text = st.text_area(
            "Posting Text",
            value=st.session_state.active_text,
            height=280,
            placeholder="Paste job title, stipend, description, contact email, requirements here...",
            label_visibility="collapsed"
        )
        st.session_state.active_text = user_text

        # Optional Metadata Controls
        with st.expander("⚙️ Optional Post Metadata Flags", expanded=False):
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                tc_flag = st.checkbox("Remote work", value=False)
            with mcol2:
                logo_flag = st.checkbox("Company logo", value=False)
            with mcol3:
                q_flag = st.checkbox("Screening questions", value=False)

        # Document File Parsing
        uploaded_file = st.file_uploader(
            "Upload document (.txt, .pdf, .docx)",
            type=["txt", "pdf", "docx", "md"],
            help="Automatically parse offer letters or PDF postings."
        )
        if uploaded_file is not None:
            extracted = extract_text_from_file(uploaded_file, uploaded_file.name)
            if extracted and not extracted.startswith("[Error"):
                st.session_state.active_text = extracted
                st.success(f"✓ Extracted text from {uploaded_file.name}")
                st.rerun()

        # Action Buttons
        bcol1, bcol2 = st.columns([2, 1])
        with bcol1:
            analyze_clicked = st.button("🛡️ Analyze Posting", use_container_width=True)
        with bcol2:
            if st.button("Clear Input", use_container_width=True):
                st.session_state.active_text = ""
                st.session_state.last_result = None
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # RIGHT COLUMN: Dynamic Risk Assessment Panel
    with col_right:
        if analyze_clicked and user_text.strip():
            # Execute ML Inference Pipeline
            res = predict(
                user_text,
                telecommuting=1 if tc_flag else 0,
                has_company_logo=1 if logo_flag else 0,
                has_questions=1 if q_flag else 0
            )

            st.session_state.last_result = res
            st.session_state.last_scanned_text = user_text

            # Log to scan history
            st.session_state.history.append({
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "text_snippet": user_text[:60] + "...",
                "risk_score": res["risk_score"],
                "risk_level": res["risk_level"],
                "indicators_count": len(res["indicators"])
            })

        # Render Results or Idle Neutral State
        if st.session_state.last_result is not None and st.session_state.last_scanned_text:
            result = st.session_state.last_result
            score = result["risk_score"]
            level = result["risk_level"]
            indicators = result["indicators"]
            vectors = result["vectors"]

            # Visual Processing Stepper Feedback
            st.markdown("""
            <div class="processing-box">
                <div class="step-item"><span class="step-check">✓</span> Text preprocessing & tokenization complete</div>
                <div class="step-item"><span class="step-check">✓</span> TF-IDF feature extraction (4,000 informative terms)</div>
                <div class="step-item"><span class="step-check">✓</span> 17 structured risk indicators evaluated</div>
                <div class="step-item"><span class="step-check">✓</span> Linear SVM classification computed</div>
                <div class="step-item"><span class="step-check">✓</span> Explainable risk assessment generated</div>
            </div>
            """, unsafe_allow_html=True)

            # Determine Risk Glass Panel Styling
            if level == "HIGH RISK":
                panel_class = "risk-panel-high"
                badge_class = "badge-high"
                score_color = "#6B1F2B"
                level_icon = "🔴"
            elif level == "MEDIUM RISK":
                panel_class = "risk-panel-medium"
                badge_class = "badge-medium"
                score_color = "#B45309"
                level_icon = "🟡"
            else:
                panel_class = "risk-panel-low"
                badge_class = "badge-low"
                score_color = "#15803D"
                level_icon = "🟢"

            # Dynamic Glass Risk Panel
            st.markdown(f"""
            <div class="{panel_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                    <div style="font-weight: 700; font-size: 0.88rem; color: var(--brown-muted); text-transform: uppercase; letter-spacing: 0.5px;">Risk Assessment</div>
                    <div class="{badge_class}">{level_icon} {level}</div>
                </div>
                <div style="text-align: center; padding: 1.1rem 0;">
                    <div class="score-display-number" style="color: {score_color};">{score}</div>
                    <div style="font-size: 0.85rem; color: var(--brown-muted); font-weight: 600;">Threat Index Score (Out of 100)</div>
                </div>
            """, unsafe_allow_html=True)

            # Plain-English AI Explanation
            st.markdown("##### 💡 Plain-English AI Explanation")
            if level == "HIGH RISK":
                exp_text = "This posting contains multiple strong characteristics commonly associated with suspicious recruitment listings. Strong signals include payment requests or urgent application pressure."
            elif level == "MEDIUM RISK":
                exp_text = "This posting shows moderate risk factors. While it could belong to an informal listing, the presence of generic contact patterns or urgent wording suggests independent verification."
            else:
                exp_text = "No major suspicious signals were detected in this posting. The wording is consistent with standard recruitment posts, though standard caution is always recommended."

            st.markdown(f"<p style='font-size: 0.88rem; color: #3A2418; line-height: 1.5;'>{exp_text}</p>", unsafe_allow_html=True)

            # Why was this flagged? Section
            st.markdown("##### 🔎 Why was this flagged?")
            if indicators:
                st.markdown('<div class="indicator-chip-grid">', unsafe_allow_html=True)
                for ind in indicators:
                    c_class = "indicator-chip-danger" if "fee" in ind["key"] else "indicator-chip"
                    st.markdown(f'<span class="{c_class}">⚠️ {ind["title"]}</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

                with st.expander("Detailed indicator explanations", expanded=False):
                    for ind in indicators:
                        st.markdown(f"**{ind['title']}**")
                        st.caption(ind["explanation"])
            else:
                st.markdown('<div class="indicator-chip-grid"><span class="indicator-chip-clean">✓ No unusual contact or fee traps detected</span></div>', unsafe_allow_html=True)

            # Sub-Vector Risk Breakdown
            st.markdown("<h5 style='margin-top: 1.2rem;'>📊 Sub-Vector Risk Breakdown</h5>", unsafe_allow_html=True)
            st.markdown(f"""
            <table class="vector-table">
                <tr><td>💰 Upfront Payment / Fee Risk</td><td>{vectors['financial_risk']}%</td></tr>
                <tr><td>⚡ Urgency & Pressure Language</td><td>{vectors['urgency_risk']}%</td></tr>
                <tr><td>📡 Contact Channel Integrity</td><td>{vectors['channel_risk']}%</td></tr>
                <tr><td>🌐 Domain & URL Risk</td><td>{vectors.get('domain_risk', 0.0)}%</td></tr>
                <tr><td>🏢 Employer Legitimacy Score</td><td>{vectors['legitimacy_score']}%</td></tr>
            </table>
            """, unsafe_allow_html=True)

            # Interactive Checklist: Before You Apply
            st.markdown("""
            <div class="checklist-box">
                <div style="font-weight: 700; font-size: 0.88rem; color: var(--espresso-dark); margin-bottom: 6px;">📋 Before You Apply Checklist</div>
                <div class="checklist-item">☐ Verify official company website & domain</div>
                <div class="checklist-item">☐ Confirm recruiter email domain matches corporate domain</div>
                <div class="checklist-item">☐ Never pay registration or security fees</div>
                <div class="checklist-item">☐ Avoid sharing bank details or sensitive documents</div>
            </div>
            </div>
            """, unsafe_allow_html=True)

            # Export Audit Reports
            st.markdown("<br>", unsafe_allow_html=True)
            ecol1, ecol2, ecol3 = st.columns(3)
            with ecol1:
                st.download_button(
                    "📥 Export JSON",
                    data=json.dumps(result, indent=2),
                    file_name="threat_report.json",
                    mime="application/json",
                    use_container_width=True
                )
            with ecol2:
                md_rep = f"# AI Fake Internship Threat Audit\nScore: {score}/100\nLevel: {level}\n"
                st.download_button(
                    "📄 Export Markdown",
                    data=md_rep,
                    file_name="threat_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with ecol3:
                html_rep = f"<html><body><h1>Threat Audit</h1><h2>Score: {score}/100 ({level})</h2></body></html>"
                st.download_button(
                    "🌐 Export HTML",
                    data=html_rep,
                    file_name="threat_report.html",
                    mime="text/html",
                    use_container_width=True
                )
        else:
            # Idle Neutral Glass Panel
            st.markdown("""
            <div class="risk-panel-idle animate-scale">
                <div style="font-size: 3.5rem; margin-bottom: 0.5rem;">🛡️</div>
                <div style="font-family: 'Playfair Display', Georgia, serif; font-size: 1.35rem; font-weight: 700; color: var(--espresso-dark);">Ready to Analyze</div>
                <div style="font-size: 0.88rem; color: var(--brown-muted); margin-top: 0.4rem; max-width: 320px; margin-left: auto; margin-right: auto;">
                    Paste a job description on the left and click <strong>Analyze Posting</strong> to generate a risk assessment.
                </div>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# TAB 2: Preset Scenario Hub
# ===========================================================================
with tab_presets:
    st.markdown("""
    <div class="card-heading">1-Click Preset Scenario Hub</div>
    <div class="card-desc">Select a documented real-world scenario to load it directly into the analyzer.</div>
    """, unsafe_allow_html=True)

    preset_cols = st.columns(2)
    idx = 0
    for title, text in PRESETS.items():
        with preset_cols[idx % 2]:
            st.markdown(f"""
            <div class="warm-glass-card animate-fade">
                <div style="font-family: 'Playfair Display', Georgia, serif; font-weight: 700; font-size: 1.05rem; color: var(--maroon-primary); margin-bottom: 0.5rem;">{title}</div>
                <div style="font-size: 0.84rem; color: var(--espresso-medium); background: #FFFDF9; padding: 10px; border-radius: 8px; border: 1px solid var(--border-warm); margin-bottom: 0.8rem; white-space: pre-wrap; max-height: 120px; overflow-y: auto;">{html.escape(text[:180])}...</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Load '{title.split()[1] if len(title.split()) > 1 else title}'", key=f"btn_preset_{idx}"):
                st.session_state.active_text = text
                st.session_state.last_result = None
                st.success(f"✓ Loaded {title} into analyzer!")
                st.rerun()
        idx += 1

# ===========================================================================
# TAB 3: Batch CSV Scanning
# ===========================================================================
with tab_batch:
    st.markdown("""
    <div class="card-heading">Batch CSV File Scanner</div>
    <div class="card-desc">Upload a CSV dataset of job postings to perform automated bulk screening.</div>
    """, unsafe_allow_html=True)

    csv_file = st.file_uploader("Upload CSV File", type=["csv"])
    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file)
            st.write(f"Loaded CSV with **{len(df)}** rows.")
            text_col = st.selectbox("Select text column for scanning", options=df.columns)

            if st.button("🚀 Process Batch Scan"):
                progress_bar = st.progress(0)
                results_list = []

                for i, row in df.iterrows():
                    val = str(row[text_col]) if pd.notna(row[text_col]) else ""
                    res = predict(val)
                    results_list.append({
                        "row_id": i + 1,
                        "text_snippet": val[:80] + "...",
                        "risk_score": res["risk_score"],
                        "risk_level": res["risk_level"],
                        "triggered_indicators": len(res["indicators"])
                    })
                    progress_bar.progress((i + 1) / len(df))

                res_df = pd.DataFrame(results_list)
                st.success("✓ Batch scanning completed!")
                st.dataframe(res_df, use_container_width=True)

                st.download_button(
                    "📥 Download Results CSV",
                    data=res_df.to_csv(index=False).encode('utf-8'),
                    file_name="batch_scan_results.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

# ===========================================================================
# TAB 4: Session Scan History
# ===========================================================================
with tab_history:
    st.markdown("""
    <div class="card-heading">Scan Session History</div>
    <div class="card-desc">Review postings scanned during your current active session.</div>
    """, unsafe_allow_html=True)

    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
        if st.button("Clear History"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("No scans performed in this session yet.")

# ===========================================================================
# TAB 5: Model Performance & "What Does This Mean?" Viva Guide
# ===========================================================================
with tab_benchmarks:
    st.markdown("""
    <div class="card-heading">Machine Learning Model Benchmarking Studio</div>
    <div class="card-desc">Reported evaluation metrics on the EMSCAD test set (3,576 postings).</div>
    """, unsafe_allow_html=True)

    # Documented Test-Set Metrics Table
    metrics_data = [
        {"Model": "Logistic Regression", "Accuracy": "95.61%", "Fraud Precision": "52.68%", "Fraud Recall": "90.75%", "Fraud F1": "0.6667"},
        {"Model": "Random Forest", "Accuracy": "97.93%", "Fraud Precision": "100.00%", "Fraud Recall": "57.23%", "Fraud F1": "0.7279"},
        {"Model": "Linear SVM (Active)", "Accuracy": "98.41%", "Fraud Precision": "90.85%", "Fraud Recall": "74.57%", "Fraud F1": "0.8190"}
    ]
    st.table(pd.DataFrame(metrics_data))

    st.markdown("##### 📐 Linear SVM Confusion Matrix (Test Set)")
    cm_data = [
        {"Actual Status": "Legitimate (3,403 total)", "Predicted Legitimate": "3,390 (True Negative)", "Predicted Fraudulent": "13 (False Positive)"},
        {"Actual Status": "Fraudulent (173 total)", "Predicted Legitimate": "44 (False Negative)", "Predicted Fraudulent": "129 (True Positive)"}
    ]
    st.table(pd.DataFrame(cm_data))

    # Viva Guide Section: What Does This Mean?
    st.markdown("""
    <div class="warm-glass-card animate-fade">
        <h4 style="font-family: 'Playfair Display', serif; color: var(--maroon-primary); margin-bottom: 0.75rem;">🎓 "What Does This Mean?" — Viva Explanation Guide</h4>
        <ul>
            <li><strong>Accuracy (98.41%):</strong> Overall percentage of test postings correctly classified as legitimate or fraudulent.</li>
            <li><strong>Fraud Precision (90.85%):</strong> Out of all postings flagged as fraudulent by Linear SVM, 90.85% were actually fraudulent (very low false alarms).</li>
            <li><strong>Fraud Recall (74.57%):</strong> Out of all actual fraudulent postings in the test set, the model correctly caught 74.57%.</li>
            <li><strong>F1-Score (0.8190):</strong> Harmonic mean balancing precision and recall for imbalanced datasets.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    # Output Plots
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if os.path.exists("outputs/model_comparison.png"):
            st.image("outputs/model_comparison.png", caption="Model Metric Comparison", use_container_width=True)
    with img_col2:
        if os.path.exists("outputs/confusion_matrix_linear_svm.png"):
            st.image("outputs/confusion_matrix_linear_svm.png", caption="Linear SVM Confusion Matrix", use_container_width=True)

# ===========================================================================
# TAB 6: Student Scam-Defense Guide
# ===========================================================================
with tab_guide:
    st.markdown("""
    <div class="card-heading">Internship Scam Defense Center</div>
    <div class="card-desc">Essential safety guidelines for students to identify and avoid recruitment fraud.</div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="warm-glass-card animate-fade">
        <h4 style="color: var(--maroon-primary); margin-bottom: 0.75rem;">🚨 Red Flag Checklist for Students</h4>
        <ul>
            <li><strong>Upfront Fee Demands:</strong> Legitimate employers never ask candidates to pay for training, processing, or laptop deposits.</li>
            <li><strong>Free Email Domains:</strong> Be suspicious if recruiters write from free webmail domains (e.g. @gmail.com) rather than corporate email domains.</li>
            <li><strong>Guaranteed High Income:</strong> Promises of ₹50,000+ per month for entry-level work with "no experience required" are common scam traps.</li>
            <li><strong>Messaging App Interviews:</strong> Employers using only WhatsApp or Telegram without corporate video interviews or emails require extra verification.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
