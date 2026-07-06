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
            'authkit-main-card relative z-10',
            variant === 'auth-register' && 'authkit-register-card',
            className
          )}
          {...props}
        >
          <div className="authkit-card-dot authkit-dot-tl" />
          <div className="authkit-card-dot authkit-dot-tr" />
          <div className="authkit-card-dot authkit-dot-bl" />
          <div className="authkit-card-dot authkit-dot-br" />
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
