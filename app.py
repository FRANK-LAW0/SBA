from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g
)
import sqlite3
import os
import functools
import fake_info
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__,
            template_folder='build',
            static_folder='build/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['DATABASE'] = os.path.join(app.root_path, 'sports_day.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
        DROP TABLE IF EXISTS results;
        DROP TABLE IF EXISTS Events;
        DROP TABLE IF EXISTS Athletes;
        DROP TABLE IF EXISTS Users;
        
        CREATE TABLE Users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN('admin','user'))
        );

        CREATE TABLE Events (
            event_id TEXT PRIMARY KEY,
            event TEXT NOT NULL,
            sex TEXT NOT NULL CHECK(sex IN('Boys','Girls')),
            grade TEXT NOT NULL CHECK(grade IN('A','B','C'))
        );
        
        CREATE TABLE Athletes (
            athlete_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            house TEXT NOT NULL,
            sex TEXT NOT NULL CHECK(sex IN('Boys','Girls')),
            grade TEXT NOT NULL CHECK(grade IN('A','B','C'))
        );
        
        CREATE TABLE results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id TEXT NOT NULL REFERENCES Athletes(athlete_id),
            event_id TEXT NOT NULL REFERENCES Events(event_id),
            result REAL NOT NULL
        );
    """)
    
    users = [
        ('admin', generate_password_hash('adminpass'), 'admin'),
        ('user', generate_password_hash('userpass'), 'user')
    ]
    db.executemany("INSERT INTO Users VALUES (?,?,?)", users)

    ath, ev, res = fake_info.sample(120)
    db.executemany("INSERT INTO Athletes VALUES (?,?,?,?,?)", ath)
    db.executemany("INSERT INTO Events VALUES (?,?,?,?)", ev)
    db.executemany(
        "INSERT INTO results(athlete_id,event_id,result) VALUES (?,?,?)",
        res
    )
    db.commit()

if not os.path.exists(app.config['DATABASE']):
    with app.app_context():
        init_db()

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admins only", "error")
            return redirect(url_for('list_results'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute(
            "SELECT * FROM Users WHERE username=?",
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome, {username}", "success")
            return redirect(url_for('index'))
        flash("Bad credentials", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_result():
    db = get_db()
    if request.method == 'POST':
        ath_id = request.form['athlete_id'].strip()
        ev_id = request.form['event_id'].strip()
        
        try:
            result = float(request.form['result'])
        except ValueError:
            flash("Result must be a number", "error")
            return redirect(url_for('add_result'))

        athlete = db.execute(
            "SELECT * FROM Athletes WHERE athlete_id=?", (ath_id,)
        ).fetchone()
        event = db.execute(
            "SELECT * FROM Events WHERE event_id=?", (ev_id,)
        ).fetchone()

        if not athlete:
            flash("Athlete ID not found", "error")
        elif not event:
            flash("Event ID not found", "error")
        elif athlete['sex'] != event['sex'] or athlete['grade'] != event['grade']:
            flash("Sex/grade mismatch between athlete & event", "error")
        else:
            db.execute(
                "INSERT INTO results(athlete_id,event_id,result) VALUES (?,?,?)",
                (ath_id, ev_id, result)
            )
            db.commit()
            flash("Result added", "success")
            return redirect(url_for('list_results'))

    return render_template('add_result.html')

@app.route('/results')
@login_required
def list_results():
    db = get_db()
    
    event_filter = request.args.get('event', '').strip()
    athlete_id = request.args.get('athlete', '').strip()
    sex_filter = request.args.get('sex', '')
    grade_filter = request.args.get('grade', '')

    sql = """
        SELECT 
            r.result_id,
            r.result,
            a.athlete_id, 
            a.name, 
            a.house, 
            a.grade AS athlete_grade,
            a.sex AS athlete_sex,
            e.event_id, 
            e.event, 
            e.sex AS event_sex, 
            e.grade AS event_grade
        FROM results r
        JOIN Athletes a ON a.athlete_id = r.athlete_id
        JOIN Events e ON e.event_id = r.event_id
        WHERE 1=1
    """
    params = []
    
    if event_filter:
        sql += " AND e.event = ?"
        params.append(event_filter)
    if sex_filter:
        sql += " AND a.sex = ?"
        params.append(sex_filter)
    if grade_filter:
        sql += " AND a.grade = ?"
        params.append(grade_filter)
    
    all_rows = db.execute(sql, tuple(params)).fetchall()

    grouped = {}
    for row in all_rows:
        key = (row['event_id'], row['event'], f"{row['event_sex']} {row['event_grade']}")
        if key not in grouped:
            grouped[key] = []
        
        is_time_based = 'meters' in row['event'].lower() or 'run' in row['event'].lower()
        
        grouped[key].append({
            'result_id': row['result_id'],
            'athlete_id': row['athlete_id'],
            'name': row['name'],
            'house': row['house'],
            'result': row['result'],
            'is_time_based': is_time_based
        })

    ranked_groups = {}
    for key, results in grouped.items():
        sorted_results = sorted(
            results,
            key=lambda x: x['result'],
            reverse=not results[0]['is_time_based']  # Reverse sort for non-time events
        )
        
        ranked_results = []
        current_rank = 1
        for i, result in enumerate(sorted_results):
            if i > 0 and result['result'] == sorted_results[i-1]['result']:
                result['rank'] = current_rank
            else:
                current_rank = i + 1
                result['rank'] = current_rank
            ranked_results.append(result)
        
        ranked_groups[key] = ranked_results

    if athlete_id:
        filtered_groups = {}
        for key, results in ranked_groups.items():
            filtered_results = [r for r in results if r['athlete_id'] == athlete_id]
            if filtered_results:
                filtered_groups[key] = filtered_results
        ranked_groups = filtered_groups

    sorted_groups = sorted(ranked_groups.items(), key=lambda x: x[0][0])
    
    events = db.execute(
        "SELECT DISTINCT event FROM Events ORDER BY event_id"
    ).fetchall()
    
    sexes = ['Boys', 'Girls']
    grades = ['A', 'B', 'C']

    return render_template('list_results.html',
                         grouped_results=sorted_groups,
                         events=events,
                         sexes=sexes,
                         grades=grades,
                         current_filters={
                             'event': event_filter,
                             'athlete': athlete_id,
                             'sex': sex_filter,
                             'grade': grade_filter
                         })

@app.route('/results/edit/<int:rid>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_result(rid):
    db = get_db()
    row = db.execute("""
        SELECT r.*, a.name as athlete_name, e.event as event_name
        FROM results r
        JOIN Athletes a ON a.athlete_id = r.athlete_id
        JOIN Events e ON e.event_id = r.event_id
        WHERE r.result_id=?
    """, (rid,)).fetchone()
    
    if not row:
        flash("Result not found", "error")
        return redirect(url_for('list_results'))
        
    if request.method == 'POST':
        try:
            result = float(request.form['result'])
            db.execute(
                "UPDATE results SET result=? WHERE result_id=?",
                (result, rid)
            )
            db.commit()
            flash("Result updated successfully", "success")
            return redirect(url_for('list_results'))
        except ValueError:
            flash("Result must be a valid number", "error")
    
    return render_template('edit_result.html', row=row)

@app.route('/results/delete/<int:rid>', methods=['POST'])
@login_required
@admin_required
def delete_result(rid):
    db = get_db()
    try:
        db.execute("DELETE FROM results WHERE result_id=?", (rid,))
        db.commit()
        flash("Result deleted successfully", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting result: {str(e)}", "error")
    return redirect(url_for('list_results'))

@app.route('/athletes')
@login_required
@admin_required
def list_athletes():
    house = request.args.get('house', '')
    sex = request.args.get('sex', '')
    grade = request.args.get('grade', '')
    
    query = "SELECT * FROM Athletes"
    where_filters = []
    params = []
    
    if house:
        where_filters.append("house=?")
        params.append(house)
    if sex:
        where_filters.append("sex=?")
        params.append(sex)
    if grade:
        where_filters.append("grade=?")
        params.append(grade)
    
    if where_filters:
        query += " WHERE " + " AND ".join(where_filters)
    
    db = get_db()
    athletes = db.execute(query, params).fetchall()
    houses = db.execute("SELECT DISTINCT house FROM Athletes").fetchall()
    grades = db.execute("SELECT DISTINCT grade FROM Athletes ORDER BY grade").fetchall()
    
    return render_template('list_athletes.html',
            athletes=athletes,
            houses=houses,
            sexes=['Boys', 'Girls'],
            grades=grades,
            current_filters={'house': house, 'sex': sex, 'grade': grade}
    )

@app.route('/events')
@login_required
@admin_required
def list_events():
    sex = request.args.get('sex', '')
    grade = request.args.get('grade', '')
    
    query = "SELECT * FROM Events"
    where_filters = []
    params = []
    
    if sex:
        where_filters.append("sex=?")
        params.append(sex)
    if grade:
        where_filters.append("grade=?")
        params.append(grade)
    
    if where_filters:
        query += " WHERE " + " AND ".join(where_filters)
    
    db = get_db()
    events = db.execute(query, params).fetchall()
    
    return render_template('list_events.html',
            events=events,
            sexes=['Boys', 'Girls'],
            grades=['A', 'B', 'C'],
            current_filters={'sex': sex, 'grade': grade}
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
