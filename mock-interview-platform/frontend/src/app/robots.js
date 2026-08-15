import { SITE_URL } from './site';

export default function robots() {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: [
        '/api/',
        '/auth',
        '/dashboard',
        '/interview/',
        '/resume',
        '/subscription-management',
        '/subscription/success',
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
