import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/stores';
import { Layout, ProtectedRoute } from '@/components/layout';
import { ToastContainer } from '@/components/ui/Toast';
import { PageLoading } from '@/components/ui';

// Feature pages
import { LoginPage, ChangePasswordPage } from '@/features/auth';
import { DashboardPage } from '@/features/dashboard';
import { UsersPage } from '@/features/users';
import { BatchesPage, BatchDetailPage } from '@/features/batches';
import { UploadPage } from '@/features/upload';
import { ReconciliationPage } from '@/features/reconciliation';
import { ReportsPage } from '@/features/reports';
import { GatewaysPage, GatewayApprovalPage } from '@/features/gateways';
import { OperationsPage, AuthorizationPage } from '@/features/operations';
import { TransactionsPage } from '@/features/transactions';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppRoutes() {
  const { isLoading, checkAuth, isAuthenticated } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <PageLoading />
      </div>
    );
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />

      {/* Protected routes with layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="/batches" element={<BatchesPage />} />
        <Route path="/batches/:batchId" element={<BatchDetailPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/reconciliation" element={<ReconciliationPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        {/* User role routes - manual reconciliation operations */}
        <Route
          path="/operations"
          element={
            <ProtectedRoute requireUserRole>
              <OperationsPage />
            </ProtectedRoute>
          }
        />

        {/* User role routes - gateway management (submit change requests) */}
        <Route
          path="/gateways"
          element={
            <ProtectedRoute requireUserRole>
              <GatewaysPage />
            </ProtectedRoute>
          }
        />

        {/* Admin (strict) routes - approval workflows */}
        <Route
          path="/reconciliation-approvals"
          element={
            <ProtectedRoute requireAdminOnly>
              <AuthorizationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/gateway-approvals"
          element={
            <ProtectedRoute requireAdminOnly>
              <GatewayApprovalPage />
            </ProtectedRoute>
          }
        />

        {/* Super Admin routes */}
        <Route
          path="/users"
          element={
            <ProtectedRoute requireSuperAdmin>
              <UsersPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
        <ToastContainer />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
