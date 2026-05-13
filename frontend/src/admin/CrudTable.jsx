import { useEffect, useState } from 'react'
import { adminApi } from '../lib/api.js'

/**
 * Generic CRUD list/edit screen.
 *
 * Props:
 *   resource: backend endpoint slug, e.g. 'age-bands'
 *   title: human label
 *   fields: [{key, label, type:'text'|'number'|'json'|'select', options?:[{value,label}]}]
 */
export default function CrudTable({ resource, title, fields }) {
  const [rows, setRows] = useState([])
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null)

  async function reload() {
    try { setRows(await adminApi.list(resource)) }
    catch (e) { setError(e.message) }
  }

  useEffect(() => { reload() }, [resource])

  function emptyDraft() {
    const d = {}
    fields.forEach((f) => { d[f.key] = f.type === 'number' ? 0 : f.type === 'json' ? {} : '' })
    return d
  }

  async function save(draft) {
    setError(null)
    try {
      if (draft.id) await adminApi.update(resource, draft.id, stripId(draft))
      else await adminApi.create(resource, stripId(draft))
      setEditing(null)
      reload()
    } catch (e) { setError(e.message) }
  }

  async function remove(id) {
    if (!confirm('Delete?')) return
    try { await adminApi.remove(resource, id); reload() } catch (e) { setError(e.message) }
  }

  return (
    <div className="crud">
      <header className="crud-header">
        <h2>{title}</h2>
        <button onClick={() => setEditing(emptyDraft())}>+ New</button>
      </header>
      {error && <div className="auth-error">{error}</div>}
      <table className="crud-table">
        <thead>
          <tr>
            {fields.map((f) => <th key={f.key}>{f.label}</th>)}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              {fields.map((f) => <td key={f.key}>{renderCell(r[f.key])}</td>)}
              <td>
                <button onClick={() => setEditing({ ...r })}>Edit</button>
                <button onClick={() => remove(r.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editing && <Editor fields={fields} value={editing} onCancel={() => setEditing(null)} onSave={save} />}
    </div>
  )
}

function Editor({ fields, value, onCancel, onSave }) {
  const [draft, setDraft] = useState(value)
  return (
    <form className="crud-editor" onSubmit={(e) => { e.preventDefault(); onSave(draft) }}>
      {fields.map((f) => (
        <label key={f.key}>{f.label}
          {f.type === 'select'
            ? <select value={draft[f.key] ?? ''} onChange={(e) => setDraft({...draft, [f.key]: e.target.value})}>
                <option value="">—</option>
                {(f.options || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            : f.type === 'json'
              ? <textarea rows={4} value={JSON.stringify(draft[f.key] ?? {}, null, 2)}
                  onChange={(e) => { try { setDraft({...draft, [f.key]: JSON.parse(e.target.value)}) } catch { /* ignore */ } }} />
              : <input type={f.type || 'text'} value={draft[f.key] ?? ''}
                  onChange={(e) => setDraft({...draft, [f.key]: f.type === 'number' ? Number(e.target.value) : e.target.value})} />
          }
        </label>
      ))}
      <div className="row">
        <button type="submit">Save</button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}

function stripId(d) { const { id, ...rest } = d; return rest }
function renderCell(v) {
  if (v === null || v === undefined) return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
