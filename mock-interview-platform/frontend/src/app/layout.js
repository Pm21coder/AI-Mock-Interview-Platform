import './globals.css';
import { GoogleAnalytics, GoogleTagManager } from '@next/third-parties/google';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/next';
import { SITE_URL } from './site';

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'MockInterview AI | Practice Job Interviews with AI',
    template: '%s | MockInterview AI',
  },
  description: 'Prepare for your next job interview with AI-generated questions, personalized feedback, and realistic mock interview practice.',
  applicationName: 'MockInterview AI',
  keywords: [
    'AI mock interview',
    'interview practice',
    'job interview preparation',
    'AI interview coach',
    'technical interview practice',
    'behavioral interview questions',
  ],
  authors: [{ name: 'MockInterview AI' }],
  creator: 'MockInterview AI',
  publisher: 'MockInterview AI',
  category: 'Career Development',
  alternates: {
    canonical: '/',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
      'max-snippet': -1,
      'max-video-preview': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'MockInterview AI',
    url: '/',
    title: 'MockInterview AI | Practice Job Interviews with AI',
    description: 'Build interview confidence with AI-generated questions, realistic practice, and personalized feedback.',
  },
  twitter: {
    card: 'summary',
    title: 'MockInterview AI | Practice Job Interviews with AI',
    description: 'Build interview confidence with AI-generated questions, realistic practice, and personalized feedback.',
  },
  verification: {
    google: 'KTVw_NsHR-ZL_LW6TbOsBSlnlz-DyUoe5p-TcFEhZck',
  },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  maximumScale: 5,
  themeColor: '#2563eb',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-scroll-behavior="smooth" suppressHydrationWarning>
      <head>
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body className="font-sans antialiased bg-white text-gray-900">
        {/* Google Tag Manager (noscript) */}
        <noscript dangerouslySetInnerHTML={{
          __html: '<iframe src="https://www.googletagmanager.com/ns.html?id=GT-NB3Z6ML3" height="0" width="0" style="display:none;visibility:hidden"></iframe>',
        }} />
        {/* End Google Tag Manager (noscript) */}
        <GoogleTagManager gtmId="GT-NB3Z6ML3" />
        <GoogleAnalytics gaId="G-NDXBR2Z82J" />
        {children}
        <Toaster position="top-right" reverseOrder={false} />
        <Analytics />
      </body>
    </html>
  );
}
