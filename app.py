from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

# Initialize the database (run once)
def init_db():
    conn = sqlite3.connect('sports_day.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS result (
            result_id integer primary key AUTOINCREMENT,
            athlete_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            result double NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()  # Ensure the table exists

# Route to display the form
@app.route('/')
def show_form():
    return render_template('add_event.html')

# Route to handle form submission
@app.route('/submit_result', methods=['POST'])
def submit_result():
    if request.method == 'POST':
        # Step 1: Get form data
        athlete_id = request.form['athlete_id']
        event_name = request.form['event_name']
        result = request.form['result']

        # Step 2: Connect to the database
        conn = sqlite3.connect('sports_day.db')
        cursor = conn.cursor()

        # Step 3: Insert data into the 'result' table
        cursor.execute('''
            INSERT INTO result (athlete_id, event_name, result)
            VALUES (?, ?, ?)
        ''', (athlete_id, event_name, result))

        # Step 4: Commit and close
        conn.commit()
        conn.close()

        # Step 5: Redirect to a success page (or back to form)
        return redirect(url_for('show_form'))

@app.route('/view_results')
def view_results():
    conn = sqlite3.connect('sports_day.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM result")
    results = cursor.fetchall()
    conn.close()
    return {"data": results}

if __name__ == '__main__':
    app.run(debug=True)
    print("RESULTS:")
    print(view_results)
