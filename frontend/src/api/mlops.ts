import { http } from '../lib/http'

export interface ModelInfo {
  id: string
  name: string
  model_type: string
  version: string
  status: string
  model_path: string
  report_path?: string | null
  dataset_id?: string | null
  dataset_path?: string | null
  metrics?: Record<string, any> | null
  artifacts?: Record<string, any> | null
  training_params?: Record<string, any> | null
  description?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ListModelsParams {
  model_type?: string
  status?: string
  limit?: number
  offset?: number
}

export interface ModelRegisterPayload {
  name: string
  model_type: string
  model_path: string
  version?: string
  report_path?: string
  dataset_id?: string
  dataset_path?: string
  metrics?: Record<string, any>
  artifacts?: Record<string, any>
  training_params?: Record<string, any>
  description?: string
  status?: string
}

export async function listModels(params?: ListModelsParams): Promise<ModelInfo[]> {
  const { data } = await http.get('/mlops/models', { params })
  return data
}

export async function getModel(modelId: string): Promise<ModelInfo> {
  const { data } = await http.get(`/mlops/models/${modelId}`)
  return data
}

export async function registerModel(payload: ModelRegisterPayload): Promise<ModelInfo> {
  const { data } = await http.post('/mlops/models/register', payload)
  return data
}

export async function updateModelStatus(modelId: string, status: string): Promise<ModelInfo> {
  const { data } = await http.post(`/mlops/models/${modelId}/status`, { status })
  return data
}

export async function deleteModel(modelId: string): Promise<void> {
  await http.delete(`/mlops/models/${modelId}`)
}
