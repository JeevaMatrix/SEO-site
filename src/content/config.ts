// src/content/config.ts
// Defines the schema for all blog post frontmatter.
// Astro validates every article against this at build time.

import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string()
      .min(10, 'Title too short')
      .max(120, 'Title too long'),  // relaxed — Groq titles can be long; og:title is truncated in BaseLayout
    description: z.string().optional().default('An in-depth guide to help small business owners choose the right tools.'),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    image: z.string().optional().default(
      'https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200&q=80'
    ),
    tags: z.array(z.string()).default([]),
    affiliate: z.string().optional().default(''),
    affiliateUrl: z.string().optional().default(''),
    amazonProducts: z.array(z.object({
      title: z.string(),
      price: z.string(),
      url:   z.string(),
      cat:   z.string(),
    })).optional().default([]),
    draft: z.boolean().optional().default(false),
    // title max relaxed to 100 — Groq generates long titles, truncation handled in generator
  }),
});

// NOTE: title max is intentionally NOT enforced here (removed .max(70))
// because Groq-generated titles like "X vs Y — Complete Guide [2026]"
// often exceed 70 chars. SEO title tag is truncated separately in BaseLayout.astro.

export const collections = { blog };