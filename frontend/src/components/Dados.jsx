import { useEffect, useState } from 'react';
import { Download, ExternalLink, FileText } from 'lucide-react';
import { apiFetch } from '../config/api';
import { formatDate } from '../utils/format';
import { tokens } from '../styles/tokens';
import { LoadingSpinner } from './common';

/**
 * /dados (#186): the files of the live parlamento-aberto release, from dados.json (the release's
 * manifest.json with the real size of each file). Only a release published on GitHub has
 * download links; a local build of the pin lists its files and says it is not published yet.
 */
const { colors, fonts } = tokens;
const REPO = 'https://github.com/rfsbraz/parlamento-aberto';
const CC_BY_URL = 'https://creativecommons.org/licenses/by/4.0/deed.pt';
const LICENSE_DATA_URL = `${REPO}/blob/main/LICENSE-DATA`;
const DICT_URL = `${REPO}/tree/main/docs/dictionary`;
const EPT_GROUP = 'Interesses declarados';

export const GROUPS = [
  ['Deputados e mandatos', [
    ['deputies', 'Deputados, um por registo da AR'],
    ['mandates', 'Mandatos por legislatura e círculo'],
    ['group_memberships', 'Pertença a grupos parlamentares'],
  ]],
  ['Votações', [
    ['votes', 'Votações em plenário'],
    ['vote_group_positions', 'Sentido de voto de cada grupo'],
    ['vote_deputy_dissents', 'Votos de deputados contra o seu grupo'],
    ['initiative_votes', 'Ligação entre votações e iniciativas'],
  ]],
  ['Iniciativas, intervenções e perguntas', [
    ['initiatives', 'Iniciativas legislativas'],
    ['initiative_authors', 'Autores de cada iniciativa'],
    ['interventions', 'Intervenções em plenário'],
    ['questions', 'Perguntas e requerimentos ao Governo'],
    ['question_authors', 'Autores de cada pergunta'],
    ['question_recipients', 'Destinatários de cada pergunta'],
  ]],
  ['Presenças', [
    ['plenary_attendance', 'Presença de cada deputado em cada reunião plenária'],
    ['plenary_attendance_summary', 'Presenças e faltas por deputado e legislatura'],
  ]],
  ['Eleições e referência', [
    ['ballot_list_seats', 'Lugares por lista e círculo, 1979 a 2025'],
    ['ballot_list_elected', 'Deputados eleitos por lista e círculo, 1979 a 1991'],
    ['coalitions', 'Coligações e partidos que as compõem'],
    ['parliamentary_groups', 'Grupos parlamentares'],
    ['electoral_circles', 'Círculos eleitorais'],
    ['legislatures', 'Legislaturas'],
    ['sessions', 'Sessões legislativas'],
  ]],
  [EPT_GROUP, [
    ['interest_declarations', 'Declarações de interesses'],
    ['interests', 'Interesses de cada declaração'],
  ]],
];

/** The release's sets in the page's groups, in the GROUPS order; a set GROUPS doesn't know goes last. */
export const groupSets = (sets) => {
  const byName = new Map(sets.map((s) => [s.nome, s]));
  const known = new Set();
  const groups = GROUPS.map(([title, items]) => [
    title,
    items
      .filter(([name]) => byName.has(name))
      .map(([name, desc]) => {
        known.add(name);
        return { ...byName.get(name), descricao: desc };
      }),
  ]);
  const rest = sets.filter((s) => !known.has(s.nome)).map((s) => ({ ...s, descricao: s.nome }));
  return [...groups, ['Outros conjuntos', rest]].filter(([, items]) => items.length > 0);
};

/** A file size as the page shows it: MB with one decimal, or kB. */
export const fileSize = (bytes) => {
  if (bytes == null) return '';
  return bytes >= 1e6
    ? `${(bytes / 1e6).toLocaleString('pt-PT', { maximumFractionDigits: 1 })} MB`
    : `${Math.max(1, Math.round(bytes / 1e3)).toLocaleString('pt-PT')} kB`;
};
const n = (x) => (x == null ? '' : x.toLocaleString('pt-PT'));

