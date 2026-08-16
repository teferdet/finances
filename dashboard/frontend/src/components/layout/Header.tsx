import React, { useState } from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Alert,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  PowerSettingsNew as PowerIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material'
import { PageId } from './Sidebar'

interface HeaderProps {
  currentPage: PageId
  onRefresh: () => void
  onLogout: () => void
  onRestartBot: () => Promise<void>
  isRefreshing: boolean
  lastRefreshTime: Date | null
}

const PAGE_TITLES: Record<PageId, { title: string; subtitle: string }> = {
  overview: { title: 'Executive Overview', subtitle: 'Real-time KPIs, active users & traffic' },
  bot: { title: 'Bot & Host Health', subtitle: 'System load, RAM/CPU allocation & process uptime' },
  database: { title: 'MongoDB Analytics', subtitle: 'Storage, collections, document counts & indexes' },
  parser: { title: 'Data Parsers', subtitle: 'Fiat rates, cryptocurrency & stock market sync' },
  alerts: { title: 'Price Alerts', subtitle: 'User-configured exchange rate threshold alerts' },
  groups: { title: 'Telegram Groups', subtitle: 'Active community chats & permissions' },
  errors: { title: 'Error Diagnostic Log', subtitle: 'Live exception traces & warning streams' },
  users: { title: 'User Demographics', subtitle: 'Language distribution & top active users' },
  config: { title: 'Bot Configuration', subtitle: 'Dynamic feature flags & runtime parameters' },
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onRefresh,
  onLogout,
  onRestartBot,
  isRefreshing,
  lastRefreshTime,
}) => {
  const [showRestartModal, setShowRestartModal] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [restartStatus, setRestartStatus] = useState<{ type: 'success' | 'error', message: string } | null>(null)

  const meta = PAGE_TITLES[currentPage] || { title: 'Dashboard', subtitle: '' }

  const handleConfirmRestart = async () => {
    try {
      setRestarting(true)
      await onRestartBot()
      setRestartStatus({ type: 'success', message: 'Bot service restart triggered successfully!' })
      setTimeout(() => {
        setShowRestartModal(false)
        setRestartStatus(null)
      }, 2000)
    } catch (err: any) {
      setRestartStatus({ type: 'error', message: err.message || 'Failed to restart bot' })
    } finally {
      setRestarting(false)
    }
  }

  return (
    <>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          bgcolor: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              {meta.title}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: { xs: 'none', sm: 'block' } }}>
              {meta.subtitle}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {lastRefreshTime && (
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace', display: { xs: 'none', md: 'block' } }} >
                Updated {lastRefreshTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </Typography>
            )}

            <Button
              variant="outlined"
              color="inherit"
              size="small"
              onClick={onRefresh}
              disabled={isRefreshing}
              startIcon={<RefreshIcon />}
              sx={{ borderColor: 'rgba(255,255,255,0.2)', color: 'text.secondary' }}
            >
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>Refresh</Box>
            </Button>

            <Button
              variant="outlined"
              color="warning"
              size="small"
              onClick={() => setShowRestartModal(true)}
              startIcon={<PowerIcon />}
              sx={{ borderColor: 'warning.dark', color: 'warning.light' }}
            >
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>Restart Bot</Box>
            </Button>

            <Button
              variant="outlined"
              color="error"
              size="small"
              onClick={onLogout}
              startIcon={<LogoutIcon />}
              sx={{ borderColor: 'error.dark', color: 'error.light' }}
            >
              <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>Logout</Box>
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Dialog
        open={showRestartModal}
        onClose={() => !restarting && setShowRestartModal(false)}
        slotProps={{ paper: { sx: { bgcolor: 'background.paper', backgroundImage: 'none', borderRadius: 3, p: 1 } } }}
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 2, pb: 1 }}>
          <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'warning.dark', color: 'warning.light', display: 'flex' }}>
            <PowerIcon />
          </Box>
          Restart Bot Service?
        </DialogTitle>
        <DialogContent sx={{ pb: 1 }}>
          <DialogContentText sx={{ mb: 2 }}>
            This temporarily restarts background polling, alert triggers, and parsers. Active private chats will resume in 3–5 seconds.
          </DialogContentText>
          {restartStatus && (
            <Alert severity={restartStatus.type} sx={{ mt: 1 }}>
              {restartStatus.message}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowRestartModal(false)} disabled={restarting} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleConfirmRestart}
            disabled={restarting}
            variant="contained"
            color="warning"
            disableElevation
          >
            {restarting ? 'Restarting...' : 'Yes, Restart'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
