import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  GitCompare,
  FileText,
  Settings,
  Cog,
  Wrench,
  ShieldCheck,
  CheckSquare,
  List,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useIsAdmin, useIsSuperAdmin, useIsAdminOnly, useIsUserRole } from '@/stores';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;       // Available to admin and super_admin
  superAdminOnly?: boolean;  // Only for super_admin
  userOnly?: boolean;        // Only for user role (inputters)
  adminOnlyStrict?: boolean; // Only for admin (not super_admin)
  excludeSuperAdmin?: boolean; // Hide from super_admin (operational items)
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Reconcile', href: '/reconcile', icon: GitCompare, userOnly: true },
  { name: 'Manual Recon', href: '/operations', icon: Wrench, userOnly: true },
  { name: 'Gateways', href: '/gateways', icon: Settings, userOnly: true },
  { name: 'Transactions', href: '/transactions', icon: List },
  { name: 'Reports', href: '/reports', icon: FileText },
  // Admin (approver) menus - only for admin role (not super_admin)
  { name: 'Reconciliation Approvals', href: '/reconciliation-approvals', icon: ShieldCheck, adminOnlyStrict: true },
  { name: 'Gateway Approvals', href: '/gateway-approvals', icon: CheckSquare, adminOnlyStrict: true },
  // Super Admin only menus
  { name: 'Users', href: '/users', icon: Users, superAdminOnly: true },
];

export function Sidebar() {
  const isAdmin = useIsAdmin();
  const isSuperAdmin = useIsSuperAdmin();
  const isAdminOnly = useIsAdminOnly();
  const isUserRole = useIsUserRole();

  const filteredNavigation = navigation.filter((item) => {
    if (item.superAdminOnly && !isSuperAdmin) return false;
    if (item.adminOnly && !isAdmin) return false;
    if (item.adminOnlyStrict && !isAdminOnly) return false;
    if (item.userOnly && !isUserRole) return false;
    if (item.excludeSuperAdmin && isSuperAdmin) return false;
    return true;
  });

  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-64 bg-neutral-100 border-r border-neutral-200">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-center border-b border-neutral-200">
          <div className="flex items-center gap-2">
            <Cog className="h-8 w-8 text-accent-300" />
            <span className="text-xl font-bold" style={{ color: '#205926' }}>Reconciler</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {filteredNavigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-100 text-primary-600'
                    : 'text-neutral-700 hover:bg-neutral-200 hover:text-primary-600'
                )
              }
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-neutral-200 p-4">
          <p className="text-xs text-neutral-400 text-center">
            Payment Gateway Reconciliation
          </p>
        </div>
      </div>
    </aside>
  );
}
