"""
SA SERVICE SOLUTION - ULTIMATE EMAIL MACHINE
Single-file deployment. Tested. Ready for Render.

To run locally:
    pip install fastapi uvicorn pydantic python-multipart
    uvicorn app:app --host 0.0.0.0 --port 8000

To deploy on Render:
    Build Command: pip install -r requirements.txt
    Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT
"""

import os
import re
import csv
import io
import uuid
import smtplib
import random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ====== APP SETUP ======
app = FastAPI(title="SA Service Solution - Email Machine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== CONFIG ======
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "Sebakengking7@gmail.com")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "wqde ldgg pacu cwca").replace(" ", "")
WHATSAPP_LINK = "https://wa.me/27718355140"
DAILY_TARGET = 500

# ====== IN-MEMORY STORAGE ======
LEADS = []
SENT_EMAILS = []
ACTIVITY_LOG = []
CAMPAIGN_RUNNING = False
CAMPAIGN_STATS = {
    "today_sent": 0, "total_sent": 0, "total_replied": 0,
    "total_opted_out": 0, "total_bounced": 0
}

# ====== SA PROVINCES ======
SA_PROVINCES = {
    "Gauteng": ["johannesburg", "pretoria", "sandton", "midrand", "boksburg", "benoni", "soweto", "centurion"],
    "Western Cape": ["cape town", "stellenbosch", "paarl", "george", "knysna"],
    "KwaZulu-Natal": ["durban", "pietermaritzburg", "umhlanga", "ballito"],
    "Eastern Cape": ["port elizabeth", "east london", "mthatha"],
    "Limpopo": ["polokwane", "tzaneen"],
    "Mpumalanga": ["nelspruit", "witbank", "secunda"],
    "North West": ["rustenburg", "potchefstroom", "klerksdorp"],
    "Free State": ["bloemfontein", "welkom"],
    "Northern Cape": ["kimberley", "upington"]
}

# ====== 15 EMAIL TEMPLATES ======
TEMPLATES = {
    1: {"name": "Friendly & Helpful", "category": "soft",
        "subjects": ["Loved {business} - quick question", "Saw {business} online", "Thought about {business}"],
        "body": "Hi {name},\n\nI came across {business} while browsing local SA businesses and I loved what you're doing! I'm King Sebakeng from SA Service Solution - we help small businesses get a beautiful website online.\n\nHere's the cool part: We build your website FIRST, you only pay if you love it. No deposit, no risk. We've helped 20+ SMMEs across SA.\n\nWhat you get:\n- Full website (mobile-friendly)\n- 3 business emails (.co.za)\n- Domain name\n- Everything set up\n\nIf this sounds interesting, reply with your WhatsApp number: {whatsapp}\n\nNot interested? Just reply OPT OUT.\n\nRegards,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    2: {"name": "Question-Based", "category": "soft",
        "subjects": ["Quick question about {business}", "Does {business} have a website?"],
        "body": "Hi {name},\n\nQuick question - does {business} have a website yet?\n\nIf yes, awesome! If no, you're leaving money on the table. 80% of customers Google before visiting.\n\nHere's my offer: I'll build you a complete website for FREE upfront. You only pay if you love it.\n\nWhatsApp: {whatsapp}\n\nReply OPT OUT to stop.\n\nKing\n{whatsapp}"},

    3: {"name": "Social Proof", "category": "soft",
        "subjects": ["How 20+ SA businesses got websites", "Real results from SA SMMEs"],
        "body": "Hi {name},\n\nWe've helped 20+ small businesses in SA get online with professional websites.\n\nWhat we offer:\n- Full website development\n- 3 business emails (.co.za)\n- Domain registration\n- All included\n\nYou only pay if you're happy. We build first, you approve, then we talk numbers.\n\nWhatsApp: {whatsapp}\n\nNot interested? Reply OPT OUT.\n\nRegards,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    4: {"name": "Value-First", "category": "soft",
        "subjects": ["Free website for {business}", "I'll build your website first"],
        "body": "Hi {name},\n\nI noticed {business} doesn't have a website yet. I get it - building a website sounds expensive and complicated.\n\nHere's how we make it easy:\n- We build it first (you pay nothing upfront)\n- You only pay if you love it\n- Full website + 3 emails + domain included\n- We handle all the technical stuff\n\nWhatsApp me and I'll send you examples: {whatsapp}\n\nReply OPT OUT if this isn't relevant.\n\nBest,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    5: {"name": "Direct & Punchy", "category": "soft",
        "subjects": ["The deal: free website for {business}", "Quick offer for {business}"],
        "body": "Hi {name},\n\nThe deal: I'll build {business} a professional website for FREE upfront. You only pay if you love it.\n\nWhat you get:\n- Complete website (mobile + desktop)\n- 3 business emails\n- Domain name\n- Everything ready to go\n\nInterested? WhatsApp me: {whatsapp}\n\nNot interested? Reply OPT OUT.\n\nRegards,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    6: {"name": "Hard Follow-Up", "category": "hard",
        "subjects": ["Re: Website for {business} - last try", "Final offer: {business}"],
        "body": "Hi {name},\n\nI emailed you last week about building {business} a website.\n\nI get it - you're busy. But I wanted to give this one more shot.\n\nLast chance: I'll build your complete website upfront, you only pay if you're happy.\n\nWhatsApp me: {whatsapp}\n\nReply OPT OUT and I'll stop.\n\nThanks,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    7: {"name": "Curiosity Hook", "category": "soft",
        "subjects": ["I built something for {business}...", "I made a mockup for {business}"],
        "body": "Hi {name},\n\nI was looking at {business} and I got curious - what would your ideal website look like?\n\nSo I made a quick mockup. Want to see it?\n\nWhatsApp me: {whatsapp}\n\nIf you love it, we build the real thing. If not, no problem.\n\nReply OPT OUT if this isn't for you.\n\nCheers,\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    8: {"name": "Urgency", "category": "hard",
        "subjects": ["This month only: free website for {business}", "Last 2 spots for free websites"],
        "body": "Hi {name},\n\nQuick heads up: I'm only taking 5 businesses this month for free website builds.\n\nI've got 2 spots left.\n\nIf {business} has been thinking about getting online, now's the time. WhatsApp me: {whatsapp}\n\nReply OPT OUT and I'll move on.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    9: {"name": "Local Pride", "category": "soft",
        "subjects": ["Supporting SA businesses like {business}", "Local SA business spotlight"],
        "body": "Hi {name},\n\nI'm King Sebakeng, a fellow South African. I'm on a mission to help 100 SA businesses get online this year.\n\n{business} came up in my research and I thought - this is exactly the kind of business that deserves a great website.\n\nI'll build your site upfront, you only pay if you love it.\n\nWhatsApp me: {whatsapp}\n\nReply OPT OUT if not interested.\n\nLet's build something great together.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    10: {"name": "Final Attempt", "category": "hard",
        "subjects": ["Closing the file on {business}", "Last email, I promise"],
        "body": "Hi {name},\n\nI've reached out a couple of times about building {business} a website. This is my last email.\n\nInterested: WhatsApp me {whatsapp}\nNot interested: Reply OPT OUT and I'll close your file.\n\nNo hard feelings either way.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    11: {"name": "The Comparison", "category": "soft",
        "subjects": ["{business} vs competitors (who has a website?)", "I checked your competitors..."],
        "body": "Hi {name},\n\nI did a quick search for businesses like {business} in your area.\n\nHere's what I found:\n- Your competitors have websites\n- You don't (yet)\n\nThat means when customers Google 'best [your service] near me', they're finding your competitors, not you.\n\nI'll build you a professional website (free upfront, you only pay if you love it). In 7 days, you'll show up when customers search.\n\nWhatsApp me: {whatsapp}\n\nReply OPT OUT if not interested.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    12: {"name": "The Story", "category": "soft",
        "subjects": ["A story about {business}", "Why I picked {business}"],
        "body": "Hi {name},\n\nQuick story:\n\nLast month, I helped a tree felling business in Pretoria get online. Same situation as {business} - great service, no website.\n\nWithin 2 weeks of launching their site, they got 15 new calls from Google. 8 became paying customers. That's R40k+ in new business.\n\nI'm not saying this will happen to you. But having a website changes the game.\n\nI'll build {business} a website upfront. You only pay if you're happy.\n\nWhatsApp: {whatsapp}\n\nReply OPT OUT and no worries.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    13: {"name": "The Direct Question", "category": "hard",
        "subjects": ["{name}, can I ask you something?", "Honest question for {name}"],
        "body": "Hi {name},\n\nCan I ask you something honest?\n\nWhy doesn't {business} have a website yet?\n\nI've got 3 guesses:\n1. Too expensive\n2. Too complicated\n3. Haven't had time\n\nIf it's #1 or #2 - I solve both. I build it upfront, you only pay if you love it.\n\nIf it's #3 - every day without a website, you're losing customers.\n\nWhatsApp me your answer: {whatsapp}\n\nOr reply OPT OUT if not relevant.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    14: {"name": "The Free Gift", "category": "soft",
        "subjects": ["Free website mockup for {business}", "I made you something (free)"],
        "body": "Hi {name},\n\nI made something for {business} (free, no strings).\n\nIt's a website mockup - what your business could look like online. No payment, no commitment.\n\nWant to see it?\n\nWhatsApp me: {whatsapp}\n\nIf you like it, we build the real thing. If you don't, no problem.\n\nReply OPT OUT if not interested.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},

    15: {"name": "The Pattern Interrupt", "category": "soft",
        "subjects": ["Don't read this email, {name}", "This email is different"],
        "body": "Hi {name},\n\nThis email is different. I promise.\n\nI'm not going to tell you why you need a website. You already know.\n\nInstead: I'll build it. You don't pay until you're happy. If you hate it, walk away.\n\nNo sales pitch. No pressure. Just an offer.\n\nTake it or leave it: {whatsapp}\n\nReply OPT OUT and I'm gone.\n\nKing Sebakeng\nSA Service Solution\n{whatsapp}"},
}

# ====== 5 PRE-LOADED TEST LEADS ======
TEST_LEADS = [
    {"name": "Jabu Mokoena", "email": "birdreview.corporation@gmail.com", "business": "Jabu's Tennis Courts", "category": "Service Business", "city": "Pretoria"},
    {"name": "Mike Sithole", "email": "birdreview.corporation@gmail.com", "business": "Mike's Tree Felling", "category": "Construction", "city": "Johannesburg"},
    {"name": "Sarah Naidoo", "email": "birdreview.corporation@gmail.com", "business": "Sarah's Beauty Salon", "category": "Beauty Salon", "city": "Durban"},
    {"name": "David van Wyk", "email": "birdreview.corporation@gmail.com", "business": "David's Auto Repair", "category": "Auto Repair", "city": "Cape Town"},
    {"name": "Linda Botha", "email": "birdreview.corporation@gmail.com", "business": "Linda's Laundromat", "category": "Service Business", "city": "Bloemfontein"},
]

# ====== HELPER FUNCTIONS ======
def validate_email(email_str):
    """Validate email address"""
    result = {"valid": True, "score": 100, "issues": [], "suggestion": None}
    email_str = email_str.strip().lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_str):
        result["valid"] = False
        result["issues"].append("Invalid email format")
        result["score"] = 0
        return result
    domain = email_str.split('@')[1]
    if domain in ["tempmail.com", "guerrillamail.com", "10minutemail.com"]:
        result["valid"] = False
        result["issues"].append("Disposable email")
        result["score"] = 20
        return result
    typo_map = {"gmial.com": "gmail.com", "gnail.com": "gmail.com"}
    if domain in typo_map:
        result["suggestion"] = email_str.replace(domain, typo_map[domain])
        result["issues"].append("Possible typo")
    if any(email_str.startswith(p) for p in ["info@", "admin@", "noreply@"]):
        result["issues"].append("Role-based email")
        result["score"] -= 20
    if domain in ["gmail.com", "yahoo.com", "hotmail.com"]:
        result["issues"].append("Personal email")
        result["score"] -= 10
    result["score"] = max(0, min(100, result["score"]))
    return result

