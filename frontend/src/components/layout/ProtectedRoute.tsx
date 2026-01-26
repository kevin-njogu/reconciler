import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore, useIsAdmin, useIsSuperAdmin, useIsAdminOnly, useIsUserRole } from '@/stores';
import { PageLoading } from '@/components/ui';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;       // Admin or super_admin
  requireSuperAdmin?: boolean;  // Only super_admin
  requireAdminOnly?: boolean;   // Only admin (not super_admin)
  requireUserRole?: boolean;    // Only user role (inputters)
}

export function ProtectedRoute({
  children,
  requireAdmin = false,
  requireSuperAdmin = false,
  requireAdminOnly = false,
  requireUserRole = false,
}: ProtectedRouteProps) {
  const location = useLocation();
  const { isAuthenticated, isLoading, mustChangePassword } = useAuthStore();
  const isAdmin = useIsAdmin();
  const isSuperAdmin = useIsSuperAdmin();
  const isAdminOnly = useIsAdminOnly();
  const isUserRole = useIsUserRole();

  if (isLoading) {
    return <PageLoading />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Redirect to change password if required (except when already on change-password page)
  if (mustChangePassword && location.pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />;
  }

  if (requireSuperAdmin && !isSuperAdmin) {
    return <Navigate to="/" replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/" replace />;
  }

  if (requireAdminOnly && !isAdminOnly) {
    return <Navigate to="/" replace />;
  }

  if (requireUserRole && !isUserRole) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
