# Legal data workspace

Downloaded legal PDFs, extracted text, parsed documents, and generated corpus
artifacts are intentionally excluded from this repository.

NyayaAI uses verified legal sources and stores processed legal evidence in
PostgreSQL. The scripts under `backend/scripts/` demonstrate the ingestion,
parsing, chunking, and embedding workflows.

Before importing legal material:

1. Obtain it from an official government source.
2. Verify the title, version, publication status, and source URL.
3. Preserve source metadata and verification status.
4. Run the appropriate ingestion and validation scripts.
5. Review the resulting records before enabling them for retrieval.

The current portfolio checkpoint was evaluated with the Bharatiya Nyaya
Sanhita, 2023 and the Constitution of India. Corpus files and populated
database volumes are not distributed with the repository.
