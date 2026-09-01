import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme, CssBaseline, alpha } from '@mui/material'
import { App } from './App'
import './index.css'

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#10b981',
      light: '#34d399',
      dark: '#059669',
      contrastText: '#000',
    },
    secondary: {
      main: '#6366f1',
      light: '#818cf8',
      dark: '#4f46e5',
    },
    error: { main: '#f43f5e', dark: '#be123c', light: '#fb7185' },
    warning: { main: '#f59e0b', dark: '#b45309', light: '#fbbf24' },
    success: { main: '#10b981', dark: '#047857', light: '#34d399' },
    background: {
      default: '#080f1a',
      paper: '#0f1d2e',
    },
    divider: 'rgba(148,163,184,0.08)',
    text: {
      primary: '#e2e8f0',
      secondary: '#94a3b8',
    },
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 800, letterSpacing: '-0.02em' },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 700 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    caption: { letterSpacing: '0.03em' },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 10,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'linear-gradient(145deg, rgba(15,29,46,0.98) 0%, rgba(10,20,36,0.92) 100%)',
          border: '1px solid rgba(148,163,184,0.07)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)',
          backdropFilter: 'blur(12px)',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
          '&:hover': {
            borderColor: 'rgba(16,185,129,0.15)',
            boxShadow: '0 12px 40px rgba(0,0,0,0.45), 0 0 0 1px rgba(16,185,129,0.08)',
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: 'linear-gradient(180deg, #080f1a 0%, #0a1628 100%)',
          borderRight: '1px solid rgba(148,163,184,0.07) !important',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: 'rgba(8,15,26,0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(148,163,184,0.07)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          background: 'linear-gradient(145deg, #0f1d2e, #080f1a)',
          border: '1px solid rgba(148,163,184,0.1)',
          borderRadius: 20,
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 999 },
        bar: { borderRadius: 999 },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: {
          borderRadius: '10px !important',
        },
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
