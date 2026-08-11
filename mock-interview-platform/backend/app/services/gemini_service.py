import json

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.config import Config


class GeminiService:
    def __init__(self):
        api_key = Config.GOOGLE_GEMINI_API_KEY
        if genai and api_key and api_key != 'demo-key':
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(Config.GOOGLE_GEMINI_MODEL)
        else:
            self.model = None

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

        if not self.model:
            return self.get_fallback_questions(job_role, category, num_questions)

        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, 'text', '')
            if not text:
                return self.get_fallback_questions(job_role, category, num_questions)
            return self._parse_json_response(text)
        except Exception as exc:
            print(f'Error generating questions: {exc}')
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

        if not self.model:
            return self.get_fallback_feedback()

        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, 'text', '')
            if not text:
                return self.get_fallback_feedback()
            return self._parse_json_response(text)
        except Exception as exc:
            print(f'Error analyzing answer: {exc}')
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

        if not self.model:
            return self.get_fallback_resume_analysis()

        try:
            response = self.model.generate_content(prompt)
            text = getattr(response, 'text', '')
            if not text:
                return self.get_fallback_resume_analysis()
            return self._parse_json_response(text)
        except Exception as exc:
            print(f'Error analyzing resume: {exc}')
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
