from app import create_app, db
from app.models import SystemConfig

app = create_app()
with app.app_context():
    SystemConfig.set_config_value('PRIMARY_LLM_PROVIDER', 'openrouter')
    # Also ensure OpenRouter is active
    SystemConfig.set_config_value('OPENROUTER_IS_ACTIVE', 'true')
    # And maybe disable Ollama explicitly if it's primary but not working
    SystemConfig.set_config_value('OLLAMA_IS_ACTIVE', 'false')
    db.session.commit()
    print("Successfully updated LLM settings: Primary=OpenRouter, OpenRouter=Active, Ollama=Inactive")
