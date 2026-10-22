import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowLeft, User, MapPin, Calendar, Briefcase, Activity, FileText, Vote, MessageSquare, Play, Clock, ExternalLink, Mail, Shield, AlertTriangle, Users, TrendingUp, TrendingDown, Minus, Info, ChevronRight, ChevronDown, Target, Award, Globe, CheckCircle2, BarChart3, GraduationCap, Building2, BookOpen, Medal } from 'lucide-react';
import VotingAnalytics from './VotingAnalytics';
import LegislatureDropdown from './LegislatureDropdown';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner } from './common';
// Phase 1 Components - Constitutional Modernism Design System
import AttendancePanel, { AttendanceCard } from './deputy/AttendancePanel';
import { EducationalBox, ImportantContextBox, MethodologyNote } from './deputy/ContextBox';
import InterestStatusCard, { ExclusivityBadge, DeclaredInterestsBadge, SectorInterestRow } from './deputy/InterestStatusCard';
import InitiativeProcessStepper, { InitiativeOutcomesSummary } from './deputy/InitiativeProcessStepper';
import InitiativeRecordTable, { SigningCounts, ApprovalLines, GroupComparison } from './deputy/InitiativeRecord';
import InterventionsSummaryBar, { ActivityBadge, VideoIndicator } from './deputy/InterventionsSummaryBar';
// Phase 2 Components - Enhanced Analytics
import TimelineSparkline, { ActivityHeatmap, TrendIndicator, BarSparkline } from './charts/TimelineSparkline';
import AchievementBadge, { BadgeCollection, BadgeSummary, RedFlagIndicator } from './deputy/AchievementBadge';
import PolicySpecializationChart, { PolicyRadar, TopicTag } from './charts/PolicySpecializationChart';
import InterestTable, { ACTIVITY_COLUMNS, SHAREHOLDING_COLUMNS } from './deputy/InterestTable';
import { formatDecimal, legislatureName, plural } from '../utils/format';

// TODO: Deputy mandate linking limitation
// Current system uses name-based linking to connect same person across legislaturas
// This is a temporary solution because deputado_id changes every legislative period
// Future enhancement: Implement proper unique person identifiers or create person-linking table

// Enhanced Statistics Components

/**
 * Calculate trend indicator based on current vs career average
 */
const getTrendIndicator = (current, total, legislaturesServed = 1) => {
  if (total === 0 || legislaturesServed === 0) return 'stable';
  const careerAverage = total / Math.max(legislaturesServed, 1);
  const threshold = 0.1; // 10% threshold for trend changes
  
  if (current > careerAverage * (1 + threshold)) return 'up';
  if (current < careerAverage * (1 - threshold)) return 'down';
  return 'stable';
};

/**
 * Color scheme mapping for Data Observatory theme
 */
const colorSchemes = {
  blue: {
    bg: '#EFF6FF',
    bgSecondary: '#DBEAFE',
    primary: '#2563EB',
    primaryDark: '#1D4ED8',
    text: '#1E40AF',
    textLight: '#3B82F6',
    border: '#BFDBFE',
  },
  green: {
    bg: '#F0FDF4',
    bgSecondary: '#DCFCE7',
    primary: '#16A34A',
    primaryDark: '#15803D',
    text: '#166534',
    textLight: '#22C55E',
    border: '#BBF7D0',
  },
  purple: {
    bg: '#FAF5FF',
    bgSecondary: '#F3E8FF',
    primary: '#9333EA',
    primaryDark: '#7E22CE',
    text: '#6B21A8',
    textLight: '#A855F7',
    border: '#E9D5FF',
  },
  orange: {
    bg: '#FFF7ED',
    bgSecondary: '#FFEDD5',
    primary: '#EA580C',
    primaryDark: '#C2410C',
    text: '#9A3412',
    textLight: '#F97316',
    border: '#FED7AA',
  },
};

/**
 * Enhanced Statistic Card Component with Data Observatory theme
 */
const StatisticCard = ({
  title,
  icon: Icon,
  current,
  total,
  colorScheme,
  description,
  tabId,
  onCardClick
}) => {
  const percentage = total > 0 ? Math.min((current / total) * 100, 100) : 0;
  const trend = getTrendIndicator(current, total, 3);
  const scheme = colorSchemes[colorScheme] || colorSchemes.blue;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? tokens.colors.success : trend === 'down' ? tokens.colors.danger : tokens.colors.textMuted;

  const handleClick = () => {
    if (onCardClick) {
      onCardClick(tabId);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <article
      style={{
        position: 'relative',
        background: `linear-gradient(135deg, ${scheme.bg} 0%, ${scheme.bgSecondary} 100%)`,
        borderRadius: '4px',
        border: `1px solid ${scheme.border}`,
        padding: '16px',
        cursor: 'pointer',
        transition: 'border-color 0.15s ease',
        fontFamily: tokens.fonts.body,
      }}
      role="listitem"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      aria-labelledby={`${tabId}-title`}
      aria-describedby={`${tabId}-description ${tabId}-stats`}
      onMouseEnter={(e) => e.currentTarget.style.borderColor = scheme.primary}
      onMouseLeave={(e) => e.currentTarget.style.borderColor = scheme.border}
    >
      {/* Header with Icon and Trend */}
      <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{
          padding: '10px',
          backgroundColor: scheme.primary,
          borderRadius: '4px',
          flexShrink: 0,
        }}>
          <Icon style={{ width: '20px', height: '20px', color: '#FFFFFF' }} aria-hidden="true" />
        </div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 8px',
          backgroundColor: 'rgba(255, 255, 255, 0.7)',
          borderRadius: '9999px',
        }}>
          <TrendIcon style={{ width: '12px', height: '12px', color: trendColor }} aria-hidden="true" />
          <span className="sr-only">
            Tendência: {trend === 'up' ? 'acima da média' : trend === 'down' ? 'abaixo da média' : 'estável'}
          </span>
        </div>
      </header>

      {/* Content */}
      <div>
        <h4
          id={`${tabId}-title`}
          style={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: scheme.text,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '12px',
          }}
        >
          {title}
        </h4>

        {/* Statistics */}
        <div id={`${tabId}-stats`}>
          {/* Current Value */}
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.875rem', fontWeight: 500, color: scheme.textLight }}>Atual</span>
            <span style={{ fontSize: '1.5rem', fontWeight: 700, color: scheme.text, fontFamily: tokens.fonts.mono }}>
              {current.toLocaleString('pt-PT')}
            </span>
          </div>

          {/* Progress Bar */}
          <div style={{ marginBottom: '12px' }}>
            <div style={{
              width: '100%',
              backgroundColor: 'rgba(255, 255, 255, 0.6)',
              borderRadius: '9999px',
              height: '6px',
              overflow: 'hidden',
            }}>
              <div
                style={{
                  height: '100%',
                  backgroundColor: scheme.primary,
                  borderRadius: '9999px',
                  width: `${Math.min(percentage, 100)}%`,
                  transition: 'width 0.5s ease',
                }}
                role="progressbar"
                aria-valuenow={percentage}
                aria-valuemin="0"
                aria-valuemax="100"
                aria-label={`${current} de ${total} (${formatDecimal(percentage, 1)}%)`}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: scheme.textLight }}>
                {formatDecimal(percentage, 1)}% do total
              </span>
              <span style={{ fontSize: '0.75rem', color: scheme.text }}>
                {total.toLocaleString('pt-PT')} total
              </span>
            </div>
          </div>

          {/* Total Career */}
          <div style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            borderTop: `1px solid ${scheme.border}`,
            paddingTop: '8px',
          }}>
            <span style={{ fontSize: '0.75rem', color: scheme.textLight }}>Total carreira</span>
            <span style={{ fontSize: '1.125rem', fontWeight: 600, color: scheme.text, fontFamily: tokens.fonts.mono }}>
              {total.toLocaleString('pt-PT')}
            </span>
          </div>
        </div>
      </div>

      {/* Screen reader description */}
      <p id={`${tabId}-description`} className="sr-only">
        {description}. Clique para ver detalhes.
      </p>
    </article>
  );
};

/**
 * Skeleton Loading Card for Statistics - Data Observatory theme
 */
const StatisticCardSkeleton = ({ colorScheme = 'gray' }) => {
  const scheme = colorSchemes[colorScheme] || { bg: '#F9FAFB', bgSecondary: '#F3F4F6', border: '#E5E7EB', primary: '#D1D5DB' };
  return (
    <article
      style={{
        background: `linear-gradient(135deg, ${scheme.bg} 0%, ${scheme.bgSecondary} 100%)`,
        borderRadius: '4px',
        border: `1px solid ${scheme.border}`,
        padding: '16px',
        fontFamily: tokens.fonts.body,
      }}
      role="listitem"
      aria-label="A carregar estatística..."
    >
      <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ padding: '10px', backgroundColor: scheme.primary || '#D1D5DB', borderRadius: '4px', opacity: 0.5 }}>
          <div style={{ width: '20px', height: '20px', backgroundColor: '#FFFFFF', borderRadius: '2px' }} />
        </div>
        <div style={{ padding: '4px 8px', backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: '9999px' }}>
          <div style={{ width: '48px', height: '12px', backgroundColor: '#D1D5DB', borderRadius: '2px' }} />
        </div>
      </header>
      <div>
        <div style={{ width: '80px', height: '16px', backgroundColor: '#D1D5DB', borderRadius: '2px', marginBottom: '12px' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ width: '48px', height: '16px', backgroundColor: '#D1D5DB', borderRadius: '2px' }} />
          <div style={{ width: '64px', height: '32px', backgroundColor: '#D1D5DB', borderRadius: '2px' }} />
        </div>
        <div style={{ width: '100%', height: '6px', backgroundColor: '#E5E7EB', borderRadius: '9999px', marginBottom: '8px' }}>
          <div style={{ width: '60%', height: '100%', backgroundColor: '#D1D5DB', borderRadius: '9999px' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: `1px solid ${tokens.colors.border}`, paddingTop: '8px' }}>
          <div style={{ width: '80px', height: '12px', backgroundColor: '#D1D5DB', borderRadius: '2px' }} />
          <div style={{ width: '56px', height: '20px', backgroundColor: '#D1D5DB', borderRadius: '2px' }} />
        </div>
      </div>
    </article>
  );
};

/**
 * Statistics Loading Skeleton Component - Data Observatory theme
 */
const StatisticsLoadingSkeleton = () => (
  <section
    style={{
      backgroundColor: tokens.colors.bgSecondary,
      borderRadius: '4px',
      border: `1px solid ${tokens.colors.border}`,
      marginBottom: '32px',
      fontFamily: tokens.fonts.body,
    }}
    aria-label="A carregar estatísticas..."
  >
    <header style={{ padding: '16px 24px', borderBottom: `1px solid ${tokens.colors.border}` }}>
      <div style={{ width: '256px', height: '24px', backgroundColor: '#D1D5DB', borderRadius: '2px', marginBottom: '8px' }} />
      <div style={{ width: '384px', height: '16px', backgroundColor: '#E5E7EB', borderRadius: '2px' }} />
    </header>
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }} role="list">
        <StatisticCardSkeleton colorScheme="blue" />
        <StatisticCardSkeleton colorScheme="green" />
        <StatisticCardSkeleton colorScheme="purple" />
        <StatisticCardSkeleton colorScheme="orange" />
      </div>
    </div>
  </section>
);

/**
 * Statistics Error Component - Data Observatory theme
 */
const StatisticsError = ({ error, onRetry }) => (
  <section
    style={{
      backgroundColor: tokens.colors.bgSecondary,
      borderRadius: '4px',
      border: `1px solid ${tokens.colors.border}`,
      marginBottom: '32px',
      fontFamily: tokens.fonts.body,
    }}
    role="alert"
    aria-labelledby="error-heading"
  >
    <header style={{ padding: '16px 24px', borderBottom: `1px solid ${tokens.colors.border}` }}>
      <h3
        id="error-heading"
        style={{ fontSize: '1.125rem', fontWeight: 600, color: tokens.colors.textPrimary, fontFamily: tokens.fonts.headline }}
      >
        Resumo de Atividade Parlamentar
      </h3>
    </header>
    <div style={{ padding: '24px', textAlign: 'center' }}>
      <AlertTriangle style={{ margin: '0 auto 16px', width: '48px', height: '48px', color: tokens.colors.danger }} aria-hidden="true" />
      <h4 style={{ fontSize: '1.125rem', fontWeight: 500, color: tokens.colors.textPrimary, marginBottom: '8px' }}>
        Erro ao carregar estatísticas
      </h4>
      <p style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, marginBottom: '16px' }}>
        Não foi possível carregar as estatísticas de atividade. Por favor, tente novamente.
      </p>
      {error && (
        <details style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, marginBottom: '16px' }}>
          <summary style={{ cursor: 'pointer' }}>Detalhes técnicos</summary>
          <p style={{ marginTop: '8px', textAlign: 'left', backgroundColor: tokens.colors.bgPrimary, padding: '8px', borderRadius: '4px' }}>{error}</p>
        </details>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '8px 16px',
            border: 'none',
            fontSize: '0.875rem',
            fontWeight: 500,
            borderRadius: '4px',
            color: '#FFFFFF',
            backgroundColor: tokens.colors.primary,
            cursor: 'pointer',
            transition: 'background-color 0.15s ease',
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = tokens.colors.primaryLight}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = tokens.colors.primary}
        >
          Tentar novamente
        </button>
      )}
    </div>
  </section>
);

/**
 * Mandate Timeline Component - Visual horizontal timeline showing career progression
 */
