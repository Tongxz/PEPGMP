import { http } from '../lib/http'

export async function getHealth() {
  const { data } = await http.get('/system/health')
  return data
}

export async function getSystemInfo() {
  const { data } = await http.get('/system/info')
  return data
}

export async function getSystemConfig() {
  const { data } = await http.get('/system/config')
  return data
}
