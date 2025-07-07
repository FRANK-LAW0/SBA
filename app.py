from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__, template_folder='build')


# Initialize the database
def init_db():
    conn = sqlite3.connect('sports_day.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            athlete_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            result REAL NOT NULL
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
        event_name = request.form['event_name']
        result = float(request.form['result'])
        
        conn = sqlite3.connect('sports_day.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO results (athlete_id, event_name, result)
            VALUES (?, ?, ?)
        ''', (athlete_id, event_name, result))
        conn.commit()
        conn.close()
        
        return redirect(url_for('index'))
    
    return render_template('add_event.html')

if __name__ == '__main__':
    app.run(debug=True)
