from app.services.gemini_service import GeminiService

service = GeminiService()
print('AVAILABLE=', service.is_available)
print('USE_NEW_SDK=', service.use_new_sdk)
print('MODEL=', service.model_name)
resp = service.generate_questions(
    job_role='Software Engineer',
    category='technical',
    difficulty='medium',
    num_questions=2,
)
print('COUNT=', len(resp))
print(resp[0])
