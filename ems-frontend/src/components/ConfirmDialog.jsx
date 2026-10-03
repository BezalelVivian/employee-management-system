import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import Icon from './Icon'

const ConfirmContext = createContext(null)

// const confirm = useConfirm();  if (await confirm({ title, message, confirmText, danger })) { ... }
export function ConfirmProvider({ children }) {
  const [ask, setAsk] = useState(null)
  const resolver = useRef(null)

  const confirm = useCallback((opts) => new Promise((resolve) => {
    resolver.current = resolve
    setAsk(opts)
  }), [])

  const close = useCallback((answer) => {
    resolver.current?.(answer)
    resolver.current = null
    setAsk(null)
  }, [])

  useEffect(() => {
    if (!ask) return undefined
    const onKey = (e) => { if (e.key === 'Escape') close(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [ask, close])

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {ask && (
        <div className="modal-backdrop confirm-backdrop" onClick={() => close(false)}>
          <div className="modal confirm-box" role="alertdialog" aria-modal="true" aria-label={ask.title} onClick={(e) => e.stopPropagation()}>
            <span className={`confirm-icon ${ask.danger ? 'is-danger' : ''}`}><Icon name={ask.danger ? 'alert' : 'shield'} size={24} /></span>
            <h2>{ask.title || 'Are you sure?'}</h2>
            <p>{ask.message}</p>
            <div className="confirm-actions">
              <button className="btn btn-secondary" onClick={() => close(false)}>Cancel</button>
              <button className={`btn ${ask.danger ? 'btn-danger-solid' : 'btn-primary'}`} onClick={() => close(true)} autoFocus>
                {ask.confirmText || 'OK'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  )
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext)
  if (!ctx) throw new Error('useConfirm must be used inside ConfirmProvider')
  return ctx
}
