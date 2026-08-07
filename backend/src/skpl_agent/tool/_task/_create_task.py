"""The creating task tool class."""
from typing import Any
from pydantic import BaseModel, Field
from ._task_tool_base import _TaskToolBase
from .._response import ToolChunk
from ...state import AgentState, Task
from ...exception import DeveloperOrientedException
from ...message import TextBlock, ToolResultState

class _TaskCreateParams(BaseModel):
    """The params of the creating task tool."""
    subject: str = Field(description='A brief title for the task')
    description: str = Field(description='What needs to be done')
    metadata: dict[str, Any] | None = Field(default=None, description='Arbitrary metadata to attach to the task')

class TaskCreate(_TaskToolBase):
    """Create a task for the agent to perform."""
    name: str = 'TaskCreate'
    description: str = 'Use this tool to create a structured task list for your current session. This helps you track progress, organize complex tasks, and demonstrate thoroughness to the user.\nIt also helps the user understand the progress of the task and overall progress of their requests.\n\n## When to Use This Tool\nUse this tool proactively in these scenarios:\n\n- Complex multi-step tasks - When a task requires 3 or more distinct steps or actions\n- Non-trivial and complex tasks - Tasks that require careful planning or multiple operations\n- Plan mode - When using plan mode, create a task list to track the work\n- User explicitly requests todo list - When the user directly asks you to use the todo list\n- User provides multiple tasks - When users provide a list of things to be done (numbered or comma-separated)\n- After receiving new instructions - Immediately capture user requirements as tasks\n- When you start working on a task - Mark it as in_progress BEFORE beginning work\n- After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation\n\n## When NOT to Use This Tool\n\nSkip using this tool when:\n- There is only **one single, straightforward** task\n- The task is trivial and tracking it provides no organizational benefit\n- The task can be completed in less than 3 trivial steps\n- The task is purely conversational or informational\n\nNOTE that you should **NOT** use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.\n\n## Task Fields\n\n- **subject**: A brief, actionable title in imperative form (e.g., "Fix authentication bug in login flow")\n- **description**: What needs to be done\n\nAll tasks are created with status `pending`.\n\n## Tips\n\n- Create tasks with clear, specific subjects that describe the outcome\n- After creating tasks, use TaskUpdate to set up dependencies (blocks/blockedBy) if needed\n- Check TaskList first to avoid creating duplicate tasks'
    input_schema: dict = _TaskCreateParams.model_json_schema()

    async def call(self, _agent_state: AgentState, subject: str, description: str, metadata: dict[str, Any] | None=None) -> ToolChunk:
        """Create the subtask and add it into the agent state."""
        if not isinstance(_agent_state, AgentState):
            raise DeveloperOrientedException(f'Error: TaskCreate requires AgentState to be provided, got {_agent_state} instead.')
        try:
            max_numeric = 0
            for t in _agent_state.tasks_context.tasks:
                try:
                    max_numeric = max(max_numeric, int(t.id))
                except (ValueError, TypeError):
                    pass
            next_id = str(max_numeric + 1)
            task = Task(id=next_id, subject=subject, description=description, metadata=metadata or {})
            _agent_state.tasks_context.tasks.append(task)
            return ToolChunk(content=[TextBlock(text=f'Task (id={next_id}) created successfully: {task.subject}')])
        except Exception as e:
            return ToolChunk(content=[TextBlock(text=f'CreateTaskError: {e}')], state=ToolResultState.ERROR)