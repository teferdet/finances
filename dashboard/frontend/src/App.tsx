import React, { useState, useEffect, useCallback } from 'react'
import { Box, Typography, CircularProgress } from '@mui/material'
import { api, OverviewStats, ActivityPoint, BotStatus, DatabaseStats, ParserStatus, AlertsStats, GroupsStats, ErrorLogEntry, ConfigData, UserLanguageStat, TopUser } from '@/api/client'
import { Sidebar, PageId } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { LoginPage } from '@/components/auth/LoginPage'
import { OverviewPage } from '@/components/pages/OverviewPage'
import { BotStatusPage } from '@/components/pages/BotStatusPage'
import { DatabasePage } from '@/components/pages/DatabasePage'
import { ParserPage } from '@/components/pages/ParserPage'
import { AlertsPage } from '@/components/pages/AlertsPage'
import { GroupsPage } from '@/components/pages/GroupsPage'
import { ErrorsPage } from '@/components/pages/ErrorsPage'
import { UsersPage } from '@/components/pages/UsersPage'
import { ConfigPage } from '@/components/pages/ConfigPage'

export const App: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(true)
  const [currentPage, setCurrentPage] = useState<PageId>('overview')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null)

  // Data stores
  const [overview, setOverview] = useState<OverviewStats | null>(null)
  const [activity, setActivity] = useState<ActivityPoint[]>([])
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)
  const [databaseStats, setDatabaseStats] = useState<DatabaseStats | null>(null)
  const [parserStatus, setParserStatus] = useState<ParserStatus | null>(null)
  const [alertsStats, setAlertsStats] = useState<AlertsStats | null>(null)
  const [groupsStats, setGroupsStats] = useState<GroupsStats | null>(null)
  const [errors, setErrors] = useState<ErrorLogEntry[]>([])
  const [usersData, setUsersData] = useState<{ by_language: UserLanguageStat[]; top_users: TopUser[] } | null>(null)
  const [config, setConfig] = useState<ConfigData | null>(null)

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as PageId
      if (['overview', 'bot', 'database', 'parser', 'alerts', 'groups', 'errors', 'users', 'config'].includes(hash)) {
        setCurrentPage(hash)
      }
    }
    handleHashChange()
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const handleSelectPage = (page: PageId) => {
    setCurrentPage(page)
    window.location.hash = page
  }

  // Fetch data for the currently active page
  const fetchPageData = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      setIsRefreshing(true)
      // Always fetch overview and bot status for sidebar pills and headers
      const [ov, bot] = await Promise.all([
        api.getOverview().catch(() => null),
        api.getBotStatus().catch(() => null),
      ])
      if (ov) setOverview(ov)
      if (bot) setBotStatus(bot)

      // Page-specific fetches
      if (currentPage === 'overview') {
        const act = await api.getActivity(30)
        setActivity(act.days || [])
      } else if (currentPage === 'database') {
        const db = await api.getDatabase()
        setDatabaseStats(db)
      } else if (currentPage === 'parser') {
        const p = await api.getParserStatus()
        setParserStatus(p)
      } else if (currentPage === 'alerts') {
        const a = await api.getAlerts()
        setAlertsStats(a)
      } else if (currentPage === 'groups') {
        const g = await api.getGroups()
        setGroupsStats(g)
      } else if (currentPage === 'errors') {
        const errs = await api.getErrors()
        setErrors(errs.errors || [])
      } else if (currentPage === 'users') {
        const u = await api.getUsers()
        setUsersData(u)
      } else if (currentPage === 'config') {
        const cfg = await api.getConfig()
        setConfig(cfg)
      }
      setLastRefreshTime(new Date())
    } catch (err: any) {
      if (err?.status === 401) {
        // setIsAuthenticated(false)
      }
    } finally {
      setIsRefreshing(false)
    }
  }, [isAuthenticated, currentPage])

  // Initial Auth Check
  useEffect(() => {
    const checkAuth = async () => {
      try {
        await api.getOverview()
        setIsAuthenticated(true)
      } catch (err: any) {
        // setIsAuthenticated(false)
      }
    }
    checkAuth()
  }, [])

  // Refetch when authenticated or page changes
  useEffect(() => {
    if (isAuthenticated) {
      fetchPageData()
    }
  }, [isAuthenticated, currentPage, fetchPageData])

  // Auto-refresh interval (30s)
  useEffect(() => {
    if (!isAuthenticated) return
    const timer = setInterval(() => {
      fetchPageData()
    }, 30000)
    return () => clearInterval(timer)
  }, [isAuthenticated, fetchPageData])

  const handleLogout = async () => {
    try {
      await api.logout()
    } finally {
      // setIsAuthenticated(false)
    }
  }

  const handleRestartBot = async () => {
    await api.restartBot()
    setTimeout(() => {
      fetchPageData()
    }, 3000)
  }

  // Loading initial state
  if (isAuthenticated === null) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
        <CircularProgress color="primary" />
        <Typography variant="caption" sx={{ fontFamily: 'monospace' }} color="text.secondary">
          Initializing Finances Dashboard...
        </Typography>
      </Box>
    )
  }

  // Login Gate
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={() => setIsAuthenticated(true)} />
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar
        currentPage={currentPage}
        onSelectPage={handleSelectPage}
        botStatus={botStatus?.service_status || 'active'}
        errorCount={overview?.errors_today || 0}
      />

      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Header
          currentPage={currentPage}
          onRefresh={fetchPageData}
          onLogout={handleLogout}
          onRestartBot={handleRestartBot}
          isRefreshing={isRefreshing}
          lastRefreshTime={lastRefreshTime}
        />

        <Box component="main" sx={{ flexGrow: 1, p: 3, overflowY: 'auto' }}>
          <Box sx={{ maxWidth: 'lg', mx: 'auto', width: '100%' }}>
            {currentPage === 'overview' && <OverviewPage overview={overview} activity={activity} />}
            {currentPage === 'bot' && <BotStatusPage status={botStatus} />}
            {currentPage === 'database' && <DatabasePage stats={databaseStats} />}
            {currentPage === 'parser' && <ParserPage status={parserStatus} />}
            {currentPage === 'alerts' && <AlertsPage stats={alertsStats} />}
            {currentPage === 'groups' && <GroupsPage stats={groupsStats} />}
            {currentPage === 'errors' && <ErrorsPage errors={errors} />}
            {currentPage === 'users' && <UsersPage usersData={usersData} />}
            {currentPage === 'config' && <ConfigPage config={config} onConfigUpdated={fetchPageData} />}
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
