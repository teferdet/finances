import React, { useState } from 'react'
import { ErrorLogEntry } from '@/api/client'
import {
  Box, Card, Typography, TextField, Button, Dialog, DialogTitle,
  DialogContent, DialogActions, Chip, ToggleButtonGroup, ToggleButton
} from '@mui/material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import { Terminal as TerminalIcon, ContentCopy as CopyIcon, Check as CheckIcon } from '@mui/icons-material'

interface ErrorsPageProps {
  errors: ErrorLogEntry[]
}

export const ErrorsPage: React.FC<ErrorsPageProps> = ({ errors }) => {
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'ERROR' | 'WARNING' | 'CRITICAL' | 'INFO'>('ALL')
  const [search, setSearch] = useState('')
  const [copied, setCopied] = useState(false)
  const [selectedError, setSelectedError] = useState<ErrorLogEntry | null>(null)

  const handleFilterChange = (event: React.MouseEvent<HTMLElement>, newFilter: string | null) => {
    if (newFilter !== null) setLevelFilter(newFilter as any)
  }

  const filtered = errors.filter((item) => {
    if (levelFilter !== 'ALL' && item.level.toUpperCase() !== levelFilter) return false
    if (search.trim() && !item.message.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const handleCopy = () => {
    const text = filtered.map((e) => `[${e.timestamp}] [${e.level}] ${e.message}`).join('\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const columns: GridColDef[] = [
    { field: 'timestamp', headerName: 'Timestamp', width: 200, renderCell: (p) => <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color="text.secondary">{p.value}</Typography> },
    { 
      field: 'level', 
      headerName: 'Level', 
      width: 120,
      renderCell: (p) => {
        const lvl = p.value as string
        const color = lvl === 'ERROR' || lvl === 'CRITICAL' ? 'error' : lvl === 'WARNING' ? 'warning' : 'info'
        return <Chip label={lvl} size="small" color={color} variant="outlined" sx={{ fontWeight: 'bold' }} />
      }
    },
    { field: 'message', headerName: 'Message', flex: 1, renderCell: (p) => <Typography variant="body2" sx={{ fontFamily: 'monospace' }} noWrap>{p.value}</Typography> }
  ]

  // Convert for DataGrid id requirement
  const rows = filtered.map((f, i) => ({ id: i, ...f }))

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Controls Bar */}
      <Card sx={{ p: 2, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', justifyContent: 'space-between' }}>
        <ToggleButtonGroup
          color="primary"
          value={levelFilter}
          exclusive
          onChange={handleFilterChange}
          size="small"
        >
          {['ALL', 'ERROR', 'CRITICAL', 'WARNING', 'INFO'].map(lvl => (
            <ToggleButton key={lvl} value={lvl} sx={{ fontWeight: 'bold' }}>{lvl}</ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1, maxWidth: 500 }}>
          <TextField
            placeholder="Search error messages…"
            size="small"
            fullWidth
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{ input: { sx: { fontFamily: 'monospace' } } }}
          />
          <Button
            variant="outlined"
            startIcon={copied ? <CheckIcon /> : <CopyIcon />}
            onClick={handleCopy}
            disabled={filtered.length === 0}
            color={copied ? "success" : "inherit"}
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </Box>
      </Card>

      {/* Log Feed */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column', height: 600 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <TerminalIcon color="error" />
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Error Stream ({filtered.length} entries)</Typography>
        </Box>

        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <DataGrid
            rows={rows}
            columns={columns}
            onRowClick={(params) => setSelectedError(params.row as ErrorLogEntry)}
            initialState={{
              pagination: { paginationModel: { pageSize: 25 } },
            }}
            pageSizeOptions={[25, 50, 100]}
            disableRowSelectionOnClick
            sx={{
              border: 0,
              cursor: 'pointer',
              '& .MuiDataGrid-columnHeaders': { bgcolor: 'background.default' },
            }}
          />
        </Box>
      </Card>

      {/* Details Dialog */}
      <Dialog open={!!selectedError} onClose={() => setSelectedError(null)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Chip 
              label={selectedError?.level} 
              color={selectedError?.level === 'ERROR' || selectedError?.level === 'CRITICAL' ? 'error' : 'warning'} 
              variant="filled" 
              size="small" 
              sx={{ fontWeight: 'bold' }} 
            />
            <Typography variant="caption" sx={{ fontFamily: 'monospace' }} color="text.secondary">
              {selectedError?.timestamp}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <Box
            component="pre"
            sx={{
              p: 2,
              bgcolor: '#000',
              color: '#10b981',
              borderRadius: 2,
              overflowX: 'auto',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              whiteSpace: 'pre-wrap'
            }}
          >
            {selectedError?.message}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedError(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
