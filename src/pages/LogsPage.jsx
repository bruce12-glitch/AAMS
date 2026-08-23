import React, { useCallback, useMemo, useState } from 'react';
import { Stack, Box, Card, Button, Table, Badge } from '../ui.jsx';
import { api } from '../api/client.js';
import { usePoll } from '../hooks/usePoll.js';

const FILTERS = ['all', 'authorized', 'proxy', 'unpaid', 'unknown', 'spoof', 'tailgate', 'noface'];

export default function LogsPage() {
  const [filter, setFilter] = useState('all');
  const load = useCallback(async () => api.get('/dashboard/activity'), []);
  const { data } = usePoll(load, 5000);
  const rows = data?.activities || [];

  const visible = useMemo(
    () => (filter === 'all' ? rows : rows.filter((r) => r.tag === filter)),
    [rows, filter],
  );

  function exportCsv() {
    const header = ['Time', 'Claimed', 'Recognized', 'Similarity', 'Payment', 'Decision', 'Reason', 'Tag'];
    const body = visible.map((r) => [
      r.event_time, r.claimed_id, r.recognized_id, r.similarity,
      r.payment_status, r.decision, r.reason, r.tag,
    ]);
    const csv = [header, ...body]
      .map((line) => line.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'facepass_entry_logs.csv';
    a.click();
  }

  return (
    <Card variant="default">
      <Stack direction="column" gap="md">
        <Stack direction="row" justify="space-between" align="center">
          <Box>
            <h2>entry_logs</h2>
            <div style={{ fontSize: 13, opacity: 0.7 }}>every attempt · retain 90 days (§26.4)</div>
          </Box>
          <Button variant="secondary" onClick={exportCsv}>Export CSV</Button>
        </Stack>
        <Stack direction="row" gap="sm">
          {FILTERS.map((f) => (
            <Button key={f} variant={filter === f ? 'primary' : 'secondary'} onClick={() => setFilter(f)}>
              {f}
            </Button>
          ))}
        </Stack>
        <Table>
          <Table.Header>
            <Table.Row>
              <Table.Head>Time</Table.Head>
              <Table.Head>Claimed</Table.Head>
              <Table.Head>Recognized</Table.Head>
              <Table.Head>Sim</Table.Head>
              <Table.Head>Payment</Table.Head>
              <Table.Head>Decision</Table.Head>
              <Table.Head>Reason</Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {visible.map((r) => (
              <Table.Row key={r.id}>
                <Table.Cell>{r.event_time}</Table.Cell>
                <Table.Cell>{r.claimed_id || '—'}</Table.Cell>
                <Table.Cell>{r.recognized_id || '—'}</Table.Cell>
                <Table.Cell>{r.similarity != null ? Number(r.similarity).toFixed(2) : '—'}</Table.Cell>
                <Table.Cell>{r.payment_status || '—'}</Table.Cell>
                <Table.Cell>
                  <Badge variant={r.decision === 'GRANTED' ? 'positive' : 'negative'}>{r.decision}</Badge>
                </Table.Cell>
                <Table.Cell>{r.reason}</Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </Stack>
    </Card>
  );
}
