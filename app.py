from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import date, datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'student_tracker_secret_key_2024'

DATABASE = 'student_tracker.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        class TEXT NOT NULL,
        section TEXT NOT NULL,
        gender TEXT NOT NULL,
        parent_name TEXT,
        parent_contact TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        marks_obtained REAL NOT NULL,
        total_marks REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        competition_name TEXT NOT NULL,
        competition_type TEXT NOT NULL,
        position TEXT NOT NULL,
        date TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS certifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        certificate_name TEXT NOT NULL,
        organization TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')

    # Default admin
    c.execute("SELECT * FROM teachers WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO teachers (username, password, full_name) VALUES (?, ?, ?)",
                  ('admin', 'admin123', 'Administrator'))

    conn.commit()
    conn.close()

@app.context_processor
def inject_now():
    return {'now': datetime.now().strftime('%B %d, %Y')}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'teacher_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        teacher = conn.execute('SELECT * FROM teachers WHERE username=? AND password=?', (username, password)).fetchone()
        conn.close()
        if teacher:
            session['teacher_id'] = teacher['id']
            session['teacher_name'] = teacher['full_name'] or teacher['username']
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    total_students = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
    total_achievements = conn.execute('SELECT COUNT(*) FROM achievements').fetchone()[0]
    total_certs = conn.execute('SELECT COUNT(*) FROM certifications').fetchone()[0]
    total_attendance = conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0]
    recent_students = conn.execute('SELECT * FROM students ORDER BY created_at DESC LIMIT 5').fetchall()
    recent_achievements = conn.execute('''
        SELECT a.*, s.name as student_name FROM achievements a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.created_at DESC LIMIT 5
    ''').fetchall()
    conn.close()
    return render_template('dashboard.html',
        total_students=total_students,
        total_achievements=total_achievements,
        total_certs=total_certs,
        total_attendance=total_attendance,
        recent_students=recent_students,
        recent_achievements=recent_achievements
    )

# ─── STUDENTS ────────────────────────────────────────────────────────────────

@app.route('/students')
@login_required
def students():
    search = request.args.get('search', '').strip()
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? OR student_id LIKE ? OR class LIKE ? ORDER BY name",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    conn.close()
    return render_template('students.html', students=rows, search=search)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        data = (
            request.form['student_id'], request.form['name'], request.form['class'],
            request.form['section'], request.form['gender'],
            request.form.get('parent_name', ''), request.form.get('parent_contact', '')
        )
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO students (student_id, name, class, section, gender, parent_name, parent_contact) VALUES (?,?,?,?,?,?,?)',
                data
            )
            conn.commit()
            conn.close()
            flash('Student added successfully.', 'success')
            return redirect(url_for('students'))
        except sqlite3.IntegrityError:
            flash('Student ID already exists.', 'danger')
    return render_template('student_form.html', student=None, action='Add')

@app.route('/students/edit/<int:sid>', methods=['GET', 'POST'])
@login_required
def edit_student(sid):
    conn = get_db()
    student = conn.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('students'))
    if request.method == 'POST':
        try:
            conn.execute(
                'UPDATE students SET student_id=?, name=?, class=?, section=?, gender=?, parent_name=?, parent_contact=? WHERE id=?',
                (request.form['student_id'], request.form['name'], request.form['class'],
                 request.form['section'], request.form['gender'],
                 request.form.get('parent_name', ''), request.form.get('parent_contact', ''), sid)
            )
            conn.commit()
            conn.close()
            flash('Student updated.', 'success')
            return redirect(url_for('students'))
        except sqlite3.IntegrityError:
            flash('Student ID already exists.', 'danger')
    conn.close()
    return render_template('student_form.html', student=student, action='Edit')

@app.route('/students/delete/<int:sid>', methods=['POST'])
@login_required
def delete_student(sid):
    conn = get_db()
    conn.execute('DELETE FROM students WHERE id=?', (sid,))
    conn.execute('DELETE FROM attendance WHERE student_id=?', (sid,))
    conn.execute('DELETE FROM marks WHERE student_id=?', (sid,))
    conn.execute('DELETE FROM achievements WHERE student_id=?', (sid,))
    conn.execute('DELETE FROM certifications WHERE student_id=?', (sid,))
    conn.commit()
    conn.close()
    flash('Student deleted.', 'success')
    return redirect(url_for('students'))

