import cv2

# Try both URL formats
url = "http://192.168.86.29:4747/video"

cap = cv2.VideoCapture(url)

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"SUCCESS! Resolution: {frame.shape[1]}x{frame.shape[0]}")
        print("iPhone stream working")
    else:
        print("Opened but no frame")
else:
    print("Failed - try /video.mjpg instead")
    
cap.release()
