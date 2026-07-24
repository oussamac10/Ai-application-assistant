# Testing Documentation

This document explains the testing strategy, commands, and continuous integration procedures.

## 1. Backend Testing

The backend uses **pytest** for unit and integration tests. 

### Running Tests
To run the complete test suite:
```bash
cd backend
source venv/bin/activate
PYTHONPATH=. pytest
```

To run only the session-specific tests:
```bash
PYTHONPATH=. pytest tests/sessions
```

To run only the form-definition tests:
```bash
PYTHONPATH=. pytest tests/forms
```

### Static Analysis & Type Checking
To run linting, formatting check, and strict type verification:
```bash
# Verify imports & syntax rules
ruff check .

# Check formatting guidelines
ruff format --check .

# Validate strict static typing
mypy app
```

---

## 2. Frontend Testing

The frontend uses **Vitest** for component and logic testing.

### Running Tests
To run all tests:
```bash
cd frontend
npm run test
```

### Type Checking & Linting
To check TypeScript types and Next.js/ESLint configuration rules:
```bash
# Type check using tsc
npm run typecheck

# Lint files
npm run lint
```
