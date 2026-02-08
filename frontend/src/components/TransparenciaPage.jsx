import React, { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Activity,
  Users,
  MessageSquare,
  Scale,
  RefreshCw,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Eye,
  Target,
  Calendar,
  Vote,
  FileText,
  Award,
  UserCheck,
  Share2
} from 'lucide-react'
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner, Section, Card } from './common';

const TransparenciaPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()

  const [activeTab, setActiveTab] = useState('live')
  const [data, setData] = useState({})
  const [loading, setLoading] = useState({})
  const [lastUpdated, setLastUpdated] = useState(null)

  const tabs = [
    { id: 'live', label: 'Atividade Ao Vivo', icon: Activity },
    { id: 'progress', label: 'Progresso Legislativo', icon: Scale },
    { id: 'deputies', label: 'Performance Deputados', icon: Users },
    { id: 'participation', label: 'Participação Cidadã', icon: MessageSquare },
    { id: 'accountability', label: 'Métricas Transparência', icon: BarChart3 }
  ]

  const API_BASE_URL = 'transparency'

  const fetchData = async (endpoint, key) => {
    setLoading(prev => ({ ...prev, [key]: true }))
    try {
      const response = await fetch(`${API_BASE_URL}/${endpoint}`)
      const result = await response.json()
      if (response.ok) {
        setData(prev => ({ ...prev, [key]: result }))
        if (result.last_updated) {
          setLastUpdated(result.last_updated)
        }
      } else {
        console.error(`Erro ao carregar ${endpoint}:`, result.message)
      }
    } catch (error) {
      console.error(`Erro ao carregar ${endpoint}:`, error)
    }
    setLoading(prev => ({ ...prev, [key]: false }))
  }

  useEffect(() => {
    switch (activeTab) {
      case 'live':
        fetchData('live-activity', 'liveActivity')
        break
      case 'progress':
        fetchData('legislative-progress', 'legislativeProgress')
        break
      case 'deputies':
        fetchData('deputy-performance', 'deputyPerformance')
        break
      case 'participation':
        fetchData('citizen-participation', 'citizenParticipation')
        break
      case 'accountability':
        fetchData('accountability-metrics', 'accountabilityMetrics')
        break
    }
  }, [activeTab])

  useEffect(() => {
    const tab = searchParams.get('tab')
    const validTabs = ['live', 'progress', 'deputies', 'participation', 'accountability']
    if (tab && validTabs.includes(tab)) {
      setActiveTab(tab)
    }
  }, [searchParams])

  const handleTabChange = (tabId) => {
    setActiveTab(tabId)
    setSearchParams({ tab: tabId })
  }

  const copyTabLink = (tabId) => {
    const url = `${window.location.origin}/transparencia?tab=${tabId}`
    navigator.clipboard.writeText(url)
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('pt-PT')
  }

  const formatPercentage = (value) => {
    return `${value}%`
  }

  const getStatusBadge = (status) => {
    const statusStyles = {
      'excellent': { bg: '#E8F5E9', color: tokens.colors.primary },
      'good': { bg: '#E3F2FD', color: '#2563EB' },
      'average': { bg: '#FFF8E1', color: tokens.colors.warning },
      'satisfactory': { bg: '#FFF8E1', color: tokens.colors.warning },
      'moderate': { bg: '#FFF3E0', color: '#EA580C' },
      'needs_improvement': { bg: '#FFEBEE', color: tokens.colors.accent },
      'concerning': { bg: '#FFEBEE', color: tokens.colors.accent },
      'strong': { bg: '#E8F5E9', color: tokens.colors.primary }
    }
    const style = statusStyles[status] || { bg: '#F5F5F5', color: tokens.colors.textMuted }
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '0.25rem 0.75rem',
          borderRadius: '2px',
          fontSize: '0.75rem',
          fontFamily: tokens.fonts.body,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.025em',
          backgroundColor: style.bg,
          color: style.color,
        }}
      >
        {status.replace('_', ' ').toUpperCase()}
      </span>
    )
  }

  // Editorial-style Metric Card
  const MetricCard = ({ icon: Icon, title, value, subtitle, trend }) => (
    <motion.div
      whileHover={{ y: -2 }}
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        padding: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <div
            style={{
              padding: '0.5rem',
              backgroundColor: '#E8F5E9',
              borderRadius: '4px',
            }}
          >
            <Icon style={{ width: '20px', height: '20px', color: tokens.colors.primary }} />
          </div>
          <div>
            <p
              style={{
                fontSize: '0.75rem',
                fontFamily: tokens.fonts.body,
                fontWeight: 600,
                color: tokens.colors.textMuted,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '0.25rem',
              }}
            >
              {title}
            </p>
            <p
              style={{
                fontSize: '1.75rem',
                fontFamily: tokens.fonts.mono,
                fontWeight: 700,
                color: tokens.colors.textPrimary,
                lineHeight: 1,
              }}
            >
              {value}
            </p>
            {subtitle && (
              <p
                style={{
                  fontSize: '0.8125rem',
                  fontFamily: tokens.fonts.body,
                  color: tokens.colors.textMuted,
                  marginTop: '0.25rem',
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {trend && (
          <div style={{ textAlign: 'right' }}>
            <span
              style={{
                fontSize: '0.875rem',
                fontFamily: tokens.fonts.mono,
                fontWeight: 600,
                color: trend > 0 ? tokens.colors.primary : tokens.colors.accent,
              }}
            >
              {trend > 0 ? '+' : ''}{trend}%
            </span>
          </div>
        )}
      </div>
    </motion.div>
  )

  // Editorial Progress Bar
  const ProgressBar = ({ percentage, color = tokens.colors.primary }) => (
    <div
      style={{
        width: '100%',
        height: '6px',
        backgroundColor: tokens.colors.border,
        borderRadius: '3px',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${Math.min(percentage, 100)}%`,
          backgroundColor: color,
          borderRadius: '3px',
          transition: 'width 300ms ease',
        }}
      />
    </div>
  )

  // Editorial Card Component
  const Card = ({ children, title, icon: Icon }) => (
    <div
      style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
      }}
    >
      {title && (
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: `1px solid ${tokens.colors.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          {Icon && <Icon style={{ width: '18px', height: '18px', color: tokens.colors.primary }} />}
          <h3
            style={{
              fontFamily: tokens.fonts.body,
              fontSize: '1rem',
              fontWeight: 600,
              color: tokens.colors.textPrimary,
              margin: 0,
            }}
          >
            {title}
          </h3>
        </div>
      )}
      <div style={{ padding: '1.25rem' }}>
        {children}
      </div>
    </div>
  )

  const renderLiveActivity = () => {
    const liveData = data.liveActivity
    if (!liveData) return (
      <div style={{ textAlign: 'center', padding: '2rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
        Carregando dados da atividade parlamentar...
      </div>
    )

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <MetricCard
            icon={Calendar}
            title="Eventos Hoje"
            value={liveData.todays_agenda?.summary?.total_events || 0}
          />
          <MetricCard
            icon={Users}
            title="Sessões Plenárias"
            value={liveData.todays_agenda?.summary?.plenary_sessions || 0}
          />
          <MetricCard
            icon={Vote}
            title="Votações (48h)"
            value={liveData.recent_votes?.summary?.total_votes_48h || 0}
          />
          <MetricCard
            icon={TrendingUp}
            title="Taxa Aprovação"
            value={formatPercentage(liveData.recent_votes?.summary?.approval_rate || 0)}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
          <Card title="Agenda de Hoje" icon={Activity}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Em Progresso</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{liveData.todays_agenda?.summary?.in_progress || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Completados</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{liveData.todays_agenda?.summary?.completed || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Reuniões Comissão</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{liveData.todays_agenda?.summary?.committee_meetings || 0}</span>
              </div>
            </div>
          </Card>

          <Card title="Atividade Votações" icon={Vote}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Taxa de Aprovação</span>
                  <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{formatPercentage(liveData.recent_votes?.summary?.approval_rate || 0)}</span>
                </div>
                <ProgressBar percentage={liveData.recent_votes?.summary?.approval_rate || 0} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'center' }}>
                <div>
                  <p style={{ fontSize: '1.5rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.primary }}>{liveData.recent_votes?.summary?.approved || 0}</p>
                  <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Aprovadas</p>
                </div>
                <div>
                  <p style={{ fontSize: '1.5rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.accent }}>{liveData.recent_votes?.summary?.rejected || 0}</p>
                  <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Rejeitadas</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    )
  }

  const renderLegislativeProgress = () => {
    const progressData = data.legislativeProgress
    if (!progressData) return (
      <div style={{ textAlign: 'center', padding: '2rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
        Carregando progresso legislativo...
      </div>
    )

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <MetricCard
            icon={FileText}
            title="Iniciativas Totais"
            value={progressData.overall_efficiency?.total_initiatives || 0}
          />
          <MetricCard
            icon={CheckCircle}
            title="Taxa Aprovação"
            value={formatPercentage(progressData.overall_efficiency?.overall_approval_rate || 0)}
          />
          <MetricCard
            icon={Users}
            title="Comissões Ativas"
            value={progressData.overall_efficiency?.committees_active || 0}
          />
          <MetricCard
            icon={Clock}
            title="Tempo Resp. Médio"
            value={`${progressData.government_responsiveness?.avg_response_days || 0} dias`}
          />
        </div>

        <Card title="Responsividade do Governo" icon={Scale}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Classificação</span>
              {getStatusBadge(progressData.government_responsiveness?.efficiency_rating)}
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Taxa de Resposta</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{formatPercentage(progressData.government_responsiveness?.response_rate || 0)}</span>
              </div>
              <ProgressBar percentage={progressData.government_responsiveness?.response_rate || 0} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'center' }}>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: '#2563EB' }}>{progressData.government_responsiveness?.total_questions || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Perguntas</p>
              </div>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.primary }}>{progressData.government_responsiveness?.total_responses || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Respostas</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const renderDeputyPerformance = () => {
    const deputyData = data.deputyPerformance
    if (!deputyData) return (
      <div style={{ textAlign: 'center', padding: '2rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
        Carregando dados dos deputados...
      </div>
    )

    const topDeputies = deputyData.deputy_performance?.slice(0, 5) || []

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <MetricCard
            icon={Users}
            title="Deputados Analisados"
            value={deputyData.analysis_period?.total_deputies_analyzed || 0}
          />
          <MetricCard
            icon={UserCheck}
            title="Assiduidade Média"
            value={formatPercentage(deputyData.analysis_period?.avg_attendance_rate || 0)}
          />
          <MetricCard
            icon={Award}
            title="High Performers"
            value={deputyData.summary_statistics?.high_performers || 0}
          />
          <MetricCard
            icon={Activity}
            title="Deputados Ativos"
            value={deputyData.summary_statistics?.active_deputies_90d || 0}
          />
        </div>

        <Card title="Top 5 Deputados" icon={Award}>
          <p style={{ fontSize: '0.875rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body, marginBottom: '1rem' }}>
            Deputados com melhor performance global
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {topDeputies.map((deputy, index) => (
              <div
                key={deputy.deputy_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.75rem',
                  backgroundColor: tokens.colors.bgPrimary,
                  borderRadius: '4px',
                  border: `1px solid ${tokens.colors.border}`,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      backgroundColor: '#E8F5E9',
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <span style={{ fontSize: '0.875rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.primary }}>
                      {index + 1}
                    </span>
                  </div>
                  <div>
                    <p style={{ fontFamily: tokens.fonts.body, fontWeight: 600, color: tokens.colors.textPrimary, margin: 0 }}>
                      {deputy.parliamentary_name || deputy.name}
                    </p>
                    <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body, margin: 0 }}>
                      {deputy.party || 'N/A'}
                    </p>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <p style={{ fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.textPrimary, margin: 0 }}>
                    {deputy.performance?.overall_score}
                  </p>
                  {getStatusBadge(deputy.performance?.rating)}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    )
  }

  const renderCitizenParticipation = () => {
    const participationData = data.citizenParticipation
    if (!participationData) return (
      <div style={{ textAlign: 'center', padding: '2rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
        Carregando dados de participação...
      </div>
    )

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <MetricCard
            icon={FileText}
            title="Petições Totais"
            value={participationData.petition_data?.total_petitions || 0}
          />
          <MetricCard
            icon={CheckCircle}
            title="Taxa Aceitação"
            value={formatPercentage(participationData.petition_data?.processing_status?.acceptance_rate || 0)}
          />
          <MetricCard
            icon={Users}
            title="Subscritores Médios"
            value={participationData.petition_data?.engagement_metrics?.avg_subscribers || 0}
          />
          <MetricCard
            icon={TrendingUp}
            title="Score Engagement"
            value={participationData.petition_data?.engagement_metrics?.citizen_engagement_score || 0}
          />
        </div>

        <Card title="Participação Cidadã" icon={MessageSquare}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Classificação Geral</span>
              {getStatusBadge(participationData.participation_summary?.overall_rating)}
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Score de Transparência</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{participationData.participation_summary?.transparency_score || 0}</span>
              </div>
              <ProgressBar percentage={participationData.participation_summary?.transparency_score || 0} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'center' }}>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.primary }}>{participationData.petition_data?.processing_status?.accepted || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Aceites</p>
              </div>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.warning }}>{participationData.petition_data?.processing_status?.processing || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Em Análise</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const renderAccountabilityMetrics = () => {
    const accountabilityData = data.accountabilityMetrics
    if (!accountabilityData) return (
      <div style={{ textAlign: 'center', padding: '2rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
        Carregando métricas de transparência...
      </div>
    )

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
          <MetricCard
            icon={Target}
            title="Score Geral"
            value={accountabilityData.accountability_summary?.overall_score || 0}
          />
          <MetricCard
            icon={TrendingUp}
            title="Responsividade"
            value={formatPercentage(accountabilityData.key_performance_indicators?.government_responsiveness?.score || 0)}
          />
          <MetricCard
            icon={Scale}
            title="Eficiência"
            value={formatPercentage(accountabilityData.key_performance_indicators?.legislative_efficiency?.score || 0)}
          />
          <MetricCard
            icon={Eye}
            title="Transparência"
            value={formatPercentage(accountabilityData.key_performance_indicators?.meeting_transparency?.score || 0)}
          />
        </div>

        <Card title="Saúde Democrática" icon={BarChart3}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Classificação Geral</span>
              {getStatusBadge(accountabilityData.accountability_summary?.overall_rating)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Saúde Democrática</span>
              {getStatusBadge(accountabilityData.benchmark_comparison?.overall_democratic_health)}
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.body }}>Score de Accountability</span>
                <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>{accountabilityData.accountability_summary?.overall_score || 0}</span>
              </div>
              <ProgressBar percentage={accountabilityData.accountability_summary?.overall_score || 0} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', textAlign: 'center' }}>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.primary }}>{accountabilityData.benchmark_comparison?.areas_above_benchmark || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Acima Benchmark</p>
              </div>
              <div>
                <p style={{ fontSize: '1.25rem', fontFamily: tokens.fonts.mono, fontWeight: 700, color: tokens.colors.accent }}>{accountabilityData.benchmark_comparison?.areas_needing_attention || 0}</p>
                <p style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>Precisam Atenção</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const renderContent = () => {
    if (loading[activeTab]) {
      return <LoadingSpinner message="A carregar dados" fullHeight={false} />
    }

    switch (activeTab) {
      case 'live': return renderLiveActivity()
      case 'progress': return renderLegislativeProgress()
      case 'deputies': return renderDeputyPerformance()
      case 'participation': return renderCitizenParticipation()
      case 'accountability': return renderAccountabilityMetrics()
      default: return null
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: tokens.colors.bgPrimary,
        padding: '2rem 1.5rem',
      }}
    >
      <div style={{ maxWidth: '1280px', margin: '0 auto' }}>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ textAlign: 'center', marginBottom: '2rem' }}
        >
          <h1
            style={{
              fontFamily: tokens.fonts.headline,
              fontSize: '2.5rem',
              fontWeight: 700,
              color: tokens.colors.textPrimary,
              marginBottom: '0.5rem',
            }}
          >
            Dashboard de Transparência
          </h1>
          <p
            style={{
              fontFamily: tokens.fonts.body,
              fontSize: '1.125rem',
              color: tokens.colors.textSecondary,
              marginBottom: '1rem',
            }}
          >
            Monitorização em tempo real da atividade parlamentar portuguesa
          </p>
          {lastUpdated && (
            <p
              style={{
                fontFamily: tokens.fonts.body,
                fontSize: '0.8125rem',
                color: tokens.colors.textMuted,
              }}
            >
              Última atualização: {formatDate(lastUpdated)}
            </p>
          )}
        </motion.div>

        {/* Tab Navigation */}
        <div
          style={{
            backgroundColor: tokens.colors.bgSecondary,
            border: `1px solid ${tokens.colors.border}`,
            borderRadius: '4px',
            padding: '0.5rem',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              return (
                <div key={tab.id} style={{ position: 'relative' }}>
                  <button
                    onClick={() => handleTabChange(tab.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.5rem 1rem',
                      borderRadius: '4px',
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.875rem',
                      fontWeight: isActive ? 600 : 500,
                      border: isActive ? `1px solid ${tokens.colors.primary}` : '1px solid transparent',
                      backgroundColor: isActive ? '#E8F5E9' : 'transparent',
                      color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                      cursor: 'pointer',
                      transition: 'all 150ms ease',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = tokens.colors.bgPrimary
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }
                    }}
                  >
                    <Icon style={{ width: '16px', height: '16px' }} />
                    <span style={{ display: 'none', '@media (min-width: 640px)': { display: 'inline' } }} className="hidden sm:inline">
                      {tab.label}
                    </span>
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        {/* Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          {renderContent()}
        </motion.div>
      </div>
    </div>
  )
}

export default TransparenciaPage
