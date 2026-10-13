import { createContext, useCallback, useContext, useState } from 'react'
import Icon from './Icon'

const ToastContext = createContext(null)

// const toast = useToast();  toast('Saved'), toast('Oops', 'error')
export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const toast = useCallback((message, tone = 'success') => {
    const id = Math.random().toString(36).slice(2)
    setItems((prev) => [...prev.slice(-2), { id, message, tone }])
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 3200)
  }, [])
  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast toast-${t.tone}`}>
            <Icon name={t.tone === 'error' ? 'alert' : 'check'} size={16} /> {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}
