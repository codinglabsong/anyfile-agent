# Model Card: Anyfile-Agent

Anyfile-Agent is a retrieval-based assistant that helps users search and analyze their own documents with the aid of a large language model.

## Model Details
- **Type**: Orchestrates document indexing and retrieval with calls to an external LLM (Google Gemini via `langchain-google-genai`).
- **Languages**: Primarily English; effectiveness may vary for other languages depending on the language model.
- **License**: MIT (see [LICENSE](LICENSE)).
- **Source**: <https://github.com/codinglabsong/anyfile-agent>

## Intended Use
- **Primary uses**: Searching personal documents, extracting structured summaries, and answering questions via natural language.
- **Users**: Individuals or teams who want a local assistant for their files. Requires a valid Google Gemini API key.
- **Out-of-scope uses**: Do not use the agent for generating legal, medical, or safety‑critical advice. It should not be used to process data that violates privacy regulations or third‑party terms of service.

## Data and Training
Anyfile-Agent does not train a new model. It indexes user-provided documents locally and sends text chunks to a Google Gemini model for embedding and chat responses. The quality of answers depends on that service and the content of the uploaded data.

## Evaluation
The repository provides unit tests for the indexing utilities and retrieval tools (`pytest` in the `tests/` directory). Functionality was also validated with example documents as shown in [README.md](README.md).

## Ethical Considerations
See [ETHICS.md](ETHICS.md) for guidance on responsible use and limitations. Users are responsible for complying with applicable laws and the terms of the language model service.

## Limitations
- The LLM may generate incorrect or biased outputs.
- OCR and parsing may be imperfect for some file formats.
- SQL execution is limited to read-only queries in DuckDB and may fail for complex schemas.

## Citation
If you use this project in your research or product, please cite it as:
```
@software{anyfile_agent,
  author = {codinglabsong},
  title = {Anyfile-Agent},
  year = {2025},
  url = {https://github.com/codinglabsong/anyfile-agent}
}
```