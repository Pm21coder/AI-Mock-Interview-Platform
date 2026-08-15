import './globals.css';
import { GoogleAnalytics, GoogleTagManager } from '@next/third-parties/google';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/next';

export const metadata = {
  title: 'AI Mock Interview Platform',
  description: 'Practice your interview skills with AI-powered mock interviews',
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
        <meta name="google-site-verification" content="KTVw_NsHR-ZL_LW6TbOsBSlnlz-DyUoe5p-TcFEhZck" />
        <script id="Cookiebot" src="https://consent.cookiebot.com/uc.js" data-cbid="14c3d677-3235-4db8-a6ac-71c42d55f64c" type="text/javascript" async></script>
        <meta charSet="utf-8" />
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
