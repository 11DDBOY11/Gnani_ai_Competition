import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = "submission/corrected_slides"
PREVIEW_DIR = "submission/previews"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PREVIEW_DIR, exist_ok=True)

# Common SVG Icons to avoid any missing font glyphs or boxes
SVG_MIC = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>"""
SVG_PLAY = """<svg width="26" height="26" viewBox="0 0 24 24" fill="#123026" stroke="#123026" stroke-width="1"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>"""
SVG_GLOBE = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e6b422" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>"""
SVG_CODE = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e6b422" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>"""
SVG_CHIP = """<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#e6b422" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>"""
SVG_CHECK = """<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2e7d32" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>"""

BASE_CSS = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}
body {
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    background-color: #f4f7f5;
    font-family: 'Nirmala UI', 'Segoe UI', system-ui, sans-serif;
    color: #14231c;
    display: flex;
    flex-direction: column;
}
.header-bar {
    height: 110px;
    background-color: #123026;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 70px;
}
.badge-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.challenge-badge {
    font-size: 22px;
    font-weight: 700;
    color: #d8f3dc;
    letter-spacing: 0.5px;
}
.project-tag {
    font-size: 18px;
    color: #b4d2c3;
}
.logo-block {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 2px;
}
.logo-kannada {
    font-size: 34px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.1;
}
.logo-english {
    font-size: 18px;
    font-weight: 600;
    color: #d8f3dc;
    letter-spacing: 1px;
}
.title-section {
    padding: 22px 70px 14px 70px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}
