export interface OverviewStats {
  total_users: number
  dau: number
  wau: number
  mau: number
  premium: number
  total_groups: number
  active_alerts: number
  requests_today: number
  requests_week: number
  errors_today: number
  parser_cycles_today: number
  retention_rate: number
}

export interface ActivityPoint {
  date: string
  dau: number
  requests: number
}

export interface UserLanguageStat {
  language: string
  count: number
}

export interface TopUser {
  id: number
  username: string
  language: string
  premium: boolean
  requests: number
  last_active: string | null
}

export interface CollectionStat {
  name: string
  count: number
  size_kb: number
  avg_obj_size_bytes: number
}

export interface DatabaseStats {
  total_size_mb: number
  storage_size_mb: number
  index_size_mb: number
  collections: CollectionStat[]
  num_collections: number
  connections_current: number
  connections_available: number
  mongo_version: string
}

export interface BotStatus {
  service_status: string
  started_at: string | null
  bot_ram_mb: number | null
  bot_cpu_pct: number | null
  bot_pid: number | null
  bot_threads: number | null
  sys_ram_used_gb: number
  sys_ram_total_gb: number
  sys_ram_pct: number
  sys_cpu_pct: number
  sys_cpu_cores: number
  load_avg_1m: number
  load_avg_5m: number
  disk_used_gb: number
  disk_total_gb: number
  disk_pct: number
  os: string
  python_version: string
  hostname: string
  bot_version: string
}

export interface ParserError {
  source: string
  count: number
  last_error: string
  last_seen: string | null
}

export interface ParserStatus {
  fiat: { count: number; last_updated: string | null }
  crypto: { last_updated: string | null }
  stocks: { last_updated: string | null }
  parser_errors: ParserError[]
  cycles_today: number
}

export interface AlertsStats {
  total: number
  active: number
  triggered: number
  top_currencies: { currency: string; count: number }[]
}

export interface GroupItem {
  chat_id: number
  title: string
  is_active: boolean
  member_count: number
  added_at: string | null
}

export interface GroupsStats {
  total: number
  active: number
  inactive: number
  recent: GroupItem[]
}

export interface ErrorLogEntry {
  timestamp: string | null
  level: string
  message: string
}

export interface ConfigData {
  bot?: {
    admin_ids?: number[]
    backup_enabled?: boolean
    version?: string
  }
  database?: {
    mongo_database?: string
    pool_min?: number
    pool_max?: number
  }
  i18n?: {
    supported_languages?: string[]
    default_language?: string
  }
  parser?: {
    auto_update?: boolean
    update_interval_sec?: number
    fiat_source_url?: string
    retry_attempts?: number
    retry_delay_sec?: number
    on_demand_cache_ttl_hours?: number
    crypto_stocks_interval_sec?: number
  }
  security?: {
    rate_limit_requests?: number
    rate_limit_window_sec?: number
    max_message_length?: number
  }
  features?: {
    mini_app_enabled?: boolean
    groups_enabled?: boolean
    inline_mode_enabled?: boolean
  }
  draft?: {
    enabled?: boolean
    loading_threshold_sec?: number
    animation_interval_sec?: number
    preview_delay_sec?: number
  }
  redis?: {
    url?: string
  }
  sentry?: {
    dsn?: string
    environment?: string
  }
}

async function req<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    credentials: 'include',
  })

  if (!res.ok) {
    let errorDetail = 'Request failed: '
    try {
      const errJson = await res.json()
      if (errJson.detail) errorDetail = errJson.detail
      else if (errJson.message) errorDetail = errJson.message
    } catch {}
    const err = new Error(errorDetail) as Error & { status?: number }
    err.status = res.status
    throw err
  }

  return res.json() as Promise<T>
}

export const api = {
  // Auth
  requestOtp: (telegram_id: number) =>
    req<{ ok: boolean; req_id: string; message: string }>('/api/auth/request-otp', {
      method: 'POST',
      body: JSON.stringify({ telegram_id }),
    }),

  verifyOtp: (telegram_id: number, otp: string) =>
    req<{ ok: boolean }>('/api/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ telegram_id, otp }),
    }),

  checkStatus: (req_id: string) =>
    req<{ ok: boolean; status: 'pending' | 'approved' | 'blocked'; message?: string }>(
      `/api/auth/check-status?req_id=${req_id}`
    ),

  logout: () =>
    req<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),

  health: () =>
    req<{ status: string }>('/api/health'),

  // Stats
  getOverview: () => req<OverviewStats>('/api/stats/overview'),
  getActivity: (days: number = 30) => req<{ days: ActivityPoint[] }>(`/api/stats/activity?days=${days}`),
  getUsers: () => req<{ by_language: UserLanguageStat[]; top_users: TopUser[] }>('/api/stats/users'),
  getDatabase: () => req<DatabaseStats>('/api/stats/database'),
  getBotStatus: () => req<BotStatus>('/api/stats/bot'),
  getParserStatus: () => req<ParserStatus>('/api/stats/parser'),
  getAlerts: () => req<AlertsStats>('/api/stats/alerts'),
  getGroups: () => req<GroupsStats>('/api/stats/groups'),
  getErrors: () => req<{ errors: ErrorLogEntry[] }>('/api/stats/errors'),

  // Config & Actions
  getConfig: () => req<ConfigData>('/api/config'),
  updateConfigSection: (section: string, settings: Record<string, any>) =>
    req<{ ok: boolean; message: string }>('/api/config/update', {
      method: 'POST',
      body: JSON.stringify({ section, settings }),
    }),
  patchFeature: (feature: string, value: boolean) =>
    req<{ ok: boolean; feature: string; value: boolean }>('/api/config/features', {
      method: 'PATCH',
      body: JSON.stringify({ feature, value }),
    }),
  restartBot: () =>
    req<{ ok: boolean; message: string }>('/api/actions/restart', { method: 'POST' }),

  // User management (admin)
  exportUserJson: (userId: number) =>
    req<Blob>(`/api/users/${userId}/export`),

  exportUserCsv: (userId: number) =>
    req<Blob>(`/api/users/${userId}/export/csv`),

  deleteUser: (userId: number) =>
    req<{
      ok: boolean
      user_id: number
      alerts_deleted: number
      api_keys_deleted: number
      otps_deleted: number
      message: string
    }>(`/api/users/${userId}`, { method: 'DELETE' }),
}

/** Trigger a file download for user data export (opens browser save dialog). */
export function downloadUserExport(userId: number, format: 'json' | 'csv' = 'json') {
  const url = format === 'csv'
    ? `/api/users/${userId}/export/csv`
    : `/api/users/${userId}/export`
  const a = document.createElement('a')
  a.href = url
  a.download = `user_${userId}_export.${format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
