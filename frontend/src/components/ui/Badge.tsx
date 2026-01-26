import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';
  children: ReactNode;
}

export function Badge({ className, variant = 'default', children, ...props }: BadgeProps) {
  const variants = {
    default: 'bg-neutral-100 text-neutral-800',
    success: 'bg-success-100 text-success-700',
    warning: 'bg-warning-100 text-warning-700',
    danger: 'bg-danger-100 text-danger-700',
    info: 'bg-secondary-100 text-secondary-700',
    purple: 'bg-primary-100 text-primary-700',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

// Helper function to get badge variant based on status
export function getStatusBadgeVariant(
  status: string
): 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple' {
  const statusMap: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple'> = {
    pending: 'warning',
    processing: 'info',
    completed: 'success',
    failed: 'danger',
    active: 'success',
    blocked: 'danger',
    deactivated: 'default',
    reconciled: 'success',
    unreconciled: 'warning',
    super_admin: 'purple',
    admin: 'info',
    user: 'default',
  };
  return statusMap[status.toLowerCase()] || 'default';
}
