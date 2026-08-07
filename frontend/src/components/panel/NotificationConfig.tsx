import {
	AlertCircle,
	Bell,
	Check,
	Loader2,
	Mail,
	MessageSquare,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Item, ItemContent, ItemDescription, ItemTitle } from '@/components/ui/item';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useTranslation } from '@/i18n/useI18n';

/** Notification channel configuration. */
interface NotificationChannel {
	/** Channel type. */
	type: 'email' | 'whatsapp' | 'in_app';
	/** Whether the channel is enabled. */
	enabled: boolean;
	/** Target address (email, phone number, etc.). */
	target: string;
	/** Whether the channel is verified. */
	verified: boolean;
}

/** Notification event type configuration. */
interface NotificationEvent {
	/** Event key (e.g., 'task_completed', 'agent_error'). */
	key: string;
	/** Human-readable label. */
	label: string;
	/** Whether this event is enabled. */
	enabled: boolean;
	/** Which channels to use for this event. */
	channels: string[];
}

interface NotificationConfigProps {
	/** Current channel configurations. */
	channels?: NotificationChannel[];
	/** Current event subscriptions. */
	events?: NotificationEvent[];
	/** Whether config is loading. */
	loading?: boolean;
	/** Called when a channel is toggled. */
	onChannelToggle?: (type: string, enabled: boolean) => Promise<void>;
	/** Called when a channel target is updated. */
	onChannelUpdate?: (type: string, target: string) => Promise<void>;
	/** Called when an event is toggled. */
	onEventToggle?: (key: string, enabled: boolean) => Promise<void>;
	/** Called when event channels are updated. */
	onEventChannels?: (key: string, channels: string[]) => Promise<void>;
}

const CHANNEL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
	email: Mail,
	whatsapp: MessageSquare,
	in_app: Bell,
};

const DEFAULT_CHANNELS: NotificationChannel[] = [
	{ type: 'in_app', enabled: true, target: '', verified: true },
	{ type: 'email', enabled: false, target: '', verified: false },
	{ type: 'whatsapp', enabled: false, target: '', verified: false },
];

const DEFAULT_EVENTS: NotificationEvent[] = [
	{ key: 'task_completed', label: 'Task Completed', enabled: true, channels: ['in_app'] },
	{ key: 'task_failed', label: 'Task Failed', enabled: true, channels: ['in_app', 'email'] },
	{ key: 'agent_error', label: 'Agent Error', enabled: true, channels: ['in_app', 'email'] },
	{ key: 'schedule_reminder', label: 'Schedule Reminder', enabled: false, channels: ['in_app'] },
	{ key: 'quota_warning', label: 'Quota Warning', enabled: true, channels: ['in_app', 'email'] },
	{ key: 'system_update', label: 'System Update', enabled: false, channels: ['in_app'] },
];

/**
 * Notification configuration panel.
 *
 * Allows users to configure which notification channels (email,
 * WhatsApp, in-app) are enabled, set target addresses, and choose
 * which events trigger notifications on which channels.
 */
export function NotificationConfig({
	channels: propChannels,
	events: propEvents,
	loading = false,
	onChannelToggle,
	onChannelUpdate,
	onEventToggle,
	onEventChannels,
}: NotificationConfigProps) {
	const { t } = useTranslation();
	const [channels, setChannels] = useState<NotificationChannel[]>(
		propChannels ?? DEFAULT_CHANNELS,
	);
	const [events, setEvents] = useState<NotificationEvent[]>(
		propEvents ?? DEFAULT_EVENTS,
	);
	const [saving, setSaving] = useState<Record<string, boolean>>({});

	useEffect(() => {
		if (propChannels) setChannels(propChannels);
	}, [propChannels]);

	useEffect(() => {
		if (propEvents) setEvents(propEvents);
	}, [propEvents]);

	const handleChannelToggle = useCallback(
		async (type: string, enabled: boolean) => {
			setSaving((prev) => ({ ...prev, [`ch_${type}`]: true }));
			setChannels((prev) =>
				prev.map((c) => (c.type === type ? { ...c, enabled } : c)),
			);
			try {
				await onChannelToggle?.(type, enabled);
			} finally {
				setSaving((prev) => ({ ...prev, [`ch_${type}`]: false }));
			}
		},
		[onChannelToggle],
	);

	const handleEventToggle = useCallback(
		async (key: string, enabled: boolean) => {
			setSaving((prev) => ({ ...prev, [`ev_${key}`]: true }));
			setEvents((prev) =>
				prev.map((e) => (e.key === key ? { ...e, enabled } : e)),
			);
			try {
				await onEventToggle?.(key, enabled);
			} finally {
				setSaving((prev) => ({ ...prev, [`ev_${key}`]: false }));
			}
		},
		[onEventToggle],
	);

	if (loading) {
		return (
			<div className="flex flex-1 items-center justify-center">
				<Loader2 className="animate-spin text-muted-foreground" />
			</div>
		);
	}

	return (
		<Tabs defaultValue="channels" className="flex flex-col flex-1 min-h-0 gap-y-3">
			<TabsList className="w-full shrink-0">
				<TabsTrigger value="channels">
					<Bell className="size-3.5" />
					{t('panel.notification.tabChannels')}
				</TabsTrigger>
				<TabsTrigger value="events">
					<AlertCircle className="size-3.5" />
					{t('panel.notification.tabEvents')}
				</TabsTrigger>
			</TabsList>

			{/* Channels tab */}
			<TabsContent value="channels" className="flex flex-col flex-1 min-h-0 gap-y-3 mt-0">
				<span className="text-muted-foreground text-sm">
					{t('panel.notification.channelDescription')}
				</span>
				<div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-y-2">
					{channels.map((channel) => {
						const Icon = CHANNEL_ICONS[channel.type] ?? Bell;
						const isPending = saving[`ch_${channel.type}`];
						return (
							<Item key={channel.type} variant="outline" className="flex-col items-stretch gap-y-2">
								<div className="flex items-center gap-x-2">
									<Icon className="size-4 shrink-0 text-muted-foreground" />
									<ItemContent>
										<ItemTitle>
											{t(`panel.notification.channel.${channel.type}`, {
												defaultValue: channel.type,
											})}
										</ItemTitle>
										<ItemDescription>
											{channel.verified
												? t('panel.notification.verified')
												: t('panel.notification.unverified')}
										</ItemDescription>
									</ItemContent>
									<div className="flex items-center gap-x-2">
										{isPending ? (
											<Loader2 className="size-4 animate-spin text-muted-foreground" />
										) : null}
										<Switch
											checked={channel.enabled}
											disabled={isPending}
											onCheckedChange={(v) => handleChannelToggle(channel.type, v)}
										/>
									</div>
								</div>
								{channel.type !== 'in_app' && channel.enabled ? (
									<div className="flex items-center gap-x-2">
										<Label className="text-xs shrink-0">
											{t('panel.notification.target')}
										</Label>
										<Input
											value={channel.target}
											onChange={(e) => {
												setChannels((prev) =>
													prev.map((c) =>
														c.type === channel.type
															? { ...c, target: e.target.value }
															: c,
													),
												);
											}}
											className="h-8 text-xs"
											placeholder={
												channel.type === 'email'
													? 'user@example.com'
													: '+8613800138000'
											}
										/>
										<Button
											variant="outline"
											size="sm"
											className="text-xs"
											onClick={() => onChannelUpdate?.(channel.type, channel.target)}
										>
											<Check className="size-3" />
											{t('common.save')}
										</Button>
									</div>
								) : null}
							</Item>
						);
					})}
				</div>
			</TabsContent>

			{/* Events tab */}
			<TabsContent value="events" className="flex flex-col flex-1 min-h-0 gap-y-3 mt-0">
				<span className="text-muted-foreground text-sm">
					{t('panel.notification.eventDescription')}
				</span>
				<div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-y-2">
					{events.map((event) => {
						const isPending = saving[`ev_${event.key}`];
						return (
							<Item key={event.key} variant="outline" className="flex-col items-stretch gap-y-2">
								<div className="flex items-center gap-x-2">
									<ItemContent>
										<ItemTitle>
											{t(`panel.notification.event.${event.key}`, {
												defaultValue: event.label,
											})}
										</ItemTitle>
									</ItemContent>
									<div className="flex items-center gap-x-2">
										{isPending ? (
											<Loader2 className="size-4 animate-spin text-muted-foreground" />
										) : null}
										<Switch
											checked={event.enabled}
											disabled={isPending}
											onCheckedChange={(v) => handleEventToggle(event.key, v)}
										/>
									</div>
								</div>
								{event.enabled ? (
									<div className="flex flex-wrap gap-1.5">
										{channels
											.filter((c) => c.enabled)
											.map((c) => {
												const active = event.channels.includes(c.type);
												return (
													<Badge
														key={c.type}
														variant={active ? 'default' : 'outline'}
														className="cursor-pointer text-xs"
														onClick={() => {
															const next = active
																? event.channels.filter((x) => x !== c.type)
																: [...event.channels, c.type];
															setEvents((prev) =>
																prev.map((e) =>
																	e.key === event.key
																		? { ...e, channels: next }
																		: e,
																),
															);
															onEventChannels?.(event.key, next);
														}}
													>
														{t(`panel.notification.channel.${c.type}`, {
															defaultValue: c.type,
														})}
													</Badge>
												);
											})}
									</div>
								) : null}
							</Item>
						);
					})}
				</div>
			</TabsContent>
		</Tabs>
	);
}
