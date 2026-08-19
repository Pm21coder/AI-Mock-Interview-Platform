Loading / Empty / Failure states improvements

Recommended changes to improve UX and avoid blank/flash-of-content:

1. Shared UI components
  - Create a lightweight LoadingSpinner component (Tailwind classes) and an ErrorFallback component.
  - Use Suspense and dynamic imports where appropriate for route-level loading.

2. Data-fetching pages
  - Ensure every page that fetches data shows a loading placeholder while requests are pending.
  - On error, show ErrorFallback with friendly message and retry button that re-triggers the fetch.

3. Accessibility
  - Add aria-busy and proper roles to loading elements.

4. Visual regression tests
  - Add a couple of Storybook stories or jest + testing-library snapshots for the loading/empty states to prevent regressions.

Suggested starting files to update:
  - src/app/interview/session/page.js (already shows loading state; ensure spinner is used instead of empty area)
  - src/components/LoadingSpinner.jsx (new)
  - src/components/ErrorFallback.jsx (new)

If you want, apply changes automatically (create components and replace a couple of usages).