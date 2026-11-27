import { ArrowLeft, CheckCircle2, Save, UserRound } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { loadClinicSettings, saveClinicSettings } from '../../services/settings'

export function ProfilePage() {
  const initial = loadClinicSettings()
  const [name, setName] = useState(initial.defaultClinician)
  const [designation, setDesignation] = useState(initial.clinicianDesignation)
  const [email, setEmail] = useState(initial.clinicianEmail)
  const [clinicName, setClinicName] = useState(initial.clinicName)
  const [clinicAddress, setClinicAddress] = useState(initial.clinicAddress)
  const [clinicContact, setClinicContact] = useState(initial.clinicContact)
  const [saved, setSaved] = useState(false)

  function handleSave(event: FormEvent) {
    event.preventDefault()
    const current = loadClinicSettings()
    saveClinicSettings({
      ...current,
      defaultClinician: name.trim(),
      clinicianDesignation: designation.trim() || 'Consultant Dermatologist',
      clinicianEmail: email.trim(),
      clinicName: clinicName.trim() || current.clinicName,
      clinicAddress: clinicAddress.trim(),
      clinicContact: clinicContact.trim(),
    })
    setSaved(true)
    window.setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="reports-page">
      <div className="clinical-page-heading">
        <div>
          <div className="eyebrow">Clinician account</div>
          <h1>My Profile</h1>
          <p>Manage your clinician identity and hospital/clinic header used in reports.</p>
        </div>
        <Link to="/settings" className="button button--secondary"><ArrowLeft size={16} />Back to settings</Link>
      </div>

      <section className="doctor-assessment" style={{ padding: '20px', marginBottom: '18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div className="avatar" style={{ width: '52px', height: '52px', fontSize: '18px' }}>
            <UserRound size={24} />
          </div>
          <div>
            <strong style={{ fontSize: '17px' }}>{name.trim() || 'Clinician Profile'}</strong>
            <div style={{ color: '#526476', fontSize: '13.5px' }}>
              {designation || 'Consultant Dermatologist'} · {clinicName || 'DermaScope Clinical Unit'}
            </div>
          </div>
        </div>
      </section>

      <form onSubmit={handleSave} className="assessment-form">
        <section className="doctor-assessment" style={{ padding: '20px' }}>
          <h2 style={{ marginTop: 0, fontSize: '15px' }}>Clinician &amp; Clinic Details</h2>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Full name
              <input value={name} maxLength={100} onChange={event => setName(event.target.value)} placeholder="Dr. Full Name" />
            </label>
            <label>
              Designation / Registration No.
              <input value={designation} maxLength={100} onChange={event => setDesignation(event.target.value)} placeholder="Consultant Dermatologist" />
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Email address
              <input type="email" value={email} maxLength={120} onChange={event => setEmail(event.target.value)} placeholder="clinician@hospital.org" />
            </label>
            <label>
              Telephone / Contact
              <input value={clinicContact} maxLength={100} onChange={event => setClinicContact(event.target.value)} placeholder="+880 ..." />
            </label>
          </div>
          <div className="assessment-fields assessment-fields--two">
            <label>
              Hospital / Clinic name
              <input value={clinicName} maxLength={100} onChange={event => setClinicName(event.target.value)} placeholder="DermaScope Clinical Unit" />
            </label>
            <label>
              Clinic address
              <input value={clinicAddress} maxLength={140} onChange={event => setClinicAddress(event.target.value)} placeholder="Department & address" />
            </label>
          </div>

          {saved && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#146C70', fontWeight: 600, marginTop: '10px' }} role="status">
              <CheckCircle2 size={16} /> Profile updated.
            </div>
          )}

          <div className="assessment-actions">
            <p>Profile details automatically pre-fill new examination reports.</p>
            <button type="submit" className="button button--primary"><Save size={15} />Save Profile</button>
          </div>
        </section>
      </form>
    </div>
  )
}
