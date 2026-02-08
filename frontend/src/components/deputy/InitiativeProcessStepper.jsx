/**
 * InitiativeProcessStepper Component
 *
 * Visual timeline showing the 7-step legislative process.
 * Uses plain Portuguese labels (no jargon) for citizen accessibility.
 *
 * Part of the Constitutional Modernism design system.
 */

import React from 'react';
import { FileText, CheckCircle, Users, BookOpen, MessageSquare, Vote, Award, Clock, XCircle } from 'lucide-react';
import { tokens } from '../../styles/tokens';

/**
 * Legislative process steps with citizen-friendly labels
 */
const PROCESS_STEPS = [
  {
    id: 'presentation',
    label: 'Apresentação',
    description: 'Iniciativa apresentada ao Parlamento',
    Icon: FileText,
  },
  {
    id: 'admission',
    label: 'Admissão',
    description: 'Verificação de conformidade regimental',
    Icon: CheckCircle,
  },
  {
    id: 'committee',
    label: 'Comissão',
    description: 'Análise pela comissão competente',
    Icon: Users,
  },
  {
    id: 'report',
    label: 'Parecer',
    description: 'Elaboração de parecer técnico',
    Icon: BookOpen,
  },
  {
    id: 'debate',
    label: 'Debate',
    description: 'Discussão em sessão plenária',
    Icon: MessageSquare,
  },
  {
    id: 'vote',
    label: 'Votação',
    description: 'Votação final em plenário',
    Icon: Vote,
  },
  {
    id: 'promulgation',
    label: 'Promulgação',
    description: 'Publicação em Diário da República',
    Icon: Award,
  },
];

/**
 * Map API phase values to step IDs
 */
const PHASE_MAPPING = {
  'Apresentação': 'presentation',
  'Admissão': 'admission',
  'Comissão': 'committee',
  'Em comissão': 'committee',
  'Parecer': 'report',
  'Debate': 'debate',
  'Discussão': 'debate',
  'Votação': 'vote',
  'Votação final': 'vote',
  'Promulgação': 'promulgation',
  'Aprovado': 'promulgation',
  'Publicado': 'promulgation',
  // Additional mappings for common variations
  'Rejeitado': 'vote',
  'Retirado': 'presentation',
  'Caducado': 'committee',
};

/**
 * Get step status based on current phase
 */
const getStepStatus = (stepIndex, currentStepIndex, isRejected, isExpired) => {
  if (isRejected && stepIndex === currentStepIndex) {
    return 'rejected';
  }
  if (isExpired && stepIndex === currentStepIndex) {
    return 'expired';
  }
  if (stepIndex < currentStepIndex) {
    return 'completed';
  }
  if (stepIndex === currentStepIndex) {
    return 'current';
  }
  return 'pending';
};

/**
 * Status color configurations
 */
const statusConfig = {
  completed: {
    bg: tokens.colors.statusGreenBg,
    border: tokens.colors.statusGreenBorder,
    color: tokens.colors.statusGreen,
    lineColor: tokens.colors.statusGreen,
  },
  current: {
    bg: tokens.colors.primary,
    border: tokens.colors.primary,
    color: '#FFFFFF',
    lineColor: tokens.colors.border,
  },
  pending: {
    bg: tokens.colors.bgTertiary,
    border: tokens.colors.border,
    color: tokens.colors.textMuted,
    lineColor: tokens.colors.border,
  },
  rejected: {
    bg: tokens.colors.statusRedBg,
    border: tokens.colors.statusRedBorder,
    color: tokens.colors.statusRed,
    lineColor: tokens.colors.statusRed,
  },
  expired: {
    bg: tokens.colors.statusNeutralBg,
    border: tokens.colors.statusNeutralBorder,
    color: tokens.colors.statusNeutral,
    lineColor: tokens.colors.statusNeutral,
  },
};

/**
 * InitiativeProcessStepper - Visual timeline of legislative process
 *
 * @param {Object} props
 * @param {string} props.currentPhase - Current phase from API (e.g., "Comissão")
 * @param {boolean} props.isRejected - Whether the initiative was rejected
 * @param {boolean} props.isExpired - Whether the initiative expired (caducou)
 * @param {boolean} props.isApproved - Whether the initiative was approved
 * @param {string} props.voteResult - Result of the vote if available
 * @param {'horizontal' | 'vertical'} props.orientation - Layout orientation
 * @param {'compact' | 'normal'} props.size - Size variant
 * @param {boolean} props.showDescriptions - Whether to show step descriptions
 */
