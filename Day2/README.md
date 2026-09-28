# Film Review Platform API — Day 2: Pydantic v2 Validation, Reusability & Inheritance

A production-style FastAPI application extending the **Day 1 Film Review Platform** by implementing **Pydantic v2 core features**: reusable models, reducing duplication through **inheritance**, validating data at the API boundary, enforcing **strict validation**, and demonstrating modern serialization.

---

## 🏗 Architecture & Separation of Concerns

The project continues the 4-layer architecture established in Day 1:

```
Routers (API Boundary & Validation)
        │
        ▼
Handlers (HTTP Orchestration & Status Codes)
        │
        ▼
Services (Business Logic & Domain Validation)
        │
        ▼
  DAO (In-Memory Persistence Layer)
```

```
Day2/
├── app/
│   ├── main.py                  # FastAPI app definition, lifespan & routers
│   ├── core/
│   │   ├── config.py            # Application settings
│   │   └── lifespan.py          # Startup and shutdown lifespan manager
│   ├── models/                  # Pydantic v2 models & domain entities (no separate schemas)
│   │   ├── base.py              # AppBaseModel with shared ConfigDict
│   │   ├── common.py            # Generic response models (MessageResponse, HealthResponse)
│   │   ├── film.py              # FilmBase, FilmCreate, FilmUpdate, FilmResponse, FilmFilterQuery, Film
│   │   ├── review.py            # ReviewBase, ReviewCreate, ReviewUpdate, ReviewResponse, RatingRangeFilter, Review
│   │   └── user.py              # UserBase, UserRegisterRequest, UserLoginRequest, UserResponse, User
│   ├── dao/                     # Data Access Objects (mock persistence)
│   │   ├── film_dao.py
│   │   ├── review_dao.py
│   │   └── user_dao.py
│   ├── services/                # Business logic & demo services
│   │   ├── film_service.py
│   │   ├── review_service.py
│   │   ├── user_service.py
│   │   └── serialization_service.py  # Demonstration of model_dump & exclusions
│   ├── handlers/                # HTTP request/response orchestration
│   │   ├── auth_handler.py
│   │   ├── film_handler.py
│   │   ├── review_handler.py
│   │   └── user_handler.py
│   └── routers/                 # Endpoint declarations & parameter binding
│       ├── api.py               # Aggregated /api/v1 router
│       ├── auth.py              # POST /auth/register, POST /auth/login
│       ├── films.py             # CRUD /films with query validation
│       ├── health.py            # GET /health
│       ├── reviews.py           # CRUD /reviews with rating bounds
│       ├── serialization.py     # GET /serialization/demo
│       └── users.py             # GET /users/me, GET /admin/stats
├── tests/                       # Complete pytest suite (28 tests)
│   ├── conftest.py
│   ├── test_endpoints.py
│   ├── test_models.py
│   ├── test_openapi.py
│   ├── test_serialization.py
│   └── test_validation.py
├── pyproject.toml
└── README.md
```

---

## 🎯 Pydantic v2 Concepts Implemented

