# Research basis and claim boundaries

This record preserves the literature reviewed during presentation preparation.
It is not a claim of a new exhaustive literature search during repository setup.
The earlier source-access limitations are retained below. Before final academic
submission, recheck citations and relevant passages against the source documents.

## Research question

Can short alternative derivations guide the discovery of reproducible examples
where removal of a rule worsens the output of a bounded deterministic optimizer?
Compare guidance against random and target-pattern-only generation under matched
settings; report negative results and end-to-end costs.

## What is established and what is proposed

- JOG already includes composition machinery; its inspected artifact includes
  length-two composition. Two-step composition is not our novelty.
- Ruler and CHOMPY already address derivability-based rule selection/minimization.
- Enumo explicitly discusses useful redundancy under limits and the importance
  of scheduling. We must not claim to discover that redundant rules can help.
- Termination-checking work already studies composition, cycles and shadowing.
- Equality saturation, scheduling, shortcut generation and compact proof
  explanations are established techniques across the references below.
- CHOMPY identifies downstream performance evaluation as future work. This project
  proposes a narrower model-optimizer audit; it does not fulfill all that future work.
- Proposed contribution: paired derivation/removal witnesses, intermediate-match
  guided test generation, reduction and a controlled empirical comparison for
  a defined subset. This is an inferred research opportunity, not a verified
  claim of global novelty or an authors' verbatim proposed project.

Semantic equivalence, a realizable rewrite path, and useful operational behavior
are separate properties. A specialized derivation does not prove whole-rule
redundancy. A finite search finding no regression does not prove safe deletion.
Operator count is a structural proxy; no machine-runtime claim follows from it.

## Corpus and evaluation discipline

Maintain provenance separately for published papers and normalized rule data.
Each rule needs a source URL/revision/location, license review, semantic conversion
notes and validation result. Do not silently import LLVM undefined behavior or
Java/JIT applicability assumptions into the total bit-vector model.

Keep synthetic fixtures separate from real-corpus evidence. The constructed
A/B/C budget example and A/B/D/C loop example are teaching/test fixtures, not
published benchmark findings or new observations about production compilers.
Use per-seed raw metrics, fixed-count comparisons and explicit partial statuses.
Do not fabricate a statistically significant win or retune only the guided mode
on held-out data. Include guidance preprocessing in end-to-end timing.

## References

The previous review classified 13 papers as peer-reviewed and one as a preprint.
Optgen full text was unavailable: no specific future-work statement is attributed
to it. CHOMPY's repository title says “Using”; the reviewed PDF says “with”.

### 1. Alive

Nuno P. Lopes; David Menendez; Santosh Nagarakatte; John Regehr. **Provably Correct Peephole Optimizations with Alive**. PLDI, 2015.

