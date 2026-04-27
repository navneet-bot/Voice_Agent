import 'bootstrap/dist/css/bootstrap.min.css';
import "./globals.css";
import { AuthProvider } from '../context/AuthContext';

export const metadata = {
  title: "Cosmic Chameleon | Voice Agent Platform",
  description: "AI-Powered Real Estate Voice Agent Platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
