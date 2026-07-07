import { type ComponentType, type ReactNode } from 'react';
import { motion } from 'framer-motion';

type IconComponent = ComponentType<{ className?: string }>;

type AuthPageProps = {
  children: ReactNode;
};

export function AuthPage({ children }: AuthPageProps) {
  return (
    <div className="blueprint-page auth-stage px-4 py-8 sm:px-6">
      <div className="auth-stack">{children}</div>
    </div>
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
    <div className="text-center mb-6">
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', delay: 0.2 }}
        className="auth-logo-mark"
      >
        <Icon className="h-6 w-6" />
      </motion.div>
      <p className="auth-eyebrow mb-4">{eyebrow}</p>
      <h2 className="auth-title">{title}</h2>
      <p className="auth-subtitle">{subtitle}</p>
    </div>
  );
}

type AuthDividerProps = {
  label?: string;
};

export function AuthDivider({ label = 'SECURE' }: AuthDividerProps) {
  return (
    <div className="auth-divider">
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
    <div className="auth-trust-row">
      <Icon className="h-4 w-4" />
      <span>{children}</span>
    </div>
  );
}
