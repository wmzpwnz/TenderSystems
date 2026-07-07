import { type HTMLAttributes, type ReactNode, forwardRef } from 'react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'auth' | 'auth-register';
  children: ReactNode;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = 'default', children, className, ...props }, ref) => {
    if (variant === 'auth' || variant === 'auth-register') {
      return (
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className={clsx(
            'auth-main-card relative z-10',
            variant === 'auth-register' && 'auth-register-card',
            className
          )}
          {...props}
        >
          <div className="auth-card-dot auth-dot-tl" />
          <div className="auth-card-dot auth-dot-tr" />
          <div className="auth-card-dot auth-dot-bl" />
          <div className="auth-card-dot auth-dot-br" />
          {children}
        </motion.div>
      );
    }

    return (
      <div
        ref={ref}
        className={clsx('blueprint-card p-5', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
