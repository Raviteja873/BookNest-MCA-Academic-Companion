# BookNest – MCA Academic Companion

BookNest is a Flask-based academic resource management system designed
for MCA students to access semester-wise subject materials (PDFs)
through secure, domain-restricted authentication.

---

## 🎓 Institution
Developed for MCA students of  
**Gayatri Vidya Parishad College of Engineering (Autonomous)**.

---

## 🔐 Authentication & Access Control

Access to this application is restricted to users with
institute-provided email addresses ending with:

@gvpce.ac.in

This ensures secure and controlled access to academic resources,
similar to real-world university and enterprise internal portals.

> Note: The allowed email domain can be modified in the source code
> to adapt this application for other institutions.

---

## 🚀 Features

- Domain-restricted login
- Semester-wise subject listing
- PDF upload & management (Admin only)
- PDF download for students
- Secure session handling
- Clean and responsive UI
- SQLite database backend

---

## 🛠️ Tech Stack

- Backend: Flask (Python)
- Frontend: HTML, CSS
- Database: SQLite (Flask-SQLAlchemy)
- Authentication: Session-based

---

## ⚙️ Installation & Setup

```bash
git clone https://github.com/your-username/booknest-mca-academic-companion.git
cd booknest-mca-academic-companion
pip install -r requirements.txt
flask initdb
python app.py
