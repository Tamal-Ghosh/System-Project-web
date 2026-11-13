import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Variant = 'primary' | 'secondary' | 'ghost'
export function Button({ variant = 'secondary', className = '', type = 'button', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type={type} className={`button button--${variant} ${className}`} {...props} />
}
export function ButtonLink({ to, children, variant = 'secondary' }: { to: string; children: ReactNode; variant?: Variant }) {
  return <Link to={to} className={`button button--${variant}`}>{children}</Link>
}
