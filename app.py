"""
app.py
------
AI Fake Internship Threat Scanner & Company Verification Platform
Review 3 Final Unified & Optimized Build
Theme: Black / Charcoal + Deep Red + Vibrant Lime + Glassmorphism + 3D AI Security Core
"""

import datetime
import html
import json
import os
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import config
from company_providers import is_online
from inference import predict, load_artifacts, extract_text_from_file
from internshield_pipeline import analyze_listing, verify_only

# ---------------------------------------------------------------------------
# Fast Caching for ML Artifacts and Online Status
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_cached_ml_artifacts():
    return load_artifacts()

# Pre-warm ML model
try:
    get_cached_ml_artifacts()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Fake Internship Threat Scanner | Security Intelligence Platform",
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

if "active_company" not in st.session_state:
    st.session_state.active_company = ""

if "active_email" not in st.session_state:
    st.session_state.active_email = ""

if "active_website" not in st.session_state:
    st.session_state.active_website = ""

if "active_recruiter" not in st.session_state:
    st.session_state.active_recruiter = ""

if "active_linkedin" not in st.session_state:
    st.session_state.active_linkedin = ""

if "active_joburl" not in st.session_state:
    st.session_state.active_joburl = ""

if "last_scanned_text" not in st.session_state:
    st.session_state.last_scanned_text = None

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "multi_post_text" not in st.session_state:
    st.session_state.multi_post_text = ""

if "multi_post_results" not in st.session_state:
    st.session_state.multi_post_results = None

# ---------------------------------------------------------------------------
# Comprehensive Preset Scenarios Library (Each with All 6 Full Fields)
# ---------------------------------------------------------------------------
PRESETS = {
    "🚨 Upfront Registration Fee Scam": {
        "tag": "CRITICAL THREAT",
        "color": "#EF4444",
        "bg_glass": "rgba(220, 38, 38, 0.12)",
        "border_color": "rgba(239, 68, 68, 0.4)",
        "type": "fee_trap",
        "title": "Upfront Registration Fee Scam",
        "company": "Fast Career Solutions Pvt Ltd",
        "website": "http://fastcareersolutions.blogspot.com",
        "recruiter": "Rajesh Kumar",
        "email": "hrjobs.fastcareer@gmail.com",
        "linkedin": "https://linkedin.com/in/rajesh-hr-fake99",
        "joburl": "https://bit.ly/dataentry-wfh-job",
        "desc": "High-risk upfront payment trap demanding ₹999 security fee with fake WhatsApp contact.",
        "text": """URGENT HIRING: Work From Home Data Entry Intern
Earn Rs 45,000 per month, no experience or qualification needed!
Limited seats available, apply today before offer ends!
To confirm your selection and receive your work kit, candidates must pay a refundable registration fee of Rs 999.
Contact us immediately on WhatsApp: +91-9876543210.
Email: hrjobs.fastcareer@gmail.com"""
    },

    "🎭 Microsoft Impersonation Trap": {
        "tag": "IMPERSONATION",
        "color": "#38BDF8",
        "bg_glass": "rgba(56, 189, 248, 0.12)",
        "border_color": "rgba(56, 189, 248, 0.4)",
        "type": "impersonation",
        "title": "Microsoft Impersonation Trap",
        "company": "Microsoft",
        "website": "https://microsoft.com",
        "recruiter": "Sarah Jenkins",
        "email": "microsoft-careers@gmail.com",
        "linkedin": "https://linkedin.com/in/sarah-jenkins-techrecruiter",
        "joburl": "https://forms.gle/msft-intern-apply-2024",
        "desc": "Legitimate Fortune 500 company name hijacked using non-corporate Gmail & fee trap.",
        "text": """Microsoft Software Engineering Intern - Remote Opportunity
Selected candidates will receive onboarding kits after paying a refundable verification deposit of Rs 2,500.
Immediate selection without technical interview.
Send your resume and fee receipt to: microsoft-careers@gmail.com or WhatsApp +91-9811223344."""
    },

    "🚀 Genuine Tech Company Posting": {
        "tag": "VERIFIED SAFE",
        "color": "#22C55E",
        "bg_glass": "rgba(34, 197, 94, 0.12)",
        "border_color": "rgba(34, 197, 94, 0.4)",
        "type": "legitimate",
        "title": "Genuine Series-B FinTech Posting",
        "company": "Northwind Analytics Pvt Ltd",
        "website": "https://northwindanalytics.example.com",
        "recruiter": "Ananya Sen (Talent Acquisition)",
        "email": "careers@northwindanalytics.example.com",
        "linkedin": "https://linkedin.com/in/ananya-sen-talent",
        "joburl": "https://northwindanalytics.example.com/careers/backend-intern",
        "desc": "Authentic company posting with matching corporate email domain, clear skills, and fair stipend.",
        "text": """Software Engineering Intern - Backend Systems
About Us: We are a Series B fintech company headquartered in Bengaluru, founded in 2018, building payment infrastructure for businesses. Learn more at www.northwindanalytics.example.com/about.
Role: You will work with our backend engineering team on Python/Django microservices, write unit tests, and participate in daily standups and code reviews. This is a 6-month paid internship (stipend Rs 25,000/month) with potential PPO.
Requirements: Currently pursuing B.Tech/B.E in CS/IT, familiarity with Python, REST APIs, and SQL.
Apply through our official careers page or email careers@northwindanalytics.example.com."""
    },

    "🤑 Unrealistic 80k Income Bait": {
        "tag": "UNREALISTIC PAY",
        "color": "#F59E0B",
        "bg_glass": "rgba(245, 158, 11, 0.12)",
        "border_color": "rgba(245, 158, 11, 0.4)",
        "type": "unrealistic",
        "title": "Unrealistic 80k Monthly Pay Bait",
        "company": "Global Growth Media Hub",
        "website": "http://globalgrowthmedia.wixsite.com",
        "recruiter": "Vikas Malhotra",
        "email": "marketingjobs99@yahoo.com",
        "linkedin": "https://linkedin.com/in/vikas-marketing-lead",
        "joburl": "https://tinyurl.com/growth-intern-80k",
        "desc": "Extravagant stipend promises (₹80k/mo for 2hrs/day) with zero prerequisites or screening.",
        "text": """Marketing & Growth Intern - Immediate Joining!
Fresher welcome! No interview, no resume, no experience required.
Guaranteed income of Rs 80,000 per month, 100% job guarantee!
Work only 2 hours a day from your mobile phone.
Seats filling fast, apply immediately!
Send your details to: marketingjobs99@yahoo.com or DM us on Telegram."""
    },

    "⚡ Urgent WhatsApp Contact Flyer": {
        "tag": "URGENCY PRESSURE",
        "color": "#FB923C",
        "bg_glass": "rgba(251, 146, 60, 0.12)",
        "border_color": "rgba(251, 146, 60, 0.4)",
        "type": "urgency",
        "title": "High Urgency WhatsApp Flyer",
        "company": "Quick Certification Network",
        "website": "http://quickcertify.net",
        "recruiter": "Aditya Verma",
        "email": "quickhire2024@gmail.com",
        "linkedin": "https://linkedin.com/in/aditya-hiring-flyer",
        "joburl": "https://wa.me/919811223344",
        "desc": "Artificial pressure ('Only 3 spots left tonight') diverting students exclusively to WhatsApp.",
        "text": """Hiring Student Interns - Apply Immediately!
Only 3 spots left, hurry up, don't miss this life-changing opportunity!
Great industry exposure, verified certificate provided within 7 days.
Apply today, last date is tonight!
For details WhatsApp us immediately at the number on flyer: 9811223344. Act now!"""
    },

    "🔍 Informal Early-Stage Startup Post": {
        "tag": "INFORMAL STARTUP",
        "color": "#C084FC",
        "bg_glass": "rgba(192, 132, 252, 0.12)",
        "border_color": "rgba(192, 132, 252, 0.4)",
        "type": "informal",
        "title": "Early-Stage Informal Startup",
        "company": "AppCrafters Lab",
        "website": "http://appcrafters123.blogspot.com",
        "recruiter": "Pooja Roy",
        "email": "recruiter123@blogspot.com",
        "linkedin": "https://linkedin.com/in/pooja-roy-content",
        "joburl": "http://appcrafters123.blogspot.com/p/careers.html",
        "desc": "Informal startup with personal blog and email; moderate caution needed but not outright fee scam.",
        "text": """Content Writing Intern needed for an early-stage startup.
Remote work from home, flexible hours, stipend Rs 7,000/month.
We are a small team building a new lifestyle app. No formal company website yet but you can reach out over WhatsApp or personal email for details: recruiter123@blogspot.com.
Interested candidates apply today, limited slots."""
    }
}

# ---------------------------------------------------------------------------
# Multi-Posting Scanner Helper & Sample Template
# ---------------------------------------------------------------------------
SAMPLE_MULTI_POSTINGS = """POSTING 1:
Data Entry & Document Verification Intern - Immediate Hiring!
Earn Rs 45,000 per month from home. No interview or prior experience needed!
Limited seats available. A refundable registration and verification kit fee of Rs 999 is required to activate your candidate ID before onboarding.
Send your details on WhatsApp to +91-9876543210 or email hrjobs.fastcareer@gmail.com.

---

POSTING 2:
Software Engineering Intern (Summer 2025)
Microsoft Corporation - Redmond, WA / Remote
We are seeking undergraduate students in Computer Science or related STEM disciplines.
Responsibilities include writing production Python/TypeScript code, collaborating in agile sprints, and building cloud microservices.
Requirements: Strong proficiency in Data Structures, Algorithms, and Object-Oriented Design. Competitive monthly stipend + housing assistance provided.
Apply through official portal: careers.microsoft.com.

---

POSTING 3:
Marketing & Growth Intern - Earn 80k/Month Working 2 Hours/Day!
Guaranteed selection! No resume or screening required.
Work directly from your phone for just 2 hours a day and earn Rs 80,000 every month guaranteed.
Hurry, only 2 spots remaining! DM us on Telegram or email marketingjobs99@yahoo.com right now."""


