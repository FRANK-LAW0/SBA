from flask import Flask, render_template, request, redirect, url_for, flash, session, g
import sqlite3
import os
import functools
import fake_info
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='build', static_folder='build/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['DATABASE'] = os.path.join(app.root_path, 'sports_day.db')

# ensure the database directory exists and connect database
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

# disconnect database
@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

# create tables & insert data
def init_db():
    print("initializing database...")
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
            grade TEXT NOT NULL CHECK(grade IN('A','B','C')),
            status TEXT NOT NULL CHECK(status IN('Completed', 'Not yet start'))
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
            result REAL,
            status TEXT NOT NULL CHECK(status IN('Completed', 'Not yet start', 'Disqualification'))
        );
    """)
    
    # sample username & password
    # hash the password
    users = [
        ('admin', generate_password_hash('adminpass'), 'admin'),
        ('user', generate_password_hash('userpass'), 'user')
    ]
    db.executemany("INSERT INTO Users VALUES (?,?,?)", users)

    ath, ev, res = fake_info.sample(120)
    db.executemany("INSERT INTO Athletes VALUES (?,?,?,?,?)", ath)
    db.executemany("INSERT INTO Events VALUES (?,?,?,?,?)", ev)
    db.executemany("INSERT INTO results(athlete_id,event_id,result,status) VALUES (?,?,?,?)", res)
    db.commit()

if not os.path.exists(app.config['DATABASE']):
    with app.app_context():
        init_db()

# authentication decorators
def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

# create admin role
def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admins only", "error")
            return redirect(url_for('list_results'))
        return f(*args, **kwargs)
    return wrapper

# login route
# check whether username matches password & show the role
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
        flash("Incorrect username or password", "error")
    return render_template('login.html')

# just logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# home route
# show the home page
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# add results to the database 
@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_result():
    db = get_db()
    if request.method == 'POST':
        ath_id = request.form['athlete_id'].strip()
        ev_id = request.form['event_id'].strip()

        # check whether the input of result is a real number
        try:
            result = float(request.form['result'])
        except ValueError:
            flash("Result must be a number", "error")
            return redirect(url_for('add_result'))
        
        if result <= 0:
            flash("Result must be a number larger than 0", "error")
            return redirect(url_for('add_result'))
        
        # check whether the athlete_id and event_id exist in results
        rid = db.execute("""
        SELECT result_id FROM results
        WHERE athlete_id=? AND event_id=?
        """, (ath_id, ev_id)).fetchone()
        
        if rid:
            flash("Result already exists for this athlete and event", "error")
            return redirect(url_for('add_result'))
        
        status = request.form['status']

        athlete = db.execute(
            "SELECT * FROM Athletes WHERE athlete_id=?", (ath_id,)
        ).fetchone()
        event = db.execute(
            "SELECT * FROM Events WHERE event_id=?", (ev_id,)
        ).fetchone()
        
        # check whether the athlete_id and event_id are found
        # also check whether the sex and grade of the athlete match the event's
        if not athlete:
            flash("Athlete ID not found", "error")
        elif not event:
            flash("Event ID not found", "error")
        elif athlete['sex'] != event['sex'] or athlete['grade'] != event['grade']:
            flash("Sex/grade mismatch between athlete & event", "error")
        else:
            # check whether the event has started
            event_status = event['status']
            if event_status == 'Not yet start':
                flash("Cannot add result to an event that has not started", "error")
                return redirect(url_for('add_result'))
            
            db.execute(
                "INSERT INTO results(athlete_id,event_id,result,status) VALUES (?,?,?,?)",
                (ath_id, ev_id, result, status)
            )
            db.commit()
            flash("Result added", "success")
            return redirect(url_for('list_results'))

    return render_template('add_result.html')

# edit result in results
@app.route('/results/edit/<int:rid>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_result(rid):
    # ensure the result is found
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
        # ensure the new result is a real number 
        try:
            result = float(request.form['result'])

            if result <= 0:
                flash("Result must be a number larger than 0", "error")
                return render_template('edit_result.html', row=row)
            
            status = request.form['status']
            
            # update the result
            if status != 'Not yet start':
                db.execute(
                  "UPDATE results SET result=?, status=? WHERE result_id=?",
                  (result, status, rid)
                )
            else:
                db.execute(
                  "UPDATE results SET result=NULL, status=? WHERE result_id=?",
                  (status, rid)
                )
            db.commit()
            flash("Result updated successfully", "success")
            return redirect(url_for('list_results'))
        except ValueError:
            flash("Result must be a valid number", "error")
    
    return render_template('edit_result.html', row=row)

# delete result in results
@app.route('/results/delete/<int:rid>', methods=['POST'])
@login_required
@admin_required
def delete_result(rid):
    db = get_db()
    # ensure the result exist
    try:
        db.execute("DELETE FROM results WHERE result_id=?", (rid,))
        db.commit()
        flash("Result deleted successfully", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error deleting result: {str(e)}", "error")
    return redirect(url_for('list_results'))

# show athletes table
@app.route('/athletes')
@login_required
@admin_required
def list_athletes():
    # filter function
    athlete_id = request.args.get('athlete_id', '').strip()
    house = request.args.get('house', '')
    sex = request.args.get('sex', '')
    grade = request.args.get('grade', '')
    
    query = "SELECT * FROM Athletes"
    where_filters = []
    params = []
    
    if athlete_id:
        where_filters.append("athlete_id=?")
        params.append(athlete_id)
    if house:
        where_filters.append("house=?")
        params.append(house)
    if sex:
        where_filters.append("sex=?")
        params.append(sex)
    if grade:
        where_filters.append("grade=?")
        params.append(grade)
    
    # add condition in the filter function to the sql
    if where_filters:
        query += " WHERE " + " AND ".join(where_filters)
    
    # create dropdown list for filtering
    db = get_db()
    athletes = db.execute(query, params).fetchall()
    
    return render_template('list_athletes.html',
            athletes=athletes,
            houses=['Red', 'Blue', 'Green', 'Yellow'],
            sexes=['Boys', 'Girls'],
            grades=['A', 'B', 'C'],
            current_filters={
                'athlete_id': athlete_id, 
                'house': house, 
                'sex': sex, 
                'grade': grade
            }
    )

# show events table
@app.route('/events')
@login_required
@admin_required
def list_events():
    # filter function
    event_name = request.args.get('event_name', '').strip()
    sex = request.args.get('sex', '')
    grade = request.args.get('grade', '')
    status = request.args.get('status', '')
    
    query = "SELECT * FROM Events"
    where_filters = []
    params = []
    
    if event_name:
        where_filters.append("event LIKE ?")
        params.append(f"%{event_name}%")
    if sex:
        where_filters.append("sex=?")
        params.append(sex)
    if grade:
        where_filters.append("grade=?")
        params.append(grade)
    if status:
        where_filters.append("status=?")
        params.append(status)
    
    # add condition in the filter function to the sql
    if where_filters:
        query += " WHERE " + " AND ".join(where_filters)
    
    query += " ORDER BY event_id"

    # create dropdown list for filtering
    db = get_db()
    events = db.execute(query, params).fetchall()
    distinct_events = db.execute("SELECT DISTINCT event FROM Events ORDER BY event_id").fetchall()

    return render_template('list_events.html',
            events=events,
            distinct_events=distinct_events,
            sexes=['Boys', 'Girls'],
            grades=['A', 'B', 'C'],
            statuses=['Completed', 'Not yet start'],
            current_filters={
                'event_name': event_name, 
                'sex': sex, 
                'grade': grade, 
                'status': status
            }
    )

# show the results table
@app.route('/results')
@login_required
def list_results():
    db = get_db()
    
    #filter function
    event_filter = request.args.get('event', '').strip()
    athlete_id = request.args.get('athlete', '').strip()
    sex_filter = request.args.get('sex', '')
    grade_filter = request.args.get('grade', '')
    status_filter = request.args.get('status', '')
    
    # sql for showing all data
    sql = """
        SELECT 
            r.result_id,
            r.result,
            r.status,
            a.athlete_id, 
            a.name, 
            a.house, 
            a.grade AS athlete_grade,
            a.sex AS athlete_sex,
            e.event_id, 
            e.event, 
            e.sex AS event_sex, 
            e.grade AS event_grade,
            e.status AS event_status
        FROM results r
        JOIN Athletes a ON a.athlete_id = r.athlete_id
        JOIN Events e ON e.event_id = r.event_id
        WHERE 1=1
    """
    params = []
    
    # add the condition in the filer function to the sql 
    if event_filter:
        sql += " AND e.event = ?"
        params.append(event_filter)
    if sex_filter:
        sql += " AND a.sex = ?"
        params.append(sex_filter)
    if grade_filter:
        sql += " AND a.grade = ?"
        params.append(grade_filter)
    if status_filter:
        sql += " AND r.status = ?"
        params.append(status_filter)

    all_rows = db.execute(sql, tuple(params)).fetchall()
    
    # group data by event
    grouped = {}
    for row in all_rows:
        key = (row['event_id'], row['event'], f"{row['event_sex']} {row['event_grade']}")
        if key not in grouped:
            grouped[key] = {'event_status': row['event_status'], 'result': []}
        
        is_time_based = 'meters' in row['event'].lower()
        
        grouped[key]['result'].append({
            'result_id': row['result_id'],
            'athlete_id': row['athlete_id'],
            'name': row['name'],
            'house': row['house'],
            'result': row['result'],
            'is_time_based': is_time_based,
            'status': row['status'] if row['event_status'] == 'Completed' else 'Not yet start',
        })

    # sort results in each event
    ranked_groups = {}
    for key, results in grouped.items():
        
        def invalid_ranking(r):
            return (r['result'] is None) or (r['status'] in ('Disqualification', 'Not yet start'))
        
        is_time_based = results['result'][0]['is_time_based'] if results['result'] else False
        valid = [res for res in results['result'] if not invalid_ranking(res)]
        invalid = [res for res in results['result'] if invalid_ranking(res)]
        
        if is_time_based:
            sorted_results = sorted(valid, key=lambda r: r['result'])
        else:
            sorted_results = sorted(valid, key=lambda r: -r['result'])
        
        sorted_results.extend(invalid)
        
        ranked_results = []
        current_rank = 1
        for i, result in enumerate(sorted_results):
            if invalid_ranking(result):
                result['rank'] = None
                ranked_results.append(result)
                continue
            if i > 0 and result['result'] == sorted_results[i-1]['result']:
                result['rank'] = current_rank
            else:
                current_rank = i + 1
                result['rank'] = current_rank
            ranked_results.append(result)
        
        ranked_groups[key] = ranked_results
    
    # filter by athlete_id
    if athlete_id:
        filtered_groups = {}
        for key, results in ranked_groups.items():
            filtered_results = [r for r in results if r['athlete_id'] == athlete_id]
            if filtered_results:
                filtered_groups[key] = filtered_results
        ranked_groups = filtered_groups
    
    # create dropdown list for filtering
    sorted_groups = sorted(ranked_groups.items(), key=lambda x: x[0][0])
    events = db.execute("SELECT DISTINCT event FROM Events ORDER BY event_id").fetchall() 

    return render_template('list_results.html',
            grouped_results=sorted_groups,
            events=events,
            sexes=['Boys', 'Girls'],
            grades=['A', 'B', 'C'],
            statuses=['Completed', 'Not yet start', 'Disqualification'],
            current_filters={
                'event': event_filter,
                'athlete': athlete_id,
                'sex': sex_filter,
                'grade': grade_filter,
                'status': status_filter
            }
    )

# execution
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
