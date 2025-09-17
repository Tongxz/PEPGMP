import { http } from '../lib/http'

export async function getHealth() {
  const { data } = await http.get('/health')
  return data
}

export async function getSystemInfo() {
  const { data } = await http.get('/system/info')
  return data
}
