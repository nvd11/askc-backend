# AskC Backend

This project is a ChatGPT-style backend service designed to power a conversational AI application. It provides a robust API for managing users, conversations, and streaming chat responses from various Large Language Models (LLMs).

## Features

- **Streaming Chat API**: Delivers real-time, streaming responses from LLMs using Server-Sent Events (SSE).
- **Conversation History**: Persists chat history in a PostgreSQL database.
- **Pluggable Authentication**: Supports both Google IAP and Auth0 (JWT-based) for secure authentication, configurable via environment variables.
- **LLM Integration**: Integrated with `langchain` to easily connect with models like Google Gemini and DeepSeek.
- **Cloud-Native Deployment**: Production-ready deployment using Docker, GKE, Helm, and Cloud Build.

## Technology Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy (async)
- **Authentication**: Google IAP, Auth0 (JWT via `python-jose`)
- **LLM Orchestration**: Langchain
- **Deployment**: Docker, Google Kubernetes Engine (GKE), Helm
- **CI/CD**: Google Cloud Build

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint                            | Description                                                                 |
|--------|-------------------------------------|-----------------------------------------------------------------------------|
| POST   | `/chat`                             | Streams a chat response for a given conversation.                           |
| POST   | `/purechat`                         | Streams a chat response without saving to the database.                     |
| GET    | `/users/{username}`                 | Gets a user's profile information (only accessible by the user themselves).  |
| POST   | `/users/`                           | Creates a new user (for admin/testing purposes).                            |
| GET    | `/me`                               | Gets the current user's info via Google IAP headers.                        |
| GET    | `/auth0/me`                         | Gets the current user's info via Auth0 Bearer Token.                        |
| POST   | `/conversations/`                   | Creates a new conversation for the current user.                            |
| GET    | `/users/{user_id}/conversations`    | Lists all conversations for the current user.                               |
| GET    | `/conversations/{conversation_id}`  | Retrieves a single conversation with all its messages.                      |

---

## Architecture & Directory Structure

The project follows a standard service-oriented architecture, separating concerns into distinct layers.

```
.
├── cloudbuild-helm.yaml    # Cloud Build config for Prod GKE deployment
├── cloudbuild-helm-dev.yaml  # Cloud Build config for Dev GKE deployment
├── Dockerfile              # Docker configuration
├── helm/                     # Helm charts for Kubernetes deployment
│   ├── templates/            # Kubernetes resource templates
│   ├── values.yaml           # Default Helm values
│   └── ...
├── src/                      # Main source code
│   ├── configs/              # Application & DB configuration
│   ├── dao/                  # Data Access Objects (raw DB queries)
│   ├── models/               # SQLAlchemy table definitions
│   ├── routers/              # API Routers (endpoints) & dependencies
│   ├── schemas/              # Pydantic models for data validation
│   ├── services/             # Business logic layer
│   └── utils/                # Shared utility functions
└── test/                     # Pytest unit and integration tests
```

---

## Deployment

The application is designed to be deployed to Google Kubernetes Engine (GKE) via Google Cloud Build.

### Prerequisites
1.  A Google Cloud Project with Billing enabled.
2.  `gcloud` CLI installed and authenticated.
3.  A GKE cluster.
4.  A PostgreSQL database (e.g., Cloud SQL).
5.  Required APIs enabled (Cloud Build, GKE, Secret Manager, Artifact Registry).

### Deployment Steps
1.  **Clone the repository.**
2.  **Update Configuration**:
    *   **Cloud Build**: In `cloudbuild-helm.yaml` and `cloudbuild-helm-dev.yaml`, update the `substitutions` block with your GCP Project ID, GKE cluster name, etc.
    *   **Helm Values**: In `helm/values-chat-api-svc.yaml` and `helm/values-chat-api-svc-dev.yaml`, update the configuration for your environment (e.g., Cloud SQL instance connection name, Auth0 variables).
3.  **Store Secrets**: Ensure all necessary secrets (e.g., `db-pass-nvd11`, `clien-id-auth0-askc-prod`) are stored in GCP Secret Manager.
4.  **Submit Build**: Run the appropriate Cloud Build command from the project root.
    *   **For Prod:**
        ```bash
        gcloud builds submit --config cloudbuild-helm.yaml .
        ```
    *   **For Dev:**
        ```bash
        gcloud builds submit --config cloudbuild-helm-dev.yaml .
