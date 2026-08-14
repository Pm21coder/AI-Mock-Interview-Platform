import './globals.css';
import { Toaster } from 'react-hot-toast';

export const metadata = {
  title: 'AI Mock Interview Platform',
  description: 'Practice your interview skills with AI-powered mock interviews',
  viewport: 'width=device-width, initial-scale=1, viewport-fit=cover, maximum-scale=5',
  themeColor: '#2563eb',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <head>
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