const InitiativeProcessStepper = ({
  currentPhase = 'Apresentação',
  isRejected = false,
  isExpired = false,
  isApproved = false,
  voteResult,
  orientation = 'horizontal',
  size = 'normal',
  showDescriptions = true,
}) => {
  // Map current phase to step index
  const currentStepId = PHASE_MAPPING[currentPhase] || 'presentation';
  const currentStepIndex = PROCESS_STEPS.findIndex(s => s.id === currentStepId);

  // Size configurations
  const sizeConfig = {
    compact: {
      iconSize: 20,
      circleSize: 32,
      fontSize: '0.75rem',
      descFontSize: '0.625rem',
      gap: '4px',
    },
    normal: {
      iconSize: 24,
      circleSize: 44,
      fontSize: '0.8125rem',
      descFontSize: '0.75rem',
      gap: '8px',
    },
  };

  const sizes = sizeConfig[size];

  // Horizontal layout
  if (orientation === 'horizontal') {
    return (
      <div style={{
        backgroundColor: tokens.colors.bgSecondary,
        border: `1px solid ${tokens.colors.border}`,
        borderRadius: '4px',
        padding: size === 'compact' ? '16px' : '24px',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          position: 'relative',
        }}>
          {/* Connection line */}
          <div style={{
            position: 'absolute',
            top: sizes.circleSize / 2,
            left: sizes.circleSize / 2,
            right: sizes.circleSize / 2,
            height: '2px',
            backgroundColor: tokens.colors.border,
            zIndex: 0,
          }} />

          {PROCESS_STEPS.map((step, index) => {
            const status = getStepStatus(index, currentStepIndex, isRejected, isExpired);
            const config = statusConfig[status];
            const StepIcon = step.Icon;

            return (
              <div
                key={step.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  flex: 1,
                  position: 'relative',
                  zIndex: 1,
                }}
              >
                {/* Step circle */}
                <div style={{
                  width: sizes.circleSize,
                  height: sizes.circleSize,
                  borderRadius: '50%',
                  backgroundColor: config.bg,
                  border: `2px solid ${config.border}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: sizes.gap,
                  transition: 'all 0.2s ease',
                }}>
                  {status === 'rejected' ? (
                    <XCircle size={sizes.iconSize - 4} style={{ color: config.color }} />
                  ) : status === 'expired' ? (
                    <Clock size={sizes.iconSize - 4} style={{ color: config.color }} />
                  ) : (
                    <StepIcon size={sizes.iconSize - 4} style={{ color: config.color }} />
                  )}
                </div>

                {/* Step label */}
                <span style={{
                  fontFamily: tokens.fonts.body,
                  fontSize: sizes.fontSize,
                  fontWeight: status === 'current' ? 600 : 500,
                  color: status === 'current' ? tokens.colors.textPrimary : tokens.colors.textSecondary,
                  textAlign: 'center',
                  whiteSpace: 'nowrap',
                }}>
                  {step.label}
                </span>

                {/* Step description */}
                {showDescriptions && size === 'normal' && (
                  <span style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: sizes.descFontSize,
                    color: tokens.colors.textMuted,
                    textAlign: 'center',
                    marginTop: '4px',
                    maxWidth: '100px',
                    lineHeight: 1.3,
                  }}>
                    {step.description}
                  </span>
                )}

                {/* Current step indicator */}
                {status === 'current' && !isRejected && !isExpired && (
                  <div style={{
                    marginTop: '8px',
                    padding: '2px 8px',
                    backgroundColor: tokens.colors.primary,
                    borderRadius: '2px',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: '#FFFFFF',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    Em curso
                  </div>
                )}

                {/* Rejected indicator */}
                {status === 'rejected' && (
                  <div style={{
                    marginTop: '8px',
                    padding: '2px 8px',
                    backgroundColor: tokens.colors.statusRedBg,
                    border: `1px solid ${tokens.colors.statusRedBorder}`,
                    borderRadius: '2px',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: tokens.colors.statusRed,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    Rejeitado
                  </div>
                )}

                {/* Expired indicator */}
                {status === 'expired' && (
                  <div style={{
                    marginTop: '8px',
                    padding: '2px 8px',
                    backgroundColor: tokens.colors.statusNeutralBg,
                    border: `1px solid ${tokens.colors.statusNeutralBorder}`,
                    borderRadius: '2px',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: tokens.colors.statusNeutral,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    Caducado
                  </div>
                )}

                {/* Approved indicator */}
                {index === PROCESS_STEPS.length - 1 && isApproved && (
                  <div style={{
                    marginTop: '8px',
                    padding: '2px 8px',
                    backgroundColor: tokens.colors.statusGreenBg,
                    border: `1px solid ${tokens.colors.statusGreenBorder}`,
                    borderRadius: '2px',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    color: tokens.colors.statusGreen,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    Aprovado
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Vertical layout
  return (
    <div style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '4px',
      padding: size === 'compact' ? '16px' : '24px',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
        {PROCESS_STEPS.map((step, index) => {
          const status = getStepStatus(index, currentStepIndex, isRejected, isExpired);
          const config = statusConfig[status];
          const StepIcon = step.Icon;
          const isLast = index === PROCESS_STEPS.length - 1;

          return (
            <div
              key={step.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '16px',
              }}
            >
              {/* Step circle and line */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}>
                <div style={{
                  width: sizes.circleSize,
                  height: sizes.circleSize,
                  borderRadius: '50%',
                  backgroundColor: config.bg,
                  border: `2px solid ${config.border}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}>
                  {status === 'rejected' ? (
                    <XCircle size={sizes.iconSize - 4} style={{ color: config.color }} />
                  ) : status === 'expired' ? (
                    <Clock size={sizes.iconSize - 4} style={{ color: config.color }} />
                  ) : (
                    <StepIcon size={sizes.iconSize - 4} style={{ color: config.color }} />
                  )}
                </div>
                {!isLast && (
                  <div style={{
                    width: '2px',
                    height: '32px',
                    backgroundColor: index < currentStepIndex ? tokens.colors.statusGreen : tokens.colors.border,
                  }} />
                )}
              </div>

              {/* Step content */}
              <div style={{
                flex: 1,
                paddingBottom: isLast ? 0 : '16px',
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}>
                  <span style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: sizes.fontSize,
                    fontWeight: status === 'current' ? 600 : 500,
                    color: status === 'current' ? tokens.colors.textPrimary : tokens.colors.textSecondary,
                  }}>
                    {step.label}
                  </span>

                  {status === 'current' && !isRejected && !isExpired && (
                    <span style={{
                      padding: '2px 6px',
                      backgroundColor: tokens.colors.primary,
                      borderRadius: '2px',
                      fontSize: '0.625rem',
                      fontWeight: 600,
                      color: '#FFFFFF',
                      textTransform: 'uppercase',
                    }}>
                      Em curso
                    </span>
                  )}

                  {status === 'rejected' && (
                    <span style={{
                      padding: '2px 6px',
                      backgroundColor: tokens.colors.statusRedBg,
                      border: `1px solid ${tokens.colors.statusRedBorder}`,
                      borderRadius: '2px',
                      fontSize: '0.625rem',
                      fontWeight: 600,
                      color: tokens.colors.statusRed,
                      textTransform: 'uppercase',
                    }}>
                      Rejeitado
                    </span>
                  )}
                </div>

                {showDescriptions && (
                  <p style={{
                    fontFamily: tokens.fonts.body,
                    fontSize: sizes.descFontSize,
                    color: tokens.colors.textMuted,
                    margin: '4px 0 0 0',
                    lineHeight: 1.4,
                  }}>
                    {step.description}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/**
 * InitiativeOutcomesSummary - Summary card showing initiative outcomes
 */
export const InitiativeOutcomesSummary = ({
  approved = 0,
  rejected = 0,
  inProgress = 0,
  expired = 0,
  total = 0,
}) => {
  return (
    <div style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '4px',
      padding: '20px 24px',
    }}>
      <h4 style={{
        fontFamily: tokens.fonts.body,
        fontSize: '0.875rem',
        fontWeight: 600,
        color: tokens.colors.textPrimary,
        margin: '0 0 16px 0',
      }}>
        Resultados das Iniciativas
      </h4>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '16px',
      }}>
        {/* Approved */}
        <div style={{
          textAlign: 'center',
          padding: '12px',
          backgroundColor: tokens.colors.statusGreenBg,
          borderRadius: '4px',
          border: `1px solid ${tokens.colors.statusGreenBorder}`,
        }}>
          <p style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '1.5rem',
            fontWeight: 700,
            color: tokens.colors.statusGreen,
            margin: 0,
          }}>
            {approved}
          </p>
          <p style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textSecondary,
            margin: '4px 0 0 0',
          }}>
            Aprovadas
          </p>
        </div>

        {/* Rejected */}
        <div style={{
          textAlign: 'center',
          padding: '12px',
          backgroundColor: tokens.colors.statusRedBg,
          borderRadius: '4px',
          border: `1px solid ${tokens.colors.statusRedBorder}`,
        }}>
          <p style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '1.5rem',
            fontWeight: 700,
            color: tokens.colors.statusRed,
            margin: 0,
          }}>
            {rejected}
          </p>
          <p style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textSecondary,
            margin: '4px 0 0 0',
          }}>
            Rejeitadas
          </p>
        </div>

        {/* In Progress */}
        <div style={{
          textAlign: 'center',
          padding: '12px',
          backgroundColor: tokens.colors.statusAmberBg,
          borderRadius: '4px',
          border: `1px solid ${tokens.colors.statusAmberBorder}`,
        }}>
          <p style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '1.5rem',
            fontWeight: 700,
            color: tokens.colors.statusAmber,
            margin: 0,
          }}>
            {inProgress}
          </p>
          <p style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textSecondary,
            margin: '4px 0 0 0',
          }}>
            Em discussão
          </p>
        </div>

        {/* Expired */}
        <div style={{
          textAlign: 'center',
          padding: '12px',
          backgroundColor: tokens.colors.statusNeutralBg,
          borderRadius: '4px',
          border: `1px solid ${tokens.colors.statusNeutralBorder}`,
        }}>
          <p style={{
            fontFamily: tokens.fonts.mono,
            fontSize: '1.5rem',
            fontWeight: 700,
            color: tokens.colors.statusNeutral,
            margin: 0,
          }}>
            {expired}
          </p>
          <p style={{
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textSecondary,
            margin: '4px 0 0 0',
          }}>
            Caducadas
          </p>
        </div>
      </div>

      {/* Context note - CRITICAL for political analyst recommendations */}
      <div style={{
        marginTop: '16px',
        padding: '12px',
        backgroundColor: tokens.colors.contextEducationalBg,
        borderLeft: `4px solid ${tokens.colors.contextEducationalBorder}`,
        borderRadius: '2px',
      }}>
        <p style={{
          fontFamily: tokens.fonts.body,
          fontSize: '0.8125rem',
          color: tokens.colors.textSecondary,
          margin: 0,
          lineHeight: 1.5,
        }}>
          <strong>Contexto importante:</strong> Em sistemas parlamentares, deputados da oposição
          apresentam frequentemente iniciativas para debate público, mesmo sem expectativa de aprovação.
          A taxa de aprovação não deve ser interpretada como medida de eficácia parlamentar.
        </p>
      </div>
    </div>
  );
};

