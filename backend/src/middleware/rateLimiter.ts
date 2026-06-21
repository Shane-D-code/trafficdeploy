import { Request, Response, NextFunction } from 'express';

const requestCounts = new Map<string, { count: number; resetTime: number }>();

export function rateLimiter(req: Request, res: Response, next: NextFunction): void {
  if (req.path.startsWith('/api/detection/status/')) {
    return next();
  }
  const windowMs = (parseInt(process.env.RATE_LIMIT_WINDOW || '15') * 60 * 1000);
  const maxRequests = parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '200');
  const ip = req.ip || req.socket.remoteAddress || 'unknown';

  const now = Date.now();
  let entry = requestCounts.get(ip);

  if (!entry || now > entry.resetTime) {
    entry = { count: 0, resetTime: now + windowMs };
    requestCounts.set(ip, entry);
  }

  entry.count++;

  if (entry.count > maxRequests) {
    res.status(429).json({
      success: false,
      error: 'Too many requests, please try again later.'
    });
    return;
  }

  next();
}
