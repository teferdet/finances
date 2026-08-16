import React, { useState, useEffect } from 'react'
import { ConfigData, api } from '@/api/client'
import {
  Box, Card, Typography, Grid, Switch, Button, TextField, Snackbar, Alert,
  Accordion, AccordionSummary, AccordionDetails, Divider
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  Save as SaveIcon,
  Security as ShieldIcon,
  Memory as CpuIcon,
  AutoAwesome as SparklesIcon,
} from '@mui/icons-material'

interface ConfigPageProps {
  config: ConfigData | null
  onConfigUpdated: () => void
}

export const ConfigPage: React.FC<ConfigPageProps> = ({ config, onConfigUpdated }) => {
  const [formData, setFormData] = useState<ConfigData>({})
  const [savingSection, setSavingSection] = useState<string | null>(null)
  const [toast, setToast] = useState<{ message: string; isError?: boolean } | null>(null)

  useEffect(() => {
    if (config) setFormData(JSON.parse(JSON.stringify(config)))
  }, [config])

  if (!config) {
    return (
      <Box sx={{ p: 4, textAlign: 'center', color: 'text.secondary' }}>
        <Typography variant="body2">Loading runtime configuration…</Typography>
      </Box>
    )
  }

  const showToast = (message: string, isError: boolean = false) => {
    setToast({ message, isError })
  }

  const handleToggleFeature = async (featureKey: string, currentValue: boolean) => {
    try {
      const nextValue = !currentValue
      await api.patchFeature(featureKey, nextValue)
      setFormData((prev) => ({
        ...prev,
        features: {
          ...(prev.features || {}),
          [featureKey]: nextValue,
        },
      }))
      showToast(`Feature '${featureKey}' updated to ${nextValue}`)
      onConfigUpdated()
    } catch (err: any) {
      showToast(err.message || 'Failed to toggle feature', true)
    }
  }

  const handleSaveSection = async (section: string, sectionData: Record<string, any>) => {
    try {
      setSavingSection(section)
      await api.updateConfigSection(section, sectionData)
      showToast(`Section '${section}' successfully saved!`)
      onConfigUpdated()
    } catch (err: any) {
      showToast(err.message || 'Failed to save', true)
    } finally {
      setSavingSection(null)
    }
  }

  const featureFlags = [
    {
      key: 'groups_enabled',
      label: 'Telegram Groups',
      desc: 'Enable responding to /rate & /crypto in community chats',
      val: formData.features?.groups_enabled ?? true,
    },
    {
      key: 'inline_mode_enabled',
      label: 'Inline Mode',
      desc: 'Allow @botname inline queries in any chat',
      val: formData.features?.inline_mode_enabled ?? true,
    },
    {
      key: 'mini_app_enabled',
      label: 'Telegram Mini App',
      desc: 'Open web view UI button for mobile clients',
      val: formData.features?.mini_app_enabled ?? false,
    },
  ]

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Snackbar
        open={!!toast}
        autoHideDuration={4000}
        onClose={() => setToast(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setToast(null)} severity={toast?.isError ? 'error' : 'success'} variant="filled">
          {toast?.message}
        </Alert>
      </Snackbar>

      {/* Feature Flags */}
      <Card sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <SparklesIcon color="primary" />
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Live Feature Flags</Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 3 }}>
          Toggles update instantly in memory without restart
        </Typography>

        <Grid container spacing={3}>
          {featureFlags.map((f) => (
            <Grid size={{ xs: 12, sm: 4 }} key={f.key}>
              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'background.default', border: '1px solid', borderColor: 'divider', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>{f.label}</Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>{f.desc}</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pt: 1, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <Typography variant="caption" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}  color={f.val ? 'success.main' : 'text.secondary'}>
                    {f.val ? 'ENABLED' : 'DISABLED'}
                  </Typography>
                  <Switch
                    checked={f.val}
                    onChange={() => handleToggleFeature(f.key, f.val)}
                    color="primary"
                  />
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Card>

      {/* Security Settings */}
      <Accordion defaultExpanded sx={{ bgcolor: 'background.paper', borderRadius: 2, '&:before': { display: 'none' } }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <ShieldIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Security & Anti-Spam Limits</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Divider sx={{ mb: 3 }} />
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Max Requests Limit"
                type="number"
                fullWidth
                size="small"
                value={formData.security?.rate_limit_requests ?? 30}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    security: { ...(prev.security || {}), rate_limit_requests: parseInt(e.target.value, 10) || 30 },
                  }))
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Rate Limit Window (sec)"
                type="number"
                fullWidth
                size="small"
                value={formData.security?.rate_limit_window_sec ?? 60}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    security: { ...(prev.security || {}), rate_limit_window_sec: parseInt(e.target.value, 10) || 60 },
                  }))
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Max Message Length"
                type="number"
                fullWidth
                size="small"
                value={formData.security?.max_message_length ?? 1000}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    security: { ...(prev.security || {}), max_message_length: parseInt(e.target.value, 10) || 1000 },
                  }))
                }
              />
            </Grid>
          </Grid>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => handleSaveSection('security', formData.security || {})}
              disabled={savingSection === 'security'}
              disableElevation
            >
              {savingSection === 'security' ? 'Saving…' : 'Save Security'}
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Parser Settings */}
      <Accordion defaultExpanded sx={{ bgcolor: 'background.paper', borderRadius: 2, '&:before': { display: 'none' }, mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <CpuIcon color="primary" />
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>Background Parser Timers</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Divider sx={{ mb: 3 }} />
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Fiat Interval (sec)"
                type="number"
                fullWidth
                size="small"
                value={formData.parser?.update_interval_sec ?? 3600}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    parser: { ...(prev.parser || {}), update_interval_sec: parseInt(e.target.value, 10) || 3600 },
                  }))
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Crypto & Stocks Interval (sec)"
                type="number"
                fullWidth
                size="small"
                value={formData.parser?.crypto_stocks_interval_sec ?? 10800}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    parser: { ...(prev.parser || {}), crypto_stocks_interval_sec: parseInt(e.target.value, 10) || 10800 },
                  }))
                }
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField
                label="Retry Attempts"
                type="number"
                fullWidth
                size="small"
                value={formData.parser?.retry_attempts ?? 3}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    parser: { ...(prev.parser || {}), retry_attempts: parseInt(e.target.value, 10) || 3 },
                  }))
                }
              />
            </Grid>
          </Grid>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={() => handleSaveSection('parser', formData.parser || {})}
              disabled={savingSection === 'parser'}
              disableElevation
            >
              {savingSection === 'parser' ? 'Saving…' : 'Save Parser Settings'}
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  )
}
