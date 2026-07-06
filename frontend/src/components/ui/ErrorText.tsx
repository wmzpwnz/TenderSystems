import { type HTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export interface ErrorTextProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'auth' | 'success' | 'auth-success';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

export function ErrorText({ variant = 'default', size = 'sm', children, className, ...props }: ErrorTextProps) {
  if (variant === 'auth' || variant === 'auth-success') {
    const isSuccess = variant === 'auth-success';
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        className={clsx(
          isSuccess ? 'blueprint-success' : 'blueprint-danger',
          'p-4',
          className
        )}
        {...props}
      >
        <div
          className={clsx(
            'font-medium',
            size === 'sm' && 'text-sm',
            size === 'md' && 'text-base',
            size === 'lg' && 'text-lg'
          )}
        >
          {children}
        </div>
      </motion.div>
    );
  }

  const isSuccess = variant === 'success';
  return (
    <div
      className={clsx(
        isSuccess ? 'text-[var(--color-cipher-mint)]' : 'text-[var(--color-ember-bright)]',
        size === 'sm' && 'text-sm',
        size === 'md' && 'text-base',
        size === 'lg' && 'text-lg',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

