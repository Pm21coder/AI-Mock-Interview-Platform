/**
 * Responsive Container Component
 * Provides consistent responsive padding and max-width constraints
 * Used across pages for mobile-first design
 */
export function Container({ children, className = '' }) {
  return (
    <div className={`mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 ${className}`}>
      {children}
    </div>
  );
}

/**
 * Responsive Section Component
 * Provides consistent responsive vertical spacing
 */
export function Section({ children, className = '' }) {
  return (
    <section className={`py-8 sm:py-12 md:py-16 lg:py-20 ${className}`}>
      {children}
    </section>
  );
}

/**
 * Responsive Grid Component
 * Mobile-first grid that adapts from 1 column to multiple columns
 */
export function ResponsiveGrid({ children, cols = 3, gap = 'md', className = '' }) {
  const gapClasses = {
    sm: 'gap-3 sm:gap-4',
    md: 'gap-4 sm:gap-6 md:gap-8',
    lg: 'gap-6 sm:gap-8 md:gap-10',
  };

  const colClasses = {
    1: 'grid-cols-1',
    2: 'md:grid-cols-2',
    3: 'md:grid-cols-3',
    4: 'md:grid-cols-2 lg:grid-cols-4',
  };

  return (
    <div className={`grid ${colClasses[cols]} ${gapClasses[gap]} ${className}`}>
      {children}
    </div>
  );
}

/**
 * Responsive Button Component
 * Touch-friendly with proper sizing for mobile and desktop
 */
export function ResponsiveButton({
  children,
  href,
  onClick,
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}) {
  const baseClasses = 'inline-flex items-center justify-center rounded-lg font-semibold transition-all duration-200 active:scale-95';

  const sizeClasses = {
    sm: 'px-4 py-2 text-sm sm:px-5 sm:py-2.5',
    md: 'px-6 py-3 text-base sm:px-8 sm:py-4 sm:text-lg',
    lg: 'px-8 py-4 text-lg sm:px-10 sm:py-5 sm:text-xl',
  };

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    ghost: 'text-blue-600 hover:bg-blue-50',
  };

  const combinedClasses = `${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`;

  const Element = href ? 'a' : 'button';

  return (
    <Element href={href} onClick={onClick} className={combinedClasses} {...props}>
      {children}
    </Element>
  );
}

/**
 * Responsive Card Component
 * Consistent card styling with responsive padding
 */
export function Card({ children, className = '', hover = false }) {
  return (
    <div
      className={`rounded-lg bg-white p-4 sm:p-6 shadow-lg transition-all duration-200 ${
        hover ? 'hover:shadow-xl hover:-translate-y-1' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
}
