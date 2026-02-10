# Docs Chunk - RAG-Enhanced Documentation Management System

Docs Chunk is a comprehensive solution for managing technical documentation with built-in RAG (Retrieval-Augmented Generation) capabilities. It allows you to host MkDocs projects and interact with them using natural language queries, powered by vector search and knowledge graphs.

## 🚀 Key Features

*   **Documentation Hosting**: distinct hosting for multiple MkDocs projects.
*   **Intelligent Search (RAG)**: Ask questions about your documentation and get context-aware answers.
*   **Hybrid Storage**: Utilizes **Qdrant** for vector embeddings and **Neo4j** for knowledge graph relationships.
*   **Modern UI**: Built with React (Vite), Tailwind CSS, and Radix UI.
*   **Observability**: Integrated monitoring stack with Prometheus, Grafana, Loki, and Promtail.
*   **LLM Flexibility**: Support for OpenAI and local models via Ollama.

## 🛠 Tech Stack

*   **Frontend**: React, Vite, Tailwind CSS, Radix UI
*   **Backend**: Node.js, Express, Sequelize, PostgreSQL
*   **AI/RAG Service**: Python, FastAPI, LightRAG, LangChain/LlamaIndex concepts
*   **Databases**: PostgreSQL (Relational), Qdrant (Vector), Neo4j (Graph)
*   **Infrastructure**: Docker Compose

## 📋 Prerequisites

*   [Docker](https://www.docker.com/products/docker-desktop) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.
*   Git

## 🔧 Installation & Setup

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd docs-chunk
    ```

2.  **Environment Configuration**
    
    The project uses `docker-compose.yml` for service orchestration. 
    
    *   Open `docker-compose.yml`.
    *   Locate the `rag_service` section.
    *   Set your `OPENAI_API_KEY` if using OpenAI models.
    
    ```yaml
   rag_service:
      environment:
        - OPENAI_API_KEY=your_api_key_here
    ```

3.  **Build and Run**
    
    Start the entire stack using Docker Compose:
    
    ```bash
    docker-compose up --build -d
    ```

    This command will build the frontend, backend, and RAG service images and start all containers including databases and monitoring tools.

## 🏃‍♂️ Usage

Once everything is up and running, you can access the following services:

| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend** | `http://localhost:3000` | Main user interface |
| **Backend API** | `http://localhost:3001` | Node.js API |
| **RAG Service API** | `http://localhost:8000` | Python AI Service (FastAPI) |
| **Neo4j Browser** | `http://localhost:7474` | Graph Database UI (Auth: `neo4j`/`password`) |
| **Grafana** | `http://localhost:3002` | Monitoring Dashboards (Auth: `admin`/`admin`) |

### Uploading Documentation

1.  Navigate to `http://localhost:3000`.
2.  Use the upload feature to submit your MkDocs project (zip file).
3.  The backend will handle extraction and hosting.

### Querying Documentation

1.  Go to the Search/Chat interface in the frontend.
2.  Type your question regarding the uploaded documentation.
3.  The RAG service will retrieve relevant context from Qdrant/Neo4j and generate an answer.

## 🐛 Troubleshooting

*   **Containers not starting?** Check logs with `docker-compose logs -f`.
*   **Database connection issues?** Ensure distinct ports (`5432`, `6333`, `7474`) are not occupied on your host machine.
*   **LLM Errors?** Verify your `OPENAI_API_KEY` is correctly set in `docker-compose.yml`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
