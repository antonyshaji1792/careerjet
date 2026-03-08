from app import create_app, db
from app.models import SystemConfig
import os

app = create_app()
with app.app_context():
    configs = SystemConfig.query.all()
    with open('llm_debug.log', 'w', encoding='utf-8') as f:
        f.write("--- System Config ---\n")
        for c in configs:
            val = "[ENCRYPTED]" if c.is_encrypted else c.value
            f.write(f"{c.key}: {val}\n")
        
        f.write("\n--- LLM Status ---\n")
        primary = SystemConfig.get_config_value('PRIMARY_LLM_PROVIDER')
        f.write(f"PRIMARY_LLM_PROVIDER: {primary}\n")
        
        providers = ['openai', 'openrouter', 'anthropic', 'gemini', 'groq', 'mistral', 'ollama']
        for p in providers:
            active = SystemConfig.get_config_value(f'{p.upper()}_IS_ACTIVE')
            key = SystemConfig.get_config_value(f'{p.upper()}_API_KEY')
            model = SystemConfig.get_config_value(f'{p.upper()}_MODEL')
            f.write(f"{p.upper()}: active={active}, key_configured={'YES' if key else 'NO'}, model={model}\n")
print("Done writing to llm_debug.log")
