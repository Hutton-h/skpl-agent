/**
 * One entry of the backend skill library (``GET /skill-library/``).
 * ``installed`` reflects whether the skill is already equipped in the
 * current ``(agent_id, session_id)`` workspace.
 */
export interface SkillLibraryItem {
	name: string;
	description: string;
	version: string;
	category: string;
	when_to_use?: string | null;
	dir_name: string;
	installed: boolean;
}

/** Response of ``POST /skill-library/install``. */
export interface SkillLibraryInstallResponse {
	ok: boolean;
	already?: boolean;
}
