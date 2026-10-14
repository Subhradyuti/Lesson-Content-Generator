# Lesson Content Generator — Frontend

Premium web interface for the Self-Evaluating Lesson Content Generator backend. Built with React 19, TypeScript, Vite, Tailwind CSS 4, and Framer Motion.

## Features

- **Premium UI/UX**: Modern dark theme with smooth animations and micro-interactions
- **Full API Integration**: Connects to FastAPI backend with typed API client
- **Responsive Design**: Mobile-first layout that works across all devices
- **Real-time Progress**: Live updates during lesson generation with polling
- **Comprehensive Evaluation Display**: Shows all 14 rubric checkpoints with pass/fail status
- **Revision History**: Complete timeline of rejected drafts and revision instructions
- **Run History**: Browse all generated lessons with detailed metadata
- **Error Boundaries**: Graceful error handling with recovery options
- **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation and screen reader support

## Technology Stack

| Category | Technology |
|----------|-----------|
| Framework | React 19.1.1 + TypeScript 5.8.3 |
| Build Tool | Vite 7.3.7 |
| Styling | Tailwind CSS 4.3.3 (custom dark theme) |
| Routing | React Router DOM 7.9.0 |
| Animations | Framer Motion 11.15.0 |
| Markdown | react-markdown 10.1.0 + remark-gfm 4.0.1 |
| Icons | lucide-react 1.0.0 |
| Fonts | Inter Variable (@fontsource-variable/inter) |

## Prerequisites

- **Node.js**: 18.x or higher
- **npm**: 9.x or higher (comes with Node.js)
- **Backend**: FastAPI backend running on `http://localhost:8000`

## Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and configure:

```env
# Optional: Leave empty to use Vite proxy (recommended for development)
# VITE_API_BASE_URL=http://localhost:8000

# Optional: Set if backend requires authentication
# VITE_API_KEY=your-api-key-here
```

**Development setup (recommended):**
- Leave `VITE_API_BASE_URL` empty or commented out
- The Vite dev server proxies `/v1` and `/health` to `http://localhost:8000`
- This avoids CORS issues during development

**Production setup:**
- Set `VITE_API_BASE_URL` to your backend URL if frontend and backend are on different origins
- Set `VITE_API_KEY` if the backend requires authentication (matches `API_KEY` in backend `.env`)

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### 4. Start the Backend

In a separate terminal, start the FastAPI backend:

```bash
# From the project root
uvicorn app.main:app --reload
```

Backend API docs: `http://localhost:8000/docs`

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server (port 5173) |
| `npm run build` | Type check + production build → `dist/` |
| `npm run preview` | Preview production build locally |
| `npm run typecheck` | Run TypeScript compiler (no emit) |

## Project Structure

```
frontend/
├── public/
│   └── favicon.svg          # App icon
├── src/
│   ├── components/
│   │   ├── CheckpointCard.tsx        # Single rubric checkpoint display
│   │   ├── CopyButton.tsx            # Copy-to-clipboard utility
│   │   ├── ErrorBoundary.tsx         # React error boundary
│   │   ├── EvaluationPanel.tsx       # Full evaluation results
│   │   ├── GenerationProgress.tsx    # Progress indicator during generation
│   │   ├── Layout.tsx                # App layout with navigation
│   │   ├── LessonViewer.tsx          # Markdown lesson renderer
│   │   ├── Logo.tsx                  # App logo components
│   │   ├── Markdown.tsx              # Markdown renderer config
│   │   ├── PageHeader.tsx            # Reusable page header
│   │   ├── RecentRuns.tsx            # Dashboard recent runs list
│   │   ├── RejectionLog.tsx          # Rejection timeline
│   │   ├── RetryDiagram.tsx          # Visual retry flow
│   │   ├── Spinner.tsx               # Loading spinners and skeletons
│   │   ├── StatusBadge.tsx           # Run status badge
│   │   └── Toast.tsx                 # Toast notification system
│   ├── lib/
│   │   ├── api.ts                    # Typed API client (fetch wrapper)
│   │   ├── config.ts                 # Environment config
│   │   ├── recentRuns.ts             # localStorage persistence
│   │   ├── types.ts                  # TypeScript interfaces (backend schemas)
│   │   └── utils.ts                  # Utility functions (formatting, dates)
│   ├── pages/
│   │   ├── Dashboard.tsx             # Home page with stats and recent runs
│   │   ├── Generate.tsx              # Lesson generation form
│   │   ├── History.tsx               # All runs history
│   │   ├── RunDetail.tsx             # Detailed run view with all drafts
│   │   └── NotFound.tsx              # 404 page
│   ├── index.css                     # Global styles + Tailwind config
│   ├── main.tsx                      # App entry point
│   └── vite-env.d.ts                 # Vite type definitions
├── .env                              # Local environment config (gitignored)
├── .env.example                      # Environment template
├── .gitignore
├── index.html                        # HTML entry point
├── package.json                      # Dependencies and scripts
├── package-lock.json
├── README.md                         # This file
├── tsconfig.json                     # TypeScript config
├── tsconfig.node.json                # TypeScript config for Vite
└── vite.config.ts                    # Vite config with proxy
```

