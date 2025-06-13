from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
import docx2txt
import fitz  # PyMuPDF
import os
import re
import io
import docx
import striprtf
import tempfile
import logging

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# استخراج النص من الملف
def extract_text(file_storage):
    filename = file_storage.filename.lower()
    try:
        if filename.endswith(".pdf"):
            file_storage.seek(0)
            reader = PdfReader(file_storage)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif filename.endswith((".doc", ".docx")):
            file_storage.seek(0)
            # docx2txt يحتاج اسم ملف، نحفظ مؤقتا
            with tempfile.NamedTemporaryFile(delete=True, suffix=".docx", dir="/tmp") as tmp:
                tmp.write(file_storage.read())
                tmp.flush()
                text = docx2txt.process(tmp.name)
            return text
        elif filename.endswith(".rtf"):
            file_storage.seek(0)
            with io.TextIOWrapper(file_storage, encoding="utf-8", errors="ignore") as f:
                rtf_text = f.read()
                return striprtf.rtf_to_text(rtf_text)
        elif filename.endswith(".txt"):
            file_storage.seek(0)
            return file_storage.read().decode("utf-8", "ignore")
        else:
            return ""
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""

# كشف الجداول والصور في PDF وDOCX
def detect_tables_images(file_storage):
    filename = file_storage.filename.lower()
    tables = 0
    images = 0
    try:
        if filename.endswith(".pdf"):
            file_storage.seek(0)
            doc = fitz.open(stream=file_storage.read(), filetype="pdf")
            for page in doc:
                images += len(page.get_images(full=True))
                # كشف جداول (تقريبي)
                text = page.get_text("dict")
                vert_lines = sum(1 for l in text.get("lines", []) if abs(l['bbox'][0] - l['bbox'][2]) < 2)
                horiz_lines = sum(1 for l in text.get("lines", []) if abs(l['bbox'][1] - l['bbox'][3]) < 2)
                if vert_lines > 5 and horiz_lines > 5:
                    tables += 1
            doc.close()
        elif filename.endswith(".docx"):
            file_storage.seek(0)
            doc = docx.Document(file_storage)
            tables = len(doc.tables)
            # استخدم related_parts لاكتشاف الصور (أفضل من inline_shapes على السيرفرات)
            images = sum(1 for rel in doc.part.related_parts if "image" in rel)
    except Exception as e:
        logger.error(f"Error detecting tables/images: {e}")
    return tables, images

# تحليل الكلمات المفتاحية
def analyze_text(text):
    if not text or len(text.strip()) < 100:
        return 0, [], [], {}
    keywords = {
        'experience': [
            'experience', 'worked at', 'job history', 'خبرة', 'العمل في', 'الوظيفة'
        ],
        'education': [
            'education', 'degree', 'university', 'bachelor', 'دراسة', 'تعليم', 'شهادة', 'جامعة', 'بكالوريوس'
        ],
        'skills': [
            'skills', 'proficient in', 'tools', 'مهارات', 'إجادة', 'مهارة'
        ],
        'contact': [
            'email', 'phone', 'contact', 'بريد', 'هاتف', 'تواصل'
        ],
        'objective': [
            'objective', 'summary', 'هدف', 'ملخص'
        ],
        'certification': [
            'certification', 'certified', 'license', 'شهادة', 'رخصة', 'اعتماد'
        ]
    }
    section_scores = {}
    found, missing = [], []
    score = 100
    text_lower = text.lower()
    for key, variants in keywords.items():
        present = any(v in text_lower for v in variants)
        section_scores[key] = 100 if present else 0
        if present:
            found.append(key)
        else:
            missing.append(key)
            score -= 10
    detail_report = {
        "experience": section_scores['experience'],
        "education": section_scores['education'],
        "skills": section_scores['skills'],
        "contact": section_scores['contact'],
        "objective": section_scores['objective'],
        "certification": section_scores['certification']
    }
    # عقوبة الرموز
    if re.search(r'[•★●▪◆■♦→]', text):
        score -= 5
    if len(text) > 5000:
        score -= 5
    return max(score, 0), found, missing, detail_report

