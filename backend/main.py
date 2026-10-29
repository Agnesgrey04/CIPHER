import cv2
import asyncio
import threading
import time
import datetime
import queue
import os
import numpy as np
from collections import deque
from fastapi.responses import FileResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

from auth.authroute import router as authrouter 
from client.clientroute import router as clientrouter
from admin.adminroute import router as adminrouter

app=FastAPI(title="CIPHER")

#other routes
app.include_router(authrouter)
app.include_router(clientrouter)
app.include_router(adminrouter)

orgins=["http://localhost:5173", "http://localhost:5174"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cameraurl="http://127.0.0.1:5000/"      #url of the live stream. code from camsimulation.py
currentframebytes=None
maineventloop=None

preeventtime=8
posteventtime=8
preeventframes=int(preeventtime * 15.0)      #seconds * target FPS
posteventframes=int(posteventtime * 15.0)      #seconds * target FPS
framebuffer=deque(maxlen=preeventframes)
isrecording=False
posteventcounter=0
videowriter=None
lastrecordingendtime=0.0
activeincidentpath=None
cooldowntime=5

#for incident clips storage
os.makedirs("incidents", exist_ok=True)

rawframequeue=queue.Queue(maxsize=1)

'''modelpath=hf_hub_download(repo_id="Subh775/Threat-Detection-YOLOv8n", filename="weights/best.pt")
model=YOLO(modelpath)    #initializing model'''

model=YOLO("yolov8s.pt")

class ContinuousRecorder:
    def __init__(self, outputdirectory: str="recordings/", segmentduration: int=120, fps: float=30.0):
        self.outputdirectory=outputdirectory
        self.segmentduration=segmentduration
        self.fps=fps
        self.writer=None
        self.currentsegemntstart=0.0
        self.framesize=None
        os.makedirs(outputdirectory, exist_ok=True)

    def writeframes(self,frame):
        currenttime=time.time()

        #initialize segment if not already started or rotate segment if the segment time is reacheed
        if self.writer is None or (currenttime-self.currentsegemntstart>=self.segmentduration):
            self._rotatesegment(frame,currenttime)

        if self.writer is not None:
            self.writer.write(frame)

    def _rotatesegment(self,frame,currenttime):
        if self.writer is not None:
            self.writer.release()

        height,width,_=frame.shape               #set video height and width same as labelled video height and width
        timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")         #set timestamp in the video recording
        archivepath=os.path.join(self.outputdirectory, f"archive_{timestamp}.mp4")

        fourcc=cv2.VideoWriter_fourcc(*'mp4v')          #fourcc is an indentifier which tells the system which compression algorithm to apply            
        self.writer=cv2.VideoWriter(archivepath, fourcc, 15.0, (width,height))    #declaring parameters of videowriter- where to save, how to save etc
        self.currentsegemntstart=currenttime
        print("New Recording Segment Initialized [NVR]")

    def release(self):
        if self.writer is not None:
            self.writer.release()
            self.writer=None

recorder=ContinuousRecorder()

class ConnectionManager:
    def __init__(self):
        self.activeconnections: list[WebSocket]=[]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.activeconnections.append(websocket)
        print(f"New Client Connected. ({len(self.activeconnections)}) ")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.activeconnections:
            self.activeconnections.remove(websocket)
            print(f"Client Disconnected. ({len(self.activeconnections)}) ")

    async def broadcast(self,data: dict):
        for connection in list(self.activeconnections):
            try:
                await connection.send_json(data)
            except:
                self.disconnect(connection)

alertmanager=ConnectionManager()

def dispatchalert(payload: dict):
    global maineventloop
    if maineventloop is not None and maineventloop.is_running():
        asyncio.run_coroutine_threadsafe(alertmanager.broadcast(payload), maineventloop)

#Producer Thread: Pulls frames from the camera and places them onto the queue
def streamreaderthread():
    global rawframequeue
    capture=cv2.VideoCapture(cameraurl) 
    
    while True:
        if not capture.isOpened():                      #if no video feed is available
            print("The Camera is not Connected. Retrying in 1s")
            time.sleep(1)    
            capture=cv2.VideoCapture(cameraurl)  
            continue

        success,frame=capture.read()            #if camera feed is available: read the frame
        
        if not success:
            print("Dropped Frame. Re-establishing the stream")
            capture.release()
            time.sleep(1)
            capture=cv2.VideoCapture(cameraurl)
            continue

        recorder.writeframes(frame)   #calling the recording class for recording raw footage to NVR
        
        if rawframequeue.full():        #when the new frame is grabbed, but the queue is full
            try:
                rawframequeue.get_nowait()  #delete the current frame
            except queue.Empty:
                pass

        try:
            rawframequeue.put_nowait(frame) #insert the new frame into the queue.
        except queue.Full:
            pass

#occlusiondetection
class AdaptiveOcclusionDetector:
    def __init__(self, calibrationframes: int=60):
        self.calibrationframes=calibrationframes
        self.iscalibrated=False

        #Baseline Data Accumulaters(During Warmup)
        self._collectedstddevs=[]
        self._collectedlaplacians=[]

        self.baselinestddevs=1.0
        self.baselinelaplacians=1.0

    def update(self, frame) -> tuple[bool, float, float]:
        resized=cv2.resize(frame, (320,180))                    #reducing the size of each frames
        gray=cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)          #converting frames to grayscale

        _, stddev=cv2.meanStdDev(gray)
        currentstd=float(stddev[0][0])

        laplacianmatrix=cv2.Laplacian(gray, cv2.CV_64F)
        currentlap=float(laplacianmatrix.var())

        if not self.iscalibrated:
            self._collectedstddevs.append(currentstd)
            self._collectedlaplacians.append(currentlap)

            if len(self._collectedstddevs)>=self.calibrationframes:
                self.baselinestddevs=max(float(np.mean(self._collectedstddevs)), 1.0)
                self.baselinelaplacians=max(float(np.mean(self._collectedlaplacians)), 1.0)
                self.iscalibrated=True
            return False, 1.0, 1.0

        #calculate the relative difference of current and baseline values
        contrastratio=currentstd/self.baselinestddevs
        sharpnessratio=currentlap/self.baselinelaplacians

        isoccluded=(contrastratio<0.25) and (sharpnessratio<0.25)

        if not isoccluded:
            alpha=0.005
            self.baselinestddevs=(alpha*currentstd)+((1.0-alpha)*self.baselinestddevs)
            self.baselinelaplacians=(alpha*currentlap)+((1.0-alpha)*self.baselinelaplacians)
        return isoccluded,contrastratio,sharpnessratio