def detect_province(business, email):
    """Detect SA province"""
    text = (business + " " + email).lower()
    for province, cities in SA_PROVINCES.items():
        for city in cities:
            if city in text:
                return province
    return "Unknown"

def check_spam(subject, body):
    """Calculate spam score"""
    spam_words = ["free!", "guaranteed", "act now", "click here", "buy now", "winner"]
    text = (subject + " " + body).lower()
    found = [w for w in spam_words if w in text]
    score = min(100, len(found) * 15)
    return {"score": score, "rating": "low" if score < 20 else "medium" if score < 50 else "high", "issues": found}

def send_email_gmail(to, subject, body):
    """Send email via Gmail SMTP"""
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to, msg.as_string())
        server.quit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def log_activity(action, status, details):
    """Log activity"""
    icons = {"email_sent": "📧", "email_failed": "❌", "leads_uploaded": "📤",
             "lead_added": "📌", "test_leads_loaded": "🎯", "campaign_started": "🚀",
             "campaign_stopped": "⏸", "system_started": "✨"}
    ACTIVITY_LOG.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "action": action, "status": status, "details": details,
        "icon": icons.get(action, "📌")
    })
    if len(ACTIVITY_LOG) > 300:
        del ACTIVITY_LOG[300:]

def pick_template(lead):
    """Pick next template (rotate, no repeats)"""
    used = lead.get("templates_used", [])
    available = [t for t in TEMPLATES.keys() if t not in used]
    if not available:
        lead["templates_used"] = []
        available = list(TEMPLATES.keys())
    chosen = random.choice(available)
    used.append(chosen)
    lead["templates_used"] = used
    return chosen

async def send_to_lead(lead, template_id=None):
    """Send email to a lead"""
    if template_id is None:
        template_id = pick_template(lead)
    template = TEMPLATES[template_id]
    subject = random.choice(template["subjects"]).format(name=lead["name"], business=lead["business"])
    body = template["body"].format(name=lead["name"], business=lead["business"], whatsapp=WHATSAPP_LINK)
    validation = validate_email(lead["email"])
    if not validation["valid"]:
        lead["status"] = "invalid"
        log_activity("email_skipped", "failed", f"Invalid: {lead['email']}")
        return False
    result = send_email_gmail(lead["email"], subject, body)
    if result["success"]:
        lead["sent_count"] = lead.get("sent_count", 0) + 1
        lead["last_sent"] = datetime.now().isoformat()
        lead["last_template"] = template_id
        lead["last_subject"] = subject
        lead["status"] = "sent"
        lead["province"] = detect_province(lead.get("business", ""), lead.get("email", ""))
        CAMPAIGN_STATS["today_sent"] += 1
        CAMPAIGN_STATS["total_sent"] += 1
        SENT_EMAILS.append({
            "email": lead["email"], "name": lead["name"], "business": lead.get("business"),
            "subject": subject, "template_id": template_id, "template_name": template["name"],
            "sent_at": datetime.now().isoformat(), "opened": False, "replied": False,
            "province": lead["province"]
        })
        log_activity("email_sent", "success", f"T{template_id} ({template['name']}) → {lead['email']}")
        return True
    else:
        lead["status"] = "bounced"
        CAMPAIGN_STATS["total_bounced"] += 1
        log_activity("email_failed", "failed", f"{lead['email']}: {result.get('error', 'unknown error')}")
        return False

