import http from './http'

export const login = (data) => http.post('/auth/login', data)
export const register = (data) => http.post('/auth/register', data)
export const me = () => http.get('/auth/me')
