from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret_key_for_session" 

# --- FOLDER CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PROFILE_PIC_FOLDER = os.path.join(BASE_DIR, 'static', 'profile_pics')
CV_FOLDER = os.path.join(BASE_DIR, 'static', 'cv_files')

for folder in [UPLOAD_FOLDER, PROFILE_PIC_FOLDER, CV_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_FOLDER
app.config['CV_FOLDER'] = CV_FOLDER

# --- XAMPP MYSQL CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/dept_results_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
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
    portfolio_link = db.Column(db.String(255))
    cv_file = db.Column(db.String(255))
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
    academic_year = db.Column(db.Integer)
    semester = db.Column(db.Integer)

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))

# --- ROUTES ---

@app.route('/')
def index():
    if 'user_role' in session:
        return redirect(url_for('admin_dashboard' if session['user_role'] == 'admin' else 'student_results'))
    return render_template('login.html')

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
            
        return "❌ Invalid Username or Password!"
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        reg_no = request.form.get('reg_no')
        birthday_input = request.form.get('birthday')
        new_password = request.form.get('new_password')

        # Verify details
        student = Student.query.filter_by(reg_no=reg_no, birthday=birthday_input).first()

        if student:
            student.password = new_password
            db.session.commit()
            return "✅ Password updated! <a href='/login'>Go to Login</a>"
        else:
            return "❌ Details do not match! <a href='/forgot_password'>Try again</a>"

    return render_template('forgot_password.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_role') != 'admin': 
        return redirect(url_for('login'))
    
    recent_logins = Student.query.filter(Student.last_login != None).order_by(Student.last_login.desc()).all()
    
    return render_template('admin_dashboard.html', 
                           scount=Student.query.count(), 
                           subcount=Subject.query.count(),
                           logins=recent_logins)

# --- UPLOAD ROUTES (UNCHANGED) ---
@app.route('/upload_subjects', methods=['POST'])
def upload_subjects():
    file = request.files.get('file')
    if file:
        df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        for _, row in df.iterrows():
            if not Subject.query.get(str(row['subject_code'])):
                new_sub = Subject(subject_code=row['subject_code'], subject_name=row['subject_name'], credits=row['credits'])
                db.session.add(new_sub)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return "❌ Error"

@app.route('/upload_students', methods=['POST'])
def upload_students():
    file = request.files.get('file')
    if file:
        df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        for _, row in df.iterrows():
            if not Student.query.get(str(row['reg_no'])):
                new_stu = Student(reg_no=row['reg_no'], name=row['name'], password=str(row['password']), batch=row['batch'])
                db.session.add(new_stu)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return "❌ Error"

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    sem_info = request.form.get('semester_info')
    if file and sem_info:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        year, sem = sem_info.split('-')
        Result.query.filter_by(semester=int(sem), academic_year=int(year)).delete()
        df = pd.read_excel(filepath) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(filepath)
        for _, row in df.iterrows():
            reg = str(row['reg_no']).strip()
            if Student.query.get(reg):
                for col in df.columns:
                    if col.lower() not in ['reg_no', 'name']:
                        res = Result(reg_no=reg, subject_code=col, grade=str(row[col]), academic_year=int(year), semester=int(sem))
                        db.session.add(res)
        db.session.commit()
        return "✅ Results Uploaded!"
    return "❌ Error"

# --- STUDENT ROUTES ---
@app.route('/student/results')
def student_results():
    if session.get('user_role') != 'student': return redirect(url_for('login'))
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    grade_map = {'A+':4.0,'A':4.0,'A-':3.7,'B+':3.3,'B':3.0,'B-':2.7,'C+':2.3,'C':2.0,'C-':1.7,'D+':1.3,'D':1.0,'D-':0.7,'F':0.0}
    results = db.session.query(Result, Subject).join(Subject, Result.subject_code == Subject.subject_code).filter(Result.reg_no == reg_no).all()
    sem_groups = {}
    for res, sub in results:
        s_val = res.semester
        if s_val not in sem_groups: sem_groups[s_val] = {'list': [], 'pts': 0.0, 'cr': 0.0}
        gp = grade_map.get(str(res.grade).strip().upper(), 0.0)
        cr = float(sub.credits) if sub.credits else 0.0
        sem_groups[s_val]['list'].append((res, sub))
        sem_groups[s_val]['pts'] += (gp * cr)
        sem_groups[s_val]['cr'] += cr
    final_semesters = []
    for s_num in sorted(sem_groups.keys()):
        data = sem_groups[s_num]
        sem_gpa = data['pts'] / data['cr'] if data['cr'] > 0 else 0.0
        final_semesters.append({'num': s_num, 'results': data['list'], 'gpa': sem_gpa})
    return render_template('student_results.html', student=student, semesters=final_semesters)

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    if session.get('user_role') != 'student': return redirect(url_for('login'))
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)

    if request.method == 'POST':
        student.bio = request.form.get('bio')
        student.github = request.form.get('github')
        student.linkedin = request.form.get('linkedin')
        student.portfolio_link = request.form.get('portfolio_link')
        student.email = request.form.get('email')
        student.birthday = request.form.get('birthday')

        clean_reg_no = reg_no.replace('/', '_') 
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"profile_{clean_reg_no}.{ext}"
            file.save(os.path.join(app.config['PROFILE_PIC_FOLDER'], filename))
            student.profile_pic = filename

        cv_file = request.files.get('cv_file')
        if cv_file and cv_file.filename.endswith('.pdf'):
            cv_filename = f"cv_{clean_reg_no}.pdf"
            cv_file.save(os.path.join(app.config['CV_FOLDER'], cv_filename))
            student.cv_file = cv_filename
        db.session.commit()
        return redirect(url_for('student_profile'))
    return render_template('student_profile.html', student=student)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)