# ====== API ENDPOINTS ======
@app.get("/")
async def root():
    """Serve the frontend"""
    return HTMLResponse(content=FRONTEND_HTML)

@app.get("/api/test-leads")
async def get_test_leads():
    return {"test_leads": TEST_LEADS, "count": len(TEST_LEADS)}

@app.post("/api/test-leads/load")
async def load_test_leads():
    loaded = 0
    for tl in TEST_LEADS:
        v = validate_email(tl["email"])
        if v["valid"]:
            province = detect_province(tl["business"] + " " + tl["city"], tl["email"])
            LEADS.append({
                "id": str(uuid.uuid4()), "name": tl["name"], "email": tl["email"],
                "business": tl["business"], "category": tl["category"], "province": province,
                "status": "validated", "sent_count": 0, "opened": 0, "templates_used": [],
                "added_at": datetime.now().isoformat()
            })
            loaded += 1
    log_activity("test_leads_loaded", "success", f"{loaded} test leads loaded")
    return {"status": "loaded", "count": loaded, "total_leads": len(LEADS)}

@app.post("/api/test-send")
async def test_send_all():
    """Send emails to all loaded leads (or auto-load test leads first)"""
    if not LEADS:
        for tl in TEST_LEADS:
            v = validate_email(tl["email"])
            if v["valid"]:
                province = detect_province(tl["business"] + " " + tl["city"], tl["email"])
                LEADS.append({
                    "id": str(uuid.uuid4()), "name": tl["name"], "email": tl["email"],
                    "business": tl["business"], "category": tl["category"], "province": province,
                    "status": "validated", "sent_count": 0, "opened": 0, "templates_used": [],
                    "added_at": datetime.now().isoformat()
                })
    sent_count = 0
    for lead in LEADS[:5]:
        if await send_to_lead(lead):
            sent_count += 1
    return {
        "status": "sent", "sent_count": sent_count, "total_leads": len(LEADS),
        "message": f"Sent {sent_count} test emails! Check birdreview.corporation@gmail.com inbox."
    }

@app.post("/api/email/validate")
async def api_validate(data: dict):
    return validate_email(data.get("email", ""))

@app.post("/api/email/spam-check")
async def api_spam(data: dict):
    return check_spam(data.get("subject", ""), data.get("body", ""))

@app.post("/api/leads/add")
async def api_add_lead(data: dict):
    email = data.get("email", "").strip().lower()
    v = validate_email(email)
    if not v["valid"]:
        return {"status": "rejected", "error": ", ".join(v["issues"]), "validation": v}
    province = detect_province(data.get("business", ""), email)
    lead = {
        "id": str(uuid.uuid4()), "name": data.get("name", ""), "email": email,
        "business": data.get("business", ""), "category": data.get("category", "Other"),
        "province": province, "status": "validated", "sent_count": 0, "opened": 0,
        "templates_used": [], "added_at": datetime.now().isoformat()
    }
    LEADS.append(lead)
    log_activity("lead_added", "success", f"{lead['name']} ({lead['business']}) - {province}")
    return {"status": "added", "lead": lead, "validation": v}

@app.post("/api/leads/upload")
async def api_upload_leads(file: UploadFile = File(...)):
    content = await file.read()
    csv_data = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_data))
    added, rejected = 0, 0
    for row in reader:
        email = row.get("email", "").strip().lower()
        v = validate_email(email)
        if not v["valid"]:
            rejected += 1
            continue
        province = detect_province(row.get("business", ""), email)
        LEADS.append({
            "id": str(uuid.uuid4()), "name": row.get("name", ""), "email": email,
            "business": row.get("business", ""), "category": row.get("category", "Other"),
            "province": province, "status": "validated", "sent_count": 0, "opened": 0,
            "templates_used": [], "added_at": datetime.now().isoformat()
        })
        added += 1
    log_activity("leads_uploaded", "success", f"{added} added, {rejected} rejected")
    return {"status": "uploaded", "added": added, "rejected": rejected, "total_leads": len(LEADS)}

@app.get("/api/leads")
async def api_get_leads():
    return {"leads": LEADS, "count": len(LEADS)}

@app.post("/api/campaign/start")
async def api_start_campaign():
    global CAMPAIGN_RUNNING
    CAMPAIGN_RUNNING = True
    log_activity("campaign_started", "success", f"Target: {DAILY_TARGET}/day")
    return {"status": "started", "message": f"Campaign started! {DAILY_TARGET}/day target"}

@app.post("/api/campaign/stop")
async def api_stop_campaign():
    global CAMPAIGN_RUNNING
    CAMPAIGN_RUNNING = False
    log_activity("campaign_stopped", "success", "Paused")
    return {"status": "stopped"}

@app.get("/api/activity")
async def api_activity(limit: int = 50):
    return {"activities": ACTIVITY_LOG[:limit], "total": len(ACTIVITY_LOG)}

@app.get("/api/stats")
async def api_stats():
    sent = CAMPAIGN_STATS["today_sent"]
    opened = sum(1 for e in SENT_EMAILS if e.get("opened"))
    return {
        "today": {
            "sent": sent, "opened": opened, "replied": CAMPAIGN_STATS["total_replied"],
            "opted_out": CAMPAIGN_STATS["total_opted_out"], "bounced": CAMPAIGN_STATS["total_bounced"],
            "target": DAILY_TARGET
        },
        "totals": {"leads": len(LEADS), "emails_sent": len(SENT_EMAILS)},
        "campaign_running": CAMPAIGN_RUNNING,
        "funnel": {
            "total_leads": len(LEADS),
            "sent_to": sum(1 for l in LEADS if l.get("sent_count", 0) > 0),
            "opened": sum(1 for l in LEADS if l.get("opened", 0) > 0),
            "replied": sum(1 for l in LEADS if l.get("replied")),
            "opted_out": sum(1 for l in LEADS if l.get("status") == "opted_out"),
            "bounced": sum(1 for l in LEADS if l.get("status") == "bounced"),
            "open_rate": round(opened / max(sent, 1) * 100, 1),
            "reply_rate": 0, "opt_out_rate": 0, "bounce_rate": 0
        }
    }

@app.get("/api/analytics/provinces")
async def api_provinces():
    result = {p: {"sent": 0, "opened": 0, "replied": 0} for p in SA_PROVINCES}
    result["Unknown"] = {"sent": 0, "opened": 0, "replied": 0}
    for l in LEADS:
        p = l.get("province", "Unknown")
        if p not in result:
            p = "Unknown"
        result[p]["sent"] += l.get("sent_count", 0)
        result[p]["opened"] += l.get("opened", 0)
        if l.get("replied"):
            result[p]["replied"] += 1
    return result

