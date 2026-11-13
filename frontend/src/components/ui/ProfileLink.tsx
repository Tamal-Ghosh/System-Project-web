import { UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

export function ProfileLink() {
  return <Link to="/settings" className="profile-button" aria-label="Open profile settings" title="Profile settings">
    <UserRound size={20} strokeWidth={1.7} aria-hidden="true" />
  </Link>
}
