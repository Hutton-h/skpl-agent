"""Bash command parser using tree-sitter for precise syntax analysis.

This module provides utilities to parse Bash commands and extract meaningful
information for permission rule generation, including:
- Splitting compound commands (&&, ||, ;, |)
- Extracting command prefixes (e.g., "npm run" from "npm run build")
- Extracting file paths from commands for dangerous path detection
- Extracting output redirections
- Checking if commands are read-only
"""
from typing import List, Optional, Set, Tuple
import re
import shlex
import tree_sitter_bash as tsbash
from tree_sitter import Language, Parser, Node
from .._constants import DANGEROUS_NODE_TYPES, DANGEROUS_COMMANDS
SAFE_COMMANDS: Set[str] = {'echo', 'cat', 'ls', 'pwd', 'cd', 'true', 'false', 'printf', 'grep', 'tee'}
SAFE_ENV_VARS = {'NODE_ENV', 'PYTHONUNBUFFERED', 'RUST_LOG', 'LANG', 'TERM', 'NO_COLOR', 'FORCE_COLOR', 'DEBUG', 'VERBOSE', 'CI', 'PATH', 'HOME', 'USER', 'SHELL', 'EDITOR', 'PAGER', 'TZ', 'LC_ALL', 'LC_CTYPE', 'COLUMNS', 'LINES', 'CLICOLOR', 'CLICOLOR_FORCE'}
GIT_READ_ONLY_COMMANDS = {'git status', 'git log', 'git diff', 'git show', 'git branch', 'git tag', 'git remote', 'git ls-files', 'git ls-tree', 'git cat-file', 'git rev-parse', 'git rev-list', 'git describe', 'git shortlog', 'git blame', 'git grep', 'git reflog', 'git config --get', 'git config --list'}
READ_ONLY_COMMANDS = {'ls', 'cat', 'head', 'tail', 'less', 'more', 'file', 'stat', 'wc', 'grep', 'rg', 'ag', 'ack', 'find', 'tree', 'pwd', 'which', 'whereis', 'type', *GIT_READ_ONLY_COMMANDS, 'docker ps', 'docker images', 'docker inspect', 'docker logs', 'docker version', 'docker info', 'gh repo view', 'gh issue list', 'gh pr list', 'gh status', 'python --version', 'python -V', 'node --version', 'node -v', 'npm list', 'npm ls', 'pip list', 'pip show'}
FIND_MUTATING_PREDICATES = {'-delete', '-exec', '-execdir', '-fls', '-fprint', '-fprint0', '-fprintf', '-ok', '-okdir'}

