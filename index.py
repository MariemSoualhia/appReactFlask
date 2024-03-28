from flask import Flask, Response
import cv2
import threading
import subprocess
import numpy as np
import time

# Fréquence d'images cible
target_fps = 30
app = Flask(__name__)
lock = threading.Lock()

# Commande ffmpeg pour lire le flux RTSP et le convertir en un flux MJPEG
# Commande ffmpeg pour lire le flux de la caméra PC et le convertir en un flux MJPEG
ffmpeg_command = [
    'ffmpeg',
    '-i', 'rtsp://rtspstream:9f8f7639a88af813b1bbfc507f8d9c63@zephyr.rtsp.stream/movie',
   '-vf', 'fps=25',
    '-f', 'image2pipe',
    '-pix_fmt', 'rgb24',
    '-vcodec', 'rawvideo',
    '-']

process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

target_fps =5

def generate():
    global lock
    last_frame_time = time.time()
    frame_interval = 1 / target_fps

    while True:
        # Calculer le temps écoulé depuis le dernier frame
        elapsed_time = time.time() - last_frame_time

        if elapsed_time < frame_interval:
            # Attendre jusqu'à ce que le prochain frame soit dû
            time.sleep(frame_interval - elapsed_time)

        # Lire les données d'image depuis la sortie standard de ffmpeg
        raw_frame = process.stdout.read(640 * 480 * 3)
        if len(raw_frame) != 640 * 480 * 3:
            break

        # Convertir les données brutes en un tableau numpy utilisable
        frame = np.frombuffer(raw_frame, dtype=np.uint8)
        frame = frame.reshape((480, 640, 3))

        with lock:
            # Redimensionner le frame à une taille standard (vous pouvez ajuster ceci)
            frame = cv2.resize(frame, (640, 480))

            # Encoder le frame en JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        # Mettre à jour le temps du dernier frame
        last_frame_time = time.time()
def cleanup():
    process.stdout.close()
    process.stderr.close()

@app.route('/stream', methods=['GET'])
def stream():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

# Nettoyer les ressources à la fin
cleanup()
