import './globals.css';
import { Toaster } from 'react-hot-toast';

export const metadata = {
  title: 'AI Mock Interview Platform',
  description: 'Practice your interview skills with AI-powered mock interviews',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
