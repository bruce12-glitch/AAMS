import React from 'react';
import { Layout, Grid, Stack, Box, Card, Button, Table, Badge } from '@astryxdesign/core';
import { Theme, neutralTheme } from '@astryxdesign/theme-neutral';

function App() {
  return (
    <Theme theme={neutralTheme}>
      <Layout>
        {/* Header Block */}
        <Box padding="md" background="surface.base">
          <Stack direction="row" justify="space-between" align="center">
            <Box>
              <h1>AAMS - FacePass FabLab</h1>
              <p>Console Prototype</p>
            </Box>
            <Stack direction="row" gap="sm">
              <Button variant="primary">Live Monitor</Button>
              <Button variant="secondary">Reports</Button>
              <Button variant="danger">Alerts</Button>
            </Stack>
          </Stack>
        </Box>

        {/* Main Content Area */}
        <Box padding="lg">
          {/* Multi-Metric Data Row */}
          <Grid columns={{ base: 1, sm: 2, lg: 4 }} gap="md">
            <Card variant="outlined">
              <Stack direction="column" gap="xs">
                <Badge variant="neutral">Total Entries</Badge>
                <Box fontSize="xl" fontWeight="bold">1,247</Box>
              </Stack>
            </Card>
            <Card variant="outlined">
              <Stack direction="column" gap="xs">
                <Badge variant="positive">Successful</Badge>
                <Box fontSize="xl" fontWeight="bold">1,198</Box>
              </Stack>
            </Card>
            <Card variant="outlined">
              <Stack direction="column" gap="xs">
                <Badge variant="attention">Pending</Badge>
                <Box fontSize="xl" fontWeight="bold">32</Box>
              </Stack>
            </Card>
            <Card variant="outlined">
              <Stack direction="column" gap="xs">
                <Badge variant="negative">Failed</Badge>
                <Box fontSize="xl" fontWeight="bold">17</Box>
              </Stack>
            </Card>
          </Grid>

          {/* Action Table Area */}
          <Box marginTop="lg">
            <Card variant="default">
              <Stack direction="column" gap="md">
                <Stack direction="row" justify="space-between" align="center">
                  <h2>Recent Entry Logs</h2>
                  <Button variant="secondary">View All</Button>
                </Stack>
                <Table>
                  <Table.Header>
                    <Table.Row>
                      <Table.Head>Name</Table.Head>
                      <Table.Head>Status</Table.Head>
                      <Table.Head>Time</Table.Head>
                      <Table.Head>Location</Table.Head>
                      <Table.Head>Action</Table.Head>
                    </Table.Row>
                  </Table.Header>
                  <Table.Body>
                    <Table.Row>
                      <Table.Cell>John Doe</Table.Cell>
                      <Table.Cell><Badge variant="positive">Granted</Badge></Table.Cell>
                      <Table.Cell>10:23 AM</Table.Cell>
                      <Table.Cell>Main Entrance</Table.Cell>
                      <Table.Cell><Button variant="secondary">Details</Button></Table.Cell>
                    </Table.Row>
                    <Table.Row>
                      <Table.Cell>Jane Smith</Table.Cell>
                      <Table.Cell><Badge variant="positive">Granted</Badge></Table.Cell>
                      <Table.Cell>10:18 AM</Table.Cell>
                      <Table.Cell>Lab Door A</Table.Cell>
                      <Table.Cell><Button variant="secondary">Details</Button></Table.Cell>
                    </Table.Row>
                    <Table.Row>
                      <Table.Cell>Mike Johnson</Table.Cell>
                      <Table.Cell><Badge variant="negative">Denied</Badge></Table.Cell>
                      <Table.Cell>10:15 AM</Table.Cell>
                      <Table.Cell>Main Entrance</Table.Cell>
                      <Table.Cell><Button variant="danger">Review</Button></Table.Cell>
                    </Table.Row>
                    <Table.Row>
                      <Table.Cell>Sarah Williams</Table.Cell>
                      <Table.Cell><Badge variant="attention">Pending</Badge></Table.Cell>
                      <Table.Cell>10:10 AM</Table.Cell>
                      <Table.Cell>Lab Door B</Table.Cell>
                      <Table.Cell><Button variant="secondary">Details</Button></Table.Cell>
                    </Table.Row>
                  </Table.Body>
                </Table>
              </Stack>
            </Card>
          </Box>
        </Box>
      </Layout>
    </Theme>
  );
}

export default App;
