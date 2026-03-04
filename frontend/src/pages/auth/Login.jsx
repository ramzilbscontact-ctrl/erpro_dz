import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signInWithPopup } from 'firebase/auth'
import { auth, googleProvider } from '../../firebase'
import { authAPI } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'

export default function Login() {
  const [form, setForm]         = useState({ email: '', password: '' })
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [gLoading, setGLoading] = useState(false)
  const { setTokens, setUser }  = useAuthStore()
  const navigate = useNavigate()

  // ── Helper: store tokens and redirect ──────────────────────
  const handleAuthSuccess = async (tokens) => {
    setTokens(tokens.access, tokens.refresh)
    try {
      const me = await authAPI.me()
      setUser(me.data)
    } catch {}
    navigate('/')
  }

  // ── Email / password login ──────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await authAPI.login(form)
      await handleAuthSuccess(data.tokens)
    } catch (err) {
      if (!err.response) {
        setError('Serveur indisponible — réessayez dans quelques secondes')
      } else {
        setError(
          err.response.data?.detail ||
          err.response.data?.non_field_errors?.[0] ||
          'Identifiants incorrects'
        )
      }
    } finally {
      setLoading(false)
    }
  }

  // ── Google login via Firebase Auth ──────────────────────────
  const handleGoogleLogin = async () => {
    setError('')
    setGLoading(true)
    try {
      const result = await signInWithPopup(auth, googleProvider)
      // Récupère le Google OAuth access token depuis Firebase
      const credential = result._tokenResponse
      const accessToken = credential?.oauthAccessToken
      if (!accessToken) throw new Error('No access token from Google')
      const { data } = await authAPI.googleLogin(accessToken)
      await handleAuthSuccess(data.tokens)
    } catch (err) {
      if (err.code === 'auth/popup-closed-by-user') {
        setError('Connexion Google annulée')
      } else if (err.code === 'auth/popup-blocked') {
        setError('Popup bloquée — autorisez les popups pour ce site')
      } else {
        setError(err.response?.data?.detail || 'Erreur Google OAuth')
      }
    } finally {
      setGLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary-600 rounded-2xl mb-4 shadow-lg">
            <span className="text-white text-xl font-bold">E</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ERPro DZ</h1>
          <p className="text-gray-500 text-sm mt-1">Connectez-vous à votre espace</p>
        </div>

        {/* Card */}
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Adresse e-mail
              </label>
              <input
                type="email"
                className="input"
                placeholder="vous@example.com"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Mot de passe
              </label>
              <input
                type="password"
                className="input"
                placeholder="••••••••"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading || gLoading}
              className="btn-primary w-full justify-center py-2.5 mt-2"
            >
              {loading ? 'Connexion…' : 'Se connecter'}
            </button>
          </form>

          {/* Separator */}
          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200" />
            </div>
            <div className="relative flex justify-center text-xs text-gray-400">
              <span className="bg-white px-3">ou</span>
            </div>
          </div>

          {/* Google button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading || gLoading}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {gLoading ? (
              <span className="text-gray-500">Connexion en cours…</span>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#4285F4" d="M44.5 20H24v8.5h11.8C34.3 33.6 29.7 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 6 1.1 8.2 3l6-6C34.5 5.1 29.5 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21c10.9 0 20.4-7.9 20.4-21 0-1.3-.1-2.7-.4-4z"/>
                  <path fill="#34A853" d="M6.3 14.7l6.6 4.8C14.5 15.1 18.9 12 24 12c3.1 0 6 1.1 8.2 3l6-6C34.5 5.1 29.5 3 24 3 16.3 3 9.7 7.8 6.3 14.7z"/>
                  <path fill="#FBBC05" d="M24 45c5.5 0 10.5-1.9 14.4-5l-6.6-5.4C29.7 36.4 27 37 24 37c-5.7 0-10.3-3.4-11.8-8.5l-6.6 4.8C9.7 40.2 16.3 45 24 45z"/>
                  <path fill="#EA4335" d="M44.5 20H24v8.5h11.8c-.8 2.3-2.3 4.2-4.2 5.6l6.6 5.4C42.1 36.1 44.5 30.7 44.5 24c0-1.3-.1-2.7-.4-4z"/>
                </svg>
                Continuer avec Google
              </>
            )}
          </button>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          ERPro DZ © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  )
}
