// Copies each column header's text onto its cells as data-label, so on phones/tablets
// the CSS can show "Label: value" cards instead of a wide table. Runs once for the whole app.
function labelTables() {
  document.querySelectorAll('.table-wrap table').forEach((table) => {
    const heads = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent.trim())
    table.querySelectorAll('tbody tr').forEach((tr) => {
      Array.from(tr.children).forEach((td, i) => {
        if (td.tagName !== 'TD' || td.colSpan > 1) return
        const text = heads[i] || ''
        if (td.getAttribute('data-label') !== text) td.setAttribute('data-label', text)
      })
    })
  })
}

let queued = false
function schedule() {
  if (queued) return
  queued = true
  requestAnimationFrame(() => { queued = false; labelTables() })
}

export function startTableLabels() {
  // childList only (not attributes), so setting data-label never re-triggers the observer.
  new MutationObserver(schedule).observe(document.body, { childList: true, subtree: true })
  schedule()
}
