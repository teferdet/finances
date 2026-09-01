import React, { useState } from 'react'
import {
  Box, Card, Typography, Grid, Chip, Button,
  ToggleButtonGroup, ToggleButton, Divider,
} from '@mui/material'
import { OverviewStats, ActivityPoint } from '@/api/client'
import { fmt } from '@/lib/utils'
import {
  People as UsersIcon,
  HowToReg as UserCheckIcon,
  Timeline as TrendingUpIcon,
  WorkspacePremium as CrownIcon,
  ShowChart as ActivityIcon,
  ReportProblem as AlertTriangleIcon,
  Sync as RefreshCwIcon,
  Forum as MessageSquareIcon,
  Notifications as BellIcon,
  PersonAdd as PersonAddIcon,
  AccountBalanceWallet as WalletIcon,
  TrendingUp as ArrowUpIcon,
} from '@mui/icons-material'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Legend,
} from 'recharts'

interface OverviewPageProps {
  overview: OverviewStats | null
  activity: ActivityPoint[]
  onChartDaysChange?: (days: number) => void
  chartDays?: number
}

// Custom recharts tooltip
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <Box sx={{
      bgcolor: '#0a1628',
      border: '1px solid rgba(148,163,184,0.15)',
      borderRadius: 2,
      p: 1.5,
      boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
    }}>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
        {label}
      </Typography>
      {payload.map((p: any) => (
        <Box key={p.dataKey} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.25 }}>
          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: p.color }} />
          <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
            {p.name}: {fmt(p.value)}
          </Typography>
        </Box>
      ))}
    </Box>
  )
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  overview,
  activity,
  onChartDaysChange,
  chartDays = 30,
}) => {
  if (!overview) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading metrics…</Typography>
      </Box>
    )
  }

  const premiumPct = overview.total_users
    ? ((overview.premium / overview.total_users) * 100).toFixed(1)
    : '0'

  const kpis = [
    {
      label: 'Total Users',
      value: fmt(overview.total_users),
      icon: <UsersIcon />,
      color: '#10b981',
      secondary: `${overview.retention_rate}% MAU retention`,
      trend: overview.new_users_today > 0 ? `+${fmt(overview.new_users_today)} today` : null,
    },
    {
      label: 'DAU / WAU / MAU',
      value: fmt(overview.dau),
      icon: <UserCheckIcon />,
      color: '#2dd4bf',
      secondary: `WAU: ${fmt(overview.wau)} · MAU: ${fmt(overview.mau)}`,
      trend: null,
    },
    {
      label: 'New Users Today',
      value: fmt(overview.new_users_today),
      icon: <PersonAddIcon />,
      color: '#818cf8',
      secondary: `This week: +${fmt(overview.new_users_week)}`,
      trend: null,
    },
    {
      label: 'Premium Subscribers',
      value: fmt(overview.premium),
      icon: <CrownIcon />,
      color: '#fbbf24',
      secondary: `${premiumPct}% of user base`,
      trend: null,
    },
    {
      label: 'Portfolio Assets',
      value: fmt(overview.total_portfolios),
      icon: <WalletIcon />,
      color: '#a78bfa',
      secondary: 'Crypto + Stock + Fiat lots',
      trend: null,
    },
    {
      label: 'Active Groups',
      value: fmt(overview.total_groups),
      icon: <MessageSquareIcon />,
      color: '#c084fc',
      secondary: 'Active Telegram groups',
      trend: null,
    },
    {
      label: 'Price Alerts Active',
      value: fmt(overview.active_alerts),
      icon: <BellIcon />,
      color: '#22d3ee',
      secondary: 'Monitoring 24/7',
      trend: null,
    },
    {
      label: 'Requests Today',
      value: fmt(overview.requests_today),
      icon: <ActivityIcon />,
      color: '#60a5fa',
      secondary: `Week: ${fmt(overview.requests_week)}`,
      trend: null,
    },
    {
      label: 'Errors Today',
      value: fmt(overview.errors_today),
      icon: <AlertTriangleIcon />,
      color: overview.errors_today > 0 ? '#fb7185' : '#10b981',
      secondary: overview.errors_today === 0 ? 'All systems operational' : 'Check error log',
      trend: null,
      alert: overview.errors_today > 0,
    },
  ]

  const chartData = activity.map(item => ({
    date: item.date,
    dau: item.dau,
    new_users: item.new_users,
  }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI Grid */}
      <Grid container spacing={2}>
        {kpis.map((kpi, idx) => (
          <Grid size={{ xs: 12, sm: 6, lg: 4, xl: 3 }} key={idx}>
            <Card sx={{
              p: 2.5,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative',
              overflow: 'hidden',
              ...(kpi.alert && {
                borderColor: 'rgba(244,63,94,0.3) !important',
                boxShadow: '0 0 20px rgba(244,63,94,0.12) !important',
              }),
            }}>
              {/* Background glow */}
              <Box sx={{
                position: 'absolute', top: -20, right: -20,
                width: 80, height: 80, borderRadius: '50%',
                bgcolor: kpi.color,
                opacity: 0.06,
                filter: 'blur(20px)',
                pointerEvents: 'none',
              }} />

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '0.04em' }}>
                  {kpi.label.toUpperCase()}
                </Typography>
                <Box sx={{
                  p: 0.75, borderRadius: 1.5,
                  bgcolor: `${kpi.color}18`,
                  color: kpi.color,
                  display: 'flex',
                  border: `1px solid ${kpi.color}22`,
                }}>
                  {React.cloneElement(kpi.icon, { sx: { fontSize: '1.1rem' } })}
                </Box>
              </Box>

              <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-0.02em', mb: 0.5 }}>
                {kpi.value}
              </Typography>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 'auto' }}>
                <Typography variant="caption" color="text.secondary">{kpi.secondary}</Typography>
                {kpi.trend && (
                  <Chip
                    label={kpi.trend}
                    size="small"
                    icon={<ArrowUpIcon sx={{ fontSize: '0.75rem !important' }} />}
                    sx={{
                      bgcolor: 'rgba(16,185,129,0.1)',
                      color: '#10b981',
                      border: '1px solid rgba(16,185,129,0.2)',
                      fontWeight: 700,
                      fontSize: '0.65rem',
                      height: 20,
                    }}
                  />
                )}
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Activity Chart */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <TrendingUpIcon sx={{ color: '#10b981' }} />
              <Typography variant="subtitle1">Activity Trends</Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              Daily active users & new registrations
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Legend */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              {[
                { color: '#10b981', label: 'DAU' },
                { color: '#818cf8', label: 'New Users' },
              ].map(l => (
                <Box key={l.label} sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: l.color, boxShadow: `0 0 6px ${l.color}` }} />
                  <Typography variant="caption" sx={{ fontWeight: 700, color: l.color }}>{l.label}</Typography>
                </Box>
              ))}
            </Box>

            {/* Days selector */}
            {onChartDaysChange && (
              <ToggleButtonGroup
                size="small"
                value={chartDays}
                exclusive
                onChange={(_, v) => v && onChartDaysChange(v)}
              >
                {[7, 14, 30].map(d => (
                  <ToggleButton key={d} value={d} sx={{ px: 1.5, fontSize: '0.7rem', fontWeight: 700 }}>
                    {d}d
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
            )}
          </Box>
        </Box>

        <Box sx={{ height: 340, width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="dauGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#10b981" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="newUsersGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#818cf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#818cf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#475569" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone" dataKey="new_users" name="New Users"
                stroke="#818cf8" strokeWidth={2}
                fillOpacity={1} fill="url(#newUsersGrad)"
              />
              <Area
                type="monotone" dataKey="dau" name="DAU"
                stroke="#10b981" strokeWidth={2}
                fillOpacity={1} fill="url(#dauGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </Card>
    </Box>
  )
}