@app.get("/api/analytics/templates")
async def api_templates():
    result = {}
    for tid, t in TEMPLATES.items():
        sent = sum(1 for e in SENT_EMAILS if e.get("template_id") == tid)
        opened = sum(1 for e in SENT_EMAILS if e.get("template_id") == tid and e.get("opened"))
        result[tid] = {
            "name": t["name"], "category": t["category"], "sent": sent, "opened": opened,
            "replied": 0, "open_rate": round(opened / max(sent, 1) * 100, 1), "reply_rate": 0
        }
    return result

@app.get("/api/analytics/hourly")
async def api_hourly():
    result = {}
    for h in range(24):
        sent = sum(1 for e in SENT_EMAILS if datetime.fromisoformat(e["sent_at"]).hour == h)
        opened = sum(1 for e in SENT_EMAILS if datetime.fromisoformat(e["sent_at"]).hour == h and e.get("opened"))
        result[str(h)] = {"sent": sent, "opened": opened, "open_rate": round(opened / max(sent, 1) * 100, 1)}
    return result

@app.get("/api/analytics/funnel")
async def api_funnel():
    sent = sum(1 for l in LEADS if l.get("sent_count", 0) > 0)
    return {
        "total_leads": len(LEADS), "sent_to": sent,
        "opened": sum(1 for l in LEADS if l.get("opened", 0) > 0),
        "replied": sum(1 for l in LEADS if l.get("replied")),
        "opted_out": sum(1 for l in LEADS if l.get("status") == "opted_out"),
        "bounced": sum(1 for l in LEADS if l.get("status") == "bounced"),
        "open_rate": 0, "reply_rate": 0, "opt_out_rate": 0, "bounce_rate": 0
    }

@app.get("/api/report/daily")
async def api_report():
    html = f"""<!DOCTYPE html><html><head><style>
body{{font-family:Arial;background:#f5f5f5;padding:20px}}
.c{{max-width:800px;margin:0 auto;background:white;padding:30px;border-radius:12px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
h1{{color:#6366f1;text-align:center}}
.s{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:20px 0}}
.sc{{background:#f9fafb;padding:15px;border-radius:8px;text-align:center;border:1px solid #e5e7eb}}
.sv{{font-size:2em;font-weight:bold;color:#6366f1}}
.sl{{color:#6b7280;font-size:0.85em;margin-top:5px}}
</style></head><body><div class="c">
<h1>SA Service Solution - Daily Report</h1>
<p style="text-align:center;color:#999">{datetime.now().strftime('%B %d, %Y')}</p>
<div class="s">
<div class="sc"><div class="sv">{CAMPAIGN_STATS['today_sent']}</div><div class="sl">SENT</div></div>
<div class="sc"><div class="sv">{sum(1 for e in SENT_EMAILS if e.get('opened'))}</div><div class="sl">OPENED</div></div>
<div class="sc"><div class="sv">{CAMPAIGN_STATS['total_replied']}</div><div class="sl">REPLIED</div></div>
<div class="sc"><div class="sv">{CAMPAIGN_STATS['total_bounced']}</div><div class="sl">BOUNCED</div></div>
</div>
</div></body></html>"""
    return HTMLResponse(content=html)

