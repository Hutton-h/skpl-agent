import { Outlet } from 'react-router-dom';

import { AppSidebar } from '@/components/layout/AppSidebar';
import { MobileBottomNav } from '@/components/layout/MobileBottomNav';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { useIsMobile } from '@/hooks/use-mobile';

export function AppLayout() {
  const isMobile = useIsMobile();

  return (
    <div className="h-screen flex">
      <SidebarProvider defaultOpen={!isMobile}>
        {/* Desktop sidebar — hidden on mobile */}
        {!isMobile && <AppSidebar />}
        <SidebarInset className="flex-1 overflow-hidden">
          {/* Mobile: add bottom padding for the nav bar */}
          <div className={`flex-1 min-h-0 overflow-hidden ${isMobile ? 'pb-14' : ''}`} data-test="app-layout-outlet-wrapper">
            <Outlet />
          </div>
        </SidebarInset>
      </SidebarProvider>
      {/* Mobile bottom navigation */}
      <MobileBottomNav />
    </div>
  );
}
