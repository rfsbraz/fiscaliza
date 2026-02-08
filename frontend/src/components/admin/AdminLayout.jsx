import { useState, createContext, useContext } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Terminal, Database, AlertTriangle, Activity, Settings,
  ChevronLeft, ChevronRight, Server, FileText, Cpu,
  HardDrive, Wifi, WifiOff, Clock, BarChart3, Layers
} from 'lucide-react'

// Admin context for shared state
const AdminContext = createContext(null)
export const useAdmin = () => useContext(AdminContext)

// Design tokens - Industrial Command Center aesthetic
const tokens = {
  // IBM Plex Mono for authentic terminal feel
  font: "'IBM Plex Mono', 'JetBrains Mono', 'Fira Code', monospace",

  colors: {
    // Backgrounds - deep space blue-black
    bg: {
      primary: '#030708',
      secondary: '#0a1014',
      tertiary: '#101820',
      elevated: '#182028',
      hover: 'rgba(0, 255, 159, 0.05)',
    },
    // Phosphor green as primary accent
    accent: {
      primary: '#00ff9f',
      secondary: '#00b4ff',
      tertiary: '#ff9f00',
      danger: '#ff3366',
      muted: 'rgba(0, 255, 159, 0.4)',
    },
    // Text hierarchy
    text: {
      primary: '#e0f0e8',
      secondary: '#7a8f85',
      muted: '#4a5f55',
      inverse: '#030708',
    },
    // Border and line colors
    border: {
      primary: 'rgba(0, 255, 159, 0.15)',
      secondary: 'rgba(0, 255, 159, 0.08)',
      glow: 'rgba(0, 255, 159, 0.3)',
    }
  }
}

// CRT scan line effect overlay
const ScanLines = () => (
  <div
    className="fixed inset-0 pointer-events-none z-50"
    style={{
      background: `repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 0, 0, 0.03) 2px,
        rgba(0, 0, 0, 0.03) 4px
      )`,
      mixBlendMode: 'multiply'
    }}
  />
)

// Subtle vignette effect
const Vignette = () => (
  <div
    className="fixed inset-0 pointer-events-none z-40"
    style={{
      background: 'radial-gradient(ellipse at center, transparent 0%, rgba(0,0,0,0.4) 100%)'
    }}
  />
)

// Grid background with glow
const GridBackground = () => (
  <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
    {/* Base grid */}
    <div
      className="absolute inset-0 opacity-[0.04]"
      style={{
        backgroundImage: `
          linear-gradient(${tokens.colors.accent.primary} 1px, transparent 1px),
          linear-gradient(90deg, ${tokens.colors.accent.primary} 1px, transparent 1px)
        `,
        backgroundSize: '60px 60px'
      }}
    />
    {/* Top glow */}
    <div
      className="absolute inset-0"
      style={{
        background: `radial-gradient(ellipse at 50% -20%, ${tokens.colors.accent.muted} 0%, transparent 60%)`
      }}
    />
    {/* Corner accents */}
    <div
      className="absolute top-0 left-0 w-32 h-32"
      style={{
        background: `linear-gradient(135deg, ${tokens.colors.accent.muted} 0%, transparent 60%)`
      }}
    />
  </div>
)

// Connection status indicator
const ConnectionStatus = ({ isConnected }) => (
  <div className="flex items-center gap-2">
    <div
      className={`w-2 h-2 rounded-full ${isConnected ? 'animate-pulse' : ''}`}
      style={{
        backgroundColor: isConnected ? tokens.colors.accent.primary : tokens.colors.accent.danger,
        boxShadow: isConnected
          ? `0 0 8px ${tokens.colors.accent.primary}`
          : `0 0 8px ${tokens.colors.accent.danger}`
      }}
    />
    <span
      className="text-xs uppercase tracking-wider"
      style={{
        color: isConnected ? tokens.colors.accent.primary : tokens.colors.accent.danger,
        fontFamily: tokens.font
      }}
    >
      {isConnected ? 'ONLINE' : 'OFFLINE'}
    </span>
  </div>
)