## Architecture Patterns

### API Client (`src/lib/api.ts`)

Thin typed wrapper around `fetch`:
- Adds `X-API-Key` header if `VITE_API_KEY` is set
- Typed request/response with TypeScript interfaces from `types.ts`
- Custom error classes: `ApiError` (HTTP errors), `NetworkError` (fetch failures)
- All endpoints return strongly typed promises

```typescript
// Example usage
import { api } from "./lib/api";

const response = await api.generateLesson({
  topic: "Introduction to RAG",
  max_retries: 2,
});
```

### State Management

- **Local component state**: `useState` for UI state (form inputs, toggles, expanded states)
- **localStorage**: Recent runs tracked per device (run ID, topic, created_at)
- **No global state library**: React Context not needed for this app's scope
- **AbortController**: All API calls support cancellation via signal

### Styling Approach

**Tailwind CSS 4** with custom design tokens in `src/index.css`:

```css
@theme {
  --color-canvas: #0a0e1a;        /* Page background */
  --color-surface: #131825;       /* Card background */
  --color-raised: #1a202e;        /* Elevated element background */
  --color-accent: #7c8bff;        /* Primary accent (indigo) */
  --color-pass: #22c55e;          /* Success green */
  --color-fail: #ef4444;          /* Error red */
  --color-warn: #f59e0b;          /* Warning amber */
}
```

**Utility classes:**
- `card`, `card-pad`: Card containers with consistent styling
- `btn`, `btn-primary`, `btn-ghost`: Button variants
- `chip`: Inline badge/tag
- `input`, `label`, `hint`: Form elements
- `animate-fade-up`, `animate-shimmer`: Custom animations

### Animation Patterns (Framer Motion)

**Page transitions:**
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.3 }}
>
  {/* page content */}
</motion.div>
```

**Staggered lists:**
```tsx
{items.map((item, idx) => (
  <motion.div
    key={item.id}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: idx * 0.05 }}
  >
    {/* item content */}
  </motion.div>
))}
```

**Badge pop-in:**
```tsx
<motion.span
  initial={{ scale: 0.8, opacity: 0 }}
  animate={{ scale: 1, opacity: 1 }}
  transition={{ type: "spring", stiffness: 200 }}
>
  {/* badge */}
</motion.span>
```

## API Integration

### Backend Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/lessons` | Generate a new lesson (request body: `LessonRequest`) |
| GET | `/v1/lessons/{run_id}` | Get run summary |
| GET | `/v1/lessons/{run_id}/history` | Get full run history with drafts |
| GET | `/health/live` | Liveness check |
| GET | `/health/ready` | Readiness check (includes database status) |

### Authentication

If the backend has `API_KEY` set in its `.env`, you **must** set `VITE_API_KEY` in the frontend `.env` to the same value.

The API client automatically adds the `X-API-Key` header to all requests.

### CORS Configuration

**Development (Vite proxy):**
- No CORS configuration needed
- Vite proxies `/v1` and `/health` to `http://localhost:8000`
- Same-origin requests from browser's perspective

**Production:**
- If frontend and backend are on different origins, configure CORS in the backend
- Set `VITE_API_BASE_URL` to the backend URL
- Backend must allow the frontend origin in its CORS middleware

## Responsive Design

**Breakpoints** (Tailwind defaults):
- `sm`: 640px (tablet portrait)
- `md`: 768px (tablet landscape)
- `lg`: 1024px (laptop)
- `xl`: 1280px (desktop)

**Mobile-first approach:**
- Base styles target mobile (320px+)
- Use responsive prefixes (`sm:`, `md:`, `lg:`) to adjust for larger screens

**Touch targets:**
- Minimum 44×44px for interactive elements (buttons, links)
- Adequate spacing between clickable elements

**Testing:**
- Chrome DevTools responsive mode
- Test on iPhone SE (375px), iPad (768px), desktop (1920px)

## Accessibility

**Keyboard Navigation:**
- All interactive elements are keyboard accessible
- Tab order follows visual order
- Focus indicators visible (outline on `:focus-visible`)
- Skip-to-content link in Layout

**Screen Reader Support:**
- Semantic HTML (`<main>`, `<nav>`, `<article>`, `<section>`)
- ARIA labels on icon-only buttons
- `role="status"` on loading indicators
- `role="alert"` on error messages
- All images/icons have `alt` text or `aria-hidden="true"`

**Color Contrast:**
- Text meets WCAG 2.1 AA standards (4.5:1 for normal text, 3:1 for large text)
- Color is never the sole indicator (status badges have icons + text)

**Testing Tools:**
- Chrome Lighthouse accessibility audit (target: 95+)
- axe DevTools extension
- NVDA screen reader (Windows)

## Troubleshooting

### Backend Unreachable

**Symptoms:** Health check shows "Backend unreachable", API calls fail with `NetworkError`

