
from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
import docx2txt
import re
import os

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import docx
except ImportError:
    docx = None

app = Flask(__name__)
CORS(app)

UNSUPPORTED_FONTS = ['comic sans', 'brush script', 'curlz mt', 'papyrus']
RECOMMENDED_FONTS = ['arial', 'calibri', 'times new roman']

def extract_text(file_storage):
    filename = file_storage.filename.lower()
    if filename.endswith(".pdf"):
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    elif filename.endswith((".doc", ".docx")):
        return docx2txt.process(file_storage)
    else:
        return ""

def detect_fonts(file_storage):
    filename = file_storage.filename.lower()
    fonts_found = set()

    if filename.endswith(".pdf") and fitz:
        try:
            doc = fitz.open(stream=file_storage.read(), filetype="pdf")
            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for b in blocks:
                    for l in b.get("lines", []):
                        for s in l.get("spans", []):
                            font = s.get("font", "").lower()
                            if font:
                                fonts_found.add(font)
        except Exception:
            pass

    elif filename.endswith(".docx") and docx:
        try:
            doc = docx.Document(file_storage)
            for para in doc.paragraphs:
                for run in para.runs:
                    font_name = run.font.name
                    if font_name:
                        fonts_found.add(font_name.lower())
        except Exception:
            pass

    return list(fonts_found)

def analyze_text(text):
    notes = []
    suggestions = []
    if not text or len(text.strip()) < 100:
        notes.append("النص الموجود في الملف قليل جدًا أو غير قابل للقراءة.")
        suggestions.append("تأكد من أن السيرة الذاتية ليست صورة ممسوحة ضوئيًا.")
        return 0, {'found': [], 'missing': []}, notes, suggestions

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

    if re.search(r'[★•●♦◆❖✔✖]', text):
        score -= 5
        notes.append("توجد رموز زخرفية غير مدعومة في ATS مثل ★ أو ●")
        suggestions.append("استخدم رموز نصية بسيطة مثل النقاط أو الشرط العادي.")

    if len(text) > 7000:
        score -= 5
        notes.append("طول السيرة الذاتية كبير جدًا، يُفضل تقليصها.")
        suggestions.append("قلل من التفاصيل المكررة أو أدمج الوظائف المتشابهة.")

    suggestions.append("يفضل أن يكون حجم الخط بين 10 و12 نقطة للقراءة المثالية في أنظمة ATS.")

    return max(score, 0), {'found': found, 'missing': missing}, notes, suggestions

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files['resume']
    file_storage_copy = uploaded_file.stream.read()
    uploaded_file.stream.seek(0)

    fonts_used = detect_fonts(uploaded_file.stream)
    uploaded_file.stream.seek(0)

    text = extract_text(uploaded_file.stream)
    score, details, notes, suggestions = analyze_text(text)

    if fonts_used:
        for font in fonts_used:
            for bad in UNSUPPORTED_FONTS:
                if bad in font:
                    score -= 10
                    notes.append(f"تم استخدام خط غير مدعوم: {font}")
                    suggestions.append("استخدم خطوط احترافية مدعومة مثل Arial أو Calibri أو Times New Roman.")
                    break

    job_description = request.form.get('job_description', '').lower()
    match_score = None
    if job_description:
        resume_words = set(text.lower().split())
        jd_words = set(job_description.split())
        common = resume_words.intersection(jd_words)
        match_score = round((len(common) / len(jd_words)) * 100) if jd_words else 0

    return jsonify({
        'score': max(score, 0),
        'details': details,
        'fonts': fonts_used,
        'notes': notes,
        'suggestions': suggestions,
        'match_score': match_score
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
