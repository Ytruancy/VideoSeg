# Video Segmenter README

## Introduction

The Video Segmenter is a Python-based application that allows users to download YouTube videos, play them, mark and remove watermarks, and segment the video into smaller clips based on specific criteria (currently set up for car accident video segmentation). It uses PyQt5 for the graphical user interface and OpenCV for video processing.

## Requirements

To run this program, you need to install the required packages. You can do this by running:

```bash
pip install -r requirements.txt
```
## Usage
### Running the Application
To start the application, run the following command:
```bash
python segmenter_pro_v2.py
```

## Features
1. Download Video:
    Click on the "Download Video" button.
    Enter the YouTube video URL.
    The video will be downloaded and ready for playback.
2. Play Video:
    Click on the "Play" button to start playing the video.
    Use the slider to navigate through the video.
3. Pause Video:
    Click on the "Pause" button to pause the video.
4. Remove Watermark:
    - When prompted, indicate if there is a watermark to remove.
    - If yes, mark the watermark areas on the frame displayed.
    - Confirm once all watermarks are marked.
    - The application will process the video to remove the watermarks.
5. Segment Video:
    - While the video is playing, press W to start segmenting at the current frame.
    - Press S to stop segmenting and save the segment.
    - Enter details for the segment, such as road type, weather condition, lighting, etc.
    - Provide a unique ID for the segment.
    - The segmented video will be saved with the provided details.

## Keyboard Shortcuts
    - Q: Quit the application.
    - W: Start video segmenting.
    - S: Stop video segmenting and save the segment.
