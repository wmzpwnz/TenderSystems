import { type ButtonHTMLAttributes, type ReactNode, forwardRef } from 'react';
import clsx from 'clsx';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'auth';
  size?: 'sm' | 'md' | 'lg' | 'auth';
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          variant === 'primary' && 'blueprint-button-primary',
          variant === 'ghost' && 'blueprint-button-ghost',
          variant === 'auth' && 'authkit-submit disabled:opacity-50 disabled:cursor-not-allowed',
          // Sizing classes for standard/product buttons
          size === 'sm' && variant !== 'auth' && 'px-3 py-1.5 text-sm',
          size === 'md' && variant !== 'auth' && 'px-4 py-2 text-base',
          size === 'lg' && variant !== 'auth' && 'px-6 py-3 text-lg',
          className
        )}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
