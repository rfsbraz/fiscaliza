/**
 * A short plain explanation of the phase of a plenary vote (#191), next to the phase as the AR
 * names it. Phases with no entry get none: the page shows the AR's name and nothing guessed.
 */
const NOTES = {
  'Votação na generalidade':
    'Na generalidade, o Plenário vota o princípio da iniciativa. Se for aprovada, o texto segue para a especialidade, artigo a artigo, e só fica aprovado na votação final global.',
  'Votação na especialidade':
    'Na especialidade vota-se o texto por partes, artigo a artigo ou proposta a proposta. A decisão sobre o texto inteiro fica para a votação final global.',
  'Votação final global':
    'A votação final global aprova ou rejeita o texto inteiro, depois da generalidade e da especialidade.',
  'Votação final':
    'Votação que decide a iniciativa de uma só vez, sem generalidade e especialidade, como é habitual nos projetos de resolução.',
  'Votação global': 'Votação única do texto inteiro, como nas propostas de resolução que aprovam tratados.',
  'Baixa comissão especialidade':
    'Votação sobre enviar a iniciativa a uma comissão parlamentar, para o texto ser trabalhado na especialidade.',
  'Requerimento avocação plenário':
    'Votação sobre um pedido para o Plenário chamar a si a votação na especialidade de partes do texto que estavam a ser votadas em comissão.',
};

export const phaseNote = (phase) => (phase && NOTES[phase]) || null;
