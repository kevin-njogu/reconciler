import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Key } from 'lucide-react';
import { useAuthStore } from '@/stores';
import { authApi, getErrorMessage } from '@/api';
import { Button, Alert, Card, CardHeader, CardTitle, CardDescription, CardContent, PasswordInput } from '@/components/ui';
import { useToast } from '@/hooks/useToast';

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, 'Current password is required'),
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { mustChangePassword, setMustChangePassword, logout } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  const onSubmit = async (data: PasswordFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.changePassword({
        current_password: data.currentPassword,
        new_password: data.newPassword,
      });

      setMustChangePassword(false);
      toast.success('Password changed successfully. Please login again.');
      await logout();
      navigate('/login');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Key className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <CardTitle>Change Password</CardTitle>
              <CardDescription>
                {mustChangePassword
                  ? 'You must change your password before continuing'
                  : 'Update your account password'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="error" className="mb-6">
              {error}
            </Alert>
          )}

          {mustChangePassword && (
            <Alert variant="warning" className="mb-6">
              Your password must be changed before you can access the system.
            </Alert>
          )}

          <Alert variant="info" className="mb-6">
            Your new password must be at least 8 characters and cannot be the same as any of your last 5 passwords.
          </Alert>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <PasswordInput
              label="Current Password"
              placeholder="Enter current password"
              error={errors.currentPassword?.message}
              {...register('currentPassword')}
            />

            <PasswordInput
              label="New Password"
              placeholder="Enter new password"
              error={errors.newPassword?.message}
              {...register('newPassword')}
            />

            <PasswordInput
              label="Confirm New Password"
              placeholder="Confirm new password"
              error={errors.confirmPassword?.message}
              {...register('confirmPassword')}
            />

            <div className="flex gap-3 pt-2">
              {!mustChangePassword && (
                <Button type="button" variant="outline" onClick={() => navigate(-1)} className="flex-1">
                  Cancel
                </Button>
              )}
              <Button type="submit" isLoading={isLoading} className="flex-1">
                Change Password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
