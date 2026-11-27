import {
  BookOpen,
  HelpCircle,
  Image,
  Mail,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { loadClinicSettings } from '../../services/settings'

export function HelpPage() {
  const isBn = loadClinicSettings().language === 'bn'

  return (
    <div className="reports-page workspace-narrow">
      <div className="clinical-page-heading">
        <div>
          <div className="eyebrow">{isBn ? 'ব্যবহারবিধি ও ক্লিনিক্যাল গাইড' : 'Documentation & clinical guidance'}</div>
          <h1>{isBn ? 'সাহায্য (Help)' : 'Help'}</h1>
          <p>
            {isBn
              ? 'ক্লিনিক্যাল ওয়ার্কফ্লো, এআই রেজাল্ট বোঝা, ছবির মানদণ্ড, FAQ এবং নিরাপত্তা নির্দেশিকা।'
              : 'Workflow guide, AI result interpretation, image quality rules, FAQs, and safety limitations.'}
          </p>
        </div>
      </div>

      {/* 1. How to Use */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><BookOpen size={20} /></span>
            <div>
              <h2>{isBn ? '১. ব্যবহারবিধি (How to Use)' : '1. How to Use'}</h2>
              <p>{isBn ? 'ছবি আপলোড থেকে PDF রিপোর্ট তৈরি পর্যন্ত ৪টি ধাপ' : 'End-to-end clinical workflow from image upload to PDF report'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div className="help-steps">
          <div className="help-step">
            <span className="help-step__num">01</span>
            <strong>Image Upload</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'ড্যাশবোর্ডে ডার্মোস্কোপিক ছবি আপলোড করুন এবং চাইলে লেশন অংশ ক্রপ করুন।' : 'Upload a dermoscopic or clinical image on Dashboard and select ROI.'}
            </p>
          </div>
          <div className="help-step">
            <span className="help-step__num">02</span>
            <strong>Analysis</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'রোগীর নাম, আইডি, বয়স, লিঙ্গ ও অবস্থান দিয়ে Start classification চাপুন।' : 'Enter patient details and click Start classification for DermFM inference.'}
            </p>
          </div>
          <div className="help-step">
            <span className="help-step__num">03</span>
            <strong>Doctor Review</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'Classification, XAI ও Uncertainty যাচাই করে Make Report-এ ক্লিক করুন।' : 'Inspect Classification, XAI, and Uncertainty, then click Make Report.'}
            </p>
          </div>
          <div className="help-step">
            <span className="help-step__num">04</span>
            <strong>Report</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'ABCDE ও ক্লিনিক্যাল নোট দিয়ে Save করুন এবং Reports থেকে PDF ডাউনলোড করুন।' : 'Document findings, save to database, and open or download PDF in Reports.'}
            </p>
          </div>
        </div>
      </section>

      {/* 2. Understanding AI Results */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><Sparkles size={20} /></span>
            <div>
              <h2>{isBn ? '২. এআই রেজাল্ট বোঝার নিয়ম (Understanding AI Results)' : '2. Understanding AI Results'}</h2>
              <p>{isBn ? 'Classification, XAI, Segmentation এবং Uncertainty সিগন্যাল' : 'How to read Classification, XAI, Segmentation, and Uncertainty outputs'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div className="settings-grid-two">
          <div className="help-step">
            <strong style={{ color: 'var(--color-sage)' }}>Classification</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? '১১টি লেশন ক্লাসে (যেমন MEL, BCC, NV) মডেলের স্কোর ও শীর্ষ প্রেডিকশন দেখায়।' : 'Shows relative model scores across 11 skin lesion classes and the leading prediction.'}
            </p>
          </div>
          <div className="help-step">
            <strong style={{ color: 'var(--color-sage)' }}>XAI (Attribution)</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'Integrated Gradients হিটম্যাপ দেখায় ছবির কোন অংশ মডেলের সিদ্ধান্তে বেশি প্রভাব ফেলেছে।' : 'Integrated Gradients highlights image regions and metadata features influencing the score.'}
            </p>
          </div>
          <div className="help-step">
            <strong style={{ color: 'var(--color-sage)' }}>Segmentation</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'লেশনের সীমানা (mask) চিহ্নিত করে; এটি পিক্সেল মাস্ক, সরাসরি মাপ (mm) নয়।' : 'Identifies lesion boundary mask when enabled; pixel mask is not a calibrated mm measurement.'}
            </p>
          </div>
          <div className="help-step">
            <strong style={{ color: 'var(--color-sage)' }}>Uncertainty</strong>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--muted)' }}>
              {isBn ? 'Top-two Margin, Entropy ও Ensemble Agreement দিয়ে কনফিডেন্স বোঝায়।' : 'Top-two Margin, Normalized Entropy, and 5-fold Ensemble Agreement reflect model certainty.'}
            </p>
          </div>
        </div>
      </section>

      {/* 3. Image Guidelines */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><Image size={20} /></span>
            <div>
              <h2>{isBn ? '৩. ছবির মানদণ্ড (Image Guidelines)' : '3. Image Guidelines'}</h2>
              <p>{isBn ? 'সঠিক বিশ্লেষণের জন্য ফরম্যাট ও কোয়ালিটি নিয়মাবলী' : 'Supported file formats and capture quality requirements'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div className="settings-grid-two" style={{ fontSize: '13.5px' }}>
          <div className="help-step">
            <strong>{isBn ? 'সাপোর্টেড ফরম্যাট' : 'Supported Images'}</strong>
            <ul style={{ margin: '4px 0 0', paddingLeft: '18px', color: 'var(--muted)', display: 'grid', gap: '4px' }}>
              <li>JPG, PNG, or WebP format</li>
              <li>Maximum file size: 20 MB</li>
              <li>Dermoscopic or focused close-up clinical photo</li>
            </ul>
          </div>
          <div className="help-step">
            <strong>{isBn ? 'কোয়ালিটি শর্তাবলী' : 'Quality Requirements'}</strong>
            <ul style={{ margin: '4px 0 0', paddingLeft: '18px', color: 'var(--muted)', display: 'grid', gap: '4px' }}>
              <li>Sharp focus on the lesion with even lighting</li>
              <li>Avoid heavy glare, motion blur, or ruler occlusion</li>
              <li>Center the full lesion with small surrounding skin margin</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 4. FAQs & Support */}
      <section className="settings-card">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><HelpCircle size={20} /></span>
            <div>
              <h2>{isBn ? '৪. সাধারণ প্রশ্ন ও সাপোর্ট (FAQs & Support)' : '4. FAQs & Support'}</h2>
              <p>{isBn ? 'সচরাচর জিজ্ঞাসিত প্রশ্ন, ট্রাবলশুটিং ও সাপোর্ট যোগাযোগ' : 'Common questions, troubleshooting tips, and support contact'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <div style={{ display: 'grid', gap: '10px' }}>
          <details className="help-faq">
            <summary>Why does classification take 30–60 seconds?</summary>
            <p>When running on CPU, the 5-fold DermFM ensemble with Test-Time Augmentation (TTA) evaluates multiple views for higher accuracy.</p>
          </details>
          <details className="help-faq">
            <summary>Why are only 5 reports shown in Reports?</summary>
            <p>The database automatically retains the 5 most recently saved clinical reports. You can edit, search, or download any of them as PDF.</p>
          </details>
          <details className="help-faq">
            <summary>What if XAI or Segmentation does not appear in the PDF report?</summary>
            <p>Visual AI evidence is included only when generated during analysis and enabled under Settings → Report Preferences.</p>
          </details>
          <div style={{ padding: '12px 14px', border: '1px solid var(--color-line)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13.5px' }}>
            <Mail size={16} style={{ color: 'var(--color-sage)' }} />
            <span><strong>Contact Support:</strong> DermaScope Clinical Engineering Team · support@dermascope.local</span>
          </div>
        </div>
      </section>

      {/* 5. AI Limitations & Safety */}
      <section className="settings-card settings-card--accent">
        <div className="settings-card__header">
          <div className="settings-card__title-group">
            <span className="disclosure-icon"><ShieldAlert size={20} /></span>
            <div>
              <h2 style={{ color: 'var(--color-sage)' }}>{isBn ? '৫. এআই সীমাবদ্ধতা ও নিরাপত্তা (AI Limitations & Safety)' : '5. AI Limitations & Safety'}</h2>
              <p>{isBn ? 'মডেল সীমাবদ্ধতা, OOD সতর্কতা ও ক্লিনিক্যাল রিভিউ নির্দেশিকা' : 'Model boundaries, out-of-distribution warnings, and clinical review obligations'}</p>
            </div>
          </div>
        </div>
        <div className="settings-card__divider" />
        <ul style={{ margin: 0, paddingLeft: '18px', display: 'grid', gap: '7px', fontSize: '13.5px' }}>
          <li><strong>Model Limitations:</strong> AI scores are uncalibrated class probabilities and must never be used as a standalone medical diagnosis.</li>
          <li><strong>OOD Warnings:</strong> Out-of-distribution inputs (non-skin images, tattoos, heavy ink markings, severe blur) can produce unreliable outputs.</li>
          <li><strong>Clinical Review Requirement:</strong> Every case requires independent clinician evaluation, patient history, and biopsy/histopathology when clinically indicated.</li>
        </ul>
      </section>
    </div>
  )
}
