export interface Point { x: number; y: number }
export interface Region { kind: 'rectangle' | 'freehand'; points: Point[] }
export interface Bounds { x: number; y: number; width: number; height: number }

export function regionBounds(region: Region, width: number, height: number): Bounds {
  const xs = region.points.map(point => Math.max(0, Math.min(width, point.x)))
  const ys = region.points.map(point => Math.max(0, Math.min(height, point.y)))
  const x = Math.floor(Math.min(...xs)), y = Math.floor(Math.min(...ys))
  return { x, y, width: Math.min(width, Math.ceil(Math.max(...xs))) - x, height: Math.min(height, Math.ceil(Math.max(...ys))) - y }
}

export function clampPoint(point: Point, width: number, height: number): Point {
  return { x: Math.max(0, Math.min(width, point.x)), y: Math.max(0, Math.min(height, point.y)) }
}