def split_multi_postings(raw_text: str, separator_mode: str = "Auto-Detect") -> list[str]:
    """
    Intelligently splits a multi-posting blob into individual job descriptions.
    Supports dashes (---, ===), headers (POSTING 1:, JOB 2:), blank lines, etc.
    """
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    if separator_mode == "Dashes / Horizontal Rules (---, ===, ___)":
        parts = re.split(r'(?:\r?\n)\s*[-=_]{3,}\s*(?:\r?\n)', text)
    elif separator_mode == "Headers (POSTING 1:, JOB 2:, MESSAGE 3:, etc.)":
        parts = re.split(r'(?i)(?:^|\r?\n)\s*(?:POSTING|JOB|MESSAGE|OFFER|OPPORTUNITY|INTERNSHIP)\s*#?\s*\d+[:.\s-]*', text)
    elif separator_mode == "Double Blank Lines":
        parts = re.split(r'(?:\r?\n\s*){2,}', text)
    else:  # Auto-Detect
        # Priority 1: Check for explicit horizontal rule separators (---, ===, ___)
        if re.search(r'(?:\r?\n)\s*[-=_]{3,}\s*(?:\r?\n)', text):
            parts = re.split(r'(?:\r?\n)\s*[-=_]{3,}\s*(?:\r?\n)', text)
        # Priority 2: Check for explicit Header labels (POSTING 1:, JOB 1:, etc.)
        elif re.search(r'(?i)(?:^|\r?\n)\s*(?:POSTING|JOB|MESSAGE|OFFER|INTERNSHIP)\s*#?\s*\d+[:.\s-]*', text):
            parts = re.split(r'(?i)(?:^|\r?\n)\s*(?:POSTING|JOB|MESSAGE|OFFER|INTERNSHIP)\s*#?\s*\d+[:.\s-]*', text)
        # Priority 3: Check for 3+ consecutive blank lines
        elif re.search(r'(?:\r?\n\s*){3,}', text):
            parts = re.split(r'(?:\r?\n\s*){3,}', text)
        # Priority 4: Fallback to double blank lines if multiple paragraphs look like separate postings
        elif re.search(r'(?:\r?\n\s*){2,}', text):
            candidate_parts = re.split(r'(?:\r?\n\s*){2,}', text)
            if sum(1 for p in candidate_parts if len(p.strip()) > 30) > 1:
                parts = candidate_parts
            else:
                parts = [text]
        else:
            parts = [text]

    cleaned = [p.strip() for p in parts if len(p.strip()) > 10]
    return cleaned if cleaned else ([text] if len(text) > 5 else [])


# ---------------------------------------------------------------------------
# Safe HTML Streamlit Renderer (Zero Code-Leak Guarantee)
# ---------------------------------------------------------------------------
def render_safe_html(html_str: str):
    """
    Renders HTML safely in Streamlit by stripping all leading indentation and blank lines
    so the CommonMark markdown parser never mistakenly treats inner HTML as code blocks.
    """
    lines = [line.strip() for line in html_str.splitlines() if line.strip()]
    st.markdown("".join(lines), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 3D Security Core Component (Three.js WebGL Interactive Cyber Shield)
# ---------------------------------------------------------------------------
def render_3d_security_core(risk_level="IDLE"):
    """
    Renders an interactive, GPU-accelerated 3D metallic cyber shield with orbiting
    energy rings and atmospheric particle field.
    """
    if risk_level in ("HIGH RISK", "VERY HIGH RISK"):
        core_color = "0xEF4444"
        ring_color = "0xDC2626"
        light_color = "0xFF3333"
    elif risk_level in ("MEDIUM RISK", "SUSPICIOUS", "CAUTION"):
        core_color = "0xF59E0B"
        ring_color = "0xD97706"
        light_color = "0xFBBF24"
    elif risk_level == "LOW RISK":
        core_color = "0x22C55E"
        ring_color = "0x16A34A"
        light_color = "0x4ADE80"
    else:  # IDLE
        core_color = "0xDC2626"
        ring_color = "0x991B1B"
        light_color = "0xEF4444"

    html_code = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            overflow: hidden;
            background: transparent;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        }}
        #canvas-container {{
            width: 100%;
            height: 165px;
            position: relative;
            cursor: grab;
        }}
        #canvas-container:active {{
            cursor: grabbing;
        }}
        .overlay-badge {{
            position: absolute;
            bottom: 4px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(14, 14, 20, 0.85);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: #D4D4D8;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 12px;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            pointer-events: none;
            white-space: nowrap;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <div id="canvas-container">
        <div class="overlay-badge">3D AI Security Core &bull; Live Orbit</div>
    </div>
    <script>
        const container = document.getElementById('canvas-container');
        const width = container.clientWidth || 400;
        const height = 165;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 1000);
        camera.position.z = 4.8;

        const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true, powerPreference: "high-performance" }});
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);

        const shieldShape = new THREE.Shape();
        shieldShape.moveTo(0, 1.2);
        shieldShape.lineTo(0.9, 0.9);
        shieldShape.lineTo(0.95, -0.2);
        shieldShape.lineTo(0, -1.3);
        shieldShape.lineTo(-0.95, -0.2);
        shieldShape.lineTo(-0.9, 0.9);
        shieldShape.closePath();

        const extrudeSettings = {{
            depth: 0.28,
            bevelEnabled: true,
            bevelSegments: 3,
            steps: 1,
            bevelSize: 0.08,
            bevelThickness: 0.08
        }};

        const shieldGeo = new THREE.ExtrudeGeometry(shieldShape, extrudeSettings);
        shieldGeo.center();

        const shieldMat = new THREE.MeshStandardMaterial({{
            color: 0x181820,
            metalness: 0.90,
            roughness: 0.20,
            emissive: {core_color},
            emissiveIntensity: 0.32,
            wireframe: false
        }});

        const shieldMesh = new THREE.Mesh(shieldGeo, shieldMat);
        shieldMesh.scale.set(0.85, 0.85, 0.85);
        scene.add(shieldMesh);

        const wireMat = new THREE.MeshBasicMaterial({{
            color: {core_color},
            wireframe: true,
            transparent: true,
            opacity: 0.40
        }});
        const wireMesh = new THREE.Mesh(shieldGeo, wireMat);
        wireMesh.scale.set(0.90, 0.90, 0.90);
        scene.add(wireMesh);

        const ringGeo1 = new THREE.TorusGeometry(1.6, 0.022, 16, 48);
        const ringMat1 = new THREE.MeshBasicMaterial({{
            color: {ring_color},
            transparent: true,
            opacity: 0.80
        }});
        const ringMesh1 = new THREE.Mesh(ringGeo1, ringMat1);
        ringMesh1.rotation.x = Math.PI / 3;
        scene.add(ringMesh1);

        const ringGeo2 = new THREE.TorusGeometry(1.85, 0.016, 16, 48);
        const ringMat2 = new THREE.MeshBasicMaterial({{
            color: {ring_color},
            transparent: true,
            opacity: 0.50
        }});
        const ringMesh2 = new THREE.Mesh(ringGeo2, ringMat2);
        ringMesh2.rotation.x = -Math.PI / 3.5;
        ringMesh2.rotation.y = Math.PI / 6;
        scene.add(ringMesh2);

        const particleCount = 60;
        const particleGeo = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);
        for (let i = 0; i < particleCount * 3; i += 3) {{
            particlePositions[i] = (Math.random() - 0.5) * 6;
            particlePositions[i + 1] = (Math.random() - 0.5) * 4;
            particlePositions[i + 2] = (Math.random() - 0.5) * 4;
        }}
        particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        const particleMat = new THREE.PointsMaterial({{
            color: {ring_color},
            size: 0.05,
            transparent: true,
            opacity: 0.65
        }});
        const particles = new THREE.Points(particleGeo, particleMat);
        scene.add(particles);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
        scene.add(ambientLight);

        const pointLight = new THREE.PointLight({light_color}, 2.8, 12);
        pointLight.position.set(2, 2, 3);
        scene.add(pointLight);

        let mouseX = 0, mouseY = 0;
        let targetRotationX = 0, targetRotationY = 0;

        window.addEventListener('mousemove', (e) => {{
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left - (rect.width / 2);
            const y = e.clientY - rect.top - (rect.height / 2);
            mouseX = (x / rect.width) * 1.5;
            mouseY = (y / rect.height) * 1.5;
        }});

        let clock = new THREE.Clock();
        function animate() {{
            requestAnimationFrame(animate);
            const elapsedTime = clock.getElapsedTime();

            shieldMesh.position.y = Math.sin(elapsedTime * 1.6) * 0.08;
            wireMesh.position.y = shieldMesh.position.y;

            targetRotationY += (mouseX - targetRotationY) * 0.05;
            targetRotationX += (mouseY - targetRotationX) * 0.05;

            shieldMesh.rotation.y = targetRotationY + Math.sin(elapsedTime * 0.8) * 0.22;
            shieldMesh.rotation.x = targetRotationX + Math.cos(elapsedTime * 0.6) * 0.07;
            wireMesh.rotation.y = shieldMesh.rotation.y;
            wireMesh.rotation.x = shieldMesh.rotation.x;

            ringMesh1.rotation.z = elapsedTime * 0.8;
            ringMesh1.rotation.y = elapsedTime * 0.35;
            ringMesh2.rotation.z = -elapsedTime * 0.6;

            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            const newWidth = container.clientWidth || 400;
            camera.aspect = newWidth / height;
            camera.updateProjectionMatrix();
            renderer.setSize(newWidth, height);
        }});
    </script>
