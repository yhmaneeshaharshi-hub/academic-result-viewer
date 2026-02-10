from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy #bridge between flask and mysql
from werkzeug.utils import secure_filename #to secure the file name when uploading profile pics and cvs
import pandas as pd#to read excel and csv files for bulk uploads of students, subjects, and results
import os#to handle file paths and directories for uploads and profile pictures
from datetime import datetime#to handle date and time for student birthdays and last login tracking
from functools import wraps#to create a login_required decorator that restricts access to certain routes based on user authentication

app = Flask(__name__) #create the Flask application instance
app.secret_key = "secret_key_for_session" # In production, use a secure and random key, and keep it secret!

# --- DATABASE CONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/dept_results_db'# Update with your MySQL credentials and database name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Disable the event system to save resources, as we won't be using it
db = SQLAlchemy(app) # Initialize the SQLAlchemy extension with our Flask app, allowing us to define models and interact with the database using an ORM (Object-Relational Mapping) approach. This means we can work with Python classes and objects instead of writing raw SQL queries, making database operations more intuitive and integrated with our application logic.

# --- FOLDER CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))# Get the absolute path of the directory where this script (app.py) is located. This is used as a base for constructing paths to the uploads and profile pictures folders, ensuring that file operations work correctly regardless of where the app is run from.
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')# Define the path for the uploads folder, which will be used to store files uploaded by the admin (like student lists, subject lists, and results). The os.path.join function is used to create a platform-independent path by combining the base directory with the 'uploads' folder name.
PROFILE_PIC_FOLDER = os.path.join(BASE_DIR, 'static', 'profile_pics')# Define the path for the profile pictures folder, which will be used to store student profile images. This folder is located within the 'static' directory, which is a common convention in Flask applications for serving static files like images, CSS, and JavaScript. Again, os.path.join is used to ensure the path is constructed correctly across different operating systems.

for folder in [UPLOAD_FOLDER, PROFILE_PIC_FOLDER]:# Check if the specified folders (uploads and profile_pics) exist, and if not, create them. This ensures that when the application tries to save files to these directories, it won't encounter errors due to missing folders. The os.path.exists function checks for the existence of the folder, and os.makedirs creates the folder if it doesn't exist.
    if not os.path.exists(folder):# If the folder does not exist, create it using os.makedirs. This is important for the application's functionality, as it relies on these directories to store uploaded files and profile pictures. By ensuring these folders are created at startup, we prevent potential issues when users try to upload files or update their profiles.
        os.makedirs(folder)# Create the folder if it doesn't exist, ensuring that the application has the necessary directory structure to function properly. This is a common practice in web applications to handle file storage and organization, especially when dealing with user-generated content like uploads and profile images.

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER# Set the UPLOAD_FOLDER configuration for the Flask app, which will be used as the destination for saving files uploaded by the admin (such as student lists, subject lists, and results). This configuration allows us to easily reference the upload directory throughout our application when handling file uploads.
app.config['PROFILE_PIC_FOLDER'] = PROFILE_PIC_FOLDER# Set the PROFILE_PIC_FOLDER configuration for the Flask app, which will be used as the destination for saving student profile pictures. This allows us to easily reference the profile pictures directory when students upload their profile images, ensuring that they are stored in a consistent location and can be accessed when needed (e.g., when displaying student profiles).

