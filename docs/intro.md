# Ask Compliance App: Introduction

**Production URL:**
[https://gateway.jpgcp.cloud/askc-ui/](https://gateway.jpgcp.cloud/askc-ui/) (Requires GitHub login via Auth0)

**Architecture Diagram:**
<img width="1801" height="924" alt="image" src="https://github.com/user-attachments/assets/0833c49a-3c29-4e1e-b05b-cce7d7360219" />


### Repositories & Tech Stack

*   **Frontend**: [askc-ui](https://github.com/nvd11/askc-ui)
    *   **Stack**: Lit (Web Components) + Nginx
*   **Backend**: [askc-backend](https://github.com/nvd11/askc-backend)
    *   **Stack**: FastAPI + LangChain
*   **Database**: Google Cloud SQL (PostgreSQL 13)
    *   **Terraform Setup**: [terraform-cloudsql](https://github.com/nvd11/terraform-cloudsql)
*   **Infrastructure**: GKE Private Cluster
    *   **Terraform Setup**: [Terraform-GCP-config/gke](https://github.com/nvd11/Terraform-GCP-config/tree/master/gke)

### CI/CD Pipeline

We use **Google Cloud Build** for continuous integration and deployment.

*   **UI Pipeline**: [cloudbuild-askc-ui.yaml](https://github.com/nvd11/askc-ui/blob/main/cloudbuild-askc-ui.yaml)
*   **Backend Pipeline**: [cloudbuild-helm.yaml](https://github.com/nvd11/askc-backend/blob/main/cloudbuild-helm.yaml)

### Technical Deep Dives

Here are detailed guides on specific technical implementations:

1.  **Database Design**:
    *   [Database Schema & Philosophy](https://github.com/nvd11/askc-backend/blob/main/docs/database_design.md)
2.  **Streaming LLM Responses**:
    *   [How we achieved the "Typewriter Effect"](https://github.com/nvd11/askc-backend/blob/main/docs/Streaming_LLM_Response_Handling.md)
3.  **Conversation Memory**:
    *   [How the LLM remembers context](https://github.com/nvd11/askc-backend/blob/main/docs/conversation_memory_architecture.md)
4.  **Auth0 + GitHub Authentication**:
    *   [OAuth 2.0 Implementation Guide](https://github.com/nvd11/askc-backend/blob/main/docs/Auth0_OAuth2_Deep_Dive.md)
5.  **Markdown Rendering**:
    *   [Implementing Markdown with SSE](https://github.com/nvd11/askc-ui/blob/main/docs/SSE-Markdown-Implementation-Guide.md)
