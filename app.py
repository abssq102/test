from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
import docx2txt
import re

app = Flask(__name__)

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
        return 0
    score = 100
    keywords = ['experience', 'education', 'skills', 'contact', 'objective', 'certification']
    found_keywords = sum(1 for word in keywords if word in text.lower())
    score -= (len(keywords) - found_keywords) * 10

    if re.search(r'[\u2022•★●]', text):
        score -= 10
    if len(text) > 5000:
        score -= 5

    return max(score, 0)

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files['resume']
    text = extract_text(uploaded_file)
    score = analyze_text(text)
    return jsonify({'score': score})

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

