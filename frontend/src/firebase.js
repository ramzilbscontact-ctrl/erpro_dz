import { initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

const firebaseConfig = {
  apiKey: 'AIzaSyBIsAxTH38eTU5K3YXRpYteynVTSd4yuuU',
  authDomain: 'blog-agenzia.firebaseapp.com',
  projectId: 'blog-agenzia',
  storageBucket: 'blog-agenzia.firebasestorage.app',
  messagingSenderId: '803790168050',
  appId: '1:803790168050:web:cf39a07cac75ddd463156b',
  measurementId: 'G-S21Y4C8PNK',
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const googleProvider = new GoogleAuthProvider()