// Navigation item
const NavItem = ({ to, icon: Icon, label, collapsed, badge }) => {
  const location = useLocation()
  const isActive = location.pathname === to

  return (
    <NavLink to={to}>
      <motion.div
        whileHover={{ x: collapsed ? 0 : 4 }}
        className={`
          relative flex items-center gap-3 px-3 py-2.5 rounded-lg
          transition-all duration-200 group cursor-pointer
        `}
        style={{
          backgroundColor: isActive ? tokens.colors.bg.hover : 'transparent',
          borderLeft: isActive ? `2px solid ${tokens.colors.accent.primary}` : '2px solid transparent',
        }}
      >
        {/* Active glow effect */}
        {isActive && (
          <div
            className="absolute inset-0 rounded-lg opacity-20"
            style={{
              background: `linear-gradient(90deg, ${tokens.colors.accent.primary}, transparent)`
            }}
          />
        )}

        <Icon
          className="h-4 w-4 flex-shrink-0 relative z-10"
          style={{
            color: isActive ? tokens.colors.accent.primary : tokens.colors.text.secondary,
          }}
        />

        <AnimatePresence>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="text-xs uppercase tracking-wider whitespace-nowrap overflow-hidden relative z-10"
              style={{
                fontFamily: tokens.font,
                color: isActive ? tokens.colors.text.primary : tokens.colors.text.secondary,
              }}
            >
              {label}
            </motion.span>
          )}
        </AnimatePresence>

        {badge && !collapsed && (
          <span
            className="ml-auto px-1.5 py-0.5 rounded text-[10px]"
            style={{
              backgroundColor: tokens.colors.accent.danger,
              color: tokens.colors.text.inverse,
              fontFamily: tokens.font
            }}
          >
            {badge}
          </span>
        )}
      </motion.div>
    </NavLink>
  )
}

// Section divider in nav
const NavSection = ({ label, collapsed }) => (
  <div className="px-3 py-2 mt-4 first:mt-0">
    {!collapsed && (
      <span
        className="text-[10px] uppercase tracking-widest"
        style={{
          color: tokens.colors.text.muted,
          fontFamily: tokens.font
        }}
      >
        {label}
      </span>
    )}
    {collapsed && <div className="h-px" style={{ backgroundColor: tokens.colors.border.secondary }} />}
  </div>
)

