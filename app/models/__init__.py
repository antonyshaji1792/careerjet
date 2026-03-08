from app.extensions import db, login_manager, migrate, csrf
from .user import User, UserProfile, Schedule, WebsitePreference
from .subscription import Plan, Subscription
from .jobs import JobPost, JobMatch, Application, LinkedInJob, NaukriJob, JobAlert
from .credentials import LinkedInCredentials, NaukriCredentials, PlatformCredential
from .config import SystemConfig, AnswerCache, CoverLetter
from .prompt_version import PromptVersion
from .ai_usage import AIUsageLog
from .decision_log import ResumeDecisionLog
from .user_action_log import UserActionLog
from .audit_log import AuditLog
from .resume import Resume, ResumeOptimization
from .resume_version import ResumeVersion
from .resume_skill import ResumeSkill
from .profile import (
    ProfileHeadline, KeySkill, Employment, Education, ITSkill, 
    Project, ProfileSummary, Accomplishment, PersonalDetails, 
    Language, DiversityInfo, CareerProfile
)
from .interview import (
    AIInterview, AIInterviewQuestion, AIInterviewAnswer, 
    AIInterviewSkillGap, AIInterviewSummary
)
from .video_interview import (
    AIVideoInterview, AIVideoQuestion, AIVideoAnswer, 
    AIVideoEvaluation, AIVideoSummary
)
from .credits import CreditWallet, CreditTransaction
from .contact import ContactThread, ContactMessage
