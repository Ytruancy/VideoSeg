import sys
import os
import cv2
import json
import glob
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QInputDialog, QMessageBox, QSlider, QProgressDialog
from PyQt5.QtCore import QTimer, Qt, QRect, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from pytubefix import YouTube
from pytubefix.cli import on_progress

class VideoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.drawing = False
        self.rects = []
        self.parent = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.drawing = True

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.end_point = event.pos()
            self.rects.append(QRect(self.start_point, self.end_point))
            self.drawing = False
            self.update()
            self.parent.prompt_watermark_done()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0), 2, Qt.SolidLine)
        painter.setPen(pen)
        for rect in self.rects:
            painter.drawRect(rect)
        if self.drawing:
            painter.drawRect(QRect(self.start_point, self.end_point))
        painter.end()

class VideoSegmenter(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_segmenting = False
        self.start_frame = 0
        self.segment_frames = []
        self.video_path = None
        self.mask_rects = []

    def initUI(self):
        self.setWindowTitle("Video Segmenter")
        self.setGeometry(100, 100, 800, 600)
        
        self.layout = QVBoxLayout()

        self.label = VideoLabel(self)
        self.layout.addWidget(self.label)

        self.download_button = QPushButton('Download Video', self)
        self.download_button.clicked.connect(self.download_video)
        self.layout.addWidget(self.download_button)

        self.play_button = QPushButton('Play', self)
        self.play_button.clicked.connect(self.play_video)
        self.layout.addWidget(self.play_button)

        self.pause_button = QPushButton('Pause', self)
        self.pause_button.clicked.connect(self.pause_video)
        self.layout.addWidget(self.pause_button)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.slider_moved)
        self.layout.addWidget(self.slider)

        self.setLayout(self.layout)

    def ask_for_watermark(self):
        reply = QMessageBox.question(self, 'Watermark', 'Is there a watermark to remove?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            return True
        else:
            QMessageBox.information(self, 'No Watermark', 'No watermark to remove. Press Play to start playing the video.')
            return False

    def prompt_watermark_done(self):
        reply = QMessageBox.question(self, 'Watermark', 'Have you marked all the watermarks?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.mask_rects = [{'x1': rect.left(), 'y1': rect.top(), 'x2': rect.right(), 'y2': rect.bottom()} for rect in self.label.rects]
            self.save_mask()
            self.label.rects.clear()  # Clear the rectangles list
            self.label.update()  # Update the label to reflect the changes
            self.process_video()
            
    def save_mask(self):
        with open('mask_data.json', 'w') as f:
            json.dump(self.mask_rects, f)
        QMessageBox.information(self, 'Mask Saved', 'Watermark mask saved as mask_data.json.')

    def process_video(self):
        self.play_button.setEnabled(False)

        # Progress dialog setup
        progress_dialog = QProgressDialog("Removing watermarks...", "Abort", 0, self.frame_count, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.show()

        # Open video capture and writer
        cap = cv2.VideoCapture(self.video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('processed_video.mp4', fourcc, self.fps, (self.width, self.height))

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Apply masks to remove watermarks
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            for rect in self.mask_rects:
                x1, y1, x2, y2 = rect['x1'], rect['y1'], rect['x2'], rect['y2']
                mask[y1:y2, x1:x2] = 255

            inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)
            out.write(inpainted_frame) 

            frame_idx += 1
            progress_dialog.setValue(frame_idx)

            if progress_dialog.wasCanceled():
                break

        cap.release()
        out.release()

        # Replace original video with processed video
        self.vdieo_path = 'processed_video.mp4'

        self.play_button.setEnabled(True)
        QMessageBox.information(self, 'Processing Complete', 'Watermark removal complete. You can now play the video.')

    def download_video(self):
        url, ok = QInputDialog.getText(self, 'Download Video', 'Enter YouTube video URL:')
        if ok and url:
            file_name = "downloaded_video.mp4"
            try:
                yt = YouTube(url, on_progress_callback=on_progress)
                ys = yt.streams.filter(adaptive=True, file_extension='mp4').order_by('resolution').desc().first()
                ys.download(filename=file_name)
                
                self.video_path = file_name
                self.cap = cv2.VideoCapture(self.video_path)
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                QMessageBox.information(self, 'Download Complete', 'Video downloaded successfully! Press Play to start playing the video.')
                self.show_frame_for_watermark()
            except Exception as e:
                QMessageBox.critical(self, 'Download Error', f'An error occurred: {e}')
        else:
            QMessageBox.warning(self, 'Input Error', 'Invalid URL entered.')

    def show_frame_for_watermark(self):
        self.cap = cv2.VideoCapture(self.video_path)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, 30000)  # 30th second frame
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
            need_watermark_removal = self.ask_for_watermark()
            if need_watermark_removal:
                self.label.setPixmap(QPixmap.fromImage(image))
        else:
            QMessageBox.critical(self, 'Error', 'Could not retrieve frame.')

    def play_video(self):
        if self.video_path:
            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.video_path)
                if not self.cap.isOpened():
                    print("Error: Could not open video.")
                    return

            # Load mask data
            try:
                with open('mask_data.json', 'r') as f:
                    self.mask_rects = json.load(f)
            except FileNotFoundError:
                QMessageBox.critical(self, 'Error', 'Mask data file not found.')
                return

            # Get the current position if the video was paused
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Retrieve video properties
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')

            # Set the slider range based on the total number of frames
            self.slider.setRange(0, self.frame_count - 1)

            # Ensure the video resumes from the current frame
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

            # Start the timer to play the video
            self.timer.start(1000 // int(self.fps))

    def pause_video(self):
        self.timer.stop()

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Apply masks to remove watermarks
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            for rect in self.mask_rects:
                x1, y1, x2, y2 = rect['x1'], rect['y1'], rect['x2'], rect['y2']
                mask[y1:y2, x1:x2] = 255

            inpainted_frame = cv2.inpaint(frame, mask, 3, cv2.INPAINT_TELEA)

            frame = cv2.cvtColor(inpainted_frame, cv2.COLOR_BGR2RGB)
            image = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(image))
            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.slider.setValue(current_frame)
            if self.is_segmenting:
                self.segment_frames.append(inpainted_frame)
        else:
            self.timer.stop()
            self.cap.release()

    def slider_moved(self, position):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888)
                self.label.setPixmap(QPixmap.fromImage(image))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Q:
            self.close()
        elif event.key() == Qt.Key_W:
            if not self.is_segmenting:
                self.is_segmenting = True
                self.start_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                print("Started segmenting at frame:", self.start_frame)
                self.segment_frames = []
        elif event.key() == Qt.Key_S:
            if self.is_segmenting:
                self.pause_video()
                end_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.is_segmenting = False
                print("Stopped segmenting at frame:", end_frame)
                filename = self.prompt_segment_details()
                if filename:
                    self.create_directory_if_not_exists(filename)
                    out = cv2.VideoWriter(filename, self.fourcc, self.fps, (self.width, self.height))
                    for f in self.segment_frames:
                        out.write(f)
                    out.release()
                    print(f"Segmented video saved as: {filename}")
                    self.segment_frames.clear()
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, end_frame)  # Resume from the last frame
                    self.timer.start(1000 // int(self.fps))  # Automatically resume playing the video
    
    def create_directory_if_not_exists(self, filepath):
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def prompt_segment_details(self):
        details = {}
        fields = {
            "Road Type": ["City", "Country", "Highway"],
            "Clear Visibility": ["Yes", "No"],
            "Weather Condition": ["good", "bad"],
            "Lighting": ["Day", "Night"],
            "Driver Directly Involvement": ["Yes", "No"],
            "Driver's Responsibility?": ["Yes","No"],
            "Traffic Condition": ["Normal","Heavy"],
            "Damage Vehicle Only": ["Yes", "No"],
            "Accident Severity": ["Minor", "Moderate", "Severe"]
        }

        for key, options in fields.items():
            item, ok = QInputDialog.getItem(self, "Input", key, options, 0, False)
            if ok and item:
                details[key] = item
            else:
                details[key] = "Unknown"

        unique_id, ok = QInputDialog.getText(self, 'Unique ID', 'Enter a unique ID for this segment:')
        if not ok or not unique_id:
            unique_id = "Unknown"
        
        filename = "_".join(details.values()) + f"/{unique_id}.mp4"
        mp4_files = glob.glob(os.path.join("_".join(details.values()), '*.mp4'))
        mp4_file_names = [os.path.splitext(os.path.basename(file))[0] for file in mp4_files]

        while unique_id in mp4_file_names:
            unique_id, ok = QInputDialog.getText(self, 'ID already exist', 'Enter a unique ID for this segment:')
            filename = "_".join(details.values()) + f"/{unique_id}.mp4"

        return filename

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoSegmenter()
    player.show()
    sys.exit(app.exec_())
