# Week 2 - Day 5: AI Service Architecture

---

## Q1. Why did you create an AIService instead of calling Gemini or Groq directly inside the route?

**Answer**

I created an AIService to decouple the application from specific LLM providers.

Instead of the route knowing whether Gemini, Groq, or DeepSeek is being used, it simply calls:

```python
ai_service.generate_answer(prompt)
```

The AIService is responsible for selecting the provider, handling retries, logging, and fallback.

This keeps the route clean and makes it easy to switch or add providers without modifying the API endpoints.

---

### Follow-up Question

**What design principle does this follow?**

**Answer**

It follows the **Separation of Concerns (SoC)** principle.

- Routes handle HTTP requests.
- AIService manages AI-related business logic.
- Providers communicate with external AI APIs.

Each component has a single responsibility.

---

## Q2. Why did you create a BaseProvider abstract class?

**Answer**

The BaseProvider defines a common interface for all AI providers.

Every provider must implement the `generate()` method.

Example:

```python
class BaseProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str):
        pass
```

This guarantees that Gemini, Groq, and DeepSeek all expose the same interface.

As a result, AIService can switch between providers without changing its own logic.

---

### Follow-up Question

**Why not create providers without inheritance?**

**Answer**

Without a common interface, different providers could implement different method names, leading to inconsistent code.

The abstract class enforces a contract and catches implementation mistakes during development.

---

## Q3. Why did you use a Provider Registry (Dictionary)?

**Answer**

Instead of writing multiple `if-else` statements, I used a dictionary to map provider names to their classes.

Example:

```python
self.provider_classes = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "deepseek": DeepSeekProvider,
}
```

Benefits:

- Cleaner code.
- Easy to add new providers.
- Constant-time lookup (O(1)).
- Better maintainability.

---

### Follow-up Question

**What happens if you add OpenAI later?**

**Answer**

I only need to:

1. Create an `OpenAIProvider`.
2. Register it in the provider registry.

No other part of the application needs to change.

This follows the **Open/Closed Principle**.

---

## Q4. What is Lazy Initialization?

**Answer**

Lazy Initialization means an object is created only when it is actually needed.

Instead of creating every provider during application startup, the provider is created the first time it is requested.

Example:

```text
Application Starts

↓

No Provider Created

↓

First Gemini Request

↓

Create Gemini Provider
```

This reduces startup time and avoids creating unused objects.

---

## Q5. Why did you cache provider instances?

**Answer**

After creating a provider once, I store it in a cache.

Future requests reuse the same instance instead of creating a new one.

Example:

```python
self.provider_cache = {}
```

Benefits:

- Avoids repeated object creation.
- Improves performance.
- Reuses existing SDK clients.

---

### Follow-up Question

**Why not create a new provider for every request?**

**Answer**

Creating provider objects repeatedly increases overhead.

Since the provider configuration does not change between requests, reusing the same instance is more efficient.

---

## Q6. What is Retry?

**Answer**

Retry automatically attempts the same request again when a temporary failure occurs.

Examples:

- Network timeout.
- Temporary API failure.
- Rate limiting.

Instead of failing immediately, the application retries the request before giving up.

---

## Q7. What is Fallback?

**Answer**

Fallback means switching to another AI provider if the current provider fails.

Example:

```text
Gemini

↓

Fail

↓

DeepSeek

↓

Fail

↓

Groq
```

This improves system reliability and availability.

---

### Follow-up Question

**What is the difference between Retry and Fallback?**

**Answer**

Retry attempts the same provider multiple times.

Fallback switches to a different provider after retries fail.

Workflow:

```text
Gemini

↓

Retry

↓

Retry

↓

Still Fail

↓

Groq
```

---

## Q8. Why did you add Logging?

**Answer**

Logging records important events during execution.

Examples:

- Which provider was used.
- Which provider failed.
- Successful responses.
- Complete failure of all providers.

Logging is essential for debugging and monitoring production systems.

---

### Follow-up Question

**Why not use print()?**

**Answer**

`print()` is only suitable for debugging during development.

Logging provides:

- Log levels (INFO, WARNING, ERROR).
- Better monitoring.
- File or remote log storage.
- Structured debugging in production.

---

## Q9. Why did you create a custom AIProviderError?

**Answer**

Instead of raising a generic Exception, I created a custom exception.

```python
class AIProviderError(Exception):
    pass
```

This allows the application to distinguish AI-related failures from other errors and return meaningful HTTP responses.

---

### Follow-up Question

**What are the advantages of custom exceptions?**

**Answer**

- Better error categorization.
- Easier debugging.
- Cleaner exception handling.
- More meaningful API responses.

---

## Q10. Explain the complete AI generation flow in your project.

**Answer**

```text
Route

↓

AIService

↓

Provider Cache

↓

Provider Selection

↓

Retry

↓

Gemini

↓

If Fail

↓

DeepSeek

↓

If Fail

↓

Groq

↓

Return Response
```

The route only interacts with AIService.

AIService manages provider selection, retries, fallback, logging, and error handling.

---

## Revision Summary

- AIService
- Abstract Base Class
- Provider Pattern
- Provider Registry
- Lazy Initialization
- Instance Caching
- Retry
- Fallback
- Logging
- Custom Exceptions
- Open/Closed Principle
- Separation of Concerns