import { useState } from 'react';
import { useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Cog } from 'lucide-react';
import { useAuthStore } from '@/stores';
import { Button, Input, Alert, PasswordInput } from '@/components/ui';
import { getErrorMessage } from '@/api';

const loginSchema = z.object({
  username: z.string().min(1, 'Email is required').email('Please enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const sessionExpired = searchParams.get('session_expired') === 'true';

  const { login } = useAuthStore();

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const from = location.state?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmitCredentials = async (data: LoginFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await login(data.username, data.password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-100 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          {/* Logo */}
          <div className="flex items-center justify-center gap-2 mb-8">
            <Cog className="h-10 w-10 text-accent-300" />
            <span className="text-2xl font-bold" style={{ color: '#205926' }}>Reconciler</span>
          </div>

          {sessionExpired && (
            <Alert variant="info" className="mb-6">
              Your session has expired. Please sign in again.
            </Alert>
          )}

          {error && (
            <Alert variant="error" className="mb-6">
              {error}
            </Alert>
          )}

          <h1 className="text-2xl font-semibold text-center text-neutral-800 mb-2">
            Welcome back
          </h1>
          <p className="text-center text-neutral-500 mb-8">
            Sign in to your account to continue
          </p>

          <form onSubmit={handleSubmit(onSubmitCredentials)} className="space-y-5">
            <Input
              label="Email"
              type="email"
              placeholder="Enter your email"
              error={errors.username?.message}
              {...register('username')}
            />

            <PasswordInput
              label="Password"
              placeholder="Enter your password"
              error={errors.password?.message}
              {...register('password')}
            />

            <div className="flex justify-end">
              <Link
                to="/forgot-password"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Forgot password?
              </Link>
            </div>

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-neutral-400 mt-6">
          Payment Gateway Reconciliation
        </p>
      </div>
    </div>
  );
}
