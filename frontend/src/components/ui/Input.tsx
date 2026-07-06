import { type ComponentType, type InputHTMLAttributes, type ReactNode, forwardRef } from 'react';
import clsx from 'clsx';

type IconComponent = ComponentType<{ className?: string }>;

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'auth';
  icon?: IconComponent;
  rightElement?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ variant = 'default', icon: Icon, rightElement, className, ...props }, ref) => {
    return (
      <div className="relative">
        {Icon && (
          <Icon
            className={clsx(
              variant === 'auth'
                ? 'authkit-input-icon'
                : 'absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--color-pebble)]'
            )}
          />
        )}
        <input
          ref={ref}
          className={clsx(
            variant === 'auth' ? 'authkit-input' : 'blueprint-input py-2 px-3',
            Icon && (variant === 'auth' ? 'pl-14' : 'pl-10'),
            rightElement && (variant === 'auth' ? 'pr-14' : 'pr-10'),
            className
          )}
          {...props}
        />
        {rightElement}
      </div>
    );
  }
);

Input.displayName = 'Input';
