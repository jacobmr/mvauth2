# Mobile OAuth Implementation with Clerk

## Overview

This document provides a comprehensive guide for implementing OAuth authentication in a React Native mobile app using Clerk, without requiring Clerk's $100/month satellite domain add-on.

## Architecture

```
Mobile App (React Native) → Backend API (FastAPI) → Clerk Frontend API → OAuth Providers
```

## Problem Statement

Clerk's official React Native SDK requires Expo or doesn't support bare React Native well. Additionally, using Clerk's satellite domains for mobile OAuth costs $100/month. This implementation provides a workaround using WebView and direct Clerk API integration.

## Solution Components

### 1. Backend API (FastAPI)

**File**: `/packages/api/main_simple.py`

The backend serves as a proxy to Clerk's API and generates the correct OAuth URLs for mobile consumption.

#### Key Endpoints:

- `POST /mobile/auth/oauth-init` - Initialize OAuth flow
- `POST /mobile/auth/oauth-complete` - Complete OAuth and get user data
- `POST /mobile/auth/login` - Email/password login (future)
- `GET /mobile/health` - Health check

#### OAuth Initialization Implementation:

```python
@app.post("/mobile/auth/oauth-init")
async def mobile_oauth_init(provider_data: dict):
    """Initialize OAuth flow for mobile by returning direct Clerk sign-in URL"""
    provider = provider_data.get("provider")  # 'oauth_google' or 'oauth_apple'
    
    if not provider:
        return {"success": False, "error": "Provider required"}
    
    try:
        clerk_publishable = os.getenv("CLERK_PUBLISHABLE_KEY", "").strip()
        
        # Extract instance domain from publishable key
        import base64
        encoded_domain = clerk_publishable.replace("pk_test_", "").replace("pk_live_", "")
        decoded_domain = base64.b64decode(encoded_domain + "==").decode('utf-8')
        domain = decoded_domain.rstrip('$')
        
        # Generate Clerk sign-in URL with OAuth redirect
        clerk_signin_url = f"https://{domain}/sign-in?redirect_url=https://auth.brasilito.org/mobile/auth/oauth-callback#/factor-one"
        
        return {
            "success": True,
            "redirectUrl": clerk_signin_url,
            "signInId": "webview_oauth",
            "provider": provider.replace("oauth_", ""),
            "note": "Mobile app should open this URL in WebView and monitor for callback"
        }
    except Exception as e:
        return {"success": False, "error": f"OAuth initialization failed: {str(e)}"}
```

### 2. Mobile App Components

#### BackendAuthContext (`/src/contexts/BackendAuthContext.tsx`)

Manages authentication state and API communication:

```typescript
const BACKEND_URL = 'https://auth.brasilito.org/mobile';

interface AuthContextType {
  user: User | null;
  isLoaded: boolean;
  isSignedIn: boolean;
  signIn: (email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  signInWithOAuth: (provider: 'google' | 'apple') => Promise<{success: boolean, redirectUrl?: string, signInId?: string, error?: string}>;
  completeOAuth: (signInId: string) => Promise<boolean>;
}

const signInWithOAuth = async (provider: 'google' | 'apple') => {
  try {
    const oauthProvider = provider === 'google' ? 'oauth_google' : 'oauth_apple';
    
    const response = await fetch(`${BACKEND_URL}/auth/oauth-init`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ provider: oauthProvider }),
    });

    const data = await response.json();
    if (data.success) {
      return {
        success: true,
        redirectUrl: data.redirectUrl,
        signInId: data.signInId
      };
    } else {
      return {success: false, error: data.error || 'OAuth initialization failed'};
    }
  } catch (error) {
    return {success: false, error: 'Failed to initialize OAuth'};
  }
};
```

#### OAuthWebView Component (`/src/components/OAuthWebView.tsx`)

Handles OAuth flow in WebView:

```typescript
const OAuthWebView: React.FC<OAuthWebViewProps> = ({
  visible, url, onSuccess, onError, onClose, provider,
}) => {
  const handleNavigationStateChange = (navState: any) => {
    const {url: currentUrl} = navState;
    
    // Check if OAuth completed successfully
    if (currentUrl.includes('/sso-callback') || 
        currentUrl.includes('?__clerk_') ||
        currentUrl.includes('__clerk_db_jwt') ||
        currentUrl.includes('session_id') ||
        currentUrl.includes('clerk-session')) {
      
      console.log('OAuth success detected in URL:', currentUrl);
      onSuccess({ success: true, url: currentUrl });
      return;
    }

    // Check for OAuth errors
    if (currentUrl.includes('error=') || 
        currentUrl.includes('oauth_error') || 
        currentUrl.includes('access_denied')) {
      
      const urlParams = new URLSearchParams(currentUrl.split('?')[1] || '');
      const error = urlParams.get('error') || urlParams.get('error_description') || 'OAuth authentication failed';
      onError(error);
      return;
    }
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
      <SafeAreaView style={styles.container}>
        <WebView
          source={{ uri: url }}
          onNavigationStateChange={handleNavigationStateChange}
          onError={(error) => onError('Failed to load authentication page')}
          javaScriptEnabled={true}
          domStorageEnabled={true}
          startInLoadingState={true}
        />
      </SafeAreaView>
    </Modal>
  );
};
```

#### Login Screen (`/src/screens/BackendLoginScreen.tsx`)

Main authentication interface:

