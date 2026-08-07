"""Mem0 L2 memory initialization utilities.

Extracted from _app.py to break the circular import between
_lifespan.py and _app.py. Both modules now import from here.
"""


def _check_ollama_available(base_url: str = "http://localhost:11434") -> bool:
    """Check if an Ollama server is reachable."""
    try:
        import ollama
        client = ollama.Client(host=base_url)
        client.list()
        return True
    except Exception:
        return False


def _resolve_mem0_llm(mem0_cfg, logger) -> tuple:
    """Resolve the best available LLM provider for Mem0.

    Priority: configured provider > OPENAI_API_KEY env > Ollama server > none.
    Returns: (provider, model, api_key_or_url, source_label)
    """
    import os

    # 1. Check configured provider
    if mem0_cfg.llm_provider == "ollama":
        url = mem0_cfg.llm_base_url or "http://localhost:11434"
        if _check_ollama_available(url):
            return ("ollama", mem0_cfg.llm_model, url, "Ollama (configured)")
        logger.info("Ollama server not reachable at %s", url)
    elif mem0_cfg.llm_provider in ("openai", "deepseek"):
        api_key = mem0_cfg.llm_api_key or os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            return (mem0_cfg.llm_provider, mem0_cfg.llm_model, api_key,
                    f"{mem0_cfg.llm_provider.upper()} API (configured)")
        logger.info("No API key for %s", mem0_cfg.llm_provider)
    elif mem0_cfg.llm_provider == "lmstudio":
        return ("lmstudio", mem0_cfg.llm_model,
                mem0_cfg.llm_base_url or "http://localhost:1234/v1",
                "LM Studio (configured)")

    # 2. Fallback: OpenAI API key
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        logger.info("Falling back to OpenAI API (OPENAI_API_KEY detected)")
        return ("openai", "gpt-4o-mini", openai_key, "OpenAI API (auto-detected)")

    # 3. Fallback: Ollama server
    if _check_ollama_available():
        logger.info("Falling back to Ollama (server detected)")
        return ("ollama", "qwen2.5:7b", "http://localhost:11434", "Ollama (auto-detected)")

    # 4. Nothing available
    return ("none", "", "", "")


def _build_mem0_llm_for(provider: str, model: str, key_or_url: str, logger) -> dict:
    """Build Mem0 LLM config from resolved provider parameters."""
    if provider == "ollama":
        return {
            "provider": "ollama",
            "config": {
                "model": model,
                "ollama_base_url": key_or_url,
            },
        }

    if provider in ("openai", "deepseek"):
        base_url = "https://api.deepseek.com/v1" if provider == "deepseek" else ""
        result = {
            "provider": "openai",
            "config": {"model": model, "api_key": key_or_url},
        }
        if base_url:
            result["config"]["openai_base_url"] = base_url
        return result

    if provider == "lmstudio":
        return {
            "provider": "openai",
            "config": {
                "model": model,
                "openai_base_url": key_or_url,
                "api_key": "lm-studio",
            },
        }

    logger.warning("Unknown Mem0 LLM provider '%s', falling back to ollama", provider)
    return {
        "provider": "ollama",
        "config": {
            "model": "qwen2.5:7b",
            "ollama_base_url": "http://localhost:11434",
        },
    }


def _build_mem0_llm_config(mem0_cfg, logger) -> dict:
    """Build Mem0 LLM config from settings (used by _lifespan.py fallback)."""
    import os
    provider = mem0_cfg.llm_provider
    model = mem0_cfg.llm_model or "qwen2.5:7b"
    key_or_url = ""
    if provider == "ollama":
        key_or_url = mem0_cfg.llm_base_url or "http://localhost:11434"
    elif provider in ("openai", "deepseek"):
        key_or_url = mem0_cfg.llm_api_key or os.environ.get("OPENAI_API_KEY", "")
    elif provider == "lmstudio":
        key_or_url = mem0_cfg.llm_base_url or "http://localhost:1234/v1"
    return _build_mem0_llm_for(provider, model, key_or_url, logger)


def _build_mem0_embedder_config(mem0_cfg, logger) -> dict:
    """Build Mem0 Embedder provider config from settings."""
    import os
    provider = mem0_cfg.embedder_provider
    model = mem0_cfg.embedder_model or "BAAI/bge-small-en-v1.5"

    if provider == "ollama":
        base_url = mem0_cfg.embedder_base_url or "http://localhost:11434"
        return {
            "provider": "ollama",
            "config": {
                "model": model,
                "ollama_base_url": base_url,
            },
        }

    if provider == "openai":
        api_key = mem0_cfg.embedder_api_key or os.environ.get("OPENAI_API_KEY", "")
        base_url = mem0_cfg.embedder_base_url or ""
        embed_model = model if model != "nomic-embed-text" else "text-embedding-3-small"
        return {
            "provider": "openai",
            "config": {
                "model": embed_model,
                "api_key": api_key,
                **({"openai_base_url": base_url} if base_url else {}),
            },
        }

    if provider == "huggingface":
        return {
            "provider": "huggingface",
            "config": {
                "model": model,
            },
        }

    if provider == "fastembed":
        # fastembed runs locally, downloads models from HuggingFace automatically
        # Default model: BAAI/bge-small-en-v1.5 (384 dims, fast, good quality)
        return {
            "provider": "fastembed",
            "config": {
                "model": model or "BAAI/bge-small-en-v1.5",
            },
        }

    logger.warning("Unknown Mem0 embedder provider '%s', falling back to fastembed", provider)
    return {
        "provider": "fastembed",
        "config": {
            "model": "BAAI/bge-small-en-v1.5",
        },
    }


