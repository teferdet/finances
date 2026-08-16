import React from 'react'
import { AlertsStats } from '@/api/client'
import { fmt } from '@/lib/utils'
import { Box, Card, Typography, Grid, LinearProgress } from '@mui/material'
import {
  Notifications as BellIcon,
  Schedule as ClockIcon,
  CheckCircle as CheckCircleIcon,
  BarChart as BarChartIcon,
} from '@mui/icons-material'

interface AlertsPageProps {
  stats: AlertsStats | null
}

export const AlertsPage: React.FC<AlertsPageProps> = ({ stats }) => {
  if (!stats) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading alerts data…</Typography>
      </Box>
    )
  }

  const maxCurrencyCount = Math.max(...stats.top_currencies.map((c) => c.count), 1)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top summary cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Total Created
              </Typography>
              <BellIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {fmt(stats.total)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Historical alert records
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Active Alerts
              </Typography>
              <ClockIcon color="info" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} color="info.main" >
              {fmt(stats.active)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Awaiting price target match
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Triggered
              </Typography>
              <CheckCircleIcon color="secondary" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} color="secondary.main" >
              {fmt(stats.triggered)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Notified to Telegram users
            </Typography>
          </Card>
        </Grid>
      </Grid>

      {/* Top Currencies in Alerts */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <BarChartIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              Most Monitored Currencies
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Top active user alert subscriptions by asset
          </Typography>
        </Box>

        {stats.top_currencies.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'background.default', borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary">No active currency alerts configured.</Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {stats.top_currencies.map((curr) => {
              const pct = (curr.count / maxCurrencyCount) * 100
              return (
                <Box key={curr.currency}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }} >
                      {curr.currency || 'USD'}
                    </Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="primary">
                      {curr.count} active alerts
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={pct} 
                    sx={{ height: 8, borderRadius: 4, bgcolor: 'background.default' }} 
                  />
                </Box>
              )
            })}
          </Box>
        )}
      </Card>
    </Box>
  )
}
