# TerraLuna AI frontend

This is the Next.js frontend for TerraLuna AI. It provides the planetary scene and site discovery interface and communicates with the FastAPI backend.

## Folder structure

```text
frontend/
├── app/
│   ├── components/
│   │   ├── CandidateMap.tsx    # Map for candidate locations
│   │   ├── MoonOrbit.tsx       # Moon/orbit scene component
│   │   ├── PlanetSelector.tsx  # Planet selection UI
│   │   ├── PlanetViewer.tsx    # Planet viewing UI
│   │   └── SpaceScene.tsx      # Main 3D space scene
│   ├── favicon.ico             # Browser tab icon
│   ├── globals.css             # Global styles
│   ├── layout.tsx              # Shared page layout and metadata
│   └── page.tsx                # Main application page
├── e2e/
│   └── terraluna.spec.ts       # Playwright end-to-end tests
├── lib/
│   └── api.ts                  # Backend API helpers
├── public/
│   ├── models/                 # 3D model assets
│   ├── textures/               # Planet texture images
│   └── *.svg                   # Static SVG assets
├── package.json                # Scripts and dependencies
├── package-lock.json           # Locked npm dependency versions
├── next.config.ts              # Next.js configuration
├── playwright.config.ts        # Playwright test configuration
├── eslint.config.mjs           # ESLint configuration
└── tsconfig.json               # TypeScript configuration
```

`node_modules/`, `.next/`, and `test-results/` are generated locally by installing dependencies, running Next.js, and running tests. They are not application source files.

## Getting Started

Install dependencies and start the development server from this folder:

```bash
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser. The FastAPI backend should also be running for features that load catalog and comparison data.

## Where to start

- Start at `app/page.tsx` to understand the main screen and how UI components fit together.
- Look in `app/components/` for the planet, map, and 3D scene components.
- Look in `lib/api.ts` for frontend requests to the backend.
- Look in `app/globals.css` for global styling and `app/layout.tsx` for the shared layout.
- Run `npm run test:e2e` to execute the Playwright browser tests.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
