# DermaInsight AI: Clinical Research & Skin Lesion Analysis Platform

DermaInsight AI is a modern clinical decision-support web application for dermatological skin lesion screening and research. Powered by a PyTorch **ResNet50** deep convolutional neural network trained on the **HAM10000** dataset, the system integrates **Uncertainty Quantification (Monte Carlo Dropout)**, **Explainable AI (Grad-CAM)**, **Lesion Boundary Segmentation**, and an **Interactive AI Clinical Assistant**.

---

## 🌟 Key Features

1. **Skin Lesion Classification (HAM10000 7-Class Model)**
   - **Architecture:** PyTorch ResNet50 with custom classification head (`Dropout(0.4) -> Linear(2048, 512) -> ReLU -> BatchNorm1d(512) -> Dropout(0.2) -> Linear(512, 7)`).
   - **Trained Performance:** 71.3% Balanced Accuracy (Epoch 36).
   - **Class Coverage:**
     - `akiec` — Actinic Keratoses & Intraepithelial Carcinoma
     - `bcc` — Basal Cell Carcinoma
     - `bkl` — Benign Keratosis-like Lesions
     - `df` — Dermatofibroma
     - `mel` — Melanoma
     - `nv` — Melanocytic Nevi
     - `vasc` — Vascular Lesions

2. **Uncertainty Quantification & Predictability**
   - **Monte Carlo Dropout (Epistemic Uncertainty):** Measures stochastic model disagreement over test-time passes.
   - **Normalized Predictive Entropy:** Shannon entropy metric evaluating decision ambiguity.
   - **Separation Margin:** Probability difference between top prediction and runner-up.
   - **Clinical Reliability Tiers:** Dynamic categorization into `High`, `Moderate`, or `Low` reliability with evidence-based recommendations.

3. **Explainable AI (Grad-CAM)**
   - High-resolution visual explanation extracted from ResNet50's final convolutional layer (`layer4[-1].conv3`).
   - Interactive dual-view comparison and smooth opacity slider.

4. **Lesion Boundary Segmentation & Morphometrics**
   - Adaptive Otsu thresholding with morphological boundary smoothing.
   - Clinical shape analysis: Area ($px$), Perimeter ($px$), and Isoperimetric Circularity Index ($4\pi \times \frac{\text{Area}}{\text{Perimeter}^2}$) for ABCDE asymmetry screening.

5. **Interactive Lesion Annotation Canvas**
   - Draw or box specific Regions of Interest (ROI) directly on uploaded dermoscopic imagery before running inference.

6. **AI Clinical Decision-Support Assistant**
   - Interactive research chatbot grounded in model confidence, Grad-CAM rationale, and clinical guidelines.

---

## 🏗️ Architecture & Technology Stack

- **Frontend:** React 18, TypeScript, Tailwind CSS, Lucide Icons, Vite
- **Backend:** Python FastAPI, PyTorch, Torchvision, OpenCV, NumPy, Pydantic
- **Deployment & Networking:** Cloudflare Tunnel (`cloudflared`), Uvicorn ASGI

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PyTorch with CUDA or CPU support

### 1. One-Click Launch (Windows)
Double-click [`start_app.bat`](./start_app.bat) in the root directory to automatically launch both backend (port 8000) and frontend (port 3000).

To create a public HTTPS Cloudflare tunnel for external sharing, double-click [`share_online.bat`](./share_online.bat).

### 2. Manual Setup

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 3000
```

Open your browser at:
- **Web Application:** `http://localhost:3000`
- **Swagger API Docs:** `http://localhost:8000/docs`

---

## ⚠️ Disclaimer
DermaInsight AI is a research decision-support prototype intended for educational and investigational purposes. It is **not** an autonomous diagnostic device and all outputs require review by a certified healthcare professional.