[Publication / DOI](https://doi.org/10.1145/2737924.2737965) · [Source access](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/alive-pldi15.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Checks rewrite correctness with SMT; returns counterexamples.

Implication for this project: Use explicit integer semantics. Correctness alone does not measure removal cost.

Previously inspected location: Sections 2–3.

### 2. Alive-Infer

David Menendez; Santosh Nagarakatte. **Alive-Infer: Data-Driven Precondition Inference for Peephole Optimizations in LLVM**. PLDI, 2017.

[Publication / DOI](https://doi.org/10.1145/3062341.3062372) · [Source access](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/pldi2017-alive-infer.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Learns valid preconditions from examples and solver checks.

Implication for this project: Guard reasoning is established. Check applicability of each alternative step.

Previously inspected location: Section 3.

### 3. Alive2

Nuno P. Lopes; Juneyoung Lee; Chung-Kil Hur; Zhengyang Liu; John Regehr. **Alive2: Bounded Translation Validation for LLVM**. PLDI, 2021.

[Publication / DOI](https://doi.org/10.1145/3453483.3454030) · [Source access](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Validates LLVM transformations within explicit bounds.

Implication for this project: Separate semantic errors from optimization regressions; disclose bounds.

Previously inspected location: Abstract and validation design.

### 4. JOG

Zhiqiang Zang; Aditya Thimmaiah; Milos Gligoric. **Pattern-Based Peephole Optimizations with Java JIT Tests**. ISSTA, 2023.

[Publication / DOI](https://doi.org/10.1145/3597926.3598038) · [Source access](https://users.ece.utexas.edu/~gligoric/papers/ZhiqiangETAL23Jog.pdf)

Prior review status: Peer-reviewed; author full text and pinned artifact reviewed.

Relevant method: Java pattern tooling and shadow analysis; artifact includes two-rule composition.

Implication for this project: Retain composition as a building block. Add a measured removal audit.

Previously inspected location: Section 5.5; artifact commit 3011b9d.

### 5. Loop checking

David Menendez; Santosh Nagarakatte. **Termination-Checking for LLVM Peephole Optimizations**. ICSE, 2016.

[Publication / DOI](https://doi.org/10.1145/2884781.2884809) · [Source access](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/icse2016-alive-loops.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Composes rules and generates inputs that expose rewrite cycles.

Implication for this project: Cycles and shadowing are known. Focus on per-rule removal and output cost.

Previously inspected location: Sections 3–5; shadowing discussion and Figure 14.

### 6. Optgen

Sebastian Buchwald. **Optgen: A Generator for Local Optimizations**. CC, 2015.

[Publication / DOI](https://doi.org/10.1007/978-3-662-46663-6_9) · [Source access](https://pp.ipd.kit.edu/uploads/publikationen/buchwald15cc.pdf)

Prior review status: Peer-reviewed; metadata and indexed introduction reviewed. Full PDF retrieval failed; no future-work claim attributed.

Relevant method: Generates local rules within a cost limit and tests for missed optimizations.

Implication for this project: Use bounded expressions and cost-based tests. Only partial text accessible.*

Previously inspected location: Publisher abstract and indexed introduction only.

### 7. Ruler

Chandrakana Nandi; Max Willsey; Amy Zhu; Yisu Remy Wang; Brett Saiki; Adam Anderson; Adriana Schulz; Dan Grossman; Zachary Tatlock. **Rewrite Rule Inference Using Equality Saturation**. OOPSLA, 2021.

[Publication / DOI](https://doi.org/10.1145/3485496) · [Source access](https://cnandi.com/docs/oopsla21-cr.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Synthesizes rules and removes candidates derivable from other rules.

Implication for this project: Derivability-based minimization already exists. It cannot be our novelty.

Previously inspected location: Rule selection/minimization and derivability evaluation.

### 8. Enumo

Anjali Pal; Brett Saiki; Ryan Tjoa; Cynthia Richey; Amy Zhu; Oliver Flatt; Max Willsey; Zachary Tatlock; Chandrakana Nandi. **Equality Saturation Theory Exploration à la Carte**. OOPSLA2, 2023.

[Publication / DOI](https://doi.org/10.1145/3622834) · [Source access](https://rtjoa.com/papers/oopsla23-enumo.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Programmable rule inference, minimization and fast-forwarding rules.

Implication for this project: Explicit: redundancy can help under limits; scheduling remains important.

Previously inspected location: Sections 4.3, 5 and 7.

### 9. CHOMPY

Andrew Cheung; Chandrakana Nandi; Sorin Lerner. **Conditional Rewrite Rule Synthesis Using E-Graphs and Implication Propagation**. FMCAD, 2026.

[Publication / DOI](https://doi.org/10.34727/2026/isbn.978-3-85448-093-8_43) · [Source access](https://repositum.tuwien.at/handle/20.500.12708/230508)

Prior review status: Peer-reviewed, September 2026; version of record reviewed. Repository title says “Using”; PDF title says “with”.

Relevant method: Synthesizes conditional rules; uses implication-aware derivability to minimize.

Implication for this project: Explicit: downstream performance is future work. Audit individual deletions.

Previously inspected location: Sections IV-A and V-B/C; PDF pp. 5–6.

### 10. Equality saturation

Ross Tate; Michael Stepp; Zachary Tatlock; Sorin Lerner. **Equality Saturation: A New Approach to Optimization**. POPL, 2009.

[Publication / DOI](https://doi.org/10.1145/1480881.1480915) · [Source access](https://www.cs.cornell.edu/~lerner/papers/popl09.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Retains equivalent alternatives before choosing a profitable program.

Implication for this project: Phase ordering is established. Our MVP models a deterministic rewrite engine.

Previously inspected location: Introduction and optimization framework.

### 11. egg

Max Willsey; Chandrakana Nandi; Yisu Remy Wang; Oliver Flatt; Zachary Tatlock; Pavel Panchekha. **egg: Fast and Extensible Equality Saturation**. POPL, 2021.

[Publication / DOI](https://doi.org/10.1145/3434304) · [Source access](https://homes.cs.washington.edu/~cnandi/docs/popl21-cr.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Efficient e-graphs, analyses, extraction and configurable rule scheduling.

Implication for this project: Schedulers already control expensive rules. Record the schedule as test input.

Previously inspected location: Section 5.2, especially backoff scheduling.

### 12. Isaria

Samuel Thomas; James Bornholt. **Automatic Generation of Vectorizing Compilers for Customizable Digital Signal Processors**. ASPLOS, 2024.

[Publication / DOI](https://doi.org/10.1145/3617232.3624873) · [Source access](https://sgt-pl.com/papers/compgen.pdf)

Prior review status: Peer-reviewed; author full text reviewed.

Relevant method: Synthesizes vectorizing compilers with rule phases and greedy pruning.

Implication for this project: Explicit: pruning sacrifices completeness. Include scheduler-sensitive cases.

Previously inspected location: Sections 3.3, 5.2 and 7.1.

### 13. Small Proofs

Oliver Flatt; Samuel Coward; Max Willsey; Zachary Tatlock; Pavel Panchekha. **Small Proofs from Congruence Closure**. FMCAD, 2022.

[Publication / DOI](https://doi.org/10.34727/2022/isbn.978-3-85448-053-2_13) · [Source access](https://par.nsf.gov/servlets/purl/10403946)

Prior review status: Peer-reviewed; full text reviewed.

Relevant method: Builds compact, checkable explanations of equality reasoning.

Implication for this project: Explainable proofs are established. Pair a derivation with a removal regression.

Previously inspected location: Abstract, proof algorithms and egg implementation.

### 14. KBC augmentation

Michael Schifferer; Marcel Ullrich; Sebastian Hack. **Augmenting Rewrite Rule Sets via Knuth-Bendix Completion**. arXiv preprint, 2026.

[Publication / DOI](https://doi.org/10.48550/arXiv.2610.01246) · [Source access](https://arxiv.org/abs/2610.01246)

Prior review status: Preprint, 1 October 2026; full text reviewed. No peer-reviewed venue verified.

Relevant method: Adds completion-derived rules, including shortcuts, and evaluates rewriting.

Implication for this project: Useful shortcut rules are also studied here. Do not claim that insight as new.

Previously inspected location: Sections 3, 5 and 6.

## Pinned JOG artifact

Previously inspected revision: `3011b9de21eae081448517fc77a85f4e8d5113d0`.
[PatternRelation.java](https://github.com/EngineeringSoftware/jog/blob/3011b9de21eae081448517fc77a85f4e8d5113d0/tool/src/main/java/jog/shadow/PatternRelation.java)
contains the composition analysis considered in the prior review. Verify any
implementation-specific statement against this revision rather than an unpinned
current branch. The existing local checkout is reference material, not application code.

## Implementation-stage source rechecks — 2026-10-23

This is a targeted recheck, not a new exhaustive search or a claim that all 14
papers were reread in full during implementation.

- [Alive author PDF](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/alive-pldi15.pdf): abstract confirms automated correctness checks/counterexamples and LLVM-specific semantic concerns.
- [JOG author PDF](https://users.ece.utexas.edu/~gligoric/papers/ZhiqiangETAL23Jog.pdf): shadow analysis and structure-sensitive matching rechecked, PDF pp. 5–6. Artifact-composition claims still refer to the separately pinned revision above.
- [Ruler author PDF](https://cnandi.com/docs/oopsla21-cr.pdf): candidate removal by derivability rechecked around `choose_eqs`/Figure 5, PDF p. 11.
- [Enumo author PDF](https://rtjoa.com/papers/oopsla23-enumo.pdf): useful redundancy under resource limits in Section 4.3 and scheduling limitations in Section 7 rechecked. This project cannot claim either observation as new.
- [CHOMPY version-of-record repository](https://repositum.tuwien.at/handle/20.500.12708/230508): full PDF retrieved through its full-text link; title discrepancy confirmed. PDF Section V-B/C explicitly leaves downstream performance evaluation for future work. Our deterministic tree model is narrower than that general task.
- [KBC preprint PDF](https://arxiv.org/pdf/2610.01246): shortcut categorization in Section 3 and remaining bit-vector-domain work in Section 6.1 rechecked. It remains a preprint in this record.
- Optgen's direct author-PDF request timed out again. Retain the existing limited-access qualification; no specific future-work claim is added.

The remaining references were checked in the same implementation-stage pass:

- [Alive-Infer](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/pldi2017-alive-infer.pdf) and [Alive2](https://users.cs.utah.edu/~regehr/alive2-pldi21.pdf): author PDFs retrieved; abstracts confirm example-based precondition inference and bounded translation validation respectively. Neither capability is claimed as a new result here.
- [Termination checking](https://people.cs.rutgers.edu/~santosh.nagarakatte/papers/icse2016-alive-loops.pdf): author PDF retrieved; abstract confirms composition/undo cycles and concrete debugging inputs as prior work.
- [Equality saturation](https://www.cs.cornell.edu/~lerner/papers/popl09.pdf): author PDF retrieved; abstract/introduction confirm nondestructive alternatives followed by extraction, distinct from this project's first-match tree runner.
- [egg](https://homes.cs.washington.edu/~cnandi/docs/popl21-cr.pdf): author PDF retrieved; scheduling/backoff discussion rechecked at PDF p. 20.
- [Isaria](https://sgt-pl.com/papers/compgen.pdf): author PDF retrieved; pruning/completeness trade-off rechecked at PDF pp. 2 and 8.
- [Small Proofs author PDF](https://ztatlock.net/pubs/2022-fmcad-smallproofs/2022-fmcad-smallproofs.pdf): retrieved after the NSF mirror returned 502. Abstract/introduction confirm compact congruence explanations as prior work; no new proof-minimization algorithm is claimed here.
- [Optgen institutional record](https://pp.ipd.kit.edu/publication.php?id=buchwald15cc&lang=en): title/author/CC-2015 metadata verified; direct PDF timeout and inaccessible publisher DOI remain access limits.

In total, 13 full-text PDFs were retrieved and relevant passages/abstracts
checked; Optgen remained metadata/previous-introduction access only. This is not
a claim of a new page-by-page rereading or an exhaustive novelty search.
