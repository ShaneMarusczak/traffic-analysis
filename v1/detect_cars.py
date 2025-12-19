import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import cv2
import torch
from ultralytics import YOLO
import time
from datetime import datetime
import csv

# Device setup
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = YOLO('yolov8n.pt')
model.to(device)

print(f"Device: {device}")
if device == 'cuda':
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Model on CUDA: {next(model.model.parameters()).is_cuda}")

cap = cv2.VideoCapture('http://192.168.86.37:4747/video')

PERSPECTIVE_FACTOR_RTL = 1.15

vehicle_count = 0
crossed_ids = set()
previous_positions = {}
first_seen_position = {}
vehicle_data = []

fps_list = []
frame_count = 0
start_time = time.time()

save_frames = True
frame_save_interval = 50
save_dir = "output_frames"
if save_frames:
    os.makedirs(save_dir, exist_ok=True)

print("Starting detection\n")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        frame_height, frame_width = frame.shape[:2]
        
        crop_width = frame_width // 2
        left_half = frame[:, :crop_width]
        line_x = crop_width // 2
        
        results = model.track(
            source=left_half,
            tracker='bytetrack.yaml',
            conf=0.25,
            device=device,
            persist=True,
            verbose=False
        )
        
        inference_time = results[0].speed['inference']
        current_fps = 1000 / inference_time if inference_time > 0 else 0
        fps_list.append(current_fps)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            track_ids = boxes.id.int().cpu().tolist()
            xyxy = boxes.xyxy.cpu().numpy()
            classes = boxes.cls.int().cpu().tolist()
            current_time = time.time()
            
            for track_id, box, cls in zip(track_ids, xyxy, classes):
                if cls not in [2, 3, 5, 7]:
                    continue
                
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                if track_id not in first_seen_position:
                    first_seen_position[track_id] = (center_x, center_y, current_time)
                
                if track_id in previous_positions:
                    prev_x, prev_y = previous_positions[track_id]
                    
                    crossed_right = prev_x < line_x <= center_x
                    crossed_left = prev_x > line_x >= center_x
                    
                    if (crossed_right or crossed_left) and track_id not in crossed_ids:
                        first_x, first_y, first_time = first_seen_position[track_id]
                        
                        distance_pixels = abs(center_x - first_x)
                        time_elapsed = current_time - first_time
                        
                        if time_elapsed > 0.1:
                            speed_raw = distance_pixels / time_elapsed
                            
                            if crossed_left:
                                speed_normalized = speed_raw * PERSPECTIVE_FACTOR_RTL
                                direction = "RTL"
                            else:
                                speed_normalized = speed_raw
                                direction = "LTR"
                            
                            vehicle_count += 1
                            crossed_ids.add(track_id)
                            
                            vehicle_data.append({
                                'vehicle_number': vehicle_count,
                                'track_id': track_id,
                                'direction': direction,
                                'speed_raw': speed_raw,
                                'speed_normalized': speed_normalized,
                                'distance_px': distance_pixels,
                                'time_elapsed': time_elapsed,
                                'timestamp': current_time - start_time
                            })
                            
                            print(f"Vehicle #{vehicle_count} | {direction} | {speed_normalized:.1f} px/s")
                
                previous_positions[track_id] = (center_x, center_y)
                
                if save_frames:
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                                (0, 255, 0), 2)
                    cv2.putText(frame, f"{track_id}", (int(x1), int(y1)-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        if save_frames:
            cv2.line(frame, (line_x, 0), (line_x, frame_height), (0, 255, 0), 3)
            cv2.line(frame, (crop_width, 0), (crop_width, frame_height), (255, 0, 0), 2)
            
            cv2.putText(frame, f"Count: {vehicle_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if frame_count % frame_save_interval == 0:
                timestamp = datetime.now().strftime("%H%M%S")
                cv2.imwrite(f"{save_dir}/frame_{frame_count:06d}_{timestamp}.jpg", frame)

        if frame_count % 100 == 0:
            avg_fps = sum(fps_list[-100:]) / min(len(fps_list), 100)
            print(f"Frame {frame_count} | FPS: {avg_fps:.1f} | Count: {vehicle_count}")

except KeyboardInterrupt:
    print("\nStopped")

finally:
    cap.release()
    
    # Save data to CSV
    if vehicle_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"traffic_data_{timestamp}.csv"
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'vehicle_number',
                'track_id', 
                'direction',
                'speed_raw',
                'speed_normalized',
                'distance_px',
                'time_elapsed',
                'timestamp'
            ])
            writer.writeheader()
            writer.writerows(vehicle_data)
        
        print(f"\nData saved: {filename}")
        print(f"Total vehicles: {len(vehicle_data)}")
    else:
        print("\nNo vehicles detected")
