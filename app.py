from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "secret_key_for_session" 

# --- DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/dept_results_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- FOLDER CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROFILE_PIC_FOLDER = os.path.join(BASE_DIR, 'static', 'profile_pics')

for folder in [UPLOAD_FOLDER, PROFILE_PIC_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_FOLDER

# --- LOGIN REQUIRED DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session:
            flash("Please login first", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- MODELS ---
class Student(db.Model):
    __tablename__ = 'students'
    reg_no = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    batch = db.Column(db.String(20), nullable=False)
    profile_pic = db.Column(db.String(255), default='default.png')
    bio = db.Column(db.Text)
    github = db.Column(db.String(255))
    linkedin = db.Column(db.String(255))
    email = db.Column(db.String(255))
    birthday = db.Column(db.Date)
    last_login = db.Column(db.DateTime)

class Subject(db.Model):
    __tablename__ = 'subjects'
    subject_code = db.Column(db.String(20), primary_key=True)
    subject_name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)

class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    reg_no = db.Column(db.String(50), db.ForeignKey('students.reg_no'))
    subject_code = db.Column(db.String(20), db.ForeignKey('subjects.subject_code'))
    grade = db.Column(db.String(5))
    semester = db.Column(db.Integer)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))

class Vacancy(db.Model):
    __tablename__ = 'vacancies'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50)) 
    title = db.Column(db.String(100))
    url = db.Column(db.String(500))

# --- ROUTES ---

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')
        
        admin = Admin.query.filter_by(username=user_input, password=pass_input).first()
        if admin:
            session.update({'user_role': 'admin', 'user_id': admin.username})
            return redirect(url_for('admin_dashboard'))
            
        student = Student.query.filter_by(reg_no=user_input, password=pass_input).first()
        if student:
            student.last_login = datetime.now()
            db.session.commit()
            session.update({'user_role': 'student', 'user_id': student.reg_no})
            return redirect(url_for('student_results'))
            
        flash("❌ Invalid Username or Password!", "danger")
    return render_template('login.html')

@app.route('/student/results')
@login_required
def student_results():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    
    # Standard Grade to Points mapping
    grade_map = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0, 'F': 0.0
    }

    # Fetch results joined with subject names
    raw_results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()

    sem_groups = {}
    
    for res, sub in raw_results:
        s_num = res.semester
        if s_num not in sem_groups:
            sem_groups[s_num] = {'list': [], 'pts': 0.0, 'cr': 0.0}
        
        # Clean the grade (remove spaces) and get points
        grade_str = str(res.grade).strip().upper()
        gp = grade_map.get(grade_str, 0.0)
        cr = float(sub.credits) if sub.credits else 0.0
        
        # Add to the semester list
        sem_groups[s_num]['list'].append({'res': res, 'sub': sub})
        sem_groups[s_num]['pts'] += (gp * cr)
        sem_groups[s_num]['cr'] += cr

    # Calculate GPA and prepare final list for HTML
    final_semesters = []
    for s_num in sorted(sem_groups.keys()):
        data = sem_groups[s_num]
        sem_gpa = data['pts'] / data['cr'] if data['cr'] > 0 else 0.0
        final_semesters.append({
            'num': s_num,
            'results': data['list'],  # This matches the HTML loop
            'gpa': sem_gpa
        })

    return render_template('student_results.html', student=student, semesters=final_semesters)


# ADDED THIS TO FIX YOUR BuildError
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        reg_no = request.form.get('reg_no')
        # Logic for resetting password would go here
        flash("Feature under development or check admin.", "info")
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/industrial')
def industrial():
    selected_cat = request.args.get('cat', 'all')
    vacancies = Vacancy.query.all() if selected_cat == 'all' else Vacancy.query.filter_by(category=selected_cat).all()
    return render_template('industrial.html', vacancies=vacancies, active_cat=selected_cat)

# --- ADMIN ROUTES ---
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('user_role') != 'admin': return redirect(url_for('login'))
    logins = Student.query.filter(Student.last_login != None).order_by(Student.last_login.desc()).all()
    return render_template('admin_dashboard.html', scount=Student.query.count(), subcount=Subject.query.count(), logins=logins)

@app.route('/admin/add-vacancy', methods=['POST'])
@login_required
def add_vacancy():
    cat = request.form.get('category')
    title = request.form.get('title')
    link = request.form.get('link')
    if title and link:
        new_v = Vacancy(category=cat, title=title, url=link)
        db.session.add(new_v)
        db.session.commit()
        flash("✅ Vacancy Posted!", "success")
    return redirect(url_for('admin_dashboard'))

# --- STUDENT ROUTES ---


@app.route('/student/profile')
@login_required
def student_profile():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    return render_template('student_profile.html', student=student)

# --- THE CV BUILDER SYSTEM ---
@app.route('/cv-builder')
@login_required
def cv_builder():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    return render_template('cv_form.html', student=student)

@app.route('/cv-preview')
@login_required
def cv_preview():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    results = db.session.query(Result, Subject).join(Subject, Result.subject_code == Subject.subject_code).filter(Result.reg_no == reg_no).all()
    return render_template('cv_preview.html', student=student, results=results)

# --- DIGITAL PORTFOLIO ---
# The "path:" part tells Flask to accept slashes (/) in the ID
@app.route('/portfolio/<path:reg_no>')
def public_portfolio(reg_no):
    # Fetch student data based on the ID in the URL
    student = Student.query.get_or_404(reg_no)
    
    # Fetch their results for the portfolio
    results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()
    
    return render_template('portfolio.html', student=student, results=results)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)