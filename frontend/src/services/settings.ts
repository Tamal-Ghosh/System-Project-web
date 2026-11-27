export interface ClinicSettings {
  clinicName: string
  clinicAddress: string
  clinicContact: string
  defaultClinician: string
  clinicianDesignation: string
  clinicianEmail: string
  defaultReviewStatus: 'Pending' | 'Signed'
  defaultSafetyAdvice: string
  theme: 'light' | 'dark'
  language: 'en' | 'bn'
  reportFormat: 'standard_2page' | 'compact'
  includeXaiInReport: boolean
  includeSegInReport: boolean
}

const STORAGE_KEY = 'dermascope_clinical_settings_v1'

export const DEFAULT_CLINIC_SETTINGS: ClinicSettings = {
  clinicName: 'DermaScope Clinical Unit',
  clinicAddress: '',
  clinicContact: '',
  defaultClinician: '',
  clinicianDesignation: 'Consultant Dermatologist',
  clinicianEmail: '',
  defaultReviewStatus: 'Pending',
  defaultSafetyAdvice:
    'Advised to monitor for ABCDE changes (asymmetry, border, color, diameter, evolution), bleeding, or ulceration and seek prompt review.',
  theme: 'light',
  language: 'en',
  reportFormat: 'standard_2page',
  includeXaiInReport: true,
  includeSegInReport: true,
}

export function applyTheme(theme: 'light' | 'dark'): void {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme)
  }
}

export function loadClinicSettings(): ClinicSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_CLINIC_SETTINGS
    const parsed = JSON.parse(raw) as Partial<ClinicSettings>
    return {
      clinicName: typeof parsed.clinicName === 'string' && parsed.clinicName.trim() ? parsed.clinicName : DEFAULT_CLINIC_SETTINGS.clinicName,
      clinicAddress: typeof parsed.clinicAddress === 'string' ? parsed.clinicAddress : '',
      clinicContact: typeof parsed.clinicContact === 'string' ? parsed.clinicContact : '',
      defaultClinician: typeof parsed.defaultClinician === 'string' ? parsed.defaultClinician : '',
      clinicianDesignation:
        typeof parsed.clinicianDesignation === 'string' && parsed.clinicianDesignation.trim()
          ? parsed.clinicianDesignation
          : DEFAULT_CLINIC_SETTINGS.clinicianDesignation,
      clinicianEmail: typeof parsed.clinicianEmail === 'string' ? parsed.clinicianEmail : '',
      defaultReviewStatus: parsed.defaultReviewStatus === 'Signed' ? 'Signed' : 'Pending',
      defaultSafetyAdvice:
        typeof parsed.defaultSafetyAdvice === 'string' && parsed.defaultSafetyAdvice.trim()
          ? parsed.defaultSafetyAdvice
          : DEFAULT_CLINIC_SETTINGS.defaultSafetyAdvice,
      theme: parsed.theme === 'dark' ? 'dark' : 'light',
      language: parsed.language === 'bn' ? 'bn' : 'en',
      reportFormat: parsed.reportFormat === 'compact' ? 'compact' : 'standard_2page',
      includeXaiInReport: typeof parsed.includeXaiInReport === 'boolean' ? parsed.includeXaiInReport : true,
      includeSegInReport: typeof parsed.includeSegInReport === 'boolean' ? parsed.includeSegInReport : true,
    }
  } catch {
    return DEFAULT_CLINIC_SETTINGS
  }
}

export function saveClinicSettings(settings: ClinicSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
  applyTheme(settings.theme)
}

export function resetClinicSettings(): ClinicSettings {
  localStorage.removeItem(STORAGE_KEY)
  applyTheme(DEFAULT_CLINIC_SETTINGS.theme)
  return DEFAULT_CLINIC_SETTINGS
}
