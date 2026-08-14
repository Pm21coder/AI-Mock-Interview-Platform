'use client';

import Image from 'next/image';
import { useState } from 'react';

/**
 * Responsive Image Component
 * Automatically handles:
 * - Lazy loading
 * - Responsive sizing with next/image
 * - Responsive srcset for different device sizes
 * - AVIF and WebP format support
 * - Proper aspect ratio handling
 * - Blur placeholder while loading
 * - Responsive object-fit
 */
export function ResponsiveImage({
  src,
  alt,
  width,
  height,
  priority = false,
  className = '',
  objectFit = 'cover',
  objectPosition = 'center',
  sizes = '(max-width: 640px) 100vw, (max-width: 1024px) 90vw, 85vw',
  ...props
}) {
  const [isLoading, setIsLoading] = useState(true);

  // Calculate aspect ratio for responsive sizing
  const aspectRatio = height ? (width / height).toFixed(3) : '16/9';

  return (
    <div
      className={`relative w-full overflow-hidden rounded-lg bg-gray-100 ${className}`}
      style={{
        aspectRatio,
      }}
    >
      <Image
        src={src}
        alt={alt}
        fill
        priority={priority}
        sizes={sizes}
        className={`transition-opacity duration-300 ${
          isLoading ? 'opacity-0' : 'opacity-100'
        }`}
        style={{
          objectFit,
          objectPosition,
        }}
        onLoadingComplete={() => setIsLoading(false)}
        {...props}
      />
      {isLoading && (
        <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-gray-100 via-gray-50 to-gray-100" />
      )}
    </div>
  );
}

/**
 * Responsive Hero Image Component
 * Optimized for full-width hero sections on mobile and desktop
 */
export function HeroImage({
  src,
  alt,
  height = 500,
  className = '',
  ...props
}) {
  return (
    <ResponsiveImage
      src={src}
      alt={alt}
      width={1920}
      height={height}
      priority
      sizes="100vw"
      className={`h-48 sm:h-64 md:h-96 lg:h-screen max-h-screen w-full ${className}`}
      {...props}
    />
  );
}

/**
 * Responsive Avatar Image Component
 * Optimized for circular user avatars
 */
export function AvatarImage({
  src,
  alt,
  size = 'md',
  className = '',
  ...props
}) {
  const sizeClasses = {
    sm: 'h-8 w-8 sm:h-10 sm:w-10',
    md: 'h-12 w-12 sm:h-14 sm:w-14',
    lg: 'h-16 w-16 sm:h-20 sm:w-20',
    xl: 'h-24 w-24 sm:h-32 sm:w-32',
  };

  return (
    <div className={`relative flex-shrink-0 overflow-hidden rounded-full bg-gray-200 ${sizeClasses[size]}`}>
      <Image
        src={src}
        alt={alt}
        fill
        sizes={size === 'sm' ? '40px' : size === 'md' ? '56px' : size === 'lg' ? '80px' : '128px'}
        className="h-full w-full object-cover"
        {...props}
      />
    </div>
  );
}

/**
 * Responsive Thumbnail Image Component
 * Optimized for small preview images in grids
 */
export function ThumbnailImage({
  src,
  alt,
  className = '',
  ...props
}) {
  return (
    <ResponsiveImage
      src={src}
      alt={alt}
      width={400}
      height={300}
      sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
      className={`aspect-video w-full ${className}`}
      {...props}
    />
  );
}