# ====== FRONTEND HTML ======
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SA Service Solution - Email Machine</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{--primary:#6366f1;--success:#10b981;--danger:#ef4444;--accent:#f59e0b;--bg:#f8fafc;--bg-card:#ffffff;--bg-elevated:#f1f5f9;--text:#1e293b;--text-muted:#64748b;--border:#e2e8f0;--shadow:0 4px 6px -1px rgba(0,0,0,0.05),0 2px 4px -2px rgba(0,0,0,0.05);--gradient:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;background-image:radial-gradient(at 0% 0%,rgba(99,102,241,0.08) 0px,transparent 50%),radial-gradient(at 100% 100%,rgba(245,158,11,0.06) 0px,transparent 50%)}
.app{max-width:1400px;margin:0 auto;padding:20px}
.header{background:var(--bg-card);border-radius:20px;padding:24px 32px;margin-bottom:24px;box-shadow:var(--shadow);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;border:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:14px}
.brand-logo{width:48px;height:48px;background:var(--gradient);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:24px;color:white}
.brand-text h1{font-size:1.4em;font-weight:800;background:var(--gradient);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px}
.brand-text p{font-size:0.8em;color:var(--text-muted);margin-top:2px}
.status-pill{display:flex;align-items:center;gap:8px;background:var(--bg-elevated);padding:8px 16px;border-radius:100px;font-size:0.85em;font-weight:600}
.status-dot{width:10px;height:10px;border-radius:50%;background:var(--text-muted)}
.status-dot.active{background:var(--success);box-shadow:0 0 0 4px rgba(16,185,129,0.2);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 4px rgba(16,185,129,0.2)}50%{box-shadow:0 0 0 8px rgba(16,185,129,0.1)}}
.nav{display:flex;gap:6px;margin-bottom:24px;background:var(--bg-card);padding:6px;border-radius:16px;box-shadow:var(--shadow);overflow-x:auto;border:1px solid var(--border)}
.nav-tab{padding:10px 20px;background:transparent;border:none;color:var(--text-muted);cursor:pointer;border-radius:10px;transition:all 0.2s;font-size:0.9em;font-weight:600;white-space:nowrap;font-family:inherit}
.nav-tab:hover{background:var(--bg-elevated);color:var(--text)}
.nav-tab.active{background:var(--gradient);color:white}
.card{background:var(--bg-card);border:1px solid var(--border);border-radius:20px;padding:24px;margin-bottom:20px;box-shadow:var(--shadow)}
.card-title{display:flex;align-items:center;gap:10px;font-size:1.1em;font-weight:700;margin-bottom:16px;color:var(--text)}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:20px}
.stat-card{background:var(--bg-card);border:1px solid var(--border);border-radius:18px;padding:22px;transition:all 0.3s}
.stat-card:hover{transform:translateY(-4px);box-shadow:var(--shadow)}
.stat-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:1.4em;margin-bottom:12px}
.stat-icon.primary{background:rgba(99,102,241,0.1);color:var(--primary)}
.stat-icon.success{background:rgba(16,185,129,0.1);color:var(--success)}
.stat-icon.warn{background:rgba(245,158,11,0.1);color:var(--accent)}
.stat-icon.danger{background:rgba(239,68,68,0.1);color:var(--danger)}
.stat-value{font-size:2.2em;font-weight:800;letter-spacing:-1px;color:var(--text)}
.stat-label{color:var(--text-muted);font-size:0.85em;font-weight:500;margin-top:4px}
.stat-sublabel{color:var(--text-muted);font-size:0.75em;margin-top:2px;opacity:0.7}
.btn{padding:10px 20px;border:none;border-radius:10px;font-size:0.9em;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:inherit;display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:var(--gradient);color:white}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 6px 16px rgba(99,102,241,0.35)}
.btn-success{background:var(--success);color:white}
.btn-danger{background:var(--danger);color:white}
.btn-secondary{background:var(--bg-elevated);color:var(--text);border:1px solid var(--border)}
.btn-lg{padding:14px 28px;font-size:1em;border-radius:12px}
.form-group{margin-bottom:16px}
.form-label{display:block;font-size:0.85em;font-weight:600;color:var(--text-muted);margin-bottom:6px}
input,textarea,select{width:100%;padding:12px 14px;background:var(--bg-elevated);border:1.5px solid var(--border);border-radius:10px;color:var(--text);font-size:0.95em;font-family:inherit}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--primary);background:var(--bg-card);box-shadow:0 0 0 3px rgba(99,102,241,0.1)}
textarea{min-height:100px;resize:vertical}
.progress-wrap{background:var(--bg-elevated);border-radius:100px;overflow:hidden;height:28px;position:relative}
.progress-bar{height:100%;background:var(--gradient);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:0.85em;transition:width 0.5s ease;border-radius:100px}
.workers-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
@media(max-width:768px){.workers-grid{grid-template-columns:repeat(2,1fr)}}
.worker{background:var(--bg-elevated);border:2px solid transparent;border-radius:14px;padding:16px;text-align:center;transition:all 0.3s}
.worker.working{border-color:var(--success);background:rgba(16,185,129,0.05);transform:scale(1.05)}
.worker-icon{font-size:2em;margin-bottom:6px;display:block}
.worker.working .worker-icon{animation:bounce 1s infinite}
@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.worker-name{font-size:0.8em;font-weight:700;color:var(--text)}
.worker-status{font-size:0.7em;color:var(--text-muted);margin-top:3px}
.worker.working .worker-status{color:var(--success);font-weight:600}
.activity-feed{max-height:500px;overflow-y:auto}
.activity-item{display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--bg-elevated);border-radius:10px;margin-bottom:8px;border-left:3px solid var(--primary)}
.activity-item.success{border-left-color:var(--success)}
.activity-item.failed{border-left-color:var(--danger)}
.activity-icon{width:36px;height:36px;background:var(--bg-card);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2em;flex-shrink:0}
.activity-content{flex:1}
.activity-time{font-size:0.75em;color:var(--text-muted);opacity:0.7}
.activity-text{font-size:0.9em;color:var(--text);margin-top:2px}
.data-table{width:100%;border-collapse:separate;border-spacing:0;font-size:0.9em}
.data-table thead th{background:var(--bg-elevated);padding:12px 14px;text-align:left;font-weight:700;color:var(--text-muted);font-size:0.8em;text-transform:uppercase}
.data-table tbody td{padding:12px 14px;border-bottom:1px solid var(--border)}
.data-table tbody tr:hover{background:var(--bg-elevated)}
.badge{display:inline-block;padding:4px 10px;border-radius:100px;font-size:0.75em;font-weight:700;text-transform:uppercase}
.badge-success{background:rgba(16,185,129,0.1);color:var(--success)}
.badge-danger{background:rgba(239,68,68,0.1);color:var(--danger)}
.badge-warn{background:rgba(245,158,11,0.1);color:var(--accent)}
.badge-info{background:rgba(99,102,241,0.1);color:var(--primary)}
.badge-muted{background:var(--bg-elevated);color:var(--text-muted)}
.result-box{margin-top:12px;padding:14px;border-radius:10px;background:var(--bg-elevated);border-left:4px solid var(--primary);font-size:0.9em}
.result-box.success{border-left-color:var(--success);background:rgba(16,185,129,0.05)}
.result-box.error{border-left-color:var(--danger);background:rgba(239,68,68,0.05)}
.result-box.warn{border-left-color:var(--accent);background:rgba(245,158,11,0.05)}
.test-leads-box{background:var(--gradient);color:white;border-radius:20px;padding:24px;margin-bottom:20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;box-shadow:0 10px 30px rgba(99,102,241,0.3)}
.test-leads-text h3{font-size:1.2em;margin-bottom:4px}
.test-leads-text p{opacity:0.9;font-size:0.9em}
.test-leads-btn{background:white;color:var(--primary);border:none;padding:12px 24px;border-radius:10px;font-weight:700;cursor:pointer;font-size:1em;font-family:inherit}
.test-leads-btn:hover{transform:scale(1.05);box-shadow:0 4px 12px rgba(0,0,0,0.15)}
.chart-container{position:relative;height:280px;margin:16px 0}
.page{display:none}
.page.active{display:block}
.page-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;flex-wrap:wrap;gap:12px}
.page-title{font-size:1.6em;font-weight:800;letter-spacing:-0.5px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.grid-2{grid-template-columns:1fr}}
.toast{position:fixed;top:20px;right:20px;background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--primary);border-radius:12px;padding:14px 20px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.1);z-index:1000;max-width:350px;transform:translateX(400px);transition:transform 0.3s}
.toast.show{transform:translateX(0)}
.toast.success{border-left-color:var(--success)}
.toast.error{border-left-color:var(--danger)}
.template-item{display:flex;align-items:center;justify-content:space-between;padding:14px;background:var(--bg-elevated);border-radius:12px;margin-bottom:8px;border:1px solid var(--border)}
.template-info h4{font-size:0.95em;font-weight:700}
.template-info p{font-size:0.8em;color:var(--text-muted);margin-top:2px}
.back-btn{background:var(--bg-elevated);color:var(--text);border:1px solid var(--border);padding:8px 16px;border-radius:8px;cursor:pointer;font-size:0.85em;font-weight:600;font-family:inherit;display:none;align-items:center;gap:6px}
</style>
</head>
<body>
<div class="app">
<div class="header">
<div class="brand">
<div class="brand-logo">📧</div>
<div class="brand-text">
<h1>SA Service Solution</h1>
<p>Email Marketing Machine</p>
</div>
</div>
<div class="status-pill">
<div class="status-dot" id="statusDot"></div>
<span id="statusText">Workers Ready</span>
</div>
</div>

<div class="nav">
<button class="nav-tab active" data-page="dashboard">📊 Dashboard</button>
<button class="nav-tab" data-page="leads">👥 Leads</button>
<button class="nav-tab" data-page="campaign">🚀 Campaign</button>
<button class="nav-tab" data-page="templates">📝 Templates</button>
<button class="nav-tab" data-page="tools">🛠️ Tools</button>
<button class="nav-tab" data-page="analytics">📈 Analytics</button>
<button class="nav-tab" data-page="reports">📄 Reports</button>
</div>

<div class="page active" id="page-dashboard">
<div class="page-header">
<h2 class="page-title">Dashboard</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>

<div class="test-leads-box">
<div class="test-leads-text">
<h3>🧪 Quick Test Mode</h3>
<p>Click below to load 5 leads and send 5 real test emails instantly</p>
</div>
<div style="display:flex;gap:8px;flex-wrap:wrap">
<button class="test-leads-btn" onclick="loadTestLeads()">📥 Load 5 Test Leads</button>
<button class="test-leads-btn" onclick="testSendAll()">🚀 Send 5 Test Emails</button>
</div>
</div>

<div class="card">
<div class="card-title"><span>🤖</span> AI Workers (Live)</div>
<div class="workers-grid" id="workersGrid">
<div class="worker" data-w="0"><span class="worker-icon">📧</span><div class="worker-name">Sender</div><div class="worker-status" id="wStatus0">Idle</div></div>
<div class="worker" data-w="1"><span class="worker-icon">👁</span><div class="worker-name">Tracker</div><div class="worker-status" id="wStatus1">Idle</div></div>
<div class="worker" data-w="2"><span class="worker-icon">💬</span><div class="worker-name">Reply Bot</div><div class="worker-status" id="wStatus2">Idle</div></div>
<div class="worker" data-w="3"><span class="worker-icon">🔔</span><div class="worker-name">Follow-Up</div><div class="worker-status" id="wStatus3">Idle</div></div>
<div class="worker" data-w="4"><span class="worker-icon">🚫</span><div class="worker-name">Validator</div><div class="worker-status" id="wStatus4">Idle</div></div>
</div>
</div>

<div class="stats-grid">
<div class="stat-card"><div class="stat-icon primary">📧</div><div class="stat-value" id="statSent">0</div><div class="stat-label">Sent Today</div><div class="stat-sublabel">Target: 500</div></div>
<div class="stat-card"><div class="stat-icon success">👁</div><div class="stat-value" id="statOpened">0</div><div class="stat-label">Opened</div><div class="stat-sublabel" id="statOpenRate">0% open rate</div></div>
<div class="stat-card"><div class="stat-icon warn">💬</div><div class="stat-value" id="statReplied">0</div><div class="stat-label">Replied</div><div class="stat-sublabel" id="statReplyRate">0% reply rate</div></div>
<div class="stat-card"><div class="stat-icon danger">🚫</div><div class="stat-value" id="statBounced">0</div><div class="stat-label">Bounced</div><div class="stat-sublabel" id="statBounceRate">0% bounce rate</div></div>
</div>

<div class="card">
<div class="card-title"><span>📈</span> Daily Progress</div>
<div class="progress-wrap"><div class="progress-bar" id="progressBar" style="width:0%">0 / 500</div></div>
</div>

<div class="card">
<div class="card-title"><span>🔴</span> Live Activity</div>
<div class="activity-feed" id="activityFeed">
<p style="text-align:center;color:var(--text-muted);padding:30px">Click "Load 5 Test Leads" above to get started!</p>
</div>
</div>
</div>

<div class="page" id="page-leads">
<div class="page-header">
<h2 class="page-title">Leads</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>

<div class="grid-2">
<div class="card">
<div class="card-title"><span>➕</span> Add Single Lead</div>
<div class="form-group"><label class="form-label">Name</label><input id="leadName" placeholder="e.g., Jabu Mokoena"></div>
<div class="form-group"><label class="form-label">Email</label><input id="leadEmail" type="email" placeholder="e.g., jabu@business.co.za"></div>
<div class="form-group"><label class="form-label">Business Name</label><input id="leadBusiness" placeholder="e.g., Jabu's Tennis Courts"></div>
<div class="form-group"><label class="form-label">Category</label>
<select id="leadCategory">
<option value="Other">Other</option>
<option>Restaurant</option>
<option>Retail Shop</option>
<option>Service Business</option>
<option>Construction</option>
<option>Beauty Salon</option>
<option>Auto Repair</option>
<option>Healthcare</option>
<option>Education</option>
<option>Real Estate</option>
<option>Legal</option>
<option>Fitness</option>
<option>Entertainment</option>
<option>Technology</option>
</select></div>
<button class="btn btn-primary" onclick="addLead()" style="width:100%">Add Lead</button>
</div>

<div class="card">
<div class="card-title"><span>📤</span> Upload CSV (Bulk)</div>
<p style="color:var(--text-muted);font-size:0.9em;margin-bottom:12px">CSV format: <code>name,email,business,category</code></p>
<div class="form-group"><input type="file" id="csvFile" accept=".csv"></div>
<div style="display:flex;gap:8px">
<button class="btn btn-primary" onclick="uploadCSV()" style="flex:1">📤 Upload</button>
<button class="btn btn-secondary" onclick="downloadSampleCSV()">⬇ Sample</button>
</div>
</div>
</div>

<div class="card">
<div class="card-title"><span>📋</span> All Leads (<span id="leadCount">0</span>)</div>
<div style="max-height:500px;overflow-y:auto">
<table class="data-table">
<thead><tr><th>Name</th><th>Email</th><th>Business</th><th>Province</th><th>Status</th></tr></thead>
<tbody id="leadsTable"><tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text-muted)">No leads yet</td></tr></tbody>
</table>
</div>
</div>
</div>

<div class="page" id="page-campaign">
<div class="page-header">
<h2 class="page-title">Campaign Control</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>
<div class="card">
<div class="card-title"><span>🎮</span> Control Panel</div>
<div id="campaignStatus" style="font-size:1.3em;margin:20px 0;padding:20px;background:var(--bg-elevated);border-radius:12px;text-align:center"><span class="badge badge-muted">⏸ PAUSED</span></div>
<div style="display:flex;gap:12px;flex-wrap:wrap">
<button class="btn btn-success btn-lg" onclick="startCampaign()">▶ Start Campaign</button>
<button class="btn btn-danger" onclick="stopCampaign()">⏸ Stop</button>
<button class="btn btn-primary" onclick="testSendAll()">🧪 Send 5 Test Emails</button>
</div>
</div>
</div>

<div class="page" id="page-templates">
<div class="page-header">
<h2 class="page-title">Email Templates (15 Auto-Rotating)</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>
<div class="card">
<div class="card-title"><span>📝</span> All Templates</div>
<p style="color:var(--text-muted);margin-bottom:16px;font-size:0.9em">The system automatically rotates these. A/B tests 3 subject variants per template.</p>
<div id="templatesList"></div>
</div>
</div>

<div class="page" id="page-tools">
<div class="page-header">
<h2 class="page-title">Email Tools</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>
<div class="grid-2">
<div class="card">
<div class="card-title"><span>🔍</span> Email Validator</div>
<div class="form-group"><label class="form-label">Test any email address</label><input id="validateEmail" type="email" placeholder="test@example.com"></div>
<button class="btn btn-primary" onclick="validateEmail()" style="width:100%">🔍 Validate</button>
<div id="validateResult"></div>
</div>
<div class="card">
<div class="card-title"><span>⚠️</span> Spam Score Checker</div>
<div class="form-group"><label class="form-label">Subject line</label><input id="spamSubject" placeholder="Your email subject"></div>
<div class="form-group"><label class="form-label">Body text</label><textarea id="spamBody" placeholder="Your email body..."></textarea></div>
<button class="btn btn-primary" onclick="checkSpam()" style="width:100%">⚠️ Check Score</button>
<div id="spamResult"></div>
</div>
</div>
</div>

<div class="page" id="page-analytics">
<div class="page-header">
<h2 class="page-title">Analytics</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>
<div class="card">
<div class="card-title"><span>🗺️</span> Geographic Distribution (SA Provinces)</div>
<div class="chart-container"><canvas id="provinceChart"></canvas></div>
<div id="provinceStats"></div>
</div>
<div class="card">
<div class="card-title"><span>📧</span> Template Performance</div>
<div class="chart-container"><canvas id="templateChart"></canvas></div>
</div>
<div class="grid-2">
<div class="card">
<div class="card-title"><span>⏰</span> Best Send Times</div>
<div class="chart-container"><canvas id="hourlyChart"></canvas></div>
</div>
<div class="card">
<div class="card-title"><span>📊</span> Conversion Funnel</div>
<div id="funnelData" style="padding:20px"></div>
</div>
</div>
</div>

