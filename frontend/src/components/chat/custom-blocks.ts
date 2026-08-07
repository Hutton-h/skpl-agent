/**
 * Custom (non-SDK) content blocks injected into the message stream from
 * ``CustomEvent`` SSE frames (``name="visual"`` / ``name="plan"``).
 *
 * They are appended to ``Msg.content`` with a cast in ``useMessages`` —
 * the SDK's ``appendEvent`` only knows agent-produced blocks, so these
 * are pushed directly and rendered by ``MessageBubble``'s ``renderBlock``
 * via its ``ExtendedContentBlock`` union.
 */

/** Visual payload kinds emitted by the backend ``publish_visual`` tool. */
export type VisualType =
	| 'chart'
	| 'table'
	| 'comparison'
	| 'dashboard'
	| 'timeline'
	| 'action';

/** Shape of a ``CustomEvent(name="visual")`` value. */
export interface VisualEventValue {
	title?: string;
	visual_type?: string;
	html?: string;
	summary?: string;
	/** Optional structured JSON data for dedicated frontend components. */
	data?: Record<string, unknown> | null;
}

/** Shape of a ``CustomEvent(name="plan")`` value. */
export interface PlanEventValue {
	reply_id?: string;
	steps?: unknown;
	raw_plan?: string;
	needs_confirmation?: boolean;
}

/** A visual render block appended to the message stream. */
export interface VisualBlock {
	type: 'visual';
	id: string;
	title: string;
	visualType: VisualType | (string & {});
	html: string;
	summary?: string;
	/** Optional structured JSON data for dedicated frontend components. */
	data?: Record<string, unknown> | null;
}

/** A plan render block appended to the message stream. */
export interface PlanBlock {
	type: 'plan';
	id: string;
	/** Backend reply id this plan belongs to (dedup / update key). */
	replyId: string;
	steps: string[];
	needsConfirmation: boolean;
}
