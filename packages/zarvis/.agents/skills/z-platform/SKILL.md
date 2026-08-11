```markdown
# z-platform Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill provides a comprehensive guide to contributing to the `z-platform` codebase, a TypeScript project with no detected framework. It covers established coding conventions, common workflows for documentation, environment configuration, and Docker Compose management, as well as testing patterns and useful commands for contributors.

## Coding Conventions

### File Naming

- Use **camelCase** for file names.
  - Example: `userService.ts`, `dataLoader.ts`

### Import Style

- Use **relative imports** for modules within the project.
  - Example:
    ```typescript
    import { fetchData } from './dataLoader';
    ```

### Export Style

- Use **named exports** for functions, types, and constants.
  - Example:
    ```typescript
    // In userService.ts
    export function getUser(id: string) { ... }
    export const USER_ROLE = 'admin';
    ```

### Commit Messages

- Freeform style, no strict prefix required.
- Keep messages concise (average ~42 characters).
  - Example: `fix user fetch error on login`

## Workflows

### Update Documentation Guide

**Trigger:** When adding or updating a documentation guide for operations or usage  
**Command:** `/add-doc-guide`

1. Create or update a documentation guide file in `docs/operations/`.
   - Example: `docs/operations/local-compose.md`
2. Update `docs/operations/README.md` to link the new or updated guide.
   - Example:
     ```markdown
     - [Local Compose Guide](./local-compose.md)
     ```
3. Optionally, finalize or refresh the guide with further edits.

### Update Environment Configuration

**Trigger:** When adding or correcting environment configuration templates for local or staging environments  
**Command:** `/update-env-template`

1. Add or update `.env.example` with new variables or corrections.
   - Example:
     ```
     DATABASE_URL=postgres://user:pass@localhost:5432/db
     API_KEY=your-api-key-here
     ```
2. Document changes or guidance in commit messages.

### Update Compose Stack

**Trigger:** When adding new services or updating network settings in the Docker Compose stack  
**Command:** `/update-compose`

1. Add or modify `compose.yml` to reflect service or network changes.
   - Example:
     ```yaml
     services:
       app:
         build: .
         ports:
           - "3000:3000"
       db:
         image: postgres:14
         environment:
           POSTGRES_PASSWORD: example
     ```

## Testing Patterns

- Test files use the pattern `*.test.*` (e.g., `userService.test.ts`).
- The testing framework is **unknown**, but tests are colocated with source files or in dedicated test files.
- Example test file name: `auth.test.ts`

## Commands

| Command            | Purpose                                                        |
|--------------------|----------------------------------------------------------------|
| /add-doc-guide     | Create or update a documentation guide and link it in the index|
| /update-env-template | Add or update environment variable templates                 |
| /update-compose    | Add or modify Docker Compose stack configurations              |
```