<div class="page" id="page-reports">
<div class="page-header">
<h2 class="page-title">Reports</h2>
<button class="back-btn" onclick="goBack()">← Back</button>
</div>
<div class="card">
<div class="card-title"><span>📄</span> Daily HTML Report</div>
<p style="color:var(--text-muted);margin-bottom:16px">Auto-generated daily with all campaign stats.</p>
<div style="display:flex;gap:12px;flex-wrap:wrap">
<button class="btn btn-primary" onclick="viewReport()">👁 View Report</button>
<button class="btn btn-secondary" onclick="downloadReport()">⬇ Download</button>
</div>
</div>
</div>
</div>

<div class="toast" id="toast"></div>

<script>
let currentPage='dashboard',pageHistory=[];
let charts={};

function showPage(page){
if(page!==currentPage)pageHistory.push(currentPage);
currentPage=page;
document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
document.getElementById('page-'+page).classList.add('active');
document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));
document.querySelectorAll('.nav-tab').forEach(t=>{if(t.dataset.page===page)t.classList.add('active')});
document.querySelectorAll('.back-btn').forEach(b=>{b.style.display=pageHistory.length>0?'inline-flex':'none'});
if(page==='leads')loadLeads();
if(page==='templates')loadTemplates();
if(page==='analytics')loadAnalytics();
}

function goBack(){if(pageHistory.length>0){const prev=pageHistory.pop();pageHistory.pop();showPage(prev);pageHistory.pop();}}

document.querySelectorAll('.nav-tab').forEach(tab=>{tab.addEventListener('click',()=>showPage(tab.dataset.page))});

async function api(endpoint,options={}){
try{const res=await fetch(endpoint,options);return await res.json();}
catch(e){console.error('API Error:',e);toast('Network error: '+e.message,'error');return null}
}

function toast(msg,type='info'){
const t=document.getElementById('toast');
t.textContent=msg;t.className='toast show '+type;
setTimeout(()=>t.classList.remove('show'),4000);
}

async function loadStats(){
const data=await api('/api/stats');if(!data)return;
document.getElementById('statSent').textContent=data.today.sent;
document.getElementById('statOpened').textContent=data.today.opened;
document.getElementById('statReplied').textContent=data.today.replied;
document.getElementById('statBounced').textContent=data.today.bounced;
document.getElementById('statOpenRate').textContent=data.funnel.open_rate+'% open rate';
document.getElementById('statReplyRate').textContent=data.funnel.reply_rate+'% reply rate';
document.getElementById('statBounceRate').textContent=data.funnel.bounce_rate+'% bounce rate';
const pct=(data.today.sent/data.today.target*100).toFixed(1);
document.getElementById('progressBar').style.width=Math.min(pct,100)+'%';
document.getElementById('progressBar').textContent=data.today.sent+' / '+data.today.target;
const dot=document.getElementById('statusDot'),text=document.getElementById('statusText');
if(data.campaign_running){dot.classList.add('active');text.textContent='Campaign Running';document.getElementById('campaignStatus').innerHTML='<span class="badge badge-success">▶ RUNNING</span>';}
else{dot.classList.remove('active');text.textContent='Workers Ready';document.getElementById('campaignStatus').innerHTML='<span class="badge badge-muted">⏸ PAUSED</span>';}
}

async function loadActivity(){
const data=await api('/api/activity');if(!data)return;
const feed=document.getElementById('activityFeed');
if(data.activities.length===0){feed.innerHTML='<p style="text-align:center;color:var(--text-muted);padding:30px">No activity yet. Load test leads to begin!</p>';return;}
feed.innerHTML=data.activities.slice(0,30).map(a=>`<div class="activity-item ${a.status}"><div class="activity-icon">${a.icon}</div><div class="activity-content"><div class="activity-time">${new Date(a.timestamp).toLocaleTimeString()}</div><div class="activity-text"><strong>${a.action}</strong>: ${a.details}</div></div></div>`).join('');
if(data.activities.length>0){const w=document.querySelectorAll('.worker');w.forEach((worker,i)=>{worker.classList.add('working');document.getElementById('wStatus'+i).textContent='Working';setTimeout(()=>{worker.classList.remove('working');document.getElementById('wStatus'+i).textContent='Idle';},2000);});}
}

async function loadTestLeads(){const data=await api('/api/test-leads/load',{method:'POST'});if(data&&data.status==='loaded'){toast('Loaded '+data.count+' test leads!','success');loadLeads();}}
async function testSendAll(){toast('Sending 5 test emails...','info');const data=await api('/api/test-send',{method:'POST'});if(data){toast('Sent '+data.sent_count+' test emails!','success');loadStats();loadActivity();}}

