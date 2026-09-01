import React, { useState, useCallback, useEffect } from 'react'
import {
  Box, Card, Typography, Grid, LinearProgress, Chip,
  TextField, InputAdornment, IconButton, Button, Select,
  MenuItem, FormControl, InputLabel, Dialog, DialogTitle,
  DialogContent, DialogActions, DialogContentText, Alert,
  Tooltip, CircularProgress, Divider, Stack, Badge,
  ToggleButtonGroup, ToggleButton,
} from '@mui/material'
import {
  Public as GlobeIcon,
  Stars as SparklesIcon,
  WorkspacePremium as CrownIcon,
  Search as SearchIcon,
  FileDownload as DownloadIcon,
  Delete as DeleteIcon,
  FilterList as FilterIcon,
  Person as PersonIcon,
  Close as CloseIcon,
  Sort as SortIcon,
  CheckCircle as ActiveIcon,
  Notifications as AlertIcon,
  AccountBalanceWallet as PortfolioIcon,
  Clear as ClearIcon,
} from '@mui/icons-material'
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid'
import { TopUser } from '@/api/client'
import { api, downloadUserExport } from '@/api/client'
import { fmt, timeAgo, formatDate } from '@/lib/utils'

interface UsersPageProps {
  initialData: { by_language: any[]; top_users: { items: TopUser[]; total: number; page: number; limit: number; pages: number } } | null
}

// ── Language flag mapping ─────────────────────────────────────────────────────
const LANG_FLAG: Record<string, string> = {
  uk: '🇺🇦', ua: '🇺🇦', en: '🇬🇧', ru: '🇷🇺',
  de: '🇩🇪', fr: '🇫🇷', es: '🇪🇸', pl: '🇵🇱',
  it: '🇮🇹', pt: '🇧🇷', tr: '🇹🇷', ar: '🇸🇦',
}

