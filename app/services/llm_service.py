import logging
import asyncio
import os
import httpx
import json
from app.models import SystemConfig

logger = logging.getLogger(__name__)

async def ask_ai(prompt, system_prompt="You are a helpful assistant.", max_tokens=1000, temperature=0.7, provider_override=None, credentials_override=None):
    """
    Unified interface for AI calls. Provider is determined by the global SystemConfig.
    Only active providers are used.
    """
    if provider_override:
        provider = provider_override
    else:
        primary = SystemConfig.get_config_value('PRIMARY_LLM_PROVIDER', 'openai').lower()
        
        # Check if primary is active
        is_primary_active = SystemConfig.get_config_value(f'{primary.upper()}_IS_ACTIVE', 'true') == 'true'
        
        provider = primary
        if not is_primary_active:
            logger.info(f"Primary provider {primary} is disabled. Looking for an active fallback...")
            # Fallback to first active and configured provider
            fallbacks = ['openai', 'openrouter', 'anthropic', 'gemini', 'groq', 'mistral', 'ollama']
            found_fallback = False
            for fallback in fallbacks:
                # Check if active
                is_active = SystemConfig.get_config_value(f'{fallback.upper()}_IS_ACTIVE', 'true') == 'true'
                if not is_active:
                    continue
                
                # Check if configured (has key/url)
                if fallback == 'ollama':
                    has_config = SystemConfig.get_config_value('OLLAMA_BASE_URL') is not None
                else:
                    has_config = SystemConfig.get_config_value(f'{fallback.upper()}_API_KEY') is not None
                
                if has_config:
                    provider = fallback
                    logger.info(f"Using fallback provider: {fallback}")
                    found_fallback = True
                    break
            
            if not found_fallback:
                logger.error("No active and configured AI providers found.")
                raise ValueError("No AI providers are currently enabled and configured in the system configuration.")

    # Route to provider logic
    if provider == 'openai':
        return await _call_openai(prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'openrouter':
        return await _call_openai_compatible(provider, "https://openrouter.ai/api/v1", prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'groq':
        return await _call_openai_compatible(provider, "https://api.groq.com/openai/v1", prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'mistral':
        return await _call_openai_compatible(provider, "https://api.mistral.ai/v1", prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'anthropic':
        return await _call_anthropic(prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'gemini':
        return await _call_gemini(prompt, system_prompt, max_tokens, temperature, credentials_override)
    elif provider == 'ollama':
        return await _call_ollama(prompt, system_prompt, max_tokens, temperature, credentials_override)
    else:
        return await _call_openai(prompt, system_prompt, max_tokens, temperature, credentials_override)

async def _call_openai_compatible(provider, base_url, prompt, system_prompt, max_tokens, temperature, creds=None):
    """Universal caller for OpenAI-compatible APIs with transient error retries"""
    max_retries = 2
    retry_delay = 1.0
    
    for attempt in range(max_retries + 1):
        try:
            api_key = (creds.get('api_key') if creds else None) or SystemConfig.get_config_value(f'{provider.upper()}_API_KEY')
            model = (creds.get('model') if creds else None) or SystemConfig.get_config_value(f'{provider.upper()}_MODEL')
            
            if not model:
                if provider == 'openrouter': model = 'anthropic/claude-3.5-sonnet'
                elif provider == 'groq': model = 'llama3-70b-8192'
                elif provider == 'mistral': model = 'mistral-large-latest'

            if not api_key:
                raise ValueError(f"{provider.capitalize()} API Key not configured.")
                
            # Internal logic for the actual call
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_headers={
                        "HTTP-Referer": SystemConfig.get_config_value('OPENROUTER_REFERER', 'https://careerjet.ai'),
                        "X-Title": SystemConfig.get_config_value('OPENROUTER_TITLE', 'CareerJet AI')
                    } if provider == 'openrouter' else None
                )
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    return {
                        "text": response.choices[0].message.content.strip(),
                        "model": response.model,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        } if hasattr(response, 'usage') else {}
                    }
            except (ImportError, Exception) as sdk_err:
                # Handle specific transient errors in SDK
                err_msg = str(sdk_err).lower()
                if any(x in err_msg for x in ['502', '503', '504', 'network', 'timeout', 'connection lost']) and attempt < max_retries:
                    logger.warning(f"{provider} transient SDK error (Attempt {attempt+1}): {str(sdk_err)}. Retrying...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                # Fallback to direct HTTPX call
                async with httpx.AsyncClient(timeout=60.0) as http_client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    if provider == 'openrouter':
                        headers.update({
                            "HTTP-Referer": SystemConfig.get_config_value('OPENROUTER_REFERER', 'https://careerjet.ai'),
                            "X-Title": SystemConfig.get_config_value('OPENROUTER_TITLE', 'CareerJet AI')
                        })
                    
                    payload = {
                        "model": model,
                        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                    
                    resp = await http_client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    
                    # Handle 5xx or specific OpenRouter 502 inside JSON
                    if resp.status_code >= 500 and attempt < max_retries:
                        logger.warning(f"{provider} HTTP {resp.status_code} (Attempt {attempt+1}). Retrying...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                        continue

                    resp_json = resp.json()
                    if 'error' in resp_json:
                        err_code = resp_json.get('error', {}).get('code')
                        if str(err_code) in ['502', '503', '504'] and attempt < max_retries:
                            logger.warning(f"{provider} API {err_code} (Attempt {attempt+1}). Retrying...")
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                            continue
                        raise ValueError(f"{provider} API Error: {resp_json['error']}")
                        
                    if 'choices' in resp_json and len(resp_json['choices']) > 0:
                        return {
                            "text": resp_json['choices'][0]['message']['content'].strip(),
                            "model": resp_json.get('model', model),
                            "usage": resp_json.get('usage', {})
                        }
                    raise ValueError(f"{provider} returned malformed response.")
                    
        except Exception as e:
            if attempt < max_retries and any(x in str(e).lower() for x in ['502', '503', '504', 'network', 'connection lost']):
                logger.warning(f"{provider} generic catch error (Attempt {attempt+1}): {str(e)}. Retrying...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                continue
            logger.error(f"{provider.capitalize()} Terminal Error: {str(e)}")
            raise

async def _call_openai(prompt, system_prompt, max_tokens, temperature, creds=None):
    try:
        api_key = (creds.get('api_key') if creds else None) or SystemConfig.get_config_value('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
        model = (creds.get('model') if creds else None) or SystemConfig.get_config_value('OPENAI_MODEL', 'gpt-4o')
        
        if not api_key:
            raise ValueError("OpenAI API Key not configured.")
            
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return {
                "text": response.choices[0].message.content.strip(),
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        else:
            raise ValueError("OpenAI returned an unexpected response structure.")
    except Exception as e:
        logger.error(f"OpenAI Error: {str(e)}")
        raise

async def _call_ollama(prompt, system_prompt, max_tokens, temperature, creds=None):
    try:
        base_url = (creds.get('api_key') if creds else None) or SystemConfig.get_config_value('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = (creds.get('model') if creds else None) or SystemConfig.get_config_value('OLLAMA_MODEL', 'llama3')
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )
            response.raise_for_status()
            resp_json = response.json()
            if 'message' in resp_json and 'content' in resp_json['message']:
                return {
                    "text": resp_json['message']['content'].strip(),
                    "model": resp_json.get('model', model),
                    "usage": {
                        "prompt_tokens": resp_json.get('prompt_eval_count', 0),
                        "completion_tokens": resp_json.get('eval_count', 0),
                        "total_tokens": resp_json.get('prompt_eval_count', 0) + resp_json.get('eval_count', 0)
                    }
                }
            else:
                raise ValueError("Ollama returned an unexpected response structure.")
    except Exception as e:
        logger.error(f"Ollama Error: {str(e)}")
        raise

async def _call_anthropic(prompt, system_prompt, max_tokens, temperature, creds=None):
    try:
        import anthropic
        api_key = (creds.get('api_key') if creds else None) or SystemConfig.get_config_value('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        model = (creds.get('model') if creds else None) or SystemConfig.get_config_value('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620')
        
        if not api_key:
            raise ValueError("Anthropic API Key not configured.")
            
        client = anthropic.Anthropic(api_key=api_key)
        response = await asyncio.to_thread(
            client.messages.create,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return {
            "text": response.content[0].text,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    except Exception as e:
        logger.error(f"Anthropic Error: {str(e)}")
        raise

async def _call_gemini(prompt, system_prompt, max_tokens, temperature, creds=None):
    try:
        import google.generativeai as genai
        api_key = (creds.get('api_key') if creds else None) or SystemConfig.get_config_value('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        model_name = (creds.get('model') if creds else None) or SystemConfig.get_config_value('GEMINI_MODEL', 'gemini-1.5-flash')
        
        if not api_key:
            raise ValueError("Gemini API Key not configured.")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        response = await asyncio.to_thread(
            model.generate_content,
            f"{system_prompt}\n\n{prompt}",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        # Gemini usage is tricky to get directly sometimes, we might need to count or use response metadata
        usage = {}
        if hasattr(response, 'usage_metadata'):
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
            
        return {
            "text": response.text,
            "model": model_name,
            "usage": usage
        }
    except Exception as e:
        logger.error(f"Gemini Error: {str(e)}")
        raise
