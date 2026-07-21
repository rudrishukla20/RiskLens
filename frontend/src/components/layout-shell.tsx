import React, { useState, useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/auth-context';
import { LogOut, Shield, Menu, X, BarChart3, ChevronDown } from 'lucide-react';

export interface NavItem {
  label: string;
  to?: string;
  icon: React.ComponentType<{ className?: string }>;
  children?: {
    label: string;
    to: string;
  }[];
}

interface LayoutShellProps {
  navItems: NavItem[];
}

export const LayoutShell = ({ navItems }: LayoutShellProps) => {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // Find if any group contains a child with the current pathname
    const autoExpand: Record<string, boolean> = {};
    navItems.forEach((item) => {
      if (item.children) {
        const hasActiveChild = item.children.some((child) => child.to === pathname);
        if (hasActiveChild) {
          autoExpand[item.label] = true;
        }
      }
    });
    if (Object.keys(autoExpand).length > 0) {
      setExpandedGroups((prev) => ({ ...prev, ...autoExpand }));
    }
  }, [pathname, navItems]);

  useEffect(() => {
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      const currentTheme = localStorage.getItem('theme') || 'light';
      if (currentTheme === 'system') {
        const root = window.document.documentElement;
        if (e.matches) {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      }
    };

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', handleSystemThemeChange);

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'theme') {
        const newTheme = (e.newValue as 'light' | 'dark' | 'system') || 'light';
        const root = window.document.documentElement;
        let activeTheme = newTheme;
        if (newTheme === 'system') {
          activeTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        if (activeTheme === 'dark') {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // Initial theme apply
    const savedTheme = (localStorage.getItem('theme') as 'light' | 'dark' | 'system') || 'light';
    const root = window.document.documentElement;
    let activeTheme = savedTheme;
    if (savedTheme === 'system') {
      activeTheme = mediaQuery.matches ? 'dark' : 'light';
    }
    if (activeTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar - Mobile drawer backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-card transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand header */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-border">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-primary dark:text-primary">
            <BarChart3 className="h-6 w-6 text-primary dark:text-primary" />
            <span>RiskLens</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="rounded p-1 text-muted-foreground hover:bg-muted lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 space-y-1 px-4 py-6 overflow-y-auto" aria-label="Main Navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            
            // Render direct link
            if (!item.children || item.children.length === 0) {
              return (
                <NavLink
                  key={item.to}
                  to={item.to!}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`
                  }
                  onClick={() => setSidebarOpen(false)}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            }

            // Render collapsible group
            const isExpanded = !!expandedGroups[item.label];
            const isGroupActive = item.children.some((child) => child.to === pathname);
            
            const toggleGroup = () => {
              setExpandedGroups((prev) => ({
                ...prev,
                [item.label]: !prev[item.label],
              }));
            };

            return (
              <div key={item.label} className="space-y-0.5">
                <button
                  onClick={toggleGroup}
                  className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors focus:outline-none ${
                    isGroupActive
                      ? 'bg-muted text-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  }`}
                  aria-expanded={isExpanded}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </div>
                  <ChevronDown className={`h-4 w-4 shrink-0 transition-transform duration-200 ${isExpanded ? '' : '-rotate-90'}`} />
                </button>
                <div
                  role="group"
                  className="overflow-hidden transition-all duration-200 ease-in-out"
                  style={{
                    maxHeight: isExpanded ? `${item.children.length * 36}px` : '0px',
                    opacity: isExpanded ? 1 : 0,
                  }}
                >
                  <div className="space-y-0.5 py-0.5 pl-6">
                    {item.children.map((child) => (
                      <NavLink
                        key={child.to}
                        to={child.to}
                        className={({ isActive }) =>
                          `flex items-center gap-3 rounded-md py-1.5 text-sm font-medium transition-colors pl-8 ${
                            isActive
                              ? 'bg-primary text-primary-foreground'
                              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                          }`
                        }
                        onClick={() => setSidebarOpen(false)}
                      >
                        <span>{child.label}</span>
                      </NavLink>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </nav>

        {/* User Info footer in Sidebar */}
        <div className="border-t border-border p-4 bg-muted/40">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary font-bold uppercase">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user?.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header bar */}
        <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="rounded p-1 text-muted-foreground hover:bg-muted lg:hidden"
              aria-label="Open sidebar"
            >
              <Menu className="h-6 w-6" />
            </button>
            <h1 className="hidden text-base font-semibold sm:block">RiskLens Analytics</h1>
          </div>

          <div className="flex items-center gap-2">
            {/* Role Badge */}
            {user?.role && (
              <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-2 py-1 text-xs font-semibold text-primary dark:text-primary border border-primary/20">
                <Shield className="h-3 w-3" />
                {user.role.replace(/_/g, ' ')}
              </span>
            )}



            {/* Logout */}
            <button
              onClick={logout}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm font-medium text-destructive hover:bg-destructive hover:text-destructive-foreground transition-colors"
              aria-label="Logout"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Main Workspace content viewport */}
        <main className="flex-1 overflow-y-auto bg-background p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
