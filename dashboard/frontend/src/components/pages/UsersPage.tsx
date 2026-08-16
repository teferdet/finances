import React from 'react'
import { Box, Card, Typography, Grid, LinearProgress, Chip } from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import { Public as GlobeIcon, Stars as SparklesIcon, WorkspacePremium as CrownIcon } from '@mui/icons-material'
import { UserLanguageStat, TopUser } from '@/api/client'
import { fmt, timeAgo, formatDate } from '@/lib/utils'

interface UsersPageProps {
  usersData: { by_language: UserLanguageStat[]; top_users: TopUser[] } | null
}

export const UsersPage: React.FC<UsersPageProps> = ({ usersData }) => {
  if (!usersData) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading user analytics…</Typography>
      </Box>
    )
  }

  const totalUsersInLangs = usersData.by_language.reduce((acc, l) => acc + l.count, 0)

  const columns: GridColDef[] = [
    { 
      field: 'id', 
      headerName: 'User ID', 
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary">
          {params.value}
        </Typography>
      )
    },
    { 
      field: 'username', 
      headerName: 'Username', 
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: "medium" }}>
          {params.value ? `@${params.value}` : 'Anonymous'}
        </Typography>
      )
    },
    { 
      field: 'language', 
      headerName: 'Language', 
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ textTransform: 'uppercase' }}>
          {params.value}
        </Typography>
      )
    },
    { 
      field: 'premium', 
      headerName: 'Tier', 
      width: 130,
      type: 'boolean',
      renderCell: (params: GridRenderCellParams) => (
        params.value ? (
          <Chip 
            icon={<CrownIcon fontSize="small" />} 
            label="PREMIUM" 
            size="small" 
            color="warning" 
            variant="outlined"
            sx={{ fontWeight: 'bold', fontSize: '0.65rem' }}
          />
        ) : (
          <Typography variant="caption" color="text.secondary">Standard</Typography>
        )
      )
    },
    { 
      field: 'requests', 
      headerName: 'Total Requests', 
      type: 'number',
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: "bold" }} color="primary">
          {fmt(params.value as number)}
        </Typography>
      )
    },
    { 
      field: 'last_active', 
      headerName: 'Last Active', 
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" color="text.secondary" title={formatDate(params.value as string)}>
          {timeAgo(params.value as string)}
        </Typography>
      )
    },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Languages Breakdown */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <GlobeIcon color="primary" />
          <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>Language Demographics</Typography>
        </Box>

        <Grid container spacing={2}>
          {usersData.by_language.map((item) => {
            const pctNum = totalUsersInLangs ? (item.count / totalUsersInLangs) * 100 : 0
            const pct = pctNum.toFixed(1)
            const isUk = item.language.toLowerCase() === 'uk' || item.language.toLowerCase() === 'ua'
            
            return (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={item.language}>
                <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: "bold", textTransform: 'uppercase' }} >
                      {isUk ? '🇺🇦 ' : '🇬🇧 '}{item.language}
                    </Typography>
                    <Typography variant="caption" sx={{ fontWeight: "bold", fontFamily: 'monospace' }} color="primary" >
                      {pct}%
                    </Typography>
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: "bold", fontFamily: 'monospace', mb: 1 }}  >
                    {fmt(item.count)} <Typography component="span" variant="caption" color="text.secondary">users</Typography>
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={pctNum} 
                    sx={{ height: 6, borderRadius: 3, bgcolor: 'background.paper' }} 
                  />
                </Box>
              </Grid>
            )
          })}
        </Grid>
      </Card>

      {/* Top Users DataGrid */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 600 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SparklesIcon color="warning" />
            <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
              Top Users by Interaction Volume ({usersData.top_users.length})
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Advanced sorting & filtering enabled
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <DataGrid
            rows={usersData.top_users}
            columns={columns}
            getRowId={(row) => row.id}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
              sorting: { sortModel: [{ field: 'requests', sort: 'desc' }] }
            }}
            pageSizeOptions={[10, 25, 50]}
            disableRowSelectionOnClick
            sx={{
              border: 0,
              '& .MuiDataGrid-columnHeaders': { bgcolor: 'background.default' },
              '& .MuiDataGrid-cell': { borderBottom: '1px solid rgba(255,255,255,0.05)' },
            }}
          />
        </Box>
      </Card>
    </Box>
  )
}
