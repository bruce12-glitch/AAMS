import { useState } from 'react'
import { adminPost, apiPut } from '../api/client'
import { isSrmistEmail, normalizeEmail } from '../auth/srmAuth'
import { useDialog } from '../hooks/useDialog'

export default function StudentModal({ student, onClose, onSaved }) {
  const editing = Boolean(student)
  const [form, setForm] = useState({
    user_id: student?.user_id ?? '', name: student?.name ?? '',
    email: student?.email ?? '', phone: student?.phone ?? '',
    department: student?.department ?? '', year: student?.year ?? '',
    section: student?.section ?? '', user_type: student?.user_type ?? 'student',
    payment_status: student?.payment_status ?? 'active',
    payment_expiry: student?.payment_expiry ?? '', active: student?.active ?? 1,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const close = () => { if (!busy) onClose() }
  const dialog = useDialog(true, close)
  const set = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const save = async (event) => {
    event.preventDefault()
    setError('')
    if (!/^[A-Za-z0-9._-]{1,64}$/.test(form.user_id.trim())) return setError('Use a student ID with letters, numbers, dots, dashes or underscores.')
    if (!isSrmistEmail(form.email)) return setError('An @srmist.edu.in email is required.')
    const data = { ...form, name: form.name.trim(), email: normalizeEmail(form.email),
      year: form.year ? Number(form.year) : null, active: Number(form.active),
      payment_expiry: form.payment_expiry || null }
    if (!data.name) return setError('Enter the student’s full name.')
    if (editing) delete data.user_id
    else delete data.active
    setBusy(true)
    try {
      if (editing) await apiPut(`/users/${encodeURIComponent(form.user_id)}`, data)
      else await adminPost('/users', { ...data, user_id: form.user_id.trim() })
      onSaved()
    } catch (err) { setError(err.message || 'Could not save student.') }
    finally { setBusy(false) }
  }
  return (
    <div className="modal-backdrop" onClick={close}>
      <form className="modal" onSubmit={save} onClick={(event) => event.stopPropagation()}
        ref={dialog} role="dialog" aria-modal="true" aria-labelledby="student-title" tabIndex={-1}>
        <h2 className="modal-title" id="student-title">{editing ? 'Edit student' : 'Add student'}</h2>
        <p className="modal-sub">Save contact and academic details. Face enrollment can be added separately.</p>
        <fieldset className="form-grid" disabled={busy}>
          <label>Student ID *<input required value={form.user_id} disabled={editing} onChange={set('user_id')} maxLength={64} /></label>
          <label>Full name *<input required value={form.name} onChange={set('name')} maxLength={120} /></label>
          <label>SRMIST email *<input required type="email" value={form.email} onChange={set('email')} maxLength={254} /></label>
          <label>Phone<input type="tel" value={form.phone} onChange={set('phone')} maxLength={30} /></label>
          <label>Department<input value={form.department} onChange={set('department')} maxLength={120} placeholder="e.g. Computer Science" /></label>
          <label>Year<select value={form.year} onChange={set('year')}><option value="">Not specified</option>{[1, 2, 3, 4, 5, 6].map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
          <label>Section<input value={form.section} onChange={set('section')} maxLength={30} /></label>
          <label>Member type<select value={form.user_type} onChange={set('user_type')}>{['student', 'faculty', 'staff', 'guest'].map((type) => <option key={type}>{type}</option>)}</select></label>
          <label>Payment status<select value={form.payment_status} onChange={set('payment_status')}>{['active', 'pending', 'expired', 'inactive'].map((status) => <option key={status}>{status}</option>)}</select></label>
          <label>Payment expiry<input type="date" value={form.payment_expiry} onChange={set('payment_expiry')} /></label>
          {editing && <label>Account status<select value={form.active} onChange={set('active')}><option value={1}>Active</option><option value={0}>Disabled</option></select></label>}
        </fieldset>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="modal-actions">
          <button className="btn ghost" type="button" onClick={close} disabled={busy}>Cancel</button>
          <button className="btn primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save student'}</button>
        </div>
      </form>
    </div>
  )
}
