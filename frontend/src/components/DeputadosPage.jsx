import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { User, Search, ArrowRight, Calendar } from 'lucide-react';
import { apiFetch } from '../config/api';
import { tokens } from '../styles/tokens';
import { LoadingSpinner, Card, PageHeader, Pagination } from './common';
import { formatNumber, plural } from '../utils/format';

// The status badge of a card, from the data: a seat now, then the latest AR situation. Every
// suspension reads "Mandato suspenso", as on the deputy page (#201).
export const statusBadge = (deputado) => {
  const status = deputado.mandate_status || deputado.career_info?.mandate_status;
  if (deputado.is_seated || deputado.career_info?.is_seated) return 'Em Exercício';
  if (status && status.startsWith('Suspenso')) return 'Mandato suspenso';
  if (status === 'Renunciou') return 'Renunciou';
  return deputado.career_info?.is_currently_active ? 'Ativo' : 'Inativo';
};

const BADGE_TONES = {
  'Em Exercício': { color: tokens.colors.primary, background: '#F0F7F4' },
  'Mandato suspenso': { color: '#92400E', background: '#FEF3C7' },
  Renunciou: { color: '#991B1B', background: '#FEE2E2' },
  Ativo: { color: tokens.colors.primary, background: '#F0F7F4' },
  Inativo: { color: tokens.colors.textMuted, background: '#F5F5F5' },
};

