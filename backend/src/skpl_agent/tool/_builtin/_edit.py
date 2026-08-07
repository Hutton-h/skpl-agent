"""The edit tool in agentscope."""
import difflib
import fnmatch
from typing import Any, List
from .._base import ToolBase, ToolMiddlewareBase
from .._constants import DEFAULT_DANGEROUS_FILES, DEFAULT_DANGEROUS_DIRECTORIES
from ...permission import PermissionContext, PermissionDecision, PermissionBehavior, PermissionMode, PermissionRule
from .._response import ToolChunk
from ...message import TextBlock, ToolResultState
from ...state import AgentState
from ._backend import BackendBase, _normalize_newlines

class Edit(ToolBase):
    """The edit tool for performing exact string replacements in files."""
    name: str = 'Edit'
    'The tool name presented to the agent.'
    description: str = 'Performs exact string replacements in files.\n\nUsage:\n- You must use your `Read` tool at least once in the conversation\n  before editing. This tool will error if you attempt an edit without\n  reading the file.\n- When editing text from Read tool output, ensure you preserve the\n  exact indentation (tabs/spaces) as it appears AFTER the line number\n  prefix. The line number prefix format is: line number + tab.\n  Everything after that is the actual file content to match. Never\n  include any part of the line number prefix in the old_string or\n  new_string.\n- ALWAYS prefer editing existing files in the codebase. NEVER write\n  new files unless explicitly required.\n- Only use emojis if the user explicitly requests it. Avoid adding\n  emojis to files unless asked.\n- The edit will FAIL if `old_string` is not unique in the file.'
    'The description presented to the agent.'
    input_schema: dict[str, Any] = {'type': 'object', 'properties': {'file_path': {'type': 'string', 'description': 'The absolute path to the file to edit.'}, 'old_string': {'type': 'string', 'description': 'The exact string to replace. Must match exactly including whitespace and indentation.'}, 'new_string': {'type': 'string', 'description': 'The string to replace old_string with.'}, 'replace_all': {'type': 'boolean', 'description': 'If true, replace all occurrences. If false (default), only replace if there is exactly one occurrence.', 'default': False}}, 'required': ['file_path', 'old_string', 'new_string']}
    is_mcp: bool = False
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_external_tool: bool = False
    is_state_injected: bool = True

    def __init__(self, dangerous_files: list[str]=DEFAULT_DANGEROUS_FILES, dangerous_directories: list[str]=DEFAULT_DANGEROUS_DIRECTORIES, middlewares: List[ToolMiddlewareBase] | None=None, backend: BackendBase | None=None) -> None:
        """Initialize the edit tool.

        Args:
            dangerous_files (`list[str]`, optional):
                Sensitive files that require explicit user confirmation,
                even in BYPASS mode. Matched by basename
                (case-insensitive). Defaults to `DEFAULT_DANGEROUS_FILES`.
                Pass a custom list to fully replace the defaults, or `[]`
                to disable the filename check.
            dangerous_directories (`list[str]`, optional):
                Sensitive directories that require explicit user
                confirmation. Matched when any path segment equals an
                entry (case-insensitive). Defaults to
                `DEFAULT_DANGEROUS_DIRECTORIES`. Pass a custom list to
                fully replace the defaults, or `[]` to disable the
                directory check.
            middlewares (`List[ToolMiddlewareBase] | None`, optional):
                Tool middlewares wrapping the tool execution.
            backend (`BackendBase | None`, optional):
                The sandbox backend to use for file I/O. When ``None``,
                a :class:`LocalBackend` is created.
        """
        from ._backend import LocalBackend
        super().__init__(middlewares=middlewares)
        self.dangerous_files = list(dangerous_files)
        self.dangerous_directories = list(dangerous_directories)
        self._backend = backend or LocalBackend()

    async def check_permissions(self, tool_input: dict[str, Any], context: PermissionContext) -> PermissionDecision:
        """Check permissions for file editing.

        This method implements Edit-specific permission checks:
        1. Dangerous path check (safety check, bypass-immune)
        2. ACCEPT_EDITS mode check for files in working directories

        Args:
            tool_input (`dict[str, Any]`):
                The tool input containing "file_path" key
            context (`PermissionContext`):
                The permission context with mode and rules

        Returns:
            `PermissionDecision`:
                ASK for dangerous paths, ALLOW for safe operations in
                ACCEPT_EDITS mode, PASSTHROUGH otherwise
        """
        file_path = tool_input.get('file_path')
        if not file_path:
            return PermissionDecision(behavior=PermissionBehavior.PASSTHROUGH, message='No file path provided')
        if self._is_dangerous_path(file_path):
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f'Permission required: Edit operation on sensitive file {file_path}', decision_reason='Safety check: dangerous file or directory', bypass_immune=True)
        if context.mode in (PermissionMode.ACCEPT_EDITS, PermissionMode.DONT_ASK):
            if self._path_in_allowed_working_path(file_path, context):
                return PermissionDecision(behavior=PermissionBehavior.ALLOW, message=f'Permission granted for editing {file_path} (in working directory)', decision_reason='File is in working directory and not a dangerous path')
        return PermissionDecision(behavior=PermissionBehavior.PASSTHROUGH, message='')

    async def match_rule(self, rule_content: str | None, tool_input: dict[str, Any]) -> bool:
        """Check if a permission rule matches the file path.

        Matches rule_content as a glob pattern against the "file_path"
        parameter using fnmatch. If rule_content is None, matches all
        invocations (tool-name-level rule).

        Args:
            rule_content (`str | None`):
                Glob pattern to match against the file path (e.g., "src/**"),
                or None to match all invocations
            tool_input (`dict[str, Any]`):
                The tool input data containing "file_path" key

        Returns:
            `bool`:
                True if the glob pattern matches the file path, False otherwise
        """
        if rule_content is None:
            return True
        file_path = tool_input.get('file_path', '')
        if not file_path:
            return False
        return fnmatch.fnmatch(file_path, rule_content)

    async def generate_suggestions(self, tool_input: dict[str, Any]) -> List[PermissionRule]:
        """Generate suggested permission rules for the file path.

        Suggests a glob pattern covering the parent directory of the file,
        allowing the user to grant permission for the entire directory at once.

        Args:
            tool_input (`dict[str, Any]`):
                The tool input data containing "file_path" key

        Returns:
            `List[PermissionRule]`:
                A single suggested rule covering the parent directory
                (e.g., file "/src/main.py" -> rule "src/**")
        """
        file_path = tool_input.get('file_path', '')
        if not file_path:
            return []
        parent = self._backend.dirname(file_path)
        pattern = parent.rstrip('/\\') + '/**' if parent else '**'
        return [PermissionRule(tool_name=self.name, rule_content=pattern, behavior=PermissionBehavior.ALLOW, source='suggested')]

    async def call(self, file_path: str, old_string: str, new_string: str, replace_all: bool=False, _agent_state: AgentState | None=None) -> ToolChunk:
        """Execute the edit and return the result."""
        if not self._backend.isabs(file_path):
            return ToolChunk(content=[TextBlock(text=f'Error: file_path must be an absolute path, got: {file_path}')], state=ToolResultState.ERROR, is_last=True)
        if not await self._backend.file_exists(file_path):
            return ToolChunk(content=[TextBlock(text=f'Error: File not found: {file_path}')], state=ToolResultState.ERROR, is_last=True)
        if old_string == new_string:
            return ToolChunk(content=[TextBlock(text='Error: old_string and new_string are identical. No changes to make.')], state=ToolResultState.ERROR, is_last=True)
        content = None
        if _agent_state is not None:
            cache = await _agent_state.tool_context.get_cache(file_path)
            if cache is None:
                return ToolChunk(content=[TextBlock(text='Error: To edit a file, you must first read it using the Read tool.')], state=ToolResultState.ERROR, is_last=True)
            content = ''.join(cache.lines)
        else:
            try:
                raw = await self._backend.read_file(file_path)
                content = _normalize_newlines(raw.decode('utf-8', errors='replace'))
            except Exception as e:
                return ToolChunk(content=[TextBlock(text=f'Error reading file: {str(e)}')], state=ToolResultState.ERROR, is_last=True)
        occurrences = content.count(old_string)
        if occurrences == 0:
            return ToolChunk(content=[TextBlock(text=f'Error: old_string not found in {file_path}')], state=ToolResultState.ERROR, is_last=True)
        if occurrences > 1 and (not replace_all):
            return ToolChunk(content=[TextBlock(text=f'Error: old_string appears {occurrences} times in {file_path}. Set replace_all=true to replace all occurrences, or make old_string more specific.')], state=ToolResultState.ERROR, is_last=True)
        if replace_all:
            updated_content = content.replace(old_string, new_string)
        else:
            updated_content = content.replace(old_string, new_string, 1)
        try:
            await self._backend.write_file(file_path, updated_content.encode('utf-8'))
        except Exception as e:
            return ToolChunk(content=[TextBlock(text=f'Error writing file: {str(e)}')], state=ToolResultState.ERROR, is_last=True)
        replacement_msg = f'all {occurrences} occurrences' if replace_all else '1 occurrence'
        diff_text = ''.join(difflib.unified_diff(content.splitlines(keepends=True), updated_content.splitlines(keepends=True), fromfile=f'a/{file_path}', tofile=f'b/{file_path}', n=3))
        return ToolChunk(content=[TextBlock(text=f'Successfully replaced {replacement_msg} in {file_path}')], state=ToolResultState.RUNNING, is_last=True, metadata={'diff': diff_text, 'file_path': file_path, 'occurrences': occurrences if replace_all else 1})