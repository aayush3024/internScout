import os, json, re, csv, io
from datetime import datetime
from urllib.parse import urlparse
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-this-before-deploying")

TINYFISH_KEY = os.getenv("TINYFISH_API_KEY", "").strip()
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
AGENT_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"

def headers():
    return {"X-API-Key": TINYFISH_KEY}

def normalize_results(payload):
    if isinstance(payload, list):
        raw = payload
    elif isinstance(payload, dict):
        raw = payload.get("results") or payload.get("data") or payload.get("organic_results") or []
    else:
        raw = []
    output = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or ""
        output.append({
            "title": item.get("title") or item.get("name") or "Internship opportunity",
            "url": url,
            "snippet": item.get("snippet") or item.get("description") or item.get("text") or "",
            "site": item.get("site_name") or (urlparse(url).netloc.replace("www.", "") if url else "Web result"),
            "position": item.get("position"),
            "source": "TinyFish Search"
        })
    return output

def tinyfish_search(query, location="India"):
    if not TINYFISH_KEY:
        return {"configured": False, "results": [], "message": "Add TINYFISH_API_KEY to .env to enable live search."}
    try:
        # TinyFish Search expects a country code for its location parameter.
        country = "IN"
        if isinstance(location, str) and len(location.strip()) == 2 and location.strip().isalpha():
            country = location.strip().upper()
        r = requests.get(SEARCH_URL, params={"query": query, "location": country, "language": "en"},
                         headers=headers(), timeout=25)
        r.raise_for_status()
        payload = r.json()
        return {"configured": True, "results": normalize_results(payload), "raw": payload}
    except requests.RequestException as exc:
        return {"configured": True, "results": [], "error": str(exc)[:260]}

def tinyfish_fetch(urls):
    if not TINYFISH_KEY:
        return {"configured": False, "documents": [], "message": "TinyFish key not configured."}
    urls = [u for u in urls if isinstance(u, str) and u.startswith(("http://", "https://"))][:10]
    if not urls:
        return {"configured": True, "documents": [], "message": "No valid source URLs to fetch."}
    try:
        r = requests.post(FETCH_URL, headers={**headers(), "Content-Type": "application/json"},
                          json={"urls": urls, "format": "markdown", "links": True}, timeout=100)
        r.raise_for_status()
        return {"configured": True, "documents": r.json()}
    except requests.RequestException as exc:
        return {"configured": True, "documents": [], "error": str(exc)[:260]}

def tinyfish_agent(url, goal):
    if not TINYFISH_KEY:
        return {"configured": False, "message": "Add TINYFISH_API_KEY to .env to enable the TinyFish Web Agent."}
    try:
        with requests.post(AGENT_URL, headers={**headers(), "Content-Type": "application/json",
                                               "Accept": "text/event-stream"},
                           json={"url": url, "goal": goal, "browser_profile": "lite"},
                           stream=True, timeout=(20, 180)) as r:
            r.raise_for_status()
            events = []
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                line = line.strip()
                if line.startswith("data:"):
                    try:
                        event = json.loads(line[5:].strip())
                        events.append(event)
                        if str(event.get("type", "")).upper() == "COMPLETE":
                            break
                    except json.JSONDecodeError:
                        events.append({"message": line[5:].strip()})
            complete = next((e for e in reversed(events) if str(e.get("type", "")).upper() == "COMPLETE"), None)
            return {"configured": True, "events": events[-25:], "result": complete or (events[-1] if events else {})}
    except requests.RequestException as exc:
        return {"configured": True, "error": str(exc)[:300]}

def tokenize(text):
    return set(re.findall(r"[a-zA-Z+#.]{2,}", (text or "").lower()))

def match_score(profile, result):
    """Explainable relevance score: skills overlap, role intent and location preference."""
    skills = tokenize(profile.get("skills", ""))
    blob = " ".join([result.get("title", ""), result.get("snippet", ""), result.get("site", "")])
    words = tokenize(blob)
    if not skills:
        skill_score = 0
    else:
        skill_score = round(65 * len(skills & words) / max(1, len(skills)))
    title = result.get("title", "").lower()
    role_score = 20 if any(x in title for x in ["intern", "internship", "trainee", "fellow"]) else 5
    loc = (profile.get("location") or "").strip().lower()
    loc_score = 15 if loc and loc in blob.lower() else (8 if loc and loc in ("india", "remote") else 0)
    return min(99, skill_score + role_score + loc_score)

def build_queries(profile):
    role = profile.get("role") or "software"
    skills = profile.get("skills") or ""
    location = profile.get("location") or "India"
    level = profile.get("level") or "student"
    return [
        f"{role} internship {skills} {location} {level} 2026 apply",
        f"paid {role} internships for students {location} 2026",
        f"remote {role} internship {skills} students apply 2026",
        f"{role} internship fresher college students {location} application deadline"
    ]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({"ok": True, "tinyfish_configured": bool(TINYFISH_KEY)})

@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json(force=True)
    profile = {
        "name": data.get("name", ""), "role": data.get("role", "software"),
        "skills": data.get("skills", ""), "location": data.get("location", "India"),
        "level": data.get("level", "student"), "work_mode": data.get("work_mode", "Any")
    }
    if not TINYFISH_KEY:
        return jsonify({"error": "TinyFish API key is missing. Add it to your .env file, then restart Flask."}), 400
    queries = build_queries(profile)
    all_results, errors = [], []
    for query in queries:
        found = tinyfish_search(query, profile["location"] or "India")
        if found.get("error"):
            errors.append(found["error"])
        all_results.extend(found.get("results", []))
    seen, unique = set(), []
    for item in all_results:
        url = item.get("url")
        key = url or item.get("title", "").lower()
        if key and key not in seen:
            seen.add(key)
            item["match_score"] = match_score(profile, item)
            item["match_reason"] = "Skill overlap and role relevance score; verify requirements on the source page."
            unique.append(item)
    unique.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify({"results": unique[:40], "queries": queries, "count": len(unique),
                    "errors": errors, "searched_at": datetime.now().isoformat(),
                    "profile": profile})

@app.route("/api/research", methods=["POST"])
def research():
    data = request.get_json(force=True)
    url = data.get("url", "")
    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "A valid source URL is required."}), 400
    result = tinyfish_fetch([url])
    return jsonify(result)

@app.route("/api/agent", methods=["POST"])
def agent():
    data = request.get_json(force=True)
    url = data.get("url", "")
    if not url.startswith(("https://", "http://")):
        return jsonify({"error": "A valid source URL is required."}), 400
    goal = ("Visit this internship or career page and extract only information visibly available on the page. "
            "Return structured JSON with: organization, role_title, location, work_mode, paid_or_unpaid, "
            "stipend, eligibility, required_skills, responsibilities, deadline, duration, application_steps, "
            "application_url, source_url. Use null for unknown values. Do not infer or invent details. "
            "Do not submit an application, create an account, or send personal information.")
    return jsonify(tinyfish_agent(url, goal))

@app.route("/api/export", methods=["POST"])
def export_csv():
    data = request.get_json(force=True)
    results = data.get("results", [])
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["title", "site", "match_score", "snippet", "url"])
    writer.writeheader()
    for item in results:
        writer.writerow({k: item.get(k, "") for k in writer.fieldnames})
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=internscout-shortlist.csv"})

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