.title-line-1 {
    font-size: 40px;
    font-weight: 700;
    color: #14231c;
    line-height: 1.15;
}
.title-line-2 {
    font-size: 24px;
    font-weight: 600;
    color: #2e7d32;
    line-height: 1.2;
}
.divider-line {
    margin: 8px 70px 0 70px;
    height: 2px;
    background-color: #d2e1d7;
}
.content-container {
    flex: 1;
    padding: 22px 70px 36px 70px;
    display: flex;
    flex-direction: column;
    gap: 20px;
}
"""

def slide_1_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.hero-box {{
    background-color: #123026;
    border-radius: 18px;
    padding: 30px 48px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}}
.hero-quote-en {{
    font-size: 42px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.25;
}}
.hero-quote-en span {{
    color: #e6b422;
}}
.hero-quote-kn {{
    font-size: 26px;
    font-weight: 500;
    color: #d8f3dc;
    line-height: 1.3;
}}
.cards-row {{
    display: flex;
    gap: 28px;
    flex: 1;
}}
.pillar-card {{
    flex: 1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 16px;
    padding: 34px 30px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.pill-num {{
    width: 56px;
    height: 46px;
    background-color: #d8f3dc;
    color: #2e7d32;
    font-size: 22px;
    font-weight: 700;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}}
.pillar-title {{
    font-size: 26px;
    font-weight: 700;
    color: #14231c;
    margin-top: 2px;
}}
.pillar-desc {{
    font-size: 21px;
    line-height: 1.5;
    color: #55695f;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">The Problem & Opportunity</div>
        <div class="title-line-2">(ಸಮಸ್ಯೆ ಮತ್ತು ಅವಕಾಶ)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="hero-box">
            <div class="hero-quote-en">“Farming questions should not require <span>complicated technology.”</span></div>
            <div class="hero-quote-kn">ಕೃಷಿ ಸಮಸ್ಯೆಗಳಿಗೆ ಪರಿಹಾರ ಪಡೆಯಲು ತಾಂತ್ರಿಕ ತಡೆಗೋಡೆಗಳಿರಬಾರದು.</div>
        </div>

        <div class="cards-row">
            <div class="pillar-card">
                <div class="pill-num">01</div>
                <div class="pillar-title">The Farmer's Reality</div>
                <div class="pillar-desc">Smallholder farmers in Karnataka often face sudden crop pest attacks and disease symptoms, requiring immediate guidance in Kannada.</div>
            </div>
            <div class="pillar-card">
                <div class="pill-num">02</div>
                <div class="pillar-title">The Digital Barrier</div>
                <div class="pillar-desc">Existing digital tools frequently require typing in English, navigating complex forms, and reading technical agricultural portals.</div>
            </div>
            <div class="pillar-card">
                <div class="pill-num">03</div>
                <div class="pillar-title">Voice-First Simplicity</div>
                <div class="pillar-desc">Krishi Mitra enables a farmer to simply tap a microphone, speak naturally in Kannada, and receive clear spoken guidance.</div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_2_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.pipeline-row {{
    display: flex;
    gap: 20px;
    margin-bottom: 6px;
}}
.pipe-step {{
    flex: 1;
    background-color: #123026;
    border-radius: 14px;
    padding: 20px 22px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}}
.pipe-num {{
    font-size: 19px;
    font-weight: 700;
    color: #e6b422;
    letter-spacing: 0.5px;
}}
.pipe-desc {{
    font-size: 17px;
    line-height: 1.4;
    color: #d8f3dc;
}}
.dual-showcase {{
    display: flex;
    gap: 28px;
    flex: 1;
}}
.showcase-card {{
    flex: 1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 16px;
    padding: 28px 32px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.pill-tag {{
    align-self: flex-start;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
.pill-green {{
    background-color: #d8f3dc;
    color: #2e7d32;
}}
.pill-gold {{
    background-color: #fef3c7;
    color: #b45309;
}}
.showcase-title {{
    font-size: 26px;
    font-weight: 700;
    color: #14231c;
}}
.bullet-list {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 4px;
}}
.bullet-item {{
    font-size: 19px;
    line-height: 1.45;
    color: #55695f;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}}
.bullet-item strong {{
    color: #14231c;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">Krishi Mitra Architecture & Workflow</div>
        <div class="title-line-2">(ವ್ಯವಸ್ಥೆಯ ವಿನ್ಯಾಸ)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="pipeline-row">
            <div class="pipe-step">
                <div class="pipe-num">1. SPEAK</div>
                <div class="pipe-desc">Farmer speaks in Kannada via browser mic (8 kHz phone quality PCM)</div>
            </div>
            <div class="pipe-step">
                <div class="pipe-num">2. TRANSCRIBE</div>
                <div class="pipe-desc">Gnani AI Vachana STT converts speech to text in real time</div>
            </div>
            <div class="pipe-step">
                <div class="pipe-num">3. REASON</div>
                <div class="pipe-desc">Guided Engine / Groq LLM provides non-diagnostic agronomic guidance</div>
            </div>
            <div class="pipe-step">
                <div class="pipe-num">4. LISTEN</div>
                <div class="pipe-desc">Gnani AI Timbre-v3.0 synthesizes clear spoken Kannada audio</div>
            </div>
        </div>

        <div class="dual-showcase">
            <div class="showcase-card">
                <div class="pill-tag pill-green">FARMER-FACING ASK WEB APP (/ask)</div>
                <div class="showcase-title">Open-Ended Agricultural Query Interface</div>
                <div class="bullet-list">
                    <div class="bullet-item">• Mobile-friendly interface designed for touchscreens</div>
                    <div class="bullet-item">• Kannada & English instant language switcher</div>
                    <div class="bullet-item">• Browser microphone streaming phone-quality audio</div>
                    <div class="bullet-item">• One-click sample questions for common crop problems</div>
                    <div class="bullet-item">• Integrated audio player with Listen and Stop controls</div>
                </div>
            </div>

            <div class="showcase-card">
                <div class="pill-tag pill-gold">GUIDED SIMULATOR & CORE PIPELINE (/sim)</div>
                <div class="showcase-title">Curated Knowledge Base Helpline Prototype</div>
                <div class="bullet-list">
                    <div class="bullet-item">• 3 Supported Crops: Paddy (ಭತ್ತ), Arecanut (ಅಡಿಕೆ), Coconut (ತೆಂಗು)</div>
                    <div class="bullet-item">• Whole-response audio delivery and playback acknowledgements</div>
                    <div class="bullet-item">• Safety-focused advisory with unreviewed chemical filtering</div>
                    <div class="bullet-item">• Dialogue engine retaining crop across conversational turns</div>
                    <div class="bullet-item">• Explicit referral flow for unsupported crops to Kisan Call Centre</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_3_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.content-grid {{
    display: flex;
    gap: 28px;
    flex: 1;
}}
.mockup-card {{
    flex: 1.1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 18px;
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.mockup-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.mockup-pill {{
    padding: 5px 12px;
    background-color: #e8f5e9;
    color: #2e7d32;
    font-size: 15px;
    font-weight: 700;
    border-radius: 6px;
}}
.lang-toggle {{
    display: flex;
    background-color: #ebf0ee;
    border-radius: 20px;
    padding: 3px;
}}
.lang-btn {{
    padding: 5px 14px;
    border-radius: 17px;
    font-size: 15px;
    font-weight: 700;
}}
.lang-btn.active {{
    background-color: #2e7d32;
    color: #ffffff;
}}
.lang-btn.inactive {{
    color: #55695f;
}}
.input-area-box {{
    background-color: #fafcfb;
    border: 2px solid #2e7d32;
    border-radius: 14px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 120px;
}}
.input-label {{
    font-size: 18px;
    font-weight: 600;
    color: #14231c;
}}
.query-kannada {{
    font-size: 24px;
    font-weight: 700;
    color: #14231c;
    line-height: 1.35;
    word-wrap: break-word;
}}
.query-english {{
    font-size: 16px;
    font-style: italic;
    color: #55695f;
    line-height: 1.3;
}}
.audio-action-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
}}
.mic-status-block {{
    display: flex;
    align-items: center;
    gap: 12px;
}}
.mic-circle {{
    width: 48px;
    height: 48px;
    background-color: #dc3545;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #ffffff;
    box-shadow: 0 0 0 4px rgba(220,53,69,0.2);
}}
.mic-text {{
    display: flex;
    flex-direction: column;
    gap: 2px;
}}
.mic-title {{
    font-size: 17px;
    font-weight: 700;
    color: #b42828;
}}
.mic-sub {{
    font-size: 14px;
    color: #55695f;
}}
.submit-btn {{
    background-color: #2e7d32;
    color: #ffffff;
    padding: 12px 24px;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 700;
}}
.samples-box {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 4px;
}}
.samples-title {{
    font-size: 16px;
    font-weight: 700;
    color: #55695f;
}}
.sample-chips {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.sample-chip {{
    background-color: #d8f3dc;
    color: #1b4332;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.3;
}}
.feature-card {{
    flex: 0.9;
    background-color: #123026;
    border-radius: 18px;
    padding: 30px 32px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
}}
.feature-badge {{
    font-size: 17px;
    font-weight: 700;
    color: #e6b422;
    letter-spacing: 0.5px;
}}
.feature-title {{
    font-size: 28px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.2;
}}
.feature-points {{
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-top: 6px;
}}
.point-block {{
    display: flex;
    flex-direction: column;
    gap: 4px;
}}
.point-head {{
    font-size: 19px;
    font-weight: 700;
    color: #d8f3dc;
}}
.point-body {{
    font-size: 16px;
    line-height: 1.4;
    color: #c8ded5;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">Voice & Text Query Interface (/ask)</div>
        <div class="title-line-2">(ಪ್ರಶ್ನೆ ಕೇಳುವ ವಿಧಾನ)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="content-grid">
            <div class="mockup-card">
                <div class="mockup-header">
                    <div class="mockup-pill">INTERFACE WALKTHROUGH · WEB PROTOTYPE</div>
                    <div class="lang-toggle">
                        <div class="lang-btn active">ಕನ್ನಡ (KN)</div>
                        <div class="lang-btn inactive">English (EN)</div>
                    </div>
                </div>

                <div class="input-area-box">
                    <div class="input-label">ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಇಲ್ಲಿ ಹೇಳಿ ಅಥವಾ ಬರೆಯಿರಿ:</div>
                    <div class="query-kannada">ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಬಂದಿದೆ, ಏನು ಮಾಡಬೇಕು?</div>
                    <div class="query-english">“Leaf folder caterpillars have appeared in my paddy crop, what should I do?”</div>
                </div>

                <div class="audio-action-row">
                    <div class="mic-status-block">
                        <div class="mic-circle">{SVG_MIC}</div>
                        <div class="mic-text">
                            <div class="mic-title">ಧ್ವನಿ ರೆಕಾರ್ಡಿಂಗ್ ಚಾಲನೆಯಲ್ಲಿದೆ...</div>
                            <div class="mic-sub">Streaming 8 kHz PCM audio to Gnani AI STT</div>
                        </div>
                    </div>
                    <div class="submit-btn">ಕೇಳಿ (Submit)</div>
                </div>

                <div class="samples-box">
                    <div class="samples-title">ಉದಾಹರಣೆ ಪ್ರಶ್ನೆಗಳು (Sample Questions):</div>
                    <div class="sample-chips">
                        <div class="sample-chip">• ಅಡಿಕೆಯಲ್ಲಿ ಕೊಳೆ ರೋಗದ ಲಕ್ಷಣಗಳು</div>
                        <div class="sample-chip">• ತೆಂಗಿನ ಮರದಲ್ಲಿ ದುಂಬಿ ಬಾಧೆ ನಿಯಂತ್ರಣ</div>
                        <div class="sample-chip">• ಭತ್ತದಲ್ಲಿ ರಸಗೊಬ್ಬರ ನಿರ್ವಹಣೆ</div>
                    </div>
                </div>
            </div>

            <div class="feature-card">
                <div class="feature-badge">GNANI AI SPEECH INTEGRATION</div>
                <div class="feature-title">Voice-First Accessibility</div>

                <div class="feature-points">
                    <div class="point-block">
                        <div class="point-head">1. Phone-Quality Speech Stream</div>
                        <div class="point-body">Captures 8 kHz audio directly through browser APIs, matching standard telecommunication audio quality.</div>
                    </div>
                    <div class="point-block">
                        <div class="point-head">2. Transparent Transcript</div>
                        <div class="point-body">Transcribed Kannada text remains visible so the farmer can inspect or edit before submitting.</div>
                    </div>
                    <div class="point-block">
                        <div class="point-head">3. Zero Typing Needed</div>
                        <div class="point-body">Farmers can ask questions naturally without navigating complex keyboards or English forms.</div>
                    </div>
                    <div class="point-block">
                        <div class="point-head">4. Native Kannada ASR</div>
                        <div class="point-body">Kannada speech input through Gnani AI.</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_4_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.main-playback-card {{
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 18px;
    padding: 24px 32px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    flex: 1;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.audio-banner {{
    background-color: #123026;
    border-radius: 14px;
    padding: 16px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}}
.play-circle {{
    width: 48px;
    height: 48px;
    background-color: #e6b422;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.audio-meta {{
    display: flex;
    flex-direction: column;
    gap: 3px;
}}
.audio-title {{
    font-size: 21px;
    font-weight: 700;
    color: #d8f3dc;
    letter-spacing: 0.5px;
}}
.audio-specs {{
    font-size: 16px;
    color: #b4d2c3;
}}
.speech-box {{
    background-color: #f5fcf7;
    border: 2px solid #2e7d32;
    border-radius: 14px;
    padding: 18px 24px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.speech-label {{
    font-size: 18px;
    font-weight: 700;
    color: #2e7d32;
}}
.speech-text {{
    font-size: 28px;
    font-weight: 700;
    color: #14231c;
    line-height: 1.35;
    word-wrap: break-word;
}}
.trans-box {{
    background-color: #fbfbfc;
    border: 1px solid #d2e1d7;
    border-radius: 14px;
    padding: 16px 24px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.trans-label {{
    font-size: 17px;
    font-weight: 700;
    color: #55695f;
}}
.trans-text {{
    font-size: 23px;
    font-weight: 600;
    color: #14231c;
    line-height: 1.35;
}}
.notes-row {{
    display: flex;
    gap: 20px;
    margin-top: 4px;
}}
.note-col {{
    flex: 1;
    background-color: #e8f5e9;
    border-left: 4px solid #2e7d32;
    border-radius: 8px;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}}
.note-head {{
    font-size: 17px;
    font-weight: 700;
    color: #1b4332;
    display: flex;
    align-items: center;
    gap: 6px;
}}
.note-desc {{
    font-size: 15px;
    line-height: 1.35;
    color: #3b5e4c;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">Spoken Answer & Audio Playback</div>
        <div class="title-line-2">(ಧ್ವನಿ ರೂಪದ ಉತ್ತರ)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="main-playback-card">
            <div class="audio-banner">
                <div class="play-circle">{SVG_PLAY}</div>
                <div class="audio-meta">
                    <div class="audio-title">AUDIO PLAYBACK: GNANI TTS SAMPLE</div>
                    <div class="audio-specs">Voice: Lakshmi · Model: timbre-v3.0 · Speed: 0.95 · Sample Rate: 8000 Hz</div>
                </div>
            </div>

            <div class="speech-box">
                <div class="speech-label">ಕೃಷಿ ಮಿತ್ರ ನೀಡಿದ ಧ್ವನಿ ಉತ್ತರ (Spoken Kannada Text):</div>
                <div class="speech-text">ಕೃಷಿ ಮಿತ್ರ: ಭತ್ತದ ಬೆಳೆಯಲ್ಲಿ ಎಲೆ ಸುತ್ತುವ ಹುಳು ಕಂಡುಬಂದರೆ, ಮುನ್ನೆಚ್ಚರಿಕೆ ಕ್ರಮಗಳನ್ನು ಕೈಗೊಳ್ಳಿ.</div>
            </div>

            <div class="trans-box">
                <div class="trans-label">English Translation:</div>
                <div class="trans-text">“Krishi Mitra: If leaf folder caterpillars are observed in the paddy crop, take precautionary control measures.”</div>
            </div>

            <div class="notes-row">
                <div class="note-col">
                    <div class="note-head">{SVG_CHECK} Synthesized Audio Streaming</div>
                    <div class="note-desc">Direct streaming delivery with response boundary checks.</div>
                </div>
                <div class="note-col">
                    <div class="note-head">{SVG_CHECK} Response End Protection</div>
                    <div class="note-desc">Explicit completion tracking prevents cutoffs before listening.</div>
                </div>
                <div class="note-col">
                    <div class="note-head">{SVG_CHECK} Playback Synchronization</div>
                    <div class="note-desc">Active Listen and Stop controls synchronized with browser audio.</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_5_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.challenges-row {{
    display: flex;
    gap: 24px;
    flex: 1;
}}
.challenge-card {{
    flex: 1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 16px;
    padding: 24px 22px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.card-header-badge {{
    background-color: #123026;
    color: #e6b422;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 700;
    line-height: 1.25;
    letter-spacing: 0.5px;
}}
.section-tag-red {{
    font-size: 16px;
    font-weight: 700;
    color: #b42828;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.section-body-muted {{
    font-size: 17px;
    line-height: 1.45;
    color: #55695f;
}}
.card-divider {{
    height: 1px;
    background-color: #e2ede6;
    margin: 2px 0;
}}
.section-tag-green {{
    font-size: 16px;
    font-weight: 700;
    color: #2e7d32;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.section-body-dark {{
    font-size: 17px;
    line-height: 1.45;
    color: #14231c;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">Engineering Challenges & Improvements</div>
        <div class="title-line-2">(ತಾಂತ್ರಿಕ ಸವಾಲುಗಳು ಮತ್ತು ಪರಿಹಾರ)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="challenges-row">
            <div class="challenge-card">
                <div class="card-header-badge">1. AUDIO CUTOFFS & PLAYBACK TIMING</div>
                <div class="section-tag-red">Observed Behavior:</div>
                <div class="section-body-muted">WebSocket disconnects were observed during voice dialogue, and browser microphone intake could overlap with playback.</div>
                <div class="card-divider"></div>
                <div class="section-tag-green">Engineering Improvement:</div>
                <div class="section-body-dark">Implemented an explicit client-server playback acknowledgement protocol. The browser suppresses mic intake while audio is playing and waits for playback completion.</div>
            </div>

            <div class="challenge-card">
                <div class="card-header-badge">2. CROP RETENTION IN MULTI-TURN DIALOGUE</div>
                <div class="section-tag-red">Observed Behavior:</div>
                <div class="section-body-muted">When symptoms were described before naming the crop, earlier versions could ask for the crop repeatedly or fail to advance.</div>
                <div class="card-divider"></div>
                <div class="section-tag-green">Engineering Improvement:</div>
                <div class="section-body-dark">Structured dialogue state to prioritize crop identification first, retain confirmed crops across turns, and transition directly to advisory content.</div>
            </div>

            <div class="challenge-card">
                <div class="card-header-badge">3. ACCESSIBLE BILINGUAL WEB EXPERIENCE</div>
                <div class="section-tag-red">Observed Behavior:</div>
                <div class="section-body-muted">Telephony integration involves carrier setup and environment dependencies during early testing.</div>
                <div class="card-divider"></div>
                <div class="section-tag-green">Engineering Improvement:</div>
                <div class="section-body-dark">Built the /ask web application alongside the simulator, offering instant Kannada/English toggles, fast reasoning, and direct spoken playback.</div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_6_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{BASE_CSS}
.safety-grid {{
    display: flex;
    gap: 28px;
    flex: 1;
}}
.safety-card-left {{
    flex: 1.1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 18px;
    padding: 24px 28px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.col-header-tag {{
    font-size: 16px;
    font-weight: 700;
    color: #2e7d32;
    letter-spacing: 0.5px;
}}
.col-title {{
    font-size: 26px;
    font-weight: 700;
    color: #14231c;
    margin-bottom: 2px;
}}
.safety-items {{
    display: flex;
    flex-direction: column;
    gap: 10px;
}}
.safety-item-box {{
    background-color: #fafcfb;
    border: 1px solid #d2e1d7;
    border-radius: 10px;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 3px;
}}
.item-head {{
    font-size: 18px;
    font-weight: 700;
    color: #14231c;
}}
.item-body {{
    font-size: 15px;
    line-height: 1.4;
    color: #55695f;
}}
.right-col {{
    flex: 0.9;
    display: flex;
    flex-direction: column;
    gap: 16px;
}}
.helpline-box {{
    background-color: #123026;
    border-radius: 16px;
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}}
.help-tag {{
    font-size: 15px;
    font-weight: 700;
    color: #e6b422;
    letter-spacing: 0.5px;
}}
.help-num {{
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
}}
.help-bullets {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.help-bullet {{
    font-size: 15px;
    line-height: 1.35;
    color: #c8ded5;
}}
.limits-box {{
    flex: 1;
    background-color: #ffffff;
    border: 2px solid #d2e1d7;
    border-radius: 16px;
    padding: 22px 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}}
.limits-tag {{
    font-size: 15px;
    font-weight: 700;
    color: #b42828;
    letter-spacing: 0.5px;
}}
.limits-title {{
    font-size: 22px;
    font-weight: 700;
    color: #14231c;
}}
.limits-bullets {{
    display: flex;
    flex-direction: column;
    gap: 6px;
}}
.limit-bullet {{
    font-size: 15px;
    line-height: 1.35;
    color: #55695f;
}}
</style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-col">
            <div class="challenge-badge">GNANI AI — GREAT INDIAN AI INTERNSHIP CHALLENGE</div>
            <div class="project-tag">Project Demonstration · 02:00 Edit</div>
        </div>
        <div class="logo-block">
            <div class="logo-kannada">ಕೃಷಿ ಮಿತ್ರ</div>
            <div class="logo-english">Krishi Mitra</div>
        </div>
    </div>
    
    <div class="title-section">
        <div class="title-line-1">Responsible Advisory & Realistic Scope</div>
        <div class="title-line-2">(ಜವಾಬ್ದಾರಿಯುತ ಸಲಹೆ ಮತ್ತು ಮಿತಿಗಳು)</div>
    </div>
    <div class="divider-line"></div>

    <div class="content-container">
        <div class="safety-grid">
            <div class="safety-card-left">
                <div class="col-header-tag">AGRICULTURAL SAFETY GUIDELINES</div>
                <div class="col-title">Advisory Boundaries & Practices</div>

                <div class="safety-items">
                    <div class="safety-item-box">
                        <div class="item-head">1. Non-Diagnostic Guidance</div>
                        <div class="item-body">Provides general agronomic guidance; does not replace in-person field inspection by plant pathologists.</div>
                    </div>
                    <div class="safety-item-box">
                        <div class="item-head">2. Chemical Advisory Gate</div>
                        <div class="item-body">Suppresses unreviewed chemical trade names and dosages from curated voice advisories.</div>
                    </div>
                    <div class="safety-item-box">
                        <div class="item-head">3. Clear Scope Boundaries</div>
                        <div class="item-body">Transparently limits advisory to paddy, arecanut, and coconut; refers other crops to agricultural officers.</div>
                    </div>
                    <div class="safety-item-box">
                        <div class="item-head">4. Safety & Protective Gear</div>
                        <div class="item-body">Highlights protective equipment (masks, gloves) and standard pre-harvest intervals.</div>
                    </div>
                </div>
            </div>

            <div class="right-col">
                <div class="helpline-box">
                    <div class="help-tag">EXTERNAL HELPLINE REFERRAL</div>
                    <div class="help-num">Kisan Call Centre: 1800-180-1551</div>
                    <div class="help-bullets">
                        <div class="help-bullet">• Government of India toll-free agricultural helpline referral</div>
                        <div class="help-bullet">• Explicitly recommended for severe, spreading, or unfamiliar crop conditions</div>
                        <div class="help-bullet">• Clearly identified as an external government service, not Krishi Mitra's number</div>
                    </div>
                </div>

                <div class="limits-box">
                    <div class="limits-tag">PROTOTYPE STATUS & LIMITATIONS</div>
                    <div class="limits-title">Development Scope</div>
                    <div class="limits-bullets">
                        <div class="limit-bullet">• Web App Demonstration: /ask and /sim prototypes are hosted on Render</div>
                        <div class="limit-bullet">• Telephony In Progress: Exotel IVR integration remains under active development</div>
                        <div class="limit-bullet">• Web Interface: Browser-based mobile view; requires network connectivity</div>
                        <div class="limit-bullet">• Expert Deference: High-stakes farming decisions defer to local KVK officers</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

def slide_7_html():
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
body {{
    width: 1920px;
    height: 1080px;
    overflow: hidden;
    background-color: #123026;
    font-family: 'Nirmala UI', 'Segoe UI', system-ui, sans-serif;
    color: #ffffff;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 60px 100px;
    gap: 22px;
}}
.project-title-block {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
}}
.main-kannada-title {{
    font-size: 82px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.1;
    letter-spacing: 1px;
}}
.main-english-title {{
    font-size: 38px;
    font-weight: 700;
    color: #e6b422;
    letter-spacing: 4px;
}}
.motto-text {{
    font-size: 28px;
    font-weight: 500;
    color: #d8f3dc;
    letter-spacing: 0.5px;
}}
.closing-divider {{
    width: 680px;
    height: 2px;
    background-color: #2d6a4f;
    margin: 6px 0;
}}
.event-info {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
}}
.challenge-callout {{
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
}}
.purpose-sub {{
    font-size: 21px;
    color: #b4d2c3;
}}
.links-card {{
    background-color: #1c4436;
    border: 2px solid #2d6a4f;
    border-radius: 16px;
    padding: 24px 36px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 1100px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}}
.link-row {{
    display: flex;
    align-items: center;
    gap: 16px;
    font-size: 22px;
}}
.link-icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.link-label {{
    font-weight: 700;
    color: #e6b422;
    width: 240px;
}}
.link-url {{
    font-weight: 500;
    color: #ffffff;
    font-family: 'Consolas', 'Segoe UI', monospace;
    font-size: 21px;
}}
.link-desc {{
    font-weight: 500;
    color: #d8f3dc;
    font-size: 21px;
}}
.gratitude-block {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
}}
.gratitude-kn {{
    font-size: 34px;
    font-weight: 700;
    color: #d8f3dc;
}}
.gratitude-en {{
    font-size: 28px;
    font-weight: 600;
    color: #b4d2c3;
}}
</style>
</head>
<body>
    <div class="project-title-block">
        <div class="main-kannada-title">ಕೃಷಿ ಮಿತ್ರ</div>
        <div class="main-english-title">KRISHI MITRA</div>
    </div>

    <div class="motto-text">“Speak. Understand. Take the next step.”</div>

    <div class="closing-divider"></div>

    <div class="event-info">
        <div class="challenge-callout">Built for the Gnani AI Great Indian AI Internship Challenge</div>
        <div class="purpose-sub">Empowering Karnataka's farmers with Kannada voice AI</div>
    </div>

    <div class="links-card">
        <div class="link-row">
            <div class="link-icon">{SVG_GLOBE}</div>
            <div class="link-label">Live Application:</div>
            <div class="link-url">https://krishi-mitra-gn3h.onrender.com/</div>
        </div>
        <div class="link-row">
            <div class="link-icon">{SVG_CODE}</div>
            <div class="link-label">GitHub Repository:</div>
            <div class="link-url">https://github.com/11DDBOY11/Gnani_ai_Competition</div>
        </div>
        <div class="link-row">
            <div class="link-icon">{SVG_CHIP}</div>
            <div class="link-label">Core Pipeline:</div>
            <div class="link-desc">Gnani AI STT & TTS · FastAPI · Groq LLM · PWA</div>
        </div>
    </div>

    <div class="gratitude-block">
        <div class="gratitude-kn">ಧನ್ಯವಾದಗಳು</div>
        <div class="gratitude-en">· Thank You</div>
    </div>
</body>
</html>"""

async def generate_all():
    slides = [
        ("slide_1.png", slide_1_html()),
        ("slide_2.png", slide_2_html()),
        ("slide_3.png", slide_3_html()),
        ("slide_4.png", slide_4_html()),
        ("slide_5.png", slide_5_html()),
        ("slide_6.png", slide_6_html()),
        ("slide_7.png", slide_7_html()),
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge")
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        for name, html in slides:
            await page.set_content(html)
            out_slide = os.path.join(OUTPUT_DIR, name)
            out_preview = os.path.join(PREVIEW_DIR, f"preview_{name}")
            
            await page.screenshot(path=out_slide)
            # Preview also saved at 1920x1080 (or copy)
            await page.screenshot(path=out_preview)
            print(f"Generated {out_slide} and {out_preview}")
            
        await browser.close()
    print("All 7 slides rendered cleanly via Edge/Playwright!")

if __name__ == "__main__":
    asyncio.run(generate_all())

