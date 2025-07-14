# How to Implement Clerk OAuth in React Native Without Paying $100/Month

*A complete guide to building mobile authentication with Clerk using WebView and Backend API approach*

## The Problem

If you've tried to implement Clerk authentication in a React Native app, you've probably encountered these challenges:

1. **Clerk's React Native SDK** doesn't work well with bare React Native (requires Expo)
2. **Satellite domains** cost $100/month just for mobile OAuth
3. **Documentation gaps** for custom mobile implementations
4. **Complex OAuth flows** that are hard to debug

After spending days trying different approaches, I found a solution that works reliably and costs nothing extra. Here's how to implement Clerk OAuth in React Native using a WebView approach with a backend proxy.

## The Solution Architecture

Instead of fighting with Clerk's mobile SDK, we'll use a hybrid approach:

```
React Native App → Backend API → Clerk Frontend API → OAuth Providers
      ↓
   WebView Modal → Clerk OAuth Pages → Callback Detection
```

This approach:
- ✅ Works with bare React Native
- ✅ Costs $0 extra (no satellite domain needed)
- ✅ Supports Google, Apple, and other OAuth providers
- ✅ Provides full session management
- ✅ Easy to debug and maintain

## Step 1: Backend API Setup

First, we need a backend API to proxy Clerk requests. I'm using FastAPI, but you can adapt this to any backend framework.

### Install Dependencies

```bash
pip install fastapi uvicorn python-dotenv httpx
```

### Create the OAuth Endpoint

```python
# main.py
from fastapi import FastAPI
import os
import base64

app = FastAPI()

@app.post("/mobile/auth/oauth-init")
async def mobile_oauth_init(provider_data: dict):
    """Initialize OAuth flow for mobile"""
    provider = provider_data.get("provider")  # 'oauth_google' or 'oauth_apple'
    
    if not provider:
        return {"success": False, "error": "Provider required"}
    
    try:
        # Get Clerk configuration
        clerk_publishable = os.getenv("CLERK_PUBLISHABLE_KEY", "").strip()
        
        # Extract instance domain from publishable key
        # pk_test_base64_encoded_domain → domain.clerk.accounts.dev
        encoded_domain = clerk_publishable.replace("pk_test_", "").replace("pk_live_", "")
        decoded_domain = base64.b64decode(encoded_domain + "==").decode('utf-8')
        domain = decoded_domain.rstrip('$')
        
        # Generate Clerk sign-in URL
        callback_url = "https://your-api.com/mobile/auth/oauth-callback"
        clerk_signin_url = f"https://{domain}/sign-in?redirect_url={callback_url}#/factor-one"
        
        return {
            "success": True,
            "redirectUrl": clerk_signin_url,
            "signInId": "webview_oauth",
            "provider": provider.replace("oauth_", "")
        }
    except Exception as e:
        return {"success": False, "error": f"OAuth failed: {str(e)}"}

@app.post("/mobile/auth/oauth-complete")
async def mobile_oauth_complete(completion_data: dict):
    """Complete OAuth flow and return user data"""
    # Implementation for session validation
    # (See full implementation in the repository)
    pass
```

### Environment Variables

```bash
CLERK_SECRET_KEY=sk_test_your_secret_key
CLERK_PUBLISHABLE_KEY=pk_test_your_publishable_key
```

## Step 2: React Native Implementation

### Install Required Packages

```bash
npm install react-native-webview @react-native-async-storage/async-storage
```

For iOS, run:
```bash
cd ios && pod install
```

### Create the Auth Context

