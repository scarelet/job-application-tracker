from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("database.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            url TEXT
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    conn = sqlite3.connect("database.db")

    all_applications = conn.execute(
        "SELECT * FROM applications ORDER BY date DESC"
    ).fetchall()

    selected_status = request.args.get("status", "All")

    if selected_status == "All":
        applications = all_applications
    else:
        applications = conn.execute(
            "SELECT * FROM applications WHERE status = ? ORDER BY date DESC",
            (selected_status,)
        ).fetchall()

    conn.close()

    total = len(all_applications)
    interviews = sum(1 for app in all_applications if app[4] == "Interview")
    offers = sum(1 for app in all_applications if app[4] == "Offer")
    rejected = sum(1 for app in all_applications if app[4] == "Rejected")

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

        conn = sqlite3.connect("database.db")

        conn.execute(
            """
            INSERT INTO applications (company, job_title, date, status, url)
            VALUES (?, ?, ?, ?, ?)
            """,
            (company, job_title, date, status, url)
        )

        conn.commit()
        conn.close()

    return render_template("add_application.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_application(id):
    conn = sqlite3.connect("database.db")

    if request.method == "POST":
        company = request.form["company"]
        job_title = request.form["job_title"]
        date = request.form["date"]
        status = request.form["status"]
        url = request.form["url"]

        conn.execute(
            """
            UPDATE applications
            SET company = ?, job_title = ?, date = ?, status = ?, url = ?
            WHERE id = ?
            """,
            (company, job_title, date, status, url, id)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    application = conn.execute(
        "SELECT * FROM applications WHERE id = ?",
        (id,)
    ).fetchone()

    conn.close()

    return render_template(
        "edit_application.html",
        application=application
    )


@app.route("/delete/<int:id>")
def delete_application(id):
    conn = sqlite3.connect("database.db")

    conn.execute(
        "DELETE FROM applications WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/api/applications", methods=["GET"])
def get_applications():
    conn = sqlite3.connect("database.db")

    applications = conn.execute(
        "SELECT * FROM applications ORDER BY date DESC"
    ).fetchall()

    conn.close()

    results = []

    for application in applications:
        results.append({
            "id": application[0],
            "company": application[1],
            "job_title": application[2],
            "date": application[3],
            "status": application[4],
            "url": application[5]
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

    conn = sqlite3.connect("database.db")

    cursor = conn.execute(
        """
        INSERT INTO applications (company, job_title, date, status, url)
        VALUES (?, ?, ?, ?, ?)
        """,
        (company, job_title, date, status, url)
    )

    conn.commit()

    application_id = cursor.lastrowid

    conn.close()

    return {
        "message": "Application created successfully",
        "id": application_id
    }, 201

@app.route("/api/applications/<int:id>", methods=["PUT"])
def update_application(id):
    data = request.get_json()

    company = data["company"]
    job_title = data["job_title"]
    date = data["date"]
    status = data["status"]
    url = data.get("url", "")

    conn = sqlite3.connect("database.db")

    conn.execute(
        """
        UPDATE applications
        SET company = ?, job_title = ?, date = ?, status = ?, url = ?
        WHERE id = ?
        """,
        (company, job_title, date, status, url, id)
    )

    conn.commit()
    conn.close()

    return {
        "message": "Application updated successfully"
    }

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