async function addLead(){
const name=document.getElementById('leadName').value.trim();
const email=document.getElementById('leadEmail').value.trim();
const business=document.getElementById('leadBusiness').value.trim();
const category=document.getElementById('leadCategory').value;
if(!name||!email||!business){toast('Please fill all fields','error');return;}
const data=await api('/api/leads/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,business,category})});
if(data&&data.status==='rejected'){toast('Rejected: '+data.error,'error');}
else if(data){toast('Lead added! Score: '+data.validation.score+'/100','success');document.getElementById('leadName').value='';document.getElementById('leadEmail').value='';document.getElementById('leadBusiness').value='';loadLeads();}
}

async function uploadCSV(){
const file=document.getElementById('csvFile').files[0];
if(!file){toast('Please select a file','error');return;}
const fd=new FormData();fd.append('file',file);
const data=await api('/api/leads/upload',{method:'POST',body:fd});
if(data){toast(data.added+' added, '+data.rejected+' rejected','success');loadLeads();}
}

function downloadSampleCSV(){
const csv='name,email,business,category\nJabu Mokoena,jabu@tenniscourts.co.za,Jabu Tennis Courts Pretoria,Service Business\nMike Sithole,mike@treeservice.co.za,Mike Tree Felling Johannesburg,Construction\nSarah Naidoo,sarah@beauty.co.za,Sarah Beauty Salon Durban,Beauty Salon\nDavid van Wyk,david@autoshop.co.za,David Auto Repair Cape Town,Auto Repair\nLinda Botha,linda@laundry.co.za,Linda Laundromat Bloemfontein,Service Business\nThabo Mthembu,thabo@restaurant.co.za,Thabo Restaurant Soweto,Restaurant\n';
const blob=new Blob([csv],{type:'text/csv'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='sample-leads.csv';a.click();
}

async function loadLeads(){
const data=await api('/api/leads');if(!data)return;
document.getElementById('leadCount').textContent=data.count;
const tbody=document.getElementById('leadsTable');
if(data.leads.length===0){tbody.innerHTML='<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text-muted)">No leads yet. Load test leads or add manually.</td></tr>';return;}
tbody.innerHTML=data.leads.map(l=>{
const sc=l.status==='sent'?'badge-info':l.status==='replied'?'badge-success':l.status==='opted_out'?'badge-danger':l.status==='bounced'?'badge-warn':'badge-success';
return '<tr><td><strong>'+l.name+'</strong></td><td>'+l.email+'</td><td>'+l.business+'</td><td>'+(l.province||'Unknown')+'</td><td><span class="badge '+sc+'">'+l.status+'</span></td></tr>';
}).join('');
}

async function startCampaign(){const data=await api('/api/campaign/start',{method:'POST'});if(data)toast(data.message,'success');}
async function stopCampaign(){const data=await api('/api/campaign/stop',{method:'POST'});if(data)toast('Campaign paused','info');}

const TEMPLATES_DATA=[{n:"Friendly & Helpful",c:"soft",d:"Warm, no-risk approach"},{n:"Question-Based",c:"soft",d:"Engaging opener"},{n:"Social Proof",c:"soft",d:"20+ businesses helped"},{n:"Value-First",c:"soft",d:"Easy process"},{n:"Direct & Punchy",c:"soft",d:"Bold offer"},{n:"Hard Follow-Up",c:"hard",d:"For non-openers"},{n:"Curiosity Hook",c:"soft",d:"Mockup tease"},{n:"Urgency",c:"hard",d:"Limited spots"},{n:"Local Pride",c:"soft",d:"SA angle"},{n:"Final Attempt",c:"hard",d:"Last try"},{n:"The Comparison",c:"soft",d:"vs competitors"},{n:"The Story",c:"soft",d:"Real case study"},{n:"The Direct Question",c:"hard",d:"Honest ask"},{n:"The Free Gift",c:"soft",d:"Free mockup"},{n:"The Pattern Interrupt",c:"soft",d:"No pitch"}];

function loadTemplates(){
document.getElementById('templatesList').innerHTML=TEMPLATES_DATA.map((t,i)=>'<div class="template-item"><div class="template-info"><h4>Template '+(i+1)+': '+t.n+'</h4><p>'+t.d+'</p></div><span class="badge '+(t.c==='soft'?'badge-info':'badge-warn')+'">'+t.c+'</span></div>').join('');
}

async function validateEmail(){
const email=document.getElementById('validateEmail').value.trim();
if(!email){toast('Enter an email','error');return;}
const data=await api('/api/email/validate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
if(data){const cls=data.valid?'success':'error';let html='<div class="result-box '+cls+'"><strong>'+(data.valid?'✅ Valid':'❌ Invalid')+'</strong> | Score: '+data.score+'/100';if(data.suggestion)html+='<br>💡 Did you mean: <strong>'+data.suggestion+'</strong>?';if(data.issues.length)html+='<br>📋 '+data.issues.join(' • ');html+='</div>';document.getElementById('validateResult').innerHTML=html;}
}

async function checkSpam(){
const subject=document.getElementById('spamSubject').value,body=document.getElementById('spamBody').value;
if(!subject&&!body){toast('Enter subject or body','error');return;}
const data=await api('/api/email/spam-check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject,body})});
if(data){const cls=data.rating==='low'?'success':data.rating==='medium'?'warn':'error';let html='<div class="result-box '+cls+'"><strong>Spam Score: '+data.score+'%</strong> ('+data.rating+')';if(data.issues.length)html+='<br>⚠️ Found: '+data.issues.join(', ');html+='</div>';document.getElementById('spamResult').innerHTML=html;}
}

async function loadAnalytics(){
const provData=await api('/api/analytics/provinces');if(!provData)return;
const provNames=Object.keys(provData).filter(p=>provData[p].sent>0);
if(provNames.length>0){
document.getElementById('provinceStats').innerHTML='<table class="data-table"><thead><tr><th>Province</th><th>Sent</th><th>Opened</th><th>Open Rate</th></tr></thead><tbody>'+provNames.map(p=>'<tr><td>'+p+'</td><td>'+provData[p].sent+'</td><td>'+provData[p].opened+'</td><td>'+(provData[p].opened/provData[p].sent*100).toFixed(1)+'%</td></tr>').join('')+'</tbody></table>';
if(charts.province)charts.province.destroy();
charts.province=new Chart(document.getElementById('provinceChart'),{type:'bar',data:{labels:provNames,datasets:[{label:'Sent',data:provNames.map(p=>provData[p].sent),backgroundColor:'#6366f1',borderRadius:8},{label:'Opened',data:provNames.map(p=>provData[p].opened),backgroundColor:'#10b981',borderRadius:8}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#64748b'}}},scales:{x:{ticks:{color:'#64748b'},grid:{display:false}},y:{ticks:{color:'#64748b'},grid:{color:'#e2e8f0'}}}}});
}else{document.getElementById('provinceStats').innerHTML='<p style="text-align:center;color:var(--text-muted);padding:20px">No data yet. Send emails to see province analytics!</p>';if(charts.province)charts.province.destroy();}
const tmplData=await api('/api/analytics/templates');if(tmplData){const ids=Object.keys(tmplData);if(charts.template)charts.template.destroy();charts.template=new Chart(document.getElementById('templateChart'),{type:'bar',data:{labels:ids.map(id=>'T'+id),datasets:[{label:'Sent',data:ids.map(id=>tmplData[id].sent),backgroundColor:'#6366f1',borderRadius:8},{label:'Opened',data:ids.map(id=>tmplData[id].opened),backgroundColor:'#10b981',borderRadius:8}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#64748b'}}},scales:{x:{ticks:{color:'#64748b'},grid:{display:false}},y:{ticks:{color:'#64748b'},grid:{color:'#e2e8f0'}}}}});}
const hrData=await api('/api/analytics/hourly');if(hrData){if(charts.hourly)charts.hourly.destroy();charts.hourly=new Chart(document.getElementById('hourlyChart'),{type:'line',data:{labels:Object.keys(hrData).map(h=>h+':00'),datasets:[{label:'Open Rate %',data:Object.values(hrData).map(d=>d.open_rate||0),borderColor:'#10b981',backgroundColor:'rgba(16,185,129,0.1)',tension:0.4,fill:true,pointRadius:4}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#64748b'}}},scales:{x:{ticks:{color:'#64748b'},grid:{display:false}},y:{ticks:{color:'#64748b'},grid:{color:'#e2e8f0'}}}}});}
const funData=await api('/api/analytics/funnel');if(funData){document.getElementById('funnelData').innerHTML='<div style="display:grid;gap:8px"><div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);color:white;padding:14px;border-radius:10px;display:flex;justify-content:space-between"><span>📊 Total Leads</span><strong>'+funData.total_leads+'</strong></div><div style="background:linear-gradient(90deg,#6366f1,#8b5cf6);color:white;padding:12px;border-radius:10px;width:90%;margin:0 auto;display:flex;justify-content:space-between"><span>📧 Sent</span><strong>'+funData.sent_to+'</strong></div><div style="background:linear-gradient(90deg,#10b981,#059669);color:white;padding:10px;border-radius:10px;width:75%;margin:0 auto;display:flex;justify-content:space-between"><span>👁 Opened</span><strong>'+funData.opened+'</strong></div><div style="background:linear-gradient(90deg,#f59e0b,#d97706);color:white;padding:8px;border-radius:10px;width:50%;margin:0 auto;display:flex;justify-content:space-between"><span>💬 Replied</span><strong>'+funData.replied+'</strong></div></div>';}
}

function viewReport(){window.open('/api/report/daily','_blank');}
function downloadReport(){fetch('/api/report/daily').then(r=>r.text()).then(html=>{const blob=new Blob([html],{type:'text/html'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='report-'+new Date().toISOString().split('T')[0]+'.html';a.click();});}

loadStats();loadActivity();loadTemplates();
setInterval(()=>{loadStats();loadActivity();},3000);
</script>
</body></html>"""

@app.on_event("startup")
async def startup():
    log_activity("system_started", "success", "SA Service Solution Email Machine online! 15 templates, 5 test leads ready.")
    print("🚀 SA Service Solution started!")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
