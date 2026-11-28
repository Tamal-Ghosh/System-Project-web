import { ScanLine, Download, MousePointer2, Paintbrush, Eraser, Undo2, RotateCcw, Layers, Contrast, Eye, EyeOff, ChevronDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import './segmentation.css'
import type { LocalImage } from './image/useLocalImage'
import { useAnalysisSession } from './AnalysisSession'
import { segmentLesion, segmentationStatus } from '../../services/segmentation'
import type { SegmentationStatus } from '../../services/segmentation'

export function SegmentationPanel({ image }: { image: LocalImage }) {
  const { site } = useAnalysisSession()
  const [status, setStatus] = useState<SegmentationStatus | null>(null)
  const [expanded,setExpanded]=useState(true)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [visible, setVisible] = useState(false)
  const [hasMask, setHasMask] = useState(false)
  const canvas = useRef<HTMLCanvasElement>(null)
  const mask = useRef<HTMLCanvasElement>(document.createElement('canvas'))
  const request = useRef<AbortController | null>(null)
  const generation = useRef(0)
  const [tool,setTool]=useState<'view'|'paint'|'erase'>('view')
  const [revision,setRevision]=useState(0)
  const painting=useRef<{x:number;y:number}|null>(null)
  const undo=useRef<ImageData[]>([])
  const originalMask=useRef<ImageData|null>(null)
  const [brush,setBrush]=useState(24)
  const [opacity,setOpacity]=useState(45)
  const [display,setDisplay]=useState<'overlay'|'binary'>('overlay')
  const preview=useRef<HTMLDivElement>(null)
  const oversized = image.width * image.height > 4_000_000
  useEffect(() => {
    const check=new AbortController(); request.current?.abort(); generation.current++
    undo.current=[];originalMask.current=null;painting.current=null;setDisplay('overlay');setTool('view');setStatus(null);setBusy(false);setMessage('');setVisible(false);setHasMask(false)
    mask.current.width=image.width;mask.current.height=image.height
    segmentationStatus(check.signal).then(setStatus).catch(()=>{if(!check.signal.aborted)setMessage('Segmentation runtime is unavailable.')})
    return ()=>{check.abort();request.current?.abort();generation.current++}
  },[image])
  useEffect(()=>{
    if(canvas.current){
      canvas.current.width=image.width;canvas.current.height=image.height
      const context=canvas.current.getContext('2d')!
      if(display==='overlay')context.drawImage(mask.current,0,0)
      else {const pixels=mask.current.getContext('2d')!.getImageData(0,0,image.width,image.height);for(let i=0;i<pixels.data.length;i+=4){const value=pixels.data[i+3]>127?255:0;pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=value;pixels.data[i+3]=255}context.putImageData(pixels,0,0)}
    }
  },[image,hasMask,visible,revision,display])
  async function run(){
    if(busy || oversized || !status || status.status==='unavailable')return
    if(hasMask){setVisible(value=>!value);return}
    const current=++generation.current;const controller=new AbortController();request.current=controller
    setBusy(true);setMessage('')
    try{
      const input=document.createElement('canvas');input.width=image.width;input.height=image.height;input.getContext('2d')!.drawImage(image.element,0,0)
      const blob=await new Promise<Blob>((resolve,reject)=>input.toBlob(value=>value?resolve(value):reject(Error('Cannot prepare image.')),'image/png'))
      if(controller.signal.aborted)return
      const response=await segmentLesion(blob,controller.signal,{site})
      if(controller.signal.aborted || current!==generation.current)return
      if(response.width!==image.width || response.height!==image.height)throw Error('Mask dimensions do not match the input image.')
      if(response.status!=='ok'){setMessage(response.reason);return}
      const decoded=new Image();decoded.src=`data:image/png;base64,${response.mask_png}`;await decoded.decode()
      if(controller.signal.aborted || current!==generation.current)return
      const context=mask.current.getContext('2d')!;context.clearRect(0,0,image.width,image.height);context.drawImage(decoded,0,0)
      const pixels=context.getImageData(0,0,image.width,image.height)
      let area=0
      for(let i=0;i<pixels.data.length;i+=4){const inside=pixels.data[i]>127 && pixels.data[i+3]>0;pixels.data[i]=0;pixels.data[i+1]=166;pixels.data[i+2]=145;pixels.data[i+3]=inside?255:0;if(inside)area++}
      context.putImageData(pixels,0,0);originalMask.current=context.getImageData(0,0,image.width,image.height);undo.current=[];setHasMask(true);setVisible(true);requestAnimationFrame(()=>preview.current?.scrollIntoView({block:'center',behavior:'smooth'}))
      if(!area)setMessage('No mask pixels were proposed. This does not rule out a skin condition.')
    }catch(error){if(!controller.signal.aborted)setMessage(error instanceof Error?error.message:'Segmentation failed.')}
    finally{if(current===generation.current)setBusy(false)}
  }
  function draw(event:PointerEvent<HTMLCanvasElement>,start=false){
    if(!visible || tool==='view' || !hasMask || busy || (!start && !painting.current))return
    event.stopPropagation()
    const rect=event.currentTarget.getBoundingClientRect(),x=(event.clientX-rect.left)*image.width/rect.width,y=(event.clientY-rect.top)*image.height/rect.height
    const context=mask.current.getContext('2d')!
    if(start){undo.current.push(context.getImageData(0,0,image.width,image.height));if(undo.current.length>10)undo.current.shift();painting.current={x,y};event.currentTarget.setPointerCapture(event.pointerId)}
    context.globalCompositeOperation=tool==='erase'?'destination-out':'source-over';context.strokeStyle=context.fillStyle='rgb(0,166,145)';context.lineWidth=brush;context.lineCap='round'
    context.beginPath();context.moveTo(painting.current!.x,painting.current!.y);context.lineTo(x,y);context.stroke();context.beginPath();context.arc(x,y,brush/2,0,Math.PI*2);context.fill();context.globalCompositeOperation='source-over';painting.current={x,y};setRevision(n=>n+1)
  }
  function downloadMask(){
    const exported=document.createElement('canvas');exported.width=image.width;exported.height=image.height
    const context=exported.getContext('2d')!,pixels=mask.current.getContext('2d')!.getImageData(0,0,image.width,image.height)
    for(let i=0;i<pixels.data.length;i+=4){const value=pixels.data[i+3]>127?255:0;pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=value;pixels.data[i+3]=255}
    context.putImageData(pixels,0,0);exported.toBlob(blob=>{if(!blob)return;const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='lesion-mask.png';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)},'image/png')
  }

  const reason=oversized?'Segmentation supports up to 4 million pixels.':status?.status==='unavailable'?status.reason:message
  return <section className="segmentation-panel segmentation-workbench" aria-label="Lesion segmentation">
    <header className="seg-workbench-header">
      <div className="seg-workbench-title"><span className="seg-workbench-icon"><ScanLine size={21} /></span><div><h2>Lesion segmentation</h2><p>Generate a mask, then refine the boundary in your own workspace.</p></div></div>
      <div className="seg-header-actions">
        <button type="button" className={`seg-action ${hasMask?'seg-action--secondary':'seg-action--primary'}`} onClick={run} disabled={busy || oversized || !status || status.status==='unavailable'} aria-busy={busy} aria-pressed={hasMask && visible} title={reason || 'Research mask; review the boundary before use.'}>
          {busy?<span className="button-spinner" aria-hidden="true" />:hasMask?(visible?<EyeOff size={16} />:<Eye size={16} />):<ScanLine size={16} />}
          <span>{busy?'Segmenting...':hasMask && visible?'Hide segmentation':hasMask?'Show segmentation':'Generate mask'}</span>
        </button>
        {hasMask && <button type="button" className="seg-action seg-action--primary" disabled={busy} onClick={downloadMask}><Download size={16} />Download mask</button>}
        <button type="button" className="seg-collapse-toggle" aria-label={expanded?'Collapse segmentation':'Expand segmentation'} aria-expanded={expanded} aria-controls="segmentation-workbench-body" onClick={()=>setExpanded(value=>!value)}><ChevronDown size={20} style={{transform:expanded?'rotate(180deg)':'none',transition:'transform .18s'}} /></button>
      </div>
    </header>
    <div id="segmentation-workbench-body" hidden={!expanded}>
    {reason && <p className="seg-workbench-message" role="status">{reason}</p>}
    {hasMask && <div className="seg-workbench-content">
      <div className="seg-toolbar">
        <div className="seg-edit-group segmentation-tools" role="group" aria-label="Mask editing tools">
          {(['view','paint','erase'] as const).map(value=>{const Icon=value==='view'?MousePointer2:value==='paint'?Paintbrush:Eraser;return <button key={value} type="button" disabled={busy || !visible} aria-pressed={tool===value} onClick={()=>setTool(value)}><Icon size={16} />{value==='view'?'View':value==='paint'?'Add to mask':'Erase'}</button>})}
        </div>
        <div className="seg-history-group segmentation-tools" role="group" aria-label="Mask edit history">
          <button type="button" disabled={busy || !undo.current.length} onClick={()=>{const previous=undo.current.pop();if(previous){mask.current.getContext('2d')!.putImageData(previous,0,0);setRevision(n=>n+1)}}}><Undo2 size={16} />Undo</button>
          <button type="button" disabled={busy} onClick={()=>{if(originalMask.current){mask.current.getContext('2d')!.putImageData(originalMask.current,0,0);undo.current=[];setRevision(n=>n+1)}}}><RotateCcw size={16} />Reset model mask</button>
        </div>
      </div>
      <div className="seg-display-row">
        <div className="seg-display-toggle segmentation-tools" role="group" aria-label="Mask display">
          <button type="button" aria-pressed={display==='overlay'} onClick={()=>{setDisplay('overlay');setVisible(true)}}><Layers size={15} />Overlay</button>
          <button type="button" aria-pressed={display==='binary'} onClick={()=>{setDisplay('binary');setVisible(true)}}><Contrast size={15} />Black &amp; white mask</button>
        </div>
        <span className="seg-mask-legend">{display==='binary'?<><i className="seg-swatch-white" />Masked region<i className="seg-swatch-black" />Background</>:<><i className="seg-swatch-teal" />Mask overlay</>}</span>
      </div>
      <div className="seg-adjustments">
        <label className={tool==='view'?'is-inactive':''}><span>Brush size<strong>{brush}<small>px</small></strong></span><input disabled={tool==='view' || !visible} aria-label="Segmentation brush size" type="range" min="2" max="100" value={brush} onChange={e=>setBrush(Number(e.target.value))} /></label>
        <label className={display==='binary'?'is-inactive':''}><span>Mask opacity<strong>{opacity}<small>%</small></strong></span><input disabled={display==='binary'} aria-label="Segmentation mask opacity" type="range" min="0" max="100" value={opacity} onChange={e=>setOpacity(Number(e.target.value))} /></label>
      </div>
      <div ref={preview} className="segmentation-preview" aria-label="Independent segmentation preview">
        <img src={image.element.src} alt="Uploaded image for segmentation review" />
        <canvas ref={canvas} aria-label="Segmentation mask editor" onPointerDown={event=>draw(event,true)} onPointerMove={event=>draw(event)} onPointerUp={()=>{painting.current=null}} onPointerCancel={()=>{painting.current=null}} style={{visibility:visible?'visible':'hidden',opacity:display==='binary'?1:opacity/100,touchAction:tool==='view'?'auto':'none',cursor:tool==='view'?'default':'crosshair',pointerEvents:tool==='view'?'none':'auto'}} />
      </div>
      <p className="seg-edit-hint">{!visible?'Mask hidden. Show segmentation to continue editing.':tool==='view'?'Choose Add to mask or Erase to refine the boundary.':tool==='paint'?'Draw on the image to add to the mask. Undo restores your previous stroke.':'Draw on the image to remove from the mask. Undo restores your previous stroke.'}</p>
    </div>}
    </div>
  </section>
}