# --- LOGIN REQUIRED DECORATOR ---
# decorator function to add extran functionalities to login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 'user_role' session එකේ නැත්නම් කෙලින්ම login පිටුවට යවනවා
        if 'user_role' not in session:
            flash("Please login first", "warning")
            return redirect(url_for('login',next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Browser එක පරණ පිටු මතක තබා ගැනීම (Cache) වැළැක්වීමට
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ------------- MODELS -------------
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
    timestamp = db.Column(db.DateTime, default=datetime.now) # tyo store time

# --- ROUTES ---

# <<<<<<<landing page>>>>>>>>
@app.route('/') 
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')
        
        # 1. Admin Login
        admin = Admin.query.filter_by(username=user_input, password=pass_input).first()
        if admin:
            session.update({'user_role': 'admin', 'user_id': admin.username})
            return redirect(url_for('admin_dashboard'))
            
        # 2. Student Login
        student = Student.query.filter_by(reg_no=user_input, password=pass_input).first()
        if student:
            # ... (උඹේ පරණ session update කෝඩ් එක) ...
            session.update({'user_role': 'student', 'user_id': student.reg_no, 'user_name': student.name})
            
            # --- අලුත් කෑල්ල මෙන්න ---
            if session.get('redirect_to_cv'):
                session.pop('redirect_to_cv', None) # දාපු ලකුණ අයින් කරනවා
                return redirect(url_for('cv_builder')) # කෙලින්ම CV Builder එකට යවනවා
            
            return redirect(url_for('student_results'))
            
        flash("❌ Invalid Username or Password!", "danger")
    return render_template('login.html')

#<<<<<<<<student Results>>>>>>>
@app.route('/student/results') #creating url to show the student results
@login_required
def student_results():
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    
    grade_map = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0, 'F': 0.0,
        'ab':0.0,'E':0.0
    }

    raw_results = db.session.query(Result, Subject).join(
        Subject, Result.subject_code == Subject.subject_code
    ).filter(Result.reg_no == reg_no).all()# Query the database to retrieve the results for the logged-in student. This query joins the Result and Subject tables based on the subject_code, allowing us to access both the grade and the subject details (like credits) in one query. The filter ensures that we only get results for the current student based on their registration number (reg_no).

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

# --- FUNCTIONAL FORGOT PASSWORD ROUTE USING BIRTHDAY ---
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Handle the form submission when the user clicks the reset button
    if request.method == 'POST':
        # Retrieve data from the HTML form fields
        reg_input = request.form.get('reg_no')
        bday_input = request.form.get('birthday')  # This is the date string from the user
        new_pass = request.form.get('new_password')

        # Query the 'students' table to find a record with the matching registration number
        student = Student.query.filter_by(reg_no=reg_input).first()

        # Check if a student was found and if their birthday matches the user input
        # Note: convert student.birthday to a string to ensure a proper comparison with the input
        if student and student.birthday and str(student.birthday) == bday_input:
            # Identity is confirmed: update the student's password in the database
            student.password = new_pass
            db.session.commit()
            
            # Send a success message and send the user back to the login page
            flash("✅ Password reset successfully! You can now login.", "success")
            return redirect(url_for('login'))
        else:
            # Identity verification failed (wrong reg_no or wrong birthday)
            flash("❌ Verification failed. Please check your Registration Number or Birthday.", "danger")
            
            # Use render_template to stay on the same page so the error message is visible here
            # Do NOT use redirect(url_for('login')) here
            return render_template('forgot_password.html')

    # Display the empty forgot password form for initial page load (GET request)
    return render_template('forgot_password.html')

#<<<<<Industrial vacancy>>>>>
@app.route('/industrial')
def industrial():
    selected_cat = request.args.get('cat', 'all')
    vacancies = Vacancy.query.all() if selected_cat == 'all' else Vacancy.query.filter_by(category=selected_cat).all()
    return render_template('industrial.html', vacancies=vacancies, active_cat=selected_cat)


# <<<<submit suggestion>>>>>
@app.route('/submit-suggestion', methods=['GET', 'POST'])
def submit_suggestion():
    if request.method == 'POST':
        msg = request.form.get('suggestion')
        if msg:
            new_sug = Suggestion(content=msg)
            db.session.add(new_sug)
            db.session.commit()
            flash("✅ Your suggestion was submitted anonymously!", "success")
    return redirect(url_for('landing')) 

# ------------------------------------------------ ADMIN ROUTES ----------------------------------------------------------------------------------

#<<<<admin dashboard>>>>>
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('user_role') != 'admin': return redirect(url_for('login'))
    logins = Student.query.filter(Student.last_login != None).order_by(Student.last_login.desc()).all()
    return render_template('admin_dashboard.html', scount=Student.query.count(), subcount=Subject.query.count(), logins=logins)

#<<<<<Add vacnacy>>>>>>
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



#<<<<<upload students>>>>>>>

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


#<<<<<upload subjects>>>>>>
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


#<<<<<upload results>>>>>>
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

#<<<<student profile>>>>>>

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

#<<<<<building the cv>>>>>>>

@app.route('/cv-builder')
def cv_builder():
    # 1. ලොග් වෙලා නැත්නම්, "මූට CV එකක් හදන්න ඕනේ" කියලා සටහන් කරගන්නවා
    if 'user_id' not in session:
        session['redirect_to_cv'] = True  # මේක තමයි අපේ ලකුණ
        return redirect(url_for('login'))
    
    # 2. ලොග් වෙලා ඉන්නවා නම් සාමාන්‍ය විදිහට පේජ් එක පෙන්වනවා
    student = Student.query.get(session.get('user_id'))
    return render_template('cv_form.html', student=student)

#<<<<generate the cv>>>>>
@app.route('/cv-preview', methods=['GET', 'POST'])
@login_required
def cv_preview():
    #  Get the logged-in student for official sidebar info (Photo, Links, Email)
    reg_no = session.get('user_id')
    student = Student.query.get(reg_no)
    
    if request.method == 'POST':
        #  Capture "Adjusted" data from the Form
        #  clean the skills string into a list to match your HTML loop
        raw_skills = request.form.get('skills', '')
        skills_list = [s.strip() for s in raw_skills.split(',') if s.strip()]

        cv_data = {
            'name': request.form.get('name'),
            'bio': request.form.get('bio'),
            'experience': request.form.get('experience'),
            'skills': skills_list ,
            'projects': request.form.get('projects')
        }
    else:
        # Fallback: If they visit the page without submitting the form
        cv_data = {
            'name': student.name,
            'bio': student.bio or "No summary provided.",
            'experience': "No details provided.",
            'projects': "No details provided.",
            'skills': []
        }

    #  Send both 'student' (Database) and 'data' (Form) to the template
    # We do NOT pass results here to keep the CV focused on job skills
    return render_template('cv_preview.html', student=student, data=cv_data)



# <<<<<admin can see the suggestion>>>>>>>>
@app.route('/admin/view-suggestions')
@login_required
def admin_suggestions():
    if session.get('user_role') != 'admin':
        return redirect(url_for('login'))
    
    # store the suggestion
    all_suggestions = Suggestion.query.order_by(Suggestion.timestamp.desc()).all()
    return render_template('admin_suggestions.html', suggestions=all_suggestions)


#<<<<log out>>>>>
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))





if __name__ == '__main__':# When the script is run directly (as the main program), this block of code will execute. It ensures that the database tables are created before starting the Flask development server. The app.run(debug=True) line starts the server in debug mode, which provides helpful error messages and auto-reloads the server when code changes are detected, making development easier.
    with app.app_context():# Ensure that we are within the application context when calling db.create_all(), which is necessary for SQLAlchemy to access the app's configuration and properly create the database tables based on the defined models.
        db.create_all()# Create the database tables based on the defined models (Student, Subject, Result, Admin, Vacancy, Suggestion). This will create the tables in the MySQL database if they do not already exist. It's important to run this before starting the server to ensure that the database schema is set up correctly for the application to function.
    app.run(debug=True)# Start the Flask development server with debug mode enabled, allowing for easier debugging and automatic reloading of the server when code changes are made. This is useful during development to see changes in real-time and to get detailed error messages if something goes wrong.