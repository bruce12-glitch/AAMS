import React, { useCallback, useState } from 'react';
import { Stack, Box, Card, Button, Table, Badge } from '../ui.jsx';
import { api } from '../api/client.js';
import { usePoll } from '../hooks/usePoll.js';

export default function UsersPage() {
  const load = useCallback(async () => api.get('/users'), []);
  const { data, reload } = usePoll(load, 8000);
  const users = data?.users || [];
  const [qr, setQr] = useState(null);

  async function cyclePay(user) {
    const next = user.payment_status === 'active' ? 'expired' : 'active';
    await api.put(`/users/${encodeURIComponent(user.user_id)}?payment_status=${next}`);
    await reload();
  }

  async function showQr(userId) {
    const res = await api.get(`/users/${encodeURIComponent(userId)}/qr`);
    setQr({ userId, uri: res.qr_data_uri });
  }

  async function remove(userId) {
    if (!window.confirm(`Delete ${userId} and purge embeddings? (§26.2)`)) return;
    await api.del(`/users/${encodeURIComponent(userId)}`);
    await reload();
  }

  return (
    <Stack direction="column" gap="md">
      <Box>
        <h2>Users · enrollment</h2>
        <div style={{ fontSize: 13, opacity: 0.7 }}>
          consent required (§26) · 3 embeddings / user (§17.4) · payment is live, no re-enroll (§30.5)
        </div>
      </Box>
      <Card variant="default">
        <Table>
          <Table.Header>
            <Table.Row>
              <Table.Head>User</Table.Head>
              <Table.Head>Type</Table.Head>
              <Table.Head>Payment</Table.Head>
              <Table.Head>Expiry</Table.Head>
              <Table.Head>Consent</Table.Head>
              <Table.Head></Table.Head>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {users.map((u) => (
              <Table.Row key={u.user_id}>
                <Table.Cell>
                  <strong>{u.name}</strong>
                  <div style={{ fontSize: 12, opacity: 0.65 }}>{u.user_id}</div>
                </Table.Cell>
                <Table.Cell>{u.user_type}</Table.Cell>
                <Table.Cell>
                  <Badge variant={u.payment_status === 'active' ? 'positive' : 'negative'}>
                    {u.payment_status}
                  </Badge>
                </Table.Cell>
                <Table.Cell>{u.payment_expiry || '—'}</Table.Cell>
                <Table.Cell>
                  <Badge variant={u.consent_given ? 'positive' : 'attention'}>
                    {u.consent_given ? 'signed' : 'missing'}
                  </Badge>
                </Table.Cell>
                <Table.Cell>
                  <Stack direction="row" gap="sm">
                    <Button variant="secondary" onClick={() => cyclePay(u)}>Toggle pay</Button>
                    <Button variant="secondary" onClick={() => showQr(u.user_id)}>QR</Button>
                    <Button variant="danger" onClick={() => remove(u.user_id)}>Delete</Button>
                  </Stack>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </Card>
      {qr && (
        <Card variant="outlined">
          <Stack direction="column" gap="sm">
            <h3>Signed QR · {qr.userId}</h3>
            <img src={qr.uri} alt="QR pass" width="180" height="180" />
            <Button variant="secondary" onClick={() => setQr(null)}>Close</Button>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
