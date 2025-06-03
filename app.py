from flask import Flask, request, send_file, render_template, jsonify
from rembg import remove, new_session
from PIL import Image
import os
import uuid
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['PROCESSED_FOLDER'] = 'static/processed'

# Store processed image info
current_image_data = {
    'original': None,
    'processed': None,
    'final': None
}

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/process', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Generate unique IDs
    file_id = str(uuid.uuid4())
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{file.filename}")
    file.save(original_path)

    try:
        # Process image
        img = Image.open(original_path)
        processed = remove(img, session=new_session("u2net"))
        
        # Save processed image
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], f"processed_{file_id}.png")
        processed.save(processed_path)
        
        # Update current image data
        current_image_data['original'] = original_path
        current_image_data['processed'] = processed_path
        current_image_data['final'] = None  # Reset final image
        
        return jsonify({
            'status': 'success',
            'processed_url': f"/{processed_path}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add-bg', methods=['POST'])
def add_background():
    data = request.json
    color = data.get('color', 'transparent')
    
    if not current_image_data['processed']:
        return jsonify({'error': 'No processed image available'}), 400

    try:
        img = Image.open(current_image_data['processed'])
        
        if color != 'transparent':
            # Convert hex to RGB
            hex_color = color.lstrip('#')
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            bg = Image.new('RGB', img.size, rgb)
            bg.paste(img, (0, 0), img)
            img = bg
        
        # Save final image
        final_path = current_image_data['processed'].replace('.png', '_final.png')
        img.save(final_path)
        current_image_data['final'] = final_path
        
        return jsonify({
            'status': 'success',
            'final_url': f"/{final_path}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download')
def download():
    if not current_image_data['final']:
        return "No image available", 404
        
    try:
        # For transparent background, send the processed image (without bg)
        if request.args.get('transparent') == 'true':
            filepath = current_image_data['processed']
        else:
            filepath = current_image_data['final']
            
        return send_file(
            filepath,
            as_attachment=True,
            download_name=f"bg_removed_{int(time.time())}.png",
            mimetype='image/png'
        )
    except Exception as e:
        return f"Error: {str(e)}", 500
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    app.run(debug=True)