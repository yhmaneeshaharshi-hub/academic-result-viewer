from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
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
    portfolio_link = db.Column(db.String(500))
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

class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now) # වෙලාව සටහන් කර ගැනීමට

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
            # Fixed the 'namef' bug here
            session.update({'user_role': 'student', 'user_id': student.reg_no, 'user_name': student.name})
            return redirect(url_for('student_results'))
            
        flash("❌ Invalid Username or Password!", "danger")
    return render_template('login.html')

@app.route('/student/results')
@login_required
def student_results():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    
    grade_map = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0, 'F': 0.0
    }

    raw_results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()

    sem_groups = {}
    for res, sub in raw_results:
        s_num = res.semester
        if s_num not in sem_groups:
            sem_groups[s_num] = {'list': [], 'pts': 0.0, 'cr': 0.0}
        
        grade_str = str(res.grade).strip().upper()
        gp = grade_map.get(grade_str, 0.0)
        cr = float(sub.credits) if sub.credits else 0.0
        
        sem_groups[s_num]['list'].append({'res': res, 'sub': sub})
        sem_groups[s_num]['pts'] += (gp * cr)
        sem_groups[s_num]['cr'] += cr

    final_semesters = []
    for s_num in sorted(sem_groups.keys()):
        data = sem_groups[s_num]
        sem_gpa = data['pts'] / data['cr'] if data['cr'] > 0 else 0.0
        final_semesters.append({
            'num': s_num,
            'results': data['list'],
            'gpa': round(sem_gpa, 2)
        })

    return render_template('student_results.html', student=student, semesters=final_semesters)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
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

# --- FILE UPLOAD ROUTES (Corrected and Added) ---

