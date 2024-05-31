from flask import Flask, request, render_template, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import numpy as np
import pickle
import sqlite3
import os
import sklearn

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = os.urandom(16)
socketio = SocketIO(app)

# Print sklearn version
print(sklearn.__version__)

# Load models
dtr = pickle.load(open('dtr.pkl', 'rb'))

# Check if static and database folders exist
if not os.path.exists('static'):
    os.makedirs('static')

if not os.path.exists('database'):
    os.makedirs('database')

# SQLite3 setup
conn = sqlite3.connect('database/famx.db', check_same_thread=False)
c = conn.cursor()

# Create table if not exists
c.execute('''CREATE TABLE IF NOT EXISTS Famx(
            Username TEXT,
            Name TEXT,
            phone INTEGER,
            password TEXT
            )''')
conn.commit()

c.execute("INSERT INTO Famx (Username, Name, phone, password) VALUES ('Naveen123', 'Naveen', 1234567890, 'aaa')")
conn.commit()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Debug information (avoid in production)
        print(f"Attempting login with Username: {username}")

        # Query the Famx table for the provided username and password
        c.execute('SELECT * FROM Famx WHERE Username = ? AND password = ?', (username, password))
        user = c.fetchone()  # Fetch the first matching row

        # Print the fetched user information for debugging
        print(f"Fetched user: {user}")

        if user:
            # Set session variables
            session['logged_in'] = True
            session['username'] = username
            session['name'] = user[1]
            # If user exists and password matches, redirect to the home page
            return redirect(url_for('home'))
        else:
            # If user does not exist or password is incorrect, show error message
            return render_template('login.html', err='Please enter correct credentials...')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('user_login'))

@app.route('/home')
def home():
    if 'logged_in' in session:
        return render_template('home.html', name=session['name'])
    else:
        return redirect(url_for('user_login'))

@app.route('/contact')
def contact():
    if 'logged_in' in session:
        return render_template('contact.html', name=session.get('name'))
    else:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('user_login'))

@app.route('/aboutus')
def aboutus():
    if 'logged_in' in session:
        return render_template('aboutus.html', name=session.get('name'))
    else:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('user_login'))

@app.route("/predict", methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        # Convert form input to numeric values
        pH = float(request.form['pH'])
        rainfall = float(request.form['rainfall'])
        temperature = float(request.form['temperature'])
        Area_in_hectares = float(request.form['Area_in_hectares'])

        # Create features array
        features = np.array([[pH, rainfall, temperature, Area_in_hectares]])

        # Predict yield
        predicted_yield = dtr.predict(features)[0]

        prediction_message = f"The predicted crop yield is approximately {predicted_yield:.2f} tons per hectare."

        if 'logged_in' in session:
            return render_template('prediction.html',
                                   prediction_message=prediction_message,
                                   ph=pH,
                                   rainfall=rainfall,
                                   temperature=temperature,
                                   area_in_hectares=Area_in_hectares,
                                   name=session.get('name'))
        else:
            # If user is not logged in, redirect to login page
            return redirect(url_for('user_login'))
    else:
        if 'logged_in' in session:
            return render_template('prediction.html', name=session.get('name'))
        else:
            # If user is not logged in, redirect to login page
            return redirect(url_for('user_login'))


# List to store readings
readings = []

@app.route("/add_reading", methods=["POST"])
def add_reading():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    temperature = data.get("temperature")
    humidity = data.get("humidity")
    rain = data.get("rain")

    # Create a dictionary for the new reading
    new_reading = {
        "id": len(readings) + 1,
        "temperature": temperature,
        "humidity": humidity,
        "rain": rain,
        "currentdate": datetime.now().strftime("%Y-%m-%d"),
        "currentime": datetime.now().strftime("%H:%M:%S"),
        "device": "Device1"  # Example device name
    }

    # Add the new reading to the list
    readings.append(new_reading)

    # Notify clients about the new reading
    socketio.emit('new_reading', new_reading)

    return jsonify({"status": "success"}), 200

@app.route("/get_readings", methods=["GET"])
def get_readings():
    return jsonify(readings), 200

@app.route("/main")
def main():
    if 'logged_in' in session:
        return render_template("main.html", name=session.get('name'))
    else:
        return redirect(url_for('user_login'))

if __name__ == "__main__":
    try:
        socketio.run(app, host='0.0.0.0', port=8181, debug=True, allow_unsafe_werkzeug=True)
    finally:
        conn.close()
