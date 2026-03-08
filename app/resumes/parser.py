import os
import magic
import logging
from PyPDF2 import PdfReader
from docx import Document
import io

logger = logging.getLogger(__name__)

class ResumeParser:
    """
    Parses PDF and DOCX resumes into structured text.
    Validates file integrity and type.
    """
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_MIMES = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]

    def validate_file(self, file_path):
        """Validates file existence, size, and MIME type."""
        if not os.path.exists(file_path):
            return False, "File not found."
            
        if os.path.getsize(file_path) > self.MAX_FILE_SIZE:
            return False, "File over 5MB limit."
            
        try:
            mime = magic.Magic(mime=True)
            file_mime = mime.from_file(file_path)
            if file_mime not in self.ALLOWED_MIMES:
                return False, f"Unsupported file type: {file_mime}"
        except Exception as e:
            return False, f"File validation error: {str(e)}"
            
        return True, "Valid"

    def extract_text(self, file_path):
        """Extracts text from PDF or DOCX."""
        is_valid, msg = self.validate_file(file_path)
        if not is_valid:
            logger.error(msg)
            return None

        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                return self._parse_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                return self._parse_docx(file_path)
            else:
                return None
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {str(e)}")
            return None

    def _parse_pdf(self, file_path):
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text.strip()

    def _parse_docx(self, file_path):
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs]).strip()

    async def to_structured_json(self, file_path, user_id):
        """Extracts text and uses AI to structure it into JSON."""
        text = self.extract_text(file_path)
        if not text:
            return None
            
        from app.services.resume_ai import ResumeAIService
        ai_service = ResumeAIService(user_id)
        
        prompt = f"""
        Extract the following information from this resume text into valid JSON:
        - header (name, title, contact)
        - summary
        - skills (list)
        - experience (list of objects with company, role, duration, achievements)
        - education (list of objects)
        
        Resume Text:
        {text[:4000]} 
        """
        
        # Use AI to structure
        return await ai_service.generate_response(
            prompt=prompt,
            schema_check=["header", "summary", "skills", "experience"]
        )