# ─── ATTENDANCE ───────────────────────────────────────────────────────────────

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    conn = get_db()
    selected_date = request.args.get('date', date.today().isoformat())
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    attendance_map = {}
    records = conn.execute('SELECT * FROM attendance WHERE date=?', (selected_date,)).fetchall()
    for r in records:
        attendance_map[r['student_id']] = r['status']

    if request.method == 'POST':
        selected_date = request.form.get('date', date.today().isoformat())
        for s in students_list:
            status = request.form.get(f'status_{s["id"]}', 'Absent')
            existing = conn.execute('SELECT id FROM attendance WHERE student_id=? AND date=?', (s['id'], selected_date)).fetchone()
            if existing:
                conn.execute('UPDATE attendance SET status=? WHERE student_id=? AND date=?', (status, s['id'], selected_date))
            else:
                conn.execute('INSERT INTO attendance (student_id, date, status) VALUES (?,?,?)', (s['id'], selected_date, status))
        conn.commit()
        flash('Attendance saved.', 'success')
        return redirect(url_for('attendance', date=selected_date))

    # Attendance history per student
    history = conn.execute('''
        SELECT s.name, s.student_id as sid,
               SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present_count,
               COUNT(a.id) as total_count
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id ORDER BY s.name
    ''').fetchall()

    conn.close()
    return render_template('attendance.html',
        students=students_list,
        attendance_map=attendance_map,
        selected_date=selected_date,
        history=history
    )

# ─── MARKS ────────────────────────────────────────────────────────────────────

@app.route('/marks')
@login_required
def marks():
    conn = get_db()
    rows = conn.execute('''
        SELECT m.*, s.name as student_name, s.student_id as sid
        FROM marks m JOIN students s ON m.student_id = s.id
        ORDER BY s.name, m.subject
    ''').fetchall()
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    # Average per student
    averages = conn.execute('''
        SELECT s.name, s.student_id as sid,
               ROUND(AVG(m.marks_obtained * 100.0 / m.total_marks), 1) as avg_pct
        FROM students s JOIN marks m ON s.id = m.student_id
        GROUP BY s.id ORDER BY avg_pct DESC
    ''').fetchall()
    conn.close()
    return render_template('marks.html', marks=rows, students=students_list, averages=averages)

@app.route('/marks/add', methods=['GET', 'POST'])
@login_required
def add_marks():
    conn = get_db()
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    if request.method == 'POST':
        conn.execute(
            'INSERT INTO marks (student_id, subject, exam_name, marks_obtained, total_marks) VALUES (?,?,?,?,?)',
            (request.form['student_id'], request.form['subject'], request.form['exam_name'],
             request.form['marks_obtained'], request.form['total_marks'])
        )
        conn.commit()
        conn.close()
        flash('Marks added.', 'success')
        return redirect(url_for('marks'))
    conn.close()
    return render_template('marks_form.html', students=students_list, mark=None, action='Add')

@app.route('/marks/edit/<int:mid>', methods=['GET', 'POST'])
@login_required
def edit_marks(mid):
    conn = get_db()
    mark = conn.execute('SELECT * FROM marks WHERE id=?', (mid,)).fetchone()
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    if request.method == 'POST':
        conn.execute(
            'UPDATE marks SET student_id=?, subject=?, exam_name=?, marks_obtained=?, total_marks=? WHERE id=?',
            (request.form['student_id'], request.form['subject'], request.form['exam_name'],
             request.form['marks_obtained'], request.form['total_marks'], mid)
        )
        conn.commit()
        conn.close()
        flash('Marks updated.', 'success')
        return redirect(url_for('marks'))
    conn.close()
    return render_template('marks_form.html', students=students_list, mark=mark, action='Edit')

@app.route('/marks/delete/<int:mid>', methods=['POST'])
@login_required
def delete_marks(mid):
    conn = get_db()
    conn.execute('DELETE FROM marks WHERE id=?', (mid,))
    conn.commit()
    conn.close()
    flash('Marks deleted.', 'success')
    return redirect(url_for('marks'))

# ─── ACHIEVEMENTS ─────────────────────────────────────────────────────────────

@app.route('/achievements')
@login_required
def achievements():
    conn = get_db()
    rows = conn.execute('''
        SELECT a.*, s.name as student_name FROM achievements a
        JOIN students s ON a.student_id = s.id ORDER BY a.date DESC
    ''').fetchall()
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    conn.close()
    return render_template('achievements.html', achievements=rows, students=students_list)