def _patch_openai_embeddings_for_voyage(logger):
    """Monkey-patch openai embeddings.create to strip encoding_format.

    Voyage AI API rejects encoding_format="float" (only accepts "base64").
    OpenAI Python SDK sends "float" by default, so we intercept and remove it
    for Voyage AI compatibility.
    """
    try:
        import openai
        # Patch async version (used by Mem0 and our AsyncClient)
        _orig_async_create = openai.resources.embeddings.AsyncEmbeddings.create
        async def _patched_async_create(self, *args, **kwargs):
            kwargs.pop("encoding_format", None)
            return await _orig_async_create(self, *args, **kwargs)
        openai.resources.embeddings.AsyncEmbeddings.create = _patched_async_create

        # Patch sync version
        _orig_create = openai.resources.embeddings.Embeddings.create
        def _patched_create(self, *args, **kwargs):
            kwargs.pop("encoding_format", None)
            return _orig_create(self, *args, **kwargs)
        openai.resources.embeddings.Embeddings.create = _patched_create

        logger.info("Patched openai embeddings to strip encoding_format for Voyage AI compatibility")
    except Exception as e:
        logger.warning("Failed to patch openai embeddings: %s", e)


def init_mem0_for_manager(memory_manager, settings) -> None:
    """Initialize Mem0 L2 semantic memory with smart provider auto-detection.

    Automatically detects the best available LLM:
      1. Configured provider (SKPL_MEM0_LLM_PROVIDER)
      2. OPENAI_API_KEY environment variable
      3. Ollama server on localhost:11434
      4. Graceful disable if nothing is available

    Embedding uses fastembed by default (local, no API key needed).
    """
    import os
    from pathlib import Path

    logger = __import__("logging").getLogger(__name__)
    mem0_cfg = settings.mem0

    if not mem0_cfg.enabled:
        logger.info("Mem0 L2 memory is disabled (SKPL_MEM0_ENABLED=false)")
        return

    try:
        from mem0 import AsyncMemory
    except ImportError as e:
        logger.warning("Mem0 package not installed, L2 memory unavailable: %s", e)
        return

    data_dir = Path(settings.core.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    chroma_path = mem0_cfg.chroma_path or str(data_dir / "mem0_chroma")
    chroma_collection = mem0_cfg.chroma_collection
    history_db_path = mem0_cfg.history_db_path or str(data_dir / "mem0_history.db")

    # ── Resolve LLM provider (with auto-fallback) ─────────────────────
    llm_provider, llm_model, llm_key_or_url, llm_source = _resolve_mem0_llm(
        mem0_cfg, logger
    )

    if llm_provider == "none":
        logger.warning(
            "Mem0 L2 disabled: no LLM provider available. Choose one:\n"
            "  (A) Install Ollama: https://ollama.com/download → ollama pull qwen2.5:7b\n"
            "  (B) Set OpenAI key: $env:OPENAI_API_KEY='sk-...' or SKPL_MEM0_LLM_PROVIDER=openai"
        )
        return

    llm_config = _build_mem0_llm_for(llm_provider, llm_model, llm_key_or_url, logger)
    # ── Embedder: use configured provider (Voyage AI / OpenAI / fastembed) ──
    embedder_config = _build_mem0_embedder_config(mem0_cfg, logger)

    if mem0_cfg.vector_store_provider == "qdrant":
        vector_store_config = {
            "provider": "qdrant",
            "config": {
                "collection_name": chroma_collection,
                "host": "localhost",
                "port": 6333,
            },
        }
    else:
        vector_store_config = {
            "provider": "chroma",
            "config": {
                "collection_name": chroma_collection,
                "path": chroma_path,
            },
        }

    mem0_config: dict = {
        "vector_store": vector_store_config,
        "llm": llm_config,
        "embedder": embedder_config,
        "history_db_path": history_db_path,
    }

    logger.info(
        "Mem0: llm=%s/%s (source=%s), embedder=%s/%s, vector_store=%s",
        llm_provider, llm_model, llm_source,
        mem0_cfg.embedder_provider, mem0_cfg.embedder_model,
        mem0_cfg.vector_store_provider,
    )

    try:
        # ── Monkey-patch: strip encoding_format for Voyage AI compatibility ──
        _patch_openai_embeddings_for_voyage(logger)
        from mem0.configs.base import MemoryConfig
        client = AsyncMemory(config=MemoryConfig(**mem0_config))
        memory_manager.connect_mem0(client)
        logger.info("Mem0 L2 memory initialized (LLM: %s)", llm_source)
    except Exception as e:
        logger.warning(
            "Mem0 L2 initialization failed: %s. "
            "Choose one:\n"
            "  (A) Install Ollama: https://ollama.com/download → ollama pull qwen2.5:7b\n"
            "  (B) Set OpenAI key: $env:OPENAI_API_KEY='sk-...' or SKPL_MEM0_LLM_PROVIDER=openai",
            e,
        )