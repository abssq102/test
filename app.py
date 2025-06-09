
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
import docx2txt
import re
import os

app = Flask(__name__)
CORS(app)

def extract_text(file_storage):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    elif filename.endswith((".doc", ".docx")):
        return docx2txt.process(file_storage)
    else:
        return ""

def analyze_text(text):
    if not text or len(text.strip()) < 100:
        return 0, {'found': [], 'missing': []}

    keywords = {
        'experience': ['experience', 'worked at', 'job history'],
        'education': ['education', 'degree', 'university', 'bachelor'],
        'skills': ['skills', 'proficient in', 'tools'],
        'contact': ['email', 'phone', 'contact'],
        'objective': ['objective', 'summary'],
        'certification': ['certification', 'certified', 'license']
    }

    found = []
    missing = []
    score = 100

    text_lower = text.lower()

    for key, variants in keywords.items():
        if any(variant in text_lower for variant in variants):
            found.append(key)
        else:
            missing.append(key)
            score -= 10

    if re.search(r'[\u2022•★●]', text):
        score -= 10
    if len(text) > 5000:
        score -= 5

    score = max(score, 0)
    return score, {'found': found, 'missing': missing}

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files['resume']
    text = extract_text(uploaded_file)
    score, details = analyze_text(text)
    return jsonify({'score': score, 'details': details})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
