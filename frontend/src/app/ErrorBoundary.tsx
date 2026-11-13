import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Frontend render error', error, info.componentStack) }
  render() {
    if (this.state.failed) return <main className="fatal-error"><h1>The workspace could not load.</h1><p>Your browser has encountered an unexpected error. Reload to try again.</p><button className="button button--primary" onClick={() => window.location.reload()}>Reload workspace</button></main>
    return this.props.children
  }
}
