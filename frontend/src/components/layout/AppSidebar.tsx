import {
	BotMessageSquare,
	Store,
	Bug,
	Calendars,
	Code,
	Globe,
	KeyRound,
	Languages,
	LayoutDashboard,
	LibraryBig,
	MessageCircle,
	Monitor,
	ScanEye,
	Search,
	Settings,
	Shield,
} from 'lucide-react';
import { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

import SkplLogo from '@/assets/images/skpl-logo.svg?react';
import {
	Sidebar,
	SidebarContent,
	SidebarFooter,
	SidebarGroup,
	SidebarGroupContent,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuButton,
	SidebarMenuItem,
} from '@/components/ui/sidebar';
import i18n from '@/i18n';
import { useTranslation } from '@/i18n/useI18n';

export function AppSidebar() {
	const navigate = useNavigate();
	const location = useLocation();
	const { t } = useTranslation();

	const isAdmin = useMemo(() => {
		return localStorage.getItem('user_role') === 'admin';
	}, []);

	const handleToggleLanguage = () => {
		const next = i18n.language.startsWith('zh') ? 'en' : 'zh';
		i18n.changeLanguage(next);
	};

	return (
		<Sidebar collapsible="none" className="w-[calc(var(--sidebar-width-icon)+1px)]! border-r">
			<SidebarHeader>
				<div className="flex items-center justify-center h-12 mt-2">
					<SkplLogo className="size-8 items-center justify-center rounded-lg" />
				</div>
			</SidebarHeader>
			<SidebarContent>
				<SidebarGroup>
					<SidebarGroupContent>
						<SidebarMenu>
							<SidebarMenuItem key={'dashboard'}>
								<SidebarMenuButton
									tooltip={{ children: t('common.dashboard'), hidden: false }}
									isActive={location.pathname === '/dashboard'}
									onClick={() => navigate('/dashboard')}
									className="px-2.5 md:px-2"
								>
									<LayoutDashboard />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem key={'chat'}>
								<SidebarMenuButton
									tooltip={{ children: t('common.chat'), hidden: false }}
									isActive={
										location.pathname === '/chat' ||
										location.pathname.startsWith('/chat/')
									}
									onClick={() => navigate('/chat')}
									className="px-2.5 md:px-2"
								>
									<BotMessageSquare />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.context'), hidden: false }}
									isActive={location.pathname === '/context'}
									onClick={() => navigate('/context')}
									className="px-2"
								>
									<ScanEye />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.schedule'), hidden: false }}
									isActive={location.pathname === '/schedule'}
									onClick={() => navigate('/schedule')}
									className="px-2"
								>
									<Calendars />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.buglog'), hidden: false }}
									isActive={location.pathname === '/buglog'}
									onClick={() => navigate('/buglog')}
									className="px-2"
								>
									<Bug />
								</SidebarMenuButton>
							</SidebarMenuItem>
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>
				<SidebarGroup>
					<SidebarGroupContent>
						<SidebarMenu>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.firecrawl'), hidden: false }}
									isActive={location.pathname === '/firecrawl'}
									onClick={() => navigate('/firecrawl')}
									className="px-2"
								>
									<Globe />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.desktop'), hidden: false }}
									isActive={location.pathname === '/desktop'}
									onClick={() => navigate('/desktop')}
									className="px-2"
								>
									<Monitor />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.whatsapp'), hidden: false }}
									isActive={location.pathname === '/whatsapp'}
									onClick={() => navigate('/whatsapp')}
									className="px-2"
								>
									<MessageCircle />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.webIntelligence'), hidden: false }}
									isActive={location.pathname === '/web-intelligence'}
									onClick={() => navigate('/web-intelligence')}
									className="px-2"
								>
									<Search />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.codeGen'), hidden: false }}
									isActive={location.pathname === '/code-generation'}
									onClick={() => navigate('/code-generation')}
									className="px-2"
								>
									<Code />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.credential'), hidden: false }}
									isActive={location.pathname === '/credential'}
									onClick={() => navigate('/credential')}
									className="px-2"
								>
									<KeyRound />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('common.knowledge'), hidden: false }}
									isActive={location.pathname === '/knowledge'}
									onClick={() => navigate('/knowledge')}
									className="px-2"
								>
									<LibraryBig />
								</SidebarMenuButton>
							</SidebarMenuItem>
							<SidebarMenuItem>
								<SidebarMenuButton
									tooltip={{ children: t('nav.agentMarket'), hidden: false }}
									isActive={location.pathname === '/agent-market'}
									onClick={() => navigate('/agent-market')}
									className="px-2"
								>
									<Store />
								</SidebarMenuButton>
							</SidebarMenuItem>
							{isAdmin && (
								<SidebarMenuItem>
									<SidebarMenuButton
										tooltip={{ children: t('nav.admin'), hidden: false }}
										isActive={location.pathname === '/admin'}
										onClick={() => navigate('/admin')}
										className="px-2"
									>
										<Shield />
									</SidebarMenuButton>
								</SidebarMenuItem>
							)}
						</SidebarMenu>
					</SidebarGroupContent>
				</SidebarGroup>
			</SidebarContent>
			<SidebarFooter>
				<SidebarMenu>
					<SidebarMenuItem>
						<SidebarMenuButton
							tooltip={{
								children: i18n.language.startsWith('zh')
									? t('common.switchToEn')
									: t('common.switchToZh'),
								hidden: false,
							}}
							onClick={handleToggleLanguage}
							className="px-2"
						>
							<Languages />
						</SidebarMenuButton>
					</SidebarMenuItem>
					<SidebarMenuItem>
						<SidebarMenuButton
							tooltip={{ children: t('common.settings'), hidden: false }}
							isActive={location.pathname === '/settings'}
							onClick={() => navigate('/settings')}
							className="px-2"
						>
							<Settings />
						</SidebarMenuButton>
					</SidebarMenuItem>
				</SidebarMenu>
			</SidebarFooter>
		</Sidebar>
	);
}
