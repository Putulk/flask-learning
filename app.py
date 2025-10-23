from flask import Flask, request, jsonify, render_template
from datetime import datetime
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json
from bson import ObjectId
import uuid
import hashlib

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
        
def _serialize_doc(doc):
    """Convert ObjectId (and nested ObjectId) to str for JSON response."""
    if isinstance(doc, list):
        return [_serialize_doc(d) for d in doc]
    if not isinstance(doc, dict):
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, dict):
            out[k] = _serialize_doc(v)
        elif isinstance(v, list):
            out[k] = [_serialize_doc(i) for i in v]
        else:
            out[k] = v
    return out


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

@app.route('/items', methods=['GET'])
def get_items():
    try:
        with open('items.json', 'r') as f:
            items = json.load(f)
        return jsonify(items)
    except FileNotFoundError:
        return jsonify({"error": "Items file not found"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Error decoding JSON file"}), 500

@app.route('/submittodoitem', methods=['GET', 'POST'])
def submit_todo_item():
    if request.method == 'GET':
        return redirect(url_for('todo'))  # optional: redirect browser GETs to the form

    # Accept form-encoded POST from frontend form (or JSON)
    if request.is_json:
        payload = request.get_json()
        item_name = payload.get('itemName')
        item_description = payload.get('itemDescription')
        item_id = payload.get('itemId')
        item_uuid = payload.get('itemUUID')
        item_hash = payload.get('itemHash')
    else:
        item_name = request.form.get('itemName')
        item_description = request.form.get('itemDescription')
        item_id = request.form.get('itemId')
        item_uuid = request.form.get('itemUUID')
        item_hash = request.form.get('itemHash')

    if not item_name or not item_description:
        return jsonify({"error": "itemName and itemDescription are required"}), 400

    # generate fallbacks if missing
    if not item_id:
        item_id = int(datetime.utcnow().timestamp())
    if not item_uuid:
        item_uuid = str(uuid.uuid4())
    if not item_hash:
        h = hashlib.sha256()
        h.update(f"{item_name}|{item_description}|{item_uuid}".encode('utf-8'))
        item_hash = h.hexdigest()

    # insert into MongoDB collection 'todo_items'
    todo_collection = db.todo_items
    doc = {
        "itemId": item_id,
        "itemUUID": item_uuid,
        "itemHash": item_hash,
        "itemName": item_name,
        "itemDescription": item_description,
        "created_at": datetime.utcnow().isoformat()
    }
    result = todo_collection.insert_one(doc)

    # serialize to remove ObjectId (PyMongo adds _id to `doc` in-place)
    serialized = _serialize_doc(doc)
    return jsonify({"status": "success", "inserted_id": str(result.inserted_id), "item": serialized}), 201

if __name__ == '__main__':
    app.run(debug=True)