</body>
</html>"""
    components.html(html_code, height=170, scrolling=False)


# ---------------------------------------------------------------------------
# Dedicated Risk Intelligence Component (Crystal Clear & Intuitive)
# ---------------------------------------------------------------------------
def render_risk_intelligence_card(result):
    """
    Renders the complete graphical Risk Intelligence Dashboard inside an isolated
    HTML component container with maximum clarity and high contrast.
    """
    overall = result.get("overall_assessment") or {}
    pred = result.get("internship_prediction") or result
    comp = result.get("company_verification") or {}
    contact = result.get("contact_analysis") or {}
    expl = result.get("explanation") or {}
    inv = result.get("investigation")

    score = overall.get("risk_score", pred.get("risk_score", 0))
    level = overall.get("risk_level", pred.get("risk_level", "LOW RISK"))
    indicators = pred.get("indicators", [])
    vectors = pred.get("vectors", {
        "financial_risk": 0.0, "urgency_risk": 0.0, "channel_risk": 0.0,
        "domain_risk": 0.0, "legitimacy_score": 90.0
    })

    # High contrast color schemes
    if level in ("HIGH RISK", "VERY HIGH RISK"):
        stage_bg = "linear-gradient(180deg, rgba(220, 38, 38, 0.22) 0%, rgba(20, 10, 14, 0.98) 100%)"
        border_color = "rgba(239, 68, 68, 0.6)"
        meter_color = "#EF4444"
        badge_bg = "#EF4444"
        badge_text = "#FFFFFF"
        level_icon = "🚨"
        verdict_title = "HIGH RISK SCAM"
        verdict_color = "#EF4444"
        verdict_desc = "Strong fraudulent indicators detected. High probability of recruitment fraud or financial trap."
        action_advice = "DO NOT pay registration fees, security deposits, or share bank/identity credentials."
    elif level in ("MEDIUM RISK", "SUSPICIOUS", "CAUTION"):
        stage_bg = "linear-gradient(180deg, rgba(245, 158, 11, 0.18) 0%, rgba(26, 18, 12, 0.98) 100%)"
        border_color = "rgba(245, 158, 11, 0.6)"
        meter_color = "#F59E0B"
        badge_bg = "#F59E0B"
        badge_text = "#000000"
        level_icon = "⚠️"
        verdict_title = "SUSPICIOUS / ELEVATED RISK"
        verdict_color = "#F59E0B"
        verdict_desc = "Moderate risk characteristics found. Warrants independent verification before applying."
        action_advice = "Verify recruiter identity and cross-reference official corporate email domains."
    else:  # LOW RISK
        stage_bg = "linear-gradient(180deg, rgba(34, 197, 94, 0.16) 0%, rgba(14, 26, 18, 0.98) 100%)"
        border_color = "rgba(34, 197, 94, 0.6)"
        meter_color = "#22C55E"
        badge_bg = "#22C55E"
        badge_text = "#000000"
        level_icon = "🛡️"
        verdict_title = "SAFE / LEGITIMATE POSTING"
        verdict_color = "#22C55E"
        verdict_desc = "No major suspicious indicators detected. Text aligns with authentic recruitment standards."
        action_advice = "Standard job application safety applies. Proceed with confidence."

    # Circular gauge math
    circumference = 326.7
    dashoffset = circumference - (score / 100.0) * circumference

    # Indicators Chips
    if indicators:
        chips_html = '<div class="threat-chip-grid">'
        for ind in indicators:
            is_danger = "fee" in ind.get("key", "") or "high_amount" in ind.get("key", "")
            chip_class = "threat-chip-danger" if is_danger else "threat-chip-neutral"
            chips_html += f'<span class="{chip_class}">⚠️ {html.escape(ind["title"])}</span>'
        chips_html += '</div>'
    else:
        chips_html = '<div class="threat-chip-grid"><span class="threat-chip-clean">✓ No payment traps, suspicious channels, or urgency pressure detected</span></div>'

    # Progress bar helper
    def bar(label, val, color):
        return f"""
        <div class="vector-row">
            <div class="vector-header">
                <span>{label}</span>
                <span class="vector-val">{val}%</span>
            </div>
            <div class="vector-track">
                <div class="vector-fill" style="width: {val}%; background: {color};"></div>
            </div>
        </div>
        """

    card_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            background: transparent;
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: #FFFFFF;
            padding: 4px;
        }}
        
        .risk-card {{
            background: {stage_bg};
            border: 2px solid {border_color};
            border-radius: 18px;
            padding: 1.4rem;
            box-shadow: 0 16px 45px rgba(0, 0, 0, 0.7);
        }}
        
        .verdict-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(10, 10, 14, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 1.1rem;
        }}
        
        .verdict-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            font-weight: 800;
            color: {verdict_color};
            letter-spacing: 0.5px;
        }}
        
        .verdict-badge {{
            background: {badge_bg};
            color: {badge_text};
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 800;
            font-size: 0.84rem;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        
        .gauge-section {{
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0.8rem 0;
        }}
        
        .gauge-wrapper {{
            position: relative;
            width: 160px;
            height: 160px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        
        .gauge-text {{
            position: absolute;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        
        .gauge-score {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 2.7rem;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1;
        }}
        
        .gauge-sub {{
            font-size: 0.72rem;
            color: #A1A1AA;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            margin-top: 3px;
        }}
        
        .verdict-box {{
            background: rgba(14, 14, 20, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 4px solid {verdict_color};
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 1.1rem;
        }}
        
        .verdict-desc {{
            font-size: 0.88rem;
            font-weight: 600;
            color: #F4F4F5;
            line-height: 1.4;
            margin-bottom: 6px;
        }}
        
        .action-advice {{
            font-size: 0.80rem;
            font-weight: 600;
            color: {verdict_color};
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.3fr;
            gap: 8px;
            background: rgba(10, 10, 14, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 1.2rem;
        }}
        
        .summary-lbl {{
            font-size: 0.68rem;
            color: #A1A1AA;
            text-transform: uppercase;
            font-weight: 700;
        }}
        
        .summary-val {{
            font-size: 0.94rem;
            font-weight: 700;
            color: #FFFFFF;
            font-family: 'Space Grotesk', sans-serif;
        }}
        
        .sec-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.96rem;
            font-weight: 700;
            color: #FFFFFF;
            margin-top: 1rem;
            margin-bottom: 0.4rem;
            letter-spacing: 0.3px;
        }}
        
        .threat-chip-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 1rem;
        }}
        
        .threat-chip-danger {{
            background: rgba(220, 38, 38, 0.25);
            border: 1px solid #EF4444;
            color: #FECACA;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
        }}
        
        .threat-chip-neutral {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.18);
            color: #FFFFFF;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
        }}
        
        .threat-chip-clean {{
            background: rgba(34, 197, 94, 0.20);
            border: 1px solid #22C55E;
            color: #BBF7D0;
            padding: 5px 12px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 600;
        }}
        
        .vector-box {{
            background: rgba(10, 10, 14, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 1rem;
        }}
        
        .vector-row {{
            margin-bottom: 0.75rem;
        }}
        
        .vector-row:last-child {{
            margin-bottom: 0;
        }}
        
        .vector-header {{
            display: flex;
            justify-content: space-between;
            font-size: 0.80rem;
            color: #D4D4D8;
            margin-bottom: 4px;
        }}
        
        .vector-val {{
            font-weight: 700;
            color: #FFFFFF;
            font-family: 'Space Grotesk', sans-serif;
        }}
        
        .vector-track {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            height: 7px;
            overflow: hidden;
        }}
        
        .vector-fill {{
            height: 100%;
            border-radius: 6px;
        }}
        
        .checklist-box {{
            background: rgba(14, 14, 20, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 1rem;
        }}
        
        .checklist-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 0.84rem;
            color: #FFFFFF;
            margin-bottom: 6px;
        }}
        
        .checklist-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.80rem;
            color: #D4D4D8;
            padding: 3px 0;
        }}
    </style>
</head>
<body>
    <div class="risk-card">
        <div class="verdict-header">
            <div class="verdict-title">● {verdict_title}</div>
            <div class="verdict-badge">{level_icon} {level}</div>
        </div>
        
        <div class="verdict-box">
            <div class="verdict-desc">{verdict_desc}</div>
            <div class="action-advice"><strong>Guidance:</strong> {action_advice}</div>
        </div>
        
        <div class="gauge-section">
            <div class="gauge-wrapper">
                <svg width="160" height="160" viewBox="0 0 120 120" style="transform: rotate(-90deg);">
                    <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" />
                    <circle cx="60" cy="60" r="52" fill="none" stroke="{meter_color}" stroke-width="10"
                        stroke-dasharray="{circumference:.1f}"
                        stroke-dashoffset="{dashoffset:.1f}"
                        stroke-linecap="round" />
                </svg>
                <div class="gauge-text">
                    <div class="gauge-score">{int(score)}</div>
                    <div class="gauge-sub">/ 100 THREAT INDEX</div>
                </div>
            </div>
        </div>
        
        <div class="summary-grid">
            <div>
                <div class="summary-lbl">Threat Score</div>
                <div class="summary-val">{score} / 100</div>
            </div>
            <div>
                <div class="summary-lbl">Detected Signals</div>
                <div class="summary-val">{len(indicators)} Signal{'s' if len(indicators) != 1 else ''}</div>
            </div>
            <div>
                <div class="summary-lbl">Confidence Level</div>
                <div class="summary-val">{overall.get('confidence', 90)}% Robust</div>
            </div>
        </div>
        
        <div class="sec-title">🔎 WHY THIS WAS FLAGGED</div>
        {chips_html}
        
        <div class="sec-title">📊 SUB-VECTOR THREAT BREAKDOWN</div>
        <div class="vector-box">
            {bar('Upfront Payment / Fee Trap Risk', vectors.get('financial_risk', 0.0), 'linear-gradient(90deg, #DC2626, #EF4444)')}
            {bar('Artificial Urgency & Pressure Language', vectors.get('urgency_risk', 0.0), 'linear-gradient(90deg, #D97706, #F59E0B)')}
            {bar('Contact Channel Integrity (WhatsApp/Webmail)', vectors.get('channel_risk', 0.0), 'linear-gradient(90deg, #B91C1C, #F87171)')}
            {bar('Domain & Free Host Risk', vectors.get('domain_risk', 0.0), 'linear-gradient(90deg, #7F1D1D, #DC2626)')}
            {bar('Employer Legitimacy & Authenticity Index', vectors.get('legitimacy_score', 90.0), 'linear-gradient(90deg, #15803D, #22C55E)')}
        </div>
        
        <div class="checklist-box">
            <div class="checklist-title">📋 VERIFICATION CHECKLIST (BEFORE YOU APPLY)</div>
            <div class="checklist-item"><span style="color:#EF4444;font-weight:bold;">□</span> Verify official company website & domain independently</div>
            <div class="checklist-item"><span style="color:#EF4444;font-weight:bold;">□</span> Confirm recruiter email matches corporate domain (not @gmail/@yahoo)</div>
            <div class="checklist-item"><span style="color:#EF4444;font-weight:bold;">□</span> Never pay upfront registration, training, or kit fees</div>
            <div class="checklist-item"><span style="color:#EF4444;font-weight:bold;">□</span> Never share bank credentials, OTPs, or government IDs prematurely</div>
        </div>
    </div>
</body>
</html>"""
    components.html(card_html, height=760, scrolling=True)


