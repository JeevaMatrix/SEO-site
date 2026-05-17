// src/content/config.ts
// Defines the schema for blog post frontmatter.
// Astro validates all articles against this — catches missing fields early.

import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().max(70, 'Title too long for SEO (max 70 chars)'),
    description: z.string()
      .min(50, 'Description too short (min 50 chars)')
      .max(200, 'Description too long (max 200 chars)'),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    // Allow relative paths as well as URLs
    image: z.string().optional(),
    tags: z.array(z.string()).default([]),
    affiliate: z.string().optional().default(''),
    draft: z.boolean().optional().default(false),
  }),
});

export const collections = { blog };
