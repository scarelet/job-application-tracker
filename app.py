import os
import json
import requests
import psycopg2
from flask import Flask, render_template, request, redirect, jsonify
from dotenv import load_dotenv
 
load_dotenv()
 
app = Flask(__name__)
 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
 
DATABASE_URL = os.environ.get("DATABASE_URL")
 
 
def get_db_connection():
    """
    Connects to Postgres. Render provides DATABASE_URL automatically once you
    attach a Postgres database to your service. Locally, docker-compose sets
    it for you (see docker-compose.yml).
    """
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Set it in your .env locally, "
            "or attach a Postgres database on Render."
        )
 
    sslmode = "require" if "render.com" in DATABASE_URL else "prefer"
 
    return psycopg2.connect(DATABASE_URL, sslmode=sslmode)
 
 
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            url TEXT
        )
    """)
 
    conn.commit()
    cur.close()
    conn.close()
 
 
def parse_job_with_gemini(description):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set on the server.")
 
    prompt = f"""You are helping a job applicant fill out a tracker and prep for an application.
Read the job posting below and respond with ONLY valid JSON (no markdown fences, no commentary),
matching exactly this shape:
 
{{
  "company": "string, the hiring company's name, or empty string if unclear",
  "job_title": "string, the job title, or empty string if unclear",
  "key_requirements": ["3-6 short strings, the most important skills/requirements"],
  "resume_talking_points": ["3-5 short strings, each a suggested angle or keyword the
      applicant should emphasize on their resume/cover letter for THIS posting -
      phrased as suggestions, not fabricated claims about the applicant's experience"]
}}
 
Job posting:
\"\"\"{description}\"\"\"
"""
 
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "response_mime_type": "application/json"
        }
    }
 
    response = requests.post(
        GEMINI_URL, params={"key": GEMINI_API_KEY}, json=body, timeout=20
    )
 
    if response.status_code != 200:
        raise ValueError(f"Gemini API error ({response.status_code}): {response.text[:300]}")
 
    data = response.json()
 
    try:
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise ValueError("Unexpected response shape from Gemini.")
 
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
 
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError("Could not parse JSON from Gemini's response.")
 
    return {
        "company": parsed.get("company", ""),
        "job_title": parsed.get("job_title", ""),
        "key_requirements": parsed.get("key_requirements", []),
        "resume_talking_points": parsed.get("resume_talking_points", [])
    }
 
 
@app.route("/")
def home():
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM applications ORDER BY date DESC")
    all_applications = cur.fetchall()
 
    selected_status = request.args.get("status", "All")
 
    if selected_status == "All":
        applications = all_applications
    else:
        cur.execute(
            "SELECT * FROM applications WHERE status = %s ORDER BY date DESC",
            (selected_status,)
        )
        applications = cur.fetchall()
 
    cur.close()
    conn.close()
 
    total = len(all_applications)
    interviews = sum(1 for a in all_applications if a[4] == "Interview")
    offers = sum(1 for a in all_applications if a[4] == "Offer")
    rejected = sum(1 for a in all_applications if a[4] == "Rejected")
 
    return render_template(
        "index.html",
        total=total,
        interviews=interviews,
        offers=offers,
        rejected=rejected,
        applications=applications,
        selected_status=selected_status
    )
 
 
@app.route("/add", methods=["GET", "POST"])
def add_application():
    if request.method == "POST":
        company = request.form["company"]
        job_title = request.form["job_title"]
        date = request.form["date"]
        status = request.form["status"]
        url = request.form["url"]
 
        conn = get_db_connection()
        cur = conn.cursor()
 
        cur.execute(
            """
            INSERT INTO applications (company, job_title, date, status, url)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (company, job_title, date, status, url)
        )
 
        conn.commit()
        cur.close()
        conn.close()
 
        return redirect("/")
 
    return render_template("add_application.html")
 
 
@app.route("/api/parse-job", methods=["POST"])
def parse_job():
    data = request.get_json(silent=True) or {}
    description = (data.get("description") or "").strip()
 
    if not description:
        return jsonify({"error": "Please paste a job description first."}), 400
 
    try:
        result = parse_job_with_gemini(description)
    except ValueError as e:
        return jsonify({"error": str(e)}), 502
 
    return jsonify(result), 200
 
 
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_application(id):
    conn = get_db_connection()
    cur = conn.cursor()
 
    if request.method == "POST":
        company = request.form.get("company", "").strip()
        job_title = request.form.get("job_title", "").strip()
        date = request.form.get("date", "").strip()
        status = request.form.get("status", "").strip()
        url = request.form.get("url", "").strip()
 
        if not company or not job_title or not date:
            cur.close()
            conn.close()
            return render_template(
                "edit_application.html",
                error="Company, job title, and date are required.",
                application=(id, company, job_title, date, status, url)
            ), 400
 
        cur.execute(
            """
            UPDATE applications
            SET company = %s, job_title = %s, date = %s, status = %s, url = %s
            WHERE id = %s
            """,
            (company, job_title, date, status, url, id)
        )
 
        conn.commit()
        cur.close()
        conn.close()
 
        return redirect("/")
 
    cur.execute("SELECT * FROM applications WHERE id = %s", (id,))
    application = cur.fetchone()
 
    cur.close()
    conn.close()
 
    return render_template("edit_application.html", application=application)
 
 
@app.route("/delete/<int:id>")
def delete_application(id):
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute("DELETE FROM applications WHERE id = %s", (id,))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return redirect("/")
 
 
@app.route("/api/applications", methods=["GET"])
def get_applications():
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM applications ORDER BY date DESC")
    applications = cur.fetchall()
 
    cur.close()
    conn.close()
 
    results = []
    for a in applications:
        results.append({
            "id": a[0], "company": a[1], "job_title": a[2],
            "date": a[3], "status": a[4], "url": a[5]
        })
 
    return results
 
 
@app.route("/api/applications", methods=["POST"])
def create_application():
    data = request.get_json()
 
    company = data["company"]
    job_title = data["job_title"]
    date = data["date"]
    status = data["status"]
    url = data.get("url", "")
 
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute(
        """
        INSERT INTO applications (company, job_title, date, status, url)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
        """,
        (company, job_title, date, status, url)
    )
 
    application_id = cur.fetchone()[0]
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"message": "Application created successfully", "id": application_id}, 201
 
 
@app.route("/api/applications/<int:id>", methods=["PUT"])
def update_application(id):
    data = request.get_json()
 
    company = data["company"]
    job_title = data["job_title"]
    date = data["date"]
    status = data["status"]
    url = data.get("url", "")
 
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute(
        """
        UPDATE applications
        SET company = %s, job_title = %s, date = %s, status = %s, url = %s
        WHERE id = %s
        """,
        (company, job_title, date, status, url, id)
    )
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"message": "Application updated successfully"}
 
 
@app.route("/api/applications/<int:id>", methods=["DELETE"])
def delete_application_api(id):
    conn = get_db_connection()
    cur = conn.cursor()
 
    cur.execute("DELETE FROM applications WHERE id = %s", (id,))
 
    conn.commit()
    cur.close()
    conn.close()
 
    return {"message": "Application deleted successfully"}
 
 
init_db()
 
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
 
