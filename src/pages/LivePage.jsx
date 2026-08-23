import React, { useCallback, useState } from 'react';
import { Grid, Stack, Box, Card, Button, Badge, Table } from '../ui.jsx';
import { api } from '../api/client.js';
import { usePoll } from '../hooks/usePoll.js';

const SCENARIOS = [
  { id: 'authorized', label: 'Authorized', hint: 'TC01 · paid member + own QR', variant: 'primary' },
  { id: 'proxy', label: 'Proxy', hint: 'TC05 · Arun scans Rahul’s QR', variant: 'danger' },
  { id: 'unpaid', label: 'Unpaid', hint: 'TC03 · payment expired', variant: 'secondary' },
  { id: 'unknown', label: 'Unknown', hint: 'TC04 · face-only, not enrolled', variant: 'secondary' },
  { id: 'spoof', label: 'Spoof', hint: 'TC08 · printed photo', variant: 'danger' },
  { id: 'tailgate', label: 'Tailgate', hint: 'TC07 · two faces, still grant', variant: 'secondary' },
  { id: 'noface', label: 'No face', hint: 'TC06 · token, empty frame', variant: 'secondary' },
];

function decisionBadge(decision) {
  if (decision === 'GRANTED') return <Badge variant="positive">GRANTED</Badge>;
  if (decision === 'DENIED') return <Badge variant="negative">DENIED</Badge>;
  return <Badge variant="neutral">{decision || '—'}</Badge>;
}

