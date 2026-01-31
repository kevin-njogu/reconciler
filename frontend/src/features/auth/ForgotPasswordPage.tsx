import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Cog, ArrowLeft, Mail, ShieldCheck, CheckCircle } from 'lucide-react';
import { Button, Input, Alert, PasswordInput } from '@/components/ui';
import { OTPInput } from '@/components/auth/OTPInput';
import { useCountdown } from '@/components/auth/CountdownTimer';
import { authApi, getErrorMessage } from '@/api';

type Step = 'email' | 'otp' | 'reset';

const emailSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email'),
});

const resetSchema = z
  .object({
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
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [otpValue, setOtpValue] = useState('');
  const [otpExpiresIn, setOtpExpiresIn] = useState(300);
  const [resetToken, setResetToken] = useState('');

  // OTP expiry countdown
  const { display: otpDisplay, isExpired: otpIsExpired } = useCountdown(
    step === 'otp' ? otpExpiresIn : 0
  );

  // Step 1: Email form
  const emailForm = useForm<EmailFormData>({
    resolver: zodResolver(emailSchema),
  });

  // Step 3: Reset password form
  const resetForm = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
  });

  // Step 1: Submit email → request OTP
  const onSubmitEmail = async (data: EmailFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.forgotPassword({ email: data.email });
      setEmail(data.email);
      setOtpExpiresIn(300);
      setOtpValue('');
      setStep('otp');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Submit OTP → verify reset code
  const onSubmitOTP = async () => {
    if (otpValue.length !== 6) return;
    setError(null);
    setIsLoading(true);

    try {
      const response = await authApi.verifyResetOTP({
        email,
        otp_code: otpValue,
      });
      setResetToken(response.reset_token);
      setStep('reset');
    } catch (err) {
      setError(getErrorMessage(err));
      setOtpValue('');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 3: Submit new password
  const onSubmitReset = async (data: ResetFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.resetPassword({
        reset_token: resetToken,
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

  // Resend OTP
  const handleResendOTP = async () => {
    setError(null);
    setIsLoading(true);

    try {
      await authApi.forgotPassword({ email });
      setOtpExpiresIn(300);
      setOtpValue('');
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
                  Enter your email and we'll send you a verification code
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
                  Send Reset Code
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

          {/* Step 2: Enter OTP */}
          {step === 'otp' && (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-50 mb-4">
                  <ShieldCheck className="h-8 w-8 text-primary-600" />
                </div>
                <h1 className="text-2xl font-semibold text-neutral-800 mb-2">
                  Enter verification code
                </h1>
                <p className="text-neutral-500">
                  We sent a 6-digit code to <span className="font-medium">{email}</span>
                </p>
              </div>

              <div className="space-y-6">
                <OTPInput
                  value={otpValue}
                  onChange={setOtpValue}
                  disabled={isLoading}
                  error={!!error}
                />

                {/* OTP Expiry Timer */}
                <div className="text-center">
                  {!otpIsExpired ? (
                    <p className="text-sm text-neutral-500">
                      Code expires in <span className="font-medium text-neutral-700">{otpDisplay}</span>
                    </p>
                  ) : (
                    <Alert variant="warning" className="text-sm">
                      Your code has expired. Please request a new one.
                    </Alert>
                  )}
                </div>

                <Button
                  onClick={onSubmitOTP}
                  className="w-full"
                  isLoading={isLoading}
                  disabled={otpValue.length !== 6 || otpIsExpired}
                >
                  Verify Code
                </Button>

                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    onClick={() => { setStep('email'); setError(null); }}
                    className="flex items-center gap-1 text-neutral-500 hover:text-neutral-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Change email
                  </button>

                  <button
                    type="button"
                    onClick={handleResendOTP}
                    disabled={isLoading}
                    className="text-primary-600 hover:text-primary-700 font-medium disabled:opacity-50"
                  >
                    Resend code
                  </button>
                </div>
              </div>
            </>
          )}

          {/* Step 3: New Password */}
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
                  Create a strong password for your account
                </p>
              </div>

              <form onSubmit={resetForm.handleSubmit(onSubmitReset)} className="space-y-5">
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