const MandateTimeline = ({ mandatos, currentLegislature }) => {
  if (!mandatos || mandatos.length === 0) return null;

  // Sort mandates chronologically (oldest first)
  const sortedMandatos = [...mandatos].sort((a, b) => {
    const legA = parseInt(a.legislatura_numero?.replace(/\D/g, '') || '0');
    const legB = parseInt(b.legislatura_numero?.replace(/\D/g, '') || '0');
    return legA - legB;
  });

  const maxMandates = sortedMandatos.length;

  return (
    <section style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '4px',
      padding: '20px 24px',
      marginBottom: '24px',
    }}>
      <h3 style={{
        fontFamily: tokens.fonts.body,
        fontSize: '0.75rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: tokens.colors.textSecondary,
        marginBottom: '16px',
      }}>
        Percurso Parlamentar
      </h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {/* Timeline Bar */}
        <div style={{
          display: 'flex',
          gap: '4px',
          height: '40px',
        }}>
          {sortedMandatos.map((mandato, index) => {
            const isCurrent = mandato.legislatura_numero === currentLegislature;
            return (
              <div
                key={mandato.deputado_id || index}
                style={{
                  flex: 1,
                  backgroundColor: isCurrent ? tokens.colors.primary : tokens.colors.primaryLight || '#2D6A4F',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative',
                  opacity: isCurrent ? 1 : 0.7,
                  transition: 'opacity 0.15s ease',
                  cursor: 'default',
                }}
                title={`${mandato.legislatura_nome} · ${mandato.partido_sigla} · ${mandato.circulo}`}
                onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                onMouseLeave={(e) => e.currentTarget.style.opacity = isCurrent ? '1' : '0.7'}
              >
                <span style={{
                  color: '#FFFFFF',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  fontFamily: tokens.fonts.mono,
                }}>
                  {mandato.legislatura_numero}
                </span>
              </div>
            );
          })}
        </div>

        {/* Timeline Labels */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: '0.6875rem',
          color: tokens.colors.textMuted,
        }}>
          <span>{sortedMandatos[0]?.mandato_inicio ? new Date(sortedMandatos[0].mandato_inicio).getFullYear() : ''}</span>
          <span>{sortedMandatos[maxMandates - 1]?.is_current ? 'Atual' : sortedMandatos[maxMandates - 1]?.mandato_fim ? new Date(sortedMandatos[maxMandates - 1].mandato_fim).getFullYear() : ''}</span>
        </div>
      </div>

      {/* Summary */}
      <div style={{
        marginTop: '12px',
        paddingTop: '12px',
        borderTop: `1px solid ${tokens.colors.border}`,
        fontSize: '0.8125rem',
        color: tokens.colors.textSecondary,
      }}>
        <span style={{ fontWeight: 500 }}>{maxMandates} mandato{maxMandates > 1 ? 's' : ''}</span>
        {sortedMandatos.length > 1 && (
          <span> · {[...new Set(sortedMandatos.map(m => m.partido_sigla))].join(', ')}</span>
        )}
        {sortedMandatos.length > 1 && (
          <span> · {[...new Set(sortedMandatos.map(m => m.circulo))].join(', ')}</span>
        )}
      </div>
    </section>
  );
};

/**
 * Dossier Section Component - Collapsible section with preview
 */
const DossierSection = ({
  title,
  icon: Icon,
  count,
  preview,
  children,
  defaultExpanded = false,
  isEmpty = false
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div style={{
      borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
      opacity: isEmpty ? 0.6 : 1,
    }}>
      <button
        onClick={() => !isEmpty && setIsExpanded(!isExpanded)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          background: 'none',
          border: 'none',
          cursor: isEmpty ? 'default' : 'pointer',
          transition: 'background-color 0.15s ease',
        }}
        onMouseEnter={(e) => !isEmpty && (e.currentTarget.style.backgroundColor = 'rgba(0,0,0,0.02)')}
        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
        aria-expanded={isExpanded}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon style={{ width: '18px', height: '18px', color: tokens.colors.primary }} />
          <h4 style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.875rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.03em',
            color: tokens.colors.textPrimary,
            margin: 0,
          }}>
            {title}
          </h4>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '0.75rem',
            color: isEmpty ? tokens.colors.textMuted : tokens.colors.textSecondary,
            backgroundColor: tokens.colors.bgTertiary,
            padding: '4px 8px',
            borderRadius: '4px',
            fontStyle: isEmpty ? 'italic' : 'normal',
          }}>
            {isEmpty ? 'Sem registos' : count}
          </span>
          {!isEmpty && (
            <ChevronDown
              style={{
                width: '16px',
                height: '16px',
                color: tokens.colors.textMuted,
                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.2s ease',
              }}
            />
          )}
        </div>
      </button>

      {/* Preview when collapsed */}
      {!isExpanded && !isEmpty && preview && (
        <div style={{
          padding: '0 20px 12px 50px',
          fontSize: '0.8125rem',
          color: tokens.colors.textSecondary,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}>
          {preview}
        </div>
      )}

      {/* Expanded content */}
      {isExpanded && !isEmpty && (
        <div style={{
          padding: '16px 20px',
          backgroundColor: 'white',
          borderTop: `1px solid ${tokens.colors.border}`,
        }}>
          {children}
        </div>
      )}
    </div>
  );
};

/**
 * Biographical Dossier Component - Accordion container for all biographical data
 */
