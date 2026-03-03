import api from './axios'

export const authAPI = {
  login:       (data)       => api.post('/api/auth/login/',   data),
  googleLogin: (credential) => api.post('/api/auth/google/',  { credential }),
  refresh:     (data)       => api.post('/api/auth/refresh/', data),
  me:          ()           => api.get('/api/auth/me/'),
}
