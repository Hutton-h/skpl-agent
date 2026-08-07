import {
	CircleAlert,
	Download,
	FileX,
	Loader2,
	PackageOpen,
	PlusCircle,
	Search,
	SearchX,
	Trash,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import type { Skill } from '@/api';
import { skillLibraryApi } from '@/api';
import { AddSkillDialog } from '@/components/dialog/AddSkillDialog.tsx';
import { DeleteDialog } from '@/components/dialog/DeleteDialog.tsx';
import { PanelEmpty } from '@/components/panel/PanelEmpty';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group';
import { Item, ItemActions, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useTranslation } from '@/i18n/useI18n.ts';
import type { SkillLibraryItem } from '@/types/skillLibrary';

interface SkillPanelProps {
	/** The skills equipped in the workspace. */
	skills: Skill[];
	/** Whether the skill list is still loading. */
	loading?: boolean;
	/**
	 * Add a skill to the workspace.
	 *
	 * @param skillPath - Path of the skill to add.
	 */
	onAdd: (skillPath: string) => Promise<void>;
	/**
	 * Remove a skill by name.
	 *
	 * @param name - The skill name to remove.
	 */
	onRemove: (name: string) => Promise<void>;
	/**
	 * Agent owning the workspace — needed by the skill-library tab.
	 * Optional for backward compatibility; the library tab renders an
	 * empty state without it.
	 */
	agentId?: string | null;
	/** Session owning the workspace — see {@link agentId}. */
	sessionId?: string | null;
	/**
	 * Called after a library install/uninstall succeeded so the parent
	 * can refetch the equipped skill list.
	 */
	onSkillsChanged?: () => Promise<void> | void;
}

interface SkillLibraryTabProps {
	agentId?: string | null;
	sessionId?: string | null;
	onSkillsChanged?: () => Promise<void> | void;
}

/**
 * The "skill library" tab: fetches the curated library for the current
 * workspace, groups entries by category (ordered by the backend's
 * category list) and offers install/uninstall actions. Errors surface
 * via the shared client's toast; the inline error state offers a retry.
 */
function SkillLibraryTab({ agentId, sessionId, onSkillsChanged }: SkillLibraryTabProps) {
	const { t } = useTranslation();
	const [items, setItems] = useState<SkillLibraryItem[]>([]);
	const [categories, setCategories] = useState<string[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<Error | null>(null);
	/** Names with an in-flight install/uninstall request. */
	const [pending, setPending] = useState<ReadonlySet<string>>(new Set());

	const refetch = useCallback(async () => {
		if (!agentId || !sessionId) {
			setItems([]);
			setCategories([]);
			return;
		}
		setLoading(true);
		setError(null);
		try {
			const [list, cats] = await Promise.all([
				skillLibraryApi.list(agentId, sessionId),
				skillLibraryApi.categories(),
			]);
			setItems(list);
			setCategories(cats);
		} catch (e) {
			setError(e as Error);
		} finally {
			setLoading(false);
		}
	}, [agentId, sessionId]);

	useEffect(() => {
		refetch();
	}, [refetch]);

	const runAction = useCallback(
		async (name: string, action: 'install' | 'uninstall') => {
			if (!agentId || !sessionId) return;
			setPending((prev) => new Set(prev).add(name));
			try {
				if (action === 'install') {
					await skillLibraryApi.install(name, agentId, sessionId);
				} else {
					await skillLibraryApi.uninstall(name, agentId, sessionId);
				}
				// Refresh both lists: the library view (installed flags) and
				// the equipped tab in the parent.
				await refetch();
				await onSkillsChanged?.();
			} catch {
				// The shared client already toasted the ApiError detail.
			} finally {
				setPending((prev) => {
					const next = new Set(prev);
					next.delete(name);
					return next;
				});
			}
		},
		[agentId, sessionId, refetch, onSkillsChanged],
	);

	if (!agentId || !sessionId) {
		return (
			<PanelEmpty
				icon={PackageOpen}
				title={t('panel.skill.library.emptyTitle')}
				description={t('panel.skill.library.noSessionDescription')}
			/>
		);
	}

	if (loading) {
		return (
			<div className="flex flex-1 items-center justify-center">
				<p className="text-muted-foreground text-sm">{t('panel.loading')}</p>
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-1 flex-col items-center justify-center gap-y-2">
				<p className="text-muted-foreground text-sm">
					{t('panel.skill.library.errorTitle')}
				</p>
				<Button variant="outline" size="sm" onClick={refetch}>
					<CircleAlert />
					{t('common.retry')}
				</Button>
			</div>
		);
	}

	if (items.length === 0) {
		return (
			<PanelEmpty
				icon={PackageOpen}
				title={t('panel.skill.library.emptyTitle')}
				description={t('panel.skill.library.emptyDescription')}
			/>
		);
	}

	// Group by category, ordered by the backend category list; unknown
	// categories append in first-seen order.
	const orderedCategories = [
		...categories,
		...items.map((i) => i.category).filter((c) => !categories.includes(c)),
	].filter((c, i, arr) => arr.indexOf(c) === i);

	return (
		<div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-y-3">
			{orderedCategories.map((category) => {
				const group = items.filter((i) => i.category === category);
				if (group.length === 0) return null;
				return (
					<div key={category} className="flex flex-col gap-y-2">
						<span className="text-muted-foreground text-xs font-semibold uppercase tracking-wide">
							{t(`panel.skill.library.categories.${category}`, {
								defaultValue: category,
							})}
						</span>
						{group.map((item) => {
							const isPending = pending.has(item.name);
							return (
								<Item key={item.name} variant="outline">
									<ItemContent>
										<ItemTitle>
											{item.name}
											<Badge variant="outline">v{item.version}</Badge>
										</ItemTitle>
										<ItemDescription>{item.description}</ItemDescription>
										{item.when_to_use ? (
											<ItemDescription className="text-xs">
												{item.when_to_use}
											</ItemDescription>
										) : null}
									</ItemContent>
									<ItemActions>
										{item.installed ? (
											<>
												<Badge variant="secondary">
													{t('panel.skill.library.installed')}
												</Badge>
												<Button
													variant="outline"
													size="sm"
													disabled={isPending}
													onClick={() => runAction(item.name, 'uninstall')}
												>
													{isPending ? (
														<Loader2 className="animate-spin" />
													) : null}
													{t('panel.skill.library.uninstall')}
												</Button>
											</>
										) : (
											<Button
												variant="default"
												size="sm"
												disabled={isPending}
												onClick={() => runAction(item.name, 'install')}
											>
												{isPending ? (
													<Loader2 className="animate-spin" />
												) : (
													<Download />
												)}
												{t('panel.skill.library.install')}
											</Button>
										)}
									</ItemActions>
								</Item>
							);
						})}
					</div>
				);
			})}
		</div>
	);
}

/**
 * Pure content body for the Skill dock panel, split into two tabs:
 *
 * - **已装备 / Equipped** — a search box, the list of equipped skills,
 *   and an "Add Skill" action (unchanged behaviour).
 * - **技能库 / Library** — the curated skill library with
 *   install/uninstall actions.
 *
 * Holds only local UI state (search text, delete confirmation target);
 * all equipped-skill data arrives via props so it owns no data fetching
 * for that tab. The library tab fetches its own data.
 *
 * Renders without its own header/border — the surrounding `Panel`
 * chrome (from `PanelDock`) provides those.
 *
 * @param skills - The skills to list.
 * @param loading - Whether the list is loading.
 * @param onAdd - Add-skill callback.
 * @param onRemove - Remove-skill callback.
 * @param agentId - Agent owning the workspace (library tab).
 * @param sessionId - Session owning the workspace (library tab).
 * @param onSkillsChanged - Refetch callback fired after library changes.
 * @returns The skill panel body.
 */
export function SkillPanel({
	skills,
	loading = false,
	onAdd,
	onRemove,
	agentId,
	sessionId,
	onSkillsChanged,
}: SkillPanelProps) {
	const { t } = useTranslation();
	const [search, setSearch] = useState('');
	const [deleteOpen, setDeleteOpen] = useState(false);
	const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

	const filtered = search
		? skills.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()))
		: skills;

	return (
		<Tabs defaultValue="equipped" className="flex flex-col flex-1 min-h-0 gap-y-2">
			<TabsList className="w-full shrink-0">
				<TabsTrigger value="equipped">{t('panel.skill.tabEquipped')}</TabsTrigger>
				<TabsTrigger value="library">{t('panel.skill.tabLibrary')}</TabsTrigger>
			</TabsList>

			<TabsContent value="equipped" className="flex flex-col flex-1 min-h-0 gap-y-2 mt-0">
				<span className="text-muted-foreground text-sm">{t('panel.skill.description')}</span>
				<InputGroup>
					<InputGroupInput
						placeholder={t('panel.skill.searchPlaceholder')}
						value={search}
						onChange={(e) => setSearch(e.target.value)}
					/>
					<InputGroupAddon align="inline-end">
						<Search />
					</InputGroupAddon>
				</InputGroup>

				{loading ? (
					<div className="flex flex-1 items-center justify-center">
						<p className="text-muted-foreground text-sm">{t('panel.loading')}</p>
					</div>
				) : filtered.length === 0 ? (
					<PanelEmpty
						icon={search ? SearchX : FileX}
						title={search ? t('panel.search.emptyTitle') : t('panel.skill.emptyTitle')}
						description={
							search
								? t('panel.search.emptyDescription', { query: search })
								: t('panel.skill.emptyDescription')
						}
					/>
				) : (
					<div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-y-2">
						{filtered.map((skill) => (
							<Item key={skill.name} variant="outline">
								<ItemContent>
									<ItemTitle>{skill.name}</ItemTitle>
									<ItemDescription>{skill.description}</ItemDescription>
								</ItemContent>
								<ItemActions>
									<Button
										variant="outline"
										size="icon-sm"
										onClick={() => {
											setDeleteTarget(skill.name);
											setDeleteOpen(true);
										}}
									>
										<Trash />
									</Button>
								</ItemActions>
							</Item>
						))}
					</div>
				)}

				<AddSkillDialog onAdd={onAdd}>
					<Button variant="default">
						<PlusCircle />
						{t('panel.skill.add')}
					</Button>
				</AddSkillDialog>

				<DeleteDialog
					open={deleteOpen}
					onOpenChange={setDeleteOpen}
					title={t('common.deleteTitle', {
						entity: t('dialog-mcp-delete.skillEntity'),
						name: deleteTarget ?? '',
					})}
					description={t('dialog-mcp-delete.skillDescription')}
					onConfirm={async () => {
						if (deleteTarget) await onRemove(deleteTarget);
					}}
				/>
			</TabsContent>

			<TabsContent value="library" className="flex flex-col flex-1 min-h-0 gap-y-2 mt-0">
				<span className="text-muted-foreground text-sm">
					{t('panel.skill.library.description')}
				</span>
				<SkillLibraryTab
					agentId={agentId}
					sessionId={sessionId}
					onSkillsChanged={onSkillsChanged}
				/>
			</TabsContent>
		</Tabs>
	);
}
