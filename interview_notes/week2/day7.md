# Week 2 - Day 7
# Interview Notes

---

# 1. Why did you introduce ChatService?

Answer:

Initially, all business logic was inside the FastAPI router, making it large and difficult to maintain. I introduced ChatService to separate business logic from HTTP handling. The router now only receives requests and returns responses, while ChatService orchestrates the complete RAG workflow. This follows the Service Layer architecture and Separation of Concerns (SoC).

---

# 2. What is the responsibility of the Router?

Answer:

The router should only:

- Receive HTTP requests
- Validate request data
- Authenticate users
- Call the appropriate service
- Return the response

It should not contain business logic, database queries, prompt building, or AI calls.

---

# 3. What is the responsibility of ChatService?

Answer:

ChatService acts as the orchestrator of the chat workflow.

Responsibilities:

- Create or load chat sessions
- Store user messages
- Retrieve conversation history
- Retrieve relevant document chunks
- Build prompts
- Generate AI responses
- Store assistant responses
- Return the final API response

---

# 4. What is an Orchestrator?

Answer:

An orchestrator coordinates multiple specialized services without implementing their internal logic.

Example:

ChatService does not generate embeddings or call Gemini directly. Instead, it coordinates RetrievalService, PromptService, and AIService to complete the workflow.

---

# 5. Why create RetrievalService?

Answer:

RetrievalService isolates semantic search logic.

Responsibilities:

- Generate query embeddings
- Search pgvector
- Return the most relevant document chunks

Keeping retrieval separate makes the code reusable and easier to maintain.

---

# 6. Why create PromptService?

Answer:

PromptService is responsible only for prompt construction.

Responsibilities:

- Format conversation history
- Format retrieved document context
- Build the final prompt

Separating prompt generation makes it easier to modify prompts without affecting other parts of the application.

---

# 7. Why create AIService?

Answer:

AIService abstracts interactions with LLM providers.

Responsibilities:

- Call Gemini, Groq, or DeepSeek
- Retry failed requests
- Automatically fall back to another provider
- Return the generated response

This keeps provider-specific logic out of the business layer.

---

# 8. What is Separation of Concerns (SoC)?

Answer:

Separation of Concerns means every module should have a single, well-defined responsibility.

Example:

Router → HTTP

ChatService → Business Logic

CRUD → Database Operations

PromptService → Prompt Generation

RetrievalService → Semantic Search

AIService → LLM Communication

This improves maintainability and testing.

---

# 9. Why store conversation history?

Answer:

Conversation history enables multi-turn conversations.

Benefits:

- Follow-up questions
- Better contextual understanding
- ChatGPT-like experience
- Persistent conversations

Without chat history, every request is treated independently.

---

# 10. What is a Chat Session?

Answer:

A ChatSession represents one complete conversation.

Each session has:

- session_id
- title
- organization_id
- user_id
- created_at

Each session contains multiple ChatMessage records.

---

# 11. Why separate ChatSession and ChatMessage?

Answer:

One ChatSession contains many ChatMessages.

Relationship:

One ChatSession → Many ChatMessages

This normalization avoids duplication and allows unlimited messages in a conversation.

---

# 12. What happens when a user sends a message?

Answer:

Workflow:

1. Receive request.
2. Create or load chat session.
3. Store user message.
4. Retrieve previous conversation history.
5. Perform semantic search.
6. Build the prompt.
7. Generate AI response.
8. Store assistant response.
9. Return the response.

---

# 13. Why use Dependency Injection?

Answer:

Instead of creating dependencies directly inside a class, they are injected through the constructor.

Benefits:

- Easier testing
- Easier mocking
- Better flexibility
- Looser coupling

---

# 14. Why remove document_id from chat requests?

Answer:

Initially, retrieval searched inside only one document.

This limited the system because users had to specify which PDF to search.

The architecture was upgraded to search across all documents belonging to the user's organization.

Now the backend automatically finds the most relevant information without requiring document selection.

---

# 15. How is multi-document retrieval implemented?

Answer:

Instead of filtering chunks by document_id, the query joins the DocumentChunk and Document tables.

Filtering is done using organization_id.

This allows searching across every document uploaded by an organization while maintaining tenant isolation.

---

# 16. Why use SQL JOIN?

Answer:

DocumentChunk only stores document_id.

Organization information exists in the Document table.

Joining both tables allows filtering chunks based on organization_id while still performing vector similarity search.

---

# 17. Explain the complete architecture.

Answer:

```
Frontend
      │
      ▼
Router
      │
      ▼
ChatService
      │
      ├─────────────┐
      ▼             ▼
Session CRUD   RetrievalService
      │             │
      ▼             ▼
Message CRUD   Semantic Search
                    │
                    ▼
             PromptService
                    │
                    ▼
               AIService
                    │
                    ▼
      Gemini / Groq / DeepSeek
```

Each layer has a single responsibility, making the application modular and scalable.

---

# 18. What design patterns are used?

Answer:

- Service Layer Pattern
- Repository/CRUD Pattern
- Dependency Injection
- Orchestrator Pattern
- Layered Architecture
- Strategy Pattern (AI provider selection)
- Retry & Fallback Pattern

---

# 19. Why is this architecture production-ready?

Answer:

Because it provides:

- Separation of Concerns
- Modular services
- Multi-provider AI support
- Persistent chat history
- Multi-tenant document retrieval
- Layered architecture
- Easy testing
- Scalability
- Maintainability

---

# 20. One-Line Interview Summary

"I refactored the RAG pipeline into a layered architecture by introducing ChatService as the orchestrator, separating retrieval, prompt generation, AI communication, and database operations into dedicated services. I also implemented persistent chat sessions and multi-document retrieval across an organization, making the system scalable and production-ready."