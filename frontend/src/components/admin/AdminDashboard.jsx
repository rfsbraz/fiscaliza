import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database, AlertTriangle, CheckCircle, Clock,
  RefreshCw, XCircle, Activity, Zap, TrendingUp,
  ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight,
  Circle, Loader2
} from 'lucide-react'
import { tokens, useAdmin } from './AdminLayout'

// Status mapping with industrial color scheme
const statusConfig = {
  completed: {
    color: tokens.colors.accent.primary,
    bg: 'rgba(0, 255, 159, 0.1)',
    label: 'COMPLETE'
  },
  pending: {
    color: tokens.colors.accent.tertiary,
    bg: 'rgba(255, 159, 0, 0.1)',
    label: 'PENDING'
  },
  processing: {
    color: tokens.colors.accent.secondary,
    bg: 'rgba(0, 180, 255, 0.1)',
    label: 'PROCESS'
  },
  downloading: {
    color: '#a855f7',
    bg: 'rgba(168, 85, 247, 0.1)',
    label: 'DOWNLOAD'
  },
  failed: {
    color: tokens.colors.accent.danger,
    bg: 'rgba(255, 51, 102, 0.1)',
    label: 'FAILED'
  },
  import_error: {
    color: tokens.colors.accent.danger,
    bg: 'rgba(255, 51, 102, 0.1)',
    label: 'ERROR'
  },
  schema_mismatch: {
    color: '#f97316',
    bg: 'rgba(249, 115, 22, 0.1)',
    label: 'SCHEMA'
  },
  discovered: {
    color: '#6366f1',
    bg: 'rgba(99, 102, 241, 0.1)',
    label: 'DISCOVERED'
  },
  download_pending: {
    color: '#ec4899',
    bg: 'rgba(236, 72, 153, 0.1)',
    label: 'DL_PEND'
  },
  skipped: {
    color: tokens.colors.text.muted,
    bg: 'rgba(74, 95, 85, 0.1)',
    label: 'SKIP'
  },
  recrawl: {
    color: '#14b8a6',
    bg: 'rgba(20, 184, 166, 0.1)',
    label: 'RECRAWL'
  },
}

const getStatus = (status) => statusConfig[status] || statusConfig.pending

// Metric card with LED-style indicator
const MetricCard = ({ label, value, icon: Icon, status = 'neutral', trend = null, subtext }) => {
  const statusColors = {
    success: tokens.colors.accent.primary,
    warning: tokens.colors.accent.tertiary,
    danger: tokens.colors.accent.danger,
    info: tokens.colors.accent.secondary,
    neutral: tokens.colors.text.muted
  }
  const color = statusColors[status]

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative p-4 rounded-lg overflow-hidden"
      style={{
        backgroundColor: tokens.colors.bg.tertiary,
        border: `1px solid ${tokens.colors.border.secondary}`
      }}
    >
      {/* LED indicator strip */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{
          backgroundColor: color,
          boxShadow: `0 0 10px ${color}, 0 0 20px ${color}`
        }}
      />

      <div className="flex items-start justify-between">
        <div className="flex-1">
          <span
            className="text-[10px] uppercase tracking-widest block mb-1"
            style={{ color: tokens.colors.text.muted }}
          >
            {label}
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className="text-2xl font-medium tabular-nums"
              style={{ color: tokens.colors.text.primary }}
            >
              {typeof value === 'number' ? value.toLocaleString() : value}
            </span>
            {trend !== null && (
              <span
                className="flex items-center text-xs"
                style={{ color: trend >= 0 ? tokens.colors.accent.primary : tokens.colors.accent.danger }}
              >
                {trend >= 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
                {Math.abs(trend)}
              </span>
            )}
          </div>
          {subtext && (
            <span className="text-[10px] mt-1 block" style={{ color: tokens.colors.text.muted }}>
              {subtext}
            </span>
          )}
        </div>
        <div
          className="w-10 h-10 rounded flex items-center justify-center"
          style={{ backgroundColor: `${color}15` }}
        >
          <Icon className="h-5 w-5" style={{ color }} />
        </div>
      </div>
    </motion.div>
  )
}