const DeputadosPage = () => {
  const [deputados, setDeputados] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState(null)
  const [filters, setFilters] = useState(null)
  // The header counts everyone, so it keeps the totals of the unfiltered list (#248).
  const [totais, setTotais] = useState(null)
  const [pesquisado, setPesquisado] = useState('')

  useEffect(() => {
    fetchDeputados()
  }, [page, search])

  const fetchDeputados = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: '20',
        active_only: 'false'
      })

      if (search) {
        params.append('search', search)
      }

      const response = await apiFetch(`deputados?${params}`)
      const data = await response.json()
      setDeputados(data.deputados || [])
      setPagination(data.pagination)
      setFilters(data.filters)
      setPesquisado(search)
      if (!search) setTotais({ pessoas: data.pagination?.total, mandatos: data.filters?.total_deputy_records })
    } catch (error) {
      console.error('Erro ao carregar deputados:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchDeputados()
  }

  if (loading && (deputados || []).length === 0) {
    return <LoadingSpinner message="A carregar deputados" />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
    >
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
        <h1
          style={{
            fontFamily: tokens.fonts.headline,
            fontSize: '2.25rem',
            fontWeight: 700,
            color: tokens.colors.textPrimary,
            marginBottom: '0.5rem',
          }}
        >
          Deputados
        </h1>
        <p
          style={{
            fontFamily: tokens.fonts.body,
            fontSize: '1rem',
            color: tokens.colors.textSecondary,
          }}
        >
          {filters ? (
            <>
              <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600, color: tokens.colors.primary }}>
                {formatNumber(totais ? totais.pessoas : pagination?.total)}
              </span> pessoas únicas · {' '}
              <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>
                {formatNumber(totais ? totais.mandatos : filters.total_deputy_records)}
              </span> mandatos totais · {' '}
              <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600, color: tokens.colors.primary }}>
                {formatNumber(filters.seated_deputies_count || filters.active_deputies_count)}
              </span> em exercício na data dos dados · {' '}
              <span style={{ fontFamily: tokens.fonts.mono, fontWeight: 600 }}>
                {formatNumber(filters.active_deputies_count)}
              </span> deputados tiveram lugar na legislatura atual
            </>
          ) : 'A carregar...'}
        </p>
      </div>

      {/* Search */}
      <div
        style={{
          backgroundColor: tokens.colors.bgSecondary,
          border: `1px solid ${tokens.colors.border}`,
          borderRadius: '4px',
          padding: '1.25rem',
        }}
      >
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: tokens.colors.textMuted,
              }}
            />
            <input
              type="text"
              placeholder="Pesquisar por nome ou partido..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '0.625rem 0.75rem 0.625rem 2.25rem',
                fontFamily: tokens.fonts.body,
                fontSize: '0.9375rem',
                border: `1px solid ${tokens.colors.border}`,
                borderRadius: '2px',
                outline: 'none',
                transition: 'border-color 150ms ease',
              }}
              onFocus={(e) => e.target.style.borderColor = tokens.colors.primary}
              onBlur={(e) => e.target.style.borderColor = tokens.colors.border}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.625rem 1.25rem',
              fontFamily: tokens.fonts.body,
              fontSize: '0.875rem',
              fontWeight: 600,
              color: tokens.colors.bgSecondary,
              backgroundColor: tokens.colors.primary,
              border: 'none',
              borderRadius: '2px',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'opacity 150ms ease',
            }}
          >
            {loading ? 'Pesquisando...' : 'Pesquisar'}
          </button>
        </form>
        <p
          style={{
            marginTop: '0.75rem',
            fontFamily: tokens.fonts.body,
            fontSize: '0.75rem',
            color: tokens.colors.textMuted,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {pesquisado
            ? `${plural(pagination?.total ?? 0, 'resultado', 'resultados')} para «${pesquisado}»`
            : 'A mostrar todos os deputados da história parlamentar'}
        </p>
      </div>

      {pesquisado && !loading && deputados.length === 0 && (
        <p
          style={{
            textAlign: 'center',
            padding: '2rem 1rem',
            fontFamily: tokens.fonts.body,
            fontSize: '0.9375rem',
            color: tokens.colors.textSecondary,
          }}
        >
          {`Nenhum deputado corresponde a «${pesquisado}». Pesquise por nome, sigla ou nome do partido.`}
        </p>
      )}

      {/* Deputados Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(340px, 100%), 1fr))',
          gap: '1rem',
        }}
      >
        {(deputados || []).map((deputado, index) => (
          <motion.div
            key={`${deputado.deputado_id}-${index}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03 }}
          >
            <div
              style={{
                backgroundColor: tokens.colors.bgSecondary,
                border: `1px solid ${tokens.colors.border}`,
                borderRadius: '4px',
                overflow: 'hidden',
                transition: 'border-color 150ms ease',
              }}
              onMouseEnter={(e) => e.currentTarget.style.borderColor = tokens.colors.borderStrong}
              onMouseLeave={(e) => e.currentTarget.style.borderColor = tokens.colors.border}
            >
              {/* Card Header */}
              <div style={{ padding: '1rem', borderBottom: `1px solid ${tokens.colors.border}` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
                  <div style={{ flexShrink: 0 }}>
                    {deputado.picture_url ? (
                      <img
                        src={deputado.picture_url}
                        alt={deputado.nome}
                        style={{
                          width: '56px',
                          height: '56px',
                          borderRadius: '50%',
                          objectFit: 'cover',
                          backgroundColor: '#F5F5F5',
                          border: `2px solid ${tokens.colors.border}`,
                        }}
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    ) : null}
                    <div
                      style={{
                        width: '56px',
                        height: '56px',
                        borderRadius: '50%',
                        backgroundColor: '#F0F7F4',
                        display: deputado.picture_url ? 'none' : 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        border: `2px solid ${tokens.colors.border}`,
                      }}
                    >
                      <User size={24} style={{ color: tokens.colors.primary }} />
                    </div>
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h3
                      style={{
                        fontFamily: tokens.fonts.body,
                        fontSize: '1rem',
                        fontWeight: 600,
                        color: tokens.colors.textPrimary,
                        marginBottom: '0.25rem',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {deputado.nome || deputado.nome_completo}
                    </h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span
                        style={{
                          fontFamily: tokens.fonts.body,
                          fontSize: '0.8125rem',
                          color: tokens.colors.textSecondary,
                        }}
                      >
                        {[deputado.partido_sigla, deputado.circulo].filter(Boolean).join(' · ')}
                      </span>
                      {/* Mandate Status Badge */}
                      {(() => {
                        const label = statusBadge(deputado);
                        const tone = BADGE_TONES[label];
                        return (
                          <span
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '0.125rem 0.5rem',
                              fontFamily: tokens.fonts.body,
                              fontSize: '0.6875rem',
                              fontWeight: 600,
                              textTransform: 'uppercase',
                              letterSpacing: '0.03em',
                              color: tone.color,
                              backgroundColor: tone.background,
                              borderRadius: '2px',
                            }}
                          >
                            {label}
                          </span>
                        );
                      })()}
                      {deputado.career_info?.is_multi_term && (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.125rem 0.5rem',
                            fontFamily: tokens.fonts.body,
                            fontSize: '0.6875rem',
                            fontWeight: 600,
                            color: '#92400E',
                            backgroundColor: '#FEF3C7',
                            borderRadius: '2px',
                          }}
                        >
                          <Calendar size={10} />
                          {plural(deputado.career_info.total_mandates, 'mandato', 'mandatos')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Card Body */}
              <div style={{ padding: '1rem' }}>
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.375rem',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    color: tokens.colors.textSecondary,
                    marginBottom: '0.875rem',
                  }}
                >
                  {deputado.profissao && (
                    <div>
                      <span style={{ color: tokens.colors.textMuted }}>Profissão:</span>{' '}
                      {deputado.profissao}
                    </div>
                  )}
                  <div>
                    {(() => {
                      const [label, value] = mandateSummary(deputado);
                      return (
                        <>
                          <span style={{ color: tokens.colors.textMuted }}>{label}</span> {value}
                        </>
                      );
                    })()}
                  </div>
                  {deputado.career_info?.is_multi_term && (
                    <div style={{ fontSize: '0.75rem', color: tokens.colors.primary }}>
                      <span style={{ fontWeight: 600 }}>Carreira:</span>{' '}
                      {deputado.career_info.first_mandate}–{deputado.career_info.latest_mandate}
                      {deputado.career_info.parties_served.length > 1 && (
                        <span> · Vários partidos</span>
                      )}
                    </div>
                  )}
                </div>
                <Link
                  to={`/deputados/${deputado.id_cadastro}`}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    fontFamily: tokens.fonts.body,
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                    color: tokens.colors.primary,
                    textDecoration: 'none',
                    transition: 'opacity 150ms ease',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
                  onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                >
                  Ver Detalhes
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Pagination */}
      <Pagination pagination={pagination} onPageChange={setPage} />
    </motion.div>
  )
}

// The mandate line of a card. "Mandato Atual" needs a seat held in the current legislature, even
// if suspended now: an election without a seat is not a mandate (#107), so it reads "Eleito na",
// as on the deputy page.
export const mandateSummary = (deputado) => {
  const career = deputado.career_info;
  if (career?.is_currently_active && career?.seated_in_current_legislature) {
    return ['Mandato Atual:', deputado.legislatura_nome];
  }
  if (career?.is_currently_active) return ['Eleito na', `${deputado.legislatura_nome} Legislatura`];
  const completed = career?.latest_completed_mandate;
  if (!career?.in_current_legislature && completed) {
    return ['Último mandato:', `${completed.legislatura} (${completed.periodo})`];
  }
  return ['Mandato:', deputado.legislatura_nome];
};

export default DeputadosPage