/**
 * AuthorshipPatternIndicator - Shows authorship pattern (Individual/Group/Cross-party)
 */
export const AuthorshipPatternIndicator = ({
  individual = 0,
  group = 0,
  crossParty = 0,
}) => {
  const total = individual + group + crossParty;
  if (total === 0) return null;

  const patterns = [
    { label: 'Individual', count: individual, color: tokens.colors.primary },
    { label: 'Grupo Parlamentar', count: group, color: tokens.colors.statusAmber },
    { label: 'Transpartidária', count: crossParty, color: tokens.colors.statusGreen },
  ];

  return (
    <div style={{
      backgroundColor: tokens.colors.bgSecondary,
      border: `1px solid ${tokens.colors.border}`,
      borderRadius: '4px',
      padding: '16px 20px',
    }}>
      <h4 style={{
        fontFamily: tokens.fonts.body,
        fontSize: '0.8125rem',
        fontWeight: 600,
        color: tokens.colors.textPrimary,
        margin: '0 0 12px 0',
      }}>
        Padrão de Autoria
      </h4>

      {/* Stacked bar */}
      <div style={{
        height: '12px',
        borderRadius: '6px',
        backgroundColor: tokens.colors.bgTertiary,
        overflow: 'hidden',
        display: 'flex',
        marginBottom: '12px',
      }}>
        {patterns.map((pattern) => (
          pattern.count > 0 && (
            <div
              key={pattern.label}
              style={{
                width: `${(pattern.count / total) * 100}%`,
                backgroundColor: pattern.color,
              }}
            />
          )
        ))}
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: '16px',
        flexWrap: 'wrap',
      }}>
        {patterns.map((pattern) => (
          <div key={pattern.label} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{
              width: '10px',
              height: '10px',
              borderRadius: '2px',
              backgroundColor: pattern.color,
            }} />
            <span style={{
              fontFamily: tokens.fonts.body,
              fontSize: '0.75rem',
              color: tokens.colors.textSecondary,
            }}>
              {pattern.label}: {pattern.count} ({total > 0 ? Math.round((pattern.count / total) * 100) : 0}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InitiativeProcessStepper;
