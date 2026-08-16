import React from 'react'
import { GroupsStats } from '@/api/client'
import { fmt, timeAgo, formatDate } from '@/lib/utils'
import { Box, Card, Typography, Grid, Chip } from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import {
  Groups as UsersIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Forum as MessageSquareIcon,
} from '@mui/icons-material'

interface GroupsPageProps {
  stats: GroupsStats | null
}

export const GroupsPage: React.FC<GroupsPageProps> = ({ stats }) => {
  if (!stats) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading groups data…</Typography>
      </Box>
    )
  }

  const columns: GridColDef[] = [
    { 
      field: 'title', 
      headerName: 'Group Title', 
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 'bold' }} noWrap>
          {params.value || 'Telegram Group'}
        </Typography>
      )
    },
    { 
      field: 'chat_id', 
      headerName: 'Chat ID', 
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary">
          {params.value}
        </Typography>
      )
    },
    { 
      field: 'is_active', 
      headerName: 'Status', 
      width: 130,
      type: 'boolean',
      renderCell: (params: GridRenderCellParams) => (
        params.value ? (
          <Chip label="ACTIVE" size="small" color="success" variant="outlined" sx={{ fontWeight: 'bold' }} />
        ) : (
          <Chip label="INACTIVE" size="small" color="error" variant="outlined" sx={{ fontWeight: 'bold' }} />
        )
      )
    },
    { 
      field: 'member_count', 
      headerName: 'Members', 
      type: 'number',
      width: 130,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
          {fmt(params.value as number)}
        </Typography>
      )
    },
    { 
      field: 'added_at', 
      headerName: 'Joined', 
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" color="text.secondary" title={formatDate(params.value as string)}>
          {timeAgo(params.value as string)}
        </Typography>
      )
    },
  ]

  // Map rows for DataGrid id
  const rows = stats.recent.map(g => ({ id: g.chat_id, ...g }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top summary cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Total Groups
              </Typography>
              <UsersIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {fmt(stats.total)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              All connected chats
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Active Communities
              </Typography>
              <CheckCircleIcon color="success" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} color="success.main" >
              {fmt(stats.active)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Responding to commands
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 4 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Inactive / Removed
              </Typography>
              <CancelIcon color="error" fontSize="small" />
            </Box>
            <Typography variant="h4"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} color="text.secondary" >
              {fmt(stats.inactive)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Bot left or uninstalled
            </Typography>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Groups Table */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 500 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MessageSquareIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              Recent Group Chats ({stats.recent.length})
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Latest additions
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <DataGrid
            rows={rows}
            columns={columns}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
            }}
            pageSizeOptions={[10, 25, 50]}
            disableRowSelectionOnClick
            sx={{
              border: 0,
              '& .MuiDataGrid-columnHeaders': { bgcolor: 'background.default' },
            }}
          />
        </Box>
      </Card>
    </Box>
  )
}
