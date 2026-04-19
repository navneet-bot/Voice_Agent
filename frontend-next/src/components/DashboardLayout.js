'use client';
import { useAuth, adminUser, clientProfile } from '../context/AuthContext';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function DashboardLayout({ children }) {
  const { currentRole, activeClient, setActiveClient, logout } = useAuth();
  const pathname = usePathname();

  if (!currentRole) return null; // Or a loading state

  const user = currentRole === 'admin' ? adminUser : clientProfile[activeClient];

  const adminMenu = [
    { label: 'Live Monitor', path: '/monitor', icon: '📊' },
    { label: 'Campaigns', path: '/campaigns', icon: '🚀' },
    { label: 'Voice Agents', path: '/agents', icon: '🤖' },
    { label: 'Clients', path: '/clients', icon: '🏢' },
    { label: 'Call Logs & QA', path: '/logs', icon: '📞' }
  ];

  const clientMenu = [
    { label: 'Dashboard', path: '/client-dashboard', icon: '🏠' },
    { label: 'Talk Live (Testing)', path: '/talk-live', icon: '🎙️' },
    { label: 'Demo Campaign', path: '/demo', icon: '🎬' },
    { label: 'Call Results', path: '/results', icon: '📊' },
    { label: 'My Phone Numbers', path: '/numbers', icon: '☎' }
  ];

  const menu = currentRole === 'admin' ? adminMenu : clientMenu;

  return (
    <div className="d-flex flex-column vh-100 bg-light">
      <header className="d-flex justify-content-between align-items-center px-4 py-2 bg-white border-bottom shadow-sm">
        <div className="d-flex align-items-center">
          <h5 className="mb-0 fw-bold">Cosmic <span className="text-primary">Chameleon</span></h5>
          <span className="badge bg-secondary ms-3 px-2 py-1">v2.0 Beta</span>
        </div>
        <div className="d-flex align-items-center gap-3">
          {currentRole === 'admin' && (
            <select 
              className="form-select form-select-sm shadow-none" 
              value={activeClient} 
              onChange={(e) => setActiveClient(e.target.value)}
              style={{ width: '200px' }}
            >
              {Object.keys(clientProfile).map(key => (
                <option key={key} value={key}>Viewing: {clientProfile[key].name}</option>
              ))}
            </select>
          )}
          <div className="d-flex align-items-center gap-2 px-3 py-1 bg-light rounded text-dark">
            <div className="rounded-circle bg-primary text-white d-flex justify-content-center align-items-center" style={{ width: '32px', height: '32px', fontSize: '14px', fontWeight: 'bold' }}>
              {user.initials}
            </div>
            <div className="d-flex flex-column">
              <span className="fw-semibold" style={{ fontSize: '13px' }}>{user.name}</span>
              <span className="text-muted" style={{ fontSize: '11px', textTransform: 'capitalize' }}>{currentRole} Access</span>
            </div>
          </div>
          <button className="btn btn-outline-danger btn-sm" onClick={logout}>Sign Out</button>
        </div>
      </header>

      <div className="d-flex flex-grow-1 overflow-hidden">
        <aside className="bg-white border-end d-flex flex-column" style={{ width: '220px' }}>
          <div className="p-3 text-muted text-uppercase fw-bold" style={{ fontSize: '11px', letterSpacing: '1px' }}>
            Main Menu
          </div>
          <nav className="flex-grow-1 px-2">
            {menu.map(item => {
              const isActive = pathname === item.path;
              return (
                <Link 
                  key={item.path} 
                  href={item.path} 
                  className={`d-flex align-items-center p-2 mb-1 text-decoration-none rounded ${isActive ? 'bg-primary text-white shadow-sm' : 'text-secondary hover-bg-light'}`}
                  style={{ gap: '10px', fontSize: '14px', fontWeight: isActive ? '600' : '500' }}
                >
                  <span style={{ fontSize: '16px' }}>{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="flex-grow-1 p-4 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
