import React from 'react'
import { DatabaseStats } from '@/api/client'
import { fmt } from '@/lib/utils'
import { Box, Card, Typography, Grid, Chip } from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import {
  Storage as DatabaseIcon,
  Layers as LayersIcon,
  Dns as HardDriveIcon,
  Timeline as ActivityIcon,
} from '@mui/icons-material'

interface DatabasePageProps {
  stats: DatabaseStats | null
}

export const DatabasePage: React.FC<DatabasePageProps> = ({ stats }) => {
  if (!stats) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading database metrics…</Typography>
      </Box>
    )
  }

  const columns: GridColDef[] = [
    { 
      field: 'name', 
      headerName: 'Collection Name', 
      flex: 1,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'primary.main' }} />
          <Typography variant="body2" sx={{ fontWeight: 'bold' }}>{params.value}</Typography>
        </Box>
      )
    },
    { 
      field: 'count', 
      headerName: 'Document Count', 
      width: 180,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }} color="primary" >
          {fmt(params.value)}
        </Typography>
      )
    },
    { 
      field: 'size_kb', 
      headerName: 'Size', 
      width: 150,
      renderCell: (params: GridRenderCellParams) => {
        const val = params.value as number
        return (
          <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary">
            {val > 1024 ? `${(val / 1024).toFixed(2)} MB` : `${val} KB`}
          </Typography>
        )
      }
    },
    { 
      field: 'avg_obj_size_bytes', 
      headerName: 'Avg Object Size', 
      width: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary">
          {params.value} bytes
        </Typography>
      )
    },
  ]

  const rows = stats.collections.map((col, index) => ({ id: index, ...col }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top summary cards */}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Data Size
              </Typography>
              <DatabaseIcon color="primary" fontSize="small" />
            </Box>
            <Typography variant="h5"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {stats.total_size_mb} MB
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Storage: {stats.storage_size_mb} MB
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Index Size
              </Typography>
              <LayersIcon sx={{ color: '#2dd4bf' }} fontSize="small" />
            </Box>
            <Typography variant="h5"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {stats.index_size_mb} MB
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Optimized query B-trees
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Total Collections
              </Typography>
              <HardDriveIcon color="info" fontSize="small" />
            </Box>
            <Typography variant="h5"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {stats.num_collections}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              MongoDB v{stats.mongo_version}
            </Typography>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <Card sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} >
                Client Connections
              </Typography>
              <ActivityIcon color="secondary" fontSize="small" />
            </Box>
            <Typography variant="h5"  sx={{ fontFamily: 'monospace', fontWeight: 'bold',  mb: 0.5 }} >
              {stats.connections_current}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {stats.connections_available} pool available
            </Typography>
          </Card>
        </Grid>
      </Grid>

      {/* Collections Table */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 500 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <LayersIcon color="primary" />
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
            MongoDB Collections ({stats.collections.length})
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <DataGrid
            rows={rows}
            columns={columns}
            initialState={{
              pagination: { paginationModel: { pageSize: 10 } },
              sorting: { sortModel: [{ field: 'count', sort: 'desc' }] }
            }}
            pageSizeOptions={[10, 25]}
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
