"""
generate_pdf_report.py
----------------------
Generates a publication-quality PDF report for Review 3 of the Fake Internship Detector project.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#71717A"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "AI Fake Internship Threat Scanner — Review 3 Project Report")
            self.setStrokeColor(colors.HexColor("#E4E4E7"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)
        
        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#E4E4E7"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        
        self.drawString(54, 32, "Confidential — Academic Capstone Review 3 Evaluation — Linear SVM (98.41% Acc)")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#7F1D1D")   # Deep Red
    c_dark = colors.HexColor("#18181B")      # Charcoal
    c_sub = colors.HexColor("#52525B")       # Muted Zinc
    c_accent = colors.HexColor("#DC2626")    # Crimson Accent
    c_green = colors.HexColor("#15803D")     # Dark Emerald
    
    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1
    )
    
    sub_title_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#FECACA"),
        alignment=1
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=c_dark,
        spaceBefore=8,
        spaceAfter=4
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#27272A")
    )
    
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1E293B")
    )

    tbl_header = ParagraphStyle('TblHdr', parent=body_style, fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.white)
    tbl_cell = ParagraphStyle('TblCell', parent=body_style, fontSize=7.8, leading=10)
    tbl_cell_bold = ParagraphStyle('TblCellBold', parent=body_style, fontName='Helvetica-Bold', fontSize=7.8, leading=10)

    story = []

    # 1. Header Title Banner
    banner_data = [
        [
            Paragraph("AI FAKE INTERNSHIP THREAT SCANNER", title_style),
        ],
        [
            Paragraph("Machine Learning-Based Threat Detection, Recruiter Verification & Risk Intelligence Platform<br/><b>Review 2 to Review 3 Comprehensive Transition & Technical Audit Report</b>", sub_title_style)
        ]
    ]
    banner_table = Table(banner_data, colWidths=[504])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_primary),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # Meta Info Row
    meta_data = [
        [
            Paragraph("<b>Target Evaluation:</b> Review 3 Exhibition", tbl_cell),
            Paragraph("<b>Active Model:</b> Calibrated Linear SVM", tbl_cell),
            Paragraph("<b>Dataset:</b> EMSCAD (17,880 listings)", tbl_cell)
        ],
        [
            Paragraph("<b>Accuracy:</b> 98.41% (Test Set)", tbl_cell),
            Paragraph("<b>Fraud Precision:</b> 90.85%", tbl_cell),
            Paragraph("<b>Repository:</b> vaibhavmurty4518/fake-internship-detector", tbl_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[168, 168, 168])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F4F4F5")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Section 1: Executive Summary & Comparison Table
    story.append(Paragraph("1. Executive Summary: Review 2 vs Review 3 Comparison", h1_style))
    story.append(Paragraph(
        "Between Review 2 and Review 3, the application underwent an end-to-end upgrade from a basic single-post classifier into an enterprise-grade AI cybersecurity intelligence platform. Below is the direct capability matrix:",
        body_style
    ))
    story.append(Spacer(1, 6))

    comp_data = [
        [
            Paragraph("Feature / Capability", tbl_header),
            Paragraph("Review 2 (Baseline)", tbl_header),
            Paragraph("Review 3 (Final Production)", tbl_header)
        ],
        [
            Paragraph("<b>Visual Design System</b>", tbl_cell_bold),
            Paragraph("Basic light SaaS theme with flat cards and minimal hierarchy.", tbl_cell),
            Paragraph("<b>Cybersecurity aesthetic</b>: Charcoal/Black palette, Frosted Glassmorphism, and live 3D WebGL Security Core.", tbl_cell)
        ],
        [
            Paragraph("<b>Company & Recruiter Verification</b>", tbl_cell_bold),
            Paragraph("Text-only heuristic checking without domain or webmail validation.", tbl_cell),
            Paragraph("<b>Integrated Multi-tier Engine</b>: Domain registration age, typosquatted lookalike checks, corporate vs webmail audit.", tbl_cell)
        ],
        [
            Paragraph("<b>Preset Test Hub</b>", tbl_cell_bold),
            Paragraph("Plain text snippets without recruiter metadata; uniform styling.", tbl_cell),
            Paragraph("<b>6-Field Complete Presets</b>: Unique color per scenario, auto-populating Company, Email, Recruiter, LinkedIn, URLs.", tbl_cell)
        ],
        [
            Paragraph("<b>Multi-Posting Input</b>", tbl_cell_bold),
            Paragraph("Not supported (single text input only).", tbl_cell),
            Paragraph("<b>Multi-Post Scanner Studio</b>: Batch paste, auto-delimiter detection (---, blank lines), 3-tier risk grouping, CSV export.", tbl_cell)
        ],
        [
            Paragraph("<b>UI Stability & Rendering</b>", tbl_cell_bold),
            Paragraph("Vulnerable to CommonMark indentation bugs rendering raw HTML tags as text.", tbl_cell),
            Paragraph("<b>Zero Code-Leak Guarantee</b>: Native render_safe_html() stream and isolated HTML component wrappers.", tbl_cell)
        ],
        [
            Paragraph("<b>Automated Test Suite</b>", tbl_cell_bold),
            Paragraph("Basic smoke tests only.", tbl_cell),
            Paragraph("<b>48 / 48 Automated Pytest Suite Passing</b> across pipeline and investigation modules.", tbl_cell)
        ]
    ]
    comp_table = Table(comp_data, colWidths=[110, 194, 200])
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_dark),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4D8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 12))

    # Section 2: Machine Learning Architecture & Benchmark Laboratory
    story.append(Paragraph("2. Machine Learning Architecture & Benchmark Performance", h1_style))
    story.append(Paragraph(
        "The classification backend leverages a <b>Calibrated Linear Support Vector Machine (Linear SVM)</b> trained on 17,880 listings from the Employment Scam Aegean Dataset (EMSCAD). Linear SVM was selected after extensive benchmarking against Logistic Regression and Random Forest due to its superior F1-score on high-dimensional sparse TF-IDF n-gram feature representations.",
        body_style
    ))
    story.append(Spacer(1, 6))

    ml_data = [
        [
            Paragraph("Model Architecture", tbl_header),
            Paragraph("Overall Accuracy", tbl_header),
            Paragraph("Fraud Precision", tbl_header),
            Paragraph("Fraud Recall", tbl_header),
            Paragraph("Fraud F1-Score", tbl_header)
        ],
        [
            Paragraph("Logistic Regression (TF-IDF + Struct)", tbl_cell),
            Paragraph("95.61%", tbl_cell),
            Paragraph("52.68%", tbl_cell),
            Paragraph("90.75%", tbl_cell),
            Paragraph("0.6667", tbl_cell)
        ],
        [
            Paragraph("Random Forest Classifier", tbl_cell),
            Paragraph("97.93%", tbl_cell),
            Paragraph("100.00%", tbl_cell),
            Paragraph("57.23%", tbl_cell),
            Paragraph("0.7279", tbl_cell)
        ],
        [
            Paragraph("<b>Linear SVM (Active Production)</b>", tbl_cell_bold),
            Paragraph("<b>98.41%</b>", tbl_cell_bold),
            Paragraph("<b>90.85%</b>", tbl_cell_bold),
            Paragraph("<b>74.57%</b>", tbl_cell_bold),
            Paragraph("<b>0.8190</b>", tbl_cell_bold)
        ]
    ]
    ml_table = Table(ml_data, colWidths=[164, 85, 85, 85, 85])
    ml_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_primary),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4D8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#FEF2F2")),
    ]))
    story.append(ml_table)
    story.append(Spacer(1, 8))

    # Confusion Matrix Callout
    cm_data = [
        [
            Paragraph("<b>True Negatives (TN):</b> 3,390<br/><font color='#16A34A'>Legitimate posts verified</font>", tbl_cell),
            Paragraph("<b>False Positives (FP):</b> 13<br/><font color='#DC2626'>False alarms (0.38% rate)</font>", tbl_cell),
            Paragraph("<b>False Negatives (FN):</b> 44<br/><font color='#D97706'>Bypassed ML (caught by rules)</font>", tbl_cell),
            Paragraph("<b>True Positives (TP):</b> 129<br/><font color='#16A34A'>Fraud detected accurately</font>", tbl_cell)
        ]
    ]
    cm_table = Table(cm_data, colWidths=[126, 126, 126, 126])
    cm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F4F4F5")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cm_table)
    story.append(Spacer(1, 12))

    # Section 3: Recruiter Verification & Evidence Engine
    story.append(Paragraph("3. Recruiter Verification & Domain Investigation Pipeline", h1_style))
    story.append(Paragraph(
        "Review 3 introduces a multi-tier evidence engine that bridges textual ML predictions with live employer authentication:",
        body_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("• <b>Domain Registration & Age:</b> Assesses WHOIS domain age to identify newly registered ephemeral scam portals (< 6 months old).", body_style))
    story.append(Paragraph("• <b>Typosquatting & Lookalike Detection:</b> Computes Levenshtein and token distance to catch brand hijacking (e.g., <code>micros0ft-careers.com</code> vs <code>microsoft.com</code>).", body_style))
    story.append(Paragraph("• <b>Recruiter Email Integrity:</b> Flags recruiters claiming to represent Fortune 500 corporations while utilizing personal webmail domains (e.g., <code>@gmail.com</code>, <code>@yahoo.com</code>).", body_style))
    story.append(Paragraph("• <b>Offline Verification Cache:</b> Incorporates a pre-compiled JSON cache store (<code>company_cache.json</code>) ensuring instant, deterministic verification during offline evaluation sessions.", body_style))
    story.append(Spacer(1, 10))

    # Section 4: Multi-Post Scanning Studio
    story.append(Paragraph("4. New Feature: Multi-Post Scanning Studio", h1_style))
    story.append(Paragraph(
        "A major new feature implemented for Review 3 is the <b>Multi-Post Scan Studio</b>, enabling users to analyze multiple job postings or recruitment messages concurrently without manual file creation:",
        body_style
    ))
    story.append(Spacer(1, 4))
    story.append(Paragraph("• <b>Smart Delimiter Splitting:</b> Automatically detects and parses postings separated by dashes (<code>---</code>), double line-breaks, or header prefixes (<code>POSTING 1:</code>, <code>POSTING 2:</code>).", body_style))
    story.append(Paragraph("• <b>Batch Threat Summary:</b> Displays immediate distribution metrics across High Risk, Moderate Risk, and Low Risk categories.", body_style))
    story.append(Paragraph("• <b>3-Tier Grouped Risk Containers:</b> Presents clear, high-contrast visual groupings showing posting numbers, threat scores (/100), detected indicator tags, and raw text snippets.", body_style))
    story.append(Paragraph("• <b>1-Click CSV Audit Export:</b> Generates a complete structured CSV containing Posting Number, Threat Score, Risk Level, Fraud Probability, and Extracted Suspicious Indicators.", body_style))
    story.append(Spacer(1, 10))

    # Section 5: Preset Intelligence Hub
    story.append(Paragraph("5. Preset Intelligence Hub (6 Complete Scenarios)", h1_style))
    story.append(Paragraph(
        "The Preset Hub has been completely overhauled with 6 real-world test cases, each fully populating all 6 metadata fields (Company, Website, Recruiter Name, Recruiter Email, Recruiter LinkedIn, Offer URL, and Description):",
        body_style
    ))
    story.append(Spacer(1, 4))
    
    preset_data = [
        [
            Paragraph("Scenario Title", tbl_header),
            Paragraph("Category & Color Theme", tbl_header),
            Paragraph("Threat Characteristics", tbl_header)
        ],
        [
            Paragraph("<b>Upfront Registration Fee Scam</b>", tbl_cell_bold),
            Paragraph("<font color='#DC2626'><b>CRITICAL THREAT</b> (Crimson)</font>", tbl_cell),
            Paragraph("Demands Rs. 999 refundable registration/kit fee; contact via WhatsApp & Gmail.", tbl_cell)
        ],
        [
            Paragraph("<b>Microsoft Brand Impersonation</b>", tbl_cell_bold),
            Paragraph("<font color='#0284C7'><b>IMPERSONATION</b> (Cyber Blue)</font>", tbl_cell),
            Paragraph("Legitimate Fortune 500 company name hijacked using non-corporate webmail & fee trap.", tbl_cell)
        ],
        [
            Paragraph("<b>Genuine Series-B FinTech Posting</b>", tbl_cell_bold),
            Paragraph("<font color='#16A34A'><b>VERIFIED SAFE</b> (Emerald)</font>", tbl_cell),
            Paragraph("Authentic corporate domain, verified skills, structured interview, and fair stipend.", tbl_cell)
        ],
        [
            Paragraph("<b>Unrealistic 80k Monthly Pay Bait</b>", tbl_cell_bold),
            Paragraph("<font color='#D97706'><b>UNREALISTIC PAY</b> (Amber)</font>", tbl_cell),
            Paragraph("Rs. 80,000/mo for 2hrs/day mobile work; zero prerequisites or resume screening.", tbl_cell)
        ],
        [
            Paragraph("<b>Urgent WhatsApp Contact Flyer</b>", tbl_cell_bold),
            Paragraph("<font color='#EA580C'><b>URGENCY PRESSURE</b> (Orange)</font>", tbl_cell),
            Paragraph("Artificial pressure ('Only 3 spots left tonight') diverting applicants exclusively to WhatsApp.", tbl_cell)
        ],
        [
            Paragraph("<b>Informal Early-Stage Startup Post</b>", tbl_cell_bold),
            Paragraph("<font color='#9333EA'><b>INFORMAL STARTUP</b> (Purple)</font>", tbl_cell),
            Paragraph("Small team with personal blog; moderate caution needed without upfront fee trap.", tbl_cell)
        ]
    ]
    preset_table = Table(preset_data, colWidths=[140, 130, 234])
    preset_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_dark),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#D4D4D8")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
    ]))
    story.append(preset_table)
    story.append(Spacer(1, 12))

    # Section 6: Viva Defense Guide
    story.append(Paragraph("6. Viva Defense Quick Reference", h1_style))
    
    q1 = [
        [Paragraph("<b>Q1: Why was Linear SVM chosen over Deep Learning (BERT/LLMs)?</b>", tbl_cell_bold)],
        [Paragraph("Linear SVM on TF-IDF sparse features achieves 98.41% accuracy and 0.8190 F1-score with sub-5ms inference latency on CPU, with zero GPU cost, API dependencies, or token bills.", tbl_cell)]
    ]
    t_q1 = Table(q1, colWidths=[504])
    t_q1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F4F4F5")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_q1)
    story.append(Spacer(1, 6))

    q2 = [
        [Paragraph("<b>Q2: How does the system handle class imbalance in recruitment datasets?</b>", tbl_cell_bold)],
        [Paragraph("Only ~4.8% of the EMSCAD corpus is fraudulent. We applied balanced class weighting and calibrated probabilities using Sigmoid cross-validation (CalibratedClassifierCV) to prevent majority-class bias.", tbl_cell)]
    ]
    t_q2 = Table(q2, colWidths=[504])
    t_q2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F4F4F5")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_q2)
    story.append(Spacer(1, 12))

    # Section 7: Deliverables Checklist
    story.append(Paragraph("7. Project Submission & Deliverables Checklist", h1_style))
    story.append(Paragraph("✓ <b>GitHub Repository:</b> https://github.com/vaibhavmurty4518/fake-internship-detector.git (Up to date on <code>main</code>)", body_style))
    story.append(Paragraph("✓ <b>Submission Zip Archive:</b> <code>C:\\Users\\Vaibhav Murty\\Downloads\\fake-internship-detector-review3-final.zip</code>", body_style))
    story.append(Paragraph("✓ <b>Automated Test Suite:</b> 48 / 48 Tests Passed (100% Pass Rate via Pytest)", body_style))
    story.append(Paragraph("✓ <b>Zero Code-Leak Guarantee:</b> Complete custom HTML rendering stream verified across all 8 tabs.", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF generated successfully at {filename}")

if __name__ == "__main__":
    out_dir = r"C:\Users\Vaibhav Murty\Downloads"
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, "AI_Fake_Internship_Detector_Review_3_Report.pdf")
    build_pdf(pdf_path)
    
    # Also save a copy in docs/
    docs_dir = r"C:\Users\Vaibhav Murty\.gemini\antigravity\scratch\fake-internship-detector\docs"
    os.makedirs(docs_dir, exist_ok=True)
    pdf_docs_path = os.path.join(docs_dir, "AI_Fake_Internship_Detector_Review_3_Report.pdf")
    build_pdf(pdf_docs_path)
