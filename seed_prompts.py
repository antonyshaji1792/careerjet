from app import create_app, db
from app.services.prompt_registry import PromptRegistryService

def seed_production_prompts():
    app = create_app()
    with app.app_context():
        print("Ensuring tables exist...")
        db.create_all()
        
        print("Seeding/Ensuring default prompts...")
        PromptRegistryService.get_prompt('resume_generation')
        PromptRegistryService.get_prompt('resume_optimization')
        
        print("Production hardening complete.")

if __name__ == '__main__':
    seed_production_prompts()