#Consumer Thread: Pulls the latest frames from the Queue and runs Yolo Inference
def inferenceworkerthread():
    global currentframebytes, isrecording, posteventcounter, videowriter, activeincidentpath, timesincelastincident, lastrecordingendtime

    consecutivehits=0
    requiredhits=2

    occlusiondetector=AdaptiveOcclusionDetector(calibrationframes=60)
    occlusioncounter=0
    occlusiontriggerframes=20
    
    while True:
        try:
            frame=rawframequeue.get(timeout=1.0)    #get the frame from the queue
        except queue.Empty:
            continue

        isoccluded,contrastratio,sharpnessratio=occlusiondetector.update(frame)
        #print(f"Contrast Ratio: {contrastratio}, \t Sharpness Ratio: {sharpnessratio}")

        if occlusiondetector.iscalibrated:
            if isoccluded:
                occlusioncounter=occlusioncounter+1
                print("The CAMERA IS OBSTRUCTED!!!!")
            else:
                occlusioncounter=0

        #YOLO Proccessing here
        result=model(frame, classes=67, conf=0.60, imgsz=640, verbose=False)      #classes=[0] targets persons only, verbose=False suppresses thinking logs
        labelledframe=result[0].plot()

        framebuffer.append(labelledframe)           #continuosly push the frame into the frame buffer inorder to roll pre-event clips

        boxes=result[0].boxes                   #check if there is any event happening
        for box in result[0].boxes:
            classid=int(box.cls[0])
            confidence=float(box.conf[0])
            classname=model.names[classid]
            print(f"Detected: {classname} ({classid}) with {confidence:.2f} confidence")

        hasthreat=len(boxes)>0        
        if len(boxes)>0:
            consecutivehits=consecutivehits+1
        else:
            consecutivehits=0

        currenttime=time.time()
        timesincelastincident=currenttime-lastrecordingendtime

        #if any event is happening and if its not already recording then, save pre event clips
        if consecutivehits>=requiredhits  and not isrecording and (timesincelastincident > cooldowntime):
            print("Incident Detected- Stitching up and saving the clips")
            isrecording=True
            posteventcounter=0

            timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")         #set timestamp in the video recording
            activeincidentpath=os.path.join("incidents", f"incident_{timestamp}.mp4")

            fourcc=cv2.VideoWriter_fourcc(*'mp4v')          #fourcc is an indentifier which tells the system which compression algorithm to apply
            height,width,_=labelledframe.shape              #set video height and width same as labelled video height and width
            videowriter=cv2.VideoWriter(activeincidentpath, fourcc, 15.0, (width,height))    #declaring parameters of videowriter- where to save, how to save etc

            #dump already recorded frames into filename as pre-event footage
            for bufferedframe in framebuffer:
                videowriter.write(bufferedframe)
            print("Pre Event Frames are saved!")

            dispatchalert({
                "event": "INCIDENT_TRIGGERED",
                "type": "yolomodel alert",
            })

        #for post event clip saving
        if isrecording:
            videowriter.write(labelledframe)

            if hasthreat:
                posteventcounter=0
            else:
                posteventcounter=posteventcounter+1

            if posteventcounter>=posteventframes:   #when the post event queue is full, stop the recording
                videowriter.release()
                isrecording=False
                consecutivehits=0                   #reset hit counter
                lastrecordingendtime=time.time()    
                framebuffer.clear()
                print("Post Event Recording Compelete")
                activeincidentpath=None

        #compressing video frames to JPEG Images
        _,buffer=cv2.imencode('.jpg',labelledframe)
        currentframebytes=buffer.tobytes()


