"""File server"""
import uuid
import io
import mimetypes
from functools import wraps
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

class DataStore:
    """simple in-memory filestore, fix bugs as needed"""
    def __init__(self):
        self.users = {}
        self.user_files = {}

    def get_user_file_names(self, user):
        """gets a users credentials from the data store"""
        if self.user_files[user]:
            return [file_name for file_name in self.user_files[user].keys()]
        else:
            return []

    def get_user_creds(self, user):
        """gets a users credentials from the data store"""
        return self.users.get(user, None)

    def put_user_credentials(self, user, cred):
        """saves a users credentials to the data store"""
        self.users[user] = cred

    def get_user_file(self, user, filename):
        """gets a users file by name, returns None if user or file doesn't exist"""
        try:
            return self.user_files[user][filename]
        except:
            return None

    def put_user_file(self, user, filename, data):
        """stores file data for user/file assumes unique fn"""
        if user in self.user_files:
            self.user_files[user][filename] = io.BytesIO(data)
        else:
            self.user_files[user] = {filename: io.BytesIO(data)}

    def delete_user_file(self, user, filename):
        """delete a users file"""
        try:
            del self.user_files[user][filename]
            return True
        except:
            return False

def basic_auth_check(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        token = request.headers.get('X-Session', None)
        if token and token in SESSION_MANAGER:
            r = f(SESSION_MANAGER[token], *args, **kwargs)
            return r
        else:
            return('', 403)
    return wrapped


db = DataStore()
SESSION_MANAGER = {}

@app.route('/register', methods=['POST'])
def register():
    """register a user with username and password"""
    if not request.is_json:
        return('', 400)

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if db.get_user_creds(username) is not None:
        resp = jsonify({'error': 'Username already taken'})
        resp.status_code = 400
        return resp

    if username is None or \
       password is None or \
       len(username) <= 3 or len(username) > 20 or \
       not str(username).isalnum() or \
       len(password) < 8:
        resp = jsonify({'error': 'Username or Password do not abide by given rules'})
        resp.status_code = 400
        return resp
    db.put_user_credentials(username, password)
    return('', 204)


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return('', 400)

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if username is not None and \
       password is not None and \
       db.get_user_creds(username) is not None and \
       db.get_user_creds(username) == password:
        token = uuid.uuid4()
        resp = jsonify({'token': token})
        resp.status_code = 200
        SESSION_MANAGER[str(token)] = username
        return resp
    else:
        resp = jsonify({'error': 'Login Failed'})
        resp.status_code = 403
        return resp


@app.route('/files/<filename>', methods=['PUT'])
@basic_auth_check
def uplaod_file(user, filename):
    db.put_user_file(user, filename, request.get_data())
    return('Status: 201 Created\nLocation: /files/%s' % filename, 201)


@app.route('/files/<filename>', methods=['GET'])
@basic_auth_check
def get_file(user, filename):
    user_file = db.get_user_file(user, filename)
    if user_file:
        file_mime = mimetypes.guess_type(filename)[0]
        return send_file(user_file, mimetype=file_mime)
    else:
        return('', 404)


@app.route('/files/<filename>', methods=['DELETE'])
@basic_auth_check
def delete_file(user, filename):
    if db.delete_user_file(user, filename):
        return('', 204)
    else:
        return('', 404)

@app.route('/files', methods=['GET'])
@basic_auth_check
def get_files_list(user):
    resp = jsonify(db.get_user_file_names(user))
    resp.status_code = 200
    return resp

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
