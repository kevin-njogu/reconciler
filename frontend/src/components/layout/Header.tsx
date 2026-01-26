import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, User, ChevronDown, Key } from 'lucide-react';
import { useAuthStore, useUser } from '@/stores';
import { Badge, getStatusBadgeVariant } from '@/components/ui';
import { cn } from '@/lib/utils';

export function Header() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const user = useUser();
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleChangePassword = () => {
    setIsDropdownOpen(false);
    navigate('/change-password');
  };

  return (
    <header className="sticky top-0 z-30 h-16 bg-white border-b border-neutral-200">
      <div className="flex h-full items-center justify-between px-6">
        <div>
          <h1 className="text-lg font-semibold text-neutral-900">
            Payment Gateway Reconciliation System
          </h1>
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-neutral-100 transition-colors"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-500 text-white">
              <User className="h-4 w-4" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-neutral-900">{user?.username}</p>
              <Badge variant={getStatusBadgeVariant(user?.role || 'user')} className="text-xs">
                {user?.role?.replace('_', ' ')}
              </Badge>
            </div>
            <ChevronDown
              className={cn(
                'h-4 w-4 text-neutral-500 transition-transform',
                isDropdownOpen && 'rotate-180'
              )}
            />
          </button>

          {isDropdownOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setIsDropdownOpen(false)}
              />
              <div className="absolute right-0 z-20 mt-2 w-56 rounded-lg bg-white py-2 shadow-lg ring-1 ring-black/5">
                <div className="px-4 py-2 border-b border-neutral-100">
                  <p className="text-sm font-medium text-neutral-900">{user?.username}</p>
                  <p className="text-xs text-neutral-500">{user?.email}</p>
                </div>
                <button
                  onClick={handleChangePassword}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-neutral-700 hover:bg-neutral-100"
                >
                  <Key className="h-4 w-4" />
                  Change Password
                </button>
                <button
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-4 py-2 text-sm text-danger-600 hover:bg-danger-50"
                >
                  <LogOut className="h-4 w-4" />
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
