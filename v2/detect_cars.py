"""
Traffic Detection - Producer
Detects vehicles crossing counting line and sends raw data to queue.
GPU-accelerated YOLO detection with ByteTrack tracking.
"""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import cv2
import torch
from ultralytics import YOLO
import time
from datetime import datetime


def run_detection(data_queue, config):
    """
    Main detection loop. Tracks vehicles and pushes raw crossing data to queue.
    
    Args:
        data_queue: multiprocessing.Queue for sending vehicle data
        config: Configuration dictionary from config.yaml
    """
    
    # Initialize model
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = YOLO(config['detection']['model_file'])
    model.to(device)
    
    # Verify GPU usage
    print(f"Detection initialized")
    print(f"  Device: {device}")
    print(f"  Model: {config['detection']['model_file']}")
    if device == 'cuda':
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  Model on CUDA: {next(model.model.parameters()).is_cuda}")
    else:
        print(f"  WARNING: Running on CPU - will be slow")
    
    # Camera setup
    cap = cv2.VideoCapture(config['camera']['url'])
    if not cap.isOpened():
        print(f"ERROR: Cannot connect to {config['camera']['url']}")
        data_queue.put(None)
        return
    
    print(f"  Camera: {config['camera']['url']}")
    print(f"  Confidence: {config['detection']['confidence_threshold']}")
    
    # State tracking
    vehicle_count = 0
    crossed_ids = set()
    previous_positions = {}
    first_seen_position = {}
    
    # Performance tracking
    fps_list = []
    frame_count = 0
    start_time = time.time()
    
    # Frame saving setup
    save_frames = config['frame_saving']['enabled']
    frame_save_interval = config['frame_saving']['interval']
    save_dir = config['frame_saving']['output_dir']
    
    if save_frames:
        os.makedirs(save_dir, exist_ok=True)
        print(f"  Frame saving: Every {frame_save_interval} frames -> {save_dir}/")
    else:
        print(f"  Frame saving: Disabled")
    
    print(f"\nDetection started\n")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("WARNING: Failed to read frame")
                break
            
            frame_count += 1
            frame_height, frame_width = frame.shape[:2]
            
            # Crop to left half (ROI) if configured
            if config['roi']['use_left_half']:
                crop_width = frame_width // 2
                left_half = frame[:, :crop_width]
            else:
                crop_width = frame_width
                left_half = frame
            
            line_x = crop_width // 2
            
            # YOLO detection + ByteTrack tracking
            results = model.track(
                source=left_half,
                tracker='bytetrack.yaml',
                conf=config['detection']['confidence_threshold'],
                device=device,
                persist=True,
                verbose=False
            )
            
            # FPS tracking
            inference_time = results[0].speed['inference']
            current_fps = 1000 / inference_time if inference_time > 0 else 0
            fps_list.append(current_fps)
            
            # Process detections
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes
                track_ids = boxes.id.int().cpu().tolist()
                xyxy = boxes.xyxy.cpu().numpy()
                classes = boxes.cls.int().cpu().tolist()
                current_time = time.time()
                
                vehicle_classes = config['detection']['vehicle_classes']
                
                for track_id, box, cls in zip(track_ids, xyxy, classes):
                    # Filter for configured vehicle classes
                    if cls not in vehicle_classes:
                        continue
                    
                    # Calculate center point
                    x1, y1, x2, y2 = box
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # First detection of this vehicle
                    if track_id not in first_seen_position:
                        first_seen_position[track_id] = (center_x, center_y, current_time)
                    
                    # Check for line crossing
                    if track_id in previous_positions:
                        prev_x, prev_y = previous_positions[track_id]
                        
                        crossed_right = prev_x < line_x <= center_x  # LTR
                        crossed_left = prev_x > line_x >= center_x   # RTL
                        
                        if (crossed_right or crossed_left) and track_id not in crossed_ids:
                            first_x, first_y, first_time = first_seen_position[track_id]
                            
                            # Calculate raw measurements
                            distance_pixels = abs(center_x - first_x)
                            time_elapsed = current_time - first_time
                            
                            # Minimum tracking time to avoid noise
                            if time_elapsed > config['tracking']['min_time_before_count']:
                                vehicle_count += 1
                                crossed_ids.add(track_id)
                                
                                direction = "RTL" if crossed_left else "LTR"
                                
                                # Send RAW data to analyzer (no computation)
                                data_queue.put({
                                    'vehicle_number': vehicle_count,
                                    'track_id': track_id,
                                    'direction': direction,
                                    'distance_pixels': distance_pixels,
                                    'time_elapsed': time_elapsed,
                                    'timestamp': current_time - start_time
                                })
                                
                                print(f"Vehicle #{vehicle_count:3d} | {direction} | "
                                      f"{distance_pixels:.0f}px / {time_elapsed:.2f}s")
                    
                    # Update tracking state
                    previous_positions[track_id] = (center_x, center_y)
                    
                    # Draw bounding boxes on saved frames
                    if save_frames:
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                                    (0, 255, 0), 2)
                        cv2.putText(frame, f"{track_id}", (int(x1), int(y1)-10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Annotate and save frames
            if save_frames:
                # Draw counting line (green) and crop boundary (blue)
                cv2.line(frame, (line_x, 0), (line_x, frame_height), (0, 255, 0), 3)
                if config['roi']['use_left_half']:
                    cv2.line(frame, (crop_width, 0), (crop_width, frame_height), (255, 0, 0), 2)
                
                # Overlay stats
                cv2.putText(frame, f"Count: {vehicle_count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"FPS: {current_fps:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save periodically
                if frame_count % frame_save_interval == 0:
                    timestamp = datetime.now().strftime("%H%M%S")
                    filename = f"{save_dir}/frame_{frame_count:06d}_{timestamp}.jpg"
                    cv2.imwrite(filename, frame)
            
            # Periodic status update (hardcoded - implementation detail)
            if frame_count % 100 == 0:
                avg_fps = sum(fps_list[-100:]) / min(len(fps_list), 100)
                elapsed = time.time() - start_time
                print(f"[{elapsed/60:.1f}min] Frame {frame_count} | "
                      f"FPS: {avg_fps:.1f} | Count: {vehicle_count}")
    
    except KeyboardInterrupt:
        print("\nDetection stopped by user")
    except Exception as e:
        print(f"\nERROR in detection: {e}")
    finally:
        cap.release()
        data_queue.put(None)  # Signal end to analyzer
        
        elapsed = time.time() - start_time
        avg_fps = sum(fps_list) / len(fps_list) if fps_list else 0
        
        print(f"\nDetection complete")
        print(f"  Runtime: {elapsed/60:.1f} minutes")
        print(f"  Frames: {frame_count}")
        print(f"  Avg FPS: {avg_fps:.1f}")
        print(f"  Vehicles: {vehicle_count}")


if __name__ == "__main__":
    # Standalone testing
    import yaml
    from multiprocessing import Queue
    
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    queue = Queue()
    run_detection(queue, config)
