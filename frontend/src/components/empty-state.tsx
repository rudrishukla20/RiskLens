import React from 'react';
import { HelpCircle } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  variant?: 'dashed' | 'solid' | 'simple';
  className?: string;
}

export const EmptyState = ({
  title,
  description,
  icon: Icon = HelpCircle,
  variant = 'dashed',
  className = '',
}: EmptyStateProps) => {
  if (variant === 'simple') {
    return (
      <div className={`flex flex-col items-center justify-center p-4 text-center h-full ${className}`}>
        <Icon className="h-6 w-6 text-muted-foreground mb-1.5 shrink-0" />
        <div className="text-xs font-semibold text-foreground">{title}</div>
        {description && <p className="text-[10px] text-muted-foreground mt-0.5 max-w-xs">{description}</p>}
      </div>
    );
  }

  const containerClasses =
    variant === 'dashed'
      ? 'border-2 border-dashed border-border rounded-lg bg-card shadow-sm'
      : 'border border-border bg-card rounded-lg shadow-sm';

  const iconClasses = variant === 'dashed' ? 'h-12 w-12 text-muted-foreground mb-3 shrink-0' : 'h-10 w-10 text-muted-foreground mb-2 shrink-0';

  return (
    <div className={`flex flex-col items-center justify-center py-16 px-4 text-center ${containerClasses} ${className}`}>
      <Icon className={iconClasses} />
      <h4 className="font-semibold text-foreground">{title}</h4>
      {description && <p className="text-xs text-muted-foreground max-w-md mt-1">{description}</p>}
    </div>
  );
};

export default EmptyState;
