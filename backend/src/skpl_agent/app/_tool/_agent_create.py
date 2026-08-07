"""The AgentCreate tool — spawns a worker into the current team."""
from __future__ import annotations
import copy
import json
from typing import TYPE_CHECKING
from pydantic import Field
from ._team_tool_base import _TeamToolBase
from .._types import SubAgentTemplate
from ..message_bus import MessageBusKeys
from .._bus_ops import enqueue_run_trigger
from ..storage import AgentData, AgentRecord, SessionConfig, TeamMember
from ..storage._utils import _ensure_team_members
from ...message import HintBlock, TextBlock, ToolResultState
from ...permission import PermissionContext
from ...state import AgentState
from ...tool import ToolChunk, ParamsBase
if TYPE_CHECKING:
    from ..message_bus import MessageBus
    from ..storage import StorageBase
    from ..workspace_manager import WorkspaceManagerBase
_DEFAULT_SYSTEM_PROMPT_TEMPLATE = "You are {member_name}, a member of team '{team_name}' led by {leader_name}.\n\nTeam purpose: {team_description}\n\nYour role: {member_description}\n\nYou communicate with the team leader and other members through the TeamSay tool. Speak on the team only when you have something external to share — your private reasoning stays private."
DEFAULT_SUB_AGENT_TEMPLATE = SubAgentTemplate(type='default', description='Default worker agent with standard configuration.', system_prompt_template=_DEFAULT_SYSTEM_PROMPT_TEMPLATE, override_leader_mode=False, extend_leader_permission_rules=True, extend_leader_working_directories=True)

def _merge_leader_permissions(template: SubAgentTemplate, leader_context: PermissionContext) -> PermissionContext:
    """Build the worker's permission context from the template, layered
    with the leader's runtime state according to the template's three
    inherit-from-leader flags.

    - ``override_leader_mode``: if True, the template's
      :attr:`PermissionContext.mode` wins; otherwise the worker
      inherits the leader's mode.
    - ``extend_leader_permission_rules``: if True, the leader's
      allow/deny/ask rules are appended after the template's rules for
      each tool, so the worker doesn't re-prompt for permissions the
      user has already granted in the leader session. The template's
      rules appear first in each list, so the engine — which returns
      on the first matching rule per stage — evaluates the template's
      intent before the leader's.
    - ``extend_leader_working_directories``: if True, the leader's
      working directories are merged in; on key (path) collisions the
      template's entry wins.

    The template fields are deep-copied so the returned context is
    independent of both the template and the leader state.
    """
    merged = template.permission_context.model_copy(deep=True)
    if not template.override_leader_mode:
        merged.mode = leader_context.mode
    if template.extend_leader_working_directories:
        for (path, wd) in leader_context.working_directories.items():
            merged.working_directories.setdefault(path, wd.model_copy(deep=True))
    if template.extend_leader_permission_rules:
        for attr in ('allow_rules', 'deny_rules', 'ask_rules'):
            merged_rules: dict = getattr(merged, attr)
            for (tool_name, rules) in getattr(leader_context, attr).items():
                merged_rules.setdefault(tool_name, []).extend((r.model_copy(deep=True) for r in rules))
    return merged

class _AgentCreateParams(ParamsBase):
    """Parameters for :class:`AgentCreate`."""
    name: str = Field(description='Short identifier for the new member, e.g. ``"researcher"`` or ``"coder-1"``. Other members address it via ``TeamSay(to=<this name>)``, so it MUST be unique within the team.')
    description: str = Field(description='One-sentence summary of the member\'s role — e.g. ``"Researches background information on the target topic"``. Becomes part of the member\'s system prompt so it understands its place in the team.')
    prompt: str = Field(description='The first task delivered to the member as a user message. The member begins executing immediately upon creation, so make this concrete and self-contained — do not just say ``"wait for instructions"`` (use TeamSay later instead). Include any context, constraints, deliverables, and deadlines the member needs.')

