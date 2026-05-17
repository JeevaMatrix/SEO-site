// src/content/config.ts
// Defines the schema for blog post frontmatter.
// Astro validates all articles against this — catches missing fields early.

import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().max(70, 'Title too long for SEO (max 70 chars)'),
    description: z.string()
      .min(100, 'Description too short (min 100 chars)')
      .max(160, 'Description too long for SEO (max 160 chars)'),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    image: z.string().url().optional(),
    tags: z.array(z.string()).default([]),
    affiliate: z.string().optional().default(''),
    draft: z.boolean().optional().default(false),
  }),
});

export const collections = { blog };