const css = `
  .dados-row { display: grid; grid-template-columns: minmax(0, 1fr) 7rem 7.5rem 7.5rem; gap: 1rem; align-items: center; padding: 0.625rem 0; border-top: 1px solid ${colors.border}; }
  .dados-head { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: ${colors.textMuted}; border-top: none; padding-bottom: 0.25rem; }
  .dados-rows { text-align: right; font-variant-numeric: tabular-nums; }
  .dados-label-mobile { display: none; }
  .dados-top { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 1.25rem; }
  @media (max-width: 640px) {
    .dados-row { grid-template-columns: 1fr 1fr; gap: 0.375rem 0.75rem; }
    .dados-row > :first-child { grid-column: 1 / -1; }
    .dados-head { display: none; }
    .dados-rows { display: none; }
    .dados-label-mobile { display: inline; }
    .dados-top { grid-template-columns: 1fr; }
    .dados-page { padding: 1.75rem 1rem 3rem !important; }
    .dados-card { padding: 1rem 1.125rem !important; }
    .dados-page h1 { font-size: 1.875rem !important; }
  }
`;

const fileStyle = { display: 'inline-flex', alignItems: 'center', gap: '0.375rem', color: '#1B4332', fontWeight: 600, textDecoration: 'none', fontSize: '0.875rem', fontVariantNumeric: 'tabular-nums' };
const card = { backgroundColor: colors.bgSecondary, border: `1px solid ${colors.borderWarm}`, borderRadius: 8, padding: '1.25rem 1.5rem' };
const h2 = { fontFamily: fonts.headline, fontSize: '1.25rem', fontWeight: 700, color: colors.textPrimary, margin: '0 0 0.5rem 0' };
const p = { fontFamily: fonts.body, fontSize: '0.9375rem', lineHeight: 1.6, color: colors.textSecondary, margin: '0 0 0.75rem 0' };
const link = { color: '#1B4332', textDecoration: 'underline' };

/** One file of a set: a download link when the release is published, else its size only. */
const FileCell = ({ file, label }) => {
  if (!file) return <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>{label}: sem ficheiro</span>;
  const size = <span style={{ fontWeight: 400, color: colors.textMuted }}>{fileSize(file.bytes)}</span>;
  if (!file.url) {
    return (
      <span style={{ ...fileStyle, color: colors.textSecondary, fontWeight: 400 }}>
        {label} {size}
      </span>
    );
  }
  return (
    <a href={file.url} style={fileStyle}>
      <Download size={14} aria-hidden="true" />
      {label} {size}
    </a>
  );
};

