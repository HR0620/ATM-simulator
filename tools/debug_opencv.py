import sys
print(f"Python: {sys.version}")

try:
    import numpy
    print(f"NumPy: {numpy.__version__}")
except ImportError as e:
    print(f"NumPy Import Failed: {e}")

try:
    import cv2
    print(f"OpenCV: {cv2.__version__}")
except ImportError as e:
    print(f"OpenCV Import Failed: {e}")
except Exception as e:
    print(f"OpenCV Crash: {e}")
