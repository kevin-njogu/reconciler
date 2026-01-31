import { useState, useCallback } from 'react';
import { useNavigate, useLocation, useSearchParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Cog, ArrowLeft, Mail, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/stores';
import { Button, Input, Alert, PasswordInput } from '@/components/ui';
import { OTPInput } from '@/components/auth/OTPInput';
import { useCountdown } from '@/components/auth/CountdownTimer';
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

  const {
    loginStep,
    login,
    verifyOTP,
    resendOTP,
    cancelLogin,
    otpExpiresIn,
    otpSource,
    resendAvailableIn,
    loginEmail,
  } = useAuthStore();

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [otpValue, setOtpValue] = useState('');
  const [otpExpired, setOtpExpired] = useState(false);

  const from = location.state?.from?.pathname || '/';

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // OTP expiry countdown
  const handleOtpExpired = useCallback(() => {
    setOtpExpired(true);
  }, []);

  const { display: otpDisplay, isExpired: otpIsExpired } = useCountdown(
    otpExpiresIn,
    handleOtpExpired
  );

  // Resend cooldown countdown
  const { display: resendDisplay, isExpired: resendReady } = useCountdown(resendAvailableIn);

  // Step 1: Credentials submission
  const onSubmitCredentials = async (data: LoginFormData) => {
    setError(null);
    setIsLoading(true);

    try {
      await login(data.username, data.password);
      setOtpExpired(false);
      setOtpValue('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: OTP verification
  const onSubmitOTP = async () => {
    if (otpValue.length !== 6) return;
    setError(null);
    setIsLoading(true);

    try {
      await verifyOTP(otpValue);
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
      setOtpValue('');
    } finally {
      setIsLoading(false);
    }
  };

  // Resend OTP
  const handleResend = async () => {
    setError(null);
    try {
      await resendOTP();
      setOtpExpired(false);
      setOtpValue('');
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  // Back to credentials
  const handleBack = () => {
    cancelLogin();
    setError(null);
    setOtpValue('');
    setOtpExpired(false);
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

          {sessionExpired && loginStep === 'credentials' && (
            <Alert variant="info" className="mb-6">
              Your session has expired. Please sign in again.
            </Alert>
          )}

          {error && (
            <Alert variant="error" className="mb-6">
              {error}
            </Alert>
          )}

          {/* Step 1: Credentials */}
          {loginStep === 'credentials' && (
            <>
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
            </>
          )}

          {/* Step 2: OTP Verification */}
          {loginStep === 'otp' && (
            <>
              <div className="text-center mb-8">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-50 mb-4">
                  {otpSource === 'welcome_email' ? (
                    <Mail className="h-8 w-8 text-primary-600" />
                  ) : (
                    <ShieldCheck className="h-8 w-8 text-primary-600" />
                  )}
                </div>
                <h1 className="text-2xl font-semibold text-neutral-800 mb-2">
                  Verify your identity
                </h1>
                <p className="text-neutral-500">
                  {otpSource === 'welcome_email' ? (
                    <>Enter the 6-digit code from your <span className="font-medium">welcome email</span></>
                  ) : (
                    <>Enter the 6-digit code sent to <span className="font-medium">{loginEmail}</span></>
                  )}
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

                {/* Resend / Back */}
                <div className="flex items-center justify-between text-sm">
                  <button
                    type="button"
                    onClick={handleBack}
                    className="flex items-center gap-1 text-neutral-500 hover:text-neutral-700"
                  >
                    <ArrowLeft className="h-4 w-4" />
                    Back to login
                  </button>

                  {resendReady ? (
                    <button
                      type="button"
                      onClick={handleResend}
                      className="text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Resend code
                    </button>
                  ) : (
                    <span className="text-neutral-400">
                      Resend in {resendDisplay}
                    </span>
                  )}
                </div>
              </div>
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