@app.route('/upload_students', methods=['POST'])
@login_required
def upload_students():
    if session.get('user_role') != 'admin': return redirect(url_for('login'))
    file = request.files.get('file')
    if not file or file.filename == '':
        flash("❌ No file selected!", "danger")
        return redirect(url_for('admin_dashboard'))

    try:
        df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        count = 0
        for _, row in df.iterrows():
            reg_val = str(row['reg_no']).strip()
            if not Student.query.get(reg_val):
                new_s = Student(reg_no=reg_val, name=row['name'], password=str(row['password']), batch=str(row['batch']))
                db.session.add(new_s)
                count += 1
        db.session.commit()
        flash(f"✅ Successfully imported {count} students!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/upload_subjects', methods=['POST'])
@login_required
def upload_subjects():
    if session.get('user_role') != 'admin': return redirect(url_for('login'))
    file = request.files.get('file')
    if not file: return redirect(url_for('admin_dashboard'))
    try:
        df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        count = 0
        for _, row in df.iterrows():
            code = str(row['subject_code']).strip()
            if not Subject.query.get(code):
                new_sub = Subject(subject_code=code, subject_name=row['subject_name'], credits=int(row['credits']))
                db.session.add(new_sub)
                count += 1
        db.session.commit()
        flash(f"✅ Successfully imported {count} subjects!", "success")
    except Exception as e:
        flash(f"❌ Error: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_results():
    if session.get('user_role') != 'admin': return redirect(url_for('login'))
    file = request.files.get('file')
    sem_info = request.form.get('semester_info')
    if file and sem_info:
        try:
            sem_num = int(sem_info.split('-')[1])
            df = pd.read_excel(file) if file.filename.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
            for _, row in df.iterrows():
                new_res = Result(reg_no=str(row['reg_no']).strip(), subject_code=str(row['subject_code']).strip(), 
                                 grade=str(row['grade']).strip().upper(), semester=sem_num)
                db.session.add(new_res)
            db.session.commit()
            flash(f"✅ Results for Semester {sem_num} Uploaded!", "success")
        except Exception as e:
            flash(f"❌ Error: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

# --- PROFILE & CV ROUTES ---

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    if request.method == 'POST':
        student.email = request.form.get('email')
        student.github = request.form.get('github')
        student.linkedin = request.form.get('linkedin')
        student.portfolio_link = request.form.get('portfolio_link')
        student.bio = request.form.get('bio')
        bday = request.form.get('birthday')
        if bday:
            try: student.birthday = datetime.strptime(bday, '%Y-%m-%d').date()
            except: pass

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename = secure_filename(f"{reg_no}_profile.png")
                file.save(os.path.join(app.config['PROFILE_PIC_FOLDER'], filename))
                student.profile_pic = filename

        if 'cv_file' in request.files:
            cv = request.files['cv_file']
            if cv and cv.filename != '':
                cv_filename = secure_filename(f"{reg_no}_cv.pdf")
                cv_path = os.path.join(app.static_folder, 'cv_files')
                if not os.path.exists(cv_path): os.makedirs(cv_path)
                cv.save(os.path.join(cv_path, cv_filename))
                student.cv_file = cv_filename

        db.session.commit()
       
        return redirect(url_for('student_profile'))
    return render_template('student_profile.html', student=student)

@app.route('/cv-builder')
@login_required
def cv_builder():
    student = Student.query.get(session.get('user_id'))
    return render_template('cv_form.html', student=student)

@app.route('/cv-preview', methods=['GET', 'POST'])
@login_required
def cv_preview():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    
    # Form එකෙන් එවන දත්ත ලබා ගැනීම
    if request.method == 'POST':
        cv_data = {
            'name': request.form.get('name'),
            'bio': request.form.get('bio'),
            'experience': request.form.get('experience'),
            'skills': request.form.get('skills', '').split(',') 
        }
    else:
        # කෙලින්ම URL එකෙන් ආවොත් පෙන්වන Default දත්ත
        cv_data = {
            'name': student.name,
            'bio': student.bio or "No summary provided.",
            'experience': "No details provided.",
            'skills': []
        }

    # Results සහ Subject join කර දත්ත ලබා ගැනීම
    # මෙන්න මෙතන තිබුණු Indentation සහ brackets mismatch එක දැන් නිවැරදියි
    results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()

    return render_template('cv_preview.html', student=student, results=results, data=cv_data)


    
    # 1. ශිෂ්‍යයාට යෝජනා එවීමට ඇති Route එක
# 1. ශිෂ්‍යයා Landing Page එකේ ඉදන් එවද්දී වැඩ කරන Route එක
@app.route('/submit-suggestion', methods=['GET', 'POST'])
def submit_suggestion():
    if request.method == 'POST':
        msg = request.form.get('suggestion')
        if msg:
            new_sug = Suggestion(content=msg)
            db.session.add(new_sug)
            db.session.commit()
            flash("✅ Your suggestion was submitted anonymously!", "success")
    return redirect(url_for('landing')) # මෙතන 'landing' යනු ඔබගේ landing page function එකේ නමයි

# 2. Admin ට මේවා පෙන්වන Route එක (BuildError එක එන්නේ මේක නැති වුණාමයි)
@app.route('/admin/view-suggestions')
@login_required
def admin_suggestions():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    # සියලුම suggestions දත්ත ගබඩාවෙන් ලබා ගැනීම
    all_suggestions = Suggestion.query.order_by(Suggestion.timestamp.desc()).all()
    return render_template('admin_suggestions.html', suggestions=all_suggestions)

@app.route('/portfolio/<reg_no>')
def public_portfolio(reg_no):
    # Registration number එකෙන් ශිෂ්‍යයාගේ විස්තර සොයාගන්න
    student = Student.query.get_or_404(reg_no)
    
    # ප්‍රතිඵල සහ විෂයන් join කර ලබාගන්න (පෝර්ට්ෆෝලියෝ එකේ පෙන්වීමට අවශ්‍ය නම්)
    results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()
    
    return render_template('public_portfolio.html', student=student, results=results)
# 2. Admin ට සියලුම යෝජනා බැලීමට ඇති Route එක

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)