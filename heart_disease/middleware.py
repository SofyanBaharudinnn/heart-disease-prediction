import time
# pyrefly: ignore [missing-import]
from django.core.cache import cache
# pyrefly: ignore [missing-import]
from django.http import JsonResponse
# pyrefly: ignore [missing-import]
from django.shortcuts import render
# pyrefly: ignore [missing-import]
from django.conf import settings

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip rate limiting if DEBUG is True (local development/testing)
        if settings.DEBUG:
            return self.get_response(request)

        # 2. Get client IP address (supporting reverse proxy headers like Cloudflare/Nginx)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # 3. Determine the rate limit parameters based on request path
        path = request.path
        if path.startswith('/train/') or path.startswith('/training/'):
            limit = 5      # Strictest limit for heavy model training
            window = 60    # 1 minute window
            key_suffix = "train"
        elif path.startswith('/predict/'):
            limit = 10     # Strict limit for prediction runs
            window = 60
            key_suffix = "predict"
        elif path.startswith('/login/') or path.startswith('/register/') or path.startswith('/social-login/'):
            limit = 10     # Prevent brute-force logins and registrations
            window = 60
            key_suffix = "auth"
        else:
            limit = 100    # General rate limit
            window = 60
            key_suffix = "general"

        cache_key = f"rl_{key_suffix}_{ip}"

        # 4. Fetch request history for this IP
        request_history = cache.get(cache_key, [])
        now = time.time()

        # Filter out timestamps outside the current window
        request_history = [t for t in request_history if now - t < window]

        # 5. Check if limit is exceeded
        if len(request_history) >= limit:
            lang = request.session.get('lang', 'id')
            
            # For API/AJAX requests, return JSON
            is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or path.startswith('/api/')
            if is_ajax:
                return JsonResponse({
                    'error': 'Too many requests. Please try again later.' if lang == 'en' else 'Terlalu banyak permintaan. Silakan coba lagi nanti.'
                }, status=429)

            # For regular page views, render a custom premium 429 page
            retry_after = int(window - (now - request_history[0])) if request_history else window
            context = {
                'retry_after': retry_after,
                'current_lang': lang,
            }
            return render(request, 'heart_disease/rate_limit.html', context, status=429)

        # 6. Record the current request timestamp
        request_history.append(now)
        cache.set(cache_key, request_history, window)

        return self.get_response(request)