@app.route('/achievements/add', methods=['POST'])
@login_required
def add_achievement():
    conn = get_db()
    conn.execute(
        'INSERT INTO achievements (student_id, competition_name, competition_type, position, date) VALUES (?,?,?,?,?)',
        (request.form['student_id'], request.form['competition_name'],
         request.form['competition_type'], request.form['position'], request.form['date'])
    )
    conn.commit()
    conn.close()
    flash('Achievement added.', 'success')
    return redirect(url_for('achievements'))

@app.route('/achievements/delete/<int:aid>', methods=['POST'])
@login_required
def delete_achievement(aid):
    conn = get_db()
    conn.execute('DELETE FROM achievements WHERE id=?', (aid,))
    conn.commit()
    conn.close()
    flash('Achievement deleted.', 'success')
    return redirect(url_for('achievements'))

# ─── CERTIFICATIONS ───────────────────────────────────────────────────────────

@app.route('/certifications')
@login_required
def certifications():
    conn = get_db()
    rows = conn.execute('''
        SELECT c.*, s.name as student_name FROM certifications c
        JOIN students s ON c.student_id = s.id ORDER BY c.date DESC
    ''').fetchall()
    students_list = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
    conn.close()
    return render_template('certifications.html', certifications=rows, students=students_list)

@app.route('/certifications/add', methods=['POST'])
@login_required
def add_certification():
    conn = get_db()
    conn.execute(
        'INSERT INTO certifications (student_id, certificate_name, organization, date, description) VALUES (?,?,?,?,?)',
        (request.form['student_id'], request.form['certificate_name'],
         request.form['organization'], request.form['date'], request.form.get('description', ''))
    )
    conn.commit()
    conn.close()
    flash('Certification added.', 'success')
    return redirect(url_for('certifications'))

@app.route('/certifications/delete/<int:cid>', methods=['POST'])
@login_required
def delete_certification(cid):
    conn = get_db()
    conn.execute('DELETE FROM certifications WHERE id=?', (cid,))
    conn.commit()
    conn.close()
    flash('Certification deleted.', 'success')
    return redirect(url_for('certifications'))



# ─── REGISTER ────────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username  = request.form.get('username', '').strip()
        password  = request.form.get('password', '').strip()
        confirm   = request.form.get('confirm_password', '').strip()

        if not full_name or not username or not password:
            flash('All fields are required.', 'danger')
        elif len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            try:
                conn = get_db()
                conn.execute(
                    'INSERT INTO teachers (username, password, full_name) VALUES (?, ?, ?)',
                    (username, password, full_name)
                )
                conn.commit()
                conn.close()
                flash('Account created! You can now sign in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('That username is already taken. Please choose another.', 'danger')
    return render_template('register.html')


# ─── MY ACCOUNT ──────────────────────────────────────────────────────────────

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    conn    = get_db()
    teacher = conn.execute('SELECT * FROM teachers WHERE id=?', (session['teacher_id'],)).fetchone()
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            username  = request.form.get('username', '').strip()
            if not full_name or not username:
                flash('Name and username are required.', 'danger')
            elif len(username) < 3:
                flash('Username must be at least 3 characters.', 'danger')
            else:
                try:
                    conn.execute(
                        'UPDATE teachers SET full_name=?, username=? WHERE id=?',
                        (full_name, username, session['teacher_id'])
                    )
                    conn.commit()
                    session['teacher_name'] = full_name
                    flash('Profile updated successfully.', 'success')
                    conn.close()
                    return redirect(url_for('account'))
                except sqlite3.IntegrityError:
                    flash('That username is already taken.', 'danger')

        elif action == 'change_password':
            current = request.form.get('current_password', '').strip()
            new_pw  = request.form.get('new_password', '').strip()
            confirm = request.form.get('confirm_password', '').strip()
            if not current or not new_pw or not confirm:
                flash('All password fields are required.', 'danger')
            elif teacher['password'] != current:
                flash('Current password is incorrect.', 'danger')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_pw != confirm:
                flash('New passwords do not match.', 'danger')
            else:
                conn.execute('UPDATE teachers SET password=? WHERE id=?', (new_pw, session['teacher_id']))
                conn.commit()
                flash('Password changed successfully.', 'success')
                conn.close()
                return redirect(url_for('account'))

    conn.close()
    return render_template('account.html', teacher=teacher)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)