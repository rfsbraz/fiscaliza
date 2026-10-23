import { useHealth } from '../config/health';
import { formatDate } from '../utils/format';

const AR_TERMS_URL = 'https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx';
const REPO_URL = 'https://github.com/rfsbraz/parlamento-aberto';
const RELEASES_URL = `${REPO_URL}/releases/tag/`;
const CC_BY_URL = 'https://creativecommons.org/licenses/by/4.0/deed.pt';

const textStyle = {
  fontFamily: "'Source Sans 3', sans-serif",
  fontSize: '0.8125rem',
  color: '#4A4A4A',
  textAlign: 'center',
  margin: 0,
};

const linkStyle = { color: '#1B4332', textDecoration: 'underline' };

// The attribution the AR terms and Lei n.º 26/2016, art. 19.º, n.º 5 ask for: the source and
// the date of the last update (source_updated of the live parlamento-aberto release), as dd/mm/aaaa.
// The tag links its GitHub release only when it is published (#186); a local build of the pin has
// a tag GitHub doesn't know, so it links the repository instead.
export const AttributionView = ({ release }) => {
  const sourceUpdated = formatDate(release?.source_updated);
  const tag = release?.tag;
  const tagUrl = release?.publicado ? `${RELEASES_URL}${tag}` : REPO_URL;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.25rem', paddingTop: '1.25rem' }}>
      <p style={textStyle}>
        <a href={AR_TERMS_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
          {sourceUpdated
            ? `Fonte: Assembleia da República, dados abertos, atualizados a ${sourceUpdated}.`
            : 'Fonte: Assembleia da República, dados abertos.'}
        </a>
      </p>
      <p style={{ ...textStyle, fontSize: '0.75rem', color: '#6B6B6B' }}>
        Dados tratados por{' '}
        {tag ? (
          <a href={tagUrl} target="_blank" rel="noopener noreferrer" style={linkStyle}>
            parlamento-aberto ({tag})
          </a>
        ) : (
          'parlamento-aberto'
        )}
        , sob{' '}
        <a href={CC_BY_URL} target="_blank" rel="noopener noreferrer" style={linkStyle}>
          CC BY 4.0
        </a>
        .
      </p>
    </div>
  );
};

const DataAttribution = () => <AttributionView release={useHealth()} />;

export default DataAttribution;
