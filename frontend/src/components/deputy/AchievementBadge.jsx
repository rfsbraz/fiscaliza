/**
 * AchievementBadge Component
 *
 * Recognition system for exceptional parliamentary activity.
 * Badges are awarded based on quantifiable metrics, not subjective assessments.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import {
  Award,
  MessageSquare,
  FileText,
  Users,
  MapPin,
  TrendingUp,
  Shield,
  BookOpen,
  Briefcase,
  Target,
  Zap,
  Clock,
} from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Badge type configurations with criteria and visual styling
 */
const BADGE_CONFIGS = {
  // Intervention badges
  topQuestioner: {
    Icon: MessageSquare,
    label: 'Questionador Ativo',
    description: 'Acima do percentil 90 em perguntas ao Governo',
    criteria: 'Mais de 50 perguntas por ano parlamentar',
    color: tokens.colors.statusGreen,
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    category: 'interventions',
  },
  debateParticipant: {
    Icon: Users,
    label: 'Participante Ativo',
    description: 'Participação consistente em debates',
    criteria: 'Intervenções em mais de 70% das sessões plenárias',
    color: tokens.colors.primary,
    bg: tokens.colors.contextEducationalBg,
    border: tokens.colors.contextEducationalBorder,
    category: 'interventions',
  },

  // Initiative badges
  legislativeProducer: {
    Icon: FileText,
    label: 'Produtor Legislativo',
    description: 'Elevada produção de iniciativas legislativas',
    criteria: 'Mais de 20 iniciativas apresentadas na legislatura',
    color: tokens.colors.primary,
    bg: tokens.colors.contextEducationalBg,
    border: tokens.colors.contextEducationalBorder,
    category: 'initiatives',
  },
  crossPartyCollaborator: {
    Icon: Users,
    label: 'Colaborador Transversal',
    description: 'Trabalho em iniciativas com múltiplos partidos',
    criteria: 'Mais de 5 iniciativas conjuntas com outros partidos',
    color: tokens.colors.statusAmber,
    bg: tokens.colors.statusAmberBg,
    border: tokens.colors.statusAmberBorder,
    category: 'initiatives',
  },
  policySpecialist: {
    Icon: Target,
    label: 'Especialista Temático',
    description: 'Foco consistente numa área política específica',
    criteria: 'Mais de 60% das iniciativas numa mesma área temática',
    color: tokens.colors.infoSecondary,
    bg: '#EBF5FF',
    border: '#3B82F6',
    category: 'initiatives',
  },
  persistentAdvocate: {
    Icon: TrendingUp,
    label: 'Defensor Persistente',
    description: 'Acompanhamento de temas ao longo de múltiplas legislaturas',
    criteria: 'Iniciativas sobre o mesmo tema em 2+ legislaturas',
    color: tokens.colors.statusGreen,
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    category: 'initiatives',
  },

  // Constituency badges
  regionalAdvocate: {
    Icon: MapPin,
    label: 'Defensor Regional',
    description: 'Forte ligação às questões do círculo eleitoral',
    criteria: 'Mais de 30% das intervenções sobre temas regionais',
    color: tokens.colors.statusAmber,
    bg: tokens.colors.statusAmberBg,
    border: tokens.colors.statusAmberBorder,
    category: 'constituency',
  },

  // Attendance badges
  consistentAttendee: {
    Icon: Clock,
    label: 'Presença Consistente',
    description: 'Taxa de presença acima da média parlamentar',
    criteria: 'Presença superior a 90% nas sessões plenárias',
    color: tokens.colors.statusGreen,
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    category: 'attendance',
  },
  committeeActive: {
    Icon: Briefcase,
    label: 'Ativo em Comissões',
    description: 'Participação elevada em trabalhos de comissão',
    criteria: 'Presença superior a 85% nas reuniões de comissão',
    color: tokens.colors.primary,
    bg: tokens.colors.contextEducationalBg,
    border: tokens.colors.contextEducationalBorder,
    category: 'attendance',
  },

  // Transparency badges
  fullDisclosure: {
    Icon: Shield,
    label: 'Declaração Completa',
    description: 'Declaração de interesses atualizada e completa',
    criteria: 'Declaração submetida dentro do prazo com todos os campos preenchidos',
    color: tokens.colors.statusGreen,
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    category: 'transparency',
  },
  exclusiveMandate: {
    Icon: Target,
    label: 'Mandato Exclusivo',
    description: 'Dedicação exclusiva ao mandato parlamentar',
    criteria: 'Declaração de regime de exclusividade',
    color: tokens.colors.primary,
    bg: tokens.colors.contextEducationalBg,
    border: tokens.colors.contextEducationalBorder,
    category: 'transparency',
  },

  // Special badges
  rookie: {
    Icon: Zap,
    label: 'Deputado de Primeira Viagem',
    description: 'Primeiro mandato parlamentar',
    criteria: 'Primeiro mandato na Assembleia da República',
    color: tokens.colors.statusAmber,
    bg: tokens.colors.statusAmberBg,
    border: tokens.colors.statusAmberBorder,
    category: 'special',
  },
  veteran: {
    Icon: Award,
    label: 'Veterano Parlamentar',
    description: 'Experiência significativa na Assembleia',
    criteria: 'Três ou mais mandatos parlamentares',
    color: tokens.colors.infoSecondary,
    bg: '#EBF5FF',
    border: '#3B82F6',
    category: 'special',
  },
};

