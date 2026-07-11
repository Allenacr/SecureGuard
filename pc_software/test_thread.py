import time
import threading
from config import logger
from database import Database
from photo_capture import PhotoCapture

print("Main: initializing db and photocapture")
class DummyDB:
    user_id = "test_user"
    def upload_photo(self, local_path, storage_path):
        print(f"Mock upload: {local_path} -> {storage_path}")
        return f"http://mock.url/{storage_path}"
    def update_incident(self, iid, data):
        print(f"Mock update: {iid} {data}")

photo_capture = PhotoCapture(DummyDB())

print("Main: starting thread")
threading.Thread(
    target=photo_capture.capture_and_upload,
    args=("test_incident_id",),
    daemon=True,
    name="PhotoCapture"
).start()

print("Main: waiting")
time.sleep(5)
print("Main: done")