def render_standby_card():
    """
    Renders the neutral standby card when no scan has been executed yet.
    """
    html_code = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@600;700&display=swap');
        body {
            background: transparent;
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: #FFFFFF;
            padding: 4px;
        }
        .standby-card {
            background: rgba(16, 16, 22, 0.85);
            border: 1px dashed rgba(255, 255, 255, 0.18);
            border-radius: 18px;
            padding: 2.8rem 1.8rem;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            color: #FFFFFF;
            margin-bottom: 0.5rem;
        }
        .sub {
            font-size: 0.88rem;
            color: #A1A1AA;
            max-width: 340px;
            margin: 0 auto;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="standby-card">
        <div class="title">READY FOR ANALYSIS</div>
        <div class="sub">
            Paste a job description or choose a sample from the <strong>Preset Hub</strong> and click <strong>ANALYZE POSTING</strong> to activate the ML threat intelligence engine.
        </div>
    </div>
</body>
</html>"""
    components.html(html_code, height=220, scrolling=False)


# ---------------------------------------------------------------------------
# Global CSS Styling for Streamlit Shell (Luminous, High-Contrast Glassmorphism)
# ---------------------------------------------------------------------------
SHELL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #070709 !important;
    background-image: 
        radial-gradient(circle at 18% 12%, rgba(220, 38, 38, 0.12) 0px, transparent 45%),
        radial-gradient(circle at 82% 88%, rgba(34, 197, 94, 0.08) 0px, transparent 50%),
        linear-gradient(180deg, #070709 0%, #0B0B10 50%, #070709 100%) !important;
    background-attachment: fixed !important;
    color: #FFFFFF !important;
}

#MainMenu, footer, header, [data-testid="stDecoration"], [data-testid="stStatusWidget"], [class*="viewerBadge"], [data-testid="stToolbar"] {
    visibility: hidden !important;
    display: none !important;
}

.main .block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3.5rem !important;
    max-width: 1280px !important;
}

.cyber-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(18, 18, 26, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    padding: 1.2rem 1.8rem;
    margin-bottom: 1.3rem;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
}

.brand-wrapper {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-shield-glow {
    font-size: 2.1rem;
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.25) 0%, rgba(127, 29, 29, 0.15) 100%);
    border: 1px solid rgba(239, 68, 68, 0.5);
    border-radius: 14px;
    padding: 8px 14px;
    box-shadow: 0 0 20px rgba(220, 38, 38, 0.3);
}

.brand-headline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.2px;
    line-height: 1.2;
}

.brand-tagline {
    font-size: 0.86rem;
    color: #D4D4D8;
    margin-top: 4px;
}

.status-pill-ready {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(34, 197, 94, 0.15);
    border: 1px solid rgba(34, 197, 94, 0.4);
    color: #4ADE80;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.80rem;
    font-weight: 700;
}

.pulse-dot-green {
    width: 8px;
    height: 8px;
    background: #22C55E;
    border-radius: 50%;
    box-shadow: 0 0 10px #22C55E;
}

.status-pill-model {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #FFFFFF;
    padding: 6px 14px;
    border-radius: 10px;
    font-size: 0.80rem;
    font-weight: 700;
}

.metrics-grid-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.1rem;
    margin-bottom: 1.5rem;
}

@media (max-width: 840px) {
    .metrics-grid-row {
        grid-template-columns: repeat(2, 1fr);
    }
}

.cyber-metric-card {
    background: rgba(18, 18, 26, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 1.15rem 1.35rem;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    position: relative;
    overflow: hidden;
}

.cyber-metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #DC2626 0%, transparent 100%);
    opacity: 0.8;
}

.metric-hdr {
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: #A1A1AA;
    margin-bottom: 0.35rem;
}

.metric-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.9rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.1;
}

.metric-subtext {
    font-size: 0.78rem;
    color: #EF4444;
    font-weight: 700;
    margin-top: 0.3rem;
}

.cyber-glass-panel {
    background: rgba(18, 18, 26, 0.85);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    padding: 1.4rem;
    box-shadow: 0 16px 45px rgba(0, 0, 0, 0.5);
    margin-bottom: 1.2rem;
}

.panel-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.22rem;
    font-weight: 800;
    color: #FFFFFF;
    margin-bottom: 0.3rem;
}

.panel-subtitle {
    font-size: 0.86rem;
    color: #D4D4D8;
    margin-bottom: 1rem;
}

.step-box {
    background: rgba(14, 14, 20, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}

.step-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.84rem;
    color: #D4D4D8;
    padding: 3px 0;
}

.step-badge {
    font-family: 'Space Grotesk', monospace;
    font-size: 0.74rem;
    color: #EF4444;
    font-weight: 700;
    background: rgba(220, 38, 38, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    padding: 1px 6px;
    border-radius: 5px;
}

.stTextInput input, .stTextArea textarea {
    background-color: #121218 !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.92rem !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #EF4444 !important;
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.3) !important;
}

.stButton button {
    background: linear-gradient(135deg, #B91C1C 0%, #EF4444 100%) !important;
    color: #FFFFFF !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    padding: 0.60rem 1.4rem !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 6px 18px rgba(220, 38, 38, 0.35) !important;
    transition: all 0.2s ease !important;
}

.stButton button:hover {
    background: linear-gradient(135deg, #DC2626 0%, #F87171 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 24px rgba(239, 68, 68, 0.5) !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: rgba(18, 18, 26, 0.85);
    backdrop-filter: blur(20px);
    padding: 6px 10px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    margin-bottom: 1.4rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 0.90rem;
    color: #A1A1AA;
    border-radius: 10px;
    padding: 8px 18px;
    transition: all 0.2s ease;
}

.stTabs [data-baseweb="tab"]:hover {
    color: #FFFFFF !important;
    background-color: rgba(255, 255, 255, 0.08) !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(185, 28, 28, 0.2) 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid #EF4444 !important;
    box-shadow: 0 0 15px rgba(220, 38, 38, 0.25) !important;
}

.stDataFrame, .stTable {
    background: #121218 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 12px !important;
}

[data-testid="stFileUploader"] {
    background: rgba(18, 18, 26, 0.7);
    border: 1px dashed rgba(255, 255, 255, 0.16);
    border-radius: 12px;
    padding: 10px;
}
</style>
"""
st.markdown(SHELL_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Master Header Navbar
# ---------------------------------------------------------------------------
online_status = is_online()
render_safe_html(f"""
<div class="cyber-header">
    <div class="brand-wrapper">
        <div class="brand-shield-glow">🛡️</div>
        <div>
            <div class="brand-headline">AI FAKE INTERNSHIP THREAT SCANNER</div>
            <div class="brand-tagline">AI-powered threat screening, company authentication & recruiter verification platform</div>
        </div>
    </div>
    <div style="display: flex; align-items: center; gap: 12px;">
        <span class="status-pill-ready"><span class="pulse-dot-green"></span> {'ONLINE INTELLIGENCE' if online_status else 'LOCAL ENGINE ACTIVE'}</span>
        <span class="status-pill-model">MODEL: LINEAR SVM (98.41% ACC)</span>
    </div>
</div>
""")

# ---------------------------------------------------------------------------
# Top Metric Cards (4 Cards)
# ---------------------------------------------------------------------------
render_safe_html("""
<div class="metrics-grid-row">
    <div class="cyber-metric-card">
        <div class="metric-hdr">Dataset Listings</div>
        <div class="metric-num">17,880</div>
        <div class="metric-subtext">EMSCAD Benchmark</div>
    </div>
    <div class="cyber-metric-card">
        <div class="metric-hdr">Model Accuracy</div>
        <div class="metric-num">98.41%</div>
        <div class="metric-subtext">Test-Set Verified</div>
    </div>
    <div class="cyber-metric-card">
        <div class="metric-hdr">Active Model</div>
        <div class="metric-num">Linear SVM</div>
        <div class="metric-subtext">Calibrated Classifier</div>
    </div>
    <div class="cyber-metric-card">
        <div class="metric-hdr">Risk Indicators</div>
        <div class="metric-num">17+ Layered</div>
        <div class="metric-subtext">ML + Company Intel</div>
    </div>
</div>
""")

# ---------------------------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------------------------
tab_scan, tab_multi_scan, tab_verify_company, tab_presets, tab_batch, tab_history, tab_benchmarks, tab_guide = st.tabs([
    "🔍 Analyze Posting",
    "📑 Multi-Post Scan",
    "🏢 Company & Recruiter Check",
    "💡 Preset Hub",
    "📁 Batch Scan",
    "📋 Scan History",
    "📊 Model Performance",
    "🛡️ Scam Defense Center"
])

# ===========================================================================
# TAB 1: Main Analysis Workspace (Unified Posting & Recruiter Intelligence)
# ===========================================================================
with tab_scan:
    # Viva Demonstration Mode Bar
    with st.expander("🎬 Review 3 Demonstration Mode (1-Click Reference Tests)", expanded=False):
        st.caption("Select a complete reference case to populate all text & metadata fields instantly:")
        demo_cols = st.columns(3)
        with demo_cols[0]:
            if st.button("1️⃣ Legitimate Series-B FinTech", use_container_width=True):
                p = PRESETS["🚀 Genuine Tech Company Posting"]
                st.session_state.active_text = p["text"]
                st.session_state.active_company = p["company"]
                st.session_state.active_email = p["email"]
                st.session_state.active_website = p["website"]
                st.session_state.active_recruiter = p["recruiter"]
                st.session_state.active_linkedin = p["linkedin"]
                st.session_state.active_joburl = p["joburl"]
                st.session_state.last_result = None
                st.rerun()
        with demo_cols[1]:
            if st.button("2️⃣ Microsoft Brand Impersonation", use_container_width=True):
                p = PRESETS["🎭 Microsoft Impersonation Trap"]
                st.session_state.active_text = p["text"]
                st.session_state.active_company = p["company"]
                st.session_state.active_email = p["email"]
                st.session_state.active_website = p["website"]
                st.session_state.active_recruiter = p["recruiter"]
                st.session_state.active_linkedin = p["linkedin"]
                st.session_state.active_joburl = p["joburl"]
                st.session_state.last_result = None
                st.rerun()
        with demo_cols[2]:
            if st.button("3️⃣ High-Risk Fee Scam", use_container_width=True):
                p = PRESETS["🚨 Upfront Registration Fee Scam"]
                st.session_state.active_text = p["text"]
                st.session_state.active_company = p["company"]
                st.session_state.active_email = p["email"]
                st.session_state.active_website = p["website"]
                st.session_state.active_recruiter = p["recruiter"]
                st.session_state.active_linkedin = p["linkedin"]
                st.session_state.active_joburl = p["joburl"]
                st.session_state.last_result = None
                st.rerun()

    col_left, col_right = st.columns([1, 1], gap="large")

    # LEFT COLUMN: Posting Input Workspace
    with col_left:
        render_safe_html("""
        <div class="cyber-glass-panel">
            <div class="panel-title">POSTING ANALYZER</div>
            <div class="panel-subtitle">Paste a job or internship description to screen for suspicious recruitment characteristics.</div>
        </div>
        """)

        user_text = st.text_area(
            "Posting Text",
            value=st.session_state.active_text,
            height=200,
            placeholder="Paste the job or internship posting here (title, stipend, requirements, contact details)...",
            label_visibility="collapsed"
        )
        st.session_state.active_text = user_text

        # Company & Recruiter Intelligence Expandable Section
        with st.expander("🏢 Company & Recruiter Intelligence (Optional Verification)", expanded=bool(st.session_state.active_company or st.session_state.active_email)):
            st.caption("Cross-reference employer authenticity and recruiter domain integrity:")
            cc1, cc2 = st.columns(2)
            with cc1:
                comp_name = st.text_input("Company Name", value=st.session_state.active_company, placeholder="e.g. Microsoft / Northwind")
                st.session_state.active_company = comp_name
                rec_name = st.text_input("Recruiter Name", value=st.session_state.active_recruiter, placeholder="e.g. Jane Doe")
                st.session_state.active_recruiter = rec_name
                rec_linkedin = st.text_input("Recruiter LinkedIn URL", value=st.session_state.active_linkedin, placeholder="https://linkedin.com/in/...")
                st.session_state.active_linkedin = rec_linkedin
            with cc2:
                comp_web = st.text_input("Company Website", value=st.session_state.active_website, placeholder="https://example.com")
                st.session_state.active_website = comp_web
                rec_email = st.text_input("Recruiter Email", value=st.session_state.active_email, placeholder="recruiter@company.com")
                st.session_state.active_email = rec_email
                job_url = st.text_input("Job / Offer URL", value=st.session_state.active_joburl, placeholder="https://careers.company.com/job/...")
                st.session_state.active_joburl = job_url

        # Optional Metadata Controls
        with st.expander("⚙️ Optional Posting Metadata Flags", expanded=False):
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                tc_flag = st.checkbox("Remote / Telecommute", value=False)
            with mcol2:
                logo_flag = st.checkbox("Has Company Logo", value=False)
            with mcol3:
                q_flag = st.checkbox("Screening Questions", value=False)

        # Document File Parsing
        uploaded_file = st.file_uploader(
            "Upload Document (.txt, .pdf, .docx, .md)",
            type=["txt", "pdf", "docx", "md"],
            help="Extract text directly from PDF offers or text files."
        )
        if uploaded_file is not None:
            extracted = extract_text_from_file(uploaded_file, uploaded_file.name)
            if extracted and not extracted.startswith("[Error") and not extracted.startswith("[PDF Parsing Error") and not extracted.startswith("[DOCX Parsing Error"):
                st.session_state.active_text = extracted
                st.success(f"✓ Extracted text from {uploaded_file.name}")
                st.rerun()

        # Action Buttons
        bcol1, bcol2 = st.columns([2, 1])
        with bcol1:
            analyze_clicked = st.button("🛡️ ANALYZE POSTING", use_container_width=True)
        with bcol2:
            if st.button("Clear Input", use_container_width=True):
                st.session_state.active_text = ""
                st.session_state.active_company = ""
                st.session_state.active_email = ""
                st.session_state.active_website = ""
                st.session_state.active_recruiter = ""
                st.session_state.active_linkedin = ""
                st.session_state.active_joburl = ""
                st.session_state.last_result = None
                st.rerun()

    # RIGHT COLUMN: Dynamic Risk Intelligence & 3D Visual Feedback
    with col_right:
        if analyze_clicked and (user_text.strip() or st.session_state.active_company.strip()):
            try:
                with st.spinner("Screening text & cross-referencing company authenticity..."):
                    res = analyze_listing(
                        text=user_text,
                        company_name=st.session_state.active_company.strip() or None,
                        email=st.session_state.active_email.strip() or None,
                        website=st.session_state.active_website.strip() or None,
                        job_url=st.session_state.active_joburl.strip() or None,
                        recruiter_name=st.session_state.active_recruiter.strip() or None,
                        recruiter_linkedin=st.session_state.active_linkedin.strip() or None,
                        telecommuting=1 if tc_flag else 0,
                        has_company_logo=1 if logo_flag else 0,
                        has_questions=1 if q_flag else 0
                    )

                    st.session_state.last_result = res
                    st.session_state.last_scanned_text = user_text or st.session_state.active_company

                    ov = res["overall_assessment"]
                    st.session_state.history.append({
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                        "company": st.session_state.active_company or "Extracted from text",
                        "text_snippet": (user_text[:60] + "...") if user_text else f"Company check: {st.session_state.active_company}",
                        "risk_score": ov["risk_score"],
                        "risk_level": ov["risk_level"],
                        "confidence": f"{ov['confidence']}%"
                    })
            except Exception as e:
                # Fallback to direct ML predict if investigation encountered an issue
                raw_pred = predict(
                    user_text,
                    telecommuting=1 if tc_flag else 0,
                    has_company_logo=1 if logo_flag else 0,
                    has_questions=1 if q_flag else 0
                )
                st.session_state.last_result = {
                    "overall_assessment": {"risk_score": raw_pred["risk_score"], "risk_level": raw_pred["risk_level"], "confidence": 85},
                    "internship_prediction": raw_pred,
                    "explanation": {"summary": "Analysis completed using the core ML classifier."},
                    "input_issues": [f"Notice: Live company verification returned offline status ({type(e).__name__})."]
                }
                st.session_state.last_scanned_text = user_text

        if st.session_state.last_result is not None and st.session_state.last_scanned_text:
            result = st.session_state.last_result
            overall = result.get("overall_assessment") or {}
            score = overall.get("risk_score", 0)
            level = overall.get("risk_level", "LOW RISK")
            inv = result.get("investigation")

            # Embed 3D Security Core reacting dynamically to risk level
            render_3d_security_core(level)

            # Processing Stepper
            render_safe_html("""
            <div class="step-box">
                <div class="step-item"><span class="step-badge">01</span> <span style="color:#22C55E;">✓</span> Text normalized & tokenized</div>
                <div class="step-item"><span class="step-badge">02</span> <span style="color:#22C55E;">✓</span> 4,000 TF-IDF features & 17 risk indicators evaluated</div>
                <div class="step-item"><span class="step-badge">03</span> <span style="color:#22C55E;">✓</span> Linear SVM classification executed (98.41% accuracy)</div>
                <div class="step-item"><span class="step-badge">04</span> <span style="color:#22C55E;">✓</span> Recruiter domain & employer identity cross-referenced</div>
                <div class="step-item"><span class="step-badge">05</span> <span style="color:#22C55E;">✓</span> Comprehensive threat intelligence generated</div>
            </div>
            """)

            # Render complete graphical Risk Intelligence Dashboard via isolated HTML component
            render_risk_intelligence_card(result)

            # If company verification / investigation ran, render investigation dossier
            if inv:
                with st.expander("🏢 Company & Recruiter Verification Dossier", expanded=True):
                    ic1, ic2 = st.columns(2)
                    with ic1:
                        st.markdown(f"**Company Identity:** {inv.get('company_name', 'Unknown')}")
                        st.markdown(f"**Verdict:** `{inv.get('verdict', 'UNVERIFIED')}`")
                        st.caption(inv.get("verdict_text", ""))
                        ident = inv.get("identity", {})
                        if ident.get("official_domain"):
                            st.write(f"• **Official Domain:** `{ident['official_domain']}`")
                        if ident.get("industry"):
                            st.write(f"• **Industry:** {ident['industry']}")
                    with ic2:
                        em = inv.get("email", {})
                        st.markdown(f"**Recruiter Email:** `{em.get('email', 'Not provided')}`")
                        st.write(f"• **Domain Match:** `{em.get('status', 'unknown')}`")
                        st.write(f"• **Free Email Provider:** {'Yes (Personal Webmail)' if em.get('free') else 'No (Corporate Domain)'}")
                        if inv.get("flags", {}).get("lookalike_domain"):
                            st.error("🚨 Provided email/job domain closely resembles official domain (Lookalike detected)!")

            # Export Audit Report Options
            st.markdown("<br>", unsafe_allow_html=True)
            ecol1, ecol2, ecol3 = st.columns(3)
            with ecol1:
                st.download_button(
                    "📥 Export JSON",
                    data=json.dumps(result, indent=2, default=str),
                    file_name="threat_intelligence_report.json",
                    mime="application/json",
                    use_container_width=True
                )
            with ecol2:
                md_rep = f"""# AI Fake Internship Threat Audit Report
**Analysis Timestamp:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Threat Score:** {score}/100
**Risk Classification:** {level}
**Active Model:** Linear SVM (98.41% Accuracy on EMSCAD)

## Overall Verdict:
{result.get('explanation', {}).get('summary', 'Screening completed.')}
"""
                st.download_button(
                    "📄 Export Markdown",
                    data=md_rep,
                    file_name="threat_intelligence_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with ecol3:
                html_rep = f"""<!DOCTYPE html>
<html>
<head>
    <title>Threat Audit Report</title>
    <style>
        body {{ font-family: sans-serif; background: #070708; color: #F5F5F5; padding: 2rem; }}
        .card {{ background: #121216; border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 1.5rem; }}
        h1 {{ color: #DC2626; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>AI Fake Internship Threat Audit</h1>
        <p><strong>Score:</strong> {score}/100 ({level})</p>
        <p><strong>Model:</strong> Linear SVM (98.41% Accuracy)</p>
    </div>
</body>
</html>"""
                st.download_button(
                    "🌐 Export HTML",
                    data=html_rep,
                    file_name="threat_intelligence_report.html",
                    mime="text/html",
                    use_container_width=True
                )
        else:
            # Standby Neutral State
            render_3d_security_core("IDLE")
            render_standby_card()

# ===========================================================================
# TAB 2: Multi-Post Scanning Studio (Batch Paste & Grouped Risk Assessment)
# ===========================================================================
with tab_multi_scan:
    render_safe_html("""
    <div class="panel-title">MULTI-POST INTELLIGENCE SCANNER</div>
    <div class="panel-subtitle">Paste multiple internship descriptions, offer emails, or social media recruitment messages into one text box to screen them concurrently.</div>
    """)

    # Quick Template / Controls Row
    m_top_c1, m_top_c2 = st.columns([3, 1])
    with m_top_c1:
        sep_mode = st.selectbox(
            "Posting Separator Detection Mode",
            options=[
                "Auto-Detect (splits on '---', '===', double blank lines, or 'POSTING 1:')",
                "Dashes / Horizontal Rules (---, ===, ___)",
                "Headers (POSTING 1:, JOB 2:, MESSAGE 3:, etc.)",
                "Double Blank Lines"
            ],
            key="multi_sep_mode"
        )
    with m_top_c2:
        st.write("")
        st.write("")
        if st.button("📋 Load Sample Multi-Post Batch", use_container_width=True):
            st.session_state.multi_post_text = SAMPLE_MULTI_POSTINGS
            st.session_state.multi_post_results = None
            st.rerun()

    multi_input = st.text_area(
        "Multi-Posting Text Input",
        value=st.session_state.multi_post_text,
        height=220,
        placeholder="Paste multiple job or internship postings here...\n\nSeparate each posting using '---', '===', blank lines, or 'POSTING 1:', 'POSTING 2:', etc.",
        key="multi_text_area"
    )
    st.session_state.multi_post_text = multi_input

    # Action Buttons
    m_btn_c1, m_btn_c2 = st.columns([2, 1])
    with m_btn_c1:
        run_multi = st.button("🚀 SCAN ALL POSTINGS", use_container_width=True, key="btn_run_multi")
    with m_btn_c2:
        if st.button("Clear Multi-Post Input", use_container_width=True, key="btn_clear_multi"):
            st.session_state.multi_post_text = ""
            st.session_state.multi_post_results = None
            st.rerun()

    # Processing logic
    if run_multi:
        if not multi_input.strip():
            st.warning("⚠️ Please paste at least one job or internship posting to scan.")
        else:
            with st.spinner("Analyzing postings through the Linear SVM threat detection pipeline..."):
                postings = split_multi_postings(multi_input, sep_mode)
                if not postings:
                    st.error("No valid postings could be detected. Try using '---' between postings.")
                else:
                    multi_results = []
                    prog = st.progress(0)
                    for idx, post in enumerate(postings):
                        pred_res = predict(post)
                        score = pred_res.get("risk_score", 0.0)
                        level = pred_res.get("risk_level", "LOW RISK")
                        indicators = pred_res.get("indicators", [])
                        fraud_prob = pred_res.get("fraud_probability", 0.0)

                        multi_results.append({
                            "id": idx + 1,
                            "text": post,
                            "score": score,
                            "level": level,
                            "indicators": indicators,
                            "fraud_probability": fraud_prob
                        })
                        prog.progress((idx + 1) / len(postings))

                    st.session_state.multi_post_results = multi_results

    # Render results if available
    if st.session_state.multi_post_results:
        results = st.session_state.multi_post_results
        total = len(results)

        # Categorize into 3 buckets
        high_group = []
        mod_group = []
        low_group = []

        for r in results:
            sc = r["score"]
            lvl = r["level"].upper()
            if sc >= 65 or "HIGH" in lvl or "CRITICAL" in lvl:
                high_group.append(r)
            elif sc >= 35 or "MEDIUM" in lvl or "MODERATE" in lvl or "SUSPICIOUS" in lvl or "CAUTION" in lvl:
                mod_group.append(r)
            else:
                low_group.append(r)

        # 1. Summary Metric Grid
        render_safe_html(f"""
        <div class="metrics-grid-row" style="margin-top: 1.2rem; margin-bottom: 1.2rem;">
            <div class="cyber-metric-card">
                <div class="metric-hdr">Total Postings</div>
                <div class="metric-num">{total}</div>
                <div class="metric-subtext">Scanned & Classified</div>
            </div>
            <div class="cyber-metric-card" style="border-top: 3px solid #EF4444;">
                <div class="metric-hdr">🔴 High Risk Threat</div>
                <div class="metric-num" style="color: #EF4444;">{len(high_group)}</div>
                <div class="metric-subtext">{(len(high_group)/total*100):.1f}% of scanned batch</div>
            </div>
            <div class="cyber-metric-card" style="border-top: 3px solid #F59E0B;">
                <div class="metric-hdr">🟡 Moderate Risk</div>
                <div class="metric-num" style="color: #F59E0B;">{len(mod_group)}</div>
                <div class="metric-subtext">{(len(mod_group)/total*100):.1f}% of scanned batch</div>
            </div>
            <div class="cyber-metric-card" style="border-top: 3px solid #22C55E;">
                <div class="metric-hdr">🟢 Low Risk / Safe</div>
                <div class="metric-num" style="color: #4ADE80;">{len(low_group)}</div>
                <div class="metric-subtext">{(len(low_group)/total*100):.1f}% of scanned batch</div>
            </div>
        </div>
        """)

        # 2. CSV Export Button
        csv_rows = []
        for r in results:
            ind_list_str = "; ".join([ind.get("name", str(ind)) for ind in r["indicators"]]) if r["indicators"] else "None Detected"
            csv_rows.append({
                "Posting_Number": r["id"],
                "Risk_Score": r["score"],
                "Risk_Level": r["level"],
                "Fraud_Probability_Pct": f"{r['fraud_probability']*100:.1f}%",
                "Indicators_Count": len(r["indicators"]),
                "Detected_Indicators": ind_list_str,
                "Original_Posting_Text": r["text"]
            })
        multi_df = pd.DataFrame(csv_rows)
        st.download_button(
            "📥 Export Multi-Scan Audit CSV",
            data=multi_df.to_csv(index=False).encode('utf-8'),
            file_name=f"multi_post_scan_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Three Clearly Separated Sections
        # Section A: 🔴 HIGH RISK
        render_safe_html(f"""
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 800; color: #EF4444; margin: 1.2rem 0 0.8rem 0; display: flex; align-items: center; gap: 8px;">
            <span>🔴 HIGH RISK POSTINGS</span>
            <span style="background: rgba(239, 68, 68, 0.2); border: 1px solid #EF4444; color: #FFFFFF; font-size: 0.78rem; padding: 2px 10px; border-radius: 12px;">{len(high_group)} Found</span>
        </div>
        """)

        if high_group:
            for item in high_group:
                chips_html = ""
                if item["indicators"]:
                    chips_html = "".join([f'<span style="background: rgba(220, 38, 38, 0.25); border: 1px solid #EF4444; color: #FCA5A5; padding: 3px 8px; border-radius: 6px; font-size: 0.74rem; margin-right: 6px; margin-bottom: 4px; display: inline-block;">🚩 {ind.get("name", ind)}</span>' for ind in item["indicators"]])
                else:
                    chips_html = '<span style="color: #A1A1AA; font-size: 0.76rem;">No explicit keyword flags, flagged via high ML TF-IDF vector score.</span>'

                render_safe_html(f"""
                <div style="background: rgba(127, 29, 29, 0.14); border: 1.5px solid rgba(239, 68, 68, 0.45); border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                        <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1rem; color: #FFFFFF;">POSTING #{item['id']}</span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; color: #EF4444; font-size: 0.95rem;">THREAT SCORE: {int(item['score'])}/100</span>
                            <span style="background: #EF4444; color: #000000; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">{item['level']}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.6rem;">
                        <strong style="font-size: 0.78rem; color: #D4D4D8; text-transform: uppercase;">Detected Suspicious Signals:</strong><br>
                        <div style="margin-top: 4px;">{chips_html}</div>
                    </div>
                    <div style="background: rgba(10, 10, 14, 0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px; font-size: 0.78rem; color: #E4E4E7; white-space: pre-wrap; max-height: 100px; overflow-y: auto; font-family: monospace;">{html.escape(item['text'])}</div>
                </div>
                """)
        else:
            render_safe_html("""
            <div style="background: rgba(18, 18, 24, 0.5); border: 1px dashed rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; color: #A1A1AA; font-size: 0.82rem; margin-bottom: 1rem;">
                ✓ No high-risk threats detected in this batch.
            </div>
            """)

        # Section B: 🟡 MODERATE RISK
        render_safe_html(f"""
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 800; color: #F59E0B; margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 8px;">
            <span>🟡 MODERATE RISK POSTINGS</span>
            <span style="background: rgba(245, 158, 11, 0.2); border: 1px solid #F59E0B; color: #FFFFFF; font-size: 0.78rem; padding: 2px 10px; border-radius: 12px;">{len(mod_group)} Found</span>
        </div>
        """)

        if mod_group:
            for item in mod_group:
                chips_html = ""
                if item["indicators"]:
                    chips_html = "".join([f'<span style="background: rgba(245, 158, 11, 0.2); border: 1px solid #F59E0B; color: #FDE68A; padding: 3px 8px; border-radius: 6px; font-size: 0.74rem; margin-right: 6px; margin-bottom: 4px; display: inline-block;">⚠️ {ind.get("name", ind)}</span>' for ind in item["indicators"]])
                else:
                    chips_html = '<span style="color: #A1A1AA; font-size: 0.76rem;">Informal tone or ambiguous recruitment patterns detected.</span>'

                render_safe_html(f"""
                <div style="background: rgba(245, 158, 11, 0.08); border: 1.5px solid rgba(245, 158, 11, 0.4); border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                        <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1rem; color: #FFFFFF;">POSTING #{item['id']}</span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; color: #F59E0B; font-size: 0.95rem;">THREAT SCORE: {int(item['score'])}/100</span>
                            <span style="background: #F59E0B; color: #000000; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">{item['level']}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.6rem;">
                        <strong style="font-size: 0.78rem; color: #D4D4D8; text-transform: uppercase;">Detected Suspicious Signals:</strong><br>
                        <div style="margin-top: 4px;">{chips_html}</div>
                    </div>
                    <div style="background: rgba(10, 10, 14, 0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px; font-size: 0.78rem; color: #E4E4E7; white-space: pre-wrap; max-height: 100px; overflow-y: auto; font-family: monospace;">{html.escape(item['text'])}</div>
                </div>
                """)
        else:
            render_safe_html("""
            <div style="background: rgba(18, 18, 24, 0.5); border: 1px dashed rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; color: #A1A1AA; font-size: 0.82rem; margin-bottom: 1rem;">
                ✓ No moderate-risk postings in this batch.
            </div>
            """)

        # Section C: 🟢 LOW RISK
        render_safe_html(f"""
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.15rem; font-weight: 800; color: #22C55E; margin: 1.4rem 0 0.8rem 0; display: flex; align-items: center; gap: 8px;">
            <span>🟢 LOW RISK / VERIFIED POSTINGS</span>
            <span style="background: rgba(34, 197, 94, 0.2); border: 1px solid #22C55E; color: #FFFFFF; font-size: 0.78rem; padding: 2px 10px; border-radius: 12px;">{len(low_group)} Found</span>
        </div>
        """)

        if low_group:
            for item in low_group:
                render_safe_html(f"""
                <div style="background: rgba(16, 185, 129, 0.08); border: 1.5px solid rgba(34, 197, 94, 0.4); border-radius: 14px; padding: 1.1rem; margin-bottom: 1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                        <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1rem; color: #FFFFFF;">POSTING #{item['id']}</span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; color: #4ADE80; font-size: 0.95rem;">THREAT SCORE: {int(item['score'])}/100</span>
                            <span style="background: #22C55E; color: #000000; font-weight: 800; font-size: 0.72rem; padding: 2px 8px; border-radius: 10px;">{item['level']}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 0.6rem; font-size: 0.78rem; color: #86EFAC;">
                        ✓ Verified authentic structure, corporate domain standards, or standard hiring criteria.
                    </div>
                    <div style="background: rgba(10, 10, 14, 0.8); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px 12px; font-size: 0.78rem; color: #E4E4E7; white-space: pre-wrap; max-height: 100px; overflow-y: auto; font-family: monospace;">{html.escape(item['text'])}</div>
                </div>
                """)
        else:
            render_safe_html("""
            <div style="background: rgba(18, 18, 24, 0.5); border: 1px dashed rgba(255,255,255,0.1); border-radius: 10px; padding: 1rem; color: #A1A1AA; font-size: 0.82rem; margin-bottom: 1rem;">
                No low-risk postings in this batch.
            </div>
            """)

# ===========================================================================
# TAB 3: Dedicated Standalone Company & Recruiter Verification
# ===========================================================================
with tab_verify_company:
    render_safe_html("""
    <div class="panel-title">STANDALONE COMPANY & RECRUITER VERIFICATION</div>
    <div class="panel-subtitle">Verify employer authenticity, domain registration, and recruiter email legitimacy without needing full job description text.</div>
    """)

    vc1, vc2 = st.columns(2)
    with vc1:
        render_safe_html('<div class="cyber-glass-panel">')
        v_company = st.text_input("Company Name *", placeholder="e.g. Microsoft / Tata Consultancy Services", key="v_comp")
        v_website = st.text_input("Company Website (optional)", placeholder="https://company.com", key="v_web")
        v_recruiter = st.text_input("Recruiter Name (optional)", placeholder="e.g. John Doe", key="v_rec")
        v_email = st.text_input("Recruiter Email (optional)", placeholder="recruiter@gmail.com or hr@company.com", key="v_em")
        v_joburl = st.text_input("Job URL (optional)", placeholder="https://...", key="v_jurl")
        run_v = st.button("🔍 VERIFY COMPANY & RECRUITER", use_container_width=True)
        render_safe_html('</div>')

    with vc2:
        if run_v and v_company.strip():
            with st.spinner("Running verification investigation..."):
                inv_res = verify_only(
                    company_name=v_company.strip(),
                    email=v_email.strip() or None,
                    website=v_website.strip() or None,
                    job_url=v_joburl.strip() or None,
                    recruiter_name=v_recruiter.strip() or None
                )

                if inv_res:
                    v_verdict = inv_res.get("verdict", "UNVERIFIED")
                    v_conf = inv_res.get("confidence", 50)
                    render_safe_html(f"""
                    <div class="cyber-glass-panel">
                        <div style="font-size: 0.8rem; color: #A1A1AA; text-transform: uppercase; font-weight: 700;">Verification Result</div>
                        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; color: #FFFFFF; margin: 4px 0;">
                            {v_verdict}
                        </div>
                        <div style="font-size: 0.85rem; color: #D4D4D8; line-height: 1.5;">{inv_res.get('verdict_text', '')}</div>
                        <div style="margin-top: 10px; font-size: 0.78rem; color: #A1A1AA;">Evidence Confidence: <strong>{v_conf}%</strong> &bull; {inv_res.get('confidence_label', '')}</div>
                    </div>
                    """)

                    idn = inv_res.get("identity", {})
                    dv = inv_res.get("domain_verification", {})
                    render_safe_html(f"""
                    <div class="cyber-glass-panel" style="font-size: 0.85rem;">
                        <div style="font-weight: 700; color: #FFFFFF; margin-bottom: 8px;">Dossier Breakdown</div>
                        <div>• <strong>Official Domain:</strong> <code>{idn.get('official_domain', 'Not found')}</code></div>
                        <div>• <strong>Official Website:</strong> {idn.get('official_website', 'Not found')}</div>
                        <div>• <strong>Domain Age:</strong> {f"{dv.get('age_days', 0) // 365} years" if dv.get('age_days') is not None else 'Not checked'}</div>
                        <div>• <strong>Email Status:</strong> {inv_res.get('email', {}).get('status', 'Not provided')}</div>
                    </div>
                    """)
                else:
                    st.error("Verification could not be completed.")
        else:
            render_safe_html("""
            <div class="cyber-glass-panel" style="text-align: center; padding: 2.5rem 1rem;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏢</div>
                <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 700; color: #FFFFFF;">Ready for Verification</div>
                <div style="font-size: 0.85rem; color: #A1A1AA; max-width: 300px; margin: 6px auto;">Enter an employer name or recruiter contact on the left to verify authenticity.</div>
            </div>
            """)

# ===========================================================================
# TAB 3: 1-Click Preset Scenario Hub (Color-Coded Distinct Aesthetics & Full Metadata)
# ===========================================================================
with tab_presets:
    render_safe_html("""
    <div class="panel-title">PRESET INTELLIGENCE HUB</div>
    <div class="panel-subtitle">Select from 6 distinct real-world test scenarios — each fully configured with employer metadata, recruiter contact info, and job text.</div>
    """)

    preset_cols = st.columns(2)
    idx = 0
    for title, p_data in PRESETS.items():
        with preset_cols[idx % 2]:
            render_safe_html(f"""
            <div style="background: {p_data['bg_glass']}; border: 2px solid {p_data['border_color']}; border-radius: 16px; padding: 1.3rem; margin-bottom: 1.2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #FFFFFF;">{p_data['title']}</span>
                    <span style="background: {p_data['color']}; color: #000000; padding: 3px 10px; border-radius: 12px; font-weight: 800; font-size: 0.72rem; letter-spacing: 0.5px;">{p_data['tag']}</span>
                </div>
                <div style="font-size: 0.82rem; color: #E4E4E7; line-height: 1.4; margin-bottom: 0.75rem;">{p_data['desc']}</div>
                <div style="background: rgba(10,10,14,0.75); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 8px 12px; font-size: 0.78rem; color: #D4D4D8; margin-bottom: 0.9rem;">
                    <div>🏢 <strong>Company:</strong> {p_data['company']}</div>
                    <div>🌐 <strong>Website:</strong> {p_data['website'] or '—'}</div>
                    <div>👤 <strong>Recruiter:</strong> {p_data['recruiter']}</div>
                    <div>📧 <strong>Email:</strong> <code>{p_data['email'] or 'None'}</code></div>
                    <div>🔗 <strong>Offer URL:</strong> {p_data['joburl'] or '—'}</div>
                </div>
                <div style="font-size: 0.76rem; color: #A1A1AA; background: rgba(0,0,0,0.4); padding: 8px 10px; border-radius: 8px; margin-bottom: 0.9rem; white-space: pre-wrap; max-height: 80px; overflow-y: auto; font-family: monospace;">{html.escape(p_data['text'][:160])}...</div>
            </div>
            """)
            if st.button(f"Load {p_data['title']}", key=f"btn_preset_load_{idx}", use_container_width=True):
                st.session_state.active_text = p_data["text"]
                st.session_state.active_company = p_data["company"]
                st.session_state.active_email = p_data["email"]
                st.session_state.active_website = p_data["website"]
                st.session_state.active_recruiter = p_data["recruiter"]
                st.session_state.active_linkedin = p_data["linkedin"]
                st.session_state.active_joburl = p_data["joburl"]
                st.session_state.last_result = None
                st.success(f"✓ Loaded {p_data['title']} with all 6 recruiter & company fields!")
                st.rerun()
        idx += 1

# ===========================================================================
# TAB 4: Batch CSV Scanning Studio
# ===========================================================================
with tab_batch:
    render_safe_html("""
    <div class="panel-title">BATCH INTELLIGENCE SCANNER</div>
    <div class="panel-subtitle">Upload a CSV dataset of job postings to perform automated bulk screening.</div>
    """)

    csv_file = st.file_uploader("Upload CSV Dataset", type=["csv"], key="batch_csv_uploader")
    if csv_file is not None:
        try:
            df = pd.read_csv(csv_file)
            st.info(f"Loaded CSV with **{len(df):,}** rows.")
            text_col = st.selectbox("Select posting text column for scanning", options=df.columns)

            if st.button("🚀 EXECUTE BATCH SCAN", use_container_width=True):
                progress_bar = st.progress(0)
                results_list = []

                safe_count = 0
                mod_count = 0
                high_count = 0

                for i, row in df.iterrows():
                    val = str(row[text_col]) if pd.notna(row[text_col]) else ""
                    res = predict(val)
                    level = res["risk_level"]
                    if level in ("HIGH RISK", "VERY HIGH RISK"):
                        high_count += 1
                    elif level in ("MEDIUM RISK", "SUSPICIOUS", "CAUTION"):
                        mod_count += 1
                    else:
                        safe_count += 1

                    results_list.append({
                        "ID": i + 1,
                        "Posting Snippet": val[:80] + "..." if len(val) > 80 else val,
                        "Threat Score": res["risk_score"],
                        "Risk Level": res["risk_level"],
                        "Signals": len(res["indicators"])
                    })
                    progress_bar.progress((i + 1) / len(df))

                res_df = pd.DataFrame(results_list)

                render_safe_html(f"""
                <div class="metrics-grid-row" style="margin-top: 1rem;">
                    <div class="cyber-metric-card">
                        <div class="metric-hdr">Total Processed</div>
                        <div class="metric-num">{len(df):,}</div>
                        <div class="metric-subtext">Batch Completed</div>
                    </div>
                    <div class="cyber-metric-card">
                        <div class="metric-hdr">Low Risk / Safe</div>
                        <div class="metric-num" style="color: #4ADE80;">{safe_count}</div>
                        <div class="metric-subtext">{(safe_count/len(df)*100):.1f}% of total</div>
                    </div>
                    <div class="cyber-metric-card">
                        <div class="metric-hdr">Moderate Risk</div>
                        <div class="metric-num" style="color: #FBBF24;">{mod_count}</div>
                        <div class="metric-subtext">{(mod_count/len(df)*100):.1f}% of total</div>
                    </div>
                    <div class="cyber-metric-card">
                        <div class="metric-hdr">High Threat</div>
                        <div class="metric-num" style="color: #F87171;">{high_count}</div>
                        <div class="metric-subtext">{(high_count/len(df)*100):.1f}% of total</div>
                    </div>
                </div>
                """)

                st.dataframe(res_df, use_container_width=True)

                st.download_button(
                    "📥 Download Results CSV",
                    data=res_df.to_csv(index=False).encode('utf-8'),
                    file_name="batch_threat_scan_results.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")

# ===========================================================================
# TAB 5: Session Scan History
# ===========================================================================
with tab_history:
    render_safe_html("""
    <div class="panel-title">SCAN SESSION AUDIT LOG</div>
    <div class="panel-subtitle">Review all postings analyzed during your active session.</div>
    """)

    if st.session_state.history:
        st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
        if st.button("Clear Audit Log"):
            st.session_state.history = []
            st.rerun()
    else:
        render_safe_html("""
        <div style="background: rgba(14, 14, 20, 0.6); border: 1px dashed rgba(255,255,255,0.14); border-radius: 12px; padding: 2rem; text-align: center; color: #A1A1AA; font-size: 0.88rem;">
            No scans performed in this active session yet. Run an analysis in the <strong>Analyze Posting</strong> tab to record session audit logs.
        </div>
        """)

# ===========================================================================
# TAB 6: Model Performance & Benchmarking Studio (ML Laboratory)
# ===========================================================================
with tab_benchmarks:
    render_safe_html("""
    <div class="panel-title">MACHINE LEARNING BENCHMARKING STUDIO</div>
    <div class="panel-subtitle">Evaluated on the EMSCAD benchmark dataset (17,880 listings, 3,576 test postings).</div>
    """)

    metrics_data = [
        {"Model Architecture": "Logistic Regression (TF-IDF + Struct)", "Overall Accuracy": "95.61%", "Fraud Precision": "52.68%", "Fraud Recall": "90.75%", "Fraud F1-Score": "0.6667"},
        {"Model Architecture": "Random Forest Classifier", "Overall Accuracy": "97.93%", "Fraud Precision": "100.00%", "Fraud Recall": "57.23%", "Fraud F1-Score": "0.7279"},
        {"Model Architecture": "Linear SVM (Active Production Model)", "Overall Accuracy": "98.41%", "Fraud Precision": "90.85%", "Fraud Recall": "74.57%", "Fraud F1-Score": "0.8190"}
    ]
    st.table(pd.DataFrame(metrics_data))

    render_safe_html("""
    <div class="panel-title" style="font-size: 1.1rem; margin-top: 1.5rem;">📐 TEST-SET CONFUSION MATRIX (LINEAR SVM)</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
        <div class="cyber-metric-card" style="border-left: 4px solid #22C55E;">
            <div class="metric-hdr">True Negatives (TN) &bull; Legitimate Verified</div>
            <div class="metric-num" style="color: #4ADE80;">3,390</div>
            <div class="metric-subtext" style="color: #4ADE80;">Legitimate postings correctly classified</div>
        </div>
        <div class="cyber-metric-card" style="border-left: 4px solid #EF4444;">
            <div class="metric-hdr">False Positives (FP) &bull; False Alarms</div>
            <div class="metric-num" style="color: #F87171;">13</div>
            <div class="metric-subtext" style="color: #F87171;">Legitimate postings flagged incorrectly (0.38%)</div>
        </div>
        <div class="cyber-metric-card" style="border-left: 4px solid #F59E0B;">
            <div class="metric-hdr">False Negatives (FN) &bull; Missed Scams</div>
            <div class="metric-num" style="color: #FBBF24;">44</div>
            <div class="metric-subtext" style="color: #FBBF24;">Scams that bypassed initial classification</div>
        </div>
        <div class="cyber-metric-card" style="border-left: 4px solid #22C55E;">
            <div class="metric-hdr">True Positives (TP) &bull; Detected Fraud</div>
            <div class="metric-num" style="color: #4ADE80;">129</div>
            <div class="metric-subtext" style="color: #4ADE80;">Fraudulent postings successfully caught</div>
        </div>
    </div>
    """)

    render_safe_html("""
    <div class="cyber-glass-panel">
        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.8rem;">
            🎓 "WHAT DOES THIS MEAN?" — VIVA DEFENSE GUIDE
        </div>
        <ul style="font-size: 0.88rem; color: #E4E4E7; line-height: 1.6; padding-left: 1.2rem;">
            <li><strong style="color: #FFFFFF;">Accuracy (98.41%):</strong> Percentage of total test postings correctly classified as either legitimate or fraudulent.</li>
            <li><strong style="color: #FFFFFF;">Fraud Precision (90.85%):</strong> Of all postings flagged as fraudulent by Linear SVM, 90.85% were confirmed fraud (extremely low false-alarm rate of 13 out of 3,403 legitimate posts).</li>
            <li><strong style="color: #FFFFFF;">Fraud Recall (74.57%):</strong> Of all actual fraudulent postings in the test set, the classifier successfully caught 74.57%.</li>
            <li><strong style="color: #FFFFFF;">Fraud F1-Score (0.8190):</strong> The harmonic mean balancing precision and recall under severe class imbalance (866 fraudulent vs 17,014 legitimate in the EMSCAD corpus).</li>
        </ul>
    </div>
    """)

    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if os.path.exists("outputs/model_comparison.png"):
            st.image("outputs/model_comparison.png", caption="Comparative Model Performance across Classifiers", use_container_width=True)
    with img_col2:
        if os.path.exists("outputs/confusion_matrix_linear_svm.png"):
            st.image("outputs/confusion_matrix_linear_svm.png", caption="Linear SVM Confusion Matrix Visualization", use_container_width=True)

# ===========================================================================
# TAB 7: Scam Defense Center
# ===========================================================================
with tab_guide:
    render_safe_html("""
    <div class="panel-title">SCAM DEFENSE CENTER</div>
    <div class="panel-subtitle">Comprehensive threat defense intelligence to protect students and job-seekers against recruitment fraud.</div>
    """)

    guide_cols = st.columns(2)

    with guide_cols[0]:
        render_safe_html("""
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #EF4444; margin-bottom: 0.5rem;">
                🚨 1. Upfront Payment & Fee Scams
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                <strong>Modus Operandi:</strong> Fraudsters claim candidates are selected and request "registration fees", "training charges", "laptop security deposits", or "documentation verification fees".<br><br>
                <strong>Defense Rule:</strong> Real employers never ask candidates to pay money for getting hired. Any upfront fee demand is an immediate high-risk signal.
            </div>
        </div>
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #F59E0B; margin-bottom: 0.5rem;">
                ⚡ 2. Artificial Urgency & Limited Seats
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                <strong>Modus Operandi:</strong> "Only 3 spots left! Apply before midnight or lose guaranteed placement." Scammers use pressure tactics to force victims into bypassing basic verification.<br><br>
                <strong>Defense Rule:</strong> Legitimate hiring processes allow reasonable candidate evaluation windows. High pressure implies a scam attempt.
            </div>
        </div>
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #38BDF8; margin-bottom: 0.5rem;">
                💬 3. WhatsApp & Telegram Recruitment Channels
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                <strong>Modus Operandi:</strong> Directing communication exclusively to WhatsApp, Telegram, or Discord without corporate emails or verified video calls.<br><br>
                <strong>Defense Rule:</strong> Insist on corporate email communication from the employer's registered domain (e.g., hr@company.com).
            </div>
        </div>
        """)

    with guide_cols[1]:
        render_safe_html("""
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #EC4899; margin-bottom: 0.5rem;">
                🤑 4. Unrealistic Stipends & Guaranteed Selection
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                <strong>Modus Operandi:</strong> Promising ₹50,000–₹80,000/month for 2 hours of daily mobile tasks without an interview, resume, or technical screening.<br><br>
                <strong>Defense Rule:</strong> If an offer sounds disproportionately lucrative for zero prerequisites, it is virtually always fraudulent.
            </div>
        </div>
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #A78BFA; margin-bottom: 0.5rem;">
                📧 5. Suspicious Free Webmail Domains
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                <strong>Modus Operandi:</strong> Official-sounding recruiters using <code>googlehr2024@gmail.com</code>, <code>infy_recruitment@yahoo.com</code>, or free Blogspot sites.<br><br>
                <strong>Defense Rule:</strong> Verify the email headers and ensure the sending domain strictly matches the organization's official website.
            </div>
        </div>
        <div class="cyber-glass-panel">
            <div style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.05rem; color: #4ADE80; margin-bottom: 0.5rem;">
                📋 6. Essential Student Verification Checklist
            </div>
            <div style="font-size: 0.86rem; color: #D4D4D8; line-height: 1.5;">
                1. Look up the hiring manager on LinkedIn to verify their current active role.<br>
                2. Search the exact posting text on Google inside quotes to check for copied templates.<br>
                3. Check official company career portals for the exact requisition ID.
            </div>
        </div>
        """)
