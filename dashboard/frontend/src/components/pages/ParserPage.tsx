import React from 'react'
import { ParserStatus } from '@/api/client'
import { fmt, timeAgo, formatDate } from '@/lib/utils'
import { Box, Card, Typography, Grid, Chip } from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import {
  AttachMoney as DollarSignIcon,
  CurrencyBitcoin as BitcoinIcon,
  ShowChart as LineChartIcon,
  Sync as RefreshCwIcon,
  Warning as AlertTriangleIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'

interface ParserPageProps {
  status: ParserStatus | null
}

export const ParserPage: React.FC<ParserPageProps> = ({ status }) => {
  if (!status) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading parser health…</Typography>
      </Box>
    )
  }

  const parsers = [
    {
      name: 'Fiat Currencies',
      icon: <DollarSignIcon color="primary" />,
      stats: `${fmt(status.fiat.count)} active exchange pairs`,
      lastUpdated: status.fiat.last_updated,
    },
    {
      name: 'Cryptocurrencies',
      icon: <BitcoinIcon color="warning" />,
      stats: 'Real-time crypto tickers',
      lastUpdated: status.crypto.last_updated,
    },
    {
      name: 'Stock Market',
      icon: <LineChartIcon color="info" />,
      stats: 'Global equity tickers',
      lastUpdated: status.stocks.last_updated,
    },
  ]

  const columns: GridColDef[] = [
    { 
      field: 'source', 
      headerName: 'Source', 
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{params.value}</Typography>
      )
    },
    { 
      field: 'count', 
      headerName: 'Failures', 
      width: 130,
      type: 'number',
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 'bold' }} color="error">
          {params.value}
        </Typography>
      )
    },
    { 
      field: 'last_error', 
      headerName: 'Last Error Message', 
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary" noWrap title={params.value}>
          {params.value || '—'}
        </Typography>
      )
    },
    { 
      field: 'last_seen', 
      headerName: 'Last Occurrence', 
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" color="text.secondary">
          {timeAgo(params.value as string)}
        </Typography>
      )
    },
  ]

  const rows = status.parser_errors.map((err, i) => ({ id: i, ...err }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top parsers cards */}
      <Grid container spacing={2}>
        {parsers.map((p, idx) => (
          <Grid size={{ xs: 12, md: 4 }} key={idx}>
            <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {p.icon}
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>{p.name}</Typography>
                </Box>
                <Chip icon={<CheckCircleIcon />} label="Syncing" color="success" variant="outlined" size="small" />
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{p.stats}</Typography>
              <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                Updated: <Typography component="span" variant="caption" color="primary">{timeAgo(p.lastUpdated)}</Typography> ({formatDate(p.lastUpdated)})
              </Typography>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Parser Cycles summary banner */}
      <Card sx={{ p: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'primary.dark', color: 'primary.light', display: 'flex' }}>
            <RefreshCwIcon />
          </Box>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Automated Sync Loops</Typography>
            <Typography variant="caption" color="text.secondary">Background workers update rates periodically</Typography>
          </Box>
        </Box>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="h4" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}  color="primary.main">
            {fmt(status.cycles_today)}
          </Typography>
          <Typography variant="caption" color="text.secondary">Cycles done today</Typography>
        </Box>
      </Card>

      {/* Error Tracking Table */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 400 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AlertTriangleIcon color="warning" />
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Parser Health & Error Tracking</Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            {status.parser_errors.length === 0 ? 'No active errors recorded' : `${status.parser_errors.length} problematic sources`}
          </Typography>
        </Box>

        {status.parser_errors.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center', bgcolor: 'rgba(16, 185, 129, 0.1)', borderRadius: 2, border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <Typography variant="body2" color="primary">
              ✅ All data sources are operating cleanly with zero recent parser failures.
            </Typography>
          </Box>
        ) : (
          <Box sx={{ flexGrow: 1, width: '100%' }}>
            <DataGrid
              rows={rows}
              columns={columns}
              initialState={{ pagination: { paginationModel: { pageSize: 10 } } }}
              pageSizeOptions={[10, 25]}
              disableRowSelectionOnClick
              sx={{ border: 0, '& .MuiDataGrid-columnHeaders': { bgcolor: 'background.default' } }}
            />
          </Box>
        )}
      </Card>
    </Box>
  )
}
