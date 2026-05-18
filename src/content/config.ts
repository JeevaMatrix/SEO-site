// src/content/config.ts
// Defines the schema for all blog post frontmatter.
// Astro validates every article against this at build time.

import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string()
      .min(10, 'Title too short')
      .max(70,  'Title too long for SEO'),
    description: z.string()
      .min(80,  'Description too short (min 80 chars)')
      .max(160, 'Description too long for SEO (max 160 chars)'),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    image: z.string().optional().default(
      'https://images.unsplash.com/photo-1551434678-e076c223a692?w=1200&q=80'
    ),
    tags: z.array(z.string()).default([]),
    affiliate: z.string().optional().default(''),
    draft: z.boolean().optional().default(false),
  }),
});

export const collections = { blog };