```typescript
const handleOAuthSignIn = async (provider: 'google' | 'apple') => {
  setIsLoading(true);
  try {
    const result = await signInWithOAuth(provider);
    
    if (result.success && result.redirectUrl && result.signInId) {
      setOauthWebView({
        visible: true,
        url: result.redirectUrl,
        provider,
        signInId: result.signInId,
      });
    } else {
      Alert.alert('OAuth Error', result.error || 'Failed to start OAuth flow');
    }
  } catch (error: any) {
    Alert.alert('OAuth Error', error.message || 'Something went wrong');
  } finally {
    setIsLoading(false);
  }
};

const handleOAuthSuccess = async (data: any) => {
  setOauthWebView(prev => ({...prev, visible: false}));
  
  setIsLoading(true);
  try {
    const success = await completeOAuth(oauthWebView.signInId);
    if (!success) {
      Alert.alert('Login Failed', 'OAuth authentication completed but token exchange failed');
    }
  } catch (error: any) {
    Alert.alert('Login Error', error.message || 'OAuth completion failed');
  } finally {
    setIsLoading(false);
  }
};
```

## Environment Configuration

### Backend Environment Variables

Required in Vercel deployment:

```bash
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Clerk Dashboard Configuration

1. **Social Connections**:
   - Navigate to [SSO Connections](https://dashboard.clerk.com/last-active?path=user-authentication/sso-connections)
   - Enable Google and Apple OAuth providers
   - For development: no additional config needed
   - For production: configure custom OAuth credentials

2. **Mobile OAuth Redirects**:
   - Go to [Native Applications](https://dashboard.clerk.com/last-active?path=native-applications)
   - Find "Allowlist for mobile OAuth redirect"
   - Add: `https://auth.brasilito.org/mobile/auth/oauth-callback`

## Deployment Architecture

### Backend Deployment (Vercel)

```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "main_simple.py",
      "use": "@vercel/python",
      "config": {
        "maxLambdaSize": "15mb",
        "runtime": "python3.11"
      }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/main_simple.py"
    }
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

### Dependencies

```txt
# requirements.txt
fastapi
uvicorn
python-dotenv
httpx
PyJWT
sqlalchemy
asyncpg
pydantic-settings
```

## Authentication Flow

### OAuth Flow Sequence

1. **Mobile App**: User taps "Continue with Google/Apple"
2. **Mobile App**: Calls `POST /mobile/auth/oauth-init` with provider
3. **Backend API**: Extracts Clerk domain from publishable key
4. **Backend API**: Returns Clerk sign-in URL with callback redirect
5. **Mobile App**: Opens URL in WebView modal
6. **WebView**: User completes OAuth with Google/Apple
7. **Clerk**: Redirects to callback URL with session data
8. **WebView**: Detects callback URL patterns
9. **Mobile App**: Closes WebView, calls `POST /mobile/auth/oauth-complete`
10. **Backend API**: Validates session and returns user data
11. **Mobile App**: Stores session data and updates UI

### URL Pattern Detection

The WebView monitors for these callback patterns:
- `/sso-callback`
- `?__clerk_`
- `__clerk_db_jwt`
- `session_id`
- `clerk-session`

## Security Considerations

1. **No Satellite Domain**: Avoids $100/month cost by using Clerk's default domain
2. **WebView Isolation**: OAuth happens in isolated WebView context
3. **Session Validation**: Backend validates all sessions with Clerk
4. **Secure Storage**: Mobile app uses AsyncStorage for session persistence
5. **HTTPS Only**: All API communication over HTTPS

## Troubleshooting

### Common Issues

1. **404 on OAuth URLs**: Check if redirect URL is allowlisted in Clerk dashboard
2. **"Browser unauthenticated"**: Using wrong API approach - use WebView instead
3. **Slow builds**: Pin dependency versions in requirements.txt
4. **WebView not detecting callback**: Check URL pattern matching logic

### Debug Endpoints

- `GET /mobile/debug` - Shows environment configuration
- `GET /mobile/health` - Basic health check

### Testing

```bash
# Test OAuth initialization
curl -X POST https://auth.brasilito.org/mobile/auth/oauth-init \
  -H "Content-Type: application/json" \
  -d '{"provider": "oauth_google"}'

# Expected response:
{
  "success": true,
  "redirectUrl": "https://deciding-skylark-2.clerk.accounts.dev/sign-in?redirect_url=...",
  "signInId": "webview_oauth",
  "provider": "google"
}
```

## Performance Optimizations

1. **Dependency Management**: Removed problematic `clerk` PyPI package
2. **Build Caching**: Vercel automatically caches builds
3. **Minimal Dependencies**: Only essential packages included
4. **Python 3.11**: Faster runtime performance

## Limitations

1. **Email/Password Login**: Currently only OAuth implemented
2. **Development Only**: Some features may need adjustment for production
3. **WebView Dependency**: Requires react-native-webview package
4. **Network Dependency**: Requires internet connection for OAuth

## Future Enhancements

1. Implement email/password authentication
2. Add biometric authentication
3. Implement session refresh logic
4. Add offline capability
5. Enhance error handling and user feedback

## Cost Analysis

- **Traditional Clerk Mobile**: $100/month for satellite domain
- **This Implementation**: $0/month additional cost (uses existing Clerk plan)
- **Savings**: $1,200/year

This implementation provides full OAuth functionality without the satellite domain cost, making it ideal for development and cost-conscious production deployments.