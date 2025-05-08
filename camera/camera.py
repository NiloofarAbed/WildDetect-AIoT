import cv2
import torch
from ultralytics import YOLO
import os
import numpy as np
from picamera2 import Picamera2
import time
import asyncio

# Load the pre-trained YOLOv8 model
model = YOLO('epoch150s200.pt')  # You can use a larger model for better accuracy if needed

# Define the class labels for your specific dataset
class_labels = ['Bull', 'Nilgai', 'Pig', 'Peacock', 'Squirrel', 'Jackal', 'Cat', 'Dog', 'Goat', 'Mouse', 'Insect',
                'Person', 'Elephant', 'Monkey', 'Bird']

# Create output folder to store images of detected objects (if not already present)
output_dir = "../ngl"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Initialize the PiCamera2 instance
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

# Function to read frames from PiCamera2
def read_frame_from_picamera():
    try:
        # Capture a frame from the PiCamera2
        frame = picam2.capture_array()
        return frame
    except Exception as e:
        print(f"Error reading frame: {e}")
        return None

# Confidence threshold for detection
confidence_threshold = 0.50

# Function to perform object detection and select the best frame
def process_frames_for_best_detection(num_frames=5):
    best_frame = None
    best_score = 0
    best_frame_idx = -1
    best_detection = None

    # Capture multiple frames and evaluate them
    for i in range(num_frames):
        frame = read_frame_from_picamera()

        if frame is None:
            print("Error: Failed to capture image or empty frame.")
            continue

        # Perform the object detection with YOLO
        results = model.predict(source=frame)

        # Evaluate the best frame based on confidence
        for result in results:
            for detection in result.boxes.data.tolist():
                x1, y1, x2, y2, score, class_id = detection[:6]

                if score > confidence_threshold:
                    if score > best_score:
                        best_score = score
                        best_frame = frame
                        best_detection = detection
                        best_frame_idx = i

    return best_frame, best_score, best_detection

# Function to handle automatic frame capturing every 30 seconds
def handle_auto_capture():
    while True:  # Infinite loop for continuous frame capturing
        print("Capturing frames every 20 seconds...")
        
        # Wait for 50 seconds before capturing the next set of frames
        time.sleep(20)
        
        # Capture 5 frames and get the best one
        best_frame, best_score, best_detection = process_frames_for_best_detection(num_frames=5)
        
        if best_frame is not None and best_score > confidence_threshold:
            print(f"Best detection score: {best_score:.2f}")
            
            # Draw bounding box on the best frame
            x1, y1, x2, y2, score, class_id = best_detection[:6]
            cv2.rectangle(best_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2)
            label = f'{class_labels[int(class_id)].upper()} {int(score * 100)}%'
            cv2.putText(best_frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Save the best detected object image
            detection_class = class_labels[int(class_id)]
            detection_filename = f'{output_dir}/{detection_class}.jpg'
            try:
                cv2.imwrite(detection_filename, best_frame)  # Save the entire frame with drawn bounding box
                print(f"Best frame saved: {detection_filename}")
            except Exception as e:
                print(f"Error saving image {detection_filename}: {e}")
            
            # Display the resulting best frame with bounding boxes and labels
            resized_frame = cv2.resize(best_frame, (640, 360))
            cv2.imshow('YOLOv8 Best Detection', resized_frame)
            #
            cv2.destroyAllWindows()

        else:
            print("No detection found in the current frames.")

# Main loop: Run the automatic capture and detection
try:
    handle_auto_capture()  # Start automatic capture and detection every 30 seconds

finally:
    # When everything is done, stop the PiCamera and destroy all OpenCV windows
    picam2.stop()
