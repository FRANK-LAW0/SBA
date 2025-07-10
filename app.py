from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, os, functools
from fake_info import sample

app = Flask(__name__, template_folder='build', static_folder='build/static')
app.secret_key = 'TH12 1s tHe sEcr37'

USERS = {
    'admin': {'password':'adminpass','role':'admin'},
    'user':  {'password':'userpass', 'role':'user'}
}

def get_db():
    conn = sqlite3.connect('sports_day.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # drop & recreate
    cursor.executescript("""
    DROP TABLE IF EXISTS results;
    DROP TABLE IF EXISTS Events;
    DROP TABLE IF EXISTS Athletes;

    CREATE TABLE Events (
      event_id TEXT PRIMARY KEY,
      event    TEXT NOT NULL,
      sex      TEXT NOT NULL,
      grade    TEXT NOT NULL,
      CHECK(sex IN('Boys','Girls') AND grade IN('A','B','C'))
    );

    CREATE TABLE Athletes (
      athlete_id TEXT PRIMARY KEY,
      name       TEXT NOT NULL,
      house      TEXT NOT NULL,
      sex        TEXT NOT NULL,
      grade      TEXT NOT NULL,
      CHECK(sex IN('Boys','Girls') AND grade IN('A','B','C'))
    );

    CREATE TABLE results (
      result_id   INTEGER PRIMARY KEY AUTOINCREMENT,
      athlete_id  TEXT NOT NULL,
      event_id    TEXT NOT NULL,
      result      REAL NOT NULL
    );
    """)
    
    sample_athletes, sample_events, sample_results = sample(75)
    #print(sample_results)
    cursor.executemany("INSERT INTO Events VALUES (?,?,?,?)", sample_events)
    cursor.executemany("INSERT INTO Athletes VALUES (?,?,?,?,?)", sample_athletes)
    cursor.executemany("INSERT INTO results (athlete_id,event_id,result) VALUES (?,?,?)", sample_results)
    
    conn.commit()
    conn.close()

if not os.path.exists('sports_day.db'):
    init_db()

# — decorators —
def login_required(f):
    @functools.wraps(f)
    def wrapped(*args,**kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args,**kwargs)
    return wrapped

def admin_required(f):
    @functools.wraps(f)
    def wrapped(*args,**kwargs):
        if session.get('role')!='admin':
            flash("Admins only", "error")
            return redirect(url_for('list_results'))
        return f(*args,**kwargs)
    return wrapped

# — auth routes —
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u = request.form['username']
        p = request.form['password']
        user = USERS.get(u)
        if user and user['password']==p:
            session['username'] = u
            session['role']     = user['role']
            flash(f"Welcome, {u}", "success")
            return redirect(url_for('index'))
        flash("Bad credentials", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('login'))

# — main dashboard —
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# — add result (admin only, free-form IDs) —
@app.route('/add', methods=['GET','POST'])
@login_required
@admin_required
def add_result():
    if request.method=='POST':
        ath = request.form['athlete_id'].strip()
        ev  = request.form['event_id'].strip()
        try:
            res = float(request.form['result'])
            db = get_db()
            db.execute(
              "INSERT INTO results(athlete_id,event_id,result) VALUES (?,?,?)",
              (ath,ev,res)
            )
            db.commit(); db.close()
            flash("Result added", "success")
            return redirect(url_for('list_results'))
        except ValueError:
            flash("Result must be a number", "error")
    return render_template('add_event.html')

# — list results (any logged-in) —
@app.route('/results')
@login_required
def list_results():
    eflt = request.args.get('event','')
    afl  = request.args.get('athlete','').strip()
    gflt = request.args.get('grade','')

    sql = """
      SELECT r.result_id,
             a.athlete_id,a.name,a.house,a.grade AS athlete_grade,
             e.event_id,e.event,e.sex,e.grade AS event_grade,
             r.result
      FROM results r
      JOIN Athletes a ON a.athlete_id=r.athlete_id
      JOIN Events   e ON e.event_id  =r.event_id
      WHERE a.sex=e.sex AND a.grade=e.grade
    """
    params = []
    if eflt:
        sql += " AND e.event_id=?";   params.append(eflt)
    if afl:
        sql += " AND a.athlete_id=?"; params.append(afl)
    if gflt:
        sql += " AND a.grade=?";      params.append(gflt)
    sql += """
      ORDER BY e.event,
        CASE 
          WHEN e.event LIKE '%meters%' OR e.event LIKE '%run%' THEN r.result
          ELSE -r.result
        END
    """

    db = get_db()
    rows = db.execute(sql, params).fetchall()
    # group
    grouped = {}
    for r in rows:
        key = (r['event_id'],r['event'],f"{r['sex']} {r['event_grade']}")
        grouped.setdefault(key,[]).append(r)

    events   = db.execute("SELECT DISTINCT event_id,event,sex,grade FROM Events ORDER BY event").fetchall()
    grades   = db.execute("SELECT DISTINCT grade FROM Athletes ORDER BY grade").fetchall()
    db.close()
    return render_template('list_results.html',
            grouped_results=grouped,
            events=events,
            grades=grades,
            current_filters={'event':eflt,'athlete':afl,'grade':gflt}
    )

# — edit/delete (admin only) —
@app.route('/results/edit/<int:rid>', methods=['GET','POST'])
@login_required
@admin_required
def edit_result(rid):
    db = get_db()
    row = db.execute("SELECT * FROM results WHERE result_id=?", (rid,)).fetchone()
    if not row:
        db.close(); flash("Not found","error")
        return redirect(url_for('list_results'))
    if request.method=='POST':
        ath = request.form['athlete_id'].strip()
        ev  = request.form['event_id'].strip()
        try:
            res = float(request.form['result'])
            db.execute(
              "UPDATE results SET athlete_id=?,event_id=?,result=? WHERE result_id=?",
              (ath,ev,res,rid)
            )
            db.commit(); db.close()
            flash("Updated","success")
            return redirect(url_for('list_results'))
        except ValueError:
            flash("Result must be number","error")
    db.close()
    return render_template('edit_result.html', row=row)

@app.route('/results/delete/<int:rid>')
@login_required
@admin_required
def delete_result(rid):
    db = get_db()
    db.execute("DELETE FROM results WHERE result_id=?", (rid,))
    db.commit(); db.close()
    flash("Deleted","info")
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
    if house: wf.append("house=?"); ps.append(house)
    if sex:   wf.append("sex=?");   ps.append(sex)
    if grade: wf.append("grade=?"); ps.append(grade)
    if wf:    q += " WHERE " + " AND ".join(wf)
    db = get_db()
    ath = db.execute(q,ps).fetchall()
    houses= db.execute("SELECT DISTINCT house FROM Athletes").fetchall()
    grades= db.execute("SELECT DISTINCT grade FROM Athletes ORDER BY grade").fetchall()
    db.close()
    return render_template('list_athletes.html',
            athletes=ath,houses=houses,sexes=['Boys','Girls'],
            grades=grades,current_filters={'house':house,'sex':sex,'grade':grade}
    )

@app.route('/events')
@login_required
@admin_required
def list_events():
    sex   = request.args.get('sex','')
    grade = request.args.get('grade','')
    q="SELECT * FROM Events"; wf=[]; ps=[]
    if sex:   wf.append("sex=?");   ps.append(sex)
    if grade: wf.append("grade=?"); ps.append(grade)
    if wf:    q+=" WHERE "+ " AND ".join(wf)
    db = get_db()
    ev = db.execute(q,ps).fetchall()
    db.close()
    return render_template('list_events.html',
            events=ev,sexes=['Boys','Girls'],grades=['A','B','C'],
            current_filters={'sex':sex,'grade':grade}
    )

if __name__=='__main__':
    app.run(debug=True)
