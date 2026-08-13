import json
import re
import time

try:
    import google.genai as genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

# Fallback to older SDK if new one is not available
if not genai:
    try:
        import google.generativeai as genai
        types = None
    except ImportError:
        genai = None
        types = None

from app.config import Config


class GeminiService:
    DEFAULT_MODELS = (
        'gemini-3.1-flash-lite', # Best quota availability for free tier
        'gemini-3.5-flash',      # Good quality fallback
        'gemini-3.6-flash',      # Latest model (higher quota use)
        'gemini-flash-latest',   # Generic latest model fallback
    )

    @staticmethod
    def normalize_model_name(model_name):
        """Normalize a Gemini model identifier."""
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
        self.use_new_sdk = False
        self.client = None
        self.model = None
        self.last_error = None

        if not Config.ENABLE_GEMINI:
            print('GeminiService: Gemini is disabled in configuration')
            return

        if not api_key or api_key == 'demo-key' or api_key == 'YOUR_GOOGLE_GEMINI_API_KEY_HERE':
            print('GeminiService: No valid API key configured')
            return

        # Try new SDK first (google.genai)
        if genai and hasattr(genai, 'Client'):
            try:
                self.client = genai.Client(api_key=api_key)
                self.use_new_sdk = True
                print(f'GeminiService: Initialized with new google.genai SDK')
                return
            except Exception as exc:
                print(f'GeminiService: Failed to initialize with google.genai SDK: {exc}')
                self.client = None
                self.use_new_sdk = False
        
        # Fallback to legacy SDK (google.generativeai)
        if genai and hasattr(genai, 'configure'):
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.use_new_sdk = False
                print(f'GeminiService: Initialized with legacy google.generativeai SDK')
            except Exception as exc:
                print(f'GeminiService: Failed to initialize with google.generativeai SDK: {exc}')
                self.model = None
        
        if not self.client and not self.model:
            print('GeminiService: Failed to initialize any SDK')

    @property
    def is_available(self):
        """Whether either the new or legacy Gemini client is ready."""
        if self.use_new_sdk:
            return bool(self.client)
        return bool(self.model)

    def _generate_json(self, prompt, max_output_tokens):
        """Request structured JSON using Gemini API (supports both new and legacy SDKs)."""
        last_error = None
        
        for model_name in self.model_candidates_list:
            try:
                if self.use_new_sdk and self.client:
                    # Use new google.genai SDK
                    response = self.client.models.generate_content(
                        model=f'models/{model_name}',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type='application/json',
                            max_output_tokens=max_output_tokens,
                            temperature=0.3,
                        ),
                    )
                    text = self._extract_response_text_new_sdk(response)
                else:
                    # Use legacy google.generativeai SDK
                    if not self.model:
                        self.model = genai.GenerativeModel(model_name)
                    response = self.model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type='application/json',
                            max_output_tokens=max_output_tokens,
                            temperature=0.3,
                        ),
                        request_options={'timeout': Config.GEMINI_TIMEOUT_SECONDS},
                    )
                    text = self._extract_response_text(response)
                
                if text:
                    self.model_name = model_name
                    return text
                    
                last_error = ValueError('Gemini returned an empty response')
            except Exception as exc:
                print(f'GeminiService._generate_json: model {model_name} failed: {exc}')
                last_error = exc
                if not self.use_new_sdk:
                    self.model = None  # Reset model on failure to try next one
                continue

        self.last_error = last_error
        raise last_error or RuntimeError('Gemini request failed for all configured models')

    @staticmethod
    def _extract_response_text(response):
        """Extract text from Gemini response object (legacy SDK)."""
        if response is None:
            return ''

        # Try direct text attribute first
        text = getattr(response, 'text', None)
        if text:
            return str(text).strip()

        # Try candidates array
        candidates = getattr(response, 'candidates', None)
        if candidates and len(candidates) > 0:
            candidate = candidates[0]
            content = getattr(candidate, 'content', None)
            if content:
                parts = getattr(content, 'parts', None)
                if parts:
                    for part in parts:
                        part_text = getattr(part, 'text', None)
                        if part_text:
                            return str(part_text).strip()

        # Fallback for other formats
        if hasattr(response, 'result'):
            result = getattr(response, 'result', None)
            if hasattr(result, 'output'):
                output = getattr(result, 'output', None)
                if isinstance(output, str):
                    return output.strip()

        return ''

    @staticmethod
    def _extract_response_text_new_sdk(response):
        """Extract text from Gemini response object (new google.genai SDK)."""
        if response is None:
            return ''
        
        # New SDK has a text property directly
        text = getattr(response, 'text', None)
        if text:
            return str(text).strip()
        
        # Try accessing candidates
        candidates = getattr(response, 'candidates', None)
        if candidates and len(candidates) > 0:
            candidate = candidates[0]
            content = getattr(candidate, 'content', None)
            if content:
                parts = getattr(content, 'parts', None)
                if parts:
                    result_text = ''
                    for part in parts:
                        if hasattr(part, 'text'):
                            result_text += getattr(part, 'text', '')
                    if result_text:
                        return result_text.strip()
        
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
            text = self._generate_json(prompt, max_output_tokens=2048)
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
            print(f'Exception details: {type(exc).__name__}: {exc}')
            return self.get_fallback_questions(job_role, category, num_questions)

    def analyze_answer(self, question, user_answer, expected_answer, is_premium=False):
        # Premium users get more detailed coaching
        detail_level = "detailed" if is_premium else "standard"
        coaching_prompt = """
        Additionally, provide personalized AI coaching based on these areas:
        - Industry best practices
        - Communication techniques
        - Career development insights
        - Interview strategy tips
        """ if is_premium else ""

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
        {coaching_prompt}

        Format as JSON:
        {{
            "content_score": 85,
            "structure_score": 75,
            "clarity_score": 80,
            "overall_score": 80,
            "strengths": ["strength1", "strength2"],
            "improvements": ["improvement1", "improvement2"],
            "detailed_feedback": "Detailed feedback text"
            {"," + '''"premium_coaching": "Premium AI coaching insights for interview preparation"''' if is_premium else ""}
        }}
        """

        if not self.is_available:
            print('GeminiService.analyze_answer: Gemini unavailable, using fallback')
            return self.get_fallback_feedback(is_premium=is_premium)

        start = time.time()
        try:
            text = self._generate_json(prompt, max_output_tokens=2048 if is_premium else 1024)
            elapsed = time.time() - start
            print(f'GeminiService.analyze_answer: got response in {elapsed:.2f}s; text_len={len(text)}')
            if not text:
                print('GeminiService.analyze_answer: empty text, using fallback')
                return self.get_fallback_feedback(is_premium=is_premium)
            feedback = self._parse_json_response(text)
            if not isinstance(feedback, dict):
                raise ValueError('Gemini returned feedback in an invalid format')
            return feedback
        except Exception as exc:
            elapsed = time.time() - start
            print(f'Error analyzing answer ({elapsed:.2f}s): {exc}')
            print(f'Exception details: {type(exc).__name__}: {exc}')
            return self.get_fallback_feedback(is_premium=is_premium)

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
                    {
                        'question': 'Explain the bias-variance tradeoff in machine learning.',
                        'expected_answer': 'High bias models underfit the data, while high variance models overfit. The goal is to find the sweet spot that minimizes both.'
                    },
                ],
                'behavioral': [
                    {
                        'question': 'Tell me about a data science project where your insights led to business impact.',
                        'expected_answer': 'Describe the problem, your approach, the insights discovered, and the quantifiable business impact.'
                    },
                ],
                'general': [
                    {
                        'question': 'Why are you interested in data science?',
                        'expected_answer': 'Connect your background to data science interests and explain what excites you about solving problems with data.'
                    },
                ],
            },
            'product_manager': {
                'technical': [
                    {
                        'question': 'How would you approach defining success metrics for a new feature?',
                        'expected_answer': 'I would align with stakeholders on business goals, define leading and lagging indicators, set clear targets, and establish monitoring.'
                    },
                    {
                        'question': 'Describe your approach to prioritizing features in a product roadmap.',
                        'expected_answer': 'Consider business impact, user value, technical feasibility, market timing, and resource constraints while maintaining balance.'
                    },
                ],
                'behavioral': [
                    {
                        'question': 'Tell me about a time you had to decide between building what the customer asked for vs. what they actually needed.',
                        'expected_answer': 'Describe how you gathered insights, communicated findings, and made a data-informed decision that benefited the customer.'
                    },
                ],
                'general': [
                    {
                        'question': 'What makes you excited about product management?',
                        'expected_answer': 'Share your passion for solving user problems, working cross-functionally, and seeing your decisions impact customers.'
                    },
                ],
            },
            'devops_engineer': {
                'technical': [
                    {
                        'question': 'How do you design a CI/CD pipeline for reliability and speed?',
                        'expected_answer': 'I use automated testing, containerization, infrastructure-as-code, parallel builds, fast feedback loops, and monitoring.'
                    },
                    {
                        'question': 'Describe your approach to handling infrastructure outages.',
                        'expected_answer': 'Rapid incident response, communication with stakeholders, root cause analysis, and implementation of preventive measures.'
                    },
                ],
                'behavioral': [
                    {
                        'question': 'Tell me about a time you improved deployment reliability and reduced downtime.',
                        'expected_answer': 'Describe the problem, the solution implemented, tools/processes changed, and the measurable improvement in availability.'
                    },
                ],
                'general': [
                    {
                        'question': 'Why are you passionate about DevOps and infrastructure?',
                        'expected_answer': 'Discuss your interest in automation, reliability, system design, and enabling teams to ship faster.'
                    },
                ],
            },
        }

        category_key = category.lower() if category else 'technical'
        
        # Try to get questions for the specific job role and category
        pool = questions_by_role.get(job_key, {}).get(category_key, [])
        
        # If not found, try other categories for the same role
        if not pool:
            for cat in ['behavioral', 'general', 'technical']:
                if cat != category_key:
                    pool = questions_by_role.get(job_key, {}).get(cat, [])
                    if pool:
                        break
        
        # If still not found, fall back to generic but job-role-specific questions
        if not pool:
            pool = [
                {
                    'question': f'What is your experience with the key technologies and skills required for a {job_role} position?',
                    'expected_answer': 'Discuss your hands-on experience with relevant tools, frameworks, methodologies, and languages for this specific role.'
                },
                {
                    'question': f'Describe a challenging {category} problem you solved as a {job_role}.',
                    'expected_answer': 'Provide a specific example showing the problem, your approach, challenges overcome, and the outcome.'
                },
                {
                    'question': f'How do you stay current with industry trends and best practices relevant to {job_role}?',
                    'expected_answer': 'Share how you follow industry developments, pursue professional growth, and apply new knowledge.'
                },
                {
                    'question': f'Tell me about how you would measure success in a {job_role} role.',
                    'expected_answer': 'Define key performance indicators and outcomes that matter for this position and demonstrate impact.'
                },
            ]

    @staticmethod
    def _parse_json_response(text):
        """Parse JSON from response text, handling markdown code fences and common formatting issues."""
        if not text:
            raise ValueError('Empty response text cannot be parsed as JSON')
        
        cleaned = text.strip()
        
        # Remove markdown code fence if present
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]  # Remove ```json
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:]  # Remove ```
        
        # Remove closing markdown fence
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        if not cleaned:
            raise ValueError('No JSON content found after removing markdown')
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            # Try to find JSON object/array in the text
            # Look for the first { or [ and the last } or ]
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(cleaned):
                if char in ['{', '['] and start_idx == -1:
                    start_idx = i
                if char in ['}', ']']:
                    end_idx = i
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    json_str = cleaned[start_idx:end_idx+1]
                    # Fix common JSON issues
                    # Handle unescaped newlines in strings
                    json_str = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # Last resort: try to fix common JSON formatting issues
            try:
                # Try removing trailing commas
                import re
                fixed = re.sub(r',\s*([}\]])', r'\1', cleaned)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
            
            raise ValueError(f'Failed to parse JSON from response: {str(e)}')

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
            print(f'Exception details: {type(exc).__name__}: {exc}')
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

    def get_fallback_feedback(self, is_premium=False):
        feedback = {
            'content_score': 72,
            'structure_score': 70,
            'clarity_score': 74,
            'overall_score': 72,
            'strengths': ['Good structure and effort.', 'Relevant points are included.'],
            'improvements': ['Add a few more concrete examples.', 'Be more direct and concise in your answer.'],
            'detailed_feedback': 'Your answer showed useful understanding and a clear direction, but it would be stronger with more specific examples and tighter structure.'
        }
        
        if is_premium:
            feedback['premium_coaching'] = 'Pro Tip: Industry leaders emphasize structured problem-solving approaches. Consider using the STAR method (Situation, Task, Action, Result) to enhance clarity and impact in your responses. Focus on quantifiable results and business impact to stand out.'
        
        return feedback
