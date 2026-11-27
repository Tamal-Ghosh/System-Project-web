import { LayoutDashboard, Settings2, ScanLine, FileText, CircleHelp, ShieldCheck } from 'lucide-react'

// Shared navigation registry: agree changes here before merging feature branches.
export const navigation = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, section: 'Workspace' },
  { to: '/analysis', label: 'Analysis', icon: ScanLine, section: 'Workspace' },
  { to: '/reports', label: 'Reports', icon: FileText, section: 'Workspace' },
  { to: '/evidence', label: 'Model Evidence', icon: ShieldCheck, section: 'Workspace' },
  { to: '/settings', label: 'Settings', icon: Settings2, section: 'Project' },
  { to: '/help', label: 'Help', icon: CircleHelp, section: 'Project' },
]