/**
 * AchievementBadge - Single achievement badge display
 *
 * @param {Object} props
 * @param {string} props.type - Badge type from BADGE_CONFIGS
 * @param {string} props.size - 'small' | 'medium' | 'large'
 * @param {boolean} props.showDescription - Show description text
 * @param {boolean} props.showCriteria - Show criteria on hover
 * @param {string} props.customLabel - Override default label
 * @param {string} props.customDescription - Override default description
 */
const AchievementBadge = ({
  type,
  size = 'medium',
  showDescription = true,
  showCriteria = true,
  customLabel,
  customDescription,
}) => {
  const config = BADGE_CONFIGS[type];

  if (!config) {
    console.warn(`Unknown badge type: ${type}`);
    return null;
  }

  const BadgeIcon = config.Icon;
  const label = customLabel || config.label;
  const description = customDescription || config.description;

  const sizeStyles = {
    small: {
      padding: '6px 10px',
      iconSize: 14,
      labelSize: '0.75rem',
      descSize: '0.625rem',
      gap: '6px',
    },
    medium: {
      padding: '10px 14px',
      iconSize: 18,
      labelSize: '0.8125rem',
      descSize: '0.75rem',
      gap: '10px',
    },
    large: {
      padding: '14px 18px',
      iconSize: 22,
      labelSize: '0.875rem',
      descSize: '0.8125rem',
      gap: '12px',
    },
  };

  const s = sizeStyles[size];

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: s.gap,
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        borderRadius: '4px',
        padding: s.padding,
        cursor: showCriteria ? 'help' : 'default',
      }}
      title={showCriteria ? `Critério: ${config.criteria}` : undefined}
    >
      <div
        style={{
          width: s.iconSize + 8,
          height: s.iconSize + 8,
          borderRadius: '4px',
          backgroundColor: `${config.color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <BadgeIcon size={s.iconSize} style={{ color: config.color }} />
      </div>
      <div>
        <span
          style={{
            display: 'block',
            fontFamily: tokens.fonts.body,
            fontSize: s.labelSize,
            fontWeight: 600,
            color: config.color,
          }}
        >
          {label}
        </span>
        {showDescription && (
          <span
            style={{
              display: 'block',
              fontFamily: tokens.fonts.body,
              fontSize: s.descSize,
              color: tokens.colors.textMuted,
              marginTop: '2px',
            }}
          >
            {description}
          </span>
        )}
      </div>
    </div>
  );
};

/**
 * BadgeCollection - Display multiple badges in a grid
 */
export const BadgeCollection = ({
  badges = [],
  size = 'medium',
  showDescriptions = true,
  maxDisplay = 6,
}) => {
  const displayBadges = badges.slice(0, maxDisplay);
  const remainingCount = badges.length - maxDisplay;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        {displayBadges.map((badge, index) => (
          <AchievementBadge
            key={index}
            type={typeof badge === 'string' ? badge : badge.type}
            size={size}
            showDescription={showDescriptions}
            customLabel={typeof badge === 'object' ? badge.label : undefined}
            customDescription={typeof badge === 'object' ? badge.description : undefined}
          />
        ))}
        {remainingCount > 0 && (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '8px 12px',
              backgroundColor: tokens.colors.bgTertiary,
              border: `1px solid ${tokens.colors.border}`,
              borderRadius: '4px',
              fontFamily: tokens.fonts.body,
              fontSize: '0.8125rem',
              color: tokens.colors.textMuted,
            }}
          >
            +{remainingCount} mais
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * BadgeSummary - Compact summary of earned badges
 */
export const BadgeSummary = ({ badges = [], label = 'Reconhecimentos' }) => {
  const categories = {};
  badges.forEach(badge => {
    const config = BADGE_CONFIGS[typeof badge === 'string' ? badge : badge.type];
    if (config) {
      categories[config.category] = (categories[config.category] || 0) + 1;
    }
  });

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '12px 16px',
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <Award size={18} style={{ color: tokens.colors.statusAmber }} />
        <span
          style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '1.25rem',
            fontWeight: 700,
            color: tokens.colors.textPrimary,
          }}
        >
          {badges.length}
        </span>
        <span
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.8125rem',
            color: tokens.colors.textSecondary,
          }}
        >
          {label}
        </span>
      </div>
      <div
        style={{
          display: 'flex',
          gap: '12px',
          paddingLeft: '16px',
          borderLeft: `1px solid ${tokens.colors.border}`,
        }}
      >
        {Object.entries(categories).map(([category, count]) => (
          <div
            key={category}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <span
              style={{
                fontFamily: tokens.fonts.mono,
                fontSize: '0.875rem',
                fontWeight: 600,
                color: tokens.colors.textPrimary,
              }}
            >
              {count}
            </span>
            <span
              style={{
                fontFamily: tokens.fonts.body,
                fontSize: '0.75rem',
                color: tokens.colors.textMuted,
                textTransform: 'capitalize',
              }}
            >
              {getCategoryLabel(category)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * RedFlagIndicator - Warning indicator for notable metrics
 * Uses factual, non-accusatory language
 */
export const RedFlagIndicator = ({
  type,
  value,
  threshold,
  showDetails = true,
}) => {
  const flagConfigs = {
    lowActivity: {
      label: 'Atividade reduzida',
      description: `${value} intervenções no último ano`,
      threshold: 'Abaixo da média do grupo parlamentar',
    },
    noQuestions: {
      label: 'Sem perguntas recentes',
      description: `${value} meses sem perguntas ao Governo`,
      threshold: 'Considere verificar o contexto (ex: licença, missão)',
    },
    missingDeclaration: {
      label: 'Declaração pendente',
      description: 'Declaração de interesses não submetida ou incompleta',
      threshold: 'Prazo legal: 30 dias após tomada de posse',
    },
    lowAttendance: {
      label: 'Presença abaixo da média',
      description: `${value}% de presença nas sessões plenárias`,
      threshold: 'Média parlamentar: 85%',
    },
  };

  const config = flagConfigs[type];
  if (!config) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '14px 16px',
        backgroundColor: tokens.colors.statusAmberBg,
        border: `1px solid ${tokens.colors.statusAmberBorder}`,
        borderRadius: '4px',
      }}
    >
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: tokens.colors.statusAmber,
          marginTop: '6px',
          flexShrink: 0,
        }}
      />
      <div>
        <span
          style={{
            display: 'block',
            fontFamily: tokens.fonts.body,
            fontSize: '0.875rem',
            fontWeight: 600,
            color: tokens.colors.textPrimary,
          }}
        >
          {config.label}
        </span>
        {showDetails && (
          <>
            <span
              style={{
                display: 'block',
                fontFamily: tokens.fonts.body,
                fontSize: '0.8125rem',
                color: tokens.colors.textSecondary,
                marginTop: '4px',
              }}
            >
              {config.description}
            </span>
            <span
              style={{
                display: 'block',
                fontFamily: tokens.fonts.body,
                fontSize: '0.75rem',
                color: tokens.colors.textMuted,
                marginTop: '4px',
                fontStyle: 'italic',
              }}
            >
              {config.threshold}
            </span>
          </>
        )}
      </div>
    </div>
  );
};

// Helper function to get category labels in Portuguese
function getCategoryLabel(category) {
  const labels = {
    interventions: 'Intervenções',
    initiatives: 'Iniciativas',
    constituency: 'Círculo',
    attendance: 'Presença',
    transparency: 'Transparência',
    special: 'Especial',
  };
  return labels[category] || category;
}

// Export badge configs for external use
export { BADGE_CONFIGS };

export default AchievementBadge;
