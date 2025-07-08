from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__, template_folder='build', static_folder='build/static')


# Initialize the database
def init_db():
    conn = sqlite3.connect('sports_day.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            result REAL NOT NULL,
            foreign key (athlete_id) references Athletes(athlete_id),
            foreign key (event_id) references Events(event_id),
            unique(athlete_id, event_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Events (
            event_id text PRIMARY KEY,
            event_name TEXT NOT NULL,
            sex text NOT NULL,
            grade text not null,
            check (sex in ('M', 'F') and grade in ('A', 'B', 'C'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Athletes (
            athlete_id TEXT primary key,
            house text not null,
            sex text not null,
            grade text not null,
            check (sex in ('M', 'F') and grade in ('A', 'B', 'C'))
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect('sports_day.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM results")
    results = cursor.fetchall()
    conn.close()
    return render_template('index.html', results=results)

@app.route('/add', methods=['GET', 'POST'])
def add_result():
    if request.method == 'POST':
        athlete_id = request.form['athlete_id']
        event_id = request.form['event_id']
        result = float(request.form['result'])
        
        conn = sqlite3.connect('sports_day.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO results (athlete_id, event_id, result)
            VALUES (?, ?, ?)
        ''', (athlete_id, event_id, result))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('add_event.html')

# Route for managing Athletes and Events
@app.route('/athletes')
def list_athletes():
    conn = ssqlite3.connect('sports_day.db')
    athletes = conn.execute("SELECT * FROM Athletes").fetchall()
    conn.close()
    return render_template('list_athletes.html', athletes=athletes)

@app.route('/events')
def list_events():
    conn = ssqlite3.connect('sports_day.db')
    events = conn.execute("SELECT * FROM Events").fetchall()
    conn.close()
    return render_template('list_events.html', events=events)

if __name__ == '__main__':
    app.run(debug=True)
