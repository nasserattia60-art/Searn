"""
AI-powered quiz generation service using Google Gemini API
Based on learning science principles: Active Recall, Spaced Repetition, Deep Encoding
"""

import json
import os
import re
from typing import List, Dict, Any
import google.generativeai as genai


class QuizGenerationService:
    """Service to generate quizzes from lesson subtitles using AI"""
    
    def __init__(self, api_key: str = None):
        """Initialize Gemini API client"""
        if api_key is None:
            api_key = os.getenv('GOOGLE_API_KEY')
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model_name = 'gemini-1.5-flash'
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 64,
            'max_output_tokens': 2048,
            'response_mime_type': 'application/json',
        }
    
    def extract_subtitles_text(self, subtitles_json: str) -> str:
        """Extract clean text from subtitles JSON"""
        try:
            if isinstance(subtitles_json, str):
                subtitles = json.loads(subtitles_json)
            else:
                subtitles = subtitles_json
            
            # Extract text from subtitles list
            if isinstance(subtitles, list):
                texts = [item.get('text', '') for item in subtitles]
            elif isinstance(subtitles, dict) and 'subtitles' in subtitles:
                texts = [item.get('text', '') for item in subtitles['subtitles']]
            else:
                return ""
            
            return " ".join(texts).strip()
        except (json.JSONDecodeError, TypeError):
            return subtitles_json if isinstance(subtitles_json, str) else ""
    
    def generate_quiz(self, lesson_title: str, subtitles_json: str, 
                     num_questions: int = 5, language: str = 'ar') -> Dict[str, Any]:
        """
        Generate quiz questions from lesson subtitles using Gemini AI
        
        Args:
            lesson_title: Title of the lesson
            subtitles_json: JSON string of subtitles
            num_questions: Number of questions to generate (default: 5)
            language: Language for questions ('ar' for Arabic, 'en' for English)
        
        Returns:
            Dictionary with quiz data including questions and answers
        """
        
        # Extract text from subtitles
        subtitles_text = self.extract_subtitles_text(subtitles_json)
        
        if not subtitles_text or len(subtitles_text) < 50:
            raise ValueError("Insufficient subtitle content to generate quiz")
        
        # Truncate if too long (Gemini has context limits)
        if len(subtitles_text) > 3000:
            subtitles_text = subtitles_text[:3000]
        
        # Build prompt based on learning science principles
        lang_instruction = "Arabic (العربية)" if language == 'ar' else "English"
        
        prompt = f"""أنت معلم خبير متخصص في تصميم الاختبارات التعليمية باستخدام مبادئ العلوم المعرفية.

استخدم المبادئ التعليمية التالية:
1. الاستدعاء النشط (Active Recall): اطرح أسئلة تتطلب استدعاء وتطبيق المعلومات
2. الترميز العميق (Deep Encoding): اطرح أسئلة عن المفاهيم والتطبيقات، وليس مجرد الحفظ
3. التعلم التوليدي (Generative Learning): اطرح أسئلة تتطلب من المتعلم إنشاء أو ربط المعلومات

موضوع الدرس: {lesson_title}

محتوى الفيديو:
{subtitles_text}

أنشئ {num_questions} أسئلة اختبار بصيغة JSON باللغة {lang_instruction}.

متطلبات الإخراج:
1. 60% من الأسئلة يجب أن تكون اختيار من متعدد (Multiple Choice)
2. 20% من الأسئلة يجب أن تكون صح/خطأ (True/False)  
3. 20% من الأسئلة يجب أن تكون إجابة قصيرة (Short Answer)
4. كل سؤال يجب أن يستهدف مستوى تصنيفي مختلف من تصنيف بلوم
5. أضف شرحاً تعليمياً لكل سؤال يساعد المتعلم على الفهم العميق

الصيغة المطلوبة (JSON فقط، بدون نص إضافي):
{{
    "quiz_title": "عنوان الاختبار",
    "description": "وصف الاختبار",
    "total_questions": {num_questions},
    "questions": [
        {{
            "question_number": 1,
            "question_text": "نص السؤال",
            "question_type": "multiple_choice|true_false|short_answer",
            "difficulty_level": "easy|medium|hard",
            "bloom_level": "remember|understand|apply|analyze|evaluate|create",
            "explanation": "شرح تعليمي مفصل للإجابة الصحيحة",
            "answers": [
                {{
                    "answer_text": "الخيار الأول",
                    "is_correct": true
                }},
                {{
                    "answer_text": "الخيار الثاني",
                    "is_correct": false
                }}
            ]
        }}
    ]
}}

تأكد أن:
- الأسئلة تقيس الفهم الحقيقي للمحتوى
- الأسئلة متوازنة في الصعوبة
- الشروحات تساعد على الفهم العميق والترميز الجيد
- اللغة واضحة وسهلة الفهم
"""
        
        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=self.generation_config,
                system_instruction="""أنت متخصص في التعليم والتقييم. 
                أنشئ أسئلة اختبارات عالية الجودة تستند إلى مبادئ العلوم المعرفية والتعلم الفعّال.
                تأكد من إرجاع JSON صحيح فقط بدون نص إضافي."""
            )
            
            response = model.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Try to extract JSON if there's extra text
            if not response_text.startswith('{'):
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group()
            
            quiz_data = json.loads(response_text)
            return quiz_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response as JSON: {e}")
            print(f"Response: {response.text}")
            raise ValueError("AI response is not valid JSON")
        except Exception as e:
            print(f"Error generating quiz with AI: {e}")
            raise
    
    def validate_quiz_structure(self, quiz_data: Dict[str, Any]) -> bool:
        """Validate that quiz data has the correct structure"""
        required_fields = ['quiz_title', 'questions']
        
        for field in required_fields:
            if field not in quiz_data:
                return False
        
        if not isinstance(quiz_data['questions'], list):
            return False
        
        if len(quiz_data['questions']) == 0:
            return False
        
        for question in quiz_data['questions']:
            if 'question_text' not in question or 'question_type' not in question:
                return False
            
            if question['question_type'] == 'multiple_choice':
                if 'answers' not in question or len(question['answers']) < 2:
                    return False
                if not any(a.get('is_correct') for a in question['answers']):
                    return False
        
        return True
    
    def get_test_quiz(self) -> Dict[str, Any]:
        """Return a test quiz for demonstration purposes"""
        return {
            "quiz_title": "اختبار تجريبي",
            "description": "اختبار تجريبي لاختبار النظام",
            "total_questions": 3,
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "ما هو مفهوم الاستدعاء النشط في التعليم؟",
                    "question_type": "multiple_choice",
                    "difficulty_level": "easy",
                    "bloom_level": "understand",
                    "explanation": "الاستدعاء النشط هو استرجاع المعلومات من الذاكرة بنشاط بدلاً من القراءة السلبية",
                    "answers": [
                        {
                            "answer_text": "استرجاع المعلومات من الذاكرة بنشاط",
                            "is_correct": True
                        },
                        {
                            "answer_text": "قراءة المادة مرات متعددة",
                            "is_correct": False
                        },
                        {
                            "answer_text": "حفظ المعلومات ميكانيكياً",
                            "is_correct": False
                        }
                    ]
                },
                {
                    "question_number": 2,
                    "question_text": "التكرار المتباعد يقلل من سرعة منحنى النسيان",
                    "question_type": "true_false",
                    "difficulty_level": "medium",
                    "bloom_level": "understand",
                    "explanation": "صحيح - المراجعة المنتظمة والموزعة في الزمن تحسن الاحتفاظ بالمعلومات",
                    "answers": [
                        {
                            "answer_text": "صحيح",
                            "is_correct": True
                        },
                        {
                            "answer_text": "خطأ",
                            "is_correct": False
                        }
                    ]
                },
                {
                    "question_number": 3,
                    "question_text": "اشرح كيفية استخدام بطاقات المراجعة في التكرار المتباعد",
                    "question_type": "short_answer",
                    "difficulty_level": "hard",
                    "bloom_level": "apply",
                    "explanation": "بطاقات المراجعة توفر طريقة فعّالة لاختبار النفس وتطبيق التكرار المتباعد تلقائياً",
                    "answers": []
                }
            ]
        }
