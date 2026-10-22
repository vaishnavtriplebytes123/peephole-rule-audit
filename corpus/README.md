# Initial source corpus

`jog.json` contains 26 normalized rules from JOG revision
`3011b9de21eae081448517fc77a85f4e8d5113d0`. Each record preserves its original
method, pinned URL and line, normalized pattern, semantic restrictions, and
redistribution record. The pinned checkout was read without modification.

Screening covered only `tool/src/test/java/AddNodeExample.java` and
`SubNodeExample.java`. `exclusions.json` records 94 other methods from those
two files, with reasons and source file hashes. It does not claim to screen the
entire JOG repository or identify all compatible rules. Selection was based on
supported operators and tractable guard-free syntax, before removal experiments;
this convenience subset can bias coverage and cannot represent production rules.

Normalization preserves operand order, repeated parameters, and constant
annotations. Java integer literals `-1` become the unsigned word 4294967295.
Java `x ^ -1` stays an XOR node; it is not silently converted into NOT. Constants
are matched literally; there is no implicit folding or production compiler pass.
The scope is total 32-bit value identities on trees. JOG compiler conditions,
SSA sharing, profitability, and machine runtime are outside these claims.

The checkout's Apache-2.0 license is retained in
[licenses/JOG-Apache-2.0.txt](licenses/JOG-Apache-2.0.txt). These JSON files are
modified representations, with original fragments and attribution retained.
No `NOTICE` file was found in the pinned checkout. The application checks
provenance field completeness; inclusion/source review is a separate activity.

`tests/fixtures/budget.json` and `interference.json` are constructed synthetic
fixtures. They are separate from the source corpus and must be reported separately.