export default function LivePage({ onBusy }) {
  const [lastSim, setLastSim] = useState(null);
  const [simulating, setSimulating] = useState(false);

  const load = useCallback(async () => {
    const [stats, activity, occupants, live] = await Promise.all([
      api.get('/dashboard/stats'),
      api.get('/dashboard/activity'),
      api.get('/occupants'),
      api.get('/dashboard/live'),
    ]);
    return { stats, activity, occupants, live };
  }, []);

  const { data, error, reload } = usePoll(load, 4000);
  const stats = data?.stats || {};
  const activities = data?.activity?.activities || [];
  const occupants = data?.occupants?.occupants || [];
  const live = data?.live || {};
  const current = lastSim || live.current_event;

  async function runScenario(id) {
    setSimulating(true);
    onBusy?.(true);
    try {
      const result = await api.post('/entry/simulate', { scenario: id });
      setLastSim({ ...result, event_time: new Date().toISOString(), scenario: id });
      await reload();
    } catch (err) {
      setLastSim({ decision: 'ERROR', reason: err.message, tag: 'error' });
    } finally {
      setSimulating(false);
      onBusy?.(false);
    }
  }

  async function checkout(userId) {
    await api.post(`/occupants/${encodeURIComponent(userId)}/exit`);
    await reload();
  }

  return (
    <Stack direction="column" gap="md">
      {error && (
        <Card variant="outlined">
          <Badge variant="negative">API offline</Badge>
          <Box marginTop="sm">Could not reach FastAPI via /api. Start the live API (`scripts/start-live.sh`).</Box>
        </Card>
      )}

      <Grid columns={{ base: 1, sm: 2, lg: 4 }} gap="md">
        <Kpi label="Entries today" value={stats.total_entries ?? '—'} tone="neutral" hint="all attempts logged" />
        <Kpi label="Currently inside" value={stats.inside_count ?? '—'} tone="positive" hint="occupants.status = inside" />
        <Kpi label="Open alerts" value={stats.alert_count ?? '—'} tone="negative" hint="unacknowledged" />
        <Kpi label="Active members" value={stats.member_count ?? '—'} tone="attention" hint="paid + active" />
      </Grid>

      <Grid columns={{ base: 1, lg: 2 }} gap="md">
        <Card variant="outlined">
          <Stack direction="column" gap="sm">
            <Stack direction="row" justify="space-between" align="center">
              <h2>Current entry event</h2>
              {decisionBadge(current?.decision)}
            </Stack>
            <Box>
              <strong>{current?.name || current?.recognized_id || 'Awaiting subject'}</strong>
              <div style={{ opacity: 0.7, fontSize: 13, marginTop: 4 }}>
                {current?.reason || 'Stand at marker · face the camera · or run a scenario'}
              </div>
            </Box>
            <Stack direction="row" gap="sm">
              {current?.tag && <Badge variant="neutral">{current.tag}</Badge>}
              {current?.similarity != null && (
                <Badge variant="neutral">cos {Number(current.similarity).toFixed(2)}</Badge>
              )}
              <Badge variant={live.camera?.online ? 'positive' : 'attention'}>
                CAM-01 {live.camera?.online ? 'live' : 'no signal (prototype)'}
              </Badge>
            </Stack>
            <Box style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12, opacity: 0.75 }}>
              pipeline: token → SCRFD → quality → ArcFace → match ≥ 0.45 → blink → payment → §11.2
            </Box>
          </Stack>
        </Card>

        <Card variant="outlined">
          <Stack direction="column" gap="sm">
            <h2>Simulate entry event</h2>
            <Box style={{ fontSize: 13, opacity: 0.75 }}>
              Writes a real row to entry_logs (and alerts / occupants). This is the live prototype loop until the webcam path is wired.
            </Box>
            <Grid columns={{ base: 1, sm: 2 }} gap="sm">
              {SCENARIOS.map((s) => (
                <Button
                  key={s.id}
                  variant={s.variant}
                  disabled={simulating}
                  onClick={() => runScenario(s.id)}
                >
                  {s.label}
                </Button>
              ))}
            </Grid>
            <Box style={{ fontSize: 12, opacity: 0.65 }}>
              {SCENARIOS.find((s) => s.id === lastSim?.scenario)?.hint || 'Pick a test case from the spec (TC01–TC08).'}
            </Box>
          </Stack>
        </Card>
      </Grid>

      <Grid columns={{ base: 1, lg: 2 }} gap="md">
        <Card variant="default">
          <Stack direction="column" gap="sm">
            <h2>Live occupants</h2>
            {occupants.length === 0 ? (
              <Box style={{ opacity: 0.7 }}>Lab is empty.</Box>
            ) : (
              <Table>
                <Table.Header>
                  <Table.Row>
                    <Table.Head>Name</Table.Head>
                    <Table.Head>Entered</Table.Head>
                    <Table.Head></Table.Head>
                  </Table.Row>
                </Table.Header>
                <Table.Body>
                  {occupants.map((o) => (
                    <Table.Row key={o.id || o.user_id}>
                      <Table.Cell>
                        <strong>{o.name || o.user_id}</strong>
                        <div style={{ fontSize: 12, opacity: 0.65 }}>{o.user_id}</div>
                      </Table.Cell>
                      <Table.Cell>{fmtTime(o.entry_time)}</Table.Cell>
                      <Table.Cell>
                        <Button variant="secondary" onClick={() => checkout(o.user_id)}>Exit</Button>
                      </Table.Cell>
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            )}
          </Stack>
        </Card>

        <Card variant="default">
          <Stack direction="column" gap="sm">
            <h2>Recent activity</h2>
            <Table>
              <Table.Header>
                <Table.Row>
                  <Table.Head>Time</Table.Head>
                  <Table.Head>ID</Table.Head>
                  <Table.Head>Decision</Table.Head>
                  <Table.Head>Tag</Table.Head>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {activities.slice(0, 8).map((row) => (
                  <Table.Row key={row.id}>
                    <Table.Cell>{fmtTime(row.event_time)}</Table.Cell>
                    <Table.Cell>{row.recognized_id || row.claimed_id || '—'}</Table.Cell>
                    <Table.Cell>{decisionBadge(row.decision)}</Table.Cell>
                    <Table.Cell>{row.tag}</Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table>
          </Stack>
        </Card>
      </Grid>
    </Stack>
  );
}

function Kpi({ label, value, tone, hint }) {
  return (
    <Card variant="outlined">
      <Stack direction="column" gap="xs">
        <Badge variant={tone}>{label}</Badge>
        <Box fontSize="xl" fontWeight="bold">{value}</Box>
        <Box style={{ fontSize: 12, opacity: 0.65 }}>{hint}</Box>
      </Stack>
    </Card>
  );
}

function fmtTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
