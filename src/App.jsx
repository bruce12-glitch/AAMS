import React, { useEffect, useState } from 'react';
import { Layout, Stack, Box, Button, Badge, Theme, neutralTheme } from './ui.jsx';
import LivePage from './pages/LivePage.jsx';
import LogsPage from './pages/LogsPage.jsx';
import AlertsPage from './pages/AlertsPage.jsx';
import UsersPage from './pages/UsersPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import { pingHealth } from './api/client.js';

const NAV = [
  { id: 'live', label: 'Live Monitor' },
  { id: 'logs', label: 'Entry Logs' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'users', label: 'Users' },
  { id: 'reports', label: 'Reports' },
];

function App() {
  const [page, setPage] = useState('live');
  const [apiUp, setApiUp] = useState(null);
  const [clock, setClock] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const ok = await pingHealth();
      if (!cancelled) setApiUp(ok);
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Theme theme={neutralTheme}>
      <Layout>
        <Box padding="md" background="surface.base">
          <Stack direction="row" justify="space-between" align="center">
            <Box>
              <h1>FacePass FabLab</h1>
              <p>AAMS live console · SRMIST Fab Lab · prototype</p>
            </Box>
            <Stack direction="row" gap="sm" align="center">
              <Badge variant={apiUp ? 'positive' : apiUp === false ? 'negative' : 'attention'}>
                API {apiUp ? 'online' : apiUp === false ? 'offline' : 'checking'}
              </Badge>
              <Badge variant="neutral">SCRFD + ArcFace · thr 0.45</Badge>
              <Badge variant="neutral">
                {clock.toLocaleTimeString('en-GB')}
              </Badge>
            </Stack>
          </Stack>
          <Box marginTop="sm">
            <Stack direction="row" gap="sm">
              {NAV.map((item) => (
                <Button
                  key={item.id}
                  variant={page === item.id ? 'primary' : 'secondary'}
                  onClick={() => setPage(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </Stack>
          </Box>
        </Box>

        <Box padding="lg">
          {page === 'live' && <LivePage />}
          {page === 'logs' && <LogsPage />}
          {page === 'alerts' && <AlertsPage />}
          {page === 'users' && <UsersPage />}
          {page === 'reports' && <ReportsPage />}
        </Box>
      </Layout>
    </Theme>
  );
}

export default App;
