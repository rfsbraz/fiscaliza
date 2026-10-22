# Contratos da API

O JSON que a aplicação React lê é o verdadeiro contrato desta API. Cada ficheiro em
`endpoints/` fixa um endpoint que o frontend chama:

- `endpoint`: o caminho como o frontend o chama, com `{id}` ou `{sigla}` no lugar dos valores.
- `route`: a rota Flask que o serve hoje.
- `keys`: todos os caminhos de chave que um componente lê. `a.b` é a chave `b` do objeto `a`, e
  `a[].b` é a chave `b` de cada elemento do array `a`. Cada chave tem um `type`, uma flag
  `nullable` e `read_at`, o ficheiro e a linha do componente que a lê.
- `dropped`: campos que as remoções aprovadas tiram, com o motivo. Ficam de fora de `keys` de
  propósito.

Os tipos são `object`, `array`, `mapping` (um objeto com nomes como chaves, como contagens por
categoria), `string`, `number`, `boolean`, `scalar` (uma string ou um número que o componente
mostra como texto) e `any`. Uma chave é `nullable` quando o componente a protege (`?.`, `||`,
`&&`, um valor por omissão), por isso pode faltar ou ser null.

## Testes

- `test_endpoint_matches_contract`: um teste por endpoint. Chama a função de serviço registada
  em `services.py` com a fonte de dados de teste (uma pequena release sintética em
  `tests/site_data.py`, sincronizada para um ficheiro DuckDB) e verifica a resposta. Enquanto um
  endpoint não passar para a nova camada de dados, não tem serviço e o teste é uma falha
  esperada.
- Os outros testes verificam os próprios contratos: cada linha `read_at` lê mesmo essa chave,
  cada chamada `apiFetch` em `frontend/src` tem um contrato e cada contrato tem quem o chame,
  cada rota existe, e os campos removidos continuam de fora.

Nenhum teste usa a rede nem um servidor de base de dados. Corra-os com `pytest tests/contracts`.

## Alterar um contrato

Quando um componente começa ou deixa de ler uma chave, altere o contrato no mesmo pull request.
Quando uma migração muda uma resposta de propósito, altere o contrato e o componente em conjunto,
e explique porquê no pull request.
