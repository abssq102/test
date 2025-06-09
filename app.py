from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
import docx2txt
import fitz  # PyMuPDF
import os
import re
import io
import docx

app = Flask(__name__)
CORS(app)

# استخراج النص من PDF أو Word
def extract_text(file_storage):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        reader = PdfReader(file_storage)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif filename.endswith((".doc", ".docx")):
        return docx2txt.process(file_storage)
    return ""

# تحليل الكلمات المفتاحية
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
    found, missing = [], []
    score = 100
    text_lower = text.lower()
    for key, variants in keywords.items():
        if any(v in text_lower for v in variants):
            found.append(key)
        else:
            missing.append(key)
            score -= 10
    if re.search(r'[•★●▪◆■♦→]', text):
        score -= 5
    if len(text) > 5000:
        score -= 5
    return max(score, 0), {'found': found, 'missing': missing}

# استخراج الخطوط من الملفات
def detect_fonts(file_storage):
    fonts = set()
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        doc = fitz.open(stream=file_storage.read(), filetype="pdf")
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        fonts.add(s.get("font", ""))
    elif filename.endswith(".docx"):
        try:
            doc = docx.Document(file_storage)
            for para in doc.paragraphs:
                if para.runs:
                    for run in para.runs:
                        fonts.add(run.font.name or "")
        except Exception:
            fonts = set()
    fonts = {f for f in fonts if f}
    return list(fonts)

# تحليل التوصيات بناءً على الخط والحجم
def suggest_improvements(text, fonts):
    suggestions = []
    notes = []

    # تحذير من الخطوط غير المدعومة
    ats_safe_fonts = {"Arial", "Calibri", "Times New Roman", "Georgia", "Helvetica"}
    for font in fonts:
        if font and font not in ats_safe_fonts:
            notes.append(f"الخط '{font}' قد لا يكون مدعومًا في أنظمة ATS.")
            suggestions.append("استخدم خطوط مثل Arial أو Calibri لضمان التوافق.")

    # اقتراح على حجم النص بناءً على عدد الكلمات
    words = len(text.split())
    if words < 100:
        notes.append("السيرة قصيرة جدًا وقد لا توضح خبراتك.")
    if re.search(r'(font-size:\s*\d+pt)', text.lower()):
        pt_size = int(re.findall(r'font-size:\s*(\d+)pt', text.lower())[0])
        if pt_size < 10 or pt_size > 14:
            suggestions.append("يفضل أن يكون حجم الخط بين 10 و 12 نقطة للقراءة المثالية في أنظمة ATS.")

    return notes, suggestions

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files['resume']
    text = extract_text(uploaded_file)
    score, details = analyze_text(text)
    fonts_used = detect_fonts(uploaded_file)
    notes, suggestions = suggest_improvements(text, fonts_used)

    job_description = request.form.get('job_description', '').lower()
    match_score = None
    if job_description:
        resume_words = set(text.lower().split())
        jd_words = set(job_description.split())
        common = resume_words.intersection(jd_words)
        match_score = round((len(common) / len(jd_words)) * 100) if jd_words else 0

    return jsonify({
        'score': score,
        'details': details,
        'fonts': fonts_used,
        'notes': notes,
        'suggestions': suggestions,
        'match_score': match_score
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)