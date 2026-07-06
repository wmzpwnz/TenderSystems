import { type LabelHTMLAttributes, type ReactNode, forwardRef } from 'react';
import clsx from 'clsx';

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  variant?: 'default' | 'auth';
  children: ReactNode;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ variant = 'default', children, className, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={clsx(
          variant === 'auth'
            ? 'authkit-label'
            : 'block text-[var(--color-glacier)] font-medium mb-2',
          className
        )}
        {...props}
      >
        {children}
      </label>
    );
  }
);

Label.displayName = 'Label';