const BiographicalDossier = ({ deputado }) => {
  // Count items for each section
  const habilitacoesCount = deputado.habilitacoes_academicas ?
    deputado.habilitacoes_academicas.split(';').filter(h => h.trim()).length : 0;
  const cargosCount = deputado.cargos_funcoes?.length || 0;
  const titulosCount = deputado.titulos?.length || 0;
  const condecoracoesCount = deputado.condecoracoes?.length || 0;
  const obrasCount = deputado.obras_publicadas?.length || 0;
  const orgaosCount = deputado.atividades_orgaos?.length || 0;

  return (
    <section style={{
      backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
      border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
      borderRadius: '4px',
      overflow: 'hidden',
      marginTop: '24px',
    }}>
      <header style={{
        padding: '16px 20px',
        borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
        backgroundColor: 'rgba(255,255,255,0.5)',
      }}>
        <h3 style={{
          fontFamily: tokens.fonts.headline,
          fontSize: '1.125rem',
          fontWeight: 600,
          color: tokens.colors.textPrimary,
          margin: 0,
        }}>
          Dossier Biográfico
        </h3>
        <p style={{
          fontSize: '0.8125rem',
          color: tokens.colors.textSecondary,
          marginTop: '4px',
        }}>
          Informação de contexto sobre o deputado
        </p>
      </header>

      {/* Percurso Profissional */}
      <DossierSection
        title="Percurso Profissional"
        icon={Briefcase}
        count={deputado.profissao ? '1 registo' : '0'}
        preview={deputado.profissao}
        isEmpty={!deputado.profissao}
        defaultExpanded={true}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {deputado.profissao && (
            <div>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: tokens.colors.textMuted,
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
              }}>Profissão Atual</span>
              <p style={{
                fontSize: '0.9375rem',
                color: tokens.colors.textPrimary,
                marginTop: '4px',
              }}>{deputado.profissao}</p>
            </div>
          )}
        </div>
      </DossierSection>

      {/* Habilitações Académicas */}
      <DossierSection
        title="Habilitações Académicas"
        icon={GraduationCap}
        count={habilitacoesCount > 0 ? `${habilitacoesCount} grau${habilitacoesCount > 1 ? 's' : ''}` : '0'}
        preview={deputado.habilitacoes_academicas?.split(';')[0]?.trim()}
        isEmpty={habilitacoesCount === 0}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {deputado.habilitacoes_academicas?.split(';').filter(h => h.trim()).map((hab, index) => (
            <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <div style={{
                width: '6px',
                height: '6px',
                backgroundColor: tokens.colors.success,
                borderRadius: '50%',
                marginTop: '8px',
                flexShrink: 0,
              }} />
              <span style={{ fontSize: '0.9375rem', color: tokens.colors.textPrimary }}>{hab.trim()}</span>
            </div>
          ))}
        </div>
      </DossierSection>

      {/* Cargos e Funções */}
      <DossierSection
        title="Cargos e Funções Políticas"
        icon={Building2}
        count={cargosCount > 0 ? `${cargosCount} cargo${cargosCount > 1 ? 's' : ''}` : '0'}
        preview={deputado.cargos_funcoes?.[0]?.cargo_nome}
        isEmpty={cargosCount === 0}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {deputado.cargos_funcoes?.map((cargo, index) => (
            <div key={index} style={{
              padding: '12px',
              backgroundColor: tokens.colors.bgTertiary,
              borderRadius: '4px',
            }}>
              <div style={{ fontWeight: 500, color: tokens.colors.textPrimary, marginBottom: '4px' }}>
                {cargo.cargo_nome || cargo.cargo}
              </div>
              {cargo.entidade && (
                <div style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
                  {cargo.entidade}
                </div>
              )}
              {(cargo.data_inicio || cargo.data_fim) && (
                <div style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, marginTop: '4px' }}>
                  {cargo.data_inicio && new Date(cargo.data_inicio).toLocaleDateString('pt-PT')}
                  {cargo.data_fim && ` – ${new Date(cargo.data_fim).toLocaleDateString('pt-PT')}`}
                </div>
              )}
            </div>
          ))}
        </div>
      </DossierSection>

      {/* Atividade em Órgãos Parlamentares */}
      <DossierSection
        title="Órgãos Parlamentares"
        icon={Users}
        count={orgaosCount > 0 ? `${orgaosCount} órgão${orgaosCount > 1 ? 's' : ''}` : '0'}
        preview={deputado.atividades_orgaos?.[0]?.nome}
        isEmpty={orgaosCount === 0}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {deputado.atividades_orgaos?.map((orgao, index) => (
            <div key={index} style={{
              padding: '12px',
              backgroundColor: '#FFF7ED',
              border: `1px solid ${tokens.colors.orange}20`,
              borderRadius: '4px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 500, color: tokens.colors.textPrimary }}>
                  {orgao.nome}
                </span>
                {orgao.sigla && (
                  <span style={{ fontSize: '0.75rem', color: tokens.colors.orange }}>({orgao.sigla})</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{
                  fontSize: '0.6875rem',
                  fontWeight: 500,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: orgao.titular ? '#DCFCE7' : '#FEF3C7',
                  color: orgao.titular ? tokens.colors.success : '#92400E',
                }}>
                  {orgao.tipo_membro}
                </span>
                {orgao.cargo && orgao.cargo !== 'membro' && (
                  <span style={{
                    fontSize: '0.6875rem',
                    fontWeight: 500,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#E8F5E9',
                    color: tokens.colors.primary,
                  }}>
                    {orgao.cargo}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </DossierSection>

      {/* Títulos e Condecorações (combined) */}
      <DossierSection
        title="Títulos e Condecorações"
        icon={Medal}
        count={(titulosCount + condecoracoesCount) > 0 ? `${titulosCount + condecoracoesCount} registo${(titulosCount + condecoracoesCount) > 1 ? 's' : ''}` : '0'}
        preview={deputado.titulos?.[0]?.titulo || deputado.condecoracoes?.[0]?.descricao}
        isEmpty={(titulosCount + condecoracoesCount) === 0}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {deputado.titulos?.map((titulo, index) => (
            <div key={`titulo-${index}`} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <Award style={{ width: '16px', height: '16px', color: tokens.colors.ouroConstitucional || '#C9A227', flexShrink: 0, marginTop: '2px' }} />
              <span style={{ fontSize: '0.9375rem', color: tokens.colors.textPrimary }}>{titulo.titulo || titulo.descricao}</span>
            </div>
          ))}
          {deputado.condecoracoes?.map((cond, index) => (
            <div key={`cond-${index}`} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <Medal style={{ width: '16px', height: '16px', color: tokens.colors.ouroConstitucional || '#C9A227', flexShrink: 0, marginTop: '2px' }} />
              <span style={{ fontSize: '0.9375rem', color: tokens.colors.textPrimary }}>{cond.descricao}</span>
            </div>
          ))}
        </div>
      </DossierSection>

      {/* Obras Publicadas */}
      <DossierSection
        title="Obras Publicadas"
        icon={BookOpen}
        count={obrasCount > 0 ? `${obrasCount} obra${obrasCount > 1 ? 's' : ''}` : '0'}
        preview={deputado.obras_publicadas?.[0]?.titulo}
        isEmpty={obrasCount === 0}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {deputado.obras_publicadas?.map((obra, index) => (
            <div key={index} style={{
              padding: '12px',
              backgroundColor: tokens.colors.bgTertiary,
              borderRadius: '4px',
            }}>
              <div style={{ fontWeight: 500, color: tokens.colors.textPrimary, marginBottom: '4px' }}>
                {obra.titulo}
              </div>
              {obra.editora && (
                <div style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary }}>
                  {obra.editora}
                </div>
              )}
              {obra.ano && (
                <div style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, marginTop: '4px' }}>
                  {obra.ano}
                </div>
              )}
            </div>
          ))}
        </div>
      </DossierSection>

      {/* Biografia Completa */}
      <DossierSection
        title="Biografia Completa"
        icon={User}
        count={deputado.biografia ? '1 registo' : '0'}
        preview={deputado.biografia?.substring(0, 100)}
        isEmpty={!deputado.biografia}
      >
        <div style={{
          fontSize: '0.9375rem',
          color: tokens.colors.textSecondary,
          lineHeight: 1.7,
          whiteSpace: 'pre-line',
        }}>
          {deputado.biografia}
        </div>
      </DossierSection>
    </section>
  );
};

const DeputadoDetalhes = () => {
  const { cadId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [deputado, setDeputado] = useState(null);
  const [atividades, setAtividades] = useState(null);
  const [conflitosInteresse, setConflitosInteresse] = useState(null);
  const [attendanceData, setAttendanceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [interventionTypeFilter, setInterventionTypeFilter] = useState(searchParams.get('tipo_intervencao') || '');
  const [interventionSort, setInterventionSort] = useState(searchParams.get('ordenacao_intervencoes') || 'newest');
  const [currentPage, setCurrentPage] = useState(parseInt(searchParams.get('page')) || 1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalInterventions, setTotalInterventions] = useState(0);
  const [expandedInitiatives, setExpandedInitiatives] = useState(new Set());
  const [selectedLegislature, setSelectedLegislature] = useState(null);
  
  // Helper function to generate deputy URLs
  const getDeputadoUrl = (cadId) => {
    return `/deputados/${cadId}`;
  };

  // Toggle initiative details expansion
  const toggleInitiativeDetails = (index) => {
    const newExpanded = new Set(expandedInitiatives);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedInitiatives(newExpanded);
  };

  // Get active tab from URL hash, default to 'intervencoes'
  const getActiveTabFromUrl = () => {
    const hash = location.hash.replace('#', '');
    const validTabs = ['intervencoes', 'iniciativas', 'votacoes', 'attendance', 'conflitos-interesse'];
    // Support legacy 'biografia' hash by redirecting to main page (no tab)
    if (hash === 'biografia' || hash === 'mandatos-anteriores') {
      return 'intervencoes';
    }
    return validTabs.includes(hash) ? hash : 'intervencoes';
  };

  const [activeTab, setActiveTab] = useState(getActiveTabFromUrl());

  // Sync activeTab with URL hash changes
  useEffect(() => {
    const handleHashChange = () => {
      setActiveTab(getActiveTabFromUrl());
    };

    // Listen for hash changes (browser back/forward)
    window.addEventListener('hashchange', handleHashChange);
    
    // Update tab when location changes
    setActiveTab(getActiveTabFromUrl());

    return () => {
      window.removeEventListener('hashchange', handleHashChange);
    };
  }, [location.hash]);

  // Handle tab change with URL update
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    navigate(`#${tabId}`, { replace: true });
  };

  // Set default tab in URL if no hash is present
  useEffect(() => {
    if (!location.hash) {
      navigate('#biografia', { replace: true });
    }
  }, [navigate, location.hash]);

  // Function to update URL parameters
  const updateInterventionParams = (newParams) => {
    const updatedParams = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value && value !== '') {
        updatedParams.set(key, value);
      } else {
        updatedParams.delete(key);
      }
    });
    setSearchParams(updatedParams);
  };

  useEffect(() => {
    const fetchDados = async () => {
      try {
        setLoading(true);

        // Build atividades URL with parameters
        const apiParams = new URLSearchParams();
        if (interventionTypeFilter) {
          apiParams.set('tipo_intervencao', interventionTypeFilter);
        }
        if (interventionSort) {
          apiParams.set('ordenacao_intervencoes', interventionSort);
        }
        if (selectedLegislature) {
          apiParams.set('legislatura', selectedLegislature);
        }
        apiParams.set('page', currentPage.toString());
        apiParams.set('per_page', '50');

        // Fetch all data in parallel
        const [deputadoResult, atividadesResult, conflitosResult, attendanceResult] = await Promise.allSettled([
          apiFetch(`deputados/${cadId}/detalhes`).then(r => { if (!r.ok) throw new Error('Erro ao carregar dados do deputado'); return r.json(); }),
          apiFetch(`deputados/${cadId}/atividades?${apiParams.toString()}`).then(r => { if (!r.ok) throw new Error('Erro ao carregar atividades do deputado'); return r.json(); }),
          apiFetch(`deputados/${cadId}/conflitos-interesse`).then(r => r.ok ? r.json() : null),
          apiFetch(`deputados/${cadId}/attendance`).then(r => r.ok ? r.json() : null),
        ]);

        // Process required results
        if (deputadoResult.status === 'rejected') throw deputadoResult.reason;
        setDeputado(deputadoResult.value);

        if (atividadesResult.status === 'rejected') throw atividadesResult.reason;
        setAtividades(atividadesResult.value);
        if (atividadesResult.value.intervention_metadata) {
          setTotalPages(atividadesResult.value.intervention_metadata.pages);
          setTotalInterventions(atividadesResult.value.intervention_metadata.total);
        }

        // Process optional results
        if (conflitosResult.status === 'fulfilled' && conflitosResult.value) {
          setConflitosInteresse(conflitosResult.value);
        }
        if (attendanceResult.status === 'fulfilled' && attendanceResult.value) {
          setAttendanceData(attendanceResult.value);
        }

      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (cadId) {
      fetchDados();
    }
  }, [cadId, interventionTypeFilter, interventionSort, currentPage, selectedLegislature]);

  if (loading) {
    return <LoadingSpinner message="A carregar dados do deputado" />;
  }

  if (error) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: tokens.colors.bgPrimary,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: tokens.fonts.body,
      }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{
            color: tokens.colors.accent,
            marginBottom: '16px',
            fontSize: '0.938rem',
          }}>Erro: {error}</p>
          <Link
            to="/deputados"
            style={{
              color: tokens.colors.primary,
              textDecoration: 'none',
            }}
            onMouseEnter={(e) => e.target.style.textDecoration = 'underline'}
            onMouseLeave={(e) => e.target.style.textDecoration = 'none'}
          >
            Voltar aos deputados
          </Link>
        </div>
      </div>
    );
  }

  if (!deputado) {
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: tokens.colors.bgPrimary,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: tokens.fonts.body,
      }}>
        <p style={{ color: tokens.colors.textSecondary }}>Deputado não encontrado</p>
      </div>
    );
  }

  const tabs = [
    { id: 'intervencoes', label: 'Intervenções', icon: MessageSquare },
    { id: 'iniciativas', label: 'Iniciativas', icon: FileText },
    { id: 'votacoes', label: 'Votações', icon: Vote },
    { id: 'attendance', label: 'Presenças', icon: Activity },
    { id: 'conflitos-interesse', label: 'Registo de Interesses', icon: Shield }
  ];

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: tokens.colors.bgPrimary,
      fontFamily: tokens.fonts.body,
    }}>
      {/* Header */}
      <div style={{
        backgroundColor: tokens.colors.bgSecondary,
        borderBottom: `1px solid ${tokens.colors.border}`,
      }}>
        <div style={{
          maxWidth: '1280px',
          margin: '0 auto',
          padding: '16px 24px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <Link
                to="/deputados"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  color: tokens.colors.textSecondary,
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  transition: 'color 0.15s ease',
                }}
                onMouseEnter={(e) => e.currentTarget.style.color = tokens.colors.primary}
                onMouseLeave={(e) => e.currentTarget.style.color = tokens.colors.textSecondary}
              >
                <ArrowLeft style={{ width: '18px', height: '18px', marginRight: '8px' }} />
                Voltar aos Deputados
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div style={{
        maxWidth: '1280px',
        margin: '0 auto',
        padding: '32px 24px',
      }}>
        {/* Perfil do Deputado */}
        <div style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          marginBottom: '32px',
        }}>
          <div style={{ padding: '32px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '24px', flexWrap: 'wrap' }}>
              {/* Avatar */}
              <div style={{ flexShrink: 0 }}>
                {deputado.picture_url ? (
                  <img
                    src={deputado.picture_url}
                    alt={deputado.nome}
                    style={{
                      width: '96px',
                      height: '96px',
                      borderRadius: '50%',
                      objectFit: 'cover',
                      backgroundColor: tokens.colors.border,
                      border: `2px solid ${tokens.colors.border}`,
                    }}
                    onError={(e) => {
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div style={{
                  width: '96px',
                  height: '96px',
                  borderRadius: '50%',
                  backgroundColor: '#E8F5E9',
                  display: deputado.picture_url ? 'none' : 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}>
                  <User style={{ width: '48px', height: '48px', color: tokens.colors.primary }} />
                </div>
              </div>

              {/* Informações Básicas */}
              <div style={{ flex: 1, minWidth: '300px' }}>
                <h1 style={{
                  fontFamily: tokens.fonts.headline,
                  fontSize: '1.875rem',
                  fontWeight: 700,
                  color: tokens.colors.textPrimary,
                  marginBottom: '8px',
                  lineHeight: 1.2,
                }}>
                  {deputado.nome}
                </h1>

                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: '16px',
                  color: tokens.colors.textSecondary,
                  marginBottom: '16px',
                  fontSize: '0.875rem',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <Briefcase style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                    <span>{deputado.profissao || 'Profissão não indicada'}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <MapPin style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                    <span>{deputado.circulo}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <Calendar style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                    <span>Mandato desde {new Date(deputado.mandato.inicio).toLocaleDateString('pt-PT')}</span>
                  </div>
                </div>

                {/* Partido */}
                {deputado.partido && (
                  <Link
                    to={`/partidos/${encodeURIComponent(deputado.partido.id)}`}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      fontSize: '0.813rem',
                      fontWeight: 500,
                      backgroundColor: '#E8F5E9',
                      color: tokens.colors.primary,
                      textDecoration: 'none',
                      border: `1px solid ${tokens.colors.primary}20`,
                      transition: 'background-color 0.15s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#C8E6C9'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#E8F5E9'}
                  >
                    {deputado.partido.sigla} - {deputado.partido.nome}
                  </Link>
                )}
              </div>

              {/* Status and Actions */}
              <div style={{ flexShrink: 0 }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '12px' }}>
                  {/* Status Badge - Enhanced with seated/suspended/resigned statuses */}
                  {(() => {
                    const status = deputado.mandate_status || deputado.career_info?.mandate_status;
                    const isSeated = deputado.is_seated || deputado.career_info?.is_seated;
                    const isActive = deputado.career_info?.is_currently_active;

                    // Determine badge style based on status
                    if (isSeated) {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: tokens.colors.successBg,
                          color: tokens.colors.success,
                          border: `1px solid ${tokens.colors.success}30`,
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: tokens.colors.success,
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Em Exercício
                        </span>
                      );
                    } else if (status === 'Suspenso(Eleito)') {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: '#FEF3C7',
                          color: '#92400E',
                          border: '1px solid #F59E0B30',
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: '#F59E0B',
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Suspenso (Eleito)
                        </span>
                      );
                    } else if (status === 'Renunciou') {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: '#FEE2E2',
                          color: '#991B1B',
                          border: '1px solid #EF444430',
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: '#EF4444',
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Renunciou
                        </span>
                      );
                    } else if (status && status.startsWith('Suspenso')) {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: '#FEF3C7',
                          color: '#92400E',
                          border: '1px solid #F59E0B30',
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: '#F59E0B',
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Suspenso
                        </span>
                      );
                    } else if (isActive) {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: tokens.colors.successBg,
                          color: tokens.colors.success,
                          border: `1px solid ${tokens.colors.success}30`,
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: tokens.colors.success,
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Ativo
                        </span>
                      );
                    } else if (deputado.career_info?.latest_completed_mandate) {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: tokens.colors.bgPrimary,
                          color: tokens.colors.textSecondary,
                          border: `1px solid ${tokens.colors.border}`,
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: tokens.colors.textMuted,
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Último mandato: {deputado.career_info.latest_completed_mandate.legislatura} ({deputado.career_info.latest_completed_mandate.periodo})
                        </span>
                      );
                    } else {
                      return (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          fontSize: '0.813rem',
                          fontWeight: 500,
                          backgroundColor: tokens.colors.bgPrimary,
                          color: tokens.colors.textSecondary,
                          border: `1px solid ${tokens.colors.border}`,
                        }}>
                          <div style={{
                            width: '8px',
                            height: '8px',
                            backgroundColor: tokens.colors.textMuted,
                            borderRadius: '50%',
                            marginRight: '8px',
                          }} />
                          Inativo
                        </span>
                      );
                    }
                  })()}

                  {/* Email Button - Only show for active deputies */}
                  {deputado.career_info?.is_currently_active && (
                    <button
                      onClick={() => {
                        const emailUrl = `https://www.parlamento.pt/DeputadoGP/Paginas/EmailDeputado.aspx?BID=${deputado.id_cadastro}`;
                        window.open(emailUrl, '_blank', 'width=800,height=600,scrollbars=yes,resizable=yes');
                      }}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        padding: '8px 16px',
                        border: `1px solid ${tokens.colors.primary}`,
                        fontSize: '0.813rem',
                        fontWeight: 500,
                        borderRadius: '4px',
                        color: tokens.colors.primary,
                        backgroundColor: tokens.colors.bgSecondary,
                        cursor: 'pointer',
                        transition: 'background-color 0.15s ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#E8F5E9'}
                      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = tokens.colors.bgSecondary}
                      title="Enviar email através do site oficial do Parlamento"
                    >
                      <Mail style={{ width: '16px', height: '16px', marginRight: '8px' }} />
                      Enviar e-mail
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Mandate Timeline - Visual career progression */}
        {deputado.mandatos_historico && deputado.mandatos_historico.length > 1 && (
          <MandateTimeline
            mandatos={deputado.mandatos_historico}
            currentLegislature={deputado.legislatura_numero}
          />
        )}

        {/* Political Performance Metrics - Meaningful Statistics */}
        <div style={{ marginBottom: '32px' }}>
          {/* Constitutional Modernism Header */}
          <header style={{
            marginBottom: '24px',
            paddingBottom: '16px',
            borderBottom: `2px solid ${tokens.colors.primary}`,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
              <BarChart3 style={{ width: '24px', height: '24px', color: tokens.colors.primary, marginRight: '10px' }} />
              <h3 style={{
                fontFamily: tokens.fonts.headline,
                fontSize: '1.25rem',
                fontWeight: 600,
                color: tokens.colors.primary,
                margin: 0,
              }}>Resumo de Atividade Parlamentar</h3>
            </div>
            <p style={{
              fontSize: '0.875rem',
              color: tokens.colors.textSecondary,
              margin: 0,
            }}>
              {plural(deputado.estatisticas.total_mandatos, 'mandato', 'mandatos')} • {formatDecimal(deputado.estatisticas.tempo_servico_anos, 1)} anos de serviço • {String(deputado.estatisticas.legislaturas_servidas || '').includes(',') ? 'Legislaturas' : 'Legislatura'} {deputado.estatisticas.legislaturas_servidas}
            </p>
          </header>

          {/* Primary Stats Grid - 2x2 on desktop, 1 column on mobile */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '16px',
            marginBottom: '24px',
          }}>
            {/* INICIATIVAS CARD - With Context Frame */}
            <article style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '6px',
              padding: '20px',
              transition: 'box-shadow 0.15s ease',
            }}>
              <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{
                  padding: '10px',
                  backgroundColor: tokens.colors.primary,
                  borderRadius: '4px',
                }}>
                  <FileText style={{ width: '20px', height: '20px', color: '#FFFFFF' }} />
                </div>
                <span style={{
                  padding: '4px 10px',
                  backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
                  borderRadius: '12px',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  color: tokens.colors.textSecondary,
                }}>
                  Legislativo
                </span>
              </header>

              <h4 style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: tokens.colors.primary,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '12px',
              }}>Iniciativas Legislativas</h4>

              {/* Latest legislature only: how the projetos were signed and how they ended */}
              {(() => {
                const latest = deputado.estatisticas.iniciativas_legislaturas?.[0];
                if (!latest) {
                  return (
                    <p style={{ margin: 0, fontSize: '0.875rem', color: tokens.colors.textSecondary }}>
                      Sem projetos de lei, de resolução ou de deliberação assinados.
                    </p>
                  );
                }
                return (
                  <div>
                    <div style={{ fontSize: '0.75rem', color: tokens.colors.textMuted, marginBottom: '8px' }}>
                      {legislatureName(latest.legislatura)}{latest.aberta ? ' (em curso)' : ''}
                    </div>
                    <SigningCounts assinatura={latest.assinatura} showNote={false} />
                    <div style={{ padding: '12px 0 0 0', marginTop: '12px', borderTop: `1px solid ${tokens.colors.border}` }}>
                      <ApprovalLines aprovacao={latest.aprovacao} aberta={latest.aberta} showNote={false} />
                    </div>
                  </div>
                );
              })()}

            </article>

            {/* INTERVENÇÕES CARD */}
            <article style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '6px',
              padding: '20px',
            }}>
              <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{
                  padding: '10px',
                  backgroundColor: tokens.colors.verdeClaro || '#2D6A4F',
                  borderRadius: '4px',
                }}>
                  <MessageSquare style={{ width: '20px', height: '20px', color: '#FFFFFF' }} />
                </div>
                <span style={{
                  padding: '4px 10px',
                  backgroundColor: '#F0FDF4',
                  borderRadius: '12px',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  color: tokens.colors.success,
                }}>
                  Plenário
                </span>
              </header>

              <h4 style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: tokens.colors.verdeClaro || '#2D6A4F',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '12px',
              }}>Intervenções Parlamentares</h4>

              <div style={{ marginBottom: '12px' }}>
                <span style={{
                  fontSize: '2rem',
                  fontWeight: 700,
                  color: tokens.colors.textPrimary,
                  fontFamily: tokens.fonts.mono,
                }}>
                  {deputado.estatisticas.intervencoes_parlamentares.toLocaleString('pt-PT')}
                </span>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, marginLeft: '8px' }}>
                  em plenário
                </span>
              </div>

              {/* Within the group, in the latest closed legislature */}
              <div style={{ paddingTop: '12px', borderTop: `1px solid ${tokens.colors.border}` }}>
                <GroupComparison
                  comparacao={deputado.estatisticas.comparacao?.intervencoes}
                  label="Comparação com o grupo parlamentar"
                  closedLabel={true}
                />
              </div>
            </article>

            {/* PRESENÇA CARD: latest legislature with attendance lists */}
            {deputado.estatisticas.assiduidade && (
              <AttendanceCard
                assiduidade={deputado.estatisticas.assiduidade}
                onOpen={() => handleTabChange('attendance')}
              />
            )}

            {/* CARREIRA CARD */}
            <article style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '6px',
              padding: '20px',
            }}>
              <header style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{
                  padding: '10px',
                  backgroundColor: '#7C3AED',
                  borderRadius: '4px',
                }}>
                  <Award style={{ width: '20px', height: '20px', color: '#FFFFFF' }} />
                </div>
                <span style={{
                  padding: '4px 10px',
                  backgroundColor: '#F3E8FF',
                  borderRadius: '12px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  color: '#7C3AED',
                }}>
                  {deputado.estatisticas.nivel_experiencia}
                </span>
              </header>

              <h4 style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#7C3AED',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                marginBottom: '12px',
              }}>Carreira Parlamentar</h4>

              <div style={{ marginBottom: '12px' }}>
                <span style={{
                  fontSize: '2rem',
                  fontWeight: 700,
                  color: tokens.colors.textPrimary,
                  fontFamily: tokens.fonts.mono,
                }}>
                  {deputado.estatisticas.total_mandatos}
                </span>
                <span style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, marginLeft: '8px' }}>
                  {deputado.estatisticas.total_mandatos === 1 ? 'mandato' : 'mandatos'}
                </span>
              </div>

              <div style={{
                paddingTop: '12px',
                borderTop: `1px solid ${tokens.colors.border}`,
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
              }}>
                <div style={{ marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600 }}>{formatDecimal(deputado.estatisticas.tempo_servico_anos, 1)}</span> anos de serviço
                </div>
                <div style={{ fontSize: '0.75rem', color: tokens.colors.textMuted }}>
                  {deputado.estatisticas.legislaturas_servidas}
                </div>
              </div>
            </article>
          </div>

          {/* Written questions to the Government in the latest legislature (#114) */}
          {deputado.perguntas_escritas && (() => {
            const perguntas = deputado.perguntas_escritas;
            return (
              <p
                data-testid="perguntas-escritas"
                style={{
                  margin: '0 0 24px 0',
                  padding: '12px 16px',
                  backgroundColor: tokens.colors.bgSecondary,
                  border: `1px solid ${tokens.colors.border}`,
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  color: tokens.colors.textSecondary,
                }}
              >
                Perguntas escritas ao Governo nesta legislatura:{' '}
                <strong style={{ color: tokens.colors.textPrimary, fontFamily: tokens.fonts.mono }}>
                  {perguntas.total.toLocaleString('pt-PT')}
                </strong>{' '}
                (como autor ou coautor).{' '}
                <a
                  href={perguntas.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: tokens.colors.primary, textDecoration: 'underline' }}
                >
                  Ver as perguntas da {perguntas.legislatura} Legislatura no site do Parlamento
                </a>
              </p>
            );
          })()}

          {/* INITIATIVE TYPES BREAKDOWN */}
          {deputado.estatisticas.iniciativas_por_tipo && deputado.estatisticas.iniciativas_por_tipo.length > 0 && (
            <section style={{
              backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
              border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
              borderRadius: '6px',
              padding: '20px',
              marginBottom: '24px',
            }}>
              <header style={{ marginBottom: '20px', paddingBottom: '12px', borderBottom: `2px solid ${tokens.colors.primary}` }}>
                <h4 style={{
                  fontFamily: tokens.fonts.headline,
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: tokens.colors.primary,
                  margin: '0 0 4px 0',
                }}>Tipos de Iniciativas</h4>
                <p style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary, margin: 0 }}>
                  Iniciativas assinadas em todos os mandatos, por tipo
                </p>
              </header>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {deputado.estatisticas.iniciativas_por_tipo.map((tipo, index) => {
                  const typesSum = deputado.estatisticas.iniciativas_por_tipo.reduce((sum, t) => sum + (t.total || 0), 0) || 1;
                  const percentage = (tipo.total / typesSum * 100);
                  const maxCount = deputado.estatisticas.iniciativas_por_tipo[0]?.total || 1;
                  const barWidth = (tipo.total / maxCount * 100);

                  // Icon mapping for initiative types
                  const tipoIcons = {
                    'J': '📜', // Projeto de Lei
                    'R': '📋', // Projeto de Resolução
                    'I': '🔍', // Inquérito Parlamentar
                    'C': '📖', // Projeto de Revisão Constitucional
                    'A': '⚖️', // Apreciação Parlamentar
                    'G': '📑', // Projeto de Regimento
                  };

                  return (
                    <div
                      key={tipo.codigo}
                      style={{
                        animation: 'slideIn 0.4s ease-out backwards',
                        animationDelay: `${index * 0.05}s`,
                      }}
                    >
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '6px',
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '1rem' }}>{tipoIcons[tipo.codigo] || '📄'}</span>
                          <span style={{
                            fontSize: '0.875rem',
                            fontWeight: 500,
                            color: tokens.colors.infoPrimary || '#1E3A5F',
                          }}>
                            {tipo.descricao}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.875rem',
                            color: tokens.colors.textSecondary,
                          }}>
                            {tipo.total.toLocaleString('pt-PT')}
                          </span>
                          <span style={{
                            fontFamily: tokens.fonts.mono,
                            fontSize: '0.875rem',
                            fontWeight: 600,
                            color: tokens.colors.primary,
                            minWidth: '48px',
                            textAlign: 'right',
                          }}>
                            {formatDecimal(percentage, 0)}%
                          </span>
                        </div>
                      </div>
                      <div style={{
                        height: '8px',
                        backgroundColor: '#E8E4DA',
                        borderRadius: '4px',
                        overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${barWidth}%`,
                          backgroundColor: tokens.colors.primary,
                          borderRadius: '4px',
                          transition: 'width 0.6s cubic-bezier(0.22, 1, 0.36, 1)',
                        }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Insight callout */}
              {deputado.estatisticas.iniciativas_por_tipo[0] && (
                <aside style={{
                  display: 'flex',
                  gap: '10px',
                  marginTop: '20px',
                  padding: '12px',
                  backgroundColor: tokens.colors.bgSecondary,
                  border: `1px solid ${tokens.colors.border}`,
                  borderRadius: '4px',
                }}>
                  <TrendingUp style={{ flexShrink: 0, width: '16px', height: '16px', color: tokens.colors.verdeClaro || '#2D6A4F' }} />
                  <p style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.5, color: tokens.colors.textSecondary }}>
                    <strong style={{ color: tokens.colors.primary }}>{deputado.estatisticas.iniciativas_por_tipo[0].descricao}</strong> é o tipo de iniciativa que este deputado mais assina.
                  </p>
                </aside>
              )}
            </section>
          )}

          {/* INITIATIVES PER LEGISLATURE: signing and outcomes, then the group comparison */}
          {deputado.estatisticas.iniciativas_legislaturas?.length > 0 && (
            <section style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '6px',
              padding: '20px',
              marginBottom: '24px',
            }}>
              <header style={{ marginBottom: '16px', paddingBottom: '12px', borderBottom: `2px solid ${tokens.colors.primary}` }}>
                <h4 style={{
                  fontFamily: tokens.fonts.headline,
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: tokens.colors.primary,
                  margin: '0 0 4px 0',
                }}>Projetos por legislatura</h4>
                <p style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary, margin: 0 }}>
                  Projetos de lei, de resolução e de deliberação: como foram assinados e como terminaram
                </p>
              </header>
              <InitiativeRecordTable rows={deputado.estatisticas.iniciativas_legislaturas} />
              <div style={{ marginTop: '16px' }}>
                <GroupComparison
                  comparacao={deputado.estatisticas.comparacao?.iniciativas_subscricao_restrita}
                  label="Iniciativas com subscrição restrita, comparação com o grupo parlamentar"
                />
              </div>
            </section>
          )}

          {/* LEGISLATURE EVOLUTION */}
          {deputado.estatisticas.evolucao_legislaturas && deputado.estatisticas.evolucao_legislaturas.length > 1 && (
            <section style={{
              backgroundColor: tokens.colors.bgSecondary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '6px',
              padding: '20px',
              marginBottom: '24px',
            }}>
              <header style={{ marginBottom: '20px' }}>
                <h4 style={{
                  fontFamily: tokens.fonts.headline,
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: tokens.colors.textPrimary,
                  margin: '0 0 4px 0',
                }}>Evolução por Legislatura</h4>
                <p style={{ fontSize: '0.8125rem', color: tokens.colors.textSecondary, margin: 0 }}>
                  Atividade legislativa ao longo das legislaturas
                </p>
              </header>

              <div style={{
                display: 'flex',
                alignItems: 'flex-end',
                justifyContent: 'space-around',
                height: '160px',
                gap: '8px',
                paddingBottom: '32px',
                position: 'relative',
              }}>
                {(() => {
                  // Pixel heights out of a fixed track: a percentage height inside a column
                  // with no height of its own resolves to auto and every bar looked the same.
                  const EVOLUTION_TRACK_PX = 96;
                  const maxValue = Math.max(...deputado.estatisticas.evolucao_legislaturas.map(e => e.iniciativas + e.intervencoes));
                  // Reverse to show oldest first (left to right)
                  const sortedEvolution = [...deputado.estatisticas.evolucao_legislaturas].reverse();

                  return sortedEvolution.map((leg, index) => {
                    const total = leg.iniciativas + leg.intervencoes;
                    const barHeight = maxValue > 0 ? Math.max(Math.round((total / maxValue) * EVOLUTION_TRACK_PX), 4) : 4;
                    const isLast = index === sortedEvolution.length - 1;

                    return (
                      <div
                        key={leg.legislatura}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          flex: 1,
                          maxWidth: '80px',
                        }}
                      >
                        <div style={{
                          fontFamily: tokens.fonts.mono,
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: tokens.colors.textSecondary,
                          marginBottom: '8px',
                        }}>
                          {total}
                        </div>
                        <div style={{
                          width: '100%',
                          height: `${barHeight}px`,
                          backgroundColor: isLast ? tokens.colors.primary : tokens.colors.infoSecondary || '#3D5A80',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.5s ease',
                        }} />
                        <div style={{
                          position: 'absolute',
                          bottom: '8px',
                          fontFamily: tokens.fonts.mono,
                          fontSize: '0.75rem',
                          fontWeight: isLast ? 600 : 400,
                          color: isLast ? tokens.colors.primary : tokens.colors.textMuted,
                        }}>
                          {leg.legislatura}
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>

              {/* Trend indicator */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                paddingTop: '12px',
                borderTop: `1px solid ${tokens.colors.border}`,
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
              }}>
                {(() => {
                  const evolution = deputado.estatisticas.evolucao_legislaturas;
                  if (evolution.length < 2) return null;
                  const oldest = evolution[evolution.length - 1];
                  const newest = evolution[0];
                  const oldTotal = oldest.iniciativas + oldest.intervencoes;
                  const newTotal = newest.iniciativas + newest.intervencoes;
                  const isGrowing = newTotal >= oldTotal;

                  return (
                    <>
                      {isGrowing ? (
                        <TrendingUp style={{ width: '16px', height: '16px', color: tokens.colors.success }} />
                      ) : (
                        <TrendingDown style={{ width: '16px', height: '16px', color: tokens.colors.warning }} />
                      )}
                      <span>
                        Atividade {isGrowing ? 'crescente' : 'decrescente'} ao longo das legislaturas
                      </span>
                    </>
                  );
                })()}
              </div>
            </section>
          )}

          {/* Methodological Note */}
          <aside style={{
            display: 'flex',
            gap: '12px',
            padding: '16px',
            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
            border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            borderRadius: '4px',
            fontSize: '0.8125rem',
            color: tokens.colors.textSecondary,
          }}>
            <Info style={{
              flexShrink: 0,
              width: '18px',
              height: '18px',
              color: tokens.colors.ouroConstitucional || '#C9A227',
              marginTop: '2px',
            }} />
            <div>
              <strong style={{ color: tokens.colors.primary }}>Nota metodológica:</strong>{' '}
              Os dados apresentados são baseados em registos oficiais da Assembleia da República.
            </div>
          </aside>
        </div>

        {/* Biographical Dossier - Accordion-style biographical information */}
        <BiographicalDossier deputado={deputado} />

        {/* Tabs de Atividade - Editorial-style section navigation */}
        <section style={{
          backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
          border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
          borderRadius: '4px',
          marginTop: '24px',
          overflow: 'hidden',
        }}>
          {/* Section Header */}
          <header style={{
            padding: '16px 24px',
            borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            backgroundColor: 'rgba(255,255,255,0.5)',
          }}>
            <h3 style={{
              fontFamily: tokens.fonts.headline,
              fontSize: '1.125rem',
              fontWeight: 600,
              color: tokens.colors.textPrimary,
              margin: 0,
            }}>
              Atividade Parlamentar
            </h3>
            <p style={{
              fontSize: '0.8125rem',
              color: tokens.colors.textSecondary,
              marginTop: '4px',
            }}>
              Acompanhe o trabalho legislativo do deputado
            </p>
          </header>

          {/* Editorial Tab Navigation */}
          <nav style={{
            display: 'flex',
            gap: '0',
            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
            borderBottom: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
            overflowX: 'auto',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
          }}>
            {tabs.map((tab, index) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '14px 20px',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    fontWeight: isActive ? 600 : 500,
                    letterSpacing: '0.01em',
                    color: isActive ? tokens.colors.primary : tokens.colors.textSecondary,
                    backgroundColor: isActive ? 'white' : 'transparent',
                    border: 'none',
                    borderBottom: isActive ? `2px solid ${tokens.colors.primary}` : '2px solid transparent',
                    borderRight: index < tabs.length - 1 ? `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}` : 'none',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s ease',
                    position: 'relative',
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.6)';
                      e.currentTarget.style.color = tokens.colors.textPrimary;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.backgroundColor = 'transparent';
                      e.currentTarget.style.color = tokens.colors.textSecondary;
                    }
                  }}
                >
                  <span style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '28px',
                    height: '28px',
                    borderRadius: '4px',
                    backgroundColor: isActive ? `${tokens.colors.primary}12` : tokens.colors.bgTertiary,
                    transition: 'background-color 0.2s ease',
                  }}>
                    <Icon style={{
                      width: '15px',
                      height: '15px',
                      color: isActive ? tokens.colors.primary : tokens.colors.textMuted,
                    }} />
                  </span>
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Tab Content - White background for readability */}
          <div style={{
            padding: '28px',
            backgroundColor: 'white',
            minHeight: '400px',
          }}>

            {activeTab === 'intervencoes' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Intervenções Parlamentares
                    </h3>
                    {totalInterventions > 0 && (
                      <p style={{
                        fontSize: '0.8125rem',
                        color: tokens.colors.textMuted,
                        marginTop: '6px',
                        fontFamily: tokens.fonts.body,
                      }}>
                        {interventionTypeFilter
                          ? `${atividades?.intervencoes?.length || 0} de ${totalInterventions} intervenções (filtrado por "${interventionTypeFilter}")`
                          : `${totalInterventions} intervenções nesta legislatura`
                        }
                      </p>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {atividades && atividades.intervencoes.length > 0 && (
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <select
                          value={interventionTypeFilter}
                          onChange={(e) => {
                            const newType = e.target.value;
                            setInterventionTypeFilter(newType);
                            setCurrentPage(1);
                            updateInterventionParams({ tipo_intervencao: newType, page: 1 });
                          }}
                          style={{
                            border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
                            borderRadius: '4px',
                            padding: '8px 12px',
                            fontSize: '0.8125rem',
                            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
                            color: tokens.colors.textPrimary,
                            fontFamily: tokens.fonts.body,
                            cursor: 'pointer',
                            outline: 'none',
                          }}
                        >
                          <option value="">Todos os tipos</option>
                          <option value="Interpelação">Interpelação à mesa</option>
                          <option value="Pedido">Pedido de esclarecimento</option>
                          <option value="Declaração">Declaração política</option>
                          <option value="Pergunta">Pergunta</option>
                        </select>
                        <select
                          value={interventionSort}
                          onChange={(e) => {
                            const newSort = e.target.value;
                            setInterventionSort(newSort);
                            updateInterventionParams({ ordenacao_intervencoes: newSort });
                          }}
                          style={{
                            border: `1px solid ${tokens.colors.borderWarm || '#E8E4DA'}`,
                            borderRadius: '4px',
                            padding: '8px 12px',
                            fontSize: '0.8125rem',
                            backgroundColor: tokens.colors.bgWarm || '#F8F6F0',
                            color: tokens.colors.textPrimary,
                            fontFamily: tokens.fonts.body,
                            cursor: 'pointer',
                            outline: 'none',
                          }}
                        >
                          <option value="newest">Mais recentes</option>
                          <option value="oldest">Mais antigas</option>
                          <option value="type">Por tipo</option>
                        </select>
                      </div>
                    )}
                    <LegislatureDropdown
                      selectedLegislature={selectedLegislature}
                      onLegislatureChange={setSelectedLegislature}
                      deputyCadId={cadId}
                      size="sm"
                    />
                  </div>
                </div>

                {atividades?.nota_intervencoes && (
                  <div style={{
                    display: 'flex',
                    gap: '10px',
                    padding: '12px 14px',
                    marginBottom: '20px',
                    backgroundColor: tokens.colors.warningBg,
                    border: '1px solid #FDE68A',
                    borderRadius: '4px',
                    fontSize: '0.8125rem',
                    color: tokens.colors.textSecondary,
                    fontFamily: tokens.fonts.body,
                  }}>
                    <Info style={{ flexShrink: 0, width: '16px', height: '16px', color: tokens.colors.warning, marginTop: '2px' }} />
                    <p style={{ margin: 0 }}>{atividades.nota_intervencoes}</p>
                  </div>
                )}

                {/* Activity Summary Bar */}
                {atividades && totalInterventions > 0 && (
                  <InterventionsSummaryBar
                    totalInterventions={totalInterventions}
                    comparison={atividades.comparacao_intervencoes}
                    videoCount={atividades.intervencoes?.filter(i => i.url_video)?.length || 0}
                    lastInterventionDate={atividades.intervencoes?.[0]?.data}
                    typeBreakdown={(() => {
                      const breakdown = {};
                      atividades.intervencoes?.forEach(i => {
                        const tipo = i.tipo || 'Outro';
                        breakdown[tipo] = (breakdown[tipo] || 0) + 1;
                      });
                      return breakdown;
                    })()}
                  />
                )}

                {/* Phase 2: Timeline and Achievements Section */}
                {atividades && atividades.intervencoes?.length > 0 && (
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                    gap: '16px',
                    marginBottom: '24px',
                  }}>
                    {/* Activity Timeline Sparkline */}
                    <div style={{
                      backgroundColor: tokens.colors.bgSecondary,
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      padding: '16px 20px',
                    }}>
                      <h4 style={{
                        margin: '0 0 12px 0',
                        fontFamily: tokens.fonts.body,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.textMuted,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>
                        Atividade ao longo do tempo
                      </h4>
                      <TimelineSparkline
                        data={(() => {
                          // Group interventions by month
                          const monthlyData = {};
                          atividades.intervencoes?.forEach(i => {
                            if (i.data) {
                              const monthKey = i.data.substring(0, 7);
                              monthlyData[monthKey] = (monthlyData[monthKey] || 0) + 1;
                            }
                          });
                          return Object.entries(monthlyData)
                            .sort(([a], [b]) => a.localeCompare(b))
                            .slice(-12) // Last 12 months
                            .map(([date, value]) => ({ date, value }));
                        })()}
                        width={280}
                        height={50}
                        color={tokens.colors.primary}
                        showTrend={true}
                      />
                    </div>

                    {/* Achievement Badges */}
                    <div style={{
                      backgroundColor: tokens.colors.bgSecondary,
                      border: `1px solid ${tokens.colors.border}`,
                      borderRadius: '4px',
                      padding: '16px 20px',
                    }}>
                      <h4 style={{
                        margin: '0 0 12px 0',
                        fontFamily: tokens.fonts.body,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.textMuted,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                      }}>
                        Reconhecimentos
                      </h4>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {atividades.intervencoes?.filter(i => i.tipo?.includes('Pergunta')).length >= 20 && (
                          <AchievementBadge type="topQuestioner" size="small" showDescription={false} />
                        )}
                        {atividades.intervencoes?.length >= 50 && (
                          <AchievementBadge type="debateParticipant" size="small" showDescription={false} />
                        )}
                        {atividades.intervencoes?.length < 5 && atividades.intervencoes?.length > 0 && (
                          <RedFlagIndicator
                            type="lowActivity"
                            value={atividades.intervencoes?.length}
                            showDetails={false}
                          />
                        )}
                        {atividades.intervencoes?.filter(i => i.tipo?.includes('Pergunta')).length === 0 && atividades.intervencoes?.length >= 10 && (
                          <RedFlagIndicator
                            type="noQuestions"
                            value={6}
                            showDetails={false}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {atividades && atividades.intervencoes.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    {(() => {
                      const interventions = atividades.intervencoes || [];

                      // Helper functions for inline styles
                      const getTipoStyle = (tipo) => {
                        if (tipo?.includes('Interpelação')) return { backgroundColor: colorSchemes.blue.bg, color: colorSchemes.blue.text, borderColor: colorSchemes.blue.border };
                        if (tipo?.includes('Declaração')) return { backgroundColor: colorSchemes.green.bg, color: colorSchemes.green.text, borderColor: colorSchemes.green.border };
                        if (tipo?.includes('Pedido')) return { backgroundColor: colorSchemes.orange.bg, color: colorSchemes.orange.text, borderColor: colorSchemes.orange.border };
                        if (tipo?.includes('Pergunta')) return { backgroundColor: colorSchemes.purple.bg, color: colorSchemes.purple.text, borderColor: colorSchemes.purple.border };
                        return { backgroundColor: tokens.colors.bgPrimary, color: tokens.colors.textSecondary, borderColor: tokens.colors.border };
                      };

                      const getQualidadeStyle = (qualidade) => {
                        if (qualidade === 'Deputado') return { backgroundColor: colorSchemes.blue.bg, color: colorSchemes.blue.text, borderColor: colorSchemes.blue.border };
                        if (qualidade === 'P.A.R.') return { backgroundColor: colorSchemes.purple.bg, color: colorSchemes.purple.text, borderColor: colorSchemes.purple.border };
                        return { backgroundColor: tokens.colors.bgPrimary, color: tokens.colors.textSecondary, borderColor: tokens.colors.border };
                      };

                      return interventions.map((intervencao, index) => (
                        <div key={index} style={{
                          border: `1px solid ${tokens.colors.border}`,
                          borderRadius: '4px',
                          padding: '24px',
                          backgroundColor: tokens.colors.bgSecondary,
                          transition: 'border-color 0.15s ease',
                        }}>
                          {/* Context badges */}
                          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
                            <span style={{
                              ...getTipoStyle(intervencao.tipo),
                              padding: '4px 12px',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: 500,
                              border: `1px solid ${getTipoStyle(intervencao.tipo).borderColor}`,
                            }}>
                              {intervencao.tipo}
                            </span>
                            {intervencao.qualidade && (
                              <span style={{
                                ...getQualidadeStyle(intervencao.qualidade),
                                padding: '4px 8px',
                                borderRadius: '4px',
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                border: `1px solid ${getQualidadeStyle(intervencao.qualidade).borderColor}`,
                              }}>
                                {intervencao.qualidade}
                              </span>
                            )}
                            {intervencao.sessao_numero && (
                              <span style={{
                                padding: '4px 8px',
                                backgroundColor: tokens.colors.bgPrimary,
                                color: tokens.colors.textSecondary,
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                borderRadius: '4px',
                                border: `1px solid ${tokens.colors.border}`,
                              }}>
                                Sessão {intervencao.sessao_numero}
                              </span>
                            )}
                          </div>

                          <div style={{ display: 'flex', gap: '16px' }}>
                            {/* Video Thumbnail */}
                            {intervencao.url_video && intervencao.thumbnail_url ? (
                              <div style={{ position: 'relative', flexShrink: 0 }}>
                                <div
                                  style={{
                                    width: '144px',
                                    height: '88px',
                                    borderRadius: '4px',
                                    overflow: 'hidden',
                                    backgroundColor: tokens.colors.bgPrimary,
                                    position: 'relative',
                                    cursor: 'pointer',
                                  }}
                                  onClick={() => window.open(intervencao.url_video, '_blank')}
                                >
                                  <img
                                    src={intervencao.thumbnail_url}
                                    alt="Video thumbnail"
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    onError={(e) => {
                                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTQ0IiBoZWlnaHQ9IjkwIiB2aWV3Qm94PSIwIDAgMTQ0IDkwIiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgo8cmVjdCB3aWR0aD0iMTQ0IiBoZWlnaHQ9IjkwIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik02MCA0NUw4NCA1N0w2MCA2OVY0NVoiIGZpbGw9IiM5Q0EzQUYiLz4KPC9zdmc+';
                                    }}
                                  />
                                  {intervencao.duracao_video && (
                                    <div style={{
                                      position: 'absolute',
                                      bottom: '4px',
                                      right: '4px',
                                      backgroundColor: 'rgba(0,0,0,0.8)',
                                      color: '#FFFFFF',
                                      fontSize: '0.75rem',
                                      padding: '2px 6px',
                                      borderRadius: '2px',
                                      display: 'flex',
                                      alignItems: 'center',
                                    }}>
                                      <Clock style={{ width: '12px', height: '12px', marginRight: '4px' }} />
                                      {intervencao.duracao_video}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : intervencao.url_video ? (
                              <div style={{ position: 'relative', flexShrink: 0 }}>
                                <div
                                  style={{
                                    width: '144px',
                                    height: '88px',
                                    borderRadius: '4px',
                                    overflow: 'hidden',
                                    backgroundColor: colorSchemes.blue.bg,
                                    border: `1px solid ${colorSchemes.blue.border}`,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                  }}
                                  onClick={() => window.open(intervencao.url_video, '_blank')}
                                >
                                  <Play style={{ width: '32px', height: '32px', color: colorSchemes.blue.primary }} />
                                </div>
                              </div>
                            ) : null}

                            {/* Content */}
                            <div style={{ flex: 1, minWidth: 0 }}>
                              {/* Header with date and action buttons */}
                              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                                  <div style={{ display: 'flex', alignItems: 'center' }}>
                                    <Calendar style={{ width: '16px', height: '16px', marginRight: '4px' }} />
                                    {new Date(intervencao.data).toLocaleDateString('pt-PT')}
                                  </div>
                                </div>

                                {/* Action Buttons */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '16px', flexShrink: 0 }}>
                                  {intervencao.url_video && (
                                    <button
                                      onClick={() => window.open(intervencao.url_video, '_blank')}
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        padding: '6px 12px',
                                        border: `1px solid ${colorSchemes.blue.border}`,
                                        fontSize: '0.875rem',
                                        fontWeight: 500,
                                        borderRadius: '4px',
                                        color: colorSchemes.blue.text,
                                        backgroundColor: colorSchemes.blue.bg,
                                        cursor: 'pointer',
                                        whiteSpace: 'nowrap',
                                      }}
                                    >
                                      <Play className="h-4 w-4 mr-1" />
                                      Ver Vídeo
                                    </button>
                                  )}
                                  {intervencao.publicacao?.url_diario && (
                                    <button
                                      onClick={() => window.open(intervencao.publicacao.url_diario, '_blank')}
                                      style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        padding: '6px 12px',
                                        border: `1px solid ${colorSchemes.orange.border}`,
                                        fontSize: '0.875rem',
                                        fontWeight: 500,
                                        borderRadius: '4px',
                                        color: colorSchemes.orange.text,
                                        backgroundColor: colorSchemes.orange.bg,
                                        cursor: 'pointer',
                                        whiteSpace: 'nowrap',
                                      }}
                                    >
                                      <ExternalLink style={{ width: '16px', height: '16px', marginRight: '4px' }} />
                                      {intervencao.publicacao.pub_numero ? `DR ${intervencao.publicacao.pub_numero}` : 'Diário'}
                                    </button>
                                  )}
                                </div>
                              </div>

                              {/* Subject/Title */}
                              {intervencao.assunto && (
                                <div style={{ marginBottom: '12px' }}>
                                  <h4 style={{ color: tokens.colors.textPrimary, fontWeight: 500, fontSize: '0.875rem', lineHeight: 1.4 }}>
                                    {intervencao.assunto}
                                  </h4>
                                </div>
                              )}

                              {/* Summary */}
                              {intervencao.resumo && (
                                <p style={{ color: tokens.colors.textSecondary, fontSize: '0.875rem', lineHeight: 1.6, marginBottom: '12px' }}>
                                  {intervencao.resumo}
                                </p>
                              )}

                              {/* Additional Info */}
                              {(intervencao.sumario || intervencao.fase_sessao) && (
                                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${tokens.colors.border}` }}>
                                  {intervencao.sumario && (
                                    <p style={{ fontSize: '0.875rem', color: tokens.colors.textSecondary, marginBottom: '8px' }}>
                                      <span style={{ fontWeight: 500, color: tokens.colors.textPrimary }}>Sumário:</span> {intervencao.sumario}
                                    </p>
                                  )}
                                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                    {intervencao.fase_sessao && (
                                      <span style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        padding: '4px 8px',
                                        borderRadius: '4px',
                                        fontSize: '0.75rem',
                                        fontWeight: 500,
                                        backgroundColor: tokens.colors.bgPrimary,
                                        color: tokens.colors.textSecondary,
                                        border: `1px solid ${tokens.colors.border}`,
                                      }}>
                                        {intervencao.fase_sessao}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Publication metadata */}
                              {intervencao.publicacao && (
                                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${tokens.colors.border}` }}>
                                  <div style={{ display: 'flex', gap: '16px', fontSize: '0.75rem', color: tokens.colors.textMuted }}>
                                    {intervencao.publicacao.pub_tipo && (
                                      <span style={{ display: 'flex', alignItems: 'center' }}>
                                        📰 {intervencao.publicacao.pub_tipo}
                                      </span>
                                    )}
                                    {intervencao.publicacao.pub_data && (
                                      <span style={{ display: 'flex', alignItems: 'center' }}>
                                        📅 Pub: {new Date(intervencao.publicacao.pub_data).toLocaleDateString('pt-PT')}
                                      </span>
                                    )}
                                    {intervencao.publicacao.paginas && (
                                      <span style={{ display: 'flex', alignItems: 'center' }}>
                                        📄 Pág. {intervencao.publicacao.paginas}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ));
                    })()}

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                      <div style={{
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        gap: '8px',
                        marginTop: '32px',
                        paddingTop: '24px',
                        borderTop: `1px solid ${tokens.colors.border}`,
                      }}>
                        <button
                          onClick={() => {
                            if (currentPage > 1) {
                              const newPage = currentPage - 1;
                              setCurrentPage(newPage);
                              updateInterventionParams({ page: newPage });
                            }
                          }}
                          disabled={currentPage <= 1}
                          style={{
                            padding: '8px 12px',
                            fontSize: '0.875rem',
                            backgroundColor: tokens.colors.bgSecondary,
                            border: `1px solid ${tokens.colors.border}`,
                            borderRadius: '4px',
                            cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
                            opacity: currentPage <= 1 ? 0.5 : 1,
                            color: tokens.colors.textPrimary,
                          }}
                        >
                          Anterior
                        </button>

                        <span style={{ padding: '8px 16px', fontSize: '0.875rem', color: tokens.colors.textSecondary, fontFamily: tokens.fonts.mono }}>
                          Página {currentPage} de {totalPages}
                        </span>

                        <button
                          onClick={() => {
                            if (currentPage < totalPages) {
                              const newPage = currentPage + 1;
                              setCurrentPage(newPage);
                              updateInterventionParams({ page: newPage });
                            }
                          }}
                          disabled={currentPage >= totalPages}
                          style={{
                            padding: '8px 12px',
                            fontSize: '0.875rem',
                            backgroundColor: tokens.colors.bgSecondary,
                            border: `1px solid ${tokens.colors.border}`,
                            borderRadius: '4px',
                            cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
                            opacity: currentPage >= totalPages ? 0.5 : 1,
                            color: tokens.colors.textPrimary,
                          }}
                        >
                          Próxima
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '48px 0' }}>
                    <div style={{
                      margin: '0 auto',
                      width: '64px',
                      height: '64px',
                      backgroundColor: tokens.colors.bgPrimary,
                      borderRadius: '50%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginBottom: '16px',
                    }}>
                      <MessageSquare style={{ width: '32px', height: '32px', color: tokens.colors.textMuted }} />
                    </div>
                    <p style={{ color: tokens.colors.textMuted, fontSize: '1.125rem', fontWeight: 500, marginBottom: '8px' }}>Nenhuma intervenção registada</p>
                    <p style={{ fontSize: '0.875rem', color: tokens.colors.textMuted }}>
                      Os dados de intervenções serão carregados em futuras atualizações
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'iniciativas' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Iniciativas Legislativas
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Projetos de lei e resoluções apresentados pelo deputado
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {atividades && atividades.iniciativas && atividades.iniciativas.length > 0 && (
                      <div style={{
                        fontFamily: tokens.fonts.mono,
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: tokens.colors.primary,
                        backgroundColor: `${tokens.colors.primary}10`,
                        padding: '6px 12px',
                        borderRadius: '4px',
                        border: `1px solid ${tokens.colors.primary}25`,
                      }}>
                        {atividades.iniciativas.length} iniciativas
                      </div>
                    )}
                    <LegislatureDropdown
                      selectedLegislature={selectedLegislature}
                      onLegislatureChange={setSelectedLegislature}
                      deputyCadId={cadId}
                      size="sm"
                    />
                  </div>
                </div>
                
                {atividades && atividades.iniciativas && atividades.iniciativas.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {/* Outcomes Summary Panel */}
                    {(() => {
                      const initiatives = atividades.iniciativas;
                      const approved = initiatives.filter(i => i.estado?.toLowerCase() === 'aprovado').length;
                      const rejected = initiatives.filter(i => i.estado?.toLowerCase() === 'rejeitado').length;
                      const inProgress = initiatives.filter(i =>
                        i.estado?.toLowerCase() !== 'aprovado' &&
                        i.estado?.toLowerCase() !== 'rejeitado' &&
                        i.estado?.toLowerCase() !== 'caducado' &&
                        i.estado?.toLowerCase() !== 'retirado'
                      ).length;
                      const expired = initiatives.filter(i =>
                        i.estado?.toLowerCase() === 'caducado' ||
                        i.estado?.toLowerCase() === 'retirado'
                      ).length;

                      return (
                        <InitiativeOutcomesSummary
                          approved={approved}
                          rejected={rejected}
                          inProgress={inProgress}
                          expired={expired}
                          total={initiatives.length}
                        />
                      );
                    })()}

                    {/* How the projetos of this legislature were signed */}
                    {atividades.assinatura && (
                      <div style={{
                        backgroundColor: tokens.colors.bgSecondary,
                        border: `1px solid ${tokens.colors.border}`,
                        borderRadius: '4px',
                        padding: '16px 20px',
                      }}>
                        <h4 style={{
                          margin: '0 0 12px 0',
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          fontWeight: 600,
                          color: tokens.colors.textPrimary,
                        }}>
                          Como assina
                        </h4>
                        <SigningCounts assinatura={atividades.assinatura} />
                        {atividades.aprovacao?.length > 0 && (
                          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${tokens.colors.border}` }}>
                            <ApprovalLines aprovacao={atividades.aprovacao} aberta={!!atividades.nota_intervencoes} />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Phase 2: Enhanced Analytics Grid */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                      gap: '16px',
                      marginTop: '16px',
                    }}>
                      {/* Policy Specialization Chart */}
                      {(() => {
                        const initiatives = atividades.iniciativas || [];
                        // Group by type for now (would ideally use policy area classification)
                        const typeLabels = {
                          'J': 'Projeto de Lei',
                          'R': 'Projeto de Resolução',
                          'P': 'Proposta de Lei',
                          'D': 'Projeto de Deliberação',
                        };
                        const byType = {};
                        initiatives.forEach(i => {
                          const area = typeLabels[i.tipo] || i.tipo || 'Outro';
                          byType[area] = (byType[area] || 0) + 1;
                        });
                        const data = Object.entries(byType).map(([area, count]) => ({ area, count }));

                        if (data.length === 0) return null;

                        return (
                          <div style={{
                            backgroundColor: tokens.colors.bgSecondary,
                            border: `1px solid ${tokens.colors.border}`,
                            borderRadius: '4px',
                            padding: '16px 20px',
                          }}>
                            <h4 style={{
                              margin: '0 0 12px 0',
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              color: tokens.colors.textMuted,
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                            }}>
                              Distribuição por tipo
                            </h4>
                            <PolicySpecializationChart
                              data={data}
                              maxDisplay={4}
                              showSpecialization={false}
                            />
                          </div>
                        );
                      })()}
                    </div>

                    {/* Initiative Cards */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {atividades.iniciativas.map((iniciativa, index) => {
                      // Helper function to get type styling - returns style object
                      const getTypeStyle = (tipo) => {
                        switch (tipo) {
                          case 'J':
                            return { backgroundColor: colorSchemes.blue.bg, color: colorSchemes.blue.text, borderColor: colorSchemes.blue.border };
                          case 'R':
                            return { backgroundColor: colorSchemes.green.bg, color: colorSchemes.green.text, borderColor: colorSchemes.green.border };
                          case 'P':
                            return { backgroundColor: colorSchemes.purple.bg, color: colorSchemes.purple.text, borderColor: colorSchemes.purple.border };
                          case 'D':
                            return { backgroundColor: colorSchemes.orange.bg, color: colorSchemes.orange.text, borderColor: colorSchemes.orange.border };
                          default:
                            return { backgroundColor: '#F3F4F6', color: tokens.colors.textSecondary, borderColor: tokens.colors.border };
                        }
                      };

                      // Helper function to get status styling - returns style object
                      const getStatusStyle = (estado) => {
                        if (!estado) return null;
                        switch (estado?.toLowerCase()) {
                          case 'aprovado':
                            return { backgroundColor: tokens.colors.successBg, color: tokens.colors.success, borderColor: '#BBF7D0' };
                          case 'rejeitado':
                            return { backgroundColor: tokens.colors.dangerBg, color: tokens.colors.danger, borderColor: '#FECACA' };
                          case 'em votação':
                            return { backgroundColor: tokens.colors.warningBg, color: tokens.colors.warning, borderColor: '#FDE68A' };
                          case 'retirado':
                            return { backgroundColor: '#F9FAFB', color: tokens.colors.textSecondary, borderColor: tokens.colors.border };
                          case 'caducado':
                            return { backgroundColor: '#FEF3C7', color: '#92400E', borderColor: '#FCD34D' };
                          case 'em tramitação':
                            return { backgroundColor: tokens.colors.infoBg, color: tokens.colors.info, borderColor: '#BFDBFE' };
                          default:
                            return { backgroundColor: tokens.colors.infoBg, color: tokens.colors.info, borderColor: '#BFDBFE' };
                        }
                      };

                      // Helper function to get progress bar color
                      const getProgressColor = (estado) => {
                        if (!estado) return tokens.colors.blue;
                        switch (estado?.toLowerCase()) {
                          case 'aprovado': return tokens.colors.success;
                          case 'rejeitado': return tokens.colors.danger;
                          case 'em votação': return '#F59E0B';
                          case 'caducado': return '#92400E';
                          case 'retirado': return tokens.colors.textSecondary;
                          default: return tokens.colors.blue;
                        }
                      };

                      // Helper function to get progress bar width
                      const getProgressWidth = (estado) => {
                        if (!estado) return '50%';
                        switch (estado?.toLowerCase()) {
                          case 'aprovado': return '100%';
                          case 'rejeitado': return '100%';
                          case 'caducado': return '100%';
                          case 'retirado': return '100%';
                          case 'em votação': return '75%';
                          case 'em tramitação': return '50%';
                          default: return '50%';
                        }
                      };

                      const typeStyles = getTypeStyle(iniciativa.tipo);
                      const statusStyles = getStatusStyle(iniciativa.estado);

                      return (
                        <div key={index} style={{
                          backgroundColor: tokens.colors.bgSecondary,
                          border: `1px solid ${tokens.colors.border}`,
                          borderRadius: '4px',
                          padding: '1.5rem',
                          transition: 'border-color 0.2s ease'
                        }}>
                          {/* Header with type and date */}
                          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                              <span style={{
                                ...typeStyles,
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.75rem',
                                fontWeight: '600',
                                padding: '0.375rem 0.75rem',
                                borderRadius: '2px',
                                border: `1px solid ${typeStyles.borderColor}`,
                                textTransform: 'uppercase',
                                letterSpacing: '0.025em'
                              }}>
                                {iniciativa.tipo_descricao || iniciativa.tipo}
                              </span>
                              {iniciativa.estado && statusStyles && (
                                <span style={{
                                  ...statusStyles,
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.75rem',
                                  fontWeight: '500',
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '2px',
                                  border: `1px solid ${statusStyles.borderColor}`
                                }}>
                                  {iniciativa.estado}
                                </span>
                              )}
                            </div>
                            <div style={{
                              fontFamily: tokens.fonts.mono,
                              fontSize: '0.75rem',
                              color: tokens.colors.textMuted,
                              display: 'flex',
                              alignItems: 'center',
                              flexShrink: 0,
                              marginLeft: '1rem'
                            }}>
                              <Calendar style={{ height: '14px', width: '14px', marginRight: '0.25rem' }} />
                              {new Date(iniciativa.data_apresentacao || iniciativa.data).toLocaleDateString('pt-PT')}
                            </div>
                          </div>

                          {/* Title */}
                          <h4 style={{
                            fontFamily: tokens.fonts.headline,
                            fontWeight: '600',
                            color: tokens.colors.textPrimary,
                            marginBottom: '0.75rem',
                            fontSize: '1.125rem',
                            lineHeight: '1.4'
                          }}>
                            {iniciativa.titulo}
                          </h4>

                          {/* Details */}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                              <div style={{
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.875rem',
                                color: tokens.colors.textSecondary,
                                display: 'flex',
                                alignItems: 'center'
                              }}>
                                <FileText style={{ height: '16px', width: '16px', marginRight: '0.25rem' }} />
                                <span>Tipo: {iniciativa.tipo}</span>
                              </div>
                              {iniciativa.subscricao && (
                                <div style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.875rem',
                                  color: tokens.colors.textSecondary,
                                }}>
                                  {iniciativa.subscricao === 'grupo_parlamentar'
                                    ? 'Do grupo parlamentar'
                                    : iniciativa.subscricao === 'outros_grupos'
                                      ? 'Com outros grupos'
                                      : `Subscrição restrita: ${iniciativa.subscritores} ${iniciativa.subscritores === 1 ? 'deputado' : 'deputados'}`}
                                </div>
                              )}
                              {iniciativa.aprovada_parcialmente && (
                                <div style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.875rem',
                                  color: tokens.colors.textSecondary,
                                }}>
                                  Aprovada só em parte (votação ponto a ponto)
                                </div>
                              )}
                              {iniciativa.resultado && (
                                <div style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.875rem',
                                  color: tokens.colors.textSecondary,
                                  display: 'flex',
                                  alignItems: 'center'
                                }}>
                                  <Activity style={{ height: '16px', width: '16px', marginRight: '0.25rem' }} />
                                  <span>Resultado: {iniciativa.resultado}</span>
                                </div>
                              )}
                            </div>

                            {/* Action button */}
                            <button
                              onClick={() => toggleInitiativeDetails(index)}
                              style={{
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.875rem',
                                fontWeight: '600',
                                color: tokens.colors.primary,
                                backgroundColor: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '2px',
                                transition: 'background-color 0.2s ease'
                              }}
                            >
                              {expandedInitiatives.has(index) ? 'Ocultar detalhes' : 'Ver detalhes'}
                              <svg
                                style={{
                                  height: '16px',
                                  width: '16px',
                                  marginLeft: '0.25rem',
                                  transform: expandedInitiatives.has(index) ? 'rotate(90deg)' : 'none',
                                  transition: 'transform 0.2s ease'
                                }}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                              </svg>
                            </button>
                          </div>

                          {/* Progress indicator based on status */}
                          {iniciativa.estado && (
                            <div style={{
                              marginTop: '1rem',
                              paddingTop: '1rem',
                              borderTop: `1px solid ${tokens.colors.border}`
                            }}>
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                fontFamily: tokens.fonts.mono,
                                fontSize: '0.75rem',
                                color: tokens.colors.textMuted
                              }}>
                                <div style={{
                                  flex: 1,
                                  backgroundColor: '#E5E7EB',
                                  borderRadius: '2px',
                                  height: '4px',
                                  marginRight: '0.75rem',
                                  overflow: 'hidden'
                                }}>
                                  <div style={{
                                    height: '100%',
                                    borderRadius: '2px',
                                    backgroundColor: getProgressColor(iniciativa.estado),
                                    width: getProgressWidth(iniciativa.estado),
                                    transition: 'width 0.3s ease'
                                  }} />
                                </div>
                                <span style={{
                                  fontSize: '0.75rem',
                                  fontWeight: '500',
                                  color: tokens.colors.textSecondary
                                }}>
                                  {iniciativa.estado || 'Em análise'}
                                </span>
                              </div>
                            </div>
                          )}

                          {/* Expandable Details Section */}
                          {expandedInitiatives.has(index) && (
                            <div style={{
                              marginTop: '1rem',
                              paddingTop: '1rem',
                              borderTop: `1px solid ${tokens.colors.border}`
                            }}>
                              <h5 style={{
                                fontFamily: tokens.fonts.headline,
                                fontWeight: '600',
                                color: tokens.colors.textPrimary,
                                marginBottom: '0.75rem',
                                fontSize: '0.9375rem'
                              }}>Detalhes da Iniciativa</h5>

                              <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                gap: '1rem',
                                fontSize: '0.875rem'
                              }}>
                                {/* Left Column */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                  <div>
                                    <span style={{
                                      fontFamily: tokens.fonts.body,
                                      fontWeight: '600',
                                      color: tokens.colors.textSecondary,
                                      fontSize: '0.75rem',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em'
                                    }}>Tipo:</span>
                                    <p style={{
                                      fontFamily: tokens.fonts.body,
                                      color: tokens.colors.textPrimary,
                                      marginTop: '0.25rem'
                                    }}>
                                      {iniciativa.tipo_descricao} ({iniciativa.tipo})
                                    </p>
                                  </div>

                                  <div>
                                    <span style={{
                                      fontFamily: tokens.fonts.body,
                                      fontWeight: '600',
                                      color: tokens.colors.textSecondary,
                                      fontSize: '0.75rem',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em'
                                    }}>Data de Apresentação:</span>
                                    <p style={{
                                      fontFamily: tokens.fonts.body,
                                      color: tokens.colors.textPrimary,
                                      marginTop: '0.25rem'
                                    }}>
                                      {new Date(iniciativa.data_apresentacao || iniciativa.data).toLocaleDateString('pt-PT', {
                                        weekday: 'long',
                                        year: 'numeric',
                                        month: 'long',
                                        day: 'numeric'
                                      })}
                                    </p>
                                  </div>

                                  {iniciativa.estado && (
                                    <div>
                                      <span style={{
                                        fontFamily: tokens.fonts.body,
                                        fontWeight: '600',
                                        color: tokens.colors.textSecondary,
                                        fontSize: '0.75rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em'
                                      }}>Estado Atual:</span>
                                      <p style={{
                                        fontFamily: tokens.fonts.body,
                                        color: tokens.colors.textPrimary,
                                        marginTop: '0.25rem'
                                      }}>{iniciativa.estado}</p>
                                    </div>
                                  )}
                                </div>

                                {/* Right Column */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                  {iniciativa.resultado && (
                                    <div>
                                      <span style={{
                                        fontFamily: tokens.fonts.body,
                                        fontWeight: '600',
                                        color: tokens.colors.textSecondary,
                                        fontSize: '0.75rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em'
                                      }}>Resultado:</span>
                                      <p style={{
                                        fontFamily: tokens.fonts.body,
                                        color: tokens.colors.textPrimary,
                                        marginTop: '0.25rem'
                                      }}>{iniciativa.resultado}</p>
                                    </div>
                                  )}

                                  <div>
                                    <span style={{
                                      fontFamily: tokens.fonts.body,
                                      fontWeight: '600',
                                      color: tokens.colors.textSecondary,
                                      fontSize: '0.75rem',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em'
                                    }}>Categoria:</span>
                                    <p style={{
                                      fontFamily: tokens.fonts.body,
                                      color: tokens.colors.textPrimary,
                                      marginTop: '0.25rem'
                                    }}>
                                      {iniciativa.tipo === 'J' ? 'Projeto de Lei' :
                                       iniciativa.tipo === 'R' ? 'Projeto de Resolução' :
                                       iniciativa.tipo === 'P' ? 'Proposta' :
                                       iniciativa.tipo === 'D' ? 'Decreto' :
                                       'Iniciativa Legislativa'}
                                    </p>
                                  </div>

                                  <div>
                                    <span style={{
                                      fontFamily: tokens.fonts.body,
                                      fontWeight: '600',
                                      color: tokens.colors.textSecondary,
                                      fontSize: '0.75rem',
                                      textTransform: 'uppercase',
                                      letterSpacing: '0.05em'
                                    }}>Estado:</span>
                                    <p style={{
                                      fontFamily: tokens.fonts.body,
                                      color: tokens.colors.textPrimary,
                                      marginTop: '0.25rem'
                                    }}>
                                      {iniciativa.estado ?
                                        `Em fase: ${iniciativa.estado}` :
                                        'Em análise nas comissões competentes'
                                      }
                                    </p>
                                  </div>
                                </div>
                              </div>

                              {/* Full Title Section */}
                              <div style={{
                                marginTop: '1rem',
                                paddingTop: '1rem',
                                borderTop: `1px solid ${tokens.colors.border}`
                              }}>
                                <span style={{
                                  fontFamily: tokens.fonts.body,
                                  fontWeight: '600',
                                  color: tokens.colors.textSecondary,
                                  fontSize: '0.75rem',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.05em'
                                }}>Título Completo:</span>
                                <p style={{
                                  fontFamily: tokens.fonts.body,
                                  color: tokens.colors.textSecondary,
                                  marginTop: '0.5rem',
                                  lineHeight: '1.6'
                                }}>
                                  {iniciativa.titulo}
                                </p>
                              </div>

                              {/* Additional Actions */}
                              <div style={{
                                marginTop: '1rem',
                                paddingTop: '1rem',
                                borderTop: `1px solid ${tokens.colors.border}`
                              }}>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                  <button
                                    onClick={() => {
                                      const url = iniciativa.urls?.documento ||
                                        `https://www.parlamento.pt/site/search/Pages/pesquisa.aspx?sq=${encodeURIComponent(iniciativa.titulo)}`;
                                      window.open(url, '_blank');
                                    }}
                                    style={{
                                      fontFamily: tokens.fonts.body,
                                      fontSize: '0.75rem',
                                      fontWeight: '500',
                                      backgroundColor: colorSchemes.blue.bg,
                                      color: colorSchemes.blue.text,
                                      padding: '0.375rem 0.75rem',
                                      borderRadius: '2px',
                                      border: `1px solid ${colorSchemes.blue.border}`,
                                      cursor: 'pointer',
                                      transition: 'background-color 0.2s ease'
                                    }}
                                  >
                                    Ver Documento
                                  </button>
                                  <button
                                    onClick={() => {
                                      const url = iniciativa.urls?.debates ||
                                        `https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalhePerguntaRequerimento.aspx?txt=${encodeURIComponent(iniciativa.titulo)}`;
                                      window.open(url, '_blank');
                                    }}
                                    style={{
                                      fontFamily: tokens.fonts.body,
                                      fontSize: '0.75rem',
                                      fontWeight: '500',
                                      backgroundColor: tokens.colors.bgPrimary,
                                      color: tokens.colors.textSecondary,
                                      padding: '0.375rem 0.75rem',
                                      borderRadius: '2px',
                                      border: `1px solid ${tokens.colors.border}`,
                                      cursor: 'pointer',
                                      transition: 'background-color 0.2s ease'
                                    }}
                                  >
                                    Histórico de Votações
                                  </button>
                                  <button
                                    onClick={() => {
                                      const url = iniciativa.urls?.oficial ||
                                        `https://www.parlamento.pt/ActividadeParlamentar/Paginas/Iniciativas.aspx?txt=${encodeURIComponent(iniciativa.titulo)}`;
                                      window.open(url, '_blank');
                                    }}
                                    style={{
                                      fontFamily: tokens.fonts.body,
                                      fontSize: '0.75rem',
                                      fontWeight: '500',
                                      backgroundColor: colorSchemes.green.bg,
                                      color: colorSchemes.green.text,
                                      padding: '0.375rem 0.75rem',
                                      borderRadius: '2px',
                                      border: `1px solid ${colorSchemes.green.border}`,
                                      cursor: 'pointer',
                                      transition: 'background-color 0.2s ease'
                                    }}
                                  >
                                    Ligação oficial
                                  </button>
                                </div>
                                <p style={{
                                  fontFamily: tokens.fonts.body,
                                  fontSize: '0.75rem',
                                  color: tokens.colors.textMuted,
                                  marginTop: '0.5rem'
                                }}>
                                  {iniciativa.urls?.documento || iniciativa.urls?.debates || iniciativa.urls?.oficial ?
                                    'Links diretos para documentos oficiais do Parlamento' :
                                    'Links direcionam para pesquisa no site oficial do Parlamento'
                                  }
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    </div>
                  </div>
                ) : (
                  <div style={{
                    textAlign: 'center',
                    padding: '3rem 1rem',
                    backgroundColor: tokens.colors.bgSecondary,
                    border: `1px solid ${tokens.colors.border}`,
                    borderRadius: '4px'
                  }}>
                    <div style={{
                      margin: '0 auto 1rem',
                      width: '4rem',
                      height: '4rem',
                      backgroundColor: tokens.colors.bgPrimary,
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: `1px solid ${tokens.colors.border}`
                    }}>
                      <FileText style={{ height: '2rem', width: '2rem', color: tokens.colors.textMuted }} />
                    </div>
                    <p style={{
                      fontFamily: tokens.fonts.headline,
                      color: tokens.colors.textSecondary,
                      fontSize: '1.125rem',
                      fontWeight: '500',
                      marginBottom: '0.5rem'
                    }}>
                      Nenhuma iniciativa registada
                    </p>
                    <p style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.875rem',
                      color: tokens.colors.textMuted
                    }}>
                      Este deputado ainda não apresentou iniciativas legislativas nesta legislatura
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'votacoes' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Análise de Votações
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Padrões de votação, disciplina partidária e alinhamentos
                    </p>
                  </div>
                </div>
                <VotingAnalytics
                  deputadoId={cadId}
                  legislatura={deputado?.legislatura?.numero || 'XVII'}
                />
              </div>
            )}

            {activeTab === 'conflitos-interesse' && (
              <div>
                {/* Tab Section Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <div>
                    <h3 style={{
                      fontSize: '1.125rem',
                      fontWeight: 600,
                      color: tokens.colors.textPrimary,
                      fontFamily: tokens.fonts.headline,
                      margin: 0,
                    }}>
                      Registo de Interesses
                    </h3>
                    <p style={{
                      fontSize: '0.8125rem',
                      color: tokens.colors.textMuted,
                      marginTop: '6px',
                      fontFamily: tokens.fonts.body,
                    }}>
                      Declaração de interesses e atividades conforme Lei n.º 52/2019
                    </p>
                  </div>
                </div>

                {conflitosInteresse?.ept?.pendente && (
                  <div style={{
                    display: 'flex',
                    gap: '10px',
                    padding: '1rem',
                    marginBottom: '1.5rem',
                    backgroundColor: tokens.colors.infoBg,
                    border: '1px solid #BFDBFE',
                    borderRadius: '4px',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.875rem',
                    color: tokens.colors.info,
                  }}>
                    <Clock style={{ flexShrink: 0, width: '20px', height: '20px', marginTop: '2px' }} />
                    <p style={{ margin: 0 }}>
                      {(() => {
                        const legs = conflitosInteresse.ept.legislaturas;
                        return legs.length > 1
                          ? `As declarações de interesses das ${legs.slice(0, -1).join(', ')} e ${legs[legs.length - 1]} Legislaturas`
                          : `As declarações de interesses da ${legs[0]} Legislatura`;
                      })()}{' '}
                      estão na Entidade para a Transparência e aguardam autorização da EpT para serem
                      publicadas aqui. Pode consultá-las no{' '}
                      <a href={conflitosInteresse.ept.url} target="_blank" rel="noopener noreferrer" style={{ color: tokens.colors.info, fontWeight: 600 }}>
                        site da EpT
                      </a>.
                    </p>
                  </div>
                )}

                {conflitosInteresse?.cobertura && (
                  <p style={{
                    margin: '0 0 1.5rem 0',
                    fontSize: '0.8125rem',
                    lineHeight: 1.5,
                    color: tokens.colors.textMuted,
                    fontFamily: tokens.fonts.body,
                  }}>
                    Os dados abertos do Parlamento só têm declaração de interesses
                    para {conflitosInteresse.cobertura.com_declaracao.toLocaleString('pt-PT')} de{' '}
                    {conflitosInteresse.cobertura.total.toLocaleString('pt-PT')} deputados com mandato
                    {conflitosInteresse.cobertura.de === conflitosInteresse.cobertura.ate
                      ? ` na ${conflitosInteresse.cobertura.de} Legislatura`
                      : ` da ${conflitosInteresse.cobertura.de} à ${conflitosInteresse.cobertura.ate} Legislatura`}{' '}
                    (cada deputado conta uma vez por legislatura).
                  </p>
                )}

                {conflitosInteresse && conflitosInteresse.tem_declaracao !== false ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {conflitosInteresse.legislatura && (
                      <p style={{ margin: 0, fontSize: '0.8125rem', color: tokens.colors.textMuted, fontFamily: tokens.fonts.body }}>
                        Última declaração publicada nos dados abertos do Parlamento: {conflitosInteresse.legislatura} Legislatura.
                      </p>
                    )}
                    {/* What the latest declaration says, as neutral facts */}
                    <DeclaredInterestsBadge
                      declaresOther={conflitosInteresse.declara_outras_atividades}
                      declaresShareholdings={conflitosInteresse.declara_participacoes}
                    />

                    {/* Exclusivity as published, with no guess when the declaration does not say */}
                    <ExclusivityBadge
                      isExclusive={conflitosInteresse.is_exclusive}
                      showExplanation={true}
                    />

                    {/* Educational Context Box */}
                    <EducationalBox title="Como interpretar esta informação">
                      <p style={{ margin: '0 0 8px 0' }}>
                        Declarar atividades e participações é uma <strong>obrigação legal</strong> (Lei n.º 52/2019)
                        e não indica qualquer irregularidade. Mostramos o que consta da última declaração publicada
                        nos dados abertos do Parlamento.
                      </p>
                      <p style={{ margin: 0 }}>
                        <strong>Regime de exclusividade:</strong> Deputados podem optar por dedicação
                        exclusiva ao mandato ou manter atividades profissionais paralelas (regime legalmente previsto).
                      </p>
                    </EducationalBox>

                    {/* What the declaration lists, with only the fields the release has */}
                    <InterestTable
                      title="Atividades e cargos declarados"
                      columns={ACTIVITY_COLUMNS}
                      items={conflitosInteresse.professional_activities}
                    />
                    <InterestTable
                      title="Participações sociais declaradas"
                      columns={SHAREHOLDING_COLUMNS}
                      items={conflitosInteresse.shareholdings}
                    />

                    {/* Personal Information */}
                    <div style={{
                      backgroundColor: tokens.colors.bgSecondary,
                      borderRadius: '4px',
                      border: `1px solid ${tokens.colors.border}`
                    }}>
                      <div style={{
                        padding: '1rem 1.5rem',
                        borderBottom: `1px solid ${tokens.colors.border}`
                      }}>
                        <h4 style={{
                          fontFamily: tokens.fonts.headline,
                          fontSize: '1rem',
                          fontWeight: '600',
                          color: tokens.colors.textPrimary,
                          display: 'flex',
                          alignItems: 'center',
                          margin: 0
                        }}>
                          <User style={{ height: '20px', width: '20px', color: tokens.colors.primary, marginRight: '0.5rem' }} />
                          Informações Pessoais
                        </h4>
                      </div>
                      <div style={{ padding: '1rem 1.5rem' }}>
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                          gap: '1.5rem'
                        }}>
                          <div>
                            <label style={{
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              color: tokens.colors.textSecondary,
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em'
                            }}>
                              Nome Completo
                            </label>
                            <p style={{
                              fontFamily: tokens.fonts.body,
                              color: tokens.colors.textPrimary,
                              fontWeight: '500',
                              marginTop: '0.25rem'
                            }}>
                              {conflitosInteresse.full_name}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Transparency Note */}
                    <div style={{
                      backgroundColor: tokens.colors.infoBg,
                      border: `1px solid #BFDBFE`,
                      borderRadius: '4px',
                      padding: '1rem'
                    }}>
                      <div style={{ display: 'flex' }}>
                        <Shield style={{ height: '20px', width: '20px', color: tokens.colors.info, marginTop: '2px', flexShrink: 0 }} />
                        <div style={{ marginLeft: '0.75rem' }}>
                          <h5 style={{
                            fontFamily: tokens.fonts.headline,
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            color: '#1E3A8A',
                            margin: 0
                          }}>
                            Transparência e Integridade
                          </h5>
                          <p style={{
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.875rem',
                            color: tokens.colors.info,
                            marginTop: '0.25rem'
                          }}>
                            Esta informação é disponibilizada em cumprimento das obrigações de transparência
                            dos deputados, conforme estabelecido na legislação parlamentar portuguesa.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : conflitosInteresse?.ept?.pendente ? null : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {/* Missing Declaration Status */}
                    <InterestStatusCard
                      data={{
                        hasDeclaration: false,
                        daysOverdue: 0, // Would need to calculate from mandate start date
                      }}
                      showDetails={false}
                    />

                    {/* Educational Context Box */}
                    <EducationalBox title="Sobre a declaração de interesses">
                      <p style={{ margin: '0 0 8px 0' }}>
                        A Lei n.º 52/2019 obriga todos os deputados a submeter uma declaração de interesses
                        no prazo de <strong>30 dias</strong> após tomada de posse.
                      </p>
                      <p style={{ margin: 0 }}>
                        Esta informação pode não estar disponível por diversos motivos: declaração ainda em
                        processamento, deputado recém-empossado, ou dados ainda não digitalizados pelo Parlamento.
                      </p>
                    </EducationalBox>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'attendance' && (
              <div>
                <div style={{
                  marginBottom: '24px',
                  paddingBottom: '20px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                }}>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    color: tokens.colors.textPrimary,
                    fontFamily: tokens.fonts.headline,
                    margin: 0,
                  }}>
                    Presenças no Plenário
                  </h3>
                  <p style={{
                    fontSize: '0.8125rem',
                    color: tokens.colors.textMuted,
                    marginTop: '6px',
                    fontFamily: tokens.fonts.body,
                  }}>
                    Listas de presenças das reuniões plenárias, por legislatura
                  </p>
                </div>
                <AttendancePanel data={attendanceData} />
              </div>
            )}

            {activeTab === 'mandatos-anteriores' && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                  <h3 style={{
                    fontFamily: tokens.fonts.headline,
                    fontSize: '1.25rem',
                    fontWeight: '600',
                    color: tokens.colors.textPrimary,
                    margin: 0
                  }}>
                    Mandatos Anteriores
                  </h3>
                </div>

                {deputado.mandatos_historico && deputado.mandatos_historico.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {deputado.mandatos_historico.map((mandato, index) => (
                      <div
                        key={index}
                        style={{
                          backgroundColor: mandato.is_current ? '#E8F5E9' : tokens.colors.bgSecondary,
                          borderRadius: '4px',
                          border: mandato.is_current ? `2px solid ${tokens.colors.primary}` : `1px solid ${tokens.colors.border}`,
                          padding: '1.5rem',
                          transition: 'border-color 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.75rem' }}>
                              <h4 style={{
                                fontFamily: tokens.fonts.headline,
                                fontSize: '1.125rem',
                                fontWeight: '600',
                                color: tokens.colors.textPrimary,
                                margin: 0
                              }}>
                                {mandato.legislatura_nome}
                              </h4>
                              {mandato.is_current && (
                                <span style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  padding: '0.25rem 0.5rem',
                                  borderRadius: '2px',
                                  fontSize: '0.75rem',
                                  fontWeight: '600',
                                  backgroundColor: tokens.colors.primary,
                                  color: '#FFFFFF',
                                  textTransform: 'uppercase',
                                  letterSpacing: '0.025em'
                                }}>
                                  Atual
                                </span>
                              )}
                            </div>

                            <div style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                              gap: '1rem',
                              marginBottom: '1rem'
                            }}>
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                fontFamily: tokens.fonts.mono,
                                fontSize: '0.875rem',
                                color: tokens.colors.textSecondary
                              }}>
                                <Calendar style={{ height: '16px', width: '16px', marginRight: '0.5rem' }} />
                                <span>
                                  {new Date(mandato.mandato_inicio).toLocaleDateString('pt-PT')} - {' '}
                                  {mandato.mandato_fim
                                    ? new Date(mandato.mandato_fim).toLocaleDateString('pt-PT')
                                    : 'Presente'
                                  }
                                </span>
                              </div>

                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.875rem',
                                color: tokens.colors.textSecondary
                              }}>
                                <MapPin style={{ height: '16px', width: '16px', marginRight: '0.5rem' }} />
                                <span>{mandato.circulo}</span>
                              </div>

                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                fontFamily: tokens.fonts.body,
                                fontSize: '0.875rem',
                                color: tokens.colors.textSecondary
                              }}>
                                <Briefcase style={{ height: '16px', width: '16px', marginRight: '0.5rem' }} />
                                <span>{mandato.partido_sigla}</span>
                              </div>
                            </div>
                          </div>

                          {mandato.is_current && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                padding: '0.5rem 0.75rem',
                                borderRadius: '4px',
                                fontSize: '0.875rem',
                                fontWeight: '500',
                                backgroundColor: colorSchemes.green.bg,
                                color: colorSchemes.green.text,
                                border: `1px solid ${colorSchemes.green.border}`
                              }}>
                                <Calendar style={{ height: '16px', width: '16px', marginRight: '0.5rem' }} />
                                Legislatura Atual
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{
                    textAlign: 'center',
                    padding: '3rem 1rem',
                    backgroundColor: tokens.colors.bgSecondary,
                    border: `1px solid ${tokens.colors.border}`,
                    borderRadius: '4px'
                  }}>
                    <div style={{
                      margin: '0 auto 1rem',
                      width: '4rem',
                      height: '4rem',
                      backgroundColor: tokens.colors.bgPrimary,
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      border: `1px solid ${tokens.colors.border}`
                    }}>
                      <Calendar style={{ height: '2rem', width: '2rem', color: tokens.colors.textMuted }} />
                    </div>
                    <p style={{
                      fontFamily: tokens.fonts.headline,
                      color: tokens.colors.textSecondary,
                      fontSize: '1.125rem',
                      fontWeight: '500',
                      marginBottom: '0.5rem'
                    }}>
                      Apenas um mandato registado
                    </p>
                    <p style={{
                      fontFamily: tokens.fonts.body,
                      fontSize: '0.875rem',
                      color: tokens.colors.textMuted
                    }}>
                      Este deputado só tem registo de mandato na legislatura atual
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};

export default DeputadoDetalhes;