**Solutions:**
1. Verify backend is running: `curl http://localhost:8000/health/live`
2. Check `VITE_API_BASE_URL` in `.env` (should be empty or `http://localhost:8000` in dev)
3. Ensure no firewall blocking port 8000
4. Check Vite proxy config in `vite.config.ts`

### Authentication Failed (401/403)

**Symptoms:** API calls fail with "Authentication failed" error

**Solutions:**
1. Backend has `API_KEY` set → frontend `.env` must have `VITE_API_KEY` with same value
2. Restart dev server after changing `.env` (environment vars are embedded at build time)
3. Check Network tab: `X-API-Key` header should be present on requests

### TypeScript Errors

**Symptoms:** `npm run build` fails with type errors

**Solutions:**
1. Run `npm install` to ensure dependencies are up to date
2. Check `tsconfig.json` is valid
3. Ensure all imports have correct paths and types
4. Run `npm run typecheck` to see errors without building

### Build Errors

**Symptoms:** `npm run build` fails

**Solutions:**
1. Check for TypeScript errors first: `npm run typecheck`
2. Ensure Node.js version is 18+: `node --version`
3. Delete `node_modules` and reinstall: `rm -rf node_modules package-lock.json && npm install`
4. Check Vite config for syntax errors

### Animations Jank or Not Smooth

**Solutions:**
1. Open Chrome DevTools → Performance → Record → Identify long frames
2. Reduce animation duration or simplify transitions
3. Use `will-change` CSS property sparingly
4. Ensure no heavy re-renders during animations

## Production Deployment

### Build

```bash
npm run build
```

Output: `dist/` directory containing:
- `index.html` (entry point)
- `assets/*.js` (JavaScript bundles)
- `assets/*.css` (stylesheets)

### Preview Build Locally

```bash
npm run preview
```

Serves `dist/` at `http://localhost:4173`

### Environment Variables in Production

**Important:** Vite embeds environment variables at **build time**, not runtime.

1. Set `VITE_API_BASE_URL` and `VITE_API_KEY` in the build environment
2. Build the app: `npm run build`
3. The values are baked into the JS bundle
4. **Never commit `.env` to version control** (it's gitignored)

For runtime configuration, use a config endpoint on the backend instead.

### Deployment Targets

**Static Hosting (Vercel, Netlify, Cloudflare Pages):**
- Upload `dist/` directory
- Configure build command: `npm run build`
- Configure output directory: `dist`
- Set environment variables in hosting provider dashboard

**Server (Nginx, Apache):**
- Copy `dist/` to web root (e.g., `/var/www/html`)
- Configure reverse proxy for API calls (if needed)
- Enable gzip compression for `.js` and `.css` files
- Set appropriate cache headers for static assets

**Docker:**
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Bundle Size

Typical production build:
- Main JS bundle: ~200-300 KB (gzipped)
- Vendor chunks: ~150-200 KB (gzipped)
- CSS: ~20-30 KB (gzipped)

**Total initial load:** ~400-500 KB gzipped

Monitor bundle size with:
```bash
npm run build
ls -lh dist/assets
```

## Development Workflow

### Adding a New Page

1. Create component in `src/pages/NewPage.tsx`
2. Add route in `src/main.tsx`:
   ```tsx
   <Route path="new-page" element={<NewPage />} />
   ```
3. Add navigation link in `src/components/Layout.tsx`

### Adding a New API Endpoint

1. Define request/response types in `src/lib/types.ts`
2. Add method to `api` object in `src/lib/api.ts`:
   ```typescript
   async newEndpoint(params: Params): Promise<Response> {
     return request<Response>("/v1/new-endpoint", { body: params });
   }
   ```
3. Use in components with proper error handling

### Styling Guidelines

- **Use Tailwind utilities** for most styling (avoid custom CSS)
- **Extract repeated patterns** to utility classes in `index.css`
- **Use design tokens** (e.g., `bg-surface`, `text-ink`) not raw colors
- **Maintain consistency** with existing component styles

### TypeScript Best Practices

- **Type all props and state** (no `any` except as last resort)
- **Use `interface` for object shapes**, `type` for unions/primitives
- **Import types** from `src/lib/types.ts` for API-related interfaces
- **Enable strict mode** (already enabled in `tsconfig.json`)

## Contributing

When adding features or fixing bugs:

1. **Read code before changing it** (understand existing patterns)
2. **Match the existing code style** (TypeScript, naming conventions)
3. **Run type check before committing**: `npm run typecheck`
4. **Test in mobile and desktop viewports**
5. **Verify keyboard navigation works**
6. **Check accessibility** (Lighthouse audit, screen reader test)

## License

This project is part of the Lesson Content Generator system. See root `LICENSE` file for details.

## Support

For issues or questions:
- Check this README's Troubleshooting section
- Review backend API docs: `http://localhost:8000/docs`
- Check browser console for errors (DevTools → Console)
- Check network requests (DevTools → Network)

---

**Version:** 1.0.0  
**Last Updated:** 2025-01-XX  
**Maintained By:** Lesson Content Generator Team
