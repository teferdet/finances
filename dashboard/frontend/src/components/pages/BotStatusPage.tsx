import React from 'react'
import { BotStatus } from '@/api/client'
import { Box, Card, Typography, Grid, LinearProgress, Divider } from '@mui/material'
import {
  SmartToy as BotIcon,
  Memory as LayersIcon,
  Update as ActivityIcon,
  Storage as HardDriveIcon,
  Terminal as TerminalIcon
} from '@mui/icons-material'

interface BotStatusPageProps {
  status: BotStatus | null
}

export const BotStatusPage: React.FC<BotStatusPageProps> = ({ status }) => {
  if (!status) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading system metrics…</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top process cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Bot Process
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'success.dark', color: 'success.light', display: 'flex' }}>
                <BotIcon fontSize="small" />
              </Box>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: status.service_status === 'active' ? 'success.main' : 'error.main' }} />
              <Typography variant="h5" sx={{ fontWeight: 'bold', textTransform: 'capitalize' }} >
                {status.service_status}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              PID: <Typography component="span" variant="caption" color="primary" sx={{ fontFamily: 'monospace' }}>{status.bot_pid ?? '—'}</Typography> | Threads: {status.bot_threads ?? '—'}
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Bot RAM RSS
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'info.dark', color: 'info.light', display: 'flex' }}>
                <LayersIcon fontSize="small" />
              </Box>
            </Box>
            <Typography variant="h5"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 1 }} >
              {status.bot_ram_mb != null ? `${status.bot_ram_mb} MB` : '—'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              CPU: {status.bot_cpu_pct != null ? `${status.bot_cpu_pct}%` : '—'}
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Service Started
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'secondary.main', color: 'secondary.light', display: 'flex' }}>
                <ActivityIcon fontSize="small" />
              </Box>
            </Box>
            <Typography variant="body1"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 1 }}  noWrap>
              {status.started_at ?? 'Active in systemd'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Version: {status.bot_version}
            </Typography>
          </Card>
        </Grid>
      </Grid>

      {/* Host Metrics & Hardware */}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
              <HardDriveIcon color="primary" />
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Host Memory & Storage</Typography>
            </Box>

            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'medium' }}>System RAM Allocation</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{status.sys_ram_used_gb} GB / {status.sys_ram_total_gb} GB ({status.sys_ram_pct}%)</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min(100, status.sys_ram_pct)} sx={{ height: 8, borderRadius: 4, bgcolor: 'background.default' }} />
            </Box>

            <Box sx={{ mb: 4 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'medium' }}>Root Filesystem Disk (/)</Typography>
                <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>{status.disk_used_gb} GB / {status.disk_total_gb} GB ({status.disk_pct}%)</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min(100, status.disk_pct)} color="info" sx={{ height: 8, borderRadius: 4, bgcolor: 'background.default' }} />
            </Box>

            <Grid container spacing={2}>
              <Grid size={{ xs: 6 }}>
                <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.default' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Host CPU Usage</Typography>
                  <Typography variant="h6"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  my: 0.5 }} >{status.sys_cpu_pct}%</Typography>
                  <Typography variant="caption" color="text.secondary">{status.sys_cpu_cores} Physical Cores</Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'background.default' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Load Avg (1m / 5m)</Typography>
                  <Typography variant="h6"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  my: 0.5 }} >{status.load_avg_1m} / {status.load_avg_5m}</Typography>
                  <Typography variant="caption" color="text.secondary">System scheduler load</Typography>
                </Box>
              </Grid>
            </Grid>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <Card sx={{ p: 3, height: '100%' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <TerminalIcon color="primary" />
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Environment & Host Details</Typography>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {[
                { label: 'Operating System', value: status.os },
                { label: 'Hostname / VPS Node', value: status.hostname },
                { label: 'Python Runtime', value: status.python_version },
                { label: 'Bot Release Version', value: status.bot_version },
                { label: 'Process Service Name', value: 'finances-bot.service' },
              ].map((row, i) => (
                <Box key={i}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1.5 }}>
                    <Typography variant="caption" color="text.secondary">{row.label}</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 'medium', fontFamily: 'monospace' }} >{row.value}</Typography>
                  </Box>
                  {i < 4 && <Divider />}
                </Box>
              ))}
            </Box>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