export const UsersPage: React.FC<UsersPageProps> = ({ initialData }) => {
  // ── Filters state ─────────────────────────────────────────────────────────
  const [search, setSearch]       = useState('')
  const [language, setLanguage]   = useState('')
  const [premium, setPremium]     = useState<'all' | 'true' | 'false'>('all')
  const [sort, setSort]           = useState<'last_active' | 'requests' | 'premium' | 'language'>('last_active')
  const [order, setOrder]         = useState<'asc' | 'desc'>('desc')
  const [page, setPage]           = useState(0)   // DataGrid is 0-indexed
  const [pageSize, setPageSize]   = useState(50)
  const [loading, setLoading]     = useState(false)
  const [data, setData]           = useState(initialData)

  // ── Export/Delete dialog state ────────────────────────────────────────────
  const [selectedUser, setSelectedUser]   = useState<TopUser | null>(null)
  const [exportDialog, setExportDialog]   = useState(false)
  const [deleteDialog, setDeleteDialog]   = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionResult, setActionResult]   = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  // ── Fetch data when filters change ───────────────────────────────────────
  const fetchUsers = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api.getUsers({
        page: page + 1,
        limit: pageSize,
        search: search || undefined,
        language: language || undefined,
        premium: premium === 'all' ? undefined : premium === 'true',
        sort,
        order,
      })
      setData(result)
    } catch (e) {
      console.error('Failed to fetch users', e)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, language, premium, sort, order])

  useEffect(() => {
    const t = setTimeout(fetchUsers, search ? 400 : 0)
    return () => clearTimeout(t)
  }, [fetchUsers])

  const byLang = data?.by_language ?? []
  const topUsers = data?.top_users?.items ?? []
  const totalUsers = data?.top_users?.total ?? 0
  const totalInLangs = byLang.reduce((s, l) => s + l.count, 0)

  // ── Export handler ────────────────────────────────────────────────────────
  const handleExport = (format: 'json' | 'csv') => {
    if (!selectedUser) return
    downloadUserExport(selectedUser.id, format)
    setExportDialog(false)
  }

  // ── Delete handler ────────────────────────────────────────────────────────
  const handleDelete = async () => {
    if (!selectedUser || deleteConfirm !== String(selectedUser.id)) return
    setActionLoading(true)
    setActionResult(null)
    try {
      const r = await api.deleteUser(selectedUser.id)
      setActionResult({ type: 'success', msg: r.message })
      setTimeout(() => {
        setDeleteDialog(false)
        setDeleteConfirm('')
        setActionResult(null)
        setSelectedUser(null)
        fetchUsers()
      }, 2000)
    } catch (e: any) {
      setActionResult({ type: 'error', msg: e.message ?? 'Delete failed' })
    } finally {
      setActionLoading(false)
    }
  }

  // ── Column defs ───────────────────────────────────────────────────────────
  const columns: GridColDef[] = [
    {
      field: 'id',
      headerName: 'Telegram ID',
      width: 140,
      renderCell: (p: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace', opacity: 0.7 }}>
          {p.value}
        </Typography>
      ),
    },
    {
      field: 'username',
      headerName: 'User',
      flex: 1,
      minWidth: 160,
      renderCell: (p: GridRenderCellParams) => {
        const user = p.row as TopUser
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', py: 0.5 }}>
            <Typography variant="body2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
              {user.name || (user.username ? `@${user.username}` : 'Anonymous')}
            </Typography>
            {user.username && user.name && (
              <Typography variant="caption" color="text.secondary">@{user.username}</Typography>
            )}
          </Box>
        )
      },
    },
    {
      field: 'language',
      headerName: 'Lang',
      width: 80,
      renderCell: (p: GridRenderCellParams) => (
        <Chip
          label={`${LANG_FLAG[p.value?.toLowerCase()] ?? '🌐'} ${p.value?.toUpperCase() ?? '?'}`}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 700, fontSize: '0.7rem', borderColor: 'rgba(255,255,255,0.1)' }}
        />
      ),
    },
    {
      field: 'premium',
      headerName: 'Tier',
      width: 110,
      renderCell: (p: GridRenderCellParams) => (
        p.value ? (
          <Chip
            icon={<CrownIcon sx={{ fontSize: '0.9rem !important' }} />}
            label="PREMIUM"
            size="small"
            sx={{
              bgcolor: 'rgba(251,191,36,0.15)',
              color: '#fbbf24',
              border: '1px solid rgba(251,191,36,0.3)',
              fontWeight: 700,
              fontSize: '0.65rem',
            }}
          />
        ) : (
          <Typography variant="caption" color="text.disabled">Free</Typography>
        )
      ),
    },
    {
      field: 'is_active',
      headerName: 'Status',
      width: 90,
      renderCell: (p: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{
            width: 6, height: 6, borderRadius: '50%',
            bgcolor: p.value ? '#10b981' : 'rgba(255,255,255,0.15)',
            boxShadow: p.value ? '0 0 6px #10b981' : 'none',
          }} />
          <Typography variant="caption" color={p.value ? 'success.main' : 'text.disabled'}>
            {p.value ? 'Online' : 'Away'}
          </Typography>
        </Box>
      ),
    },
    {
      field: 'total_requests',
      headerName: 'Requests',
      type: 'number',
      width: 110,
      renderCell: (p: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontWeight: 700, fontFamily: 'monospace' }} color="primary">
          {fmt(p.value as number)}
        </Typography>
      ),
    },
    {
      field: 'alerts_count',
      headerName: 'Alerts',
      type: 'number',
      width: 80,
      renderCell: (p: GridRenderCellParams) => (
        <Chip
          label={p.value}
          size="small"
          sx={{
            bgcolor: p.value > 0 ? 'rgba(34,211,238,0.1)' : 'transparent',
            color: p.value > 0 ? '#22d3ee' : 'text.disabled',
            border: p.value > 0 ? '1px solid rgba(34,211,238,0.2)' : '1px solid transparent',
            fontFamily: 'monospace',
            fontWeight: 700,
            minWidth: 32,
          }}
        />
      ),
    },
    {
      field: 'portfolio_assets',
      headerName: 'Portfolio',
      type: 'number',
      width: 90,
      renderCell: (p: GridRenderCellParams) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace' }} color={p.value > 0 ? 'text.primary' : 'text.disabled'}>
          {p.value > 0 ? `${p.value} assets` : '—'}
        </Typography>
      ),
    },
    {
      field: 'last_active',
      headerName: 'Last Active',
      width: 120,
      renderCell: (p: GridRenderCellParams) => (
        <Tooltip title={formatDate(p.value as string)} placement="top">
          <Typography variant="body2" color="text.secondary">
            {timeAgo(p.value as string)}
          </Typography>
        </Tooltip>
      ),
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 130,
      sortable: false,
      renderCell: (p: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
          <Tooltip title="Export user data">
            <IconButton
              size="small"
              onClick={() => { setSelectedUser(p.row as TopUser); setExportDialog(true) }}
              sx={{ color: '#10b981', '&:hover': { bgcolor: 'rgba(16,185,129,0.1)' } }}
            >
              <DownloadIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete user permanently">
            <IconButton
              size="small"
              onClick={() => { setSelectedUser(p.row as TopUser); setDeleteDialog(true); setDeleteConfirm('') }}
              sx={{ color: '#f43f5e', '&:hover': { bgcolor: 'rgba(244,63,94,0.1)' } }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      ),
    },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Language breakdown */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(16,185,129,0.1)', display: 'flex' }}>
            <GlobeIcon sx={{ color: '#10b981' }} />
          </Box>
          <Box>
            <Typography variant="subtitle1">Language Demographics</Typography>
            <Typography variant="caption" color="text.secondary">
              {totalInLangs.toLocaleString()} users across {byLang.length} languages
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={2}>
          {byLang.map((item) => {
            const pctNum = totalInLangs ? (item.count / totalInLangs) * 100 : 0
            const flag = LANG_FLAG[item.language?.toLowerCase()] ?? '🌐'
            return (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={item.language}>
                <Box sx={{
                  p: 2.5, borderRadius: 3,
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  transition: 'all 0.2s',
                  '&:hover': { borderColor: 'rgba(16,185,129,0.25)', background: 'rgba(16,185,129,0.04)' },
                }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                      <Typography sx={{ fontSize: '1.2rem' }}>{flag}</Typography>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                        {item.language}
                      </Typography>
                    </Box>
                    <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 700 }} color="primary">
                      {pctNum.toFixed(1)}%
                    </Typography>
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: 800, fontFamily: 'monospace', mb: 1.5 }}>
                    {fmt(item.count)}
                    <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 0.5 }}>users</Typography>
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={pctNum}
                    sx={{ height: 5, bgcolor: 'rgba(255,255,255,0.05)', '& .MuiLinearProgress-bar': { background: 'linear-gradient(90deg, #10b981, #2dd4bf)' } }}
                  />
                </Box>
              </Grid>
            )
          })}
        </Grid>
      </Card>

      {/* User table */}
      <Card sx={{ p: 3, display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(251,191,36,0.1)', display: 'flex' }}>
              <SparklesIcon sx={{ color: '#fbbf24' }} />
            </Box>
            <Box>
              <Typography variant="subtitle1">User Management</Typography>
              <Typography variant="caption" color="text.secondary">
                {fmt(totalUsers)} users total · export & delete by ID
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* Filters row */}
        <Box sx={{ display: 'flex', gap: 1.5, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          {/* Search */}
          <TextField
            size="small"
            placeholder="Search by name, @username or ID…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0) }}
            sx={{ flexGrow: 1, minWidth: 220 }}
            slotProps={{
              input: {
                startAdornment: <InputAdornment position="start"><SearchIcon sx={{ fontSize: 18, color: 'text.secondary' }} /></InputAdornment>,
                endAdornment: search ? (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => { setSearch(''); setPage(0) }}>
                      <ClearIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  </InputAdornment>
                ) : undefined,
              }
            }}
          />

          {/* Language */}
          <FormControl size="small" sx={{ minWidth: 110 }}>
            <InputLabel>Language</InputLabel>
            <Select
              value={language}
              label="Language"
              onChange={e => { setLanguage(e.target.value); setPage(0) }}
            >
              <MenuItem value="">All</MenuItem>
              {byLang.map(l => (
                <MenuItem key={l.language} value={l.language}>
                  {LANG_FLAG[l.language?.toLowerCase()] ?? '🌐'} {l.language?.toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Premium */}
          <FormControl size="small" sx={{ minWidth: 100 }}>
            <InputLabel>Tier</InputLabel>
            <Select
              value={premium}
              label="Tier"
              onChange={e => { setPremium(e.target.value as any); setPage(0) }}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="true">⭐ Premium</MenuItem>
              <MenuItem value="false">Free</MenuItem>
            </Select>
          </FormControl>

          {/* Sort */}
          <FormControl size="small" sx={{ minWidth: 130 }}>
            <InputLabel>Sort by</InputLabel>
            <Select
              value={sort}
              label="Sort by"
              onChange={e => setSort(e.target.value as any)}
            >
              <MenuItem value="last_active">Last Active</MenuItem>
              <MenuItem value="requests">Requests</MenuItem>
              <MenuItem value="premium">Premium</MenuItem>
              <MenuItem value="language">Language</MenuItem>
            </Select>
          </FormControl>

          {/* Order toggle */}
          <ToggleButtonGroup
            size="small"
            value={order}
            exclusive
            onChange={(_, v) => v && setOrder(v)}
          >
            <ToggleButton value="desc" sx={{ px: 1.5, fontSize: '0.7rem', fontWeight: 700 }}>↓ DESC</ToggleButton>
            <ToggleButton value="asc"  sx={{ px: 1.5, fontSize: '0.7rem', fontWeight: 700 }}>↑ ASC</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* DataGrid */}
        <Box sx={{ height: 580, width: '100%' }}>
          <DataGrid
            rows={topUsers}
            columns={columns}
            loading={loading}
            getRowId={r => r.id}
            rowCount={totalUsers}
            paginationMode="server"
            paginationModel={{ page, pageSize }}
            onPaginationModelChange={m => { setPage(m.page); setPageSize(m.pageSize) }}
            pageSizeOptions={[25, 50, 100]}
            disableRowSelectionOnClick
            getRowClassName={r => (r.row as TopUser).is_active ? 'row-active' : ''}
            sx={{
              border: 0,
              '& .MuiDataGrid-columnHeaders': {
                bgcolor: 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
              },
              '& .MuiDataGrid-cell': { borderBottom: '1px solid rgba(255,255,255,0.04)' },
              '& .MuiDataGrid-row:hover': { bgcolor: 'rgba(16,185,129,0.04)' },
              '& .row-active': { bgcolor: 'rgba(16,185,129,0.025)' },
              '& .MuiDataGrid-footerContainer': { borderTop: '1px solid rgba(255,255,255,0.06)' },
            }}
          />
        </Box>
      </Card>

      {/* ── Export dialog ──────────────────────────────────────────────────── */}
      <Dialog open={exportDialog} onClose={() => setExportDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(16,185,129,0.15)', display: 'flex' }}>
            <DownloadIcon sx={{ color: '#10b981' }} />
          </Box>
          Export User Data
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Export all data for <strong>{selectedUser?.name ?? `@${selectedUser?.username}` ?? `ID ${selectedUser?.id}`}</strong>.
            Includes profile, portfolio, alerts, and API key metadata (secrets excluded).
          </DialogContentText>
          <Stack direction="row" spacing={1.5}>
            <Button
              fullWidth
              variant="contained"
              color="primary"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('json')}
              sx={{ py: 1.5 }}
            >
              Download JSON
            </Button>
            <Button
              fullWidth
              variant="outlined"
              color="primary"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('csv')}
              sx={{ py: 1.5 }}
            >
              Download CSV
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialog(false)} color="inherit">Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* ── Delete dialog ──────────────────────────────────────────────────── */}
      <Dialog open={deleteDialog} onClose={() => !actionLoading && setDeleteDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ p: 1, borderRadius: 2, bgcolor: 'rgba(244,63,94,0.15)', display: 'flex' }}>
            <DeleteIcon sx={{ color: '#f43f5e' }} />
          </Box>
          Delete User Permanently
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            This will <strong>permanently delete</strong> all data for user{' '}
            <Typography component="span" sx={{ fontFamily: 'monospace', color: '#f43f5e' }}>
              {selectedUser?.id}
            </Typography>
            , including their portfolio, alerts, and API keys. This action is{' '}
            <strong>irreversible</strong>.
          </DialogContentText>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Type the user ID to confirm:
          </Typography>
          <TextField
            fullWidth
            size="small"
            placeholder={String(selectedUser?.id ?? '')}
            value={deleteConfirm}
            onChange={e => setDeleteConfirm(e.target.value)}
            disabled={actionLoading}
            sx={{ fontFamily: 'monospace' }}
            error={!!deleteConfirm && deleteConfirm !== String(selectedUser?.id)}
            helperText={deleteConfirm && deleteConfirm !== String(selectedUser?.id) ? 'ID does not match' : ''}
          />
          {actionResult && (
            <Alert severity={actionResult.type} sx={{ mt: 2 }}>{actionResult.msg}</Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDeleteDialog(false); setDeleteConfirm('') }} disabled={actionLoading} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            disabled={actionLoading || deleteConfirm !== String(selectedUser?.id)}
            variant="contained"
            color="error"
            startIcon={actionLoading ? <CircularProgress size={14} color="inherit" /> : <DeleteIcon />}
          >
            {actionLoading ? 'Deleting…' : 'Delete Forever'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
