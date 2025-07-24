from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, g
)
import sqlite3, os, functools
import fake_info

app = Flask(__name__,
            template_folder='build',
            static_folder='build/static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','dev')
app.config['DATABASE']   = os.path.join(app.root_path, 'sports_day.db')

USERS = {
    'admin': {'password':'adminpass','role':'admin'},
    'user':  {'password':'userpass', 'role':'user'}
}

# ——— Database helpers ———
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db',None)
    if db: db.close()

def init_db():
    db = get_db()
    db.executescript("""
      DROP TABLE IF EXISTS results;
      DROP TABLE IF EXISTS Events;
      DROP TABLE IF EXISTS Athletes;
      CREATE TABLE Events (
        event_id TEXT PRIMARY KEY,
        event    TEXT NOT NULL,
        sex      TEXT NOT NULL CHECK(sex IN('Boys','Girls')),
        grade    TEXT NOT NULL CHECK(grade IN('A','B','C'))
      );
      CREATE TABLE Athletes (
        athlete_id TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        house      TEXT NOT NULL,
        sex        TEXT NOT NULL CHECK(sex IN('Boys','Girls')),
        grade      TEXT NOT NULL CHECK(grade IN('A','B','C'))
      );
      CREATE TABLE results (
        result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        athlete_id  TEXT NOT NULL REFERENCES Athletes(athlete_id),
        event_id    TEXT NOT NULL REFERENCES Events(event_id),
        result      REAL NOT NULL
      );
    """)
    # now real sample data
    ath, ev, res = fake_info.sample(50)
    db.executemany("INSERT INTO Athletes VALUES (?,?,?,?,?)", ath)
    db.executemany("INSERT INTO Events    VALUES (?,?,?,?)", ev)
    db.executemany(
      "INSERT INTO results(athlete_id,event_id,result) VALUES (?,?,?)",
      res
    )
    db.commit()

if not os.path.exists(app.config['DATABASE']):
    with app.app_context():
        init_db()

# ——— Auth decorators ———
def login_required(f):
    @functools.wraps(f)
    def w(*a,**kw):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*a,**kw)
    return w

def admin_required(f):
    @functools.wraps(f)
    def w(*a,**kw):
        if session.get('role')!='admin':
            flash("Admins only","error")
            return redirect(url_for('list_results'))
        return f(*a,**kw)
    return w

# ——— Routes ———
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u,p = request.form['username'], request.form['password']
        user = USERS.get(u)
        if user and user['password']==p:
            session['username'],session['role']=u,user['role']
            flash(f"Welcome, {u}","success")
            return redirect(url_for('index'))
        flash("Bad credentials","error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out","info")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET','POST'])
@login_required
@admin_required
def add_result():
    db = get_db()
    if request.method=='POST':
        ath_id = request.form['athlete_id'].strip()
        ev_id  = request.form['event_id'].strip()
        # 1) parse result
        try:
            result = float(request.form['result'])
        except ValueError:
            flash("Result must be a number","error")
            return redirect(url_for('add_result'))

        # 2) validate IDs exist
        athlete = db.execute(
            "SELECT * FROM Athletes WHERE athlete_id=?", (ath_id,)
        ).fetchone()
        event = db.execute(
            "SELECT * FROM Events WHERE event_id=?", (ev_id,)
        ).fetchone()

        if athlete is None:
            flash("Athlete ID not found","error")
        elif event is None:
            flash("Event ID not found","error")
        # 3) validate sex/grade match
        elif athlete['sex']!=event['sex'] \
           or athlete['grade']!=event['grade']:
            flash("Sex/grade mismatch between athlete & event","error")
        else:
            db.execute(
              "INSERT INTO results(athlete_id,event_id,result) VALUES (?,?,?)",
              (ath_id, ev_id, result)
            )
            db.commit()
            flash("Result added","success")
            return redirect(url_for('list_results'))

    # GET or failed POST re-displays form
    return render_template('add_result.html')




   

