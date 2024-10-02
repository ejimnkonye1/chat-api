from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from flask import Flask, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import secrets
import datetime
from flask_socketio import SocketIO,emit

uri = "mongodb+srv://ejimnkonyeonyedika:nPs0iXR5gyPvxZG2@cluster0.rdsyp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
app = Flask(__name__)
CORS(app)

secret_key = secrets.token_urlsafe(16)
app.secret_key = secret_key
socketio = SocketIO(app, cors_allowed_origins="*")

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
 print(f'Error connecting to MongoDb: {e}')

db = client['database1']
user_collection = db['users']
messages_collection = db['messages']
@app.route('/')
def index():
   return 'py is running'
@app.route('/register', methods=['POST'])
def register():
   # make the data a json
   data = request.get_json()
   
   username = data.get('username')
   password = data.get('password')

   if not username or not password:
      return jsonify({"error": "username and password is required"}), 400
   if len(password) < 8 :
      return jsonify({'error': 'password should be 8 and above'}),400
   #check if username is taken
   if user_collection.find_one({'username':username}):
      return jsonify({'error':'username is already taken'}), 401
   
  # hased the password
   hased_password = generate_password_hash(password)
   #store username and hased password in users collection
   user_collection.insert_one({
      'username': username,
       'password': hased_password
   })
   user = user_collection.find_one({'username':username})
   session['user_id'] = str(user['_id'])
   session['username'] = user['username'] 
   return jsonify({'message':'user succesfully registered', 'username':user['username'], 'user_id':str(user['_id'])}),201
@app.route('/login', methods=['POST'])
def Login():
   data = request.get_json()
   username = data.get('username')
   password = data.get('password')

   if not username or not password:
      return jsonify({"error": "username and password is required"}), 400
   # find user in db
   user = user_collection.find_one({'username':username})
   #check if user exists
   if not user:
      return jsonify({'error': 'user not found'}), 404
   #check the password the user entered is same with the hashed password
   if check_password_hash(user['password'], password):
      session['user_id'] = str(user['_id']) 
      session['username'] = user['username']
      return jsonify({'message':'user exists logging in now', 'username': user['username'], 'user_id': str(user['_id'])}),200
   else:
      return jsonify({'error': 'invalid password'}),401
   
# @app.route('/sendmessage', methods=["POST"])
@socketio.on('message')
def sendmessage(data):
   print('recieved message', data)
   sender_username = data.get('sender_username')
   messages = data.get('message')

   #find user
   sender_user = user_collection.find_one({"username":sender_username})   

   if not sender_user :
      emit({"error": 'invalid sender ' }), 400
   # find all user expect sender
   receiver_user = list(user_collection.find({'username':{'$ne': sender_username} }))
   if not receiver_user :
      emit({'error':'others users not found'}),400
   #send mes to all users
   for receiver in receiver_user:
      messages_collection.insert_one({
       'senderId': sender_user['_id'],
       'receiverId': receiver['_id'],
       "messages": messages,
        "timestamp":datetime.datetime.now(datetime.timezone.utc)
      
    })
       # Emit the message using Socket.IO
   emit('message', {
    'sender_username': sender_username,
    'message': messages,
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
}, to='/')

   
   emit({'message':'message successfully sent'}),201
@socketio.on('fetchmessages')
def fetchmessage(data):
    senderId = data.get('senderId')
    sender_user = user_collection.find_one({'username': senderId})
    if not sender_user:
        emit({"error": 'invalid user'}, room=request.sid)
        return

    # Find all messages in the collection
    messages = list(messages_collection.find({}))
    if not messages:
        emit({'error': 'Messages not found'}, room=request.sid)
        return

    for message in messages:
        message['_id'] = str(message['_id'])
        message['senderId'] = str(message['senderId'])
        message['receiverId'] = str(message['receiverId'])
        if 'timestamp' in message:
            message['timestamp'] = message['timestamp'].isoformat()
        else:
            message['timestamp'] = 'none'

    # Emit fetched messages to the specific client
    emit("fetchMessagesResponse", {"message": messages}, room=request.sid)

@socketio.on('connect')
def handle_connect():
    print('A user connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('A user disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
