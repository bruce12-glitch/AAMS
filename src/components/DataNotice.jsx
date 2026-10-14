export default function DataNotice({ error, loading = false }) {
  if (error) return <div className="form-error" role="alert">Could not refresh data: {error}. Previously loaded data may be out of date.</div>
  if (loading) return <p role="status" className="alert-time">Loading current data…</p>
  return null
}