```typescript
// contexts/AuthContext.tsx
import React, {createContext, useContext, useEffect, useState} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const BACKEND_URL = 'https://your-api.com/mobile';

interface User {
  id: string;
  email: string;
  fullName: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  isLoaded: boolean;
  isSignedIn: boolean;
  signInWithOAuth: (provider: 'google' | 'apple') => Promise<{
    success: boolean; 
    redirectUrl?: string; 
    signInId?: string; 
    error?: string;
  }>;
  completeOAuth: (signInId: string) => Promise<boolean>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{children: React.ReactNode}> = ({children}) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    checkExistingSession();
  }, []);

  const checkExistingSession = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('auth_token');
      const storedUser = await AsyncStorage.getItem('user_data');
      
      if (storedToken && storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Error checking session:', error);
    } finally {
      setIsLoaded(true);
    }
  };

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
        return {
          success: false,
          error: data.error || 'OAuth initialization failed'
        };
      }
    } catch (error) {
      return {
        success: false,
        error: 'Failed to initialize OAuth'
      };
    }
  };

  const completeOAuth = async (signInId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${BACKEND_URL}/auth/oauth-complete`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ signInId }),
      });

      const data = await response.json();

      if (data.success) {
        setUser(data.user);
        await AsyncStorage.setItem('auth_token', data.token);
        await AsyncStorage.setItem('user_data', JSON.stringify(data.user));
        return true;
      }
      return false;
    } catch (error) {
      console.error('OAuth completion error:', error);
      return false;
    }
  };

  const signOut = async () => {
    setUser(null);
    await AsyncStorage.removeItem('auth_token');
    await AsyncStorage.removeItem('user_data');
  };

  return (
    <AuthContext.Provider value={{
      user,
      isLoaded,
      isSignedIn: !!user,
      signInWithOAuth,
      completeOAuth,
      signOut,
    }}>
      {children}
    </AuthContext.Provider>
  );
};
```

### Create the OAuth WebView Component

```typescript
// components/OAuthWebView.tsx
import React from 'react';
import {
  Modal,
  View,
  StyleSheet,
  TouchableOpacity,
  Text,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import {WebView} from 'react-native-webview';

interface OAuthWebViewProps {
  visible: boolean;
  url: string;
  onSuccess: (data: any) => void;
  onError: (error: string) => void;
  onClose: () => void;
  provider: 'google' | 'apple';
}

const OAuthWebView: React.FC<OAuthWebViewProps> = ({
  visible,
  url,
  onSuccess,
  onError,
  onClose,
  provider,
}) => {
  const handleNavigationStateChange = (navState: any) => {
    const {url: currentUrl} = navState;
    
    console.log('OAuth WebView URL:', currentUrl);

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
      const error = urlParams.get('error') || 
                   urlParams.get('error_description') || 
                   'OAuth authentication failed';
      onError(error);
      return;
    }

    // Check if user cancelled
    if (currentUrl.includes('cancelled') || currentUrl.includes('cancel')) {
      onError('User cancelled authentication');
      return;
    }
  };

  return (
    <Modal visible={visible} animationType="slide" presentationStyle="pageSheet">
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>
            Sign in with {provider === 'google' ? 'Google' : 'Apple'}
          </Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Text style={styles.closeButtonText}>Cancel</Text>
          </TouchableOpacity>
        </View>
        
        <WebView
          source={{ uri: url }}
          onNavigationStateChange={handleNavigationStateChange}
          onError={() => onError('Failed to load authentication page')}
          style={styles.webView}
          javaScriptEnabled={true}
          domStorageEnabled={true}
          startInLoadingState={true}
          renderLoading={() => (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#6366f1" />
              <Text style={styles.loadingText}>Loading authentication...</Text>
            </View>
          )}
        />
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#111827',
  },
  closeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#f3f4f6',
    borderRadius: 6,
  },
  closeButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
  },
  webView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6b7280',
  },
});

export default OAuthWebView;
```

### Create the Login Screen

```typescript
// screens/LoginScreen.tsx
import React, {useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import {useAuth} from '../contexts/AuthContext';
import OAuthWebView from '../components/OAuthWebView';

const LoginScreen: React.FC = () => {
  const {signInWithOAuth, completeOAuth} = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [oauthWebView, setOauthWebView] = useState<{
    visible: boolean;
    url: string;
    provider: 'google' | 'apple';
    signInId: string;
  }>({
    visible: false,
    url: '',
    provider: 'google',
    signInId: '',
  });

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
    console.log('OAuth success data:', data);
    setOauthWebView(prev => ({...prev, visible: false}));
    
    setIsLoading(true);
    try {
      const success = await completeOAuth(oauthWebView.signInId);
      if (!success) {
        Alert.alert('Login Failed', 'OAuth completed but token exchange failed');
      }
    } catch (error: any) {
      console.error('OAuth completion error:', error);
      Alert.alert('Login Error', error.message || 'OAuth completion failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthError = (error: string) => {
    console.error('OAuth error:', error);
    setOauthWebView(prev => ({...prev, visible: false}));
    Alert.alert('OAuth Error', error);
  };

  const handleOAuthClose = () => {
    setOauthWebView(prev => ({...prev, visible: false}));
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Welcome to MyApp</Text>
        <Text style={styles.subtitle}>Sign in to continue</Text>

        <TouchableOpacity
          style={[styles.button, styles.googleButton]}
          onPress={() => handleOAuthSignIn('google')}
          disabled={isLoading}
        >
          <Text style={styles.googleButtonText}>Continue with Google</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.appleButton]}
          onPress={() => handleOAuthSignIn('apple')}
          disabled={isLoading}
        >
          <Text style={styles.appleButtonText}>Continue with Apple</Text>
        </TouchableOpacity>

        {isLoading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#6366f1" />
            <Text style={styles.loadingText}>Signing in...</Text>
          </View>
        )}
      </View>

      <OAuthWebView
        visible={oauthWebView.visible}
        url={oauthWebView.url}
        provider={oauthWebView.provider}
        onSuccess={handleOAuthSuccess}
        onError={handleOAuthError}
        onClose={handleOAuthClose}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    marginBottom: 40,
  },
  button: {
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  googleButton: {
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#d1d5db',
  },
  googleButtonText: {
    color: '#374151',
    fontSize: 16,
    fontWeight: '600',
  },
  appleButton: {
    backgroundColor: '#000',
  },
  appleButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  loadingContainer: {
    alignItems: 'center',
    marginTop: 20,
  },
  loadingText: {
    marginTop: 8,
    fontSize: 14,
    color: '#6b7280',
  },
});

