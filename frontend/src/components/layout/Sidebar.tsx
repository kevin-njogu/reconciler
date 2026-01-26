import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  FolderOpen,
  Upload,
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
}

const navigation: NavItem[] = [
  // User (inputter) menus - available to all roles except where specified
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Batches', href: '/batches', icon: FolderOpen },
  { name: 'Upload Files', href: '/upload', icon: Upload, userOnly: true },
  { name: 'Reconciliation', href: '/reconciliation', icon: GitCompare, userOnly: true },
  { name: 'Manual Recon', href: '/operations', icon: Wrench, userOnly: true },
  { name: 'Reports', href: '/reports', icon: FileText },
  { name: 'Transactions', href: '/transactions', icon: List },
  // Gateway management - users can request changes
  { name: 'Gateways', href: '/gateways', icon: Settings, userOnly: true },
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
    return true;
  });

  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-64 bg-primary-900">
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-center border-b border-primary-800">
          <div className="flex items-center gap-2">
            <Cog className="h-8 w-8 text-accent-300" />
            <span className="text-xl font-bold text-white">ReconPay</span>
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
                    ? 'bg-primary-500 text-white'
                    : 'text-primary-100 hover:bg-primary-800 hover:text-white'
                )
              }
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-primary-800 p-4">
          <p className="text-xs text-primary-400 text-center">
            Payment Gateway Reconciliation
          </p>
        </div>
      </div>
    </aside>
  );
}