@app.on_event("startup")
async def startupevent():
    global maineventloop
    maineventloop=asyncio.get_running_loop()

    #Start the camera recorder loop
    readerthread=threading.Thread(target=streamreaderthread, daemon=True)
    readerthread.start()

    #Start the processing thread 
    workerthread=threading.Thread(target=inferenceworkerthread, daemon=True)
    workerthread.start()
    print("Both Reader and Inference worker Thread has started!")


#this endpoint will be used by frontend to stream video
@app.websocket("/ws/video")
async def videowebsocket(websocket: WebSocket):         
    await websocket.accept()
    print("Client connected to WebSocket")

    try:
        while True:
            if currentframebytes:
                await websocket.send_bytes(currentframebytes)   #send bytes to software
                await asyncio.sleep(0.033)          #30FPS

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.websocket("/ws/alerts")
async def alertswebsocket(websocket: WebSocket):
    await alertmanager.connect(websocket)
    try:
        while True:
            # Keeps connection open and receives client heartbeat/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        alertmanager.disconnect(websocket)
    except Exception:
        alertmanager.disconnect(websocket)

@app.get("/")
async def get_test_page():
    """Serves a basic HTML page to test the WebSocket stream."""
    return FileResponse("stream.html")

#for laptop only
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,port=8000)

#cross platform- use ipcongif IPv4 Addess as host
'''if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0" ,port=8000)'''

