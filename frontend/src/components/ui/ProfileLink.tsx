import { UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'

export function ProfileLink() {
  return <Link to="/profile" className="profile-button" aria-label="Open profile" title="My Profile">
    <UserRound size={20} strokeWidth={1.7} aria-hidden="true" />
  </Link>
}
