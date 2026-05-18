// astro.config.mjs
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';

export default defineConfig({
  site: 'https://aitoolsidea.com',
  integrations: [
    sitemap({
      changefreq: 'weekly',
      priority:   0.7,
      lastmod:    new Date(),
      customPages: [
        'https://aitoolsidea.com/best-ai-tools',
        'https://aitoolsidea.com/compare',
      ],
    }),
    mdx(),
  ],
  markdown: {
    // Allow raw HTML in markdown (needed for schema injection scripts)
    shikiConfig: { theme: 'github-dark' },
  },
  output: 'static',
  build: {
    // Clean asset names for better caching
    assets: '_assets',
  },
});
