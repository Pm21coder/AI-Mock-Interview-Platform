from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request, current_app
import os

from app import mongo
from app.services.gemini_service import GeminiService
from app.services.subscription_service import SubscriptionService
from app.utils.auth import token_required

resume_bp = Blueprint('resume', __name__)
gemini_service = GeminiService()
subscription_service = SubscriptionService()
# Keeps guest-mode resume results available for the current backend process
# when MongoDB cannot be reached during local development.
demo_resumes = {}

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@resume_bp.route('/upload', methods=['POST'])
@token_required
def upload_resume():
    """Upload a resume file (PDF, DOCX, or TXT) and analyze it with Gemini AI."""

    if not request.current_user or not hasattr(request.current_user, 'get'):
        return jsonify({'error': 'Authentication required'}), 401

    user_id = str(request.current_user.get('_id', 'guest'))
    if not subscription_service.has_feature(user_id, 'resume_review'):
        return jsonify({
            'error': 'Resume review is only available on the Pro plan.',
            'required_tier': 'pro',
            'message': 'Upgrade to Pro to unlock resume analysis.'
        }), 403

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Invalid file type. Please upload PDF, DOCX, or TXT files only.'}), 400
    
    try:
        # Save the file
        filename = f"{uuid4()}{file_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Extract text from file
        resume_text = extract_text_from_file(filepath, file_ext)
        
        if not resume_text or len(resume_text.strip()) < 50:
            return jsonify({'error': 'Could not extract sufficient text from the resume. Please ensure the file is not empty or corrupted.'}), 400
        
        # Analyze resume with Gemini AI
        analysis = gemini_service.analyze_resume(resume_text)
        
        # Save analysis to database
        resume_document = {
            '_id': str(uuid4()),
            'user_id': str(request.current_user.get('_id', 'guest')),
            'filename': file.filename,
            'file_path': filepath,
            'resume_text': resume_text[:1000],  # Store first 1000 chars
            'analysis': analysis,
            'uploaded_at': datetime.utcnow(),
        }
        demo_resumes[resume_document['_id']] = resume_document
        
        try:
            mongo.db.resumes.insert_one(resume_document)
        except Exception:
            # If MongoDB is not available, continue without saving
            pass
        
        return jsonify({
            'success': True,
            'resume_id': resume_document['_id'],
            'analysis': analysis
        })
        
    except Exception as exc:
        return jsonify({'error': f'Failed to process resume: {str(exc)}'}), 500


def extract_text_from_file(filepath, extension):
    """Extract text content from uploaded resume file."""
    
    try:
        if extension == '.txt':
            # Plain text file
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif extension == '.pdf':
            # Try to extract text from PDF
            try:
                import PyPDF2
                with open(filepath, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in pdf_reader.pages:
                        text += page.extract_text() or ''
                    return text
            except ImportError:
                return "PDF text extraction requires PyPDF2 library. Please install it with: pip install PyPDF2"
        
        elif extension in ['.docx', '.doc']:
            # Try to extract text from DOCX
            try:
                import docx
                doc = docx.Document(filepath)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                return text
            except ImportError:
                return "DOCX text extraction requires python-docx library. Please install it with: pip install python-docx"
        
        else:
            return f"Unsupported file format: {extension}"
    
    except Exception as e:
        return f"Error extracting text: {str(e)}"


@resume_bp.route('/analysis/<resume_id>', methods=['GET'])
@token_required
def get_resume_analysis(resume_id):
    """Retrieve a previously analyzed resume."""
    
    try:
        user_id = str(request.current_user.get('_id', 'guest'))
        resume = demo_resumes.get(resume_id)
        if resume and resume['user_id'] != user_id:
            resume = None

        if not resume and current_app.config.get('MONGO_AVAILABLE', False):
            resume = mongo.db.resumes.find_one({
                '_id': resume_id,
                'user_id': user_id,
            })
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404

        uploaded_at = resume.get('uploaded_at')
        if not isinstance(uploaded_at, str) and hasattr(uploaded_at, 'isoformat'):
            uploaded_at = uploaded_at.isoformat()

        return jsonify({
            'resume_id': str(resume['_id']),
            'filename': resume['filename'],
            'analysis': resume['analysis'],
            'uploaded_at': uploaded_at
        })
    
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@resume_bp.route('/history', methods=['GET'])
@token_required
def get_resume_history():
    """Get resume analysis history for the current user."""

    user_id = str(request.current_user.get('_id', 'guest'))
    if current_app.config.get('MONGO_AVAILABLE', False):
        try:
            resumes = list(mongo.db.resumes.find(
                {'user_id': user_id},
                {'_id': 1, 'filename': 1, 'analysis': 1, 'uploaded_at': 1}
            ).sort('uploaded_at', -1).limit(10))
        except Exception:
            resumes = []
    else:
        resumes = [
            resume for resume in demo_resumes.values()
            if resume['user_id'] == user_id
        ]
        resumes.sort(key=lambda resume: resume['uploaded_at'], reverse=True)
        resumes = resumes[:10]

    def _format_uploaded_at(uploaded_at):
        if isinstance(uploaded_at, str):
            return uploaded_at
        if hasattr(uploaded_at, 'isoformat'):
            return uploaded_at.isoformat()
        return None

    return jsonify({
        'resumes': [
            {
                'id': str(resume['_id']),
                'filename': resume['filename'],
                'overall_score': resume.get('analysis', {}).get('overall_score', 0),
                'uploaded_at': _format_uploaded_at(resume.get('uploaded_at')),
            }
            for resume in resumes
        ]
    })
