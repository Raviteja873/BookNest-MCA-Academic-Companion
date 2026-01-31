from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------
# Admin / Domain
# -----------------------
ALLOWED_DOMAIN = "@gvpce.ac.in"
ADMIN_EMAIL = "ravitejadasari873@gmail.com"  # remembers admin mail

def valid_domain_mail(email: str) -> bool:
    """Allow institute emails or the one admin Gmail."""
    if not isinstance(email, str):
        return False
    e = email.strip().lower()
    return e.endswith(ALLOWED_DOMAIN) or e == ADMIN_EMAIL

def is_admin() -> bool:
    """Check whether the current session user is the admin."""
    return (session.get("user_email") or "").strip().lower() == ADMIN_EMAIL

# -----------------------
# Models
# -----------------------
class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(120), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    data = db.Column(db.LargeBinary, nullable=True)
    mimetype = db.Column(db.String(100), default='application/pdf')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def has_pdf(self):
        return self.data is not None and len(self.data) > 0

# -----------------------
# Constants (updated)
# -----------------------
SEMESTERS = {
    1: [
        "C and Data Structures",
        "Introduction to Python Programming",
        "Computer Organization",
        "Operating Systems",
        "Mathematical Foundations of Computer Applications",
        
    ],
    2: [
        "Data Base Management Systems",
        "Object Oriented Programming through Java",
        "Design and Analysis of Algorithms",
        "E-commerce",
        "Artificial Intelligence",
        "Organizational Structural Human Resource Management",
        "Fundamentals of Data Science",  # ADDED
    ],
    3: [
        "Web Technologies & Services",
        "Networking and Cloud Computing",
        "Internet of Things",
        "Introduction to Machine Learning",
        "Management Information Systems",
        "Big Data Analytics",
        "Data Warehouse and Data Mining",  # ADDED
    ],
    4: [
        "Cyber Security",
        "Software Engineering",
        "Social Network Analysis",
        "Computer Vision",
        "Applied Natural Language Processing",
        "Block Chain and its Applications"
    ]
}

# -----------------------
# Helpers
# -----------------------
def ensure_subject_rows():
    """Ensure every subject exists in DB once with correct semester mapping."""
    existing_subjects = set()
    for sem, subjects in SEMESTERS.items():
        for subj in subjects:
            row = Document.query.filter_by(subject=subj).first()
            if not row:
                db.session.add(Document(semester=sem, subject=subj))
            else:
                # keep semester in sync if it changed
                if row.semester != sem:
                    row.semester = sem
            existing_subjects.add(subj)
    db.session.commit()
    # Note: we do NOT delete rows for subjects removed from mapping, to keep any PDFs safe.

# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def landing():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not name:
            flash("Please enter your name.", "error")
            return redirect(url_for("landing"))

        if not valid_domain_mail(email):
            flash(f"Enter a valid institute email ending with {ALLOWED_DOMAIN} (or admin email).", "error")
            return redirect(url_for("landing"))

        # Save minimal session
        session["user_name"] = name
        session["user_email"] = email

        return redirect(url_for("welcome"))
    return render_template("login.html", allowed_domain=ALLOWED_DOMAIN)

@app.route("/welcome")
def welcome():
    name = session.get("user_name")
    if not name:
        return redirect(url_for("landing"))
    return render_template("welcome.html", name=name, semesters=sorted(SEMESTERS.keys()), is_admin=is_admin())

@app.route("/semester/<int:sem_id>")
def semester_page(sem_id: int):
    name = session.get("user_name")
    if not name:
        return redirect(url_for("landing"))
    if sem_id not in SEMESTERS:
        abort(404)
    ensure_subject_rows()
    docs = Document.query.filter_by(semester=sem_id).order_by(Document.subject.asc()).all()
    return render_template("subjects.html", sem=sem_id, docs=docs, name=name, is_admin=is_admin())

@app.route("/download/<int:doc_id>")
def download(doc_id: int):
    if not session.get("user_name"):
        return redirect(url_for("landing"))

    doc = Document.query.get_or_404(doc_id)
    if not doc.has_pdf():
        flash("PDF not uploaded for this subject yet.", "error")
        return redirect(url_for("semester_page", sem_id=doc.semester))

    return send_file(
        io.BytesIO(doc.data),
        mimetype=doc.mimetype or "application/pdf",
        as_attachment=True,
        download_name=doc.filename or (doc.subject.replace(" ", "_") + ".pdf")
    )

@app.route("/manage", methods=["GET", "POST"])
def manage():
    """
    Admin-only page to upload/update PDFs for each subject (stored in SQLite BLOB).
    """
    if not session.get("user_name"):
        return redirect(url_for("landing"))

    if not is_admin():
        flash("You are not authorized to access Manage. Admin only.", "error")
        return redirect(url_for("welcome"))

    ensure_subject_rows()

    if request.method == "POST":
        subject = request.form.get("subject")
        file = request.files.get("file")
        if not subject or not file:
            flash("Choose a subject and a PDF file.", "error")
            return redirect(url_for("manage"))
        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "error")
            return redirect(url_for("manage"))

        doc = Document.query.filter_by(subject=subject).first()
        if not doc:
            flash("Subject not found.", "error")
            return redirect(url_for("manage"))

        doc.filename = file.filename
        doc.data = file.read()
        doc.mimetype = "application/pdf"
        db.session.commit()
        flash(f"Uploaded PDF for '{subject}'.", "success")
        return redirect(url_for("manage"))

    # Group docs by semester for tidy UI
    grouped = []
    for sem in sorted(SEMESTERS.keys()):
        docs = Document.query.filter_by(semester=sem).order_by(Document.subject.asc()).all()
        grouped.append((sem, docs))

    return render_template("manage.html", grouped=grouped, is_admin=True)

# CLI helper to init DB once
@app.cli.command("initdb")
def initdb():
    """flask initdb"""
    db.create_all()
    ensure_subject_rows()
    print("Database initialized & subjects ensured.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        ensure_subject_rows()
    app.run(debug=True)
