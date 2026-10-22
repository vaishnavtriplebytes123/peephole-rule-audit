# Expression format (schema version 1)

M1 defines runtime expressions only. Rules, guards, configuration, and witness
schemas belong to their later milestones.

An expression file is a UTF-8 JSON object with exactly these fields:

```json
{
  "schema_version": 1,
  "expression": {
    "op": "add",
    "args": [{"op": "var", "name": "x"}, {"op": "const", "value": 1}]
  }
}
```

Nodes use `op`. A `var` has only `name`; a `const` has only `value`.
`not` has one entry in `args`; `add`, `sub`, `and`, `or`, and `xor` have two.
Argument order is significant. No folding or commutative canonicalization occurs.

Constants and evaluation bindings are integers from 0 through 4294967295;
booleans and floating-point values are rejected. Names match
`[A-Za-z_][A-Za-z0-9_]*` and contain at most 64 ASCII characters. Arithmetic and
bitwise results are masked to 32 bits. Variable bindings are explicit; a missing
binding is an error.

Input ceilings are 10 MiB of UTF-8, 1,000 expression nodes, and depth 64. Root
depth is 1. Repeated subtrees count at each occurrence. Library callers may
select lower positive limits. Duplicate keys, unknown fields, unsupported versions,
non-finite numbers, malformed UTF-8 and invalid node types fail with an input
path and reason. Additional JSON container nesting is bounded before node decoding.

Canonical encoding sorts object keys, uses compact separators and ASCII escapes,
and rejects non-finite numbers. It has no trailing newline. Content hashes are
SHA-256 of those bytes. Hashing does not change expression structure.

`measure` returns `(nodes, depth, operators)`. Constants and variables cost zero;
each unary/binary operator costs one. This cost is unrelated to CPU runtime.

M1 exposes these contracts through the typed Python API (`ruleaudit.ir` and
`ruleaudit.io`). Only CLI help/version are available at this milestone.
