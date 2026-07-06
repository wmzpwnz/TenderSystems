import { type ComponentType, type InputHTMLAttributes, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

type IconComponent = ComponentType<{ className?: string }>;

type AuthPageProps = {
  children: ReactNode;
};

export function AuthPage({ children }: AuthPageProps) {
  return (
    <div className="blueprint-page authkit-stage px-4 py-8 sm:px-6">
      <div className="authkit-stack">{children}</div>
    </div>
  );
}

type AuthCardProps = {
  children: ReactNode;
  variant?: 'default' | 'register';
};

export function AuthCard({ children, variant = 'default' }: AuthCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={clsx(
        'authkit-main-card relative z-10',
        variant === 'register' && 'authkit-register-card',
      )}
    >
      <div className="authkit-card-dot authkit-dot-tl" />
      <div className="authkit-card-dot authkit-dot-tr" />
      <div className="authkit-card-dot authkit-dot-bl" />
      <div className="authkit-card-dot authkit-dot-br" />
      {children}
    </motion.div>
  );
}

type AuthHeaderProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  icon: IconComponent;
};

export function AuthHeader({ eyebrow, title, subtitle, icon: Icon }: AuthHeaderProps) {
  return (
    <div className="text-center mb-8">
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', delay: 0.2 }}
        className="authkit-logo-mark"
      >
        <Icon className="h-8 w-8" />
      </motion.div>
      <p className="authkit-eyebrow mb-5">{eyebrow}</p>
      <h2 className="authkit-title">{title}</h2>
      <p className="authkit-subtitle">{subtitle}</p>
    </div>
  );
}

type AuthInputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  icon: IconComponent;
  rightElement?: ReactNode;
};

export function AuthInput({ label, icon: Icon, rightElement, className, ...inputProps }: AuthInputProps) {
  return (
    <div>
      <label className="authkit-label">{label}</label>
      <div className="relative">
        <Icon className="authkit-input-icon" />
        <input
          {...inputProps}
          className={clsx('authkit-input', rightElement ? 'pl-14 pr-14' : 'pl-14 pr-5', className)}
        />
        {rightElement}
      </div>
    </div>
  );
}

type AuthSubmitProps = {
  children: ReactNode;
  disabled?: boolean;
};

export function AuthSubmit({ children, disabled }: AuthSubmitProps) {
  return (
    <button
      type="submit"
      disabled={disabled}
      className="authkit-submit disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {children}
    </button>
  );
}

type AuthMessageProps = {
  children: ReactNode;
  variant: 'error' | 'success';
  className?: string;
};

export function AuthMessage({ children, variant, className }: AuthMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={clsx(
        variant === 'success' ? 'blueprint-success' : 'blueprint-danger',
        'p-4',
        className,
      )}
    >
      {children}
    </motion.div>
  );
}

type AuthDividerProps = {
  label?: string;
};

export function AuthDivider({ label = 'SECURE' }: AuthDividerProps) {
  return (
    <div className="authkit-divider">
      <span />
      <b>{label}</b>
      <span />
    </div>
  );
}

type AuthTrustRowProps = {
  icon: IconComponent;
  children: ReactNode;
};

export function AuthTrustRow({ icon: Icon, children }: AuthTrustRowProps) {
  return (
    <div className="authkit-trust-row">
      <Icon className="h-4 w-4" />
      <span>{children}</span>
    </div>
  );
}
