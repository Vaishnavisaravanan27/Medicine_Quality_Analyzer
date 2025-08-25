import cv2
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime
import re
import tkinter as tk
from threading import Thread, Event
from queue import Queue, Empty

# Function to extract expiry date from QR code
def extract_expiry_date_from_qr(qr_data):
    date_pattern = r'\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b'
    dates = []
    matches = re.findall(date_pattern, qr_data)
    
    for match in matches:
        try:
            if '-' in match:
                date_obj = datetime.strptime(match, '%Y-%m-%d')
            elif '/' in match:
                date_obj = datetime.strptime(match, '%d/%m/%Y')
            dates.append(date_obj)
        except ValueError:
            continue
    
    if dates:
        return max(dates).strftime('%Y-%m-%d')
    
    return None

# Function to check if the product is expired
def check_expiry(expiry_date_str):
    if not expiry_date_str:
        return "No expiry date found in QR code."

    try:
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
    except ValueError:
        return "Invalid date format found in QR code. Expected YYYY-MM-DD."

    current_date = datetime.now()

    if current_date > expiry_date:
        return "The product has expired."
    else:
        return "The product is still valid."

# Function to get remaining duration until expiry
def get_remaining_duration(expiry_date_str):
    if not expiry_date_str:
        return "No expiry date found."

    try:
        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        current_date = datetime.now()

        if current_date > expiry_date:
            return "The product has already expired."

        remaining_time = expiry_date - current_date
        days_left = remaining_time.days

        if days_left > 0:
            return f"{days_left} day(s) remaining"
        else:
            return "The product will expire today!"
    
    except ValueError:
        return "Invalid date format found."    

# Function to update the note window with the result
def update_note_window(queue, qr_data, result, duration):
    if not queue.empty():
        queue.get()
    queue.put((qr_data, result, duration))

# Create and setup the note window
def setup_note_window(queue, stop_event):
    global qr_data_text, result_text, duration_text, note_window

    def update_gui():
        if not queue.empty():
            try:
                qr_data, result, duration = queue.get_nowait()
                qr_data_text.set(f"QR Code Data: {qr_data}")
                result_text.set(f"Expiry Check: {result}")
                duration_text.set(f"Duration: {duration}")
            except Empty:
                pass
        if not stop_event.is_set():
            note_window.after(500, update_gui)

    note_window = tk.Tk()
    note_window.title("QR Code Results")
    
    # Set the window position to the right side of the screen
    screen_width = note_window.winfo_screenwidth()
    screen_height = note_window.winfo_screenheight()
    window_width = 500
    window_height = 250
    x_position = screen_width - window_width
    y_position = (screen_height - window_height) // 2
    
    note_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    note_window.attributes("-topmost", True)  # Keep the window on top

    # Styling the note window
    note_window.configure(bg='#f5f5f5')

    # Title label with enhanced style
    title_label = tk.Label(note_window, text="QR Code Results", font=("Arial", 18, 'bold'), bg='#f5f5f5', fg='#333333')
    title_label.pack(pady=(10, 5))

    # QR Code data label
    qr_data_text = tk.StringVar()
    qr_data_label = tk.Label(note_window, textvariable=qr_data_text, font=("Arial", 12), bg='#f5f5f5', fg='#555555', wraplength=480)
    qr_data_label.pack(pady=(5, 5))
    
    # Result and duration labels
    result_text = tk.StringVar()
    duration_text = tk.StringVar()

    result_label = tk.Label(note_window, textvariable=result_text, font=("Arial", 14, 'bold'), bg='#f5f5f5', fg='#ff5722')
    result_label.pack(pady=(5, 5))
    
    duration_label = tk.Label(note_window, textvariable=duration_text, font=("Arial", 12), bg='#f5f5f5', fg='#009688')
    duration_label.pack(pady=(5, 10))
    
    # Add a border around the note window
    note_window.configure(borderwidth=2, relief="groove")

    update_gui()
    note_window.mainloop()

def process_frame(frame, queue):
    decoded_objects = decode(frame)
    
    for obj in decoded_objects:
        qr_data = obj.data.decode("utf-8")
        expiry_date_str = extract_expiry_date_from_qr(qr_data)
        
        # Update note window with the result
        result = check_expiry(expiry_date_str)
        duration = get_remaining_duration(expiry_date_str)
        update_note_window(queue, qr_data, result, duration)
        
        # Draw bounding box (optional) and display QR code data
        points = obj.polygon
        if len(points) == 4:
            pts = [(point.x, point.y) for point in points]
            cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, (0, 255, 0), 2)
    
    return frame

def main():
    queue = Queue()
    stop_event = Event()
    
    # Start the note window in a separate thread
    Thread(target=setup_note_window, args=(queue, stop_event), daemon=True).start()
    
    cap = cv2.VideoCapture(0)  # Open the camera
    
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return
    
    print("Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Failed to grab frame.")
            break
        
        frame = process_frame(frame, queue)
        
        cv2.imshow('QR Code Scanner', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    stop_event.set()

if __name__ == "__main__":
    main()
