import os
import re
import sqlite3
import secrets
from functools import wraps
from flask import Flask, render_template, request, g, session, redirect, url_for, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

APP_SECRET = os.getenv('SECRET_KEY', 'dev-secret-change-me')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'adminpass-change-me')
DEFAULT_ADMIN = 'adminpass-change-me'
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
STUDENT_TOKEN = os.getenv('STUDENT_TOKEN', '')
TRUSTED_PROXIES = os.getenv('TRUSTED_PROXIES', '')
DATABASE = os.path.join(os.path.dirname(__file__), 'students.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = APP_SECRET

# Rate limiting to protect the lookup endpoint from abuse
# Initialize limiter without passing the app to avoid argument conflicts,
# then attach it to the Flask app.
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)


def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.context_processor
def inject_lang():
    # Make `lang` available in all templates; respect ?lang=ar for Arabic/RTL
    lang = request.args.get('lang') or request.cookies.get('lang') or 'en'
    return dict(lang=lang)



def ensure_tables():
    """Ensure all required tables exist (safe to call on startup)."""
    db = get_db()
    db.execute('''
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        score REAL,
        max_score REAL
    )
    ''')
    db.execute('''
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        exam_name TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )
    ''')
    # tokens table for per-student shareable links
    db.execute('''
    CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(student_id)
    )
    ''')
    db.commit()


def ensure_share_token_column():
    """Ensure `share_token` column exists on `students` table."""
    db = get_db()
    cur = db.execute("PRAGMA table_info(students)")
    cols = [r['name'] for r in cur.fetchall()]
    if 'share_token' not in cols:
        db.execute('ALTER TABLE students ADD COLUMN share_token TEXT')
        db.commit()


def ensure_class_name_column():
    """Ensure `class_name` column exists on `students` table."""
    db = get_db()
    cur = db.execute("PRAGMA table_info(students)")
    cols = [r['name'] for r in cur.fetchall()]
    if 'class_name' not in cols:
        db.execute('ALTER TABLE students ADD COLUMN class_name TEXT')
        db.commit()


def get_client_ip():
    """Return the real client IP, honoring X-Forwarded-For when TRUSTED_PROXIES is set.

    TRUSTED_PROXIES should be a comma-separated list of proxy IPs (e.g. "127.0.0.1,::1").
    When set, this function will parse the `X-Forwarded-For` header and strip
    any trusted proxy IPs from the right; the remaining rightmost IP is
    considered the client IP. If parsing fails or TRUSTED_PROXIES is not set,
    falls back to `request.remote_addr`.
    """
    remote = request.remote_addr or ''
    trusted = {p.strip() for p in TRUSTED_PROXIES.split(',') if p.strip()}
    xff = request.headers.get('X-Forwarded-For', '')
    if not trusted or not xff:
        return remote
    parts = [p.strip() for p in xff.split(',') if p.strip()]
    # Remove trusted proxies from the right side of the list
    while parts and parts[-1] in trusted:
        parts.pop()
    if parts:
        return parts[-1]
    return remote


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/migrate', methods=['POST'])
@admin_required
def admin_migrate():
    """Move any existing students.score entries into the grades table.

    This is an admin action run once during migration.
    """
    db = get_db()
    cur = db.execute('SELECT student_id, full_name, score, max_score FROM students WHERE score IS NOT NULL')
    rows = cur.fetchall()
    moved = 0
    for r in rows:
        sid = r['student_id']
        score = r['score']
        max_score = r['max_score'] or 100
        # Insert as an imported exam row
        db.execute('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', (sid, 'Imported', score, max_score))
        db.execute('UPDATE students SET score = NULL, max_score = NULL WHERE student_id = ?', (sid,))
        moved += 1
    db.commit()
    flash(f'Migrated {moved} student score(s) into grades')
    return redirect(url_for('admin_list'))


