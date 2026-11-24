# Skin lesion class reference

Educational reference summaries for retrieval, not treatment guidelines. The class
mapping follows the official MILK10k benchmark:
https://challenge.isic-archive.com/landing/milk10k/
Checked 2026-11-23. Source descriptions are paraphrased; images are not included.
Do not infer that a feature described here was detected in the current image.

## AKIEC — Actinic keratosis and intraepidermal carcinoma
AKIEC combines actinic keratosis and intraepidermal carcinoma in the benchmark.
It is a grouped classification label, not one histological diagnosis. NCI discusses
actinic keratosis alongside keratinocyte skin cancers; clinical interpretation
requires examination and, when indicated by the clinician, further investigation.
Reference: https://www.cancer.gov/types/skin/hp/skin-treatment-pdq

## BCC — Basal cell carcinoma
BCC is basal cell carcinoma, a keratinocyte skin cancer. NCI distinguishes it from
squamous cell carcinoma and melanoma. A model score does not confirm pathology,
and this reference does not determine stage or treatment.
Reference: https://www.cancer.gov/types/skin/hp/skin-treatment-pdq

## BEN_OTH — Other benign proliferations
BEN_OTH is the benchmark's other-benign group, including collision tumors. The
label covers multiple entities and cannot identify a specific constituent lesion.
Use the official taxonomy rather than interpreting it as a specific disease.
Reference: https://challenge.isic-archive.com/landing/milk10k/

## BKL — Benign keratinocytic lesion
BKL is a grouped benign keratinocytic label. Seborrhoeic keratosis is a common
benign skin growth discussed by DermNet; it can resemble malignant lesions.
Its described dermoscopic structures are reference information, not findings
established by this classifier. Do not equate every BKL result with one subtype.
Reference: https://dermnetnz.org/topics/seborrhoeic-keratosis

## DF — Dermatofibroma
DF denotes dermatofibroma. DermNet describes a benign fibrous skin lesion, often
firm and sometimes showing dimpling with lateral compression. Those examination
features cannot be established by a model class score or attribution map.
Reference: https://dermnetnz.org/topics/dermatofibroma

## INF — Inflammatory and infectious conditions
INF combines inflammatory and infectious conditions in the benchmark. It is not
one infection, organism or inflammatory diagnosis. The category alone cannot
justify antimicrobial or anti-inflammatory medication selection.
Reference: https://challenge.isic-archive.com/landing/milk10k/

## MAL_OTH — Other malignant proliferations
MAL_OTH is the other-malignant group, including collision tumors. It is distinct
from the separately named melanoma, BCC and SCCKA classes. A prediction cannot
resolve its histological subtype or establish a treatment plan.
Reference: https://challenge.isic-archive.com/landing/milk10k/

## MEL — Melanoma
MEL denotes melanoma, a malignancy of melanocytes. The NCI reference discusses
melanoma separately from keratinocyte cancers. Classification output does not
establish invasion, stage, prognosis or management. The PDQ summary is evidence
information rather than a formal guideline or an automatic decision rule.
Reference: https://www.cancer.gov/types/skin/hp/melanoma-treatment-pdq

## NV — Melanocytic nevus
NV denotes melanocytic nevus, also called a mole. DermNet describes a benign
proliferation of melanocytes. Nevi have different clinical forms; some lesions can
resemble melanoma. Neither a benign label nor a model score rules out disease.
Reference: https://dermnetnz.org/topics/melanocytic-naevus

## SCCKA — Squamous cell carcinoma and keratoacanthoma
SCCKA groups squamous cell carcinoma with keratoacanthoma in the MILK10k taxonomy.
The class should not be interpreted as a confirmed choice between its components.
NCI provides background on cutaneous SCC; model output alone does not establish
histology, invasion or the appropriate intervention.
References: https://challenge.isic-archive.com/landing/milk10k/
https://www.cancer.gov/types/skin/hp/skin-treatment-pdq

## VASC — Vascular lesions and hemorrhage
VASC groups vascular lesions and hemorrhage in the benchmark. It must not be
treated as synonymous with a single angioma subtype. DermNet's benign-lesion
reference discusses angiomas, but that does not identify the patient's lesion
from a VASC score.
References: https://challenge.isic-archive.com/landing/milk10k/
https://dermnetnz.org/topics/benign-skin-lesions