### 1. Shared Configuration (`ConfigDict`) & Base Model
Avoid duplicating settings across dozens of models. All application models inherit from `AppBaseModel` in [`app/models/base.py`](file:///c:/Users/Durgapasad/sprint2/Day2/app/models/base.py):
* `strict = True`: Enforces strict type checking. For instance, integer fields will reject string values like `"10"` rather than performing implicit type coercion.
* `from_attributes = True`: Allows generating Pydantic model instances directly from ORM/dataclass/domain models using `Model.model_validate(obj)`.
* `populate_by_name = True`: Permits population of fields either by their defined Python attribute name (e.g. `release_year`) or by their alias (e.g. `releaseYear`).
* `str_strip_whitespace = True`: Automatically trims leading and trailing whitespaces from string inputs before constraint validation.

### 2. Model Reuse Through Inheritance
Duplication is eliminated by establishing base contracts:

```
      AppBaseModel
           │
     ┌─────┴───────────────┬──────────────────────┐
     │                     │                      │
 FilmBase              ReviewBase              UserBase
  ├── FilmCreate        ├── ReviewCreate        ├── UserRegisterRequest
  ├── FilmResponse      ├── ReviewResponse      └── UserResponse
  └── (FilmUpdate)      └── (ReviewUpdate)
```

* **Film Models** ([`app/models/film.py`](file:///c:/Users/Durgapasad/sprint2/Day2/app/models/film.py)):
  * `FilmBase`: Defines core fields: `title`, `release_year` (alias `releaseYear`), `genre`, `director`, `description`.
  * `FilmCreate(FilmBase)`: Directly inherits all fields without re-declaring a single attribute.
  * `FilmResponse(FilmBase)`: Adds persistent `id`, `created_at`, and the `@computed_field` `years_since_release`.
* **Review Models** ([`app/models/review.py`](file:///c:/Users/Durgapasad/sprint2/Day2/app/models/review.py)):
  * `ReviewBase`: Defines `film_id`, `rating` (1–10 inclusive), `review` (min 50 characters).
  * `ReviewCreate(ReviewBase)`: Adds `reviewer_display_name`.
  * `ReviewResponse(ReviewBase)`: Adds `id`, `reviewer_display_name`, and `submitted_at`.
* **User Models** ([`app/models/user.py`](file:///c:/Users/Durgapasad/sprint2/Day2/app/models/user.py)):
  * `UserBase`: Exposes `username`, `email`, `role`.
  * `UserRegisterRequest(UserBase)`: Adds `password: SecretStr` and optional `confirm_password: SecretStr`.
  * `UserResponse(UserBase)`: Adds `id` and `created_at`. Password is strictly absent.

### 3. Computed Fields (`@computed_field`)
In `FilmResponse`, the elapsed time since a movie came out is calculated dynamically:
```python
@computed_field
@property
def years_since_release(self) -> int:
    current_year = datetime.now(timezone.utc).year
    return max(0, current_year - self.release_year)
```
This field is automatically included in serialized JSON output (`model_dump()`, `model_dump_json()`) and is rendered in the OpenAPI schema under `/docs`.

### 4. Field Constraints vs Custom Validators
* **`Field(...)` for declarative constraints**: `min_length`, `max_length`, `ge`, `le`, `description`, `examples`, `alias`.
* **`@field_validator` for contextual/dynamic checks**:
  * `release_year`: Rejects dates more than 5 years into the future (`current_year + 5`).
  * `title`: Ensures titles are not composed entirely of punctuation symbols.
  * `role`: Restricts user roles to `{"user", "critic", "moderator", "admin"}`.
* **`@model_validator(mode="after")` for cross-field relationships**:
  * `FilmFilterQuery`: Ensures `start_year <= end_year`.
  * `RatingRangeFilter`: Ensures `min_rating <= max_rating`.
  * `UserRegisterRequest`: Verifies `password == confirm_password` and confirms password does not contain the username.

### 5. Sensitive Data Protection (`SecretStr`)
User passwords in registration and login are typed as `SecretStr`.
* String representation `str(payload.password)` and `repr(payload.password)` display `**********`.
* Never serialized in API responses or plain logs.
* Unwrapped securely only when hashing or validating credentials via `payload.password.get_secret_value()`.

### 6. Aliases & Dual Population
The field `release_year` specifies `alias="releaseYear"` with `populate_by_name=True`.
* Incoming requests can send camelCase (`releaseYear: 2010`) or snake_case (`release_year: 2010`).
* Internally, Python code always references `payload.release_year`.

### 7. Serialization Demonstration
Exposed live at `GET /api/v1/serialization/demo` and implemented in [`app/services/serialization_service.py`](file:///c:/Users/Durgapasad/sprint2/Day2/app/services/serialization_service.py):
* `model_dump()`: Converts model to native Python dictionary.
* `model_dump_json()`: Serializes model directly to standard JSON string.
* `include`: Whitelists fields (e.g., `include={"id", "title"}`).
* `exclude`: Blacklists fields (e.g., `exclude={"created_at"}`).
* `exclude_none`: Omits fields whose values are `None`.
* `exclude_unset`: Omits fields not explicitly provided during instantiation.
* `exclude_defaults`: Omits fields whose values equal their schema default.

---

## 🚀 Running the Application & Tests

### 1. Install Dependencies
```bash
cd Day2
uv sync
```

### 2. Start the Development Server
```bash
uv run uvicorn app.main:app --reload --port 8000
```
* **Swagger UI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Serialization Demo**: [http://127.0.0.1:8000/api/v1/serialization/demo](http://127.0.0.1:8000/api/v1/serialization/demo)

### 3. Run Test Suite
```bash
uv run pytest -v
```
All 28 tests cover strict mode rejection, inheritance hierarchy, computed fields, serialization options, validators, and endpoints.

---

## 💡 Reflection & Architecture Questions

### 1. Why is model inheritance better than duplicating models?
Model inheritance follows the DRY (Don't Repeat Yourself) principle and creates a single source of truth for shared entity attributes. If a core field changes (e.g. updating the title length constraint or adding a field description), modifying `FilmBase` updates `FilmCreate` and `FilmResponse` immediately without needing to track down and edit multiple duplicate models. It also makes domain models more maintainable and guarantees contract consistency across endpoints.

### 2. When should you create a child model instead of modifying the base model?
You should create a child model when an attribute or behavior belongs only to a specific operational lifecycle:
* **Output-only data**: Fields generated by the database or backend (such as auto-incrementing `id`, `created_at`, or `@computed_field` values) should exist on `Response` child models, not on `Create` models.
* **Sensitive input**: Fields required only on creation (like raw `password` or terms acceptance) belong exclusively to `Create`/`Request` models.
* **Modifying the base model directly**: Only modify the base model when every child model (creation, response, internal representation) requires that attribute and validation constraint.

### 3. Why should configuration be shared through inheritance?
In Pydantic v2, configurations (like `strict=True`, `from_attributes=True`, `str_strip_whitespace=True`, and `populate_by_name=True`) dictate how models parse and serialize data. Declaring these settings in an `AppBaseModel` guarantees uniform behavior across the entire API boundary. Without shared configuration, developers would inevitably forget `strict=True` or `from_attributes=True` on newly introduced models, leading to subtle bugs such as type coercion inconsistencies or ORM deserialization failures.

### 4. Why is strict mode important?
By default, Pydantic performs lenient type coercion (e.g. converting string `"10"` into integer `10`, or `"true"` into boolean `True`). In strict mode (`strict=True`), Pydantic rejects values that do not match the declared type, raising a `422 Unprocessable Entity` validation error. Strict mode is critical for:
* **Contract integrity**: Clients are forced to conform strictly to the API contract.
* **Preventing bugs**: Prevents unintended parsing of strings containing leading zeroes, floats rounded to integers, or strings misconstrued as booleans.
* **Security & Clarity**: Eliminates ambiguity at the API boundary before data reaches business logic or database storage.

### 5. When should you use `Field()` instead of a validator?
Use `Field()` for static, declarative constraints that Pydantic and OpenAPI understand natively:
* Value ranges: `ge`, `gt`, `le`, `lt`
* String lengths: `min_length`, `max_length`
* Regex matching: `pattern`
* Documentation metadata: `description`, `examples`, `alias`, `title`

Because `Field()` constraints are declarative, FastAPI translates them directly into the generated OpenAPI schema (`minimum`, `maximum`, `minLength`), so API consumers can inspect them in Swagger UI. Validators (`@field_validator`) should be reserved for dynamic, complex, or external validation logic (such as checking against current timestamps, database uniqueness checks, or algorithmic parsing) that cannot be expressed declaratively.

### 6. What is the difference between a field validator and a model validator?
* **Field Validator (`@field_validator`)**:
  * Operates on a **single field** in isolation.
  * Runs before or after field-level type parsing.
  * Ideal for formatting, regex adjustments, or custom checks specific to one property (e.g. normalizing email addresses or checking title characters).
* **Model Validator (`@model_validator`)**:
  * Operates on the **entire model instance** (when `mode="after"`) or the raw dictionary of inputs (when `mode="before"`).
  * Has access to all model fields simultaneously.
  * Essential for **cross-field relationship validation** (e.g. verifying `start_year <= end_year`, `min_rating <= max_rating`, or `password == confirm_password`).

### 7. Why is `SecretStr` useful?
`SecretStr` prevents accidental disclosure of sensitive credentials:
* **Masked Output**: When printed (`print(model)`), converted to string (`str(model)`), inspected in a debugger (`repr(model)`), or dumped to JSON, `SecretStr` displays as `'**********'`.
* **Log & Traceback Protection**: Prevents secrets from being leaked to application logs, APM systems, or exception tracebacks.
* **Explicit Access**: The raw string value can only be retrieved intentionally by calling `.get_secret_value()`.

### 8. When should a value be a computed field instead of a stored field?
A value should be a `@computed_field` when:
* **It is derived from other existing fields**: e.g., `years_since_release` derived from `current_year - release_year`, or `full_name` derived from `first_name + last_name`.
* **It is time-dependent**: Storing "years since release" in a database would require updating every record on January 1st every year. Computing it dynamically guarantees it is always accurate.
* **It avoids database redundancy and synchronization errors**: Deriving values on read prevents stored calculations from drifting out of sync with their source attributes.

### 9. What is the difference between `model_dump()` and `model_dump_json()`?
* **`model_dump()`**: Serializes the Pydantic model into a native **Python dictionary** containing Python objects (e.g., `datetime` objects remain `datetime` instances, `UUID` objects remain `UUID` instances).
* **`model_dump_json()`**: Serializes the Pydantic model directly into an encoded **JSON string**, serializing datetimes into ISO 8601 strings, converting UUIDs to strings, and using optimized C/Rust parsing via `pydantic-core` for maximum throughput.

### 10. How does FastAPI use Pydantic models to generate `/docs` automatically?
FastAPI inspects route definitions at application startup. For every endpoint:
1. It analyzes the type annotations in the function signature (e.g. `payload: FilmCreate`) and the `response_model` argument (e.g. `response_model=FilmResponse`).
2. It extracts Pydantic's JSON schema definitions, including field names, types, default values, `Field()` constraints (`minimum`, `maximum`, `minLength`), aliases, and `@computed_field` definitions.
3. It compiles these schemas into a single OpenAPI 3.0+ document served at `/openapi.json`.
4. The Swagger UI single-page application hosted at `/docs` fetches `/openapi.json` and renders an interactive explorer allowing users to inspect contracts, test requests, and view response structures in real time.
