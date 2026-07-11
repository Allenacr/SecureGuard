import cv2
import time

print("Starting cv2 test")
try:
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    print("Opened with DSHOW:", cap.isOpened())
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        print("Opened without DSHOW:", cap.isOpened())
    
    if cap.isOpened():
        ret, frame = cap.read()
        print("Read frame:", ret)
        cap.release()
    else:
        print("Could not open camera")
except Exception as e:
    print("Exception:", e)
print("Finished cv2 test")
