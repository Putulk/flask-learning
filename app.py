from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json

load_dotenv()

mongo_uri = os.getenv('MONGO_URI')

client = MongoClient(mongo_uri)
db = client.python_learning
collection = db.registar
app = Flask(__name__)
DATA_FILE = 'data.json'


def read_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []
        

@app.route('/api', methods=['POST'])
def add_data():
    new_entry = request.get_json()  # expects JSON body
    if not new_entry or 'name' not in new_entry:
        return jsonify({'error': 'Invalid data. "name" field required.'}), 400

    data = read_data()

    # auto-increment ID
    new_entry['id'] = data[-1]['id'] + 1 if data else 1
    data.append(new_entry)
    write_data(data)

    return jsonify({'message': 'Data added successfully', 'data': new_entry}), 201


@app.route('/api', methods=['GET'])
def get_data():
    try:
        # Read data from file
        with open('data.json', 'r') as f:
            data = json.load(f)
        # Return JSON response
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Data file not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding JSON file"}), 500

@app.route('/')
def home(): 
    day_of_week = datetime.now().strftime('%A')
    print(f"Today is {day_of_week}")
    return render_template('index.html', day_of_week = day_of_week, datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@app.route('/submit', methods=['POST'])
def submit():
    formdata = dict(request.form)
    print("Received form data:", formdata)  # Debug print
    result = collection.insert_one(formdata)
    print("Inserted ID:", result.inserted_id)  # Debug print
    return jsonify({"status": "success", "inserted_id": str(result.inserted_id)})

@app.route('/view', methods=['GET'])
def view():
    data = list(collection.find({}, {'_id': 0}))
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)