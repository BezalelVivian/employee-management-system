// Turns a picked photo into a small square JPEG data URL that fits one Google Sheets cell
// (server accepts up to 42,000 chars). Fast path: one 200px render at good quality (~10 KB);
// only falls back to smaller sizes for unusually detailed photos. All in the browser.

const MAX_INPUT_BYTES = 20 * 1024 * 1024
export const MAX_DATA_URL_CHARS = 38000

async function decode(file) {
  if (typeof createImageBitmap === 'function') {
    try { return await createImageBitmap(file) } catch { /* fall through to <img> */ }
  }
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('That file could not be read as an image.')) }
    img.src = url
  })
}

export async function fileToAvatarDataUrl(file) {
  if (!file) throw new Error('No file selected.')
  if (!file.type.startsWith('image/')) throw new Error('Please choose an image file (JPG, PNG, WebP…).')
  if (file.size > MAX_INPUT_BYTES) throw new Error('That image is over 20 MB. Please choose a smaller one.')

  const img = await decode(file)
  const w = img.width || img.naturalWidth
  const h = img.height || img.naturalHeight
  const side = Math.min(w, h)
  if (!side) throw new Error('That image appears to be empty.')
  const sx = (w - side) / 2
  const sy = (h - side) / 2

  for (const [size, quality] of [[200, 0.82], [200, 0.6], [160, 0.6], [120, 0.5]]) {
    const canvas = document.createElement('canvas')
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, size, size)
    ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size)
    const dataUrl = canvas.toDataURL('image/jpeg', quality)
    if (dataUrl.startsWith('data:image/jpeg') && dataUrl.length <= MAX_DATA_URL_CHARS) return dataUrl
  }
  throw new Error('Could not shrink that image enough. Please try a different photo.')
}
