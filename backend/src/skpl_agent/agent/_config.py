"""The agent config classes."""
from pydantic import BaseModel, Field, field_validator
from ..model import ChatModelBase

class SummarySchema(BaseModel):
    """The compressed memory model, used to generate summary of old memories"""
    task_overview: str = Field(description="The user's core request and success criteria.\nAny clarifications or constraints they specified")
    current_state: str = Field(description='What has been completed so far.\nFile created, modified, or analyzed (with paths if relevant).\nKey outputs or artifacts produced.')
    important_discoveries: str = Field(description="Technical constraints or requirements uncovered.\nDecisions made and their rationale.\nErrors encountered and how they were resolved.\nWhat approaches were tried that didn't work (and why)")
    next_steps: str = Field(description='Specific actions needed to complete the task.\nAny blockers or open questions to resolve.\nPriority order if multiple steps remain')
    context_to_preserve: str = Field(description="User preferences or style requirements.\nDomain-specific details that aren't obvious.\nAny promises made to the user")
    'The important context to preserve across compression, e.g. user\n    preferences, domain-specific details and promises made to the user.'

class ContextConfig(BaseModel):
    """The context related configuration in AgentScope"""
    model_config = {'arbitrary_types_allowed': True}
    'Allow arbitrary types in the pydantic model.'
    trigger_ratio: float = Field(default=0.8, gt=0, lt=0.9)
    'When the token exceeds this ratio of the maximum context length, the\n    context will be compressed. To reserve the context for context compression,\n    the maximum ratio is 0.9.'
    reserve_ratio: float = Field(default=0.1, gt=0, lt=0.9)
    'The ratio of the tokens to reserve in context compression, which should\n    be smaller than the trigger ratio.'
    compression_prompt: str = Field(default="<system-hint>You have been working on the task described above but have not yet completed it. Now write a continuation summary that will allow you to resume work efficiently in a future context window where the conversation history will be replaced with this summary. Your summary should be structured, concise, and actionable.\nThe current time is {current_time}.\nThis summary may itself be summarized again later, and the conversation history it refers to will be gone, so every reference must be self-contained — resolve anything that depends on the vanished context into an absolute, fully-qualified form:\n- Time: convert relative expressions ('today', 'now', 'yesterday', 'tomorrow', 'recently') to absolute dates using the current time above; re-anchor them even if an earlier summary already wrote them relatively.\n- Names & pointers: use file paths, symbol names, PR/issue numbers, IDs, URLs, and exact commands/error strings verbatim instead of 'this file', 'the above', 'the second approach', 'the 5 failing tests'.\n- In-flight work: record everything still pending, especially tools launched in the background whose results you are still waiting on — give each one's id and a short note of what it is doing — and mark each item's owner (user request vs your own decision) and status (done / pending / blocked).\n</system-hint>", json_schema_extra={'format': 'textarea'})
    'The prompt used to guide the compression model to generate the\n    compressed summary, which will be wrapped into a user message and\n    attach to the end of the current memory.'
    summary_template: str = Field(default='<system-info>Here is a summary of your previous work\n# Task Overview\n{task_overview}\n\n# Current State\n{current_state}\n\n# Important Discoveries\n{important_discoveries}\n\n# Next Steps\n{next_steps}\n\n# Context to Preserve\n{context_to_preserve}</system-info>', json_schema_extra={'format': 'textarea'})
    'The string template to present the compressed summary to the agent,\n    which will be formatted with the fields from the\n    `summary_schema`.'
    summary_schema: dict = Field(default_factory=SummarySchema.model_json_schema)
    'The structured model used to guide the agent to generate the\n    structured compressed summary.'
    tool_result_limit: int = Field(title='Tool Result Limit', default=50000, description='The maximum length of the tool results in tokens. If exceeded, the tool result will be truncated.')
    'The tool result limit to avoid tool result bursting.'

class InjectionConfig(BaseModel):
    """The state injection related configuration in AgentScope."""
    inject_runtime_state: bool = Field(title='Inject Runtime State', description='Inject the runtime state to context, including current time,tasks state, context length, etc.', default=True)
    'Whether to inject the runtime state to context, including current time,\n    tasks state, context length, etc.'
    timezone: str = Field(title='Timezone', default='UTC', description="The injected timezone. e.g. 'America/New_York' or 'Asia/Shanghai'.")
    "The timezone to inject into the context, follow the standard timezone\n    database format, e.g. 'America/New_York' or 'Asia/Shanghai'."
    time_format: str = Field(title='Time Format', default='%Y-%m-%dT%H:%M:%S', description="The format to inject and parse the time information, which must round-trip a full timestamp, i.e. carry the date part. A time-only format such as '%H:%M:%S' makes the parsed time fall back to year 1900, so that the time is injected in every iteration.")
    'The format to inject and parse the time information, which must carry\n    the date part to round-trip a full timestamp.'
    time_interval: float = Field(title='Time Interval', default=0.5, ge=0, description='The minimum time interval in hours from the last injection to trigger new time injection')
    'The minimum elapsed time in **hours** from the recorded time to trigger\n    a new time injection.'
    context_buffer_ratio: float = Field(title='Context Buffer', default=0.2, ge=0, le=1, description="The buffer that will activate context length injection before context compression, which should be smaller than the 'trigger_ratio' of the context config.")
    'The buffer ahead of the compression threshold, e.g. with a trigger ratio\n    of 0.8 and a buffer of 0.2, the context length is injected once the input\n    tokens exceed 60% of the model context size.'
    template: str = Field(title='Template', default='<system-reminder>Treat the following as the ground truth at this point of the conversation. Anything stated earlier is outdated, and a later reminder, if any, supersedes this one:\n{runtime_state}\n</system-reminder>', description="The template to wrap the injected runtime state, where the '{runtime_state}' placeholder will be replaced by the injected fields.")
    'The template to wrap the injected runtime state, which must contain the\n    ``{runtime_state}`` placeholder.'

    @field_validator('template')
    @classmethod
    def _check_template(cls, value: str) -> str:
        """Ensure the template won't silently drop the injected fields."""
        if '{runtime_state}' not in value:
            raise ValueError(f"The injection template must contain the '{{runtime_state}}' placeholder, got {value!r}.")
        return value
    injection_source: str = Field(title='Injection Source', default='{"label": "System", "sublabel": "Runtime State"}', description='The source of the injected hint block, which is also used to identify the previous injections within the context.')
    "The source of the injected hint block, used to identify the agent's own\n    injections when scanning the context."
    task_tool_names: list[str] = Field(title='Task Tool Names', default_factory=lambda : ['TaskCreate', 'TaskGet', 'TaskList', 'TaskUpdate'], description='The names of the task related tools. Their presence in the context suppresses the tasks injection.')
    'The names of the task related tools, whose tool calls in the context\n    indicate the agent is already aware of the tasks.'
    extra_fields: dict[str, str] = Field(title='Extra Fields', default_factory=dict, description="The extra fields to inject, which will be wrapped into the '<{key}>{value}</{key}>' format.")
    'The user defined fields to inject, which are attached to the injection\n    without triggering one by themselves.'
    emit_hint_event: bool = Field(title='Emit Hint Event', default=True, description='If emit the HintBlockEvent when runtime state injection happens.')

