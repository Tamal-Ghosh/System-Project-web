import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, Link } from 'react-router-dom'
import { Activity, ChevronLeft, Menu, X } from 'lucide-react'
import { navigation } from './navigation'
import { ProfileLink } from '../components/ui/ProfileLink'
import { FloatingAssistant } from '../features/assistant/FloatingAssistant'

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const mobileToggle = useRef<HTMLButtonElement>(null)
  const drawer = useRef<HTMLElement>(null)
  const current = navigation.find(item => location.pathname.startsWith(item.to))?.label ?? (location.pathname.startsWith('/cases/') ? 'Analysis' : 'Workspace')

  useEffect(() => {
    setMobileOpen(false)
    document.title = `${current} · DermaScope`
  }, [location.pathname, current])
  useEffect(() => {
    const media = window.matchMedia('(min-width: 701px)')
    const closeOnDesktop = () => { if (media.matches) setMobileOpen(false) }
    media.addEventListener('change', closeOnDesktop)
    return () => media.removeEventListener('change', closeOnDesktop)
  }, [])
  useEffect(() => {
    if (!mobileOpen) return
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    drawer.current?.querySelector<HTMLButtonElement>('button')?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') setMobileOpen(false)
      if (event.key === 'Tab') {
        const nodes = Array.from(drawer.current?.querySelectorAll<HTMLElement>('a, button') ?? []).filter(node => node.getClientRects().length > 0)
        if (!nodes?.length) return
        const first = nodes[0], last = nodes[nodes.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = oldOverflow
      document.removeEventListener('keydown', onKey)
      mobileToggle.current?.focus()
    }
  }, [mobileOpen])

  return <div className={`app-shell ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}>
    <a href="#main-content" className="skip-link">Skip to content</a>
    {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}
    <aside ref={drawer} className="sidebar" aria-label="Primary navigation" role={mobileOpen ? 'dialog' : undefined} aria-modal={mobileOpen || undefined}>
      <Link to="/dashboard" className="brand" aria-label="DermaScope dashboard"><span className="brand-mark"><Activity size={23} strokeWidth={1.8} /></span><span className="sidebar-label">DermaScope<span className="brand-subtitle">CLINICIAN WORKSPACE</span></span></Link>
      <button className="mobile-close icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={20} /></button>
      <nav className="navigation">
        {['Workspace', 'Project'].map(section => <div className="nav-group" key={section}>
          <div className="nav-caption sidebar-label">{section}</div>
          {navigation.filter(item => item.section === section).map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `nav-link ${isActive ? 'is-active' : ''}`} title={label}><Icon size={19} strokeWidth={1.7} aria-hidden="true" /><span className="sidebar-label">{label}</span></NavLink>)}
        </div>)}
      </nav>
      <div className="sidebar-bottom"><button className="collapse-button" onClick={() => setCollapsed(value => !value)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} aria-expanded={!collapsed}><ChevronLeft size={18} className={collapsed ? 'rotate-icon' : ''} /><span className="sidebar-label">Collapse sidebar</span></button></div>
    </aside>
    <div className="app-main" inert={mobileOpen}>
      <header className="topbar"><div className="topbar-context"><button ref={mobileToggle} className="icon-button mobile-toggle" onClick={() => setMobileOpen(true)} aria-label="Open navigation" aria-expanded={mobileOpen}><Menu size={21} /></button>{current === 'Dashboard' ? <h1 className="dashboard-title">{current}</h1> : <span className="breadcrumb"><strong>{current}</strong></span>}</div><ProfileLink /></header>
      <main id="main-content" tabIndex={-1}><Outlet /></main>
      <FloatingAssistant key={location.pathname} />
    </div>
  </div>
}
