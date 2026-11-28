import {
  ArrowRight,
  CheckCircle2,
  FileText,
  Globe,
  KeyRound,
  LogOut,
  Moon,
  ShieldCheck,
  Sun,
  UserRound,
} from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { loadClinicSettings, saveClinicSettings } from '../../services/settings'
import type { ClinicSettings } from '../../services/settings'

export function SettingsPage() {
  const [settings, setSettings] = useState<ClinicSettings>(() => loadClinicSettings())
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [securityMessage, setSecurityMessage] = useState('')
  const [securityError, setSecurityError] = useState('')
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [prefsSaved, setPrefsSaved] = useState(false)

  const isBn = settings.language === 'bn'

  function updateAndSave(patch: Partial<ClinicSettings>) {
    const next = { ...settings, ...patch }
    setSettings(next)
    saveClinicSettings(next)
    setPrefsSaved(true)
    window.setTimeout(() => setPrefsSaved(false), 2500)
  }

  function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault()
    setSecurityError('')
    setSecurityMessage('')
    if (!currentPassword || newPassword.length < 8) {
      setSecurityError(
        isBn
          ? 'বর্তমান পাসওয়ার্ড দিন এবং নতুন পাসওয়ার্ড কমপক্ষে ৮ অক্ষরের রাখুন।'
          : 'Enter your current password and a new password of at least 8 characters.'
      )
      return
    }
    if (newPassword !== confirmPassword) {
      setSecurityError(isBn ? 'নতুন পাসওয়ার্ড দুটি মিলছে না।' : 'New passwords do not match.')
      return
    }
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setShowPasswordForm(false)
    setSecurityMessage(isBn ? 'পাসওয়ার্ড সফলভাবে আপডেট হয়েছে।' : 'Password updated successfully.')
  }

  function handleLogoutAllDevices() {
    setLogoutConfirm(false)
    setSecurityError('')
    setSecurityMessage(
      isBn
        ? 'সব ডিভাইস থেকে সেশন লগ-আউট করা হয়েছে।'
        : 'All active device sessions have been signed out.'
    )
  }

  return (
    <div className="reports-page workspace-narrow">
      <div className="clinical-page-heading">
        <div>
          <div className="eyebrow">{isBn ? 'ওয়ার্কস্পেস কনফিগারেশন' : 'Workspace preferences'}</div>
          <h1>{isBn ? 'সেটিংস (Settings)' : 'Settings'}</h1>
          <p>
            {isBn
              ? 'প্রোফাইল, থিম, ভাষা, নিরাপত্তা এবং রিপোর্টের পছন্দসমূহ নিয়ন্ত্রণ করুন।'
              : 'Manage your profile, appearance, security, and report export preferences.'}
          </p>
        </div>
      </div>

      {/* 1. My Profile */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><UserRound size={20} /></span>
            <div>
              <h2>{isBn ? 'আমার প্রোফাইল (My Profile)' : 'My Profile'}</h2>
              <p>{settings.defaultClinician || (isBn ? 'ক্লিনিশিয়ান প্রোফাইল' : 'Clinician Profile')} · {settings.clinicianDesignation}</p>
            </div>
          </div>
          <Link to="/profile" className="button button--primary">
            {isBn ? 'প্রোফাইল পেজে যান' : 'Go to Profile'} <ArrowRight size={15} />
          </Link>
        </div>
      </section>

      {/* 2. Appearance & Language */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><Globe size={20} /></span>
            <div>
              <h2>{isBn ? 'অ্যাপিয়ারেন্স ও ভাষা (Appearance & Language)' : 'Appearance & Language'}</h2>
              <p>{isBn ? 'থিম মোড এবং ইন্টারফেসের ভাষা পরিবর্তন করুন।' : 'Customize color theme and display language across workspace pages.'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div className="settings-grid-two">
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: 'var(--muted)' }}>
              {isBn ? 'থিম (Theme)' : 'Theme'}
            </div>
            <div className="segmented-control" role="group" aria-label="Theme">
              <button
                type="button"
                aria-pressed={settings.theme === 'light'}
                className={settings.theme === 'light' ? 'is-selected' : ''}
                onClick={() => updateAndSave({ theme: 'light' })}
              >
                <Sun size={15} /> {isBn ? 'লাইট মোড' : 'Light Mode'}
              </button>
              <button
                type="button"
                aria-pressed={settings.theme === 'dark'}
                className={settings.theme === 'dark' ? 'is-selected' : ''}
                onClick={() => updateAndSave({ theme: 'dark' })}
              >
                <Moon size={15} /> {isBn ? 'ডার্ক মোড' : 'Dark Mode'}
              </button>
            </div>
          </div>

          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: 'var(--muted)' }}>
              {isBn ? 'ভাষা (Language)' : 'Language'}
            </div>
            <div className="segmented-control" role="group" aria-label="Language">
              <button
                type="button"
                aria-pressed={settings.language === 'en'}
                className={settings.language === 'en' ? 'is-selected' : ''}
                onClick={() => updateAndSave({ language: 'en' })}
              >
                English
              </button>
              <button
                type="button"
                aria-pressed={settings.language === 'bn'}
                className={settings.language === 'bn' ? 'is-selected' : ''}
                onClick={() => updateAndSave({ language: 'bn' })}
              >
                বাংলা (Bangla)
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Security & Privacy */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><ShieldCheck size={20} /></span>
            <div>
              <h2>{isBn ? 'নিরাপত্তা ও গোপনীয়তা (Security & Privacy)' : 'Security & Privacy'}</h2>
              <p>{isBn ? 'পাসওয়ার্ড পরিবর্তন করুন এবং অ্যাক্টিভ সেশন নিয়ন্ত্রণ করুন।' : 'Update account credentials and manage active device sessions.'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => {
              setShowPasswordForm(prev => !prev)
              setSecurityError('')
              setSecurityMessage('')
            }}
          >
            <KeyRound size={15} /> {isBn ? 'পাসওয়ার্ড পরিবর্তন করুন' : 'Change Password'}
          </button>
          <button
            type="button"
            className="button button--secondary"
            style={{ color: '#c92a2a', borderColor: '#f3c6c6' }}
            onClick={() => setLogoutConfirm(true)}
          >
            <LogOut size={15} /> {isBn ? 'সব ডিভাইস থেকে লগ-আউট' : 'Logout from All Devices'}
          </button>
        </div>

        {showPasswordForm && (
          <form onSubmit={handlePasswordSubmit} className="assessment-form" style={{ marginTop: '14px', padding: '16px', background: 'var(--surface-muted)', borderRadius: '9px', border: '1px solid var(--color-line)' }}>
            <label>
              {isBn ? 'বর্তমান পাসওয়ার্ড' : 'Current password'}
              <input type="password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />
            </label>
            <div className="settings-grid-two">
              <label>
                {isBn ? 'নতুন পাসওয়ার্ড' : 'New password'}
                <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
              </label>
              <label>
                {isBn ? 'নতুন পাসওয়ার্ড নিশ্চিত করুন' : 'Confirm new password'}
                <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
              </label>
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button type="button" className="button button--secondary" onClick={() => setShowPasswordForm(false)}>
                {isBn ? 'বাতিল' : 'Cancel'}
              </button>
              <button type="submit" className="button button--primary">
                {isBn ? 'পাসওয়ার্ড সেভ করুন' : 'Update Password'}
              </button>
            </div>
          </form>
        )}

        {logoutConfirm && (
          <div style={{ marginTop: '14px', padding: '12px 14px', border: '1px solid #f3c6c6', borderRadius: '8px', background: '#fff5f5', color: '#203047', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <span>{isBn ? 'আপনি কি নিশ্চিতভাবে সব ডিভাইস থেকে লগ-আউট করতে চান?' : 'Sign out from all active devices?'}</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="button" className="button button--secondary" onClick={() => setLogoutConfirm(false)}>
                {isBn ? 'না' : 'Cancel'}
              </button>
              <button type="button" className="button button--primary" style={{ background: '#c92a2a', borderColor: '#c92a2a' }} onClick={handleLogoutAllDevices}>
                {isBn ? 'হ্যাঁ, লগ-আউট করুন' : 'Confirm Logout'}
              </button>
            </div>
          </div>
        )}

        {securityError && <p style={{ color: '#c92a2a', marginTop: '10px', fontSize: '13.5px' }}>{securityError}</p>}
        {securityMessage && (
          <p style={{ color: 'var(--color-sage)', marginTop: '10px', fontSize: '13.5px', fontWeight: 600 }} role="status">
            {securityMessage}
          </p>
        )}
      </section>

      {/* 4. Report Preferences */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><FileText size={20} /></span>
            <div>
              <h2>{isBn ? 'রিপোর্ট পছন্দসমূহ (Report Preferences)' : 'Report Preferences'}</h2>
              <p>{isBn ? 'রিপোর্টের ফরম্যাট এবং XAI/Segmentation এভিডেন্স যুক্ত করা নিয়ন্ত্রণ করুন।' : 'Choose default PDF layout and toggle visual AI evidence sections.'}</p>
            </div>
          </div>
          {prefsSaved && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: 'var(--color-sage)', fontWeight: 600, fontSize: '13px' }} role="status">
              <CheckCircle2 size={15} /> {isBn ? 'সেভ হয়েছে' : 'Saved'}
            </span>
          )}
        </div>
        <div className="settings-card__divider" />

        <div className="assessment-form">
          <label style={{ maxWidth: '460px' }}>
            {isBn ? 'রিপোর্ট ফরম্যাট (Report format)' : 'Report format'}
            <select
              value={settings.reportFormat}
              onChange={event =>
                updateAndSave({ reportFormat: event.target.value as 'standard_2page' | 'compact' })
              }
            >
              <option value="standard_2page">
                {isBn ? 'স্ট্যান্ডার্ড ক্লিনিক্যাল রিপোর্ট (২-পেজ PDF)' : 'Standard Clinical Examination Report (2-Page PDF)'}
              </option>
              <option value="compact">
                {isBn ? 'সংক্ষিপ্ত সামারি ফরম্যাট (Compact)' : 'Compact Clinical Summary'}
              </option>
            </select>
          </label>

          <div className="settings-grid-two" style={{ marginTop: '4px' }}>
            <div
              role="switch"
              tabIndex={0}
              aria-checked={settings.includeXaiInReport}
              className={`toggle-tile ${settings.includeXaiInReport ? 'is-checked' : ''}`}
              onClick={() => updateAndSave({ includeXaiInReport: !settings.includeXaiInReport })}
              onKeyDown={e => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  updateAndSave({ includeXaiInReport: !settings.includeXaiInReport })
                }
              }}
            >
              <div className="toggle-tile__copy">
                <strong>{isBn ? 'XAI Attribution এভিডেন্স' : 'Include XAI Attribution'}</strong>
                <span>{isBn ? 'রিপোর্টে Integrated Gradients ওভারলে দেখান' : 'Show Integrated Gradients heatmap in PDF report'}</span>
              </div>
              <span className="switch-pill" aria-hidden="true" />
            </div>

            <div
              role="switch"
              tabIndex={0}
              aria-checked={settings.includeSegInReport}
              className={`toggle-tile ${settings.includeSegInReport ? 'is-checked' : ''}`}
              onClick={() => updateAndSave({ includeSegInReport: !settings.includeSegInReport })}
              onKeyDown={e => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  updateAndSave({ includeSegInReport: !settings.includeSegInReport })
                }
              }}
            >
              <div className="toggle-tile__copy">
                <strong>{isBn ? 'Lesion Segmentation এভিডেন্স' : 'Include Lesion Segmentation'}</strong>
                <span>{isBn ? 'রিপোর্টে সেগমেন্টেশন মাস্ক সেকশন দেখান' : 'Show lesion boundary mask section when available'}</span>
              </div>
              <span className="switch-pill" aria-hidden="true" />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
