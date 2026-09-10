# arXiv preparation review — 2026-09-10

This is a local preparation and reproducibility review, not peer review,
rights clearance, or a guarantee of arXiv acceptance. The report remains a
retrospective forensic case study, not evidence that a swarm improves forecasts.

## Submission files

Use the **full technical report**, `08_paper/ecn_bench_paper.tex`. The concise
and two-column renderings are alternatives, not additional main files to upload
with the same submission.

Run from the repository root, after caching the TeX dependencies:

```sh
python tools/prepare_arxiv.py --output-dir ../artifacts/arxiv-1.2.3
```

The script refuses to overwrite an existing ZIP. Use a fresh output directory
when rebuilding a revised submission. It copies the required TeX inputs,
bibliography and 31 figures; includes the generated, correctly named `.bbl`;
and excludes PDFs, logs, auxiliary files, alternative manuscripts and datasets.
It then extracts the ZIP into a new directory and compiles it offline. Build
directories are retained beside the artifact for diagnosis, not for upload.

Upload `ECN-BENCH-arxiv-1.2.3.zip`; select `ecn_bench_paper.tex` and **XeLaTeX**
with TeX Live 2025. The local validation uses Tectonic/XeTeX, not arXiv's actual
TeX Live installation. Review arXiv's generated PDF before final submission.
The font configuration uses TeX-distributed font filenames, not system font
names. These choices follow the current
[TeX submission instructions](https://info.arxiv.org/help/submit_tex.html) and
[supported engines/font guidance](https://info.arxiv.org/help/faq/texlive.html).

For this workspace's completed preparation, use the artifact in
`../artifacts/arxiv-1.2.3/final/`, not the earlier intermediate ZIP in its parent
directory. Its SHA-256 is
`fc35212d58424e443341b39489d6af4b0831d322dc4e4cd5b01ae5e0c91a88d6`.
It has 38 members and is 4,499,908 bytes. The full PDF has 81 pages; the concise
and two-column alternatives have 12 and 9 pages. All three compile without
undefined citations, missing glyphs, font substitutions or overfull boxes.
The full report retains two nonfatal underfull-box spacing warnings.

## Citation and provenance corrections

- The shared bibliography contains 47 entries, all used by the full report.
  Model papers and model cards are distinct from citations to executable
  software and archived configurations. The concise paper cites its relevant
  subset rather than padding its bibliography with unused entries.
- Corrected Zhou et al.'s EMNLP 2024 author list and pages against
  [ACL Anthology](https://aclanthology.org/2024.emnlp-main.1208/). Narrowed the
  associated claim to information asymmetry rather than a general validation
  claim about all human behavior.
- Corrected **Mrinank Sharma** and restored **Newton Cheng** in the sycophancy
  citation using the
  [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/0105f7972202c1d4fb817da9f21a9663-Abstract-Conference.html).
- OASIS is credited separately as a paper and software. `CITATION.cff` now lists
  all 23 paper authors, not just the first author. The archive pins
  `camel-oasis==0.2.5` and `camel-ai==0.2.78`; these pins are not a claim that
  current upstream HEAD was executed.
- Added CAMEL, original MiroFish, Ollama, Neo4j, Nomic and Ministral-family
  references. These refer to primary project repositories/model cards; version
  uncertainty is explicit. A model-card citation alone cannot establish the
  exact checkpoint, quantization or serving configuration used by a hosted API.
- Removed the implication that local MiroFish project commit
  `909830f9151c26974ba4ad457f756532b9633e41` is a verified public upstream
  revision. The released `07_pipeline/backend/` is the inspectable execution
  source; the exact upstream base commit remains unestablished.
- Six ICLR/NeurIPS entries now link to the publisher's proceedings rather than
  browser-challenged OpenReview pages. Other DOI and arXiv identifiers remain
  in the shared bibliography. This review does not establish permanent future
  accessibility of every external URL.
- A final metadata pass queried primary sources for all 47 entries. Seven
  direct requests encountered certificate, anti-bot or rate-limit errors; their
  metadata was checked through publisher pages, author-hosted papers or arXiv
  instead. The pass also restored GraphRAG's two additional authors from its
  current arXiv record, expanded OASIS's BibTeX author list and aligned Gati V.
  Aher's name with PMLR. Automated metadata retrieval is not a full-text
  replication or an endorsement of each cited paper's findings.

## Scientific boundaries that must remain in the paper

The matched-evidence analysis contains 132 simulated units. Its extraction
sensitivity finding does not establish which extractor is correct. The
20-event release-date subset is not protected against evaluator knowledge
leakage. Configuration changes, wrong-event injections, unmatched payload
lengths, incomplete raw traces and unmatched serving/precision prevent strong
causal claims. Historical figures are preserved as explicitly annotated
historical diagnostics, not current inferential evidence. Offline reanalysis
does not replay model inference, the GPU pipeline or upstream services.

## GitHub and companion data

Only publish this sanitized `GITHUB-READY/ECN-BENCH` repository, not the original
workspace. The earlier source archive contains credential material; the
sanitization record is `PUBLICATION_CHANGES.json`. Pattern-based secret scanning
does not prove that no possible secret exists. Owner review and rotation of any
still-active original credentials remain necessary.

Read-only remote inspection on 2026-09-10 confirmed `main` and `v1.2.1` at
`689c9f11ede54830b5fad7f0f12e8d0fca7a7e12`, and `v1.2.2` at
`197f0875ce6a2faf8a0752c4756a4da31e389818`. Do not rewrite these tags. The local
1.2.3 preparation has not been committed, pushed or tagged by this review.
Repository visibility has not been changed. A private URL is not public data
availability; either publish the reviewed archive or retain the access caveat.

The companion trace ZIP has 1,861 files and matches the published archive
SHA-256; its ZIP CRC check passed. It is not deposited and has no public URL.
No DOI or arXiv identifier should be invented. GitHub publication and DOI
deposition are separate from submitting the manuscript.

## Author decisions before pressing Submit

1. Confirm authorship, acknowledgement and affiliation. The previously
   confirmed student number remains in the manuscript; consider removing this
   unnecessary personal identifier before public distribution.
2. Select the arXiv license and review third-party quotation/figure rights.
   `LICENSE.txt` has mixed data/code/upstream terms and does not explicitly
   enumerate `08_paper/` in its data-directory list. Do not assume that a
   dataset license settles the manuscript's distribution rights. No license
   grant has been broadened by this review.
3. Use an eligible arXiv account; complete any endorsement requested by arXiv.
   Choose the category based on scope (likely cs.AI or cs.MA; author decision).
4. Use `ARXIV_METADATA.md` for copy-ready title, author and an abridged abstract
   within arXiv's 1,920-character metadata limit; do not use the differently
   titled concise paper. Leave journal-reference and
   DOI fields empty unless real publication identifiers have been assigned.
5. Inspect the server-generated PDF, especially references, tables, historical
   captions and page breaks. Local compilation is not a substitute for this.

No submission, repository visibility change, remote write or model call was
performed as part of this preparation.

The corrected `CITATION.cff` passed validation against the official CFF 1.2.0
schema, including required authors for both software references. The offline
release verifier also checks citation keys, duplicate labels and form-abstract
length. This checks structure and consistency, not the truth of every claim.
The complete offline verifier passed all 12 tests, regenerated both JSON
results and both LaTeX tables identically, and reproduced the figure bytes.
All 1,861 trace-file hashes also matched their manifest. Re-run these checks
after any further changes; validation applies to the prepared files, not to
future edits or an untested hosted service.
