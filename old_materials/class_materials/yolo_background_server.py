"""
YOLO Background Detection Server
=================================
Runs continuously in the background, capturing frames and performing object detection.
Updates shared files that the MCP server can read.

Shared State Files:
- latest_frame.jpg: Current camera snapshot with annotations
- latest_metadata.json: Detection results (objects, bboxes, counts)

This script runs independently and does NOT interact with MCP or users directly.
"""

import cv2
from ultralytics import YOLO
import json
import time
import sys
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Camera settings
CAMERA_INDEX = 1                   # 0 = default webcam, 1 = external camera

# YOLO settings
MODEL_NAME = "yolov8n.pt"           # Nano model (fastest, ~6MB)
CONFIDENCE_THRESHOLD = 0.5          # Minimum confidence to include detection

# Output file paths (temp directory for real-time updates)
TEMP_DIR = "temp"
FRAME_OUTPUT = os.path.join(TEMP_DIR, "current_frame.jpg")
METADATA_OUTPUT = os.path.join(TEMP_DIR, "current_metadata.json")

# Performance settings
FPS_LIMIT = 10                      # Target frames per second (prevents CPU overload)
SHOW_PREVIEW = True                 # Show live annotated window for debugging

# ============================================================================
# YOLO BACKGROUND SERVER CLASS
# ============================================================================

class YOLOBackgroundServer:
    """
    Background server that continuously runs YOLO detection and updates shared files.
    """
    
    def __init__(self):
        """Initialize camera and YOLO model."""
        self.camera = None
        self.model = None
        self.frame_count = 0
        self.running = False
        
    def initialize(self):
        """
        Initialize camera and YOLO model.
        Returns True if successful, False otherwise.
        """
        print("[INIT] YOLO Background Server Starting...")
        
        # Create temp directory for output files
        os.makedirs(TEMP_DIR, exist_ok=True)
        print(f"[OK] Temp directory created: {TEMP_DIR}/")
        
        # Initialize camera
        try:
            self.camera = cv2.VideoCapture(CAMERA_INDEX)
            if not self.camera.isOpened():
                print(f"[ERROR] Could not open camera at index {CAMERA_INDEX}")
                return False
            
            # Get camera properties
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"[OK] Camera initialized ({width}x{height})")
            
        except Exception as e:
            print(f"[ERROR] Camera initialization failed: {e}")
            return False
        
        # Initialize YOLO model
        try:
            print(f"[LOAD] Loading YOLO model: {MODEL_NAME}")
            self.model = YOLO(MODEL_NAME)
            print("[OK] YOLOv8n model loaded successfully")
            
        except Exception as e:
            print(f"[ERROR] YOLO model loading failed: {e}")
            print("[TIP] First run will download the model (~6MB)")
            return False
        
        return True
    
    def process_frame(self, frame):
        """
        Run YOLO detection on a single frame.
        
        Args:
            frame: OpenCV image (numpy array)
            
        Returns:
            tuple: (annotated_frame, metadata_dict)
        """
        # Run YOLO inference
        results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        # Get annotated frame with bounding boxes
        annotated_frame = results[0].plot()
        
        # Extract detection information
        detections = []
        class_counts = {}
        
        for box in results[0].boxes:
            # Get class name and confidence
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]
            confidence = float(box.conf[0])
            
            # Get bounding box coordinates [x1, y1, x2, y2]
            bbox = box.xyxy[0].tolist()
            bbox = [int(coord) for coord in bbox]
            
            # Add to detections list
            detections.append({
                "class": class_name,
                "confidence": round(confidence, 3),
                "bbox": bbox
            })
            
            # Count objects by class
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        # Build metadata dictionary
        metadata = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "frame_number": self.frame_count,
            "objects": detections,
            "summary": {
                "total_objects": len(detections),
                "class_counts": class_counts,
                "unique_classes": list(class_counts.keys())
            }
        }
        
        return annotated_frame, metadata
    
    def save_results(self, frame, metadata):
        """
        Save frame and metadata to shared files.
        
        Args:
            frame: Annotated OpenCV image
            metadata: Detection metadata dictionary
        """
        try:
            # Save frame as JPEG (overwrites previous)
            cv2.imwrite(FRAME_OUTPUT, frame)
            
        except Exception as e:
            print(f"[WARNING] Failed to save frame: {e}")
        
        try:
            # Save metadata as JSON (overwrites previous)
            with open(METADATA_OUTPUT, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"[WARNING] Failed to save metadata: {e}")
    
    def run(self):
        """
        Main detection loop - runs continuously until stopped.
        """
        if not self.initialize():
            print("[ERROR] Initialization failed. Exiting.")
            return
        
        print("[RUN] Detection loop running...")
        print("      Press 'q' in preview window or Ctrl+C to quit")
        print("")
        
        self.running = True
        fps_start_time = time.time()
        fps_frame_count = 0
        current_fps = 0
        
        try:
            while self.running:
                loop_start_time = time.time()
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    print("[WARNING] Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Process frame with YOLO
                annotated_frame, metadata = self.process_frame(frame)
                
                # Save results to shared files
                self.save_results(annotated_frame, metadata)
                
                # Increment frame counter
                self.frame_count += 1
                fps_frame_count += 1
                
                # Calculate FPS every second
                if time.time() - fps_start_time >= 1.0:
                    current_fps = fps_frame_count / (time.time() - fps_start_time)
                    fps_start_time = time.time()
                    fps_frame_count = 0
                
                # Print status
                obj_summary = ", ".join([f"{count} {cls}" for cls, count in metadata["summary"]["class_counts"].items()])
                if not obj_summary:
                    obj_summary = "No objects"
                    
                print(f"Frame {self.frame_count:4d} | FPS: {current_fps:4.1f} | {obj_summary}", end='\r')
                
                # Show preview window (if enabled)
                if SHOW_PREVIEW:
                    # Add FPS counter to display
                    display_frame = annotated_frame.copy()
                    cv2.putText(display_frame, f"FPS: {current_fps:.1f}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, (0, 255, 0), 2)
                    
                    cv2.imshow("YOLO Background Server - Press 'q' to quit", display_frame)
                    
                    # Check for 'q' key press
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("\n[QUIT] Quit signal received")
                        self.running = False
                        break
                
                # FPS limiter - sleep to maintain target FPS
                elapsed = time.time() - loop_start_time
                target_delay = 1.0 / FPS_LIMIT
                if elapsed < target_delay:
                    time.sleep(target_delay - elapsed)
        
        except KeyboardInterrupt:
            print("\n[QUIT] Keyboard interrupt received")
        
        except Exception as e:
            print(f"\n[ERROR] Exception in main loop: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources and cleanup."""
        print("\n[CLEANUP] Cleaning up...")
        
        if self.camera is not None:
            self.camera.release()
            print("[OK] Camera released")
        
        if SHOW_PREVIEW:
            cv2.destroyAllWindows()
            print("[OK] Windows closed")
        
        print("[OK] Shutdown complete")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  YOLO BACKGROUND DETECTION SERVER")
    print("=" * 60)
    print("")
    
    # Create and run server
    server = YOLOBackgroundServer()
    server.run()

