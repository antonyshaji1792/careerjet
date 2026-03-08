import time
import logging
from functools import wraps
from flask import request, jsonify
from app import extensions

logger = logging.getLogger(__name__)


def rate_limit(limit=10, period=60):
    """
    Redis-based rate limiting decorator.
    - limit: maximum requests
    - period: time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not extensions.redis_client:
                # Fallback if Redis is not configured
                return f(*args, **kwargs)

            # Use IP address or user_id for key
            from flask_login import current_user
            identifier = current_user.id if current_user.is_authenticated else request.remote_addr
            key = f"rate_limit:{f.__name__}:{identifier}"

            try:
                pipeline = extensions.redis_client.pipeline()
                pipeline.incr(key)
                pipeline.expire(key, period)

                results = pipeline.execute()
                
                request_count = results[0]
                
                if request_count > limit:
                    logger.warning(f"RATE LIMIT EXCEEDED: {identifier} on {f.__name__} ({request_count}/{limit})")
                    return jsonify({
                        'error': 'too_many_requests',
                        'message': f"Rate limit exceeded. Please wait {period} seconds.",
                        'limit': limit,
                        'period': period
                    }), 429

            except Exception as e:
                logger.error(f"Rate limiter Redis error: {str(e)}")
                # Fail open to avoid blocking users if Redis is down
                return f(*args, **kwargs)

            return f(*args, **kwargs)
        return wrapped
    return decorator
