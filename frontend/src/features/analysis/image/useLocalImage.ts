import { useEffect, useRef, useState } from 'react'
import type { Region } from './geometry'
import { regionBounds } from './geometry'

export interface LocalImage { src: string; element: HTMLImageElement; name: string; bytes: number; width: number; height: number }

export function useLocalImage() {
  const [image, setImage] = useState<LocalImage | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const request = useRef(0)
  useEffect(() => () => { request.current++ }, [])
  useEffect(() => () => { if (image) URL.revokeObjectURL(image.src) }, [image])

  function load(file: File) {
    const id = ++request.current
    setError('')
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setLoading(false); setError('Choose a JPG, PNG or WebP image.'); return
    }
    if (file.size > 20 * 1024 * 1024) {
      setLoading(false); setError('The image must be smaller than 20 MB.'); return
    }
    setLoading(true)
    const src = URL.createObjectURL(file)
    const element = new Image()
    element.onload = () => {
      if (id !== request.current) { URL.revokeObjectURL(src); return }
      if (element.naturalWidth * element.naturalHeight > 40_000_000) {
        URL.revokeObjectURL(src); setLoading(false); setError('Choose an image with fewer than 40 million pixels.'); return
      }
      setImage({ src, element, name: file.name, bytes: file.size, width: element.naturalWidth, height: element.naturalHeight })
      setLoading(false)
    }
    element.onerror = () => {
      URL.revokeObjectURL(src)
      if (id === request.current) { setError('This image could not be opened. Try another file.'); setLoading(false) }
    }
    element.src = src
  }

  function clear() { request.current++; setImage(null); setError(''); setLoading(false) }
  return { image, loading, error, load, clear }
}

export function createRegionPreview(image: LocalImage, region: Region): string {
  const bounds = regionBounds(region, image.width, image.height)
  if (bounds.width < 2 || bounds.height < 2) return image.src
  const canvas = document.createElement('canvas')
  canvas.width = bounds.width; canvas.height = bounds.height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Image preview is unavailable in this browser.')
  context.drawImage(image.element, bounds.x, bounds.y, bounds.width, bounds.height, 0, 0, bounds.width, bounds.height)
  return canvas.toDataURL('image/png')
}
