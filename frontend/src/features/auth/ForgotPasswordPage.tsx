import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Cog, ArrowLeft, Mail, CheckCircle } from 'lucide-react';
import { Button, Input, Alert, PasswordInput } from '@/components/ui';
import { authApi, getErrorMessage } from '@/api';

type Step = 'email' | 'reset';

const emailSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
});

const resetSchema = z
  .object({
    resetToken: z.string().min(1, 'Reset token is required'),
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });

type EmailFormData = z.infer<typeof emailSchema>;
type ResetFormData = z.infer<typeof resetSchema>;

export function ForgotPasswordPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>('email');
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Step 1: Email form
  const emailForm = useForm<EmailFormData>({
    resolver: zodResolver(emailSchema),
  });

  // Step 2: Reset password form
  const resetForm = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
  });

  // Step 1: Submit email → request reset token
  const onSubmitEmail = async (data: EmailFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await authApi.forgotPassword({ email: data.email });
      setSuccessMessage(response.message);
      setStep('reset');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Submit new password with reset token
  const onSubmitReset = async (data: ResetFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.resetPassword({
        reset_token: data.resetToken,
        new_password: data.newPassword,
      });
      navigate('/login', {
        state: { passwordReset: true },
        replace: true,
      });
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

          {error && (
            <Alert variant="error" className="mb-6">
              {error}
            </Alert>
          )}

          {/* Step 1: Enter Email */}
          {step === 'email' && (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-50 mb-4">
                  <Mail className="h-8 w-8 text-primary-600" />
                </div>
                <h1 className="text-2xl font-semibold text-neutral-800 mb-2">
                  Forgot password?
                </h1>
                <p className="text-neutral-500">
                  Enter your email and we'll send you a reset token
                </p>
              </div>

              <form onSubmit={emailForm.handleSubmit(onSubmitEmail)} className="space-y-5">
                <Input
                  label="Email"
                  type="email"
                  placeholder="Enter your email"
                  error={emailForm.formState.errors.email?.message}
                  {...emailForm.register('email')}
                />

                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Send Reset Token
                </Button>

                <div className="text-center">
                  <Link
                    to="/login"
                    className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to login
                  </Link>
                </div>
              </form>
            </>
          )}

          {/* Step 2: Enter Reset Token + New Password */}
          {step === 'reset' && (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-success-50 mb-4">
                  <CheckCircle className="h-8 w-8 text-success-600" />
                </div>
                <h1 className="text-2xl font-semibold text-neutral-800 mb-2">
                  Set new password
                </h1>
                <p className="text-neutral-500">
                  Check your email for the reset token, then enter it below with your new password
                </p>
              </div>

              {successMessage && (
                <Alert variant="info" className="mb-6">
                  {successMessage}
                </Alert>
              )}

              <form onSubmit={resetForm.handleSubmit(onSubmitReset)} className="space-y-5">
                <Input
                  label="Reset Token"
                  type="text"
                  placeholder="Paste the reset token from your email"
                  error={resetForm.formState.errors.resetToken?.message}
                  {...resetForm.register('resetToken')}
                />

                <PasswordInput
                  label="New Password"
                  placeholder="Enter new password"
                  error={resetForm.formState.errors.newPassword?.message}
                  {...resetForm.register('newPassword')}
                />

                <PasswordInput
                  label="Confirm Password"
                  placeholder="Confirm new password"
                  error={resetForm.formState.errors.confirmPassword?.message}
                  {...resetForm.register('confirmPassword')}
                />

                <Button type="submit" className="w-full" isLoading={isLoading}>
                  Reset Password
                </Button>

                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => { setStep('email'); setError(null); setSuccessMessage(null); }}
                    className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to email
                  </button>
                </div>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-sm text-neutral-400 mt-6">
          Payment Gateway Reconciliation
        </p>
      </div>
    </div>
  );
}
