# Ethics Statement

Anyfile-Agent helps users explore their local documents with the assistance of an external language model. I designed the software with the following principles:

- **User Control and Privacy** – Files remain on the local machine. Processing uses open-source libraries and the configured language model API. No uploaded content is sent elsewhere by the application.
- **Transparency** – Indexing creates temporary representations of the documents (e.g., embeddings, OCR text) so the agent can search them. These artifacts are stored locally and users may delete them at any time.
- **Responsible Use** – The agent can generate or execute SQL queries over the user’s data. Only read-only commands are permitted, but users should review outputs before acting on them. Do not rely on the agent for legal, medical, or safety-critical decisions.
- **Bias and Limitations** – Responses may reflect biases of the underlying language model or the provided data. Users should validate critical information from original sources.
- **Open Development** – The project is MIT licensed so that others may inspect, modify, and improve the code. Contributions must follow these ethical guidelines.

By using this project you agree to handle any personal or sensitive data responsibly and comply with applicable laws and terms of the language model service.