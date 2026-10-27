import { historyCount } from '../utils/records'

export default function RecordScope({ scope, onChange, counts }) {
  const older = historyCount(counts)
  return (
    <div className="record-scope">
      <label>Records
        <select value={scope} onChange={(event) => onChange(event.target.value)}>
          <option value="recorded">Current recorded events</option>
          <option value="history">Older / unverified records</option>
          <option value="all">All records</option>
        </select>
      </label>
      <p>{scope === 'recorded'
        ? `${older} older or demo record${older === 1 ? '' : 's'} kept separately. Nothing has been deleted.`
        : 'Older records lack capture provenance; demo records are examples, not security evidence. Original records are preserved.'}</p>
    </div>
  )
}
