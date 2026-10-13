import { useRef, useState } from 'react'
import Avatar from './Avatar'
import Icon from './Icon'
import { fileToAvatarDataUrl } from '../utils/image'
import { useToast } from './Toast'

// Pick a photo -> it shows instantly and saves quietly in the background.
// If the save fails, the old photo comes back and an error is shown.
export default function PhotoPicker({ name, photo, onUpload, onRemove }) {
  const inputRef = useRef(null)
  const toast = useToast()
  const [preview, setPreview] = useState(null) // shown immediately while saving
  const [removed, setRemoved] = useState(false)
  const [saving, setSaving] = useState(false)

  const shown = removed ? null : (preview || photo)

  async function handleFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    try {
      const dataUrl = await fileToAvatarDataUrl(file)
      setPreview(dataUrl); setRemoved(false); setSaving(true)
      await onUpload(dataUrl)
      toast('Photo updated')
    } catch (err) {
      setPreview(null)
      toast(err.message || 'Could not save the photo.', 'error')
    } finally { setSaving(false) }
  }

  async function handleRemove() {
    setRemoved(true); setPreview(null); setSaving(true)
    try {
      await onRemove()
      toast('Photo removed')
    } catch (err) {
      setRemoved(false)
      toast(err.message || 'Could not remove the photo.', 'error')
    } finally { setSaving(false) }
  }

  return (
    <div className="photo-picker">
      <button type="button" className={`photo-drop ${saving ? 'is-saving' : ''}`} onClick={() => inputRef.current?.click()} aria-label="Choose a photo">
        <Avatar name={name} src={shown} size="xl" />
        <span className="photo-drop-badge"><Icon name="camera" size={15} /></span>
      </button>
      <div>
        <div className="photo-actions">
          <button type="button" className="btn btn-primary btn-sm" disabled={saving} onClick={() => inputRef.current?.click()}>
            <Icon name="camera" size={15} /> {shown ? 'Change photo' : 'Upload photo'}
          </button>
          {shown && <button type="button" className="btn btn-secondary btn-sm" disabled={saving} onClick={handleRemove}>Remove</button>}
        </div>
        <p className="hint-text" style={{ marginBottom: 0 }}>
          {saving ? 'Saving in the background…' : 'Pick any photo — it is cropped and saved automatically.'}
        </p>
      </div>
      <input ref={inputRef} type="file" accept="image/*" hidden onChange={handleFile} />
    </div>
  )
}
