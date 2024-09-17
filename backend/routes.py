from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    """Return health status of the app."""
    return jsonify({"status": "OK"}), 200

@app.route("/count", methods=["GET"])
def count():
    """Return the total number of songs in the MongoDB collection."""
    count = db.songs.count_documents({})  # Count all documents in the 'songs' collection
    return jsonify({"count": count}), 200

######################################################################
# SONGS ENDPOINT
######################################################################
@app.route("/song", methods=["GET"])
def songs():
    """Return all songs from the MongoDB collection."""
    # Fetch all songs from the MongoDB collection
    songs = list(db.songs.find({}))  # Convert the cursor to a list
    return jsonify({"songs": parse_json(songs)}), 200  # Return the songs in JSON format

######################################################################
# GET SONG BY ID ENDPOINT
######################################################################
@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Return a song by its id."""
    # Search for the song in the MongoDB collection
    song = db.songs.find_one({"id": id})

    # If song not found, return 404 with a message
    if not song:
        return jsonify({"message": f"song with id {id} not found"}), 404

    # Return the found song as JSON with a 200 status
    return jsonify(parse_json(song)), 200

######################################################################
# CREATE SONG ENDPOINT
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    data = request.get_json()  # Extract JSON data from the request
    song_id = data.get('id')   # Get song ID
    
    # Check if the song ID already exists
    if db.songs.find_one({"id": song_id}):
        return jsonify({"Message": f"song with id {song_id} already present"}), 302
    
    # Insert the new song
    result = db.songs.insert_one(data)
    
    # Convert the inserted song to a serializable format
    data['_id'] = str(result.inserted_id)  # Convert ObjectId to string
    
    return jsonify(data), 201

def serialize_document(doc):
    """Convert MongoDB document to a serializable format"""
    if doc:
        doc["_id"] = str(doc["_id"])  # Convert ObjectId to string
    return doc

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update an existing song by id"""
    
    # Extract song data from the request body
    data = request.get_json()
    
    # Find the song by id
    song = db.songs.find_one({"id": id})
    
    if song:
        # Update the song with the incoming data
        db.songs.update_one({"id": id}, {"$set": data})
        
        # Return the updated song data
        updated_song = db.songs.find_one({"id": id})
        return jsonify({"song": serialize_document(updated_song)}), 200
    else:
        # Return 404 if the song doesn't exist
        return jsonify({"message": "song not found"}), 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete a song by id"""
    
    # Attempt to delete the song from the database
    result = db.songs.delete_one({"id": id})
    
    if result.deleted_count == 1:
        # Song was successfully deleted
        return "", 204
    else:
        # Song was not found
        return jsonify({"message": "song not found"}), 404
