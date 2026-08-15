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
    <html lang="en" data-scroll-behavior="smooth" suppressHydrationWarning>
      <head>
        {/* Google Tag Manager */}
        <script dangerouslySetInnerHTML={{
          __html: `(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
          new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
          j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
          'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
          })(window,document,'script','dataLayer','GT-NB3Z6ML3');`,
        }} />
        {/* End Google Tag Manager */}
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
        {/* Google Tag Manager (noscript) */}
        <noscript dangerouslySetInnerHTML={{
          __html: '<iframe src="https://www.googletagmanager.com/ns.html?id=GT-NB3Z6ML3" height="0" width="0" style="display:none;visibility:hidden"></iframe>',
        }} />
        {/* End Google Tag Manager (noscript) */}
        {children}
        <Toaster position="top-right" reverseOrder={false} />
      </body>
    </html>
  );
}
