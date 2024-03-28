# Import necessary modules
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for
from aiortc import RTCPeerConnection, RTCSessionDescription
import cv2
import json
import uuid
import asyncio
import logging
import time
from flask_socketio import SocketIO, emit, join_room
import os


# Create a Flask app instance
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
# Set to keep track of RTCPeerConnection instances
pcs = set()
# Metered Secret Key
METERED_SECRET_KEY = os.environ.get("METERED_SECRET_KEY")
# Metered Domain
METERED_DOMAIN = os.environ.get("METERED_DOMAIN")
# Function to generate video frames from the camera
def generate_frames():
    camera = cv2.VideoCapture(1)
    while True:
        start_time = time.time()
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Concatenate frame and yield for streaming
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') 
            elapsed_time = time.time() - start_time
            logging.debug(f"Frame generation time: {elapsed_time} seconds")

# Route to render the HTML template
@app.route('/')
def index():
    return render_template('index.html')
    # return redirect(url_for('video_feed')) #to render live stream directly

# Asynchronous function to handle offer exchange
async def offer_async():
    try:
        params = request.get_json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        # Create an RTCPeerConnection instance
        pc = RTCPeerConnection()

        # Generate a unique ID for the RTCPeerConnection
        pc_id = "PeerConnection(%s)" % uuid.uuid4()
        pc_id = pc_id[:8]

        # Create and set the local description
        await pc.createOffer(offer)
        await pc.setLocalDescription(offer)

        # Prepare the response data with local SDP and type
        response_data = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

        return jsonify(response_data)

    except Exception as e:
        # Handle any exceptions and return a 400 error
        return jsonify({"error": str(e)}), 400


# Wrapper function for running the asynchronous offer function
def offer():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    future = asyncio.run_coroutine_threadsafe(offer_async(), loop)
    return future.result()

# Route to handle the offer request
@app.route('/offer', methods=['POST'])
def offer_route():
    return offer()

# Route to stream video frames
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Run the Flask app
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=9000)