import tkinter as tk
import cv2
import threading
import time

def capture_thread():
    print("Background thread starting...")
    time.sleep(1)
    print("Calling VideoCapture...")
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        print("VideoCapture returned! isOpened:", cap.isOpened())
        cap.release()
    except Exception as e:
        print("Exception:", e)
    print("Background thread finished.")

print("Starting tk...")
root = tk.Tk()
print("Starting thread...")
threading.Thread(target=capture_thread, daemon=True).start()
print("Starting mainloop...")
root.after(3000, root.destroy)
root.mainloop()
print("Mainloop finished.")
