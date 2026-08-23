import React, { useCallback, useState } from 'react';
import { Grid, Stack, Box, Card, Button, Badge } from '../ui.jsx';
import { api } from '../api/client.js';
import { usePoll } from '../hooks/usePoll.js';

const TABS = [
  { id: 'daily', label: 'Daily' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'proxy', label: 'Proxy' },
  { id: 'unpaid', label: 'Unpaid' },
  { id: 'occupancy', label: 'Occupancy' },
];

export default function ReportsPage() {
  const [tab, setTab] = useState('daily');
  const load = useCallback(async () => {
    const [daily, weekly, proxy, unpaid, occupancy] = await Promise.all([
      api.get('/reports/daily'),
      api.get('/reports/weekly'),
      api.get('/reports/proxy'),
      api.get('/reports/unpaid'),
      api.get('/reports/occupancy'),
    ]);
    return { daily, weekly, proxy, unpaid, occupancy };
  }, []);
  const { data } = usePoll(load, 8000);
  const report = data?.[tab];

  return (
    <Stack direction="column" gap="md">
      {data?.daily && (
        <Grid columns={{ base: 2, lg: 6 }} gap="sm">
          <Stat label="Total entries" value={data.daily.total_entries} />
          <Stat label="Unique users" value={data.daily.unique_users} />
          <Stat label="Authorized" value={data.daily.authorized} />
          <Stat label="Proxy" value={data.daily.proxy_attempts} />
          <Stat label="Unpaid" value={data.daily.unpaid_attempts} />
          <Stat label="Spoof" value={data.daily.spoof_attempts} />
        </Grid>
      )}

      <Stack direction="row" gap="sm">
        {TABS.map((t) => (
          <Button key={t.id} variant={tab === t.id ? 'primary' : 'secondary'} onClick={() => setTab(t.id)}>
            {t.label}
          </Button>
        ))}
      </Stack>

      <Card variant="outlined">
        <Stack direction="column" gap="sm">
          <h2>{report?.title || 'Report'}</h2>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.6 }}>
            {JSON.stringify(report, null, 2)}
          </pre>
          <Box style={{ fontSize: 12, opacity: 0.65 }}>
            Retention (§26.4): logs 90d · alert images 30d · daily reports 1y. Auto-send 20:00.
          </Box>
        </Stack>
      </Card>
    </Stack>
  );
}

function Stat({ label, value }) {
  return (
    <Card variant="outlined">
      <Stack direction="column" gap="xs">
        <Badge variant="neutral">{label}</Badge>
        <Box fontSize="xl" fontWeight="bold">{value ?? 0}</Box>
      </Stack>
    </Card>
  );
}
