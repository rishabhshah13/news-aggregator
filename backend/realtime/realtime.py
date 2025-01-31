#!/usr/bin/env python3
"""
realtime.py - Real-time Communication Module
This example uses Flask-SocketIO to enable real-time updates.
"""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return "Real-time communication server running."

@socketio.on('connect')
def test_connect():
    emit('message', {'data': 'Connected to real-time server.'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=6000)
