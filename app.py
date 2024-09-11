from flask import Flask, request, jsonify, render_template
import os
import requests
from google.cloud import vision
import io
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Set upload and output directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'static/logo_output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

def analyze_image(image_path):
    """
    Analyze image using Google Vision API and get labels.
    """
    client = vision.ImageAnnotatorClient()
    
    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    if response.error.message:
        raise Exception(f'{response.error.message}')

    return [label.description for label in labels]

def search_image(query, api_key, cse_id, start=1):
    """
    Search for images using Google Custom Search API with pagination support.
    """
    search_url = 'https://www.googleapis.com/customsearch/v1'
    params = {
        'q': query,
        'key': api_key,
        'cx': cse_id,
        'searchType': 'image',
        'num': 10,  # Number of results per page
        'start': start  # Start index for pagination
    }

    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        results = response.json()
        items = results.get('items', [])
        return items
    else:
        response.raise_for_status()

@app.route('/upload_and_search', methods=['POST'])
def upload_and_search():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    try:
        # Analyze image
        labels = analyze_image(file_path)
        
        # Search for labels using Google Custom Search API
        search_query = ' '.join(labels)
        api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
        cse_id = os.getenv('GOOGLE_CUSTOM_SEARCH_CSE_ID')
        image_results = search_image(search_query, api_key, cse_id)
        
        if image_results:
            return jsonify({'images': image_results, 'labels': labels})
        else:
            return jsonify({'message': 'No images found for the query', 'labels': labels}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_image', methods=['POST'])
def search_image_route():
    query = request.form.get('query')
    start = int(request.form.get('start', 1))  # Start index for pagination
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
    cse_id = os.getenv('GOOGLE_CUSTOM_SEARCH_CSE_ID')

    try:
        image_results = search_image(query, api_key, cse_id, start)
        if image_results:
            return jsonify({'images': image_results})
        else:
            return jsonify({'message': 'No images found for the query'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
