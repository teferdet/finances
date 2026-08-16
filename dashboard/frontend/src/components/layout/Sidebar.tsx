import React from 'react'
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
  Chip,
  Divider,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  SmartToy as BotIcon,
  Storage as DatabaseIcon,
  Memory as CpuIcon,
  NotificationsActive as BellIcon,
  Groups as GroupsIcon,
  WarningAmber as AlertTriangleIcon,
  PeopleAlt as UsersIcon,
  Settings as SettingsIcon,
  Security as ShieldCheckIcon,
} from '@mui/icons-material'

export type PageId =
  | 'overview'
  | 'bot'
  | 'database'
  | 'parser'
  | 'alerts'
  | 'groups'
  | 'errors'
  | 'users'
  | 'config'

interface SidebarProps {
  currentPage: PageId
  onSelectPage: (page: PageId) => void
  botStatus?: string
  errorCount?: number
}

interface NavItem {
  id: PageId
  label: string
  icon: React.ElementType
  badge?: number | string
}

const DRAWER_WIDTH = 260

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  botStatus = 'active',
  errorCount = 0,
}) => {
  const navItems: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: DashboardIcon },
    { id: 'bot', label: 'Bot & System', icon: BotIcon },
    { id: 'database', label: 'Database', icon: DatabaseIcon },
    { id: 'parser', label: 'Parsers & Rates', icon: CpuIcon },
    { id: 'alerts', label: 'Price Alerts', icon: BellIcon },
    { id: 'groups', label: 'Telegram Groups', icon: GroupsIcon },
    { id: 'errors', label: 'Error Logs', icon: AlertTriangleIcon, badge: errorCount > 0 ? errorCount : undefined },
    { id: 'users', label: 'Users & Activity', icon: UsersIcon },
    { id: 'config', label: 'Configuration', icon: SettingsIcon },
  ]

  const isOnline = botStatus === 'active'

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: 'background.paper',
          borderRight: '1px solid rgba(255, 255, 255, 0.08)',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            background: 'linear-gradient(45deg, #10b981 30%, #2dd4bf 90%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#000',
            fontWeight: 'bold',
            boxShadow: '0 4px 10px rgba(16, 185, 129, 0.3)',
          }}
        >
          💎
        </Box>
        <Box>
          <Typography variant="subtitle1"  sx={{ fontWeight: 'bold',  lineHeight: 1.2 }}>
            Finances Bot
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
            v6.0 Enterprise
          </Typography>
        </Box>
      </Box>

      <Box sx={{ px: 2, pb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 1,
            borderRadius: 1,
            bgcolor: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.05)',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: isOnline ? 'success.main' : 'error.main',
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'medium' }}>
              Daemon:
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ fontWeight: 'bold', fontFamily: 'monospace', textTransform: 'uppercase' }}  >
            {botStatus}
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />

      <List sx={{ px: 1, flex: 1, pt: 2 }}>
        {navItems.map((item) => {
          const active = currentPage === item.id
          return (
            <ListItem key={item.id} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={() => onSelectPage(item.id)}
                selected={active}
                sx={{
                  borderRadius: 2,
                  py: 1,
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: '#000',
                    '&:hover': { bgcolor: 'primary.dark' },
                    '& .MuiListItemIcon-root': { color: '#000' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: active ? '#000' : 'text.secondary' }}>
                  <item.icon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  slotProps={{ primary: { sx: { fontSize: '0.875rem', fontWeight: active ? 600 : 500 } } }}
                />
                {item.badge && (
                  <Chip
                    label={item.badge}
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: '0.65rem',
                      fontWeight: 'bold',
                      fontFamily: 'monospace',
                      bgcolor: active ? 'rgba(0,0,0,0.2)' : 'error.dark',
                      color: active ? '#000' : 'error.contrastText',
                    }}
                  />
                )}
              </ListItemButton>
            </ListItem>
          )
        })}
      </List>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.05)' }} />
      <Box sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            p: 1.5,
            borderRadius: 2,
            bgcolor: 'rgba(255,255,255,0.03)',
          }}
        >
          <ShieldCheckIcon fontSize="small" color="primary" />
          <Typography variant="caption" color="text.secondary">
            2FA OTP Secured
          </Typography>
        </Box>
      </Box>
    </Drawer>
  )
}
