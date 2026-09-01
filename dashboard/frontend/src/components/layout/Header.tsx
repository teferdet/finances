import React from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Logout as LogoutIcon,
} from '@mui/icons-material'
import { PageId } from './Sidebar'

interface HeaderProps {
  currentPage: PageId
  onRefresh: () => void
  onLogout: () => void
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
  isRefreshing,
  lastRefreshTime,
}) => {
  const meta = PAGE_TITLES[currentPage] || { title: 'Dashboard', subtitle: '' }

  return (
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
  )
}

