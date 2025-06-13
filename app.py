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
import logging
from collections import Counter
from difflib import SequenceMatcher
import spacy
from datetime import datetime

app = Flask(__name__)
CORS(app)

# إعداد الـ logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تحميل نموذج spaCy للمعالجة المتقدمة (اختياري)
try:
    nlp = spacy.load("en_core_web_sm")
    HAS_SPACY = True
except OSError:
    HAS_SPACY = False
    logger.warning("spaCy model not found. Using basic text processing.")

class ATSAnalyzer:
    def __init__(self):
        # كلمات مفتاحية محسّنة مع مرادفات أكثر
        self.keywords = {
            'experience': {
                'en': ['experience', 'worked at', 'job history', 'employment', 'position', 'role', 'worked as', 'served as', 'career', 'professional'],
                'ar': ['خبرة', 'العمل في', 'الوظيفة', 'منصب', 'دور', 'مهنة', 'عملت في', 'شغلت منصب']
            },
            'education': {
                'en': ['education', 'degree', 'university', 'bachelor', 'master', 'phd', 'diploma', 'college', 'school', 'academic'],
                'ar': ['دراسة', 'تعليم', 'شهادة', 'جامعة', 'بكالوريوس', 'ماجستير', 'دكتوراه', 'دبلوم', 'كلية']
            },
            'skills': {
                'en': ['skills', 'proficient in', 'tools', 'expertise', 'competent', 'abilities', 'technical skills', 'soft skills'],
                'ar': ['مهارات', 'إجادة', 'مهارة', 'خبرة في', 'كفاءة', 'قدرات', 'مهارات تقنية']
            },
            'contact': {
                'en': ['email', 'phone', 'contact', 'mobile', 'telephone', 'address', 'linkedin', 'portfolio'],
                'ar': ['بريد', 'هاتف', 'تواصل', 'جوال', 'عنوان', 'لينكد إن']
            },
            'objective': {
                'en': ['objective', 'summary', 'profile', 'about', 'career objective', 'professional summary'],
                'ar': ['هدف', 'ملخص', 'نبذة', 'الهدف المهني', 'ملخص مهني']
            },
            'certification': {
                'en': ['certification', 'certified', 'license', 'certificate', 'accreditation', 'credential'],
                'ar': ['شهادة', 'رخصة', 'اعتماد', 'شهادة معتمدة', 'مؤهل']
            },
            'achievements': {
                'en': ['achievements', 'accomplishments', 'awards', 'recognition', 'honors', 'success'],
                'ar': ['إنجازات', 'جوائز', 'تقدير', 'نجاحات', 'مكافآت']
            }
        }
        
        # خطوط آمنة لـ ATS
        self.ats_safe_fonts = {
            "Arial", "Calibri", "Times New Roman", "Georgia", 
            "Helvetica", "Verdana", "Tahoma", "Trebuchet MS"
        }
        
        # كلمات إيجابية للبحث عنها
        self.positive_indicators = [
            'achieved', 'improved', 'increased', 'developed', 'managed', 
            'led', 'created', 'implemented', 'optimized', 'delivered'
        ]

    def extract_text_enhanced(self, file_storage):
        """استخراج نص محسّن مع معالجة أفضل للأخطاء"""
        try:
            filename = file_storage.filename.lower()
            file_storage.seek(0)
            
            if filename.endswith(".pdf"):
                return self._extract_from_pdf(file_storage)
            elif filename.endswith((".doc", ".docx")):
                return self._extract_from_docx(file_storage)
            elif filename.endswith(".rtf"):
                return self._extract_from_rtf(file_storage)
            elif filename.endswith(".txt"):
                return self._extract_from_txt(file_storage)
            else:
                raise ValueError(f"نوع الملف غير مدعوم: {filename}")
                
        except Exception as e:
            logger.error(f"خطأ في استخراج النص: {str(e)}")
            return ""

    def _extract_from_pdf(self, file_storage):
        """استخراج محسّن من PDF"""
        try:
            # استخدام PyPDF2 أولاً
            reader = PdfReader(file_storage)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            
            # إذا فشل PyPDF2، استخدم PyMuPDF
            if not text.strip():
                file_storage.seek(0)
                doc = fitz.open(stream=file_storage.read(), filetype="pdf")
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
                
            return text
        except Exception as e:
            logger.error(f"خطأ في استخراج PDF: {str(e)}")
            return ""

    def _extract_from_docx(self, file_storage):
        """استخراج محسّن من DOCX"""
        try:
            return docx2txt.process(file_storage)
        except Exception as e:
            logger.error(f"خطأ في استخراج DOCX: {str(e)}")
            return ""

    def _extract_from_rtf(self, file_storage):
        """استخراج محسّن من RTF"""
        try:
            with io.TextIOWrapper(file_storage, encoding="utf-8", errors="ignore") as f:
                rtf_text = f.read()
                return striprtf.rtf_to_text(rtf_text)
        except Exception as e:
            logger.error(f"خطأ في استخراج RTF: {str(e)}")
            return ""

    def _extract_from_txt(self, file_storage):
        """استخراج محسّن من TXT"""
        try:
            return file_storage.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"خطأ في استخراج TXT: {str(e)}")
            return ""

    def detect_structure_advanced(self, file_storage):
        """كشف متقدم للجداول والصور والهيكل"""
        filename = file_storage.filename.lower()
        file_storage.seek(0)
        
        structure_info = {
            'tables': 0,
            'images': 0,
            'columns': 1,
            'has_headers': False,
            'has_bullets': False,
            'formatting_issues': []
        }
        
        try:
            if filename.endswith(".pdf"):
                structure_info.update(self._analyze_pdf_structure(file_storage))
            elif filename.endswith(".docx"):
                structure_info.update(self._analyze_docx_structure(file_storage))
        except Exception as e:
            logger.error(f"خطأ في تحليل الهيكل: {str(e)}")
            
        return structure_info

    def _analyze_pdf_structure(self, file_storage):
        """تحليل هيكل PDF بطريقة متقدمة"""
        doc = fitz.open(stream=file_storage.read(), filetype="pdf")
        tables = 0
        images = 0
        has_columns = False
        
        for page in doc:
            # كشف الصور
            images += len(page.get_images(full=True))
            
            # كشف الجداول بطريقة أكثر دقة
            tables += len(page.find_tables())
            
            # كشف الأعمدة
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            if len(blocks) > 1:
                x_positions = [block["bbox"][0] for block in blocks if "lines" in block]
                if len(set(x_positions)) > 2:  # أكثر من عمودين
                    has_columns = True
        
        doc.close()
        return {
            'tables': tables,
            'images': images,
            'columns': 2 if has_columns else 1
        }

    def _analyze_docx_structure(self, file_storage):
        """تحليل هيكل DOCX"""
        doc = docx.Document(file_storage)
        
        return {
            'tables': len(doc.tables),
            'images': len([r for p in doc.paragraphs for r in p.runs if r._element.xpath('.//pic:pic')]),
            'has_headers': any(p.style.name.startswith('Heading') for p in doc.paragraphs),
            'has_bullets': any('•' in p.text or p.style.name.startswith('List') for p in doc.paragraphs)
        }

    def analyze_content_advanced(self, text):
        """تحليل محتوى متقدم مع NLP"""
        if not text or len(text.strip()) < 50:
            return {
                'score': 0,
                'sections': {},
                'found': [],
                'missing': list(self.keywords.keys()),
                'detailed_analysis': {},
                'readability': 0
            }

        # تحليل الأقسام
        sections_analysis = self._analyze_sections(text)
        
        # حساب النقرة الإجمالية
        total_score = self._calculate_total_score(sections_analysis, text)
        
        # تحليل القابلية للقراءة
        readability = self._calculate_readability(text)
        
        # العثور على المفقود والموجود
        found = [k for k, v in sections_analysis.items() if v['score'] > 0]
        missing = [k for k, v in sections_analysis.items() if v['score'] == 0]
        
        return {
            'score': total_score,
            'sections': {k: v['score'] for k, v in sections_analysis.items()},
            'found': found,
            'missing': missing,
            'detailed_analysis': sections_analysis,
            'readability': readability
        }

    def _analyze_sections(self, text):
        """تحليل تفصيلي للأقسام"""
        text_lower = text.lower()
        sections = {}
        
        for section, keywords in self.keywords.items():
            all_keywords = keywords['en'] + keywords['ar']
            
            # حساب التطابقات
            matches = sum(1 for keyword in all_keywords if keyword.lower() in text_lower)
            
            # تحليل عمق المحتوى
            context_score = self._analyze_section_depth(text_lower, all_keywords)
            
            # النقرة النهائية للقسم
            base_score = min(100, (matches / len(all_keywords)) * 100)
            final_score = min(100, base_score + context_score)
            
            sections[section] = {
                'score': int(final_score),
                'matches': matches,
                'total_keywords': len(all_keywords),
                'context_quality': context_score
            }
            
        return sections

    def _analyze_section_depth(self, text, keywords):
        """تحليل عمق المحتوى في كل قسم"""
        score = 0
        
        # البحث عن كلمات في سياق
        for keyword in keywords:
            if keyword in text:
                # البحث عن الجمل التي تحتوي على الكلمة المفتاحية
                sentences = re.split(r'[.!?]\s+', text)
                relevant_sentences = [s for s in sentences if keyword in s]
                
                # تقييم جودة الجمل
                for sentence in relevant_sentences:
                    if len(sentence.split()) > 5:  # جملة مفيدة
                        score += 5
                    if any(indicator in sentence for indicator in self.positive_indicators):
                        score += 10
                        
        return min(score, 50)  # حد أقصى 50 نقطة إضافية

    def _calculate_total_score(self, sections_analysis, text):
        """حساب النقرة الإجمالية"""
        # متوسط نقاط الأقسام
        section_scores = [v['score'] for v in sections_analysis.values()]
        base_score = sum(section_scores) / len(section_scores) if section_scores else 0
        
        # خصومات
        penalties = 0
        
        # خصم للرموز المعقدة
        if re.search(r'[•★●▪◆■♦→]', text):
            penalties += 5
            
        # خصم للطول المفرط
        if len(text) > 8000:
            penalties += 10
        elif len(text) < 300:
            penalties += 15
            
        # خصم لعدم وجود أرقام (إنجازات كمية)
        if not re.search(r'\d+', text):
            penalties += 10
            
        return max(0, int(base_score - penalties))

    def _calculate_readability(self, text):
        """حساب قابلية القراءة"""
        sentences = len(re.split(r'[.!?]+', text))
        words = len(text.split())
        
        if sentences == 0:
            return 0
            
        avg_sentence_length = words / sentences
        
        # نقرة القابلية للقراءة (مبسطة)
        if 10 <= avg_sentence_length <= 20:
            return 100
        elif avg_sentence_length < 10:
            return 80
        else:
            return max(0, 100 - (avg_sentence_length - 20) * 2)

    def advanced_job_matching(self, resume_text, job_description):
        """مطابقة متقدمة مع الوصف الوظيفي"""
        if not job_description:
            return None
            
        # تنظيف النصوص
        resume_clean = re.sub(r'[^\w\s]', ' ', resume_text.lower())
        jd_clean = re.sub(r'[^\w\s]', ' ', job_description.lower())
        
        # استخراج الكلمات المفتاحية
        resume_words = set(resume_clean.split())
        jd_words = set(jd_clean.split())
        
        # إزالة الكلمات الشائعة
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'من', 'في', 'على', 'إلى', 'مع', 'هذا', 'هذه', 'ذلك', 'التي', 'التي'
        }
        
        resume_keywords = resume_words - stop_words
        jd_keywords = jd_words - stop_words
        
        # حساب التطابق
        common_keywords = resume_keywords.intersection(jd_keywords)
        
        # حساب نقاط مختلفة
        exact_match = len(common_keywords) / len(jd_keywords) * 100 if jd_keywords else 0
        
        # تطابق ضبابي للمرادفات
        fuzzy_matches = 0
        for jd_word in jd_keywords:
            for resume_word in resume_keywords:
                similarity = SequenceMatcher(None, jd_word, resume_word).ratio()
                if similarity > 0.8:  # تشابه عالي
                    fuzzy_matches += 1
                    break
        
        fuzzy_score = fuzzy_matches / len(jd_keywords) * 100 if jd_keywords else 0
        
        # النقرة النهائية
        final_score = (exact_match * 0.7) + (fuzzy_score * 0.3)
        
        return {
            'overall_match': round(final_score, 1),
            'exact_matches': len(common_keywords),
            'total_jd_keywords': len(jd_keywords),
            'common_keywords': list(common_keywords)[:10],  # أول 10 كلمات مشتركة
            'missing_keywords': list(jd_keywords - resume_keywords)[:10]
        }

    def generate_improvements(self, analysis_result, structure_info, fonts):
        """إنشاء توصيات تحسين متقدمة"""
        suggestions = []
        critical_issues = []
        
        # مشاكل في الخطوط
        problematic_fonts = [f for f in fonts if f and f not in self.ats_safe_fonts]
        if problematic_fonts:
            critical_issues.append(f"خطوط غير آمنة لـ ATS: {', '.join(problematic_fonts)}")
            suggestions.append("استخدم خطوط آمنة مثل Arial أو Calibri")
        
        # مشاكل في الهيكل
        if structure_info['tables'] > 0:
            critical_issues.append(f"يحتوي على {structure_info['tables']} جدول قد يسبب مشاكل")
            suggestions.append("حول الجداول إلى نص منسق بدلاً من جداول")
        
        if structure_info['images'] > 0:
            critical_issues.append(f"يحتوي على {structure_info['images']} صورة")
            suggestions.append("احذف الصور واستبدلها بنص وصفي")
        
        # مقترحات تحسين المحتوى
        missing_sections = analysis_result['missing']
        if missing_sections:
            for section in missing_sections:
                suggestions.append(f"أضف قسم {section} لتحسين النقرة")
        
        # مقترحات تحسين النقرة
        if analysis_result['score'] < 60:
            suggestions.extend([
                "أضف المزيد من الكلمات المفتاحية ذات الصلة",
                "اكتب إنجازات كمية بأرقام محددة",
                "حسّن وصف الخبرات المهنية"
            ])
        
        return {
            'critical_issues': critical_issues,
            'suggestions': suggestions,
            'priority_fixes': critical_issues[:3]  # أهم 3 مشاكل
        }


# إنشاء كائن المحلل
analyzer = ATSAnalyzer()

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # التحقق من وجود الملف
        if 'resume' not in request.files:
            return jsonify({'error': 'لم يتم رفع ملف'}), 400
        
        uploaded_file = request.files['resume']
        if uploaded_file.filename == '':
            return jsonify({'error': 'لم يتم اختيار ملف'}), 400
        
        # استخراج النص
        text = analyzer.extract_text_enhanced(uploaded_file)
        if not text:
            return jsonify({'error': 'فشل في استخراج النص من الملف'}), 400
        
        # تحليل الهيكل
        uploaded_file.seek(0)
        structure_info = analyzer.detect_structure_advanced(uploaded_file)
        
        # تحليل المحتوى
        content_analysis = analyzer.analyze_content_advanced(text)
        
        # كشف الخطوط
        uploaded_file.seek(0)
        fonts_used = analyzer.detect_fonts_enhanced(uploaded_file)
        
        # مطابقة الوصف الوظيفي
        job_description = request.form.get('job_description', '')
        job_match = analyzer.advanced_job_matching(text, job_description)
        
        # إنشاء التوصيات
        improvements = analyzer.generate_improvements(
            content_analysis, structure_info, fonts_used
        )
        
        # النتيجة النهائية
        result = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'file_info': {
                'name': uploaded_file.filename,
                'size': len(text),
                'word_count': len(text.split())
            },
            'ats_score': content_analysis['score'],
            'readability_score': content_analysis['readability'],
            'sections': content_analysis['sections'],
            'found_sections': content_analysis['found'],
            'missing_sections': content_analysis['missing'],
            'structure': structure_info,
            'fonts': fonts_used,
            'job_matching': job_match,
            'improvements': improvements,
            'detailed_analysis': content_analysis['detailed_analysis']
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"خطأ في التحليل: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'حدث خطأ في معالجة الملف',
            'details': str(e)
        }), 500

# إضافة method لكشف الخطوط المحسن
def detect_fonts_enhanced(self, file_storage):
    """كشف خطوط محسن"""
    fonts = set()
    filename = file_storage.filename.lower()
    file_storage.seek(0)
    
    try:
        if filename.endswith(".pdf"):
            doc = fitz.open(stream=file_storage.read(), filetype="pdf")
            for page in doc:
                blocks = page.get_text("dict").get("blocks", [])
                for block in blocks:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_name = span.get("font", "")
                            if font_name:
                                fonts.add(font_name)
            doc.close()
            
        elif filename.endswith(".docx"):
            doc = docx.Document(file_storage)
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    if run.font.name:
                        fonts.add(run.font.name)
                        
    except Exception as e:
        logger.error(f"خطأ في كشف الخطوط: {str(e)}")
    
    return list(fonts)

# إضافة الmethod للكلاس
ATSAnalyzer.detect_fonts_enhanced = detect_fonts_enhanced

@app.route('/health', methods=['GET'])
def health_check():
    """فحص صحة الخدمة"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