# استخراج الخطوط من الملفات
def detect_fonts(file_storage):
    fonts = set()
    filename = file_storage.filename.lower()
    try:
        file_storage.seek(0)
        if filename.endswith(".pdf"):
            doc = fitz.open(stream=file_storage.read(), filetype="pdf")
            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for b in blocks:
                    for l in b.get("lines", []):
                        for s in l.get("spans", []):
                            font = s.get("font", "")
                            if font:
                                fonts.add(font)
            doc.close()
        elif filename.endswith(".docx"):
            doc = docx.Document(file_storage)
            for para in doc.paragraphs:
                for run in para.runs:
                    if run.font.name:
                        fonts.add(run.font.name)
    except Exception as e:
        logger.error(f"Error extracting fonts: {e}")
    return list(fonts)

# تحليل التوصيات بناءً على الخط والحجم والجداول/الصور
def suggest_improvements(text, fonts, tables, images):
    suggestions = set()
    notes = []
    ats_safe_fonts = {"Arial", "Calibri", "Times New Roman", "Georgia", "Helvetica"}
    for font in fonts:
        if font and font not in ats_safe_fonts:
            notes.append(f"الخط '{font}' قد لا يكون مدعومًا في أنظمة ATS.")
            suggestions.add("استخدم خطوط مثل Arial أو Calibri لضمان التوافق.")
    words = len(text.split())
    if words < 100:
        notes.append("السيرة قصيرة جدًا وقد لا توضح خبراتك.")
    if re.search(r'(font-size:\s*\d+pt)', text.lower()):
        pt_size = int(re.findall(r'font-size:\s*(\d+)pt', text.lower())[0])
        if pt_size < 10 or pt_size > 14:
            suggestions.add("يفضل أن يكون حجم الخط بين 10 و 12 نقطة للقراءة المثالية في أنظمة ATS.")
    if tables > 0:
        notes.append(f"تم اكتشاف {tables} جدول في الملف، وهذا قد يسبب مشاكل لبعض أنظمة ATS.")
    if images > 0:
        notes.append(f"تم اكتشاف {images} صورة/عنصر رسومي في الملف، ويفضل تجنب الصور.")
    return notes, list(suggestions)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'لم يتم رفع ملف'}), 400
        uploaded_file = request.files['resume']
        if uploaded_file.filename == '':
            return jsonify({'error': 'لم يتم اختيار ملف'}), 400

        text = extract_text(uploaded_file)
        if not text or len(text.strip()) < 10:
            logger.error("No text extracted from file!")
            return jsonify({'error': 'فشل في استخراج النص من الملف أو الملف فارغ أو غير مدعوم'}), 400

        uploaded_file.seek(0)
        tables, images = detect_tables_images(uploaded_file)
        uploaded_file.seek(0)
        score, found, missing, section_scores = analyze_text(text)
        fonts_used = detect_fonts(uploaded_file)
        notes, suggestions = suggest_improvements(text, fonts_used, tables, images)

        job_description = request.form.get('job_description', '').lower()
        match_score = None
        if job_description:
            resume_words = set(text.lower().split())
            jd_words = set(job_description.split())
            if jd_words:
                common = resume_words.intersection(jd_words)
                match_score = round((len(common) / len(jd_words)) * 100)
            else:
                match_score = 0

        return jsonify({
            'score': score,
            'details': {
                'found': found,
                'missing': missing,
                'sections': section_scores
            },
            'fonts': fonts_used,
            'notes': notes,
            'suggestions': suggestions,
            'match_score': match_score,
            'tables': tables,
            'images': images
        })
    except Exception as e:
        logger.error(f"Exception in analyze: {e}")
        return jsonify({'error': 'خطأ غير متوقع أثناء تحليل السيرة الذاتية', 'details': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
