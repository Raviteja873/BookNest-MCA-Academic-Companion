from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import io
import os

# -----------------------
# App Config
# -----------------------
app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')

# ✅ ABSOLUTE SQLITE PATH (RENDER SAFE)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, "database.db")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------
# Admin / Domain
# -----------------------
ALLOWED_DOMAIN = "@gvpce.ac.in"
ADMIN_EMAIL = "ravitejadasari873@gmail.com"

def valid_domain_mail(email: str) -> bool:
    if not isinstance(email, str):
        return False
    email = email.strip().lower()
    return email.endswith(ALLOWED_DOMAIN) or email == ADMIN_EMAIL

def is_admin() -> bool:
    return (session.get("user_email") or "").lower() == ADMIN_EMAIL

# -----------------------
# Models
# -----------------------
class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(120), unique=True, nullable=False)
    filename = db.Column(db.String(255))
    data = db.Column(db.LargeBinary)
    mimetype = db.Column(db.String(100), default="application/pdf")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def has_pdf(self):
        return self.data is not None and len(self.data) > 0

# -----------------------
# Semester Data
# -----------------------
SEMESTERS = {
    1: [
        "C and Data Structures",
        "Introduction to Python Programming",
        "Computer Organization",
        "Operating Systems",
        "Mathematical Foundations of Computer Applications"
    ],
    2: [
        "Data Base Management Systems",
        "Object Oriented Programming through Java",
        "Design and Analysis of Algorithms",
        "E-commerce",
        "Artificial Intelligence",
        "Organizational Structural Human Resource Management",
        "Fundamentals of Data Science"
    ],
    3: [
        "Web Technologies & Services",
        "Networking and Cloud Computing",
        "Internet of Things",
        "Introduction to Machine Learning",
        "Management Information Systems",
        "Big Data Analytics",
        "Data Warehouse and Data Mining"
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
# DB INIT (RUN ONCE)
# -----------------------
def ensure_subject_rows():
    for sem, subjects in SEMESTERS.items():
        for subj in subjects:
            row = Document.query.filter_by(subject=subj).first()
            if not row:
                db.session.add(Document(semester=sem, subject=subj))
            else:
                if row.semester != sem:
                    row.semester = sem
    db.session.commit()

# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def landing():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not name:
            flash("Please enter your name", "error")
            return redirect(url_for("landing"))

        if not valid_domain_mail(email):
            flash("Enter valid institute email", "error")
            return redirect(url_for("landing"))

        session["user_name"] = name
        session["user_email"] = email

        return redirect(url_for("welcome"))

    return render_template("login.html", allowed_domain=ALLOWED_DOMAIN)

@app.route("/welcome")
def welcome():
    name = session.get("user_name")
    if not name:
        return redirect(url_for("landing"))

    return render_template(
        "welcome.html",
        name=name,
        semesters=sorted(SEMESTERS.keys()),
        is_admin=is_admin()
    )

@app.route("/semester/<int:sem_id>")
def semester_page(sem_id):
    name = session.get("user_name")
    if not name:
        return redirect(url_for("landing"))

    if sem_id not in SEMESTERS:
        abort(404)

    docs = Document.query.filter_by(semester=sem_id)\
                         .order_by(Document.subject.asc())\
                         .all()

    return render_template(
        "subjects.html",
        sem=sem_id,
        docs=docs,
        name=name,
        is_admin=is_admin()
    )

@app.route("/download/<int:doc_id>")
def download(doc_id):
    if not session.get("user_name"):
        return redirect(url_for("landing"))

    doc = Document.query.get_or_404(doc_id)

    if not doc.has_pdf():
        flash("PDF not uploaded yet", "error")
        return redirect(url_for("semester_page", sem_id=doc.semester))

    return send_file(
        io.BytesIO(doc.data),
        mimetype=doc.mimetype,
        as_attachment=True,
        download_name=doc.filename or doc.subject.replace(" ", "_") + ".pdf"
    )

@app.route("/manage", methods=["GET", "POST"])
def manage():
    if not session.get("user_name"):
        return redirect(url_for("landing"))

    if not is_admin():
        flash("Admin only access", "error")
        return redirect(url_for("welcome"))

    if request.method == "POST":
        subject = request.form.get("subject")
        file = request.files.get("file")

        if not subject or not file:
            flash("Select subject & PDF", "error")
            return redirect(url_for("manage"))

        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF allowed", "error")
            return redirect(url_for("manage"))

        doc = Document.query.filter_by(subject=subject).first()
        if not doc:
            flash("Subject not found", "error")
            return redirect(url_for("manage"))

        doc.filename = file.filename
        doc.data = file.read()
        doc.mimetype = "application/pdf"
        db.session.commit()

        flash("PDF uploaded successfully", "success")
        return redirect(url_for("manage"))

    grouped = []
    for sem in sorted(SEMESTERS.keys()):
        docs = Document.query.filter_by(semester=sem).order_by(Document.subject).all()
        grouped.append((sem, docs))

    return render_template("manage.html", grouped=grouped, is_admin=True)

# -----------------------
# App Startup
# -----------------------
with app.app_context():
    db.create_all()
    ensure_subject_rows()

if __name__ == "__main__":
    app.run(debug=True)
