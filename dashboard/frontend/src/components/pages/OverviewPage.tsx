import React from 'react'
import { Box, Card, Typography, Grid } from '@mui/material'
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
} from '@mui/icons-material'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface OverviewPageProps {
  overview: OverviewStats | null
  activity: ActivityPoint[]
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ overview, activity }) => {
  if (!overview) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading metrics…</Typography>
      </Box>
    )
  }

  const kpis = [
    {
      label: 'Total Registered Users',
      value: fmt(overview.total_users),
      icon: <UsersIcon sx={{ color: '#10b981' }} />,
      bg: 'rgba(16, 185, 129, 0.1)',
      secondary: `${overview.retention_rate}% DAU/WAU Retention`,
    },
    {
      label: 'Daily Active Users (DAU)',
      value: fmt(overview.dau),
      icon: <UserCheckIcon sx={{ color: '#2dd4bf' }} />,
      bg: 'rgba(45, 212, 191, 0.1)',
      secondary: `WAU: ${fmt(overview.wau)} | MAU: ${fmt(overview.mau)}`,
    },
    {
      label: 'Requests Today',
      value: fmt(overview.requests_today),
      icon: <ActivityIcon sx={{ color: '#60a5fa' }} />,
      bg: 'rgba(96, 165, 250, 0.1)',
      secondary: `Week Total: ${fmt(overview.requests_week)}`,
    },
    {
      label: 'Premium Subscribers',
      value: fmt(overview.premium),
      icon: <CrownIcon sx={{ color: '#fbbf24' }} />,
      bg: 'rgba(251, 191, 36, 0.1)',
      secondary: `${overview.total_users ? ((overview.premium / overview.total_users) * 100).toFixed(1) : 0}% of userbase`,
    },
    {
      label: 'Active Groups',
      value: fmt(overview.total_groups),
      icon: <MessageSquareIcon sx={{ color: '#c084fc' }} />,
      bg: 'rgba(192, 132, 252, 0.1)',
      secondary: 'Group chat deployments',
    },
    {
      label: 'Active Price Alerts',
      value: fmt(overview.active_alerts),
      icon: <BellIcon sx={{ color: '#22d3ee' }} />,
      bg: 'rgba(34, 211, 238, 0.1)',
      secondary: 'Monitoring rates 24/7',
    },
    {
      label: 'Parser Cycles Today',
      value: fmt(overview.parser_cycles_today),
      icon: <RefreshCwIcon sx={{ color: '#10b981' }} />,
      bg: 'rgba(16, 185, 129, 0.1)',
      secondary: 'Background sync jobs',
    },
    {
      label: 'Errors Today',
      value: fmt(overview.errors_today),
      icon: <AlertTriangleIcon sx={{ color: overview.errors_today > 0 ? '#fb7185' : '#10b981' }} />,
      bg: overview.errors_today > 0 ? 'rgba(251, 113, 133, 0.1)' : 'rgba(16, 185, 129, 0.1)',
      secondary: overview.errors_today === 0 ? 'All systems operational' : 'Review in error log',
    },
  ]

  const chartData = activity.map((item) => ({
    date: item.date.slice(5), // MM-DD
    dau: item.dau,
    requests: item.requests,
  }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* KPI Grid */}
      <Grid container spacing={2}>
        {kpis.map((kpi, idx) => (
          <Grid size={{ xs: 12, sm: 6, lg: 3 }} key={idx}>
            <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'medium' }}>
                  {kpi.label}
                </Typography>
                <Box sx={{ p: 1, borderRadius: 2, bgcolor: kpi.bg, display: 'flex' }}>
                  {kpi.icon}
                </Box>
              </Box>
              <Typography variant="h4"  sx={{ fontWeight: 'bold',  mb: 0.5 }}>
                {kpi.value}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {kpi.secondary}
              </Typography>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 30-Day Activity Chart */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <TrendingUpIcon sx={{ color: '#10b981' }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                Activity & Traffic (Last 30 Days)
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              Daily active users and command requests trend
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#10b981' }} />
              <Typography variant="caption"  sx={{ fontWeight: 'bold',  color: '#10b981' }}>DAU</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#3b82f6' }} />
              <Typography variant="caption"  sx={{ fontWeight: 'bold',  color: '#3b82f6' }}>Requests</Typography>
            </Box>
          </Box>
        </Box>

        <Box sx={{ height: 350, width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="dauGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="requestsGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  borderColor: '#334155',
                  borderRadius: '0.75rem',
                  color: '#fff'
                }}
                itemStyle={{ color: '#fff' }}
              />
              <Area type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#requestsGradient)" />
              <Area type="monotone" dataKey="dau" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#dauGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </Card>
    </Box>
  )
}