# === List results ===
@app.route('/results')
@login_required
def list_results():
    db = get_db()
    
    # Get filter parameters from request
    event_filter = request.args.get('event', '').strip()
    athlete_id = request.args.get('athlete', '').strip()
    sex_filter = request.args.get('sex', '')
    grade_filter = request.args.get('grade', '')

    # Base SQL query - now including result_id
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
    
    # Apply filters
    if event_filter:
        sql += " AND e.event = ?"
        params.append(event_filter)
    if athlete_id:
        sql += " AND a.athlete_id = ?"
        params.append(athlete_id)
    if sex_filter:
        sql += " AND a.sex = ?"
        params.append(sex_filter)
    if grade_filter:
        sql += " AND a.grade = ?"
        params.append(grade_filter)
    sql += """
      ORDER BY e.event,
        CASE
          WHEN e.event LIKE '%meters%' OR e.event LIKE '%run%' THEN r.result
          ELSE -r.result
        END
    """
    # Execute query
    if params:
        rows = db.execute(sql, tuple(params)).fetchall()
    else:
        rows = db.execute(sql).fetchall()
    
    # Group results by event and category, now including result_id
    grouped = {}
    for r in rows:
        key = (r['event_id'], r['event'], f"{r['event_sex']} {r['event_grade']}")
        if key not in grouped:
            grouped[key] = []
        grouped[key].append({
            'result_id': r['result_id'],
            'athlete_id': r['athlete_id'],
            'name': r['name'],
            'house': r['house'],
            'result': r['result']
        })
    sorted_groups = sorted(grouped.items(), key=lambda x: x[0][0])
    # Get filter options
    events = db.execute(
        "SELECT DISTINCT event FROM Events ORDER BY event"
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



# — edit/delete (admin only) —
@app.route('/results/edit/<int:rid>', methods=['GET','POST'])
@login_required
@admin_required
def edit_result(rid):
    db = get_db()
    # Get the full result details including athlete and event info
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

# — list athletes / events (admin only) —
@app.route('/athletes')
@login_required
@admin_required
def list_athletes():
    house = request.args.get('house','')
    sex   = request.args.get('sex','')
    grade = request.args.get('grade','')
    q = "SELECT * FROM Athletes"
    wf=[]; ps=[]
    if house: 
        wf.append("house=?")
        ps.append(house)
    if sex:   
        wf.append("sex=?")
        ps.append(sex)
    if grade: 
        wf.append("grade=?")
        ps.append(grade)
    if wf:    
        q += " WHERE " + " AND ".join(wf)
    db = get_db()
    ath = db.execute(q,ps).fetchall()
    houses= db.execute("SELECT DISTINCT house FROM Athletes").fetchall()
    grades= db.execute("SELECT DISTINCT grade FROM Athletes ORDER BY grade").fetchall()
    db.close()
    return render_template('list_athletes.html',
            athletes=ath,houses=houses,sexes=['Boys','Girls'],
            grades=grades,current_filters={'house':house,'sex':sex,'grade':grade}
    )
    pass

@app.route('/events')
@login_required
@admin_required
def list_events():
    sex   = request.args.get('sex','')
    grade = request.args.get('grade','')
    q="SELECT * FROM Events"; wf=[]; ps=[]
    if sex:   
        wf.append("sex=?")
        ps.append(sex)
    if grade: 
        wf.append("grade=?")
        ps.append(grade)
    if wf:    
        q+=" WHERE "+ " AND ".join(wf)
    db = get_db()
    ev = db.execute(q,ps).fetchall()
    db.close()
    return render_template('list_events.html',
            events=ev,sexes=['Boys','Girls'],grades=['A','B','C'],
            current_filters={'sex':sex,'grade':grade}
    )
    pass

@app.route('/clear_results', methods=['GET', 'POST'])
@login_required
@admin_required
def clear_results():
    if request.method == 'POST':
        try:
            db = get_db()
            db.execute("DELETE FROM results")
            db.commit()
            flash("All results have been cleared successfully", "success")
            return redirect(url_for('list_results'))
        except Exception as e:
            flash(f"Error clearing results: {str(e)}", "error")
            return redirect(url_for('list_results'))
    
    # GET request shows confirmation page
    return render_template('confirm_clear.html')

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
