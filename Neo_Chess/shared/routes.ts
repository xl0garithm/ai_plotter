import { z } from 'zod';
import { insertGameSchema, games } from './schema';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

export const api = {
  games: {
    list: {
      method: 'GET' as const,
      path: '/api/games',
      responses: {
        200: z.array(z.custom<typeof games.$inferSelect>()),
      },
    },
    create: {
      method: 'POST' as const,
      path: '/api/games',
      input: insertGameSchema,
      responses: {
        201: z.custom<typeof games.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
  },
  chess: {
    preview: {
      method: 'GET' as const,
      path: '/api/chess/preview',
      query: z.object({
        size: z.string().optional().default('800'),
        hatch_spacing: z.string().optional().default('6.0'),
      }),
      responses: {
        200: z.string(),
      },
    },
    demoPreview: {
      method: 'GET' as const,
      path: '/api/chess/demo/preview',
      responses: {
        200: z.string(),
      },
    },
    demoRun: {
      method: 'POST' as const,
      path: '/api/chess/demo/run',
      responses: {
        200: z.object({
          success: z.boolean(),
          dry_run: z.boolean().optional(),
          stats: z.record(z.any()),
        }),
      },
    },
    pickPlaceDemo: {
      method: 'POST' as const,
      path: '/api/chess/pick-place-demo',
      input: z.object({
        from: z.string().optional().default('e2'),
        to: z.string().optional().default('e4'),
      }).optional(),
      responses: {
        200: z.object({
          success: z.boolean(),
          dry_run: z.boolean().optional(),
          stats: z.record(z.any()),
          gcode_lines: z.array(z.string()).optional(),
        }),
        400: errorSchemas.validation,
      },
    },
    move: {
      method: 'POST' as const,
      path: '/api/chess/move',
      input: z.object({
        from: z.string(),
        to: z.string(),
        piece: z.string(),
        color: z.enum(['w', 'b']),
        flags: z.string().optional().default(''),
        captured: z.string().nullable().optional(),
        promotion: z.string().nullable().optional(),
        capture_index: z.number().optional().default(0),
      }),
      responses: {
        200: z.object({
          success: z.boolean(),
          dry_run: z.boolean().optional(),
          stats: z.record(z.any()),
          gcode_lines: z.array(z.string()).optional(),
        }),
        400: errorSchemas.validation,
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
