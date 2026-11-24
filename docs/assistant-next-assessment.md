# Possible next assessment considerations for skin lesions

Educational decision-support reference. Checked 2026-11-23. These are conditional
considerations for a qualified clinician, not a model-predicted management plan.
Local pathways and patient factors govern actual care. UK guidance is identified
as UK guidance and is not automatically a Bangladesh referral rule.

## Start with missing clinical information
Before discussing a next assessment, clarify lesion duration, evolution, symptoms,
relevant history, examination findings, anatomical site and clinician concern.
The classifier receives limited inputs and cannot establish these facts. Ask for
missing information rather than inventing it. Low model confidence alone is not a
validated biopsy or referral rule. A benign leading class does not rule out malignancy.
This paragraph defines the application's evidence requirements, not a medical guideline.

## Clinician-performed dermoscopy
NICE NG14 describes assessment of referred pigmented lesions in secondary or tertiary
care using dermoscopy by appropriately trained healthcare professionals. The chatbot
may describe that assessment option, while distinguishing an automated image score
from a clinical dermoscopic examination.
Source: https://www.nice.org.uk/guidance/ng14/chapter/recommendations
Scope: UK specialist assessment; paraphrased educational summary.

## Selected monitoring and baseline photography
NG14 describes baseline photography and a review at three months for a clinically
atypical melanocytic lesion judged not to require excision at first specialist
presentation. This selected pathway must not be offered as routine monitoring of
every suspicious lesion or an alternative to an indicated referral. Selection is
the clinician's responsibility, not a threshold on the model's NV or MEL score.
Source: https://www.nice.org.uk/guidance/ng14/chapter/recommendations

## Referral when melanoma or squamous malignancy is clinically suspected
NICE NG12 provides suspected-cancer pathways for melanoma and consideration of
such referral for a lesion suspicious for squamous cell carcinoma. The pathway
depends on clinical suspicion and the guideline's assessment criteria, not the
model's leading class. The chatbot may explain that specialist assessment is a
possible consideration when the clinician reports suspicion; it must not assign
urgency from a score alone. This is relevant background to MEL and SCCKA, and
does not resolve the subtype of a MAL_OTH prediction.
Source: https://www.nice.org.uk/guidance/ng12/chapter/Recommendations-organised-by-site-of-cancer
Scope: UK referral guidance; clinical criteria must be checked in the original.

## Basal cell carcinoma referral considerations
NG12 generally describes non-urgent referral for suspected BCC, with a suspected-
cancer pathway considered when delay could materially affect outcome, including
concerns related to lesion location or size. The model does not determine these
conditions or confirm BCC. Use local pathways and the clinician's assessment.
Source: https://www.nice.org.uk/guidance/ng12/chapter/Recommendations-organised-by-site-of-cancer

## Tissue diagnosis and other investigations
The assistant may explain that a clinician can consider histological confirmation
when clinically appropriate. It must not instruct that this patient needs biopsy,
select the biopsy technique or provide a treatment plan based on classification.
This is an application boundary; individual investigation choices require the
relevant clinical guideline and professional assessment.

## Broad or unresolved labels
BEN_OTH, INF, MAL_OTH and VASC are grouped labels. They do not select one disease,
organism, medication, investigation or next action. For NV, BKL, DF and AKIEC, an
image label similarly cannot determine whether reassurance, monitoring, referral
or investigation is appropriate for the individual. Ask what the clinician found
and cite an applicable source before explaining a conditional assessment option.
Taxonomy: https://challenge.isic-archive.com/landing/milk10k/
