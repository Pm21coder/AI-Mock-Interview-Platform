import './globals.css';
import { Toaster } from 'react-hot-toast';

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
    <html lang="en" data-scroll-behavior="smooth">
      <head>
        <meta name="google-site-verification" content="KTVw_NsHR-ZL_LW6TbOsBSlnlz-DyUoe5p-TcFEhZck" />
        <script id="Cookiebot" src="https://consent.cookiebot.com/uc.js" data-cbid="14c3d677-3235-4db8-a6ac-71c42d55f64c" type="text/javascript" async></script>
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-NDXBR2Z82J" />
        <script dangerouslySetInnerHTML={{
          __html: `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-NDXBR2Z82J');
          `,
        }} />
        <meta charSet="utf-8" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body className="font-sans antialiased bg-white text-gray-900">
        {children}
        <Toaster position="top-right" reverseOrder={false} />
      </body>
    </html>
  );
}
