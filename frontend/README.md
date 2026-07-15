# RiskLens Frontend

The frontend is a modern SPA web application built with React, TypeScript, and Vite, styled using TailwindCSS.

---

## Technical Stack
- **React**: Declarative, component-based user interfaces.
- **TypeScript**: Strict compile-time type-safety.
- **Vite**: Rapid, hot-module-reloading frontend compiler.
- **TailwindCSS**: Utility-first CSS framework for layout styling.
- **TanStack React Query**: Server-state management and query caching.
- **React Router DOM**: Client-side routing with nested layout structures.
- **Recharts**: Responsive charting components for analytics.

---

## Local Development Setup

### 1. Installation
1. Navigate to the `frontend/` directory.
2. Install Node dependencies:
   ```bash
   npm install
   ```

### 2. Development Execution
Launch the Vite hot-reloading development server:
```bash
npm run dev
```
The application will run locally at `http://localhost:5173`.

### 3. Production Build
Verify code compilation and compile minified HTML/JS assets:
```bash
npm run build
```
To run the local preview server of the production build output:
```bash
npm run preview
```

---

## TypeScript Guidelines

The project enforces strict TypeScript check rules:
- Avoid the use of `any` types unless explicitly justified and isolated.
- Provide descriptive interfaces for all API payloads and response schemas.
- Ensure component props are typed.

---

## Running Tests

We utilize Vitest and React Testing Library for frontend testing.

To run the frontend tests:
```bash
npm run test
```
To run coverage reporting:
```bash
npm run coverage
```
