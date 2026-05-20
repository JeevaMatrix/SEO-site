// src/pages/rss.xml.ts
// Generates /rss.xml — submit to Feedly, Inoreader, feed aggregators
// Also used by IFTTT/Zapier to auto-post new articles to Twitter/LinkedIn

import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';

export async function GET(context: APIContext) {
  const posts = await getCollection('blog', ({ data }) => !data.draft);
  const sorted = posts.sort(
    (a, b) => new Date(b.data.pubDate).valueOf() - new Date(a.data.pubDate).valueOf()
  );

  return rss({
    title: 'AI Tools Idea — Weekly Reviews',
    description: 'Honest, in-depth reviews of AI tools for small business owners and freelancers.',
    site: context.site!,
    items: sorted.map((post) => ({
      title:       post.data.title,
      pubDate:     new Date(post.data.pubDate),
      description: post.data.description,
      link:        `/blog/${post.slug}/`,
      categories:  post.data.tags ?? [],
    })),
    customData: `<language>en-us</language><ttl>1440</ttl>`,
    stylesheet: false,
  });
}