class BashCommandParser:
    """Parse Bash commands using tree-sitter for accurate syntax analysis."""

    def __init__(self) -> None:
        """Initialize the parser with tree-sitter-bash language."""
        self.parser = Parser(Language(tsbash.language()))

    def is_read_only_command(self, command: str) -> bool:
        """Check if a command is read-only (safe to auto-allow).

        For compound commands (&&, ||, ;, |), ALL subcommands must be
        read-only for the entire command to be considered read-only.

        Commands with output redirections (>, >>) are NOT considered read-only.

        Args:
            command (`str`):
                The bash command string

        Returns:
            `bool`:
                True if the command (and all subcommands) are read-only,
                False otherwise
        """
        cmd = command.strip()
        if '>' in cmd:
            return False
        if any((op in cmd for op in ['&&', '||', ';', '|'])):
            try:
                tree = self.parser.parse(bytes(cmd, 'utf8'))
                root = tree.root_node
                subcommands = self.split_compound_command(root, cmd)
                for subcmd in subcommands:
                    if not self._is_single_command_read_only(subcmd.strip()):
                        return False
                return True
            except Exception:
                return False
        return self._is_single_command_read_only(cmd)

    def _is_single_command_read_only(self, cmd: str) -> bool:
        """Check if a single (non-compound) command is read-only.

        Args:
            cmd (`str`):
                A single command string (no &&, ||, ;, |)

        Returns:
            `bool`:
                True if the command is read-only, False otherwise
        """
        if cmd in READ_ONLY_COMMANDS:
            return True
        if self._is_mutating_find_command(cmd):
            return False
        for readonly_cmd in READ_ONLY_COMMANDS:
            if cmd == readonly_cmd or cmd.startswith(readonly_cmd + ' '):
                return True
        tokens = cmd.split()
        if tokens:
            base_cmd = tokens[0]
            i = 0
            while i < len(tokens) and '=' in tokens[i]:
                i += 1
            if i < len(tokens):
                base_cmd = tokens[i]
            if base_cmd in SAFE_COMMANDS:
                return True
        return False

    def _is_mutating_find_command(self, cmd: str) -> bool:
        """Check if a find command contains mutating predicates via AST."""
        try:
            tree = self.parser.parse(bytes(cmd, 'utf8'))
        except Exception:
            return False
        root = tree.root_node
        cmd_node = self._find_first_simple_command(root)
        if cmd_node is None:
            return False
        name_node = cmd_node.child_by_field_name('name')
        if name_node is None or name_node.text.decode('utf8') != 'find':
            return False
        for child in cmd_node.children:
            if child.type == 'word':
                text = child.text.decode('utf8')
                if text in FIND_MUTATING_PREDICATES:
                    return True
        return False

    def extract_file_paths(self, command: str) -> List[Tuple[str, str]]:
        """Extract file paths from a bash command using tree-sitter.

        Returns paths that are arguments to file-manipulating commands
        (rm, mv, cp, chmod, chown, etc.) and output redirection targets.

        Args:
            command (`str`):
                The bash command string

        Returns:
            `List[Tuple[str, str]]`:
                List of tuples (command_name, file_path)
        """
        paths = []
        try:
            tree = self.parser.parse(bytes(command, 'utf8'))
            root = tree.root_node
            self._extract_paths_from_node(root, command, paths)
        except Exception:
            paths = self._extract_paths_fallback(command)
        return paths

    def _extract_paths_from_node(self, node: Node, command: str, paths: List[Tuple[str, str]]) -> None:
        """Recursively extract file paths from AST nodes.

        Args:
            node (`Node`):
                The AST node to process
            command (`str`):
                The original command string
            paths (`List[Tuple[str, str]]`):
                List to append (command_name, path) tuples to
        """
        if node.type == 'file_redirect':
            for child in node.children:
                if child.type == 'word':
                    path = command[child.start_byte:child.end_byte]
                    paths.append(('redirect', path.strip('\'"')))
        if node.type == 'command':
            cmd_name = None
            args = []
            for child in node.children:
                if child.type == 'command_name':
                    cmd_name = command[child.start_byte:child.end_byte]
                elif child.type == 'word' and cmd_name:
                    arg = command[child.start_byte:child.end_byte]
                    args.append(arg.strip('\'"'))
            if cmd_name in ['rm', 'mv', 'cp', 'chmod', 'chown', 'chgrp', 'touch', 'ln', 'sed', 'mkdir', 'rmdir']:
                for arg in args:
                    if not arg.startswith('-'):
                        paths.append((cmd_name, arg))
        for child in node.children:
            self._extract_paths_from_node(child, command, paths)

    def _extract_paths_fallback(self, command: str) -> List[Tuple[str, str]]:
        """Fallback path extraction using simple token parsing.

        Args:
            command (`str`):
                The bash command string

        Returns:
            `List[Tuple[str, str]]`:
                List of tuples (command_name, file_path)
        """
        paths = []
        tokens = command.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in ['>', '>>', '2>', '&>']:
                if i + 1 < len(tokens):
                    path = tokens[i + 1].strip('\'"')
                    paths.append(('redirect', path))
                i += 2
                continue
            if token in ['rm', 'mv', 'cp', 'chmod', 'chown', 'sed', 'touch', 'mkdir', 'rmdir']:
                cmd_name = token
                j = i + 1
                while j < len(tokens):
                    arg = tokens[j].strip('\'"')
                    if arg.startswith('-'):
                        j += 1
                        continue
                    paths.append((cmd_name, arg))
                    j += 1
                break
            i += 1
        return paths

    def extract_redirections(self, command: str) -> List[str]:
        """Extract output redirection targets from a bash command.

        Args:
            command (`str`):
                The bash command string

        Returns:
            `List[str]`:
                List of file paths that are redirection targets
        """
        redirections = []
        try:
            tree = self.parser.parse(bytes(command, 'utf8'))
            root = tree.root_node
            self._extract_redirections_from_node(root, command, redirections)
        except Exception:
            tokens = command.split()
            for (i, token) in enumerate(tokens):
                if token in ['>', '>>', '2>', '&>'] and i + 1 < len(tokens):
                    path = tokens[i + 1].strip('\'"')
                    redirections.append(path)
        return redirections

    def _extract_redirections_from_node(self, node: Node, command: str, redirections: List[str]) -> None:
        """Recursively extract redirections from AST nodes.

        Args:
            node (`Node`):
                The AST node to process
            command (`str`):
                The original command string
            redirections (`List[str]`):
                List to append redirection targets to
        """
        if node.type == 'file_redirect':
            for child in node.children:
                if child.type == 'word':
                    path = command[child.start_byte:child.end_byte]
                    redirections.append(path.strip('\'"'))
        for child in node.children:
            self._extract_redirections_from_node(child, command, redirections)

    def extract_command_prefixes(self, command: str, max_prefixes: int=5) -> List[str]:
        """Extract command prefixes from a bash command.

        Automatically handles compound commands (&&, ||, ;, |) and extracts
        prefixes from each subcommand. Returns deduplicated list of prefixes.

        Args:
            command (`str`):
                The bash command string (may be compound)
            max_prefixes (`int`):
                Maximum number of prefixes to return (default: 5)

        Returns:
            `List[str]`:
                List of command prefixes (deduplicated), e.g., ["npm run",
                "git commit"]

        Examples:
            >>> parser.extract_command_prefixes("git add . && git commit")
            ['git add', 'git commit']
            >>> parser.extract_command_prefixes("npm run build")
            ['npm run']
            >>> parser.extract_command_prefixes("ls -la")
            []
        """
        if not command or not command.strip():
            return []
        tree = self.parser.parse(bytes(command, 'utf8'))
        root = tree.root_node
        subcommands = self.split_compound_command(root, command)
        prefixes = []
        seen = set()
        for subcmd in subcommands[:max_prefixes]:
            prefix = self._extract_command_prefix(subcmd)
            if prefix and prefix not in seen:
                prefixes.append(prefix)
                seen.add(prefix)
            if len(prefixes) >= max_prefixes:
                break
        return prefixes

    def split_compound_command(self, root: Node, command: str) -> List[str]:
        """Split compound commands using tree-sitter for precise parsing.

        Recognizes: &&, ||, ;, |

        Args:
            root (`Node`):
                The root AST node
            command (`str`):
                The original command string

        Returns:
            `List[str]`:
                List of individual subcommands
        """
        subcommands = []

        def extract_commands(node: Node) -> None:
            """Recursively extract commands from AST."""
            if node.type == 'command':
                cmd_text = command[node.start_byte:node.end_byte]
                subcommands.append(cmd_text)
            elif node.type in ['list', 'pipeline', 'command_list']:
                for child in node.children:
                    if child.type not in ['&&', '||', ';', '|', '|&']:
                        extract_commands(child)
            else:
                for child in node.children:
                    extract_commands(child)
        extract_commands(root)
        return subcommands if subcommands else [command]

    def _extract_command_prefix(self, subcmd: str) -> Optional[str]:
        """Extract command prefix (first two words) from a subcommand.

        Logic:
        1. Skip safe environment variable assignments
        2. Extract command name and first subcommand
        3. Verify the second word looks like a subcommand (not a flag)

        Args:
            subcmd (`str`):
                The subcommand string to extract prefix from

        Returns:
            `Optional[str]`:
                Command prefix (e.g., "npm run") or None if cannot extract
        """
        tree = self.parser.parse(bytes(subcmd, 'utf8'))
        root = tree.root_node
        simple_cmd = self._find_first_simple_command(root)
        if not simple_cmd:
            return None
        parts = []
        env_vars = []
        for child in simple_cmd.children:
            if child.type == 'variable_assignment':
                var_name = subcmd[child.start_byte:child.end_byte].split('=')[0]
                env_vars.append(var_name)
            elif child.type == 'command_name':
                parts.append(subcmd[child.start_byte:child.end_byte])
            elif child.type == 'word' and len(parts) >= 1:
                word = subcmd[child.start_byte:child.end_byte]
                parts.append(word)
                if len(parts) >= 2:
                    break
        if env_vars and (not all((v in SAFE_ENV_VARS for v in env_vars))):
            return None
        if parts and parts[0].lower() in SAFE_COMMANDS:
            return None
        if len(parts) >= 2:
            return ' '.join(parts[:2])
        return None

    def _find_first_simple_command(self, node: Node) -> Optional[Node]:
        """Recursively find the first command node in AST.

        Args:
            node (`Node`):
                The AST node to search from

        Returns:
            `Optional[Node]`:
                The first command node found, or None
        """
        if node.type == 'command':
            return node
        for child in node.children:
            result = self._find_first_simple_command(child)
            if result:
                return result
        return None

    def check_dangerous_command(self, command: str) -> Optional[str]:
        """Check if command contains dangerous patterns.

        Uses word-boundary aware matching to avoid false positives like
        'git add' matching 'dd' pattern.

        Args:
            command (`str`):
                The bash command to check

        Returns:
            `Optional[str]`:
                The matched dangerous pattern if found, None otherwise
        """
        normalized = ' '.join(command.split())
        for pattern in DANGEROUS_COMMANDS:
            if ' ' not in pattern and len(pattern) <= 4:
                regex = '\\b' + re.escape(pattern) + '\\b'
                if re.search(regex, normalized):
                    return pattern
            elif pattern in normalized:
                return pattern
        return None

    def check_sed_constraints(self, command: str, dangerous_files: List[str]) -> str | None:
        """Check if sed command violates safety constraints.

        Implements allowlist/denylist system:
        - Allowlist: Line printing (sed -n 'Np') and substitution (sed 's///')
        - Denylist: Dangerous operations (w/W/e/E), file writes, command
         execution

        Args:
            command: The bash command to check
            dangerous_files: List of dangerous file patterns

        Returns:
            Error message if dangerous sed operation found, None otherwise
        """
        if 'sed' not in command:
            return None
        try:
            tokens = shlex.split(command)
        except ValueError:
            return 'sed command has invalid shell syntax'
        sed_idx = None
        for (i, token) in enumerate(tokens):
            if token == 'sed' or token.endswith('/sed'):
                sed_idx = i
                break
        if sed_idx is None:
            return None
        args = tokens[sed_idx + 1:]
        flags = []
        expressions = []
        file_args = []
        i = 0
        found_first_expr = False
        while i < len(args):
            arg = args[i]
            if arg.startswith('-') and (not arg.startswith('--')):
                flag_chars = arg[1:]
                for char in flag_chars:
                    flags.append(char)
                if 'i' in flag_chars and i + 1 < len(args):
                    next_arg = args[i + 1]
                    if not next_arg.startswith('-') and (not next_arg.startswith('s')) and ('.' not in next_arg):
                        i += 1
            elif arg == '--in-place':
                flags.append('i')
                if i + 1 < len(args):
                    next_arg = args[i + 1]
                    if not next_arg.startswith('-') and (not next_arg.startswith('s')) and ('.' not in next_arg):
                        i += 1
            elif arg in ['-e', '--expression']:
                if i + 1 < len(args):
                    expressions.append(args[i + 1])
                    i += 1
            elif not arg.startswith('-'):
                if not found_first_expr:
                    expressions.append(arg)
                    found_first_expr = True
                else:
                    file_args.append(arg)
            i += 1
        if not expressions:
            return 'sed command missing expression'
        allowed_flags = {'n', 'E', 'e', 'i'}
        for flag in flags:
            if flag not in allowed_flags:
                return f'sed flag -{flag} not allowed'
        has_n_flag = 'n' in flags
        has_i_flag = 'i' in flags
        for expr in expressions:
            if re.search('/[wW]\\s+\\S+', expr) or expr.endswith('/w') or expr.endswith('/W'):
                return 'sed write operation (w/W) not allowed'
            if re.search('/[eE](?:\\s|$)', expr) or expr.endswith('/e') or expr.endswith('/E'):
                return 'sed execute operation (e/E) not allowed'
            if '{' in expr or '}' in expr:
                return 'sed curly braces not allowed'
            if expr.startswith('!'):
                return 'sed negation (!) not allowed'
            if '#' in expr and (not expr.startswith('s#')):
                return 'sed comments not allowed'
            if has_n_flag:
                if re.match('^\\d+p$', expr) or re.match('^\\d+,\\d+p$', expr):
                    continue
            if expr.startswith('s/') or expr.startswith('s|') or expr.startswith('s#'):
                delimiter = expr[1]
                parts = expr[2:].split(delimiter)
                if len(parts) >= 2:
                    if len(parts) > 2:
                        sub_flags = parts[2]
                        if all((c in 'gp0123456789' for c in sub_flags)):
                            continue
                    else:
                        continue
            return f"sed expression '{expr}' not in allowlist"
        if has_i_flag and file_args:
            for file_path in file_args:
                for dangerous_file in dangerous_files:
                    if dangerous_file in file_path or file_path.endswith(dangerous_file):
                        return f'sed -i modifying dangerous file: {file_path}'
        return None

    def check_injection_risk(self, command: str) -> Optional[str]:
        """Check if command contains structures that cannot be statically
        analyzed.

        This detects command substitution, process substitution, complex
        expansions, control flow, and other dynamic shell features that
        make it impossible to determine the command's behavior without
        execution.

        Args:
            command (`str`):
                The bash command to check

        Returns:
            `Optional[str]`:
                Reason string if command is too complex, None if it can be
                statically analyzed

        Examples:
            >>> parser.check_injection_risk("ls -la")
            None
            >>> parser.check_injection_risk("rm $(find . -name '*.tmp')")
            "Command contains command_substitution which cannot be statically
            analyzed"
            >>> parser.check_injection_risk("for f in *.txt; do cat $f; done")
            "Command contains for_statement which cannot be statically
            analyzed"
        """
        try:
            tree = self.parser.parse(bytes(command, 'utf8'))
            return self._walk_for_dangerous_nodes(tree.root_node)
        except Exception:
            return 'Command parsing failed, cannot verify safety'

    def _walk_for_dangerous_nodes(self, node: Node) -> Optional[str]:
        """Recursively walk AST to find dangerous node types.

        Args:
            node (`Node`):
                The AST node to check

        Returns:
            `Optional[str]`:
                Reason string if dangerous node found, None otherwise
        """
        if node.type in DANGEROUS_NODE_TYPES:
            return f'Command contains {node.type} which cannot be statically analyzed'
        for child in node.children:
            result = self._walk_for_dangerous_nodes(child)
            if result:
                return result
        return None