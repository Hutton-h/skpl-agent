"""The bash tool in agentscope."""
import os
from typing import AsyncGenerator, Any, List
import re
from ._bash_parser import BashCommandParser
from .._base import ToolBase, ToolMiddlewareBase
from .._constants import DEFAULT_DANGEROUS_FILES, DEFAULT_DANGEROUS_DIRECTORIES
from ...permission import PermissionContext, PermissionDecision, PermissionBehavior, PermissionMode, PermissionRule
from ...message import TextBlock, ToolResultState
from .._response import ToolChunk
from ._backend import BackendBase

class Bash(ToolBase):
    """The bash tool."""
    name: str = 'Bash'
    'The tool name presented to the agent.'
    description: str = 'Executes a bash command and returns its output.\n\nThe working directory persists between commands, but shell state does\nnot. The shell environment is initialized from the user\'s profile\n(bash or zsh).\n\nIMPORTANT: Avoid using this tool to run `find`, `grep`, `cat`, `head`,\n`tail`, `sed`, `awk`, or `echo` commands, unless explicitly instructed\nor after you have verified that a dedicated tool cannot accomplish your\ntask. Instead, use the appropriate dedicated tool as this will provide\na much better experience for the user:\n\n - File search: Use Glob (NOT find or ls)\n - Content search: Use Grep (NOT grep or rg)\n - Read files: Use Read (NOT cat/head/tail)\n - Edit files: Use Edit (NOT sed/awk)\n - Write files: Use Write (NOT echo >/cat <<EOF)\n - Communication: Output text directly (NOT echo/printf)\n\nWhile the Bash tool can do similar things, it\'s better to use the\nbuilt-in tools as they provide a better user experience and make it\neasier to review tool calls and give permission.\n\n# Instructions\n - If your command will create new directories or files, first use\n   this tool to run `ls` to verify the parent directory exists and is\n   the correct location.\n - Always quote file paths that contain spaces with double quotes in\n   your command (e.g., cd "path with spaces/file.txt")\n - Try to maintain your current working directory throughout the\n   session by using absolute paths and avoiding usage of `cd`. You may\n   use `cd` if the User explicitly requests it.\n - You may specify an optional timeout in milliseconds (up to 600000ms\n   / 10 minutes). By default, your command will timeout after 120000ms\n   (2 minutes).\n - Write a clear, concise description of what your command does. For\n   simple commands, keep it brief (5-10 words). For complex commands\n   (piped commands, obscure flags, or anything hard to understand at a\n   glance), include enough context so that the user can understand what\n   your command will do.\n - When issuing multiple commands:\n  - If the commands are independent and can run in parallel, make\n    multiple Bash tool calls in a single message. Example: if you need\n    to run "git status" and "git diff", send a single message with two\n    Bash tool calls in parallel.\n  - If the commands depend on each other and must run sequentially,\n    use a single Bash call with \'&&\' to chain them together.\n  - Use \';\' only when you need to run commands sequentially but don\'t\n    care if earlier commands fail.\n  - DO NOT use newlines to separate commands (newlines are ok in\n    quoted strings).\n - For git commands:\n  - Prefer to create a new commit rather than amending an existing\n    commit.\n  - Before running destructive operations (e.g., git reset --hard, git\n    push --force, git checkout --), consider whether there is a safer\n    alternative that achieves the same goal. Only use destructive\n    operations when they are truly the best approach.\n  - Never skip hooks (--no-verify) or bypass signing (--no-gpg-sign,\n    -c commit.gpgsign=false) unless the user has explicitly asked for\n    it. If a hook fails, investigate and fix the underlying issue.\n - Avoid unnecessary `sleep` commands:\n  - Do not sleep between commands that can run immediately — just run\n    them.\n  - Do not retry failing commands in a sleep loop — diagnose the root\n    cause or consider an alternative approach.\n  - If you must sleep, keep the duration short (1-5 seconds) to avoid\n    blocking the user.'
    'The description presented to the agent.'
    input_schema: dict[str, Any] = {'type': 'object', 'properties': {'command': {'type': 'string', 'description': 'The bash command to execute.'}, 'description': {'type': 'string', 'description': 'Clear, concise description of what this command does. For simple commands, keep it brief (5-10 words). For complex commands, include enough context.'}, 'timeout': {'type': 'integer', 'description': 'Optional timeout in milliseconds (default: 120000, max: 600000)', 'default': 120000, 'maximum': 600000, 'minimum': 0}}, 'required': ['command']}
    is_mcp: bool = False
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_external_tool: bool = False
    is_state_injected: bool = False

    def __init__(self, dangerous_files: list[str]=DEFAULT_DANGEROUS_FILES, dangerous_directories: list[str]=DEFAULT_DANGEROUS_DIRECTORIES, cwd: str | os.PathLike[str] | None=None, middlewares: List[ToolMiddlewareBase] | None=None, backend: BackendBase | None=None) -> None:
        """Initialize the bash tool.

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
            cwd (`str | os.PathLike[str] | None`, optional):
                The working directory used when executing bash commands.
            middlewares (`List[ToolMiddlewareBase] | None`, optional):
                Tool middlewares wrapping the tool execution.
            backend (`BackendBase | None`, optional):
                The sandbox backend to use for shell execution. When
                ``None``, a :class:`LocalBackend` is created.
        """
        from ._backend import LocalBackend
        super().__init__(middlewares=middlewares)
        self._bash_parser = BashCommandParser()
        self.dangerous_files = list(dangerous_files)
        self.dangerous_directories = list(dangerous_directories)
        self._cwd = os.fspath(cwd) if cwd is not None else None
        self._backend = backend or LocalBackend()

    async def check_read_only(self, tool_input: dict[str, Any]) -> bool:
        """Decide whether this specific bash invocation is read-only.

        Inspects the command and returns ``True`` for known-safe read-only
        commands (e.g. ``ls``, ``cat``, ``grep``, ``git status``). The
        static :attr:`is_read_only` class attribute is ``False`` because
        Bash can execute arbitrary commands; this method overrides that
        with a per-invocation answer.
        """
        command = tool_input.get('command', '')
        if not command:
            return self.is_read_only
        if self._bash_parser.check_injection_risk(command):
            return False
        return self._bash_parser.is_read_only_command(command)

    async def check_permissions(self, tool_input: dict[str, Any], context: PermissionContext) -> PermissionDecision:
        """Check permissions for bash command execution.

        This method implements Bash-specific permission checks:

        0. Injection risk check (bypass-immune safety ASK if command
           contains dynamic expansion like ``$(...)`` or ``<(...)``)
        1. Read-only command check — auto-ALLOW in **every mode**
           (including DEFAULT) for known-safe read-only commands
           (``ls``, ``pwd``, ``git status``, ``cat``, etc.). This is
           the static counterpart to :meth:`check_read_only`.
        2. Dangerous command pattern check (bypass-immune safety ASK)
        3. Sed in-place constraint check (bypass-immune safety ASK)
        4. Dangerous path check for config files (bypass-immune safety
           ASK)
        5. Dangerous removal path check for system dirs (bypass-immune
           safety ASK)
        6. ACCEPT_EDITS auto-allow for ``mkdir``/``touch``/``rm``/
           ``rmdir``/``mv``/``cp``/``sed`` — only when **every**
           target path resolves inside a working directory
        7. PASSTHROUGH (engine continues with rule matching)

        "Bypass-immune" decisions set
        :attr:`PermissionDecision.bypass_immune` so they cannot be
        silenced by allow rules in DEFAULT mode. In BYPASS mode all
        bypass-immune ASKs are intentionally skipped — see
        :attr:`PermissionMode.BYPASS`.

        Args:
            tool_input (`dict[str, Any]`):
                The tool input containing "command" key
            context (`PermissionContext`):
                The permission context with mode and rules

        Returns:
            `PermissionDecision`:
                ALLOW for safe operations, ASK for dangerous operations,
                PASSTHROUGH to let Engine continue with rule matching
        """
        command = tool_input.get('command', '')
        if not command:
            return PermissionDecision(behavior=PermissionBehavior.PASSTHROUGH, message='Empty command')
        injection_reason = self._bash_parser.check_injection_risk(command)
        if injection_reason:
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f'Permission required: {injection_reason}', decision_reason='Safety check: command contains dynamic expansion that cannot be statically analyzed', bypass_immune=True)
        if self._bash_parser.is_read_only_command(command):
            return PermissionDecision(behavior=PermissionBehavior.ALLOW, message='Permission granted for read-only command', decision_reason='Read-only command is allowed')
        dangerous_pattern = self._bash_parser.check_dangerous_command(command)
        if dangerous_pattern:
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f'Permission required: Command contains dangerous pattern: {dangerous_pattern}', decision_reason='Safety check: dangerous command pattern detected', bypass_immune=True)
        sed_error = self._bash_parser.check_sed_constraints(command, self.dangerous_files)
        if sed_error:
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f'Permission required: {sed_error}', decision_reason='Safety check: sed in-place modification of dangerous file', bypass_immune=True)
        dangerous_paths = self._extract_dangerous_paths_from_bash(command)
        if dangerous_paths:
            paths_str = ', '.join(dangerous_paths)
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f'Permission required: Bash command operates on sensitive paths: {paths_str}', decision_reason='Safety check: dangerous file or directory in bash command', bypass_immune=True)
        removal_path = await self._check_dangerous_removal_path(command)
        if removal_path:
            return PermissionDecision(behavior=PermissionBehavior.ASK, message=f"Dangerous removal operation detected: '{removal_path}'\n\nThis command would remove a critical system directory. This requires explicit approval and cannot be auto-allowed by permission rules.", decision_reason='Safety check: dangerous removal of critical system path', bypass_immune=True)
        if context.mode in (PermissionMode.ACCEPT_EDITS, PermissionMode.DONT_ASK):
            filesystem_commands = {'mkdir', 'touch', 'rm', 'rmdir', 'mv', 'cp', 'sed'}
            base_command = command.strip().split()[0] if command.strip() else ''
            if base_command in filesystem_commands:
                target_paths = [path for (_cmd, path) in self._bash_parser.extract_file_paths(command)]
                if target_paths and all((self._path_in_allowed_working_path(path, context) for path in target_paths)):
                    return PermissionDecision(behavior=PermissionBehavior.ALLOW, message=f"Permission granted for '{base_command}' command (filesystem command, all targets in working directory)", decision_reason=f"Filesystem command '{base_command}' is auto-allowed because all target paths are within a working directory")
        return PermissionDecision(behavior=PermissionBehavior.PASSTHROUGH, message=f'Execute bash command: {command}')

    async def match_rule(self, rule_content: str | None, tool_input: dict[str, Any]) -> bool:
        """Match Bash command using regex-based wildcard matching.

        Implements wildcard matching with escape sequences:
        - Supports \\* for literal asterisk and \\\\ for literal backslash
        - Special optimization: "git *" matches both "git" and "git add"
        - Prefix pattern (e.g., "git:*"): matches commands starting with "git "
        - Wildcard pattern: converts to regex with proper escape handling
        - Substring pattern: exact substring matching
        - If rule_content is None, matches all invocations
         (tool-name-level rule)

        Args:
            rule_content: The command pattern to match, or None to match all
            tool_input: Must contain a "command" key with the command string

        Returns:
            True if pattern matches the command
        """
        if rule_content is None:
            return True
        command = tool_input.get('command', '')
        if rule_content.endswith(':*'):
            prefix = rule_content[:-2].strip()
            return command.startswith(prefix + ' ') or command == prefix

        def has_wildcards(pattern: str) -> bool:
            """Check if pattern contains unescaped * wildcards."""
            i = 0
            while i < len(pattern):
                if pattern[i] == '\\':
                    i += 2
                elif pattern[i] == '*':
                    return True
                else:
                    i += 1
            return False
        if not has_wildcards(rule_content):
            pattern = rule_content
            pattern = pattern.replace('\\\\', '\x00BACKSLASH\x00')
            pattern = pattern.replace('\\*', '*')
            pattern = pattern.replace('\x00BACKSLASH\x00', '\\')
            return pattern in command
        ESCAPED_STAR = '\x00ESCAPED_STAR\x00'
        ESCAPED_BACKSLASH = '\x00ESCAPED_BACKSLASH\x00'
        pattern = rule_content
        pattern = pattern.replace('\\\\', ESCAPED_BACKSLASH)
        pattern = pattern.replace('\\*', ESCAPED_STAR)
        special_chars = '.^$+?{}[]|()'
        for char in special_chars:
            pattern = pattern.replace(char, '\\' + char)
        pattern = pattern.replace('*', '.*')
        pattern = pattern.replace(ESCAPED_STAR, '\\*')
        pattern = pattern.replace(ESCAPED_BACKSLASH, '\\\\')
        if pattern.endswith('.*'):
            base_pattern = pattern[:-2]
            base_pattern = base_pattern.rstrip()
            if re.fullmatch(base_pattern, command):
                return True
        try:
            return bool(re.fullmatch(pattern, command))
        except re.error:
            return rule_content.replace('*', '') in command

    async def generate_suggestions(self, tool_input: dict[str, Any]) -> List['PermissionRule']:
        """Generate suggested permission rules for Bash commands.

        Generates prefix rules based on command + subcommand (two words).
        For example, "git commit -m 'xxx'" generates "git commit:*".

        Args:
            tool_input (`dict[str, Any]`):
                The tool input data containing "command" key

        Returns:
            `List[PermissionRule]`:
                List of suggested permission rules based on command prefixes
        """
        command = tool_input.get('command', '')
        if not command:
            return []
        prefixes = self._bash_parser.extract_command_prefixes(command, max_prefixes=5)
        if not prefixes:
            return []
        rules = []
        for prefix in prefixes:
            rules.append(PermissionRule(tool_name='Bash', rule_content=f'{prefix}:*', behavior=PermissionBehavior.ALLOW, source='suggested'))
        return rules

    def _extract_dangerous_paths_from_bash(self, command: str) -> list[str]:
        """Extract dangerous paths from a bash command using tree-sitter.

        Checks for dangerous paths in:
        - File-manipulating commands (rm, mv, cp, chmod, chown, sed, touch)
        - Output redirections (>, >>)

        Args:
            command (`str`):
                The bash command string

        Returns:
            `list[str]`:
                List of dangerous paths found in the command
        """
        dangerous_paths = []
        file_paths = self._bash_parser.extract_file_paths(command)
        for (_cmd_name, path) in file_paths:
            if self._is_dangerous_path(path):
                dangerous_paths.append(path)
        return dangerous_paths

    async def _check_dangerous_removal_path(self, command: str) -> str | None:
        """Check if a rm/rmdir command targets a critical system path.

        Detects commands like `rm -rf /`, `rm -rf /usr`, `rmdir ~` that
        would destroy critical system directories. Unlike _is_dangerous_path
        (which checks against a configurable list of sensitive config files),
        this checks against a fixed set of system-level paths that must
        never be removed regardless of user configuration.

        Dangerous paths are:
        - Root directory (/)
        - Home directory (~)
        - Wildcard alone (*) or as dir/* (removes everything)
        - Direct children of root (/usr, /etc, /tmp, /var, etc.)

        Args:
            command (`str`):
                The bash command string

        Returns:
            `str | None`:
                The dangerous path if found, None otherwise
        """
        tokens = command.strip().split()
        if not tokens:
            return None
        try:
            tree = self._bash_parser.parser.parse(bytes(command, 'utf8'))
            subcommands = self._bash_parser.split_compound_command(tree.root_node, command)
        except Exception:
            subcommands = [command]
        for subcmd in subcommands:
            subcmd_tokens = subcmd.strip().split()
            if not subcmd_tokens:
                continue
            base = subcmd_tokens[0]
            if base not in ('rm', 'rmdir'):
                continue
            i = 1
            while i < len(subcmd_tokens):
                tok = subcmd_tokens[i]
                if tok.startswith('-'):
                    i += 1
                    continue
                path = tok.strip('\'"')
                if await self._is_dangerous_removal_path(path):
                    return path
                i += 1
        return None

    async def _is_dangerous_removal_path(self, path: str) -> bool:
        """Check if a path is a critical system directory that must not be
        removed.

        All path resolution is performed via the backend so that the
        check operates on the **backend environment's** ``$HOME`` /
        ``cwd`` / path semantics, not the host process's.

        Args:
            path (`str`):
                The path to check (may be relative, absolute, or contain ~)

        Returns:
            `bool`:
                True if removing this path would be catastrophic
        """
        if path in ('*', './*', '/'):
            return True
        if path.endswith('/*') or path.endswith('\\*'):
            return True
        expanded = await self._backend.expanduser(path)
        backend_cwd = await self._backend.getcwd()
        abs_path = self._backend.abspath(expanded, cwd=backend_cwd)
        home = await self._backend.expanduser('~')
        if abs_path == home:
            return True
        parent = self._backend.dirname(abs_path)
        if abs_path == parent:
            return True
        if self._backend.dirname(parent) == parent:
            return True
        return False

    async def call(self, command: str, description: str='', timeout: int=120000) -> AsyncGenerator[ToolChunk, None]:
        """Execute the bash and return the output.

        Args:
            command: The bash command to execute.
            description: Optional description of what the command does.
            timeout: Timeout in milliseconds (default: 120000, max: 600000).

        Yields:
            ToolChunk: The tool execution result with stdout/stderr content.
        """
        timeout_ms = min(timeout, 600000)
        timeout_sec = timeout_ms / 1000.0
        try:
            if os.name == 'nt':
                shell_command = ['cmd', '/c', command]
            else:
                shell_command = ['/bin/sh', '-c', command]
            result = await self._backend.exec_shell(shell_command, cwd=self._cwd, timeout=timeout_sec)
            stdout = result.stdout.decode('utf-8', errors='replace').replace('\r\n', '\n')
            stderr = result.stderr.decode('utf-8', errors='replace').replace('\r\n', '\n')
            if result.exit_code == -1 and result.stderr == b'timed out':
                error_msg = f'Command timed out after {timeout_ms}ms: {command}'
                yield ToolChunk(content=[TextBlock(text=error_msg)], state=ToolResultState.ERROR, is_last=True)
                return
            output = stdout
            if stderr:
                if output:
                    output += '\n'
                output += stderr
            if len(output) > 30000:
                output = output[:30000] + '\n... (output truncated)'
            if not result.ok():
                error_result = f'Command failed: {command}\n'
                if stdout:
                    error_result += f'\nStdout:\n{stdout}'
                if stderr:
                    error_result += f'\nStderr:\n{stderr}'
                if len(error_result) > 30000:
                    error_result = error_result[:30000] + '\n... (output truncated)'
                yield ToolChunk(content=[TextBlock(text=error_result)], state=ToolResultState.ERROR, is_last=True)
            else:
                yield ToolChunk(content=[TextBlock(text=output)], state=ToolResultState.RUNNING, is_last=True)
        except Exception as e:
            error_msg = f'Command failed: {command}\nError: {str(e)}'
            yield ToolChunk(content=[TextBlock(text=error_msg)], state=ToolResultState.ERROR, is_last=True)