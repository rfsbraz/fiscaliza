# API contract tests

The JSON the React app reads is the real contract of this API. Each file in
`endpoints/` pins one endpoint the frontend calls:

- `endpoint`: the path as the frontend calls it, with `{id}` or `{sigla}` placeholders.
- `route`: the Flask route that serves it today.
- `keys`: every key path a component reads. `a.b` is key `b` of object `a`, and `a[].b` is
  key `b` of each element of array `a`. Each key has a `type`, a `nullable` flag and
  `read_at`, the component file and line that reads it.
- `dropped`: fields the approved drops remove, with the reason. They are left out of
  `keys` on purpose.

Types are `object`, `array`, `mapping` (an object keyed by names, such as counts per
category), `string`, `number`, `boolean`, `scalar` (a string or number the component
renders as text) and `any`. A key is `nullable` when the component guards it (`?.`, `||`,
`&&`, a default), so it may be missing or null.

## Tests

- `test_endpoint_matches_contract`: one test per endpoint. It calls the service function
  registered in `services.py` with the fixture data source and checks the payload. Until
  an endpoint is ported to the new data layer it has no service and the test is an
  expected failure.
- The other tests check the contracts themselves: every `read_at` line really reads that
  key, every `apiFetch` call in `frontend/src` has a contract and every contract has a
  caller, every route exists, and the dropped fields stay out.

No test touches the network or a database server. Run them with
`pytest tests/contracts`.

## Changing a contract

When a component starts or stops reading a key, change the contract in the same PR.
When a port changes a response on purpose, change the contract and the component
together, and say why in the PR.
