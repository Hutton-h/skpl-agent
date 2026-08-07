"""The embedding model card class."""
from __future__ import annotations
import copy
from typing import Literal, Type
from typing_extensions import Self
import yaml
from pydantic import BaseModel, Field

class EmbeddingModelCard(BaseModel):
    """A card describing an embedding model's capabilities.

    Mirrors :class:`~agentscope.model.ModelCard` but tailored for
    embedding models.  Uses ``input_types`` / ``output_types`` to
    describe model capabilities, and ``parameter_schema`` (built from
    the embedding class's ``Parameters`` + YAML ``parameter_overrides``)
    to tell the frontend which knobs the user can adjust.

    The output type ``application/x-embedding`` indicates that the
    model produces dense vector embeddings.
    """
    type: Literal['embedding_model'] = 'embedding_model'
    'The card type, always ``"embedding_model"``.'
    name: str = Field(description='The model name used in API calls.')
    'The model name (e.g. ``"text-embedding-3-small"``).'
    label: str = Field(description='Human-readable label for the frontend.')
    'Display label (e.g. ``"Text Embedding 3 Small"``).'
    status: Literal['active', 'deprecated', 'sunset'] = Field(default='active', description='The model lifecycle status.')
    'The model status.'
    input_types: list[str] = Field(default=['text/plain'], description='Supported input media types.')
    'Supported input types (e.g. ``["text/plain"]``,\n    ``["text/plain", "image/jpeg", "image/png"]``).'
    output_types: list[str] = Field(default=['application/x-embedding'], description='Supported output media types.')
    'Output types. ``application/x-embedding`` for vector output.'
    dimensions: int = Field(..., description='Default output vector dimensions for this model.', gt=0)
    "The default output dimensions for this model.\n\n    First-class top-level field — kept outside of\n    :attr:`parameter_schema` so that callers can rely on a strongly\n    typed ``int`` rather than the soft ``parameter_schema['properties']\n    ['dimensions']['default']`` lookup.\n    "
    supported_dimensions: list[int] | None = Field(default=None, description='If set, the only dimensions this model can produce. ``None`` means dimensions are fixed at :attr:`dimensions` and cannot be overridden.')
    "Optional set of allowed output dimensions.\n\n    Set for Matryoshka-style models (e.g. OpenAI's\n    ``text-embedding-3-*``) that can be truncated to a smaller size.\n    ``None`` indicates a fixed-dimension model.\n    "
    context_size: int | None = Field(default=None, description='Maximum input length (in tokens) per request.', gt=0)
    'Maximum input context size, if known.'
    parameter_schema: dict = Field(default_factory=dict, description='JSON Schema for user-configurable parameters (built from the Parameters class + YAML overrides).')
    'The parameter schema sent to the frontend for form rendering.\n    Empty ``properties`` means nothing to configure (e.g. fixed\n    dimensions).'
    parameter_overrides: dict[str, dict] = Field(default_factory=dict, description='Raw parameter overrides from the YAML file.')
    'The raw parameter overrides, preserved for reference.'

    @classmethod
    def from_yaml(cls, yaml_path: str, parameter_class: Type[BaseModel]) -> Self:
        """Load an embedding model card from a YAML file.

        Merges the base ``parameter_class`` JSON Schema with
        ``parameter_overrides`` from the YAML — identical to the
        approach used by :meth:`~agentscope.model.ModelCard.from_yaml`.

        Args:
            yaml_path (`str`):
                Path to the YAML file.
            parameter_class (`Type[BaseModel]`):
                The ``Parameters`` class from the embedding model subclass.

        Returns:
            `EmbeddingModelCard`: The loaded model card.
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if 'dimensions' not in config:
            raise ValueError(f"Embedding model card {yaml_path!r} is missing the required top-level 'dimensions' field.")
        base_schema = parameter_class.model_json_schema()
        properties = copy.deepcopy(base_schema.get('properties', {}))
        overrides = config.get('parameter_overrides', {})
        for (param_name, override) in overrides.items():
            if override is None:
                properties.pop(param_name, None)
                continue
            if isinstance(override, dict):
                if override.get('hidden'):
                    properties.pop(param_name, None)
                    continue
                if param_name in properties:
                    properties[param_name] = {**properties[param_name], **override}
        final_schema = {'type': 'object', 'properties': properties, 'required': base_schema.get('required', [])}
        return cls(name=config['name'], label=config['label'], status=config.get('status', 'active'), input_types=config.get('input_types', ['text/plain']), output_types=config.get('output_types', ['application/x-embedding']), dimensions=config['dimensions'], supported_dimensions=config.get('supported_dimensions'), context_size=config.get('context_size'), parameter_schema=final_schema, parameter_overrides=overrides)