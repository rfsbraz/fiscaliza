# Segurança

## Como reportar

Não abra uma issue pública para reportar uma vulnerabilidade ou uma fuga de dados.

Use o reporte privado de vulnerabilidades do GitHub:

1. Abra o separador **Security** deste repositório.
2. Carregue em **Report a vulnerability**.
3. Descreva o problema, onde o encontrou e, se possível, como o reproduzir.

Ligação direta: <https://github.com/rfsbraz/parliament/security/advisories/new>

O reporte fica visível apenas para quem mantém o repositório.

## O que reportar por esta via

- Vulnerabilidades no código do site, nos cabeçalhos de segurança (`deploy/_headers`), nos workflows do GitHub Actions ou nas dependências.
- Um segredo ou token publicado no repositório ou no histórico.
- Dados pessoais que o site mostra e não devia: por exemplo uma morada, contactos, o motivo de uma falta ou elementos dos separadores 2 (dados pessoais) ou 3 (rendimentos e património) de uma declaração da Entidade para a Transparência.

Não copie o dado pessoal para o reporte. Indique a página, o ficheiro ou o commit e o identificador do registo.

## Correções de dados

Um número errado não é uma vulnerabilidade. Se o erro está nos dados de origem, use o formulário [Correção de dados](https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml) do parlamento-aberto. Se os dados estão certos e o site os mostra mal, abra uma issue aqui com o formulário "Número errado no site".

## Versões suportadas

Só o ramo `master`, que é o que está publicado em [fiscaliza.pt](https://fiscaliza.pt), recebe correções.