// Main Admin Layout
const AdminLayout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [isConnected, setIsConnected] = useState(true)
  const [currentTime, setCurrentTime] = useState(new Date())

  // Update clock
  useState(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(interval)
  })

  const contextValue = {
    tokens,
    isConnected,
    setIsConnected
  }

  return (
    <AdminContext.Provider value={contextValue}>
      <div
        className="h-screen flex overflow-hidden"
        style={{
          backgroundColor: tokens.colors.bg.primary,
          fontFamily: tokens.font
        }}
      >
        <ScanLines />
        <Vignette />
        <GridBackground />

        {/* Sidebar */}
        <motion.aside
          initial={false}
          animate={{ width: collapsed ? 60 : 220 }}
          className="relative z-20 flex flex-col border-r flex-shrink-0 overflow-hidden"
          style={{
            backgroundColor: tokens.colors.bg.secondary,
            borderColor: tokens.colors.border.primary
          }}
        >
          {/* Logo / Header */}
          <div
            className="h-14 flex items-center justify-between px-3 border-b"
            style={{ borderColor: tokens.colors.border.primary }}
          >
            <div className="flex items-center gap-2 overflow-hidden">
              <div
                className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0"
                style={{
                  backgroundColor: tokens.colors.bg.tertiary,
                  border: `1px solid ${tokens.colors.border.primary}`
                }}
              >
                <Terminal
                  className="h-4 w-4"
                  style={{ color: tokens.colors.accent.primary }}
                />
              </div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <span
                      className="text-sm font-medium tracking-tight"
                      style={{ color: tokens.colors.text.primary }}
                    >
                      PARL<span style={{ color: tokens.colors.accent.primary }}>_</span>ADMIN
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 py-4 px-2 overflow-y-auto">
            <NavSection label="Monitor" collapsed={collapsed} />
            <NavItem to="/admin" icon={BarChart3} label="Dashboard" collapsed={collapsed} />
            <NavItem to="/admin/imports" icon={Database} label="Imports" collapsed={collapsed} />
            <NavItem to="/admin/errors" icon={AlertTriangle} label="Errors" collapsed={collapsed} badge="3" />

            <NavSection label="Pipeline" collapsed={collapsed} />
            <NavItem to="/admin/pipeline" icon={Activity} label="Pipeline" collapsed={collapsed} />
            <NavItem to="/admin/queue" icon={Layers} label="Queue" collapsed={collapsed} />

            <NavSection label="System" collapsed={collapsed} />
            <NavItem to="/admin/database" icon={HardDrive} label="Database" collapsed={collapsed} />
            <NavItem to="/admin/logs" icon={FileText} label="Logs" collapsed={collapsed} />
            <NavItem to="/admin/performance" icon={Cpu} label="Performance" collapsed={collapsed} />

            <NavSection label="Config" collapsed={collapsed} />
            <NavItem to="/admin/settings" icon={Settings} label="Settings" collapsed={collapsed} />
          </nav>

          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="absolute -right-3 top-20 w-6 h-6 rounded-full flex items-center justify-center z-30"
            style={{
              backgroundColor: tokens.colors.bg.tertiary,
              border: `1px solid ${tokens.colors.border.primary}`,
              color: tokens.colors.text.secondary
            }}
          >
            {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
          </button>

          {/* Footer status */}
          <div
            className="p-3 border-t"
            style={{ borderColor: tokens.colors.border.primary }}
          >
            <ConnectionStatus isConnected={isConnected} />
          </div>
        </motion.aside>

        {/* Main content area */}
        <div className="flex-1 flex flex-col min-w-0 relative z-10 overflow-hidden">
          {/* Top bar */}
          <header
            className="h-14 flex items-center justify-between px-6 border-b flex-shrink-0"
            style={{
              backgroundColor: tokens.colors.bg.secondary,
              borderColor: tokens.colors.border.primary
            }}
          >
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4" style={{ color: tokens.colors.text.muted }} />
                <span
                  className="text-xs"
                  style={{ color: tokens.colors.text.secondary }}
                >
                  localhost:5000
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              {/* System time */}
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3" style={{ color: tokens.colors.text.muted }} />
                <span
                  className="text-xs tabular-nums"
                  style={{ color: tokens.colors.text.secondary }}
                >
                  {currentTime.toLocaleTimeString('en-GB', { hour12: false })}
                </span>
              </div>

              {/* Status indicators */}
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center gap-1.5 px-2 py-1 rounded"
                  style={{ backgroundColor: tokens.colors.bg.tertiary }}
                >
                  <Cpu className="h-3 w-3" style={{ color: tokens.colors.accent.secondary }} />
                  <span className="text-[10px]" style={{ color: tokens.colors.text.secondary }}>
                    2.4%
                  </span>
                </div>
                <div
                  className="flex items-center gap-1.5 px-2 py-1 rounded"
                  style={{ backgroundColor: tokens.colors.bg.tertiary }}
                >
                  <HardDrive className="h-3 w-3" style={{ color: tokens.colors.accent.tertiary }} />
                  <span className="text-[10px]" style={{ color: tokens.colors.text.secondary }}>
                    847MB
                  </span>
                </div>
              </div>
            </div>
          </header>

          {/* Page content */}
          <main
            className="flex-1 overflow-auto p-6"
            style={{ backgroundColor: tokens.colors.bg.primary }}
          >
            <Outlet />
          </main>
        </div>
      </div>
    </AdminContext.Provider>
  )
}

export default AdminLayout
export { tokens }
