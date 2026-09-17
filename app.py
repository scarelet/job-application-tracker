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

    applications = conn.execute(
    "SELECT * FROM applications ORDER BY date DESC"
    ).fetchall()

    conn.close()

    total = len(applications)
    interviews = sum(1 for app in applications if app[4] == "Interview")
    offers = sum(1 for app in applications if app[4] == "Offer")
    rejected = sum(1 for app in applications if app[4] == "Rejected")

    return render_template(
    "index.html",
    total=total,
    interviews=interviews,
    offers=offers,
    rejected=rejected,
    applications=applications
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

if __name__ == "__main__":
    init_db()
    app.run(debug=True)