
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
            content = page.extract_text()
            if content:
                text += content
        return text
    elif filename.endswith((".doc", ".docx")):
        return docx2txt.process(file_storage)
    else:
        return ""

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

    unsupported_fonts_keywords = ['comic sans', 'brush script', 'curlz mt', 'papyrus']
    for font in unsupported_fonts_keywords:
        if font in text_lower:
            score -= 10
            notes.append(f"تم استخدام خط غير مدعوم: {font}")
            suggestions.append("استخدم خطوط احترافية مدعومة مثل Arial أو Calibri أو Times New Roman.")
            break

    # اقتراح حجم خط مثالي
    suggestions.append("يفضل أن يكون حجم الخط بين 10 و12 نقطة للقراءة المثالية في أنظمة ATS.")

    return max(score, 0), {'found': found, 'missing': missing}, notes, suggestions

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files['resume']
    text = extract_text(uploaded_file)
    score, details, notes, suggestions = analyze_text(text)

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
        'notes': notes,
        'suggestions': suggestions,
        'match_score': match_score
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
