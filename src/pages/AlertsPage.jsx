import React, { useCallback } from 'react';
import { Stack, Box, Card, Button, Badge } from '../ui.jsx';
import { api } from '../api/client.js';
import { usePoll } from '../hooks/usePoll.js';

export default function AlertsPage() {
  const load = useCallback(async () => api.get('/alerts'), []);
  const { data, reload } = usePoll(load, 4000);
  const alerts = data?.alerts || [];

  async function ack(id) {
    await api.post(`/alerts/${id}/ack`);
    await reload();
  }

  async function approve(id) {
    await api.post(`/alerts/${id}/approve`);
    await reload();
  }

  return (
    <Stack direction="column" gap="md">
      <Box>
        <h2>In-charge alert feed</h2>
        <div style={{ fontSize: 13, opacity: 0.7 }}>Telegram contract §15.2 · ack / approve here first</div>
      </Box>
      {alerts.length === 0 && <Card variant="outlined">No alerts yet. Run a proxy / unpaid / spoof scenario on Live.</Card>}
      {alerts.map((a) => (
        <Card key={a.id} variant="outlined">
          <Stack direction="column" gap="sm">
            <Stack direction="row" justify="space-between" align="center">
              <Stack direction="row" gap="sm" align="center">
                <Badge variant={a.severity === 'high' ? 'negative' : 'attention'}>{a.alert_type}</Badge>
                <Badge variant="neutral">{a.severity}</Badge>
                {a.acked ? <Badge variant="neutral">ACK</Badge> : null}
                {a.approved ? <Badge variant="positive">APPROVED</Badge> : null}
              </Stack>
              <Box style={{ fontSize: 12, opacity: 0.65 }}>{a.created_at}</Box>
            </Stack>
            <Box style={{ fontFamily: 'ui-monospace, monospace', fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {a.message}
            </Box>
            <Stack direction="row" gap="sm">
              {!a.acked && <Button variant="secondary" onClick={() => ack(a.id)}>Acknowledge</Button>}
              {!a.approved && a.alert_type === 'UNPAID' && (
                <Button variant="primary" onClick={() => approve(a.id)}>Approve one-time entry</Button>
              )}
            </Stack>
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}
