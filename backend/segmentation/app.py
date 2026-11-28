"""Internal segmentation-only sidecar. Does not load the DermFM classifier or chatbot."""
import os
import torch
from fastapi import FastAPI
from .routes import segmentation_router
torch.set_num_threads(max(1, min(8, int(os.getenv('TORCH_THREADS', '4')))))
app = FastAPI(title='DermScope lesion segmentation')
app.include_router(segmentation_router())
