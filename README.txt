CyberStego - Local Steganography Web App
---------------------------------------

How to run:

1. Create a Python virtual environment (recommended):
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate

2. Install requirements:
   pip install flask pillow cryptography

3. Run the app:
   python app.py

4. Open in your browser:
   http://127.0.0.1:5000/

Notes:
- The app embeds the encrypted payload into the least-significant bits of the image (R,G,B channels).
- Output images are saved as PNG (to avoid lossy compression).
- The extractor expects the same password used for hiding.
- This project is for educational use only.
