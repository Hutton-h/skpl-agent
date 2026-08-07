import type { SkillLibraryInstallResponse, SkillLibraryItem } from '../types/skillLibrary';
import { client } from './client';

/**
 * Skill library API — browse, install and uninstall curated skills for
 * the current ``(agentId, sessionId)`` workspace. Follows the same flat
 * query-param style as ``workspaceApi``; JWT auth is handled by the
 * shared client.
 */
export const skillLibraryApi = {
	list: (agentId: string, sessionId: string) =>
		client.get<SkillLibraryItem[]>('/skill-library/', {
			agent_id: agentId,
			session_id: sessionId,
		}),

	categories: () => client.get<string[]>('/skill-library/categories'),

	install: (name: string, agentId: string, sessionId: string) =>
		client.post<SkillLibraryInstallResponse>('/skill-library/install', {
			name,
			agent_id: agentId,
			session_id: sessionId,
		}),

	uninstall: (name: string, agentId: string, sessionId: string) =>
		client.post<void>('/skill-library/uninstall', {
			name,
			agent_id: agentId,
			session_id: sessionId,
		}),
};
