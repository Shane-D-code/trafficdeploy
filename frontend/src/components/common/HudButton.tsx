import React from 'react';

interface HudButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  loading?: boolean;
}

export const HudButton: React.FC<HudButtonProps> = ({
  variant = 'default',
  size = 'md',
  children,
  className = '',
  loading,
  disabled,
  ...props
}) => {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-5 py-2 text-sm',
    lg: 'px-6 py-2.5 text-sm',
  };

  const variantClass = variant === 'primary' ? 'hud-btn-primary' : variant === 'danger' ? 'hud-btn-danger' : '';

  return (
    <button
      className={`hud-btn ${variantClass} ${sizeClasses[size]} ${className} inline-flex items-center justify-center gap-2`}
      disabled={disabled || loading}
      {...props}
    >
      <span className="corner-bl" /><span className="corner-br" />
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  );
};
