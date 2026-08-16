import React, { useState, useEffect, useRef } from 'react'
import { api } from '@/api/client'
import {
  Box, Card, Typography, TextField, Button, Alert, CircularProgress
} from '@mui/material'
import {
  Security as ShieldIcon,
  ArrowForward as ArrowRightIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'

interface LoginPageProps {
  onLoginSuccess: () => void
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const [step, setStep] = useState<1 | 2>(1)
  const [telegramId, setTelegramId] = useState('')
  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [reqId, setReqId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [infoMessage, setInfoMessage] = useState<string | null>(null)
  const [pollApproved, setPollApproved] = useState(false)

  const otpInputs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (step !== 2 || !reqId || pollApproved) return

    const interval = setInterval(async () => {
      try {
        const res = await api.checkStatus(reqId)
        if (res.status === 'approved') {
          setPollApproved(true)
          clearInterval(interval)
          setTimeout(() => {
            onLoginSuccess()
          }, 800)
        } else if (res.status === 'blocked') {
          setError(res.message || 'IP address blocked by admin')
          clearInterval(interval)
        }
      } catch {
        // Ignore background polling errors
      }
    }, 2500)

    return () => clearInterval(interval)
  }, [step, reqId, pollApproved, onLoginSuccess])

  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    const idNum = parseInt(telegramId.trim(), 10)
    if (isNaN(idNum) || idNum <= 0) {
      setError('Please enter a valid Telegram User ID')
      return
    }

    try {
      setLoading(true)
      const res = await api.requestOtp(idNum)
      setReqId(res.req_id)
      setStep(2)
      setInfoMessage('OTP sent! Check your Telegram for the 6-digit code or tap [Accept] directly.')
    } catch (err: any) {
      setError(err.message || 'Failed to request OTP')
    } finally {
      setLoading(false)
    }
  }

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return
    const newOtp = [...otp]
    newOtp[index] = value.slice(-1)
    setOtp(newOtp)

    if (value && index < 5) {
      otpInputs.current[index + 1]?.focus()
    }
  }

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpInputs.current[index - 1]?.focus()
    }
  }

  const handleVerifyOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setError(null)
    const code = otp.join('')
    if (code.length < 6) {
      setError('Please enter all 6 digits')
      return
    }

    const idNum = parseInt(telegramId.trim(), 10)
    try {
      setLoading(true)
      await api.verifyOtp(idNum, code)
      onLoginSuccess()
    } catch (err: any) {
      setError(err.message || 'Invalid or expired OTP')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2, bgcolor: 'background.default' }}>
      <Card sx={{ w: '100%', maxWidth: 400, p: 4, display: 'flex', flexDirection: 'column', gap: 3, position: 'relative', overflow: 'hidden' }}>

        <Box sx={{ textAlign: 'center' }}>
          <Box sx={{ display: 'inline-flex', p: 2, borderRadius: 3, bgcolor: 'primary.dark', color: 'primary.light', mb: 2 }}>
            <ShieldIcon fontSize="large" />
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 'bold' }}>Finances Dashboard</Typography>
          <Typography variant="caption" color="text.secondary">Enterprise 2FA Authentication Gate</Typography>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}
        {infoMessage && !error && <Alert severity="info">{infoMessage}</Alert>}
        {pollApproved && (
          <Alert severity="success" icon={<CheckCircleIcon fontSize="inherit" />}>
            Telegram 2FA Approved! Logging in...
          </Alert>
        )}

        {step === 1 && (
          <Box component="form" onSubmit={handleRequestOtp} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Telegram User ID"
              placeholder="e.g. 000000000000"
              value={telegramId}
              onChange={(e) => setTelegramId(e.target.value)}
              required
              fullWidth
              slotProps={{ input: { sx: { fontFamily: 'monospace' } } }}
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={loading || !telegramId.trim()}
              endIcon={loading ? <CircularProgress size={20} color="inherit" /> : <ArrowRightIcon />}
              disableElevation
            >
              Request Login Code
            </Button>
          </Box>
        )}

        {step === 2 && (
          <Box component="form" onSubmit={handleVerifyOtp} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box sx={{ textAlign: 'center' }}>
              <Typography variant="caption" sx={{ fontWeight: 'bold', textTransform: 'uppercase' }} color="text.secondary" >
                Enter 6-Digit OTP
              </Typography>
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, mt: 1 }}>
                {otp.map((digit, i) => (
                  <TextField
                    key={i}
                    inputRef={(el) => (otpInputs.current[i] = el)}
                    value={digit}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)}
                    slotProps={{ htmlInput: { maxLength: 1, style: { textAlign: 'center', fontSize: '1.25rem', fontFamily: 'monospace' } } }}
                    sx={{ width: 44 }}
                  />
                ))}
              </Box>
            </Box>

            <Alert severity="info" icon={<CircularProgress size={16} />}>
              Waiting for Telegram 2FA response...
            </Alert>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={loading || otp.join('').length < 6}
                startIcon={loading && <CircularProgress size={20} color="inherit" />}
                disableElevation
              >
                Verify Code & Enter
              </Button>
              <Button
                onClick={() => {
                  setStep(1)
                  setOtp(['', '', '', '', '', ''])
                  setError(null)
                  setInfoMessage(null)
                }}
                color="inherit"
                size="small"
              >
                Back to Telegram ID entry
              </Button>
            </Box>
          </Box>
        )}
      </Card>
    </Box>
  )
}