export const DadosView = ({ dados }) => {
  const tag = dados.tag;
  const published = dados.publicado;
  const updated = formatDate(dados.source_updated);
  const sets = dados.conjuntos || [];
  const manifest = dados.manifest;
  const cc = sets.filter((s) => s.cc_by).length;

  return (
    <article className="dados-page" style={{ maxWidth: '1040px', margin: '0 auto', padding: '2.5rem 1.5rem 4rem', fontFamily: fonts.body }}>
      <style>{css}</style>
      <h1 style={{ fontFamily: fonts.headline, fontSize: '2.25rem', fontWeight: 700, color: colors.textPrimary, margin: '0 0 0.75rem 0' }}>
        Descarregar dados
      </h1>
      <p style={{ ...p, fontSize: '1.0625rem', maxWidth: '46rem', marginBottom: '1.75rem' }}>
        Todos os números do Fiscaliza saem destes ficheiros. São os dados abertos da Assembleia da
        República, tratados pelo parlamento-aberto e publicados numa release com cada atualização.
        Pode descarregá-los para verificar as contas ou reutilizá-los.
      </p>

      <div className="dados-top" style={{ marginBottom: '2rem' }}>
        <section className="dados-card" style={card}>
          <h2 style={h2}>Release {tag}</h2>
          <p style={p}>
            {updated && (
              <>
                Dados da AR atualizados a <strong style={{ color: colors.textPrimary }}>{updated}</strong>.{' '}
              </>
            )}
            {sets.length} conjuntos, cada um em Parquet e em CSV comprimido (gzip), com{' '}
            {fileSize(dados.total_parquet)} em Parquet
            {dados.total_csv > 0 && ` e ${fileSize(dados.total_csv)} em CSV`}.
          </p>
          {!published && (
            <p style={{ ...p, color: colors.textPrimary }}>
              Esta versão dos dados ainda não está publicada no GitHub. As ligações para descarregar
              aparecem aqui quando a release for publicada.
            </p>
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
            {published && dados.release_url && (
              <a
                href={dados.release_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', backgroundColor: colors.primary, color: '#fff', padding: '0.5rem 0.875rem', borderRadius: 6, fontWeight: 600, fontSize: '0.9375rem', textDecoration: 'none' }}
              >
                Ver a release no GitHub <ExternalLink size={15} aria-hidden="true" />
              </a>
            )}
            {manifest?.url && (
              <a href={manifest.url} style={{ ...link, fontSize: '0.9375rem', display: 'inline-flex', alignItems: 'center', gap: '0.375rem' }}>
                <FileText size={15} aria-hidden="true" /> manifest.json ({fileSize(manifest.bytes)})
              </a>
            )}
            <a href={DICT_URL} target="_blank" rel="noopener noreferrer" style={{ ...link, fontSize: '0.9375rem' }}>
              Dicionário de dados
            </a>
          </div>
        </section>

        <section className="dados-card" style={{ ...card, backgroundColor: colors.bgWarm }}>
          <h2 style={h2}>Licença</h2>
          <p style={p}>
            {cc} dos {sets.length} conjuntos estão sob a{' '}
            <a href={CC_BY_URL} target="_blank" rel="noopener noreferrer" style={link}>CC BY 4.0</a>.
            Pode reutilizá-los, também para fins comerciais, desde que cite a fonte:
          </p>
          <p style={{ ...p, fontSize: '0.875rem', backgroundColor: colors.bgSecondary, border: `1px solid ${colors.borderWarm}`, borderRadius: 6, padding: '0.625rem 0.75rem', color: colors.textPrimary }}>
            Fonte: Assembleia da República, dados abertos{updated ? `, atualizados a ${updated}` : ''}. Dados
            tratados por parlamento-aberto ({tag}), CC BY 4.0.
          </p>
          <p style={{ ...p, fontSize: '0.8125rem', margin: 0, color: colors.textMuted }}>
            Os dados da AR seguem os termos da AR. Todas as regras em{' '}
            <a href={LICENSE_DATA_URL} target="_blank" rel="noopener noreferrer" style={link}>LICENSE-DATA</a>.
          </p>
        </section>
      </div>

      {groupSets(sets).map(([title, items]) => (
        <section key={title} style={{ marginBottom: '1.75rem' }}>
          <h2 style={{ ...h2, fontSize: '1.0625rem' }}>{title}</h2>
          <div className="dados-row dados-head">
            <span>Conjunto</span><span className="dados-rows">Linhas</span><span>Parquet</span><span>CSV</span>
          </div>
          {items.map((s) => (
            <div key={s.nome} className="dados-row" data-set={s.nome}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '0.9375rem', color: colors.textPrimary }}>
                  {s.descricao}
                  {!s.cc_by && (
                    <span
                      title={s.licenca}
                      style={{ marginLeft: '0.5rem', fontSize: '0.75rem', fontWeight: 600, color: colors.statusAmber, backgroundColor: colors.statusAmberBg, border: `1px solid ${colors.statusAmberBorder}`, borderRadius: 4, padding: '0.0625rem 0.375rem', whiteSpace: 'nowrap' }}
                    >
                      Fora da CC BY 4.0
                    </span>
                  )}
                </div>
                <code style={{ fontSize: '0.8125rem', color: colors.textMuted }}>{s.nome}</code>
                <span className="dados-label-mobile" style={{ fontSize: '0.8125rem', color: colors.textMuted }}> · {n(s.linhas)} linhas</span>
              </div>
              <span className="dados-rows" style={{ fontSize: '0.875rem', color: colors.textSecondary }}>{n(s.linhas)}</span>
              <FileCell file={s.parquet} label="Parquet" />
              <FileCell file={s.csv} label="CSV" />
            </div>
          ))}
          {title === EPT_GROUP && (
            <p style={{ ...p, fontSize: '0.8125rem', color: colors.textMuted, margin: '0.5rem 0 0 0' }}>
              Os elementos públicos do registo de interesses dos Deputados da XVI e da XVII são
              republicados com indicação da Entidade para a Transparência (EpT) como fonte, ao abrigo
              da Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1.
              Fica excluído apenas o NIF dos titulares. Estes dois conjuntos têm regras próprias,
              descritas no ponto 3 da LICENSE-DATA.
            </p>
          )}
        </section>
      ))}
    </article>
  );
};

const Dados = () => {
  const [dados, setDados] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const title = document.title;
    document.title = 'Descarregar dados · Fiscaliza';
    let live = true;
    apiFetch('dados')
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
      })
      .then((body) => live && setDados(body))
      .catch(() => live && setError('Não foi possível carregar a lista de ficheiros. Tente de novo mais tarde.'));
    return () => {
      live = false;
      document.title = title;
    };
  }, []);

  if (error) {
    return <p style={{ fontFamily: fonts.body, color: colors.textSecondary, textAlign: 'center', padding: '3rem 1rem' }}>{error}</p>;
  }
  if (!dados) return <LoadingSpinner message="A carregar os ficheiros dos dados" />;
  return <DadosView dados={dados} />;
};

export default Dados;
