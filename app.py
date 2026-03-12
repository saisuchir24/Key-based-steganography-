from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from PIL import Image
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import io
import struct

app = Flask(__name__)
app.secret_key = 'change_this_to_a_secure_random_value'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Derive key from password and salt
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def _bytes_to_bits(data: bytes):
    for byte in data:
        for i in range(7, -1, -1):
            yield (byte >> i) & 1

def _bits_to_bytes(bits):
    b = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | bit
        b.append(byte)
    return bytes(b)

# Hide message in image using LSB on R,G,B channels (3 bits per pixel)
def hide_message(image_path, secret_text, password, output_path):
    # Convert to bytes and encrypt with Fernet using a random salt
    salt = os.urandom(16)
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(secret_text.encode())

    payload = salt + encrypted  # store salt first so extractor can derive same key
    payload_len = len(payload)
    header = struct.pack('>I', payload_len)  # 4-byte big-endian length
    full = header + payload

    # Convert to bits
    bits = list(_bytes_to_bits(full))

    img = Image.open(image_path).convert('RGB')
    width, height = img.size
    capacity = width * height * 3  # 3 bits per pixel (R,G,B)
    if len(bits) > capacity:
        raise ValueError(f'Payload too large to hide in image. Need {len(bits)} bits but capacity is {capacity} bits. Use a larger image.')

    encoded = img.copy()
    pixels = encoded.load()

    bit_idx = 0
    for y in range(height):
        for x in range(width):
            if bit_idx >= len(bits):
                break
            r, g, b = pixels[x, y]
            # set R LSB
            if bit_idx < len(bits):
                r = (r & ~1) | bits[bit_idx]; bit_idx += 1
            # set G LSB
            if bit_idx < len(bits):
                g = (g & ~1) | bits[bit_idx]; bit_idx += 1
            # set B LSB
            if bit_idx < len(bits):
                b = (b & ~1) | bits[bit_idx]; bit_idx += 1
            pixels[x, y] = (r, g, b)
        if bit_idx >= len(bits):
            break

    # Save as PNG to avoid compression losses
    encoded.save(output_path, format='PNG')

# Extract message from image
def extract_message(stego_image_path, password):
    img = Image.open(stego_image_path).convert('RGB')
    width, height = img.size
    pixels = img.load()

    bits = []
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            bits.append(r & 1)
            bits.append(g & 1)
            bits.append(b & 1)

    # First 32 bits -> header length (4 bytes)
    header_bits = bits[:32]
    header_bytes = _bits_to_bytes(header_bits)
    if len(header_bytes) < 4:
        raise ValueError('Image does not contain a valid hidden message.')
    payload_len = struct.unpack('>I', header_bytes)[0]
    total_payload_bits = payload_len * 8
    needed_bits = 32 + total_payload_bits
    if needed_bits > len(bits):
        # not enough bits present
        return None

    payload_bits = bits[32:32 + total_payload_bits]
    payload_bytes = _bits_to_bytes(payload_bits)
    if len(payload_bytes) < 16:
        # must at least contain salt (16 bytes)
        return None
    salt = payload_bytes[:16]
    encrypted = payload_bytes[16:]
    try:
        key = derive_key(password, salt)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
        return decrypted.decode()
    except Exception:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'hide':
            file = request.files.get('image')
            message = request.form.get('message')
            password = request.form.get('password')
            
            if not file or not message or not password:
                flash('All fields are required for hiding.', 'error')
                return redirect(url_for('index'))
            
            if len(message) > 10000:
                flash('Message too long (max 10000 characters).', 'error')
                return redirect(url_for('index'))
            
            filename = file.filename
            # Save uploaded file to a temp path
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            output_filename = os.path.splitext(filename)[0] + '_stego.png'
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
            file.save(input_path)
            
            try:
                hide_message(input_path, message, password, output_path)
                return send_file(output_path, as_attachment=True, download_name=output_filename)
            except Exception as e:
                flash(f'Error hiding message: {str(e)}', 'error')
                return redirect(url_for('index'))
        
        elif action == 'extract':
            file = request.files.get('stego_image')
            password = request.form.get('extract_password')
            
            if not file or not password:
                flash('All fields are required for extraction.', 'error')
                return redirect(url_for('index'))
            
            filename = file.filename
            stego_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(stego_path)
            
            try:
                message = extract_message(stego_path, password)
                if message:
                    flash(f'Extracted Message: {message}', 'success')
                else:
                    flash('Extraction failed! Wrong password or no hidden message.', 'error')
            except Exception as e:
                flash(f'Error extracting message: {str(e)}', 'error')
            return redirect(url_for('index'))
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