@app.route('/admin/import', methods=['GET', 'POST'])
@admin_required
def admin_import():
    # CSV import: expected columns: student_id,full_name,exam_name,score,max_score[,class_name]
    if request.method == 'POST':
        file = request.files.get('csvfile')
        if not file:
            flash('No file uploaded')
            return redirect(url_for('admin_import'))
        text = file.read().decode('utf-8', errors='replace')
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        imported = 0
        db = get_db()
        for i, line in enumerate(lines):
            if i == 0 and line.lower().startswith('student_id'):
                continue
            parts = [p.strip().strip('"') for p in line.split(',')]
            if len(parts) < 5:
                continue
            sid, name, exam_name, score_s, max_s = parts[:5]
            class_name = parts[5] if len(parts) > 5 else ''
            try:
                score = float(score_s)
                max_score = float(max_s)
            except ValueError:
                continue
            # Upsert student
            existing = db.execute('SELECT class_name FROM students WHERE student_id = ?', (sid,)).fetchone()
            if not class_name and existing:
                class_name = existing['class_name'] or ''
            db.execute('REPLACE INTO students(student_id, full_name, class_name, score, max_score) VALUES (?, ?, ?, ?, ?)', (sid, name, class_name, None, None))
            db.execute('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', (sid, exam_name, score, max_score))
            imported += 1
        db.commit()
        flash(f'Imported {imported} rows')
        return redirect(url_for('admin_list'))
    return render_template('admin_import.html')


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.errorhandler(500)
def handle_500(e):
    return render_template('error.html', message='An internal error occurred.'), 500


@app.route('/', methods=['GET'])
def index():
    # Expose the temporary admin token to the template for easy one-click login
    return render_template('index.html')