export default LoginScreen;
```

## Step 3: Clerk Dashboard Configuration

### 1. Enable OAuth Providers

1. Go to [SSO Connections](https://dashboard.clerk.com/last-active?path=user-authentication/sso-connections)
2. Enable Google and Apple OAuth
3. For development, no additional config needed
4. For production, add custom OAuth credentials

### 2. Configure Mobile Redirects

1. Navigate to [Native Applications](https://dashboard.clerk.com/last-active?path=native-applications)
2. Find "Allowlist for mobile OAuth redirect"
3. Add your callback URL: `https://your-api.com/mobile/auth/oauth-callback`

## Step 4: Testing

### Test the Backend

```bash
curl -X POST https://your-api.com/mobile/auth/oauth-init \
  -H "Content-Type: application/json" \
  -d '{"provider": "oauth_google"}'
```

Expected response:
```json
{
  "success": true,
  "redirectUrl": "https://your-clerk-instance.clerk.accounts.dev/sign-in?redirect_url=...",
  "signInId": "webview_oauth",
  "provider": "google"
}
```

### Test the Mobile App

1. Build and install the app on a device/simulator
2. Tap "Continue with Google"
3. WebView should open with Clerk's sign-in page
4. Complete OAuth flow
5. App should detect success and close WebView
6. User should be logged in

## Troubleshooting

### Common Issues

**"Failed to initialize OAuth"**
- Check your backend URL is correct
- Verify environment variables are set
- Test backend endpoint with curl

**"Browser unauthenticated"**
- You're using the wrong Clerk API approach
- Make sure you're using the WebView method, not direct API calls

**WebView doesn't detect OAuth success**
- Check the callback URL patterns in `handleNavigationStateChange`
- Enable console logging to see what URLs are being visited
- Verify your callback URL is allowlisted in Clerk

**Build errors**
- Make sure react-native-webview is properly installed
- Run `cd ios && pod install` for iOS
- Check that AsyncStorage is installed correctly

## Why This Approach Works

1. **No Satellite Domain**: Uses Clerk's default domain, saving $100/month
2. **WebView Isolation**: OAuth happens in secure WebView context
3. **Backend Validation**: All sessions validated server-side with Clerk
4. **Cross-Platform**: Works on both iOS and Android
5. **Debuggable**: Easy to see what's happening in the OAuth flow

## Production Considerations

1. **Error Handling**: Add comprehensive error handling and retry logic
2. **Loading States**: Implement proper loading indicators
3. **Session Refresh**: Add token refresh mechanism
4. **Offline Handling**: Cache user data for offline access
5. **Security**: Validate all sessions server-side

## Conclusion

This approach gives you full Clerk OAuth functionality in React Native without the complexity and cost of satellite domains. The WebView method is reliable, secure, and works across all platforms.

The key insight is that instead of fighting Clerk's mobile limitations, we use the web OAuth flow in a WebView and detect completion through URL monitoring. This is actually more reliable than native SDK approaches and gives you complete control over the authentication experience.

## Complete Code Repository

Find the complete working implementation at: [GitHub Repository Link]

---

*Have questions? Found this helpful? Let me know in the comments or reach out on Twitter [@yourhandle]*