class AgentCreate(_TeamToolBase):
    """Spawn a new worker member into the team you lead."""
    name: str = 'AgentCreate'
    is_state_injected: bool = True
    description: str = 'Add a new member to the team you lead.\n\n## When to Use This Tool\nAfter ``TeamCreate``, call this for each member you want on the team. Each call:\n- Creates a worker agent dedicated to this team.\n- Delivers ``prompt`` as the worker\'s first user message — **the worker starts executing it immediately**. (So DONT use ``TeamSay`` right after creating one agent).\n\n## When NOT to Use This Tool\n- You\'re not currently leading a team. Call ``TeamCreate`` first.\n- The new member would duplicate an existing member\'s role; reuse the existing member via ``TeamSay`` instead.\n\n## Effects\n- Use the ``name`` you chose as ``to=<name>`` in ``TeamSay`` to direct messages to this member specifically. Names must be unique within the team (including against the leader\'s name); duplicates are rejected.\n- Members spawned this way live only as long as the team — they are deleted when ``TeamDelete`` is called.\n\n## Important\n- You are responsible for organising the team, assigning tasks, collecting every member\'s report, and producing the final answer — all members report directly to you. Therefore, **DO NOT** encourage members to communicate with each other, and **AVOID** creating "integrator"-style members; both make the overall communication topology unnecessarily complex.\n'
    input_schema: dict = _AgentCreateParams.model_json_schema()

    def __init__(self, storage: 'StorageBase', message_bus: 'MessageBus', workspace_manager: 'WorkspaceManagerBase', user_id: str, session_id: str, agent_id: str, sub_agent_templates: dict[str, SubAgentTemplate] | None=None) -> None:
        """Bind request-scoped identifiers plus sub-agent templates.

        Extends :meth:`_TeamToolBase.__init__` with the optional
        template registry. The built-in ``"default"`` template is
        always injected; extra templates unlock a ``subagent_type``
        enum in the tool's input schema.

        Args:
            storage (`StorageBase`):
                Application storage backend.
            message_bus (`MessageBus`):
                Application message bus.
            workspace_manager (`WorkspaceManagerBase`):
                Workspace manager (forwarded to base for uniform
                team-tool wiring; currently unused here).
            user_id (`str`):
                The owner user id.
            session_id (`str`):
                The calling session id.
            agent_id (`str`):
                The calling agent id.
            sub_agent_templates (`dict[str, SubAgentTemplate] | None`, optional):
                Template registry keyed by type.
        """
        super().__init__(storage, message_bus, workspace_manager, user_id, session_id, agent_id)
        self._sub_agent_templates: dict[str, SubAgentTemplate] = dict(sub_agent_templates or {})
        if 'default' not in self._sub_agent_templates:
            self._sub_agent_templates['default'] = DEFAULT_SUB_AGENT_TEMPLATE
        has_custom_templates = set(self._sub_agent_templates) != {'default'}
        if has_custom_templates:
            schema = copy.deepcopy(_AgentCreateParams.model_json_schema())
            type_descriptions = '\n'.join((f'- ``{t.type!r}`` — {t.description}' for t in self._sub_agent_templates.values()))
            schema['properties']['subagent_type'] = {'type': 'string', 'enum': list(self._sub_agent_templates), 'description': f'The type of sub-agent template to use. Available types:\n\n{type_descriptions}\n\nEach type has pre-configured system prompt, permissions, and task context.'}
            self.input_schema = schema

    async def __call__(self, name: str, description: str, prompt: str, subagent_type: str='default', _agent_state: AgentState | None=None) -> ToolChunk:
        """Spawn the worker agent + session directly via storage.

        Reads the current session + team records from storage to
        enforce two preconditions: the calling session must be in a
        team, and it must be that team's leader.

        The worker's configuration (system prompt, context/react
        config, permission context, task context) is determined by
        the :class:`SubAgentTemplate` matching ``subagent_type``. The
        leader's user-confirmed permission rules and working
        directories are merged into the template's permission context
        so the worker does not re-prompt for permissions the user has
        already granted.

        Args:
            name (`str`):
                Short identifier for the worker, unique within the
                team. Used as the ``to`` target in ``TeamSay``.
            description (`str`):
                One-sentence summary of the worker's role.
            prompt (`str`):
                First task delivered as a user message to the worker.
            subagent_type (`str`, defaults to ``"default"``):
                Template type to use. Must match a registered
                :class:`SubAgentTemplate.type`.
            _agent_state (`AgentState | None`, optional):
                Live leader state injected by the toolkit.

        Returns:
            `ToolChunk`:
                A success message containing the new member id, or an
                error chunk on failure.
        """
        try:
            session = await self._storage.get_session(self._user_id, self._agent_id, self._session_id)
            if session is None or session.team_id is None:
                return ToolChunk(content=[TextBlock(text='AgentCreate: this session is not in any team — call TeamCreate first.')], state=ToolResultState.ERROR)
            team = await self._storage.get_team(self._user_id, session.team_id)
            if team is None:
                return ToolChunk(content=[TextBlock(text=f'AgentCreate: team {session.team_id} no longer exists.')], state=ToolResultState.ERROR)
            if team.session_id != self._session_id:
                return ToolChunk(content=[TextBlock(text='AgentCreate: only the team leader can add members; this session is a worker.')], state=ToolResultState.ERROR)
            leader_session = await self._storage.get_session(self._user_id, '', team.session_id)
            if leader_session is None:
                return ToolChunk(content=[TextBlock(text=f'AgentCreate: leader session {team.session_id} for team {team.id} is missing — team is in an inconsistent state.')], state=ToolResultState.ERROR)
            template = self._sub_agent_templates.get(subagent_type)
            if template is None:
                available = list(self._sub_agent_templates)
                return ToolChunk(content=[TextBlock(text=f'AgentCreate: unknown subagent_type {subagent_type!r}; expected one of {available}.')], state=ToolResultState.ERROR)
            if '@' in name:
                return ToolChunk(content=[TextBlock(text=f"AgentCreate: member name {name!r} cannot contain the character '@'.")], state=ToolResultState.ERROR)
            leader_agent_record = await self._storage.get_agent(self._user_id, leader_session.agent_id)
            existing_names: set[str] = set()
            if leader_agent_record is not None:
                existing_names.add(leader_agent_record.data.name)
            members = await _ensure_team_members(self._storage, self._user_id, team)
            for member in members:
                member_record = await self._storage.get_agent(member.owner_id, member.agent_id)
                if member_record is not None:
                    existing_names.add(member_record.data.name)
            if name in existing_names:
                return ToolChunk(content=[TextBlock(text=f"AgentCreate: a team member named {name!r} already exists. Member names must be unique within the team (including the leader's name); pick another.")], state=ToolResultState.ERROR)
            leader_name = leader_agent_record.data.name if leader_agent_record is not None else leader_session.agent_id
            system_prompt = template.system_prompt_template.format(team_name=team.data.name, team_description=team.data.description, member_name=name, member_description=description, leader_name=leader_name)
            worker_agent = AgentRecord(user_id=self._user_id, source='team', data=AgentData(name=name, system_prompt=system_prompt, context_config=template.context_config.model_copy(deep=True), react_config=template.react_config.model_copy(deep=True)))
            await self._storage.upsert_agent(self._user_id, worker_agent)
            leader_permission_context = _agent_state.permission_context if _agent_state is not None else leader_session.state.permission_context
            worker_permission_context = _merge_leader_permissions(template, leader_permission_context)
            worker_state = AgentState(permission_context=worker_permission_context, tasks_context=template.tasks_context.model_copy(deep=True))
            worker_session = await self._storage.upsert_session(user_id=self._user_id, agent_id=worker_agent.id, config=SessionConfig(workspace_id=leader_session.config.workspace_id, name=f'team:{team.id}/{name}', chat_model_config=leader_session.config.chat_model_config, fallback_chat_model_config=leader_session.config.fallback_chat_model_config), state=worker_state)
            await self._storage.set_session_team_id(self._user_id, worker_session.id, team.id)
            team.data.member_ids = [*team.data.member_ids, worker_agent.id]
            team.data.members = [*members, TeamMember(owner_id=self._user_id, agent_id=worker_agent.id, session_id=worker_session.id, role='created')]
            await self._storage.upsert_team(self._user_id, team)
            hint = HintBlock(hint=f'<team-message from="{leader_name}">\n{prompt}\n</team-message>', source=json.dumps({'label': 'team_message', 'sublabel': leader_name}, ensure_ascii=False))
            await self._message_bus.queue_push(MessageBusKeys.inbox(worker_session.id), hint.model_dump(mode='json'))
            await enqueue_run_trigger(self._message_bus, user_id=self._user_id, session_id=worker_session.id, agent_id=worker_agent.id)
            return ToolChunk(content=[TextBlock(text=f'Member {name!r} added to team {team.data.name!r}.')])
        except Exception as e:
            return ToolChunk(content=[TextBlock(text=f'AgentCreate failed: {e}')], state=ToolResultState.ERROR)