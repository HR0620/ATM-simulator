# AI-based Touchless Machine (ATM)

[日本語版はこちら](README.md)

> **AI-based Touchless Machine (ATM)** is a next-generation ATM system that leverages image recognition technology to enable touch-like interactions on displays that do not natively support touch input.

**Note: The user interface of this application is available in Japanese only.**

<div align="center">
<img src="docs/images/icon.png" width="200" height="200">
</div>

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Since](https://img.shields.io/badge/since-2025.12-blue)](Since)

</div>

---

## Development Period

December 2025 – January 2026

## About the Project

### Overview

This system is a next-generation "**AI-powered Contactless ATM**" developed to address the risks of contact-based infections in traditional touch-panel ATMs and to prevent skimming through physical button manipulation. In response to rising public health awareness and the trend of Digital Transformation (DX), this project aims to provide a safer and more intuitive financial transaction experience.

### Key Features

The core feature is **gesture recognition technology** using a standard webcam. In addition to general gesture recognition, we have implemented high-precision **Finger Tracking**. Users can perform transactions such as "Transfer," "Withdrawal," and "Account Creation" smoothly without ever touching the screen, using intuitive pointing motions.

To prevent accidental inputs, the system includes a **consecutive input prevention filter** for the same direction and an **upper-screen misdetection filter** to ensure maximum reliability.

### Technical Stack

* **AI Model:** Uses **Ultralytics YOLOv8-Pose**, the industry standard for object detection and pose estimation. By detecting coordinates for the wrist and elbow as well as the hand shape, it infers fingertip positions through vector calculations, achieving fast and accurate pointing.
* **Performance:** Fully compatible with Python 3.13. It utilizes **Asynchronous Inference** to prevent UI lag during processing.
* **Face Detection:** Uses **OpenCV Haar Cascades** to automatically detect users when they stand in front of the camera, guiding them to the optimal position.
* **User Interface:** Built on **Tkinter**, featuring a real-time camera background with semi-transparent overlays for information display.

### Notable Details

We implemented a **"tactile feedback"** effect for buttons. When a button is selected via gesture, it visually mimics being physically pressed through shadow movement and offsets. Combined with audio cues, this creates a satisfying and intuitive user experience.

On the security front, PIN codes are stored using **salted hashing**, and the system includes a lockout feature after multiple failed attempts.

## System Requirements

* **Python 3.13** or higher (Required)
    Check your version with:
    ```bash
    python --version
    ```
    [Download Python here](https://www.python.org/downloads/)
* **Webcam**
* **Windows 11** (Recommended. Functionality on other versions of Windows, Linux, or macOS has not been verified.)
* **5GB** of available storage space

## Dependencies

* numpy
* opencv-python
* Pillow
* PyYAML
* pygame
* ultralytics

## Installation

### Binary Download (Recommended)

Latest Version: [Releases](https://github.com/HR0620/ATM-simulator/releases/latest)

<details>
<summary><b>Windows</b></summary>

Download `AI-based Touchless Machine (ATM).zip` from the [Releases page](https://github.com/HR0620/ATM-simulator/releases/latest), extract it, and run the executable.

> **Note**: If a Windows Defender warning appears, click "More info" → "Run anyway."
</details>

### Build from Source

```bash
git clone [https://github.com/HR0620/ATM-simulator.git](https://github.com/HR0620/ATM-simulator.git)
cd ATM-simulator
python -m venv venv
# On Windows:
venv\Scripts\activate
pip install -r requirements.txt
python run.py

```

## Operation Demo (v1.2.0)

### Standby & Face Detection

Automatically detects the user's face when they approach.

![Face Alignment](docs/images/face_align.png)

### Main Menu

Select "Transfer," "Withdrawal," or "Create Account" via fingertip control.

![Main Menu](docs/images/menu.png)

### PIN Entry

Enter your PIN using the on-screen keypad.

![PIN Entry](docs/images/pin.png)

### Confirmation Screen

Review transaction details and confirm with a gesture.

![Confirmation Screen](docs/images/confirm.png)

### Transaction Complete

Displays results with audio guidance.

![Transaction Complete](docs/images/complete.png)

## Directory Structure

```
.
├── src/                # Source code
│   ├── core/           # App logic (Controllers, State Management)
│   ├── ui/             # UI Rendering (Tkinter)
│   ├── vision/         # Camera Processing & AI (YOLOv8/OpenCV)
│   └── main.py         # App Entry Point
├── resources/          # External Assets
│   ├── assets/         # Images & Audio
│   ├── config/         # Config files (atm_config.yml)
│   ├── model/          # AI Models (yolov8n-pose.pt)
│   └── icon.ico        # App Icon
├── scripts/            # Build Scripts
├── docs/               # Documentation Assets
├── data/               # Operation Data (Accounts, etc. / Gitignored)
├── tools/              # Dev Tools & Debugging
├── run.py              # Dev Entry Point
├── requirements.txt    # Dependencies
└── pyproject.toml      # Project Definition

```

## FAQ

<details>
<summary><b>
Q: I get a security warning (Windows Defender) when running the EXE.
</b></summary>

A: Since this binary is unsigned, Windows may flag it. Please click **"More info" → "Run anyway."**
</details>

<details>
<summary><b>
Q: Is this available on OS other than Windows?
</b></summary>

A: Currently, it has only been tested on **Windows 11**.
</details>

<details>
<summary><b>
Q: Where is the configuration file?
</b></summary>

A: It is located at `./resources/config/atm_config.yml`. You can modify application behavior there.
</details>

<details>
<summary><b>
Q: The buttons are triggering unintentionally.</b></summary>
A: Complex background patterns or low lighting can affect YOLOv8-Pose accuracy. You can increase `min_detection_confidence` in the `vision` section of the config file to reduce false positives.
</details>

<details>
<summary><b>
Q: The buttons won't react.
</b></summary>
A: The system determines interaction based on wrist position. Please stand at least **70cm** away from the screen with good posture.
</details>

<details>
<summary><b>
Q: I get errors running python run.py.
</b></summary>
A:

1. Ensure you have **Python 3.13+**.
2. Update dependencies: `pip install -U pip` and `pip install -r requirements.txt --force-reinstall`.
3. Ensure your webcam isn't being used by another app (Zoom, Teams, etc.).
</details>

---

## License

This project is licensed under the MIT License - see the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

---

Made by [Renju (HR0620)](https://github.com/HR0620)
