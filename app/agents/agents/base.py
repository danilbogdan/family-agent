from app.core.config import settings

# Mapping from our provider shorthand to pydantic-ai model id prefix
PROVIDER_MODEL_PREFIX: dict[str, str] = {
    "openai": "openai:",
    "gemini": "google-gla:",
    "openrouter": "openrouter:",
    "grok": "grok:",
}


def get_main_model() -> str:
    """Return the pydantic-ai model id string for the configured main model."""
    provider = settings.LLM_PROVIDER
    prefix = PROVIDER_MODEL_PREFIX.get(provider, "")
    model_attr = f"{provider.upper()}_MAIN_MODEL"
    model_name = getattr(settings, model_attr, "gemini-2.5-flash")
    return f"{prefix}{model_name}"


def get_lite_model() -> str:
    """Return the pydantic-ai model id string for the configured lite model."""
    provider = settings.LLM_PROVIDER
    prefix = PROVIDER_MODEL_PREFIX.get(provider, "")
    model_attr = f"{provider.upper()}_LITE_MODEL"
    model_name = getattr(settings, model_attr, "gemini-2.5-flash")
    return f"{prefix}{model_name}"


def resolve_model(model_id: str | None) -> str:
    """Resolve 'main', 'lite', or a raw model id to a pydantic-ai model string.
    - 'main' -> get_main_model()
    - 'lite' -> get_lite_model()
    - None -> get_main_model()
    - anything else -> returned as-is (allows raw pydantic-ai model strings in YAML)"""
    if model_id is None or model_id == "main":
        return get_main_model()
    if model_id == "lite":
        return get_lite_model()
    return model_id


def check_provider_key() -> bool:
    """Check that the API key for the configured LLM_PROVIDER is set.
    Returns True if key is present, False otherwise."""
    provider_key_map = {
        "openai": settings.OPENAI_API_KEY,
        "gemini": settings.GOOGLE_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
        "grok": settings.GROK_API_KEY,
    }
    key = provider_key_map.get(settings.LLM_PROVIDER)
    return bool(key)