class ReActConfig(BaseModel):
    """The reasoning related configuration"""
    max_iters: int = Field(title='Max Iterations', default=20, description='The maximum number of reasoning-acting iterations in one reply')
    'The maximum number of iterations for the reasoning-acting loop.'
    structured_output_grace_iters: int = Field(title='Grace Iters for Structured Output', description='The grace iterations for structured output when exceeding the max iterations', default=5, gt=0)
    'The extra iterations allowed beyond ``max_iters`` to generate the\n    required structured output.'
    stop_on_reject: bool = Field(title='Rejection Handling', default=False, description='Whether to stop replying when being rejected to execute tools.')
    "If stop reasoning when tool call(s) are rejected. If `True`, the agent\n    won't continue reasoning and wait for outside interaction from the user.\n    "
    interruption_message: str = Field(title='Interruption Message', default='I notice the interruption. How can I help you?', description='The quick reply message when interrupted.')
    'The interruption message.'
    interruption_raise_cancelled_error: bool = Field(title='Raise CancelledError on Interruption', default=False, description='Whether to re-raise ``asyncio.CancelledError`` after handling the interruption. When ``False``, the ``CancelledError`` is swallowed once the interruption context has been produced.')
    'Whether to re-raise the ``asyncio.CancelledError`` after the\n    interruption has been handled. When ``False``, the ``CancelledError``\n    is swallowed once the fallback interruption message and\n    ``ReplyEndEvent`` have been emitted.'

class PlanConfig(BaseModel):
    """The planning phase configuration.

    When enabled, the agent runs a short planning step before the
    reasoning-acting loop: the user's goal is broken into a few
    executable steps, published to the front-end as a
    ``CustomEvent(name='plan')``, and (optionally) injected into the
    context as a system hint so the ReAct loop follows it.
    """
    enabled: bool = Field(title='Enable Planning', default=True, description='Enable planning phase before ReAct loop')
    'Whether to run the planning phase before the reasoning-acting loop.'
    max_plan_steps: int = Field(title='Max Plan Steps', default=5, ge=1, le=20, description='The maximum number of steps in the generated plan.')
    'The generated plan is truncated to at most this many steps.'
    plan_system_prompt: str = Field(title='Plan System Prompt', default='你是一个规划器。把用户目标拆成不超过 {max_steps} 个可执行步骤，每步一行：动作 + 预期产出 + 需要的工具。只输出计划，不要执行。', description='The system prompt for the planning model call. May contain a ``{max_steps}`` placeholder, replaced with ``max_plan_steps``.', json_schema_extra={'format': 'textarea'})
    'The system prompt for the planning call, formatted with ``max_steps``.'
    inject_plan_to_context: bool = Field(title='Inject Plan', default=True, description='Inject the generated plan into the context as a system hint so the ReAct loop follows it.')
    'Whether to inject the plan into the context as a hint block.'
    require_confirmation: bool = Field(title='Require Confirmation', default=False, description='为 True 时呈现计划后结束本轮回复，等用户下一条消息确认')
    'When True, the plan is presented to the user and the reply ends right after; the next user message is treated as the confirmation.'

class ModelConfig(BaseModel):
    """The model related configuration."""
    model_config = {'arbitrary_types_allowed': True}
    max_retries: int = Field(default=0, ge=0, description="Number of retries on top of the initial call before falling over to the fallback model. ``0`` means call the model exactly once and immediately move to the fallback on failure. Same semantics as ``ChatModelBase.max_retries``. Defaults to 0 to avoid compounding with the model's own inner retry loop.")
    'Number of retries on top of the initial call before falling over to\n    the fallback model. ``0`` means a single attempt with no retries.\n    Mirrors the semantics of ``ChatModelBase.max_retries``.'
    fallback_model: ChatModelBase | None = Field(default=None, description='The fallback model used when the main model fails.')
    'The fallback model used when the main model fails. Also supports the\n    max_retries logic.'