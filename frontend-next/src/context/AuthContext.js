'use client';
import { createContext, useContext, useState } from 'react';

// Mirroring the mock profiles from index.html
export const adminUser = { name: "Sarah Admin", email: "sarah@cosmic", role: "admin", initials: "SA" };
export const clientProfile = {
  'realty-demo': { name: 'Realty Pro', agent: 'Neha', agentId: 'real-estate-demo', role: 'client', initials: 'RP' },
  'finserv': { name: 'FinServ Plus', agent: 'Arjun', agentId: 'insurance-renewal', role: 'client', initials: 'FS' }
};

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [currentRole, setCurrentRole] = useState(null); // 'admin' or 'client'
  const [activeClient, setActiveClient] = useState('realty-demo');

  const login = (role) => {
    setCurrentRole(role);
  };

  const logout = () => {
    setCurrentRole(null);
  };

  return (
    <AuthContext.Provider value={{ currentRole, activeClient, setActiveClient, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
