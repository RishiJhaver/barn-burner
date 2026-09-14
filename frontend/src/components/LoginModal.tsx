import React, { useState } from 'react';
import {
  X,
  Shield,
  User as UserIcon,
  Cloud,
  ArrowRight,
  KeyRound,
  Mail,
  Lock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type AuthTab = 'signin' | 'register' | 'presets';
type AuthStep = 'form' | 'verify_otp' | 'forgot_password' | 'reset_otp';

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose }) => {
  const {
    login,
    register,
    confirmSignUp,
    resendCode,
    forgotPassword,
    confirmForgotPassword,
    loginDemo,
    authConfig,
  } = useAuth();

  const [tab, setTab] = useState<AuthTab>('signin');
  const [step, setStep] = useState<AuthStep>('form');

  // Form Fields
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [registerUsername, setRegisterUsername] = useState('');
  const [registerEmail, setRegisterEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [selectedRole, setSelectedRole] = useState<UserRole>('user');
  const [showPassword, setShowPassword] = useState(false);

  // OTP Verification Fields
  const [otpTargetUsername, setOtpTargetUsername] = useState('');
  const [otpTargetEmail, setOtpTargetEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');

  // UI States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const resetState = () => {
    setErrorMessage(null);
    setSuccessMessage(null);
    setPassword('');
    setConfirmPassword('');
    setOtpCode('');
    setNewPassword('');
    setShowPassword(false);
  };

  const handleClose = () => {
    resetState();
    setStep('form');
    onClose();
  };

  // 1. Sign In Handler
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim() || !password) {
      setErrorMessage('Please enter both username/email and password.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await login(usernameOrEmail.trim(), password);
      handleClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message || 'Authentication failed.';
      if (detail.includes('not verified') || err.response?.status === 403) {
        setOtpTargetUsername(usernameOrEmail.trim());
        setStep('verify_otp');
        setErrorMessage('Your account is not verified yet. Please enter the OTP code.');
      } else {
        setErrorMessage(detail);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // 2. Register Handler
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registerUsername.trim() || !registerEmail.trim() || !password) {
      setErrorMessage('Please fill in all required fields.');
      return;
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      const res = await register(
        registerUsername.trim(),
        registerEmail.trim(),
        password,
        selectedRole
      );
      setOtpTargetUsername(registerUsername.trim());
      setOtpTargetEmail(registerEmail.trim());
      setSuccessMessage('Account created! Please verify your email with the confirmation code.');
      setStep('verify_otp');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 3. Confirm OTP Handler
  const handleConfirmOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim()) {
      setErrorMessage('Please enter the 6-digit confirmation code.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await confirmSignUp(otpTargetUsername, otpCode.trim());
      setSuccessMessage('Account verified successfully! You can now sign in.');
      setStep('form');
      setTab('signin');
      setUsernameOrEmail(otpTargetUsername);
      setPassword('');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Invalid verification code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 4. Resend Code Handler
  const handleResendOtp = async () => {
    try {
      await resendCode(otpTargetUsername);
      setSuccessMessage('A new verification code has been dispatched.');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to resend code.');
    }
  };

  // 5. Forgot Password Request Handler
  const handleForgotPasswordRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail.trim()) {
      setErrorMessage('Please enter your username or email address.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      const res = await forgotPassword(usernameOrEmail.trim());
      setOtpTargetUsername(usernameOrEmail.trim());
      setSuccessMessage(res.message || 'Verification code sent to your email.');
      setStep('reset_otp');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to send reset code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // 6. Confirm Password Reset Handler
  const handleConfirmPasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!otpCode.trim() || !newPassword) {
      setErrorMessage('Please enter both verification code and new password.');
      return;
    }
    if (newPassword.length < 6) {
      setErrorMessage('New password must be at least 6 characters.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      await confirmForgotPassword(otpTargetUsername, otpCode.trim(), newPassword);
      setSuccessMessage('Password reset successfully! Please sign in with your new password.');
      setStep('form');
      setTab('signin');
      setPassword('');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to reset password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLiveCognito = authConfig && !authConfig.mock_cognito;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-black/10 dark:border-white/15 bg-white/95 dark:bg-[#0c0e14]/95 p-8 shadow-2xl backdrop-blur-3xl transition-all">
        {/* Iridescent ambient glow */}
        <div className="pointer-events-none absolute -top-24 -right-24 h-56 w-56 rounded-full bg-gradient-to-br from-purple-500/25 to-pink-500/25 dark:from-purple-600/20 dark:to-pink-600/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-56 w-56 rounded-full bg-gradient-to-tr from-cyan-500/20 to-indigo-500/20 dark:from-cyan-600/15 dark:to-indigo-600/15 blur-3xl" />

        {/* Close Button */}
        <button
          onClick={handleClose}
          className="absolute top-6 right-6 rounded-xl p-1.5 text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.04] dark:hover:bg-white/[0.05] transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal Header */}
        <div className="mb-5 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl border border-black/10 dark:border-white/15 bg-black/[0.02] dark:bg-white/[0.04] text-slate-900 dark:text-white shadow-sm">
            <Cloud className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>

          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wider uppercase border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] mb-1">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                isLiveCognito ? 'bg-emerald-500 animate-pulse' : 'bg-blue-500'
              }`}
            />
            <span className="text-slate-500 dark:text-slate-400">
              {isLiveCognito ? 'AWS Cognito Live' : 'Cognito Auth Gateway'}
            </span>
          </div>

          <h3 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white font-sans">
            {step === 'verify_otp'
              ? 'Verify Email'
              : step === 'forgot_password' || step === 'reset_otp'
              ? 'Reset Password'
              : tab === 'signin'
              ? 'Sign In to CodeGrid'
              : tab === 'register'
              ? 'Create an Account'
              : 'Developer Presets'}
          </h3>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 font-sans">
            {step === 'verify_otp'
              ? `Enter the 6-digit verification code sent to ${otpTargetEmail || 'your email'}`
              : step === 'forgot_password'
              ? 'Enter your username or email to receive a recovery code'
              : step === 'reset_otp'
              ? 'Enter the recovery code and your new password'
              : 'Secure authentication backed by AWS Cognito User Pools'}
          </p>
        </div>

        {/* Status Alerts */}
        {errorMessage && (
          <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400 animate-fadeIn">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span className="font-medium leading-relaxed">{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="mb-4 flex items-start gap-2.5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400 animate-fadeIn">
            <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
            <span className="font-medium leading-relaxed">{successMessage}</span>
          </div>
        )}

        {/* Primary Navigation Tabs (Only in Form Step) */}
        {step === 'form' && (
          <div className="flex gap-1.5 rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-1 mb-5 text-xs">
            <button
              onClick={() => {
                setTab('signin');
                resetState();
              }}
              className={`flex-1 py-2 rounded-xl font-medium transition-all ${
                tab === 'signin'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              onClick={() => {
                setTab('register');
                resetState();
              }}
              className={`flex-1 py-2 rounded-xl font-medium transition-all ${
                tab === 'register'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              Register
            </button>
            <button
              onClick={() => {
                setTab('presets');
                resetState();
              }}
              className={`flex-1 py-2 rounded-xl font-medium transition-all ${
                tab === 'presets'
                  ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              1-Click Demo
            </button>
          </div>
        )}

        {/* ========================================================= */}
        {/* STEP 1: SIGN IN FORM                                      */}
        {/* ========================================================= */}
        {step === 'form' && tab === 'signin' && (
          <form onSubmit={handleSignIn} className="space-y-3.5 text-xs">
            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Handle or Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  placeholder="e.g. alex_coder or alex@codegrid.dev"
                  value={usernameOrEmail}
                  onChange={(e) => setUsernameOrEmail(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] pl-9 pr-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-slate-500 dark:text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setStep('forgot_password');
                    resetState();
                  }}
                  className="text-[11px] text-purple-600 dark:text-purple-400 hover:underline font-medium"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] pl-9 pr-10 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* ========================================================= */}
        {/* STEP 2: REGISTRATION FORM                                 */}
        {/* ========================================================= */}
        {step === 'form' && tab === 'register' && (
          <form onSubmit={handleRegister} className="space-y-3 text-xs">
            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Coder Handle
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <UserIcon className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  placeholder="e.g. dev_rishi"
                  value={registerUsername}
                  onChange={(e) => setRegisterUsername(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] pl-9 pr-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="email"
                  placeholder="name@company.com"
                  value={registerEmail}
                  onChange={(e) => setRegisterEmail(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] pl-9 pr-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                  Password
                </label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Min 6 chars"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] px-3 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                  Confirm
                </label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Repeat pwd"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] px-3 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>
            </div>

            {/* Role Selection */}
            <div className="pt-1">
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Account Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                <label
                  className={`flex items-center gap-2 rounded-xl border p-2.5 cursor-pointer transition-all ${
                    selectedRole === 'user'
                      ? 'border-slate-900 bg-slate-900/5 dark:border-white dark:bg-white/5 font-semibold text-slate-900 dark:text-white'
                      : 'border-black/10 dark:border-white/10 text-slate-500 hover:border-black/20'
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    checked={selectedRole === 'user'}
                    onChange={() => setSelectedRole('user')}
                    className="sr-only"
                  />
                  <UserIcon className="h-3.5 w-3.5" />
                  <span>Coder</span>
                </label>

                <label
                  className={`flex items-center gap-2 rounded-xl border p-2.5 cursor-pointer transition-all ${
                    selectedRole === 'admin'
                      ? 'border-slate-900 bg-slate-900/5 dark:border-white dark:bg-white/5 font-semibold text-slate-900 dark:text-white'
                      : 'border-black/10 dark:border-white/10 text-slate-500 hover:border-black/20'
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    checked={selectedRole === 'admin'}
                    onChange={() => setSelectedRole('admin')}
                    className="sr-only"
                  />
                  <Shield className="h-3.5 w-3.5" />
                  <span>Setter (Admin)</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* ========================================================= */}
        {/* STEP 3: OTP CONFIRMATION STEP                             */}
        {/* ========================================================= */}
        {step === 'verify_otp' && (
          <form onSubmit={handleConfirmOtp} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-center">
                6-Digit Confirmation Code
              </label>
              <input
                type="text"
                maxLength={6}
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                className="w-full rounded-2xl border border-black/15 dark:border-white/15 bg-white/60 dark:bg-white/[0.04] px-4 py-3 text-center text-xl tracking-[0.4em] font-mono font-bold text-slate-900 dark:text-white placeholder-slate-300 focus:border-slate-900 dark:focus:border-white focus:outline-none shadow-sm"
                required
                autoFocus
              />
              {!isLiveCognito && (
                <p className="mt-1.5 text-center text-[11px] text-purple-600 dark:text-purple-400 font-medium">
                  💡 In Sandbox mode, code is <span className="font-mono font-bold">123456</span>
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Verify & Activate</span>
                </>
              )}
            </button>

            <div className="flex items-center justify-between pt-1 text-[11px]">
              <button
                type="button"
                onClick={() => {
                  setStep('form');
                  resetState();
                }}
                className="text-slate-500 hover:text-slate-900 dark:hover:text-white"
              >
                ← Back to Sign In
              </button>
              <button
                type="button"
                onClick={handleResendOtp}
                className="text-purple-600 dark:text-purple-400 hover:underline font-medium"
              >
                Resend Code
              </button>
            </div>
          </form>
        )}

        {/* ========================================================= */}
        {/* STEP 4: FORGOT PASSWORD REQUEST                           */}
        {/* ========================================================= */}
        {step === 'forgot_password' && (
          <form onSubmit={handleForgotPasswordRequest} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Enter your Handle or Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  placeholder="e.g. dev_rishi"
                  value={usernameOrEmail}
                  onChange={(e) => setUsernameOrEmail(e.target.value)}
                  className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] pl-9 pr-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none transition-all shadow-sm"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <span>Send Recovery Code</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>

            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setStep('form');
                  resetState();
                }}
                className="text-slate-500 hover:text-slate-900 dark:hover:text-white text-[11px]"
              >
                ← Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ========================================================= */}
        {/* STEP 5: RESET PASSWORD WITH OTP                           */}
        {/* ========================================================= */}
        {step === 'reset_otp' && (
          <form onSubmit={handleConfirmPasswordReset} className="space-y-3.5 text-xs">
            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                Recovery Code
              </label>
              <input
                type="text"
                maxLength={6}
                placeholder="123456"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] px-3.5 py-2.5 text-center font-mono font-bold tracking-widest text-slate-900 dark:text-white focus:border-slate-900 dark:focus:border-white focus:outline-none"
                required
              />
            </div>

            <div>
              <label className="block text-slate-500 dark:text-slate-400 mb-1 text-[11px] font-semibold uppercase tracking-wider">
                New Password
              </label>
              <input
                type="password"
                placeholder="Minimum 6 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-black/10 dark:border-white/10 bg-white/60 dark:bg-white/[0.04] px-3.5 py-2.5 text-slate-900 dark:text-white placeholder-slate-400 focus:border-slate-900 dark:focus:border-white focus:outline-none"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900 py-3 font-semibold shadow-sm hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {isSubmitting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <KeyRound className="h-4 w-4" />
                  <span>Update Password</span>
                </>
              )}
            </button>

            <div className="text-center pt-1">
              <button
                type="button"
                onClick={() => {
                  setStep('form');
                  resetState();
                }}
                className="text-slate-500 hover:text-slate-900 dark:hover:text-white text-[11px]"
              >
                ← Back to Sign In
              </button>
            </div>
          </form>
        )}

        {/* ========================================================= */}
        {/* TAB 3: QUICK DEVELOPER PRESETS                            */}
        {/* ========================================================= */}
        {step === 'form' && tab === 'presets' && (
          <div className="space-y-4 text-xs">
            <div className="space-y-2">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                1-Click Instant Developer Access:
              </p>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  onClick={async () => {
                    await loginDemo('user', 'alex_coder', 'alex@codegrid.dev');
                    handleClose();
                  }}
                  className="flex flex-col items-start rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-3.5 text-left hover:border-black/30 dark:hover:border-white/30 transition-all shadow-sm"
                >
                  <span className="font-bold text-slate-900 dark:text-white text-xs">👤 Coder Alex</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Role: Standard User</span>
                  <span className="text-[10px] text-purple-600 dark:text-purple-400 mt-1 font-mono">alex_coder</span>
                </button>

                <button
                  onClick={async () => {
                    await loginDemo('admin', 'elena_admin', 'elena@codegrid.dev');
                    handleClose();
                  }}
                  className="flex flex-col items-start rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-3.5 text-left hover:border-black/30 dark:hover:border-white/30 transition-all shadow-sm"
                >
                  <span className="font-bold text-slate-900 dark:text-white text-xs">🛡️ Admin Elena</span>
                  <span className="text-[10px] text-slate-400 mt-0.5">Role: Problem Setter</span>
                  <span className="text-[10px] text-purple-600 dark:text-purple-400 mt-1 font-mono">elena_admin</span>
                </button>
              </div>
            </div>

            <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-3.5 text-slate-600 dark:text-slate-400 text-[11px] leading-relaxed">
              <span className="font-semibold text-slate-900 dark:text-white block mb-0.5">
                💡 Dual-Mode Architecture Notice:
              </span>
              CodeGrid seamlessly switches between local developer mode and live AWS Cognito User Pools via{' '}
              <code className="px-1 py-0.5 rounded bg-black/5 dark:bg-white/10 font-mono text-[10px]">
                MOCK_COGNITO=False
              </code>
              . Tokens are cryptographically validated RS256/HS256 JWTs.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
