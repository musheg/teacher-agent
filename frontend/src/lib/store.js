import { create } from 'zustand'
import { auth, authApi } from './api.js'

export const useAuthStore = create((set, get) => ({
  user: null,
  loading: true,
  async refresh() {
    if (!auth.getAccess()) {
      set({ user: null, loading: false })
      return
    }
    try {
      const me = await authApi.me()
      set({ user: me, loading: false })
    } catch {
      auth.clear()
      set({ user: null, loading: false })
    }
  },
  async login(email, password) {
    await authApi.login({ email, password })
    await get().refresh()
  },
  logout() {
    auth.clear()
    set({ user: null })
  },
}))
