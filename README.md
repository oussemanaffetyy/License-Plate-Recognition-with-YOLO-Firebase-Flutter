# License Plate Extraction with YOLOv10 and PaddleOCR & Save Data to SQL Database

## Project Overview

This project aims to detect license plates from video files using **YOLOv10** for object detection and **PaddleOCR** for Optical Character Recognition (OCR) to extract license plate numbers. The recognized license plates are then stored in an **SQLite** database, and alerts are sent using **Firebase** for unauthorized plates.

Key Features:
- Real-time license plate detection using YOLOv10.
- OCR-based license plate text recognition with PaddleOCR.
- Logs detected license plates into an SQLite database.
- Sends alerts for unauthorized license plates to Firebase.
- Supports video file inputs.

## Requirements

Before running the project, make sure you have the following installed:

- **Python 3.11+**
- **Conda** (for environment and dependency management)
- **SQLite** (for storing detected license plates)
- **Firebase Account** (for sending alerts)

## Installation Steps

Follow these steps to set up the project:

### Step 1: Clone the Repository

First, clone the repository to your local machine.

```bash
git clone https://github.com/THU-MIG/yolov10.git

```bash
git clone https://github.com/THU-MIG/yolov10.git
```

```bash
conda create -n cvproj python=3.11 -y
```

```bash
conda activate cvproj
```

```bash
pip install -r requirements.txt
```

```bash
cd yolov10
```

```bash
pip install -e .
```

```bash
cd ..
```

```bash
python sqldb.py
```

```bash
python main.py
```

## Error Fixed

```bash
pip uninstall numpy
```

```bash
pip install numpy==1.26.4
```


### sqlite viewer:

https://inloop.github.io/sqlite-viewer/