@app.route('/result', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def result():
    # Allow lookup via POST form or GET query (one-click student link)
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
    else:
        student_id = request.args.get('student_id', '').strip()

    # Validate: allow alphanumeric and dash, length 3-12
    if not re.match(r'^[A-Za-z0-9-]{3,12}$', student_id):
        return render_template('error.html', message='Invalid Student ID format.'), 400

    db = get_db()
    cur = db.execute('SELECT student_id, full_name, class_name FROM students WHERE student_id = ?', (student_id,))
    student = cur.fetchone()
    if not student:
        return render_template('error.html', message='Student ID not found.'), 404

    # Fetch all grades for this student (multiple exams)
    gcur = db.execute('SELECT id, exam_name, score, max_score FROM grades WHERE student_id = ? ORDER BY exam_name', (student_id,))
    grade_rows = gcur.fetchall()

    # Compute simple grade letters (percent not stored/displayed)
    exams = []
    for r in grade_rows:
        score = r['score']
        max_score = r['max_score'] or 100
        ratio = (score / max_score) * 100
        if ratio >= 90:
            letter = 'A'
        elif ratio >= 75:
            letter = 'B'
        elif ratio >= 60:
            letter = 'C'
        else:
            letter = 'D'
        exams.append({'id': r['id'], 'exam_name': r['exam_name'], 'score': score, 'max_score': max_score, 'grade': letter})

    return render_template('result.html', student_id=student['student_id'], name=student['full_name'], class_name=student['class_name'], exams=exams)


# Admin pages: simple password-protected interface (use HTTPS & strong password in production)
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # Require deployer to set a non-default ADMIN_PASS before allowing login
    if ADMIN_PASS == DEFAULT_ADMIN:
        # Provide the token-login link when admin password is not configured
        return render_template('admin_login.html', warn='Please set ADMIN_PASS in your environment (see .env.example)', admin_token=ADMIN_TOKEN)

    if request.method == 'POST':
        pwd = request.form.get('password', '')
        if pwd == ADMIN_PASS:
            session['admin'] = True
            flash('Logged in')
            return redirect(url_for('admin_list'))
        flash('Invalid password')
    return render_template('admin_login.html', admin_token=ADMIN_TOKEN)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def admin_add():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        full_name = request.form.get('full_name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        # Optional exam fields: if provided, we'll insert into `grades`.
        exam_name = request.form.get('exam_name', '').strip()
        score_raw = request.form.get('score', '').strip()
        max_raw = request.form.get('max_score', '').strip() or '100'
        score = None
        max_score = None
        if score_raw:
            try:
                score = float(score_raw)
                max_score = float(max_raw)
            except ValueError:
                flash('Score and max score must be numbers')
                return render_template('admin_add.html')

        if not re.match(r'^[A-Za-z0-9-]{3,12}$', student_id):
            flash('Invalid student ID format')
            return render_template('admin_add.html')

        db = get_db()
        if not class_name:
            existing = db.execute('SELECT class_name FROM students WHERE student_id = ?', (student_id,)).fetchone()
            if existing:
                class_name = existing['class_name'] or ''
        # Ensure student record exists (score/max_score preserved if provided)
        # Use REPLACE to create or update basic student info (we keep score fields but prefer grades table).
        db.execute('REPLACE INTO students(student_id, full_name, class_name, score, max_score) VALUES (?, ?, ?, ?, ?)', (student_id, full_name, class_name, None, None))
        # If an exam was provided, insert into grades
        if exam_name and score is not None:
            db.execute('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', (student_id, exam_name, score, max_score))
        db.commit()
        flash(f'Inserted/updated {student_id}')
        return redirect(url_for('admin_student', student_id=student_id))

    return render_template('admin_add.html')


@app.route('/admin/list')
@admin_required
def admin_list():
    q = request.args.get('q', '').strip()
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per', 10))
    except ValueError:
        per_page = 10

    db = get_db()
    params = []
    where = ''
    if q:
        pattern = f'%{q}%'
        where = 'WHERE student_id LIKE ? OR full_name LIKE ? OR class_name LIKE ?'
        params.extend([pattern, pattern, pattern])

    # total count
    cnt_cur = db.execute(f'SELECT COUNT(*) as cnt FROM students {where}', params)
    total = cnt_cur.fetchone()['cnt']
    total_pages = max(1, (total + per_page - 1) // per_page)
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    cur = db.execute(f'SELECT student_id, full_name, class_name, score, max_score FROM students {where} ORDER BY student_id LIMIT ? OFFSET ?', params)
    rows = cur.fetchall()
    return render_template('admin_list.html', rows=rows, q=q, page=page, per_page=per_page, total=total, total_pages=total_pages)


@app.route('/admin/student/<student_id>', methods=['GET', 'POST'])
@admin_required
def admin_student(student_id):
    db = get_db()
    s = db.execute('SELECT student_id, full_name, class_name FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if not s:
        flash('Student not found')
        return redirect(url_for('admin_list'))

    if request.method == 'POST':
        # Add a single exam row from the form
        exam_name = request.form.get('exam_name', '').strip()
        try:
            score = float(request.form.get('score', ''))
            max_score = float(request.form.get('max_score', '100') or 100)
        except ValueError:
            flash('Score and max score must be numbers')
            return redirect(url_for('admin_student', student_id=student_id))

        if not exam_name:
            flash('Exam name required')
            return redirect(url_for('admin_student', student_id=student_id))

        db.execute('INSERT INTO grades(student_id, exam_name, score, max_score) VALUES (?, ?, ?, ?)', (student_id, exam_name, score, max_score))
        db.commit()
        flash('Added exam')
        return redirect(url_for('admin_student', student_id=student_id))

    grades = db.execute('SELECT id, exam_name, score, max_score FROM grades WHERE student_id = ? ORDER BY exam_name', (student_id,)).fetchall()
    # fetch share token if present
    cur = db.execute('SELECT share_token FROM students WHERE student_id = ?', (student_id,))
    st = cur.fetchone()
    share_token = st['share_token'] if st and 'share_token' in st.keys() else None
    return render_template('admin_student.html', student=s, grades=grades, share_token=share_token)


@app.route('/admin/student/<student_id>/share', methods=['POST'])
@admin_required
def admin_generate_share(student_id):
    db = get_db()
    # ensure column exists
    ensure_share_token_column()
    token = secrets.token_urlsafe(16)
    db.execute('UPDATE students SET share_token = ? WHERE student_id = ?', (token, student_id))
    db.commit()
    flash('Generated share link')
    return redirect(url_for('admin_student', student_id=student_id))


@app.route('/admin/student/<student_id>/share/revoke', methods=['POST'])
@admin_required
def admin_revoke_share(student_id):
    db = get_db()
    ensure_share_token_column()
    db.execute('UPDATE students SET share_token = NULL WHERE student_id = ?', (student_id,))
    db.commit()
    flash('Revoked share link')
    return redirect(url_for('admin_student', student_id=student_id))


@app.route('/admin/student/<student_id>/delete/<int:grade_id>')
@admin_required
def admin_delete_grade(student_id, grade_id):
    db = get_db()
    db.execute('DELETE FROM grades WHERE id = ? AND student_id = ?', (grade_id, student_id))
    db.commit()
    flash('Deleted exam')
    return redirect(url_for('admin_student', student_id=student_id))


@app.route('/admin/student/<student_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit(student_id):
    db = get_db()
    s = db.execute('SELECT student_id, full_name, class_name FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if not s:
        flash('Student not found')
        return redirect(url_for('admin_list'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        if not full_name:
            flash('Full name required')
            return render_template('admin_edit.html', student=s)
        db.execute('UPDATE students SET full_name = ?, class_name = ? WHERE student_id = ?', (full_name, class_name, student_id))
        db.commit()
        flash('Updated student')
        return redirect(url_for('admin_list'))

    return render_template('admin_edit.html', student=s)


@app.route('/admin/student/<student_id>/delete', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    db = get_db()
    # Remove grades, then student
    db.execute('DELETE FROM grades WHERE student_id = ?', (student_id,))
    db.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
    db.commit()
    flash('Deleted student and their exams')
    return redirect(url_for('admin_list'))


@app.route('/admin/export')
@admin_required
def admin_export():
    import io
    from flask import Response

    db = get_db()
    typ = request.args.get('type', 'grades')
    if typ == 'students':
        cur = db.execute('SELECT student_id, full_name, class_name FROM students ORDER BY student_id')
        rows = cur.fetchall()
        si = io.StringIO()
        si.write('student_id,full_name,class_name\n')
        for r in rows:
            sid = r['student_id']
            name = (r['full_name'] or '').replace('"', '""')
            class_name = (r['class_name'] or '').replace('"', '""')
            si.write(f'"{sid}","{name}","{class_name}"\n')
        output = si.getvalue()
        return Response(output, mimetype='text/csv', headers={'Content-Disposition':'attachment; filename="students.csv"'})

    # Default: Export grades with student full name
    cur = db.execute('''
        SELECT g.student_id, s.full_name, s.class_name, g.exam_name, g.score, g.max_score
        FROM grades g
        LEFT JOIN students s ON s.student_id = g.student_id
        ORDER BY g.student_id, g.exam_name
    ''')
    rows = cur.fetchall()

    si = io.StringIO()
    si.write('student_id,full_name,class_name,exam_name,score,max_score\n')
    for r in rows:
        sid = r['student_id']
        name = (r['full_name'] or '').replace('"', '""')
        class_name = (r['class_name'] or '').replace('"', '""')
        exam = (r['exam_name'] or '').replace('"', '""')
        si.write(f'"{sid}","{name}","{class_name}","{exam}",{r["score"]},{r["max_score"]}\n')

    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition':'attachment; filename="grades.csv"'})


@app.route('/admin/token-login')
def admin_token_login():
    # Temporary token login for convenience during setup. Token should be
    # set in the environment as ADMIN_TOKEN. Only enable when running locally.
    # Compute the real client IP (honors X-Forwarded-For when TRUSTED_PROXIES is set)
    client_ip = get_client_ip()
    if client_ip not in ('127.0.0.1', '::1'):
        return render_template('error.html', message='Token login is allowed from localhost only.'), 403

    token = request.args.get('t', '')
    if not ADMIN_TOKEN:
        return render_template('error.html', message='Token login not configured.'), 403
    if token != ADMIN_TOKEN:
        return render_template('error.html', message='Invalid token.'), 403
    session['admin'] = True
    flash('Logged in via token')
    return redirect(url_for('admin_list'))


@app.route('/student/<student_id>')
def student_link(student_id):
    # Short shareable URL that redirects to the result view.
    # Behavior:
    # - If a per-student `share_token` exists in the database, require ?t=token to match that token.
    # - Else if a global `STUDENT_TOKEN` is set, require ?t=STUDENT_TOKEN.
    db = get_db()
    # Try per-student token first
    try:
        cur = db.execute('SELECT share_token FROM students WHERE student_id = ?', (student_id,))
        row = cur.fetchone()
        per_token = row['share_token'] if row and 'share_token' in row.keys() else None
    except Exception:
        per_token = None

    provided = request.args.get('t', '').strip()
    if per_token:
        if not provided or provided != per_token:
            return render_template('token_required.html', student_id=student_id), 403
        return redirect(url_for('result', student_id=student_id))

    # Fallback to global token if configured
    if STUDENT_TOKEN:
        if not provided or provided != STUDENT_TOKEN:
            return render_template('token_required.html', student_id=student_id), 403

    return redirect(url_for('result', student_id=student_id))


if __name__ == '__main__':
    # ensure grades table exists when starting
    with app.app_context():
        ensure_tables()
        ensure_share_token_column()
        ensure_class_name_column()
    # Print helpful startup info (parsed TRUSTED_PROXIES and LAN URL) to help
    # when accessing the app from other devices on the same network.
    parsed_proxies = [p.strip() for p in TRUSTED_PROXIES.split(',') if p.strip()]
    if parsed_proxies:
        print('TRUSTED_PROXIES:', parsed_proxies)
    else:
        print('TRUSTED_PROXIES: (none)')

    # Try to detect a likely LAN IP for convenience (best-effort).
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = '127.0.0.1'

    port = int(os.getenv('PORT', '5000'))
    print(f'Running on http://127.0.0.1:{port} and http://{lan_ip}:{port}')
    print('Tip: set TRUSTED_PROXIES when using a reverse proxy so local-only routes work.')
    app.run(host='0.0.0.0', port=port, debug=False)
