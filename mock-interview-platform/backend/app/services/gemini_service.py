import json
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    import google.genai as genai_new
except ImportError:
    genai_new = None

from app.config import Config


class GeminiService:
    DEFAULT_MODELS = (
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
    )

    @staticmethod
    def normalize_model_name(model_name):
        """Normalize a Gemini model identifier across both SDK variants."""
        name = (model_name or '').strip().replace('\\', '/')
        if not name:
            return 'gemini-2.0-flash'
        if name.startswith('models/'):
            name = name[len('models/'):]
        if name.startswith('model/'):
            name = name[len('model/'):]
        return name or 'gemini-2.0-flash'

    @classmethod
    def model_candidates(cls, configured_model=None):
        seen = set()
        ordered = []
        for candidate in [configured_model, *cls.DEFAULT_MODELS]:
            model_name = cls.normalize_model_name(candidate)
            if model_name and model_name not in seen:
                seen.add(model_name)
                ordered.append(model_name)
        return ordered

    def __init__(self):
        api_key = Config.GOOGLE_GEMINI_API_KEY
        self.model_name = self.normalize_model_name(Config.GOOGLE_GEMINI_MODEL)
        self.model_candidates_list = self.model_candidates(self.model_name)
        self.use_genai = False
        self.genai_client = None
        self.model = None
        self.last_error = None

        if genai_new and Config.ENABLE_GEMINI and api_key and api_key != 'demo-key':
            try:
                self.genai_client = genai_new.Client(api_key=api_key)
                self.use_genai = True
                print('GeminiService: configured google.genai client')
            except Exception as exc:
                print('GeminiService: failed to configure google.genai client:', exc)
                self.genai_client = None
                self.use_genai = False

        if not self.use_genai and genai and Config.ENABLE_GEMINI and api_key and api_key != 'demo-key':
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(self.model_name)
                print('GeminiService: configured model', self.model_name)
            except Exception as exc:
                print('GeminiService: failed to configure model:', exc)
                self.model = None
        if not self.use_genai and not self.model:
            self.model = None

    @property
    def is_available(self):
        """Whether either supported Gemini client is ready for a request."""
        return bool(self.genai_client) if self.use_genai else bool(self.model)

    def _generate_json(self, prompt, max_output_tokens):
        """Request structured JSON using the active Gemini SDK."""
        last_error = None
        for model_name in self.model_candidates_list:
            try:
                if self.use_genai and self.genai_client:
                    response = self.genai_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=genai_new.types.GenerateContentConfig(
                            response_mime_type='application/json',
                            max_output_tokens=max_output_tokens,
                            temperature=0.2,
                        ),
                    )
                else:
                    if not self.model:
                        self.model = genai.GenerativeModel(model_name)
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type='application/json',
                            max_output_tokens=max_output_tokens,
                            temperature=0.2,
                        ),
                        request_options={'timeout': Config.GEMINI_TIMEOUT_SECONDS},
                    )
                text = self._extract_response_text(response)
                if text:
                    self.model_name = model_name
                    return text
                last_error = ValueError('Gemini returned an empty response')
            except Exception as exc:  # pragma: no cover - runtime SDK variance
                print(f'GeminiService._generate_json: model {model_name} failed: {exc}')
                last_error = exc
                continue

        self.last_error = last_error
        raise last_error or RuntimeError('Gemini request failed for all configured models')

    @staticmethod
    def _extract_response_text(response):
        """Read text from current and legacy Gemini response objects."""
        if response is None:
            return ''

        text = getattr(response, 'text', '') or ''
        if text:
            return str(text)

        candidates = getattr(response, 'candidates', None) or []
        if candidates:
            candidate = candidates[0]
            content = getattr(candidate, 'content', None)
            parts = getattr(content, 'parts', None) or []
            for part in parts:
                if hasattr(part, 'text') and getattr(part, 'text', None):
                    return str(part.text)
            text = ''.join(getattr(part, 'text', '') or '' for part in parts)
            if text:
                return text

        if hasattr(response, 'output') and response.output:
            output = getattr(response, 'output')
            if isinstance(output, dict):
                text = output.get('text') or output.get('content') or ''
                if text:
                    return str(text)

        if hasattr(response, 'to_dict'):
            try:
                data = response.to_dict()
                if isinstance(data, dict):
                    text = data.get('text') or data.get('content') or ''
                    if text:
                        return str(text)
            except Exception:
                pass

        return ''

    def generate_questions(self, job_role, category, difficulty, num_questions=5):
        prompt = f"""
        Generate {num_questions} {difficulty} level interview questions for a {job_role} position
        focusing on {category}. Include the expected answer for each question.

        Format as JSON:
        [
            {{
                "question": "question text",
                "expected_answer": "expected answer text"
            }}
        ]
        """

        if not self.is_available:
            print('GeminiService.generate_questions: Gemini unavailable, using fallback')
            return self.get_fallback_questions(job_role, category, num_questions)

        start = time.time()
        try:
            text = self._generate_json(prompt, max_output_tokens=1024)
            elapsed = time.time() - start
            print(f'GeminiService.generate_questions: got response in {elapsed:.2f}s; text_len={len(text)}')
            if not text:
                print('GeminiService.generate_questions: empty text, using fallback')
                return self.get_fallback_questions(job_role, category, num_questions)
            questions = self._parse_json_response(text)
            if not isinstance(questions, list):
                raise ValueError('Gemini returned questions in an invalid format')
            return questions
        except Exception as exc:
            elapsed = time.time() - start
            print(f'Error generating questions ({elapsed:.2f}s): {exc}')
            return self.get_fallback_questions(job_role, category, num_questions)

    def analyze_answer(self, question, user_answer, expected_answer):
        prompt = f"""
        Analyze this interview answer:

        Question: {question}
        Expected Answer: {expected_answer}
        User's Answer: {user_answer}

        Provide feedback on:
        1. Content accuracy
        2. Structure and clarity
        3. Areas for improvement
        4. Overall score (0-100)

        Format as JSON:
        {{
            "content_score": 85,
            "structure_score": 75,
            "clarity_score": 80,
            "overall_score": 80,
            "strengths": ["strength1", "strength2"],
            "improvements": ["improvement1", "improvement2"],
            "detailed_feedback": "Detailed feedback text"
        }}
        """

        if not self.is_available:
            print('GeminiService.analyze_answer: Gemini unavailable, using fallback')
            return self.get_fallback_feedback()

        start = time.time()
        try:
            text = self._generate_json(prompt, max_output_tokens=1024)
            elapsed = time.time() - start
            print(f'GeminiService.analyze_answer: got response in {elapsed:.2f}s; text_len={len(text)}')
            if not text:
                print('GeminiService.analyze_answer: empty text, using fallback')
                return self.get_fallback_feedback()
            feedback = self._parse_json_response(text)
            if not isinstance(feedback, dict):
                raise ValueError('Gemini returned feedback in an invalid format')
            return feedback
        except Exception as exc:
            elapsed = time.time() - start
            print(f'Error analyzing answer ({elapsed:.2f}s): {exc}')
            return self.get_fallback_feedback()

    def get_fallback_questions(self, job_role, category, num_questions=5):
        job_key = (job_role or '').lower().replace(' ', '_')
        questions_by_role = {
            'software_engineer': {
                'technical': [
                    {
                        'question': 'Explain the difference between REST and GraphQL APIs.',
                        'expected_answer': 'REST uses predefined endpoints and fixed response shapes, while GraphQL allows clients to request only the data they need and can combine multiple resources in one query.'
                    },
                    {
                        'question': 'What is the time complexity of quicksort in the worst case?',
                        'expected_answer': 'The worst-case time complexity of quicksort is O(n²), although its average and best-case performance are O(n log n).'
                    },
                    {
                        'question': 'How do you design for scalability in a backend system?',
                        'expected_answer': 'I would use horizontal scaling, stateless services, load balancing, caching, database optimization, message queues, and monitoring to support growth.'
                    },
                ],
                'behavioral': [
                    {
                        'question': 'Describe a challenging project you worked on and how you overcame obstacles.',
                        'expected_answer': 'A strong answer includes a clear challenge, the action taken, collaboration, and measurable results.'
                    },
                    {
                        'question': 'How do you handle disagreements with teammates or stakeholders?',
                        'expected_answer': 'I listen carefully, align on goals, discuss trade-offs respectfully, and work toward a technically sound and collaborative decision.'
                    },
                ],
                'general': [
                    {
                        'question': 'Why do you want to work in this role?',
                        'expected_answer': 'A good answer connects the role to the candidate’s skills, interests, and long-term goals while showing motivation for the company.'
                    },
                    {
                        'question': 'Tell me about a time you improved a process or system.',
                        'expected_answer': 'Strong answers explain the problem, the steps taken, and the measurable impact on efficiency, quality, or customer experience.'
                    },
                ],
            },
            'data_scientist': {
                'technical': [
                    {
                        'question': 'How do you evaluate a machine learning model?',
                        'expected_answer': 'I evaluate using relevant metrics, validation strategies, bias-variance analysis, and business impact while checking for overfitting and fairness.'
                    },
                    {
                        'question': 'What is the difference between supervised and unsupervised learning?',
                        'expected_answer': 'Supervised learning uses labeled data to learn mappings, while unsupervised learning finds patterns or structure in unlabeled data.'
                    },
                ],
            },
        }

        category_key = category.lower() if category else 'technical'
        pool = questions_by_role.get(job_key, {}).get(category_key) or questions_by_role.get('software_engineer', {}).get(category_key) or []
        if not pool:
            pool = [
                {
                    'question': f'What skills and experience make you a strong candidate for this {job_role} role?',
                    'expected_answer': 'Explain the most relevant skills, experience, accomplishments, and the value you would bring to the role.'
                },
                {
                    'question': f'Describe how you would approach a challenging {category} problem in this role.',
                    'expected_answer': 'A strong answer defines the problem, explains a structured approach, considers trade-offs, and describes how success would be measured.'
                },
                {
                    'question': 'Tell me about a time you learned from feedback or a setback.',
                    'expected_answer': 'Use a specific example, explain the action you took, and share the positive outcome or lesson learned.'
                },
                {
                    'question': 'How do you prioritize work when several important tasks have the same deadline?',
                    'expected_answer': 'Discuss impact, urgency, dependencies, communication with stakeholders, and how you keep progress visible.'
                },
                {
                    'question': 'What questions would you ask to understand a new project before starting?',
                    'expected_answer': 'Ask about goals, users, constraints, success metrics, timeline, stakeholders, and technical or operational risks.'
                },
            ]
        if len(pool) >= num_questions:
            return pool[:num_questions]

        generic_questions = [
            {
                'question': f'What skills and experience make you a strong candidate for this {job_role} role?',
                'expected_answer': 'Explain the most relevant skills, experience, accomplishments, and the value you would bring to the role.'
            },
            {
                'question': f'Describe how you would approach a challenging {category} problem in this role.',
                'expected_answer': 'A strong answer defines the problem, explains a structured approach, considers trade-offs, and describes how success would be measured.'
            },
            {
                'question': 'How do you prioritize work when several important tasks have the same deadline?',
                'expected_answer': 'Discuss impact, urgency, dependencies, communication with stakeholders, and how you keep progress visible.'
            },
        ]
        for question in generic_questions:
            if len(pool) >= num_questions:
                break
            if question not in pool:
                pool.append(question)
        return pool[:num_questions]

    @staticmethod
    def _parse_json_response(text):
        """Accept JSON returned either directly or inside a Markdown code fence."""
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else ''
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())

    def analyze_resume(self, resume_text):
        """Analyze a resume and provide rating and improvement suggestions."""
        
        prompt = f"""
        Analyze this resume and provide detailed feedback:

        Resume Content:
        {resume_text[:3000]}  # Limit to first 3000 characters

        Provide analysis in the following JSON format:
        {{
            "overall_score": 85,
            "sections": {{
                "formatting": {{
                    "score": 90,
                    "feedback": "Well-structured and easy to read"
                }},
                "content": {{
                    "score": 85,
                    "feedback": "Strong experience section with quantifiable achievements"
                }},
                "skills": {{
                    "score": 80,
                    "feedback": "Good technical skills listed, consider adding more soft skills"
                }},
                "experience": {{
                    "score": 88,
                    "feedback": "Clear career progression with relevant roles"
                }},
                "education": {{
                    "score": 75,
                    "feedback": "Education section is present but could include relevant coursework"
                }}
            }},
            "strengths": [
                "Strong technical skill set",
                "Quantifiable achievements with metrics",
                "Clear career progression"
            ],
            "improvements": [
                "Add a professional summary at the top",
                "Include more action verbs in experience descriptions",
                "Add relevant certifications or projects"
            ],
            "suggestions": [
                "Consider adding a LinkedIn profile link",
                "Tailor the resume for specific job applications",
                "Add keywords from job descriptions to pass ATS systems"
            ],
            "ats_optimization": {{
                "score": 78,
                "feedback": "Good use of standard formatting, but could improve keyword density"
            }},
            "detailed_feedback": "This is a solid resume with strong technical experience. The candidate has demonstrated clear career growth and achieved measurable results. To make it even stronger, consider adding a professional summary, using more action verbs, and optimizing for ATS systems by including relevant keywords from target job descriptions."
        }}

        Provide constructive, actionable feedback that will help improve the resume.
        """

        if not self.is_available:
            print('GeminiService.analyze_resume: Gemini unavailable, using fallback')
            return self.get_fallback_resume_analysis()

        start = time.time()
        try:
            text = self._generate_json(prompt, max_output_tokens=2048)
            elapsed = time.time() - start
            print(f'GeminiService.analyze_resume: got response in {elapsed:.2f}s; text_len={len(text)}')
            if not text:
                print('GeminiService.analyze_resume: empty text, using fallback')
                return self.get_fallback_resume_analysis()
            analysis = self._parse_json_response(text)
            if not isinstance(analysis, dict):
                raise ValueError('Gemini returned resume analysis in an invalid format')
            return analysis
        except Exception as exc:
            elapsed = time.time() - start
            print(f'Error analyzing resume ({elapsed:.2f}s): {exc}')
            return self.get_fallback_resume_analysis()

    def get_fallback_resume_analysis(self):
        """Provide a fallback resume analysis when Gemini is not available."""
        return {
            'overall_score': 75,
            'sections': {
                'formatting': {
                    'score': 80,
                    'feedback': 'Resume appears to be well-formatted'
                },
                'content': {
                    'score': 75,
                    'feedback': 'Content looks good, consider adding more details'
                },
                'skills': {
                    'score': 70,
                    'feedback': 'Skills section is present'
                },
                'experience': {
                    'score': 78,
                    'feedback': 'Experience section shows relevant background'
                },
                'education': {
                    'score': 72,
                    'feedback': 'Education information is included'
                }
            },
            'strengths': [
                'Clear structure and organization',
                'Relevant experience highlighted',
                'Professional presentation'
            ],
            'improvements': [
                'Add more quantifiable achievements',
                'Include a professional summary',
                'Optimize for ATS with relevant keywords'
            ],
            'suggestions': [
                'Consider adding a projects section',
                'Add links to portfolio or LinkedIn',
                'Tailor resume for specific roles'
            ],
            'ats_optimization': {
                'score': 70,
                'feedback': 'Basic ATS compatibility, could be improved with more keywords'
            },
            'detailed_feedback': 'This resume provides a good foundation with clear structure and relevant experience. To improve it further, focus on adding quantifiable achievements, a compelling professional summary, and optimizing for ATS systems by incorporating keywords from job descriptions you are targeting.'
        }

    def get_fallback_feedback(self):
        return {
            'content_score': 72,
            'structure_score': 70,
            'clarity_score': 74,
            'overall_score': 72,
            'strengths': ['Good structure and effort.', 'Relevant points are included.'],
            'improvements': ['Add a few more concrete examples.', 'Be more direct and concise in your answer.'],
            'detailed_feedback': 'Your answer showed useful understanding and a clear direction, but it would be stronger with more specific examples and tighter structure.'
        }
