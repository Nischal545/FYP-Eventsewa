from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
import time
import json
import base64
import hmac
import hashlib
from django.http import HttpRequest

class CustomSessionMiddleware(MiddlewareMixin):
    """
    Custom session middleware that stores session data in cookies instead of database.
    This is a temporary solution until the database permission issues are resolved.
    """
    
    def process_request(self, request):
        """Process the request and add session data to request object."""
        request.session = {}
        
        # Get session cookie
        session_cookie = request.COOKIES.get('custom_session')
        if session_cookie:
            try:
                # Decode and verify the session data
                parts = session_cookie.split('.')
                if len(parts) == 3:
                    payload, timestamp, signature = parts
                    
                    # Verify signature
                    expected_sig = self._get_signature(payload, timestamp)
                    if hmac.compare_digest(signature, expected_sig):
                        # Check if session is expired
                        if int(timestamp) > int(time.time()):
                            # Session is valid, decode payload
                            decoded = base64.b64decode(payload).decode('utf-8')
                            request.session = json.loads(decoded)
            except Exception as e:
                print(f"Error processing session cookie: {str(e)}")
        
        # Add session methods
        request.session['get'] = lambda key, default=None: request.session.get(key, default)
        request.session['set_expiry'] = lambda timeout: None  # Dummy method
        request.session['flush'] = lambda: request.session.clear()
        request.session['save'] = lambda: None  # Will be handled in process_response
        
        # Original implementation
        setattr(request, '_session', request.session)
    
    def process_response(self, request, response):
        """Process the response and add session cookie if needed."""
        if hasattr(request, 'session') and request.session:
            # Create session cookie
            session_data = {k: v for k, v in request.session.items() if not callable(v)}
            
            if session_data:
                payload = base64.b64encode(json.dumps(session_data).encode('utf-8')).decode('utf-8')
                timestamp = str(int(time.time()) + 86400 * 14)  # 14 days expiry
                signature = self._get_signature(payload, timestamp)
                
                cookie_value = f"{payload}.{timestamp}.{signature}"
                
                # Set cookie
                response.set_cookie(
                    'custom_session',
                    cookie_value,
                    max_age=86400 * 14,  # 14 days
                    httponly=True,
                    samesite='Lax'
                )
        
        return response
    
    def _get_signature(self, payload, timestamp):
        """Generate HMAC signature for session data."""
        key = settings.SECRET_KEY.encode('utf-8')
        message = f"{payload}.{timestamp}".encode('utf-8')
        return hmac.new(key, message, hashlib.sha256).hexdigest()
