"""Validate doctor-supplied prompts; never guess the lesion or anatomical site."""
import json
import math
from dermfm.loader import SITES

def validate_context(image_type,site='unknown',allow_unspecified=False):
    if image_type not in ('clinical','dermoscopic') and not (allow_unspecified and image_type=='unspecified'):
        raise ValueError('Select Clinical photograph or Dermoscopic image before segmentation.')
    if site not in (*SITES,'unknown'):raise ValueError('Choose a supported anatomical site or Unknown.')

def validate_prompt(image, box, image_type, site='unknown'):
    validate_context(image_type,site)
    try: coordinates=json.loads(box) if isinstance(box,str) else box
    except (ValueError,TypeError):raise ValueError('The lesion box must contain four image coordinates.') from None
    if not isinstance(coordinates,(list,tuple)) or len(coordinates)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in coordinates):
        raise ValueError('Draw a rectangle around the target lesion before segmentation.')
    x1,y1,x2,y2=coordinates
    if not (0<=x1<x2<=image.width and 0<=y1<y2<=image.height) or x2-x1<2 or y2-y1<2:
        raise ValueError('The lesion box must lie inside the image and be at least two pixels wide and high.')
    if site not in (*SITES,'unknown'):raise ValueError('Choose a supported anatomical site or Unknown.')
    return {'box':[float(x) for x in coordinates],'image_type':image_type,'site':site}
