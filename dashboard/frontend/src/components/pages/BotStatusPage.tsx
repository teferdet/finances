import React, { useState, useEffect } from 'react'
import { BotStatus, api } from '@/api/client'
import {
  Box, Card, Typography, Grid, LinearProgress, Divider,
  Button, CircularProgress, Alert, ToggleButtonGroup, ToggleButton,
  IconButton, Tooltip, Chip,
} from '@mui/material'
import {
  SmartToy as BotIcon,
  Memory as LayersIcon,
  Update as ActivityIcon,
  Storage as HardDriveIcon,
  Terminal as TerminalIcon,
  CleaningServices as CleanIcon,
  Refresh as RefreshIcon,
  Description as LogIcon,
} from '@mui/icons-material'

interface BotStatusPageProps {
  status: BotStatus | null
}

export const BotStatusPage: React.FC<BotStatusPageProps> = ({ status }) => {
  // ── Log Viewer state ──────────────────────────────────────────────────────
  const [logSource, setLogSource] = useState<'api' | 'bot'>('api')
  const [logLines, setLogLines] = useState<number>(100)
  const [logs, setLogs] = useState<string[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [logFileName, setLogFileName] = useState('')

  // ── OTP Cleanup state ─────────────────────────────────────────────────────
  const [otpLoading, setOtpLoading] = useState(false)
  const [otpMessage, setOtpMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchLogs = async (source = logSource, lines = logLines) => {
    setLogsLoading(true)
    try {
      const res = await api.getLogs(source, lines)
      setLogs(res.content || [])
      setLogFileName(res.file || '')
    } catch (e: any) {
      setLogs([`[Error fetching logs: ${e.message || 'Unknown error'}]`])
    } finally {
      setLogsLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs(logSource, logLines)
  }, [logSource, logLines])

  const handleClearOtps = async () => {
    setOtpLoading(true)
    setOtpMessage(null)
    try {
      const res = await api.clearOtps()
      setOtpMessage({
        type: 'success',
        text: res.message || `Deleted ${res.deleted} expired OTP tokens.`,
      })
      setTimeout(() => setOtpMessage(null), 5000)
    } catch (e: any) {
      setOtpMessage({ type: 'error', text: e.message || 'Failed to clear OTPs' })
    } finally {
      setOtpLoading(false)
    }
  }

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
          <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Bot Process
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(16,185,129,0.15)', color: '#10b981', display: 'flex' }}>
                <BotIcon fontSize="small" />
              </Box>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Box sx={{
                width: 10, height: 10, borderRadius: '50%',
                bgcolor: status.service_status === 'active' || status.service_status === 'running' ? '#10b981' : '#f43f5e',
                boxShadow: status.service_status === 'active' || status.service_status === 'running' ? '0 0 8px #10b981' : 'none'
              }} />
              <Typography variant="h5" sx={{ fontWeight: 'bold', textTransform: 'capitalize' }}>
                {status.service_status}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              PID: <Typography component="span" variant="caption" color="primary" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>{status.bot_pid ?? '—'}</Typography> | Threads: {status.bot_threads ?? '—'}
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Bot Memory
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(99,102,241,0.15)', color: '#818cf8', display: 'flex' }}>
                <LayersIcon fontSize="small" />
              </Box>
            </Box>
            <Typography variant="h5" sx={{ fontFamily: 'monospace', fontWeight: 'bold', mb: 1 }}>
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
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                System Uptime
              </Typography>
              <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(245,158,11,0.15)', color: '#fbbf24', display: 'flex' }}>
                <ActivityIcon fontSize="small" />
              </Box>
            </Box>
            <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'bold', mb: 1 }} noWrap>
              {status.started_at ?? 'Active daemon'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Release: {status.bot_version}
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
                <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'rgba(255,255,255,0.02)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Host CPU Usage</Typography>
                  <Typography variant="h6" sx={{ fontFamily: 'monospace', fontWeight: 'bold', my: 0.5 }}>{status.sys_cpu_pct}%</Typography>
                  <Typography variant="caption" color="text.secondary">{status.sys_cpu_cores} Physical Cores</Typography>
                </Box>
              </Grid>
              <Grid size={{ xs: 6 }}>
                <Box sx={{ p: 2, borderRadius: 2, border: '1px solid', borderColor: 'divider', bgcolor: 'rgba(255,255,255,0.02)' }}>
                  <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>Load Avg (1m / 5m)</Typography>
                  <Typography variant="h6" sx={{ fontFamily: 'monospace', fontWeight: 'bold', my: 0.5 }}>{status.load_avg_1m} / {status.load_avg_5m}</Typography>
                  <Typography variant="caption" color="text.secondary">System scheduler load</Typography>
                </Box>
              </Grid>
            </Grid>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, lg: 6 }}>
          <Card sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TerminalIcon color="primary" />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Environment & Maintenance</Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
              {[
                { label: 'Operating System', value: status.os },
                { label: 'Hostname / VPS Node', value: status.hostname },
                { label: 'Python Runtime', value: status.python_version },
                { label: 'Bot Release Version', value: status.bot_version },
                { label: 'Process Service Name', value: 'finances-bot.service' },
              ].map((row, i) => (
                <Box key={i}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
                    <Typography variant="caption" color="text.secondary">{row.label}</Typography>
                    <Typography variant="caption" sx={{ fontWeight: 'medium', fontFamily: 'monospace' }}>{row.value}</Typography>
                  </Box>
                  {i < 4 && <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />}
                </Box>
              ))}
            </Box>

            {/* Quick Actions */}
            <Box sx={{ mt: 'auto', pt: 2, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase', display: 'block', mb: 1.5 }}>
                Database Maintenance
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  startIcon={otpLoading ? <CircularProgress size={14} color="inherit" /> : <CleanIcon />}
                  onClick={handleClearOtps}
                  disabled={otpLoading}
                  sx={{ borderRadius: 2 }}
                >
                  Clear Expired OTP Tokens
                </Button>
              </Box>
              {otpMessage && (
                <Alert severity={otpMessage.type} sx={{ mt: 1.5, py: 0 }}>
                  {otpMessage.text}
                </Alert>
              )}
            </Box>
          </Card>
        </Grid>
      </Grid>

      {/* Live System Logs */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(99,102,241,0.15)', color: '#818cf8', display: 'flex' }}>
              <LogIcon />
            </Box>
            <Box>
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Real-time Server Logs</Typography>
              <Typography variant="caption" color="text.secondary">
                {logFileName ? `Viewing ${logFileName}` : 'Streaming rolling log stream'}
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <ToggleButtonGroup
              size="small"
              value={logSource}
              exclusive
              onChange={(_, v) => v && setLogSource(v)}
            >
              <ToggleButton value="api" sx={{ px: 2, fontWeight: 700, fontSize: '0.75rem' }}>API (ASP.NET)</ToggleButton>
              <ToggleButton value="bot" sx={{ px: 2, fontWeight: 700, fontSize: '0.75rem' }}>Bot Daemon</ToggleButton>
            </ToggleButtonGroup>

            <ToggleButtonGroup
              size="small"
              value={logLines}
              exclusive
              onChange={(_, v) => v && setLogLines(v)}
            >
              <ToggleButton value={50} sx={{ px: 1, fontSize: '0.7rem' }}>50</ToggleButton>
              <ToggleButton value={100} sx={{ px: 1, fontSize: '0.7rem' }}>100</ToggleButton>
              <ToggleButton value={250} sx={{ px: 1, fontSize: '0.7rem' }}>250</ToggleButton>
            </ToggleButtonGroup>

            <Tooltip title="Refresh logs">
              <IconButton onClick={() => fetchLogs()} disabled={logsLoading} size="small" color="primary">
                {logsLoading ? <CircularProgress size={16} /> : <RefreshIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Box sx={{
          bgcolor: '#040811',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 2,
          p: 2,
          maxHeight: 380,
          overflowY: 'auto',
          fontFamily: '"JetBrains Mono", "Fira Code", monospace',
          fontSize: '0.78rem',
          color: '#cbd5e1',
          lineHeight: 1.6,
          boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.6)',
        }}>
          {logs.length === 0 ? (
            <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
              No log entries found for {logSource.toUpperCase()}.
            </Typography>
          ) : (
            logs.map((line, idx) => {
              const isErr = line.includes('[ERR]') || line.includes('ERROR') || line.includes('Exception')
              const isWarn = line.includes('[WRN]') || line.includes('WARN')
              const isInf = line.includes('[INF]') || line.includes('INFO')
              return (
                <Box
                  key={idx}
                  sx={{
                    color: isErr ? '#fb7185' : isWarn ? '#fbbf24' : isInf ? '#94a3b8' : 'inherit',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    '&:hover': { bgcolor: 'rgba(255,255,255,0.03)' },
                  }}
                >
                  {line}
                </Box>
              )
            })
          )}
        </Box>
      </Card>
    </Box>
  )
}
