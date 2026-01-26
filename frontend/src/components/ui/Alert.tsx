import type { HTMLAttributes, ReactNode } from 'react';
import { AlertCircle, CheckCircle, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  children: ReactNode;
}

export function Alert({ className, variant = 'info', title, children, ...props }: AlertProps) {
  const variants = {
    info: {
      container: 'bg-secondary-50 border-secondary-200',
      icon: <Info className="h-5 w-5 text-secondary-400" />,
      title: 'text-secondary-800',
      content: 'text-secondary-700',
    },
    success: {
      container: 'bg-success-50 border-success-200',
      icon: <CheckCircle className="h-5 w-5 text-success-500" />,
      title: 'text-success-700',
      content: 'text-success-600',
    },
    warning: {
      container: 'bg-warning-50 border-warning-200',
      icon: <AlertCircle className="h-5 w-5 text-warning-400" />,
      title: 'text-warning-700',
      content: 'text-warning-600',
    },
    error: {
      container: 'bg-danger-50 border-danger-200',
      icon: <XCircle className="h-5 w-5 text-danger-400" />,
      title: 'text-danger-800',
      content: 'text-danger-700',
    },
  };

  const styles = variants[variant];

  return (
    <div
      className={cn('rounded-lg border p-4', styles.container, className)}
      role="alert"
      {...props}
    >
      <div className="flex">
        <div className="flex-shrink-0">{styles.icon}</div>
        <div className="ml-3">
          {title && <h3 className={cn('text-sm font-medium', styles.title)}>{title}</h3>}
          <div className={cn('text-sm', title && 'mt-2', styles.content)}>{children}</div>
        </div>
      </div>
    </div>
  );
}