// Status badge with glow
const StatusBadge = ({ status, pulse = false }) => {
  const config = getStatus(status)
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] uppercase tracking-wider font-medium ${pulse ? 'animate-pulse' : ''}`}
      style={{
        backgroundColor: config.bg,
        color: config.color,
        border: `1px solid ${config.color}30`,
        boxShadow: pulse ? `0 0 12px ${config.color}40` : 'none'
      }}
    >
      <Circle className="h-1.5 w-1.5 fill-current" />
      {config.label}
    </span>
  )
}

// Activity ring visualization
const ActivityRing = ({ stats }) => {
  if (!stats?.status_counts) return null

  const total = Object.values(stats.status_counts).reduce((a, b) => a + b, 0)
  const segments = Object.entries(stats.status_counts)
    .filter(([_, count]) => count > 0)
    .map(([status, count]) => ({
      status,
      count,
      percentage: (count / total) * 100,
      color: getStatus(status).color
    }))
    .sort((a, b) => b.count - a.count)

  let currentAngle = -90

  return (
    <div
      className="p-4 rounded-lg"
      style={{
        backgroundColor: tokens.colors.bg.tertiary,
        border: `1px solid ${tokens.colors.border.secondary}`
      }}
    >
      <span
        className="text-[10px] uppercase tracking-widest block mb-4"
        style={{ color: tokens.colors.text.muted }}
      >
        Status Distribution
      </span>

      <div className="flex items-center gap-6">
        {/* Ring */}
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            {segments.map((seg, i) => {
              const angle = (seg.percentage / 100) * 360
              const startAngle = currentAngle
              currentAngle += angle

              const startRad = (startAngle * Math.PI) / 180
              const endRad = ((startAngle + angle) * Math.PI) / 180

              const x1 = 50 + 40 * Math.cos(startRad)
              const y1 = 50 + 40 * Math.sin(startRad)
              const x2 = 50 + 40 * Math.cos(endRad)
              const y2 = 50 + 40 * Math.sin(endRad)

              const largeArc = angle > 180 ? 1 : 0

              return (
                <path
                  key={seg.status}
                  d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArc} 1 ${x2} ${y2} Z`}
                  fill={seg.color}
                  opacity={0.8}
                  style={{ filter: `drop-shadow(0 0 4px ${seg.color}40)` }}
                />
              )
            })}
            <circle cx="50" cy="50" r="25" fill={tokens.colors.bg.tertiary} />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span
              className="text-lg font-medium"
              style={{ color: tokens.colors.text.primary }}
            >
              {total.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-1">
          {segments.slice(0, 8).map(seg => (
            <div key={seg.status} className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: seg.color }}
              />
              <span className="text-[10px] uppercase" style={{ color: tokens.colors.text.secondary }}>
                {seg.status.replace('_', ' ')}
              </span>
              <span className="text-[10px] ml-auto tabular-nums" style={{ color: tokens.colors.text.muted }}>
                {seg.count}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Recent imports table
const ImportsTable = ({ records, loading }) => {
  const [sortField, setSortField] = useState('updated_at')
  const [sortDir, setSortDir] = useState('desc')

  const sorted = [...records].sort((a, b) => {
    const aVal = a[sortField]
    const bVal = b[sortField]
    const dir = sortDir === 'desc' ? -1 : 1
    if (aVal < bVal) return -1 * dir
    if (aVal > bVal) return 1 * dir
    return 0
  })

  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        backgroundColor: tokens.colors.bg.tertiary,
        border: `1px solid ${tokens.colors.border.secondary}`
      }}
    >
      <div className="px-4 py-3 border-b" style={{ borderColor: tokens.colors.border.secondary }}>
        <span
          className="text-[10px] uppercase tracking-widest"
          style={{ color: tokens.colors.text.muted }}
        >
          Recent Activity
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr style={{ backgroundColor: tokens.colors.bg.elevated }}>
              {['File', 'Category', 'Leg', 'Status', 'Records', 'Time'].map(col => (
                <th
                  key={col}
                  className="px-3 py-2 text-left text-[10px] uppercase tracking-wider font-medium"
                  style={{ color: tokens.colors.text.muted }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center">
                  <Loader2 className="h-5 w-5 animate-spin mx-auto" style={{ color: tokens.colors.accent.secondary }} />
                </td>
              </tr>
            ) : sorted.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-8 text-center text-xs" style={{ color: tokens.colors.text.muted }}>
                  No records found
                </td>
              </tr>
            ) : (
              sorted.slice(0, 15).map((record, i) => {
                const isActive = ['processing', 'downloading'].includes(record.status)
                return (
                  <motion.tr
                    key={record.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="border-t"
                    style={{
                      borderColor: tokens.colors.border.secondary,
                      backgroundColor: isActive ? `${tokens.colors.accent.secondary}08` : 'transparent'
                    }}
                  >
                    <td className="px-3 py-2">
                      <span
                        className="text-xs truncate block max-w-[180px]"
                        style={{ color: tokens.colors.text.primary }}
                        title={record.file_name}
                      >
                        {record.file_name}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-[10px] uppercase" style={{ color: tokens.colors.text.secondary }}>
                        {record.category}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="text-[10px]" style={{ color: tokens.colors.text.muted }}>
                        {record.legislatura || '—'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={record.status} pulse={isActive} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-xs tabular-nums" style={{ color: tokens.colors.text.secondary }}>
                        {record.records_imported?.toLocaleString() || '—'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span className="text-[10px] tabular-nums" style={{ color: tokens.colors.text.muted }}>
                        {record.processing_duration_seconds
                          ? `${record.processing_duration_seconds.toFixed(1)}s`
                          : '—'}
                      </span>
                    </td>
                  </motion.tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Error item with expand
const ErrorItem = ({ error, isExpanded, onToggle }) => {
  const config = getStatus(error.status)

  return (
    <div className="border-b last:border-b-0" style={{ borderColor: tokens.colors.border.secondary }}>
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-white/[0.02]"
        onClick={onToggle}
      >
        <div
          className="w-1 h-8 rounded-full self-stretch"
          style={{ backgroundColor: config.color }}
        />
        <div className="flex-1 min-w-0">
          <p className="text-xs truncate" style={{ color: tokens.colors.text.primary }}>
            {error.file_name}
          </p>
          <p className="text-[10px]" style={{ color: tokens.colors.text.muted }}>
            {error.category} • {error.legislatura || 'N/A'}
          </p>
        </div>
        <StatusBadge status={error.status} />
        {isExpanded ? (
          <ChevronUp className="h-4 w-4" style={{ color: tokens.colors.text.muted }} />
        ) : (
          <ChevronDown className="h-4 w-4" style={{ color: tokens.colors.text.muted }} />
        )}
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div
              className="px-4 py-3 mx-4 mb-3 rounded"
              style={{ backgroundColor: tokens.colors.bg.primary }}
            >
              <pre
                className="text-xs whitespace-pre-wrap break-all"
                style={{ color: tokens.colors.accent.danger }}
              >
                {error.error_message || 'No error message available'}
              </pre>
              {error.schema_issues && (
                <pre
                  className="text-xs whitespace-pre-wrap break-all mt-3 pt-3 border-t"
                  style={{
                    color: tokens.colors.accent.tertiary,
                    borderColor: tokens.colors.border.secondary
                  }}
                >
                  {error.schema_issues}
                </pre>
              )}
              <div className="flex gap-4 mt-3 pt-3 border-t" style={{ borderColor: tokens.colors.border.secondary }}>
                <span className="text-[10px]" style={{ color: tokens.colors.text.muted }}>
                  Attempts: <span style={{ color: tokens.colors.accent.danger }}>{error.error_count || 0}</span>
                </span>
                {error.retry_at && (
                  <span className="text-[10px]" style={{ color: tokens.colors.text.muted }}>
                    Retry: <span style={{ color: tokens.colors.accent.tertiary }}>
                      {new Date(error.retry_at).toLocaleString()}
                    </span>
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Main Dashboard Component
const AdminDashboard = () => {
  const { setIsConnected } = useAdmin() || {}
  const [stats, setStats] = useState(null)
  const [records, setRecords] = useState([])
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)
  const [expandedError, setExpandedError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

      const [statsRes, recordsRes, errorsRes] = await Promise.all([
        fetch(`${baseUrl}/admin/import-stats`),
        fetch(`${baseUrl}/admin/import-status?limit=50&sort=updated_at&order=desc`),
        fetch(`${baseUrl}/admin/recent-errors?limit=10`)
      ])

      if (statsRes.ok) setStats(await statsRes.json())
      if (recordsRes.ok) {
        const data = await recordsRes.json()
        setRecords(data.records || [])
      }
      if (errorsRes.ok) {
        const data = await errorsRes.json()
        setErrors(data.errors || [])
      }

      setLastUpdate(new Date())
      setIsConnected?.(true)
    } catch (error) {
      console.error('Failed to fetch admin data:', error)
      setIsConnected?.(false)
    } finally {
      setLoading(false)
    }
  }, [setIsConnected])

  useEffect(() => {
    fetchData()
    let interval
    if (autoRefresh) {
      interval = setInterval(fetchData, 8000)
    }
    return () => interval && clearInterval(interval)
  }, [fetchData, autoRefresh])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1
            className="text-lg font-medium"
            style={{ color: tokens.colors.text.primary }}
          >
            Import Dashboard
          </h1>
          <p className="text-xs mt-0.5" style={{ color: tokens.colors.text.muted }}>
            Real-time pipeline monitoring and analytics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="flex items-center gap-2 px-3 py-1.5 rounded text-xs transition-all"
            style={{
              backgroundColor: autoRefresh ? `${tokens.colors.accent.primary}15` : tokens.colors.bg.tertiary,
              color: autoRefresh ? tokens.colors.accent.primary : tokens.colors.text.secondary,
              border: `1px solid ${autoRefresh ? tokens.colors.accent.primary + '40' : tokens.colors.border.secondary}`
            }}
          >
            <Activity className={`h-3 w-3 ${autoRefresh ? 'animate-pulse' : ''}`} />
            {autoRefresh ? 'LIVE' : 'PAUSED'}
          </button>

          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-1.5 rounded text-xs transition-colors"
            style={{
              backgroundColor: tokens.colors.bg.tertiary,
              color: tokens.colors.text.secondary,
              border: `1px solid ${tokens.colors.border.secondary}`
            }}
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            REFRESH
          </button>

          {lastUpdate && (
            <span className="text-[10px] tabular-nums" style={{ color: tokens.colors.text.muted }}>
              {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard
          label="Total Imported"
          value={stats?.totals?.records_imported || 0}
          icon={Database}
          status="success"
          subtext="all time"
        />
        <MetricCard
          label="Completed (24h)"
          value={stats?.recent_24h?.completed || 0}
          icon={CheckCircle}
          status="success"
          trend={stats?.recent_24h?.completed}
        />
        <MetricCard
          label="Failed (24h)"
          value={stats?.recent_24h?.failed || 0}
          icon={XCircle}
          status={stats?.recent_24h?.failed > 0 ? 'danger' : 'neutral'}
        />
        <MetricCard
          label="Processing"
          value={stats?.totals?.currently_processing || 0}
          icon={Zap}
          status="info"
        />
        <MetricCard
          label="Pending"
          value={stats?.totals?.pending || 0}
          icon={Clock}
          status="warning"
        />
        <MetricCard
          label="Avg Duration"
          value={`${stats?.totals?.avg_processing_seconds?.toFixed(1) || 0}s`}
          icon={TrendingUp}
          status="neutral"
        />
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity Table */}
        <div className="lg:col-span-2">
          <ImportsTable records={records} loading={loading} />
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Status Ring */}
          <ActivityRing stats={stats} />

          {/* Errors Panel */}
          <div
            className="rounded-lg overflow-hidden"
            style={{
              backgroundColor: tokens.colors.bg.tertiary,
              border: `1px solid ${tokens.colors.border.secondary}`
            }}
          >
            <div
              className="px-4 py-3 border-b flex items-center justify-between"
              style={{ borderColor: tokens.colors.border.secondary }}
            >
              <span
                className="text-[10px] uppercase tracking-widest flex items-center gap-2"
                style={{ color: tokens.colors.text.muted }}
              >
                <AlertTriangle className="h-3 w-3" style={{ color: tokens.colors.accent.danger }} />
                Recent Errors
              </span>
              {errors.length > 0 && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: tokens.colors.accent.danger + '20',
                    color: tokens.colors.accent.danger
                  }}
                >
                  {errors.length}
                </span>
              )}
            </div>

            <div className="max-h-[400px] overflow-y-auto">
              {errors.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <CheckCircle className="h-6 w-6 mx-auto mb-2" style={{ color: tokens.colors.accent.primary + '40' }} />
                  <p className="text-xs" style={{ color: tokens.colors.text.muted }}>
                    No recent errors
                  </p>
                </div>
              ) : (
                errors.map(error => (
                  <ErrorItem
                    key={error.id}
                    error={error}
                    isExpanded={expandedError === error.id}
                    onToggle={() => setExpandedError(expandedError === error.id ? null : error.id)}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      {stats?.category_counts && Object.keys(stats.category_counts).length > 0 && (
        <div
          className="rounded-lg p-4"
          style={{
            backgroundColor: tokens.colors.bg.tertiary,
            border: `1px solid ${tokens.colors.border.secondary}`
          }}
        >
          <span
            className="text-[10px] uppercase tracking-widest block mb-4"
            style={{ color: tokens.colors.text.muted }}
          >
            Files by Category
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {Object.entries(stats.category_counts)
              .sort(([,a], [,b]) => b - a)
              .map(([category, count]) => (
                <div
                  key={category}
                  className="p-3 rounded"
                  style={{ backgroundColor: tokens.colors.bg.elevated }}
                >
                  <p
                    className="text-[10px] uppercase truncate"
                    style={{ color: tokens.colors.text.muted }}
                    title={category}
                  >
                    {category}
                  </p>
                  <p
                    className="text-lg font-medium tabular-nums mt-1"
                    style={{ color: tokens.colors.text.primary }}
                  >
                    {count.toLocaleString()}
                  </p>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard
