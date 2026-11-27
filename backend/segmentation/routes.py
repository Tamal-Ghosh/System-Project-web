import hashlib
import logging
import os
from fastapi import APIRouter, File, HTTPException, UploadFile, Form
from starlette.concurrency import run_in_threadpool
from dermfm.preprocessing import MAX_BYTES, decode_image
from .service import NnUNetService, SegmentationBusy, SegmentationUnavailable

logger = logging.getLogger(__name__)

def segmentation_router(service=None):
    if service is None:
        from .proxy import RemoteSegmentationService
        url = os.environ.get('SEGMENTATION_SERVICE_URL', '')
        provider = os.environ.get('SEGMENTATION_PROVIDER', 'segformer_b2')
        if url:
            service = RemoteSegmentationService(url)
        elif provider == 'segformer_b2':
            from .segformer_b2 import SegFormerB2Service
            service = SegFormerB2Service()
        elif provider == 'grounded_sam2':
            from .automatic import AutomaticSegmentationService
            service = AutomaticSegmentationService()
        elif provider == 'sam2':
            from .sam2_service import SAM2Service
            service = SAM2Service()
        elif provider == 'nnunet':
            service = NnUNetService()
        elif provider == 'segformer':
            from .segformer import SegFormerService
            service = SegFormerService()
        else:
            raise ValueError('Unsupported segmentation provider')
    router = APIRouter(prefix='/api/v1/segmentation', tags=['segmentation'])

    @router.get('/status')
    def status():
        return {'method': getattr(service, 'method', 'nnunetv2'), **service.status()}

    @router.post('')
    async def segment(image: UploadFile = File(...), box: str | None = Form(default=None), image_type: str | None = Form(default=None), site: str = Form(default='unknown')):
        contents = await image.read(MAX_BYTES + 1)
        try:
            decoded = await run_in_threadpool(decode_image, contents)
            options = {}
            if getattr(service, 'requires_prompt', False):
                from .prompt import validate_prompt
                options = validate_prompt(decoded, box, image_type, site)
            elif getattr(service, 'requires_image_type', False):
                from .prompt import validate_context
                if image_type is None and getattr(service,'allows_unspecified_type',False):image_type='unspecified'
                validate_context(image_type,site,allow_unspecified=getattr(service,'allows_unspecified_type',False))
                options = {'image_type':image_type,'site':site}
            return await run_in_threadpool(service.predict, decoded, hashlib.sha256(contents).hexdigest(), **options)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except SegmentationBusy as exc:
            raise HTTPException(409, str(exc)) from exc
        except SegmentationUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        except Exception as exc:
            logger.exception('Lesion segmentation failed')
            raise HTTPException(503, 'Segmentation failed. The classifier remains available.') from exc
        finally:
            await image.close()
    return router
