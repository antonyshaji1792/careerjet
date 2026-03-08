from app.extensions import db
from datetime import datetime

class ResumeSkill(db.Model):
    """
    Granular skills extracted or added to a resume.
    """
    __tablename__ = 'resume_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    
    skill_name = db.Column(db.String(100), nullable=False, index=True)
    proficiency = db.Column(db.String(50)) # e.g., Beginner, Advanced, Expert
    years_of_experience = db.Column(db.Float, nullable=True)
    
    is_extracted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'proficiency': self.proficiency,
            'years': self.years_of_experience,
            'is_extracted': self.is_extracted
        }

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
