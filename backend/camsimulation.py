import cv2
import threading
import time
from flask import Flask, Response

app=Flask(__name__)


camera=cv2.VideoCapture(0, cv2.CAP_DSHOW)        #CAP_DSHOW
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

latestframebytes=None
lock=threading.Lock()


def cameracapturethread():
    global latestframebytes
    encodeparameters=[int(cv2.IMWRITE_JPEG_QUALITY), 95]

    while True:
        success,frame=camera.read()
        if not success:
            time.sleep(0.01)    
            continue

        ret,buffer=cv2.imencode('.jpg',frame ,encodeparameters)
        if ret:
            with lock:
                latestframebytes=buffer.tobytes()
        time.sleep(0.03)

threading.Thread(target=cameracapturethread, daemon=True).start()       #starting the camera capture thread
        
#read frames from camera, resizes them, and encodes to MJPEG
def generateframes():
    while True:
        with lock:
            framebytes=latestframebytes

        if framebytes is None:
            time.sleep(0.01)
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + str(len(framebytes)).encode() + b'\r\n\r\n'
            + framebytes + b'\r\n'
        )
        time.sleep(0.033)


@app.route('/')
def videofeed():                    
    return Response(generateframes(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("CIPHER Camera Simulator running...")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)