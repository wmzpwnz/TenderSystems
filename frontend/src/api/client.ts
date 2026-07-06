import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8003/api/v1'

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 секунд таймаут
})

// Interceptor для добавления токена авторизации
apiClient.interceptors.request.use(
  (config) => {
    // Получаем токен из localStorage
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    return Promise.reject(error)
  }
)

export const api = apiClient;

// Типы данных
export interface Tender {
  id: number
  eis_id: string
  number: string | null
  title: string
  description: string | null
  purchaseObjectInfo?: string | null  // Объект закупки (альтернативное поле)
  customer_name: string | null
  customer_inn: string | null
  customer_region: string | null
  initial_price: number | null
  currency: string
  guarantee_amount: number | null
  contract_guarantee: number | null
  publication_date: string | null
  application_deadline: string | null
  contract_deadline: string | null
  status: string
  procedure_type: string | null
  documents_url: string | null
  documents_data: any[] | null
  okpd2_codes: string[] | null
  requirements: any | null
  platform: string | null  // Площадка (Росэлторг, Сбербанк-АСТ и т.д.)
  prepayment_type: string | null  // Тип авансирования
  preferences: string[] | null  // Преимущества (СМП, СОНКО и т.д.)
  is_analyzed: boolean
  is_favorite?: boolean
  crm_status?: string
  created_at: string
  updated_at: string
  url?: string // URL для Live Search тендеров (внешняя ссылка на zakupki.gov.ru)
}

export interface Analysis {
  id: number
  tender_id: number
  summary: string | null
  critical_requirements: any | null
  deadlines: any | null
  financial_info: any | null
  evaluation_criteria: any | null
  risks: any | null
  margin_analysis: any | null
  win_probability: number | null
  risk_level: string | null
  raw_ai_response: any | null
  analysis_version: string
  analysis_type: string
  documents_analyzed: any[] | null
  cost_breakdown: any | null
  created_at: string
}

export type AnalysisType = 'quick' | 'deep'

export interface CompanyProfile {
  id: number
  name: string | null
  inn: string | null
  region: string | null
  licenses: string[] | null
  sro_certificates: string[] | null
  experience_contracts: number | null
  experience_sum: number | null
  okpd2_codes: string[] | null
  equipment: string[] | null
}

export interface TenderListResponse {
  items: Tender[]
  total: number
  page: number
  page_size: number
  pages: number
  search_time_ms?: number
}

// API методы
export const tendersApi = {
  search: async (params: {
    page?: number
    page_size?: number
    region?: string
    okpd2?: string
    price_from?: number
    price_to?: number
    status?: string
  }): Promise<TenderListResponse> => {
    const { data } = await apiClient.get('/tenders/', { params })
    return data
  },

  advancedSearch: async (params: {
    query?: string
    exclude_keywords?: string | string[]
    regions?: string[]
    okpd2_codes?: string[]
    price_from?: number
    price_to?: number
    published_from?: string
    published_to?: string
    deadline_less_than_days?: number
    statuses?: string[]
    customer_name?: string
    platform?: string
    guarantee_from?: number
    guarantee_to?: number
    contract_guarantee_from?: number
    contract_guarantee_to?: number
    prepayment_type?: string
    preferences?: string[]
    sort_by?: string
    sort_order?: string
    page?: number
    page_size?: number
    procurement_types?: string[]
    procedure_types?: string[]
  }): Promise<TenderListResponse & { search_time_ms: number; filters_applied: any }> => {
    // Преобразуем параметры для соответствия бэкенду
    const backendParams: any = {
      ...params,
      // Преобразуем exclude_keywords в массив, если это строка
      exclude_keywords: params.exclude_keywords 
        ? Array.isArray(params.exclude_keywords) 
          ? params.exclude_keywords 
          : params.exclude_keywords.split(',').map(k => k.trim()).filter(k => k)
        : undefined,
      // Преобразуем published_from/published_to в published_after/published_before
      published_after: params.published_from || undefined,
      published_before: params.published_to || undefined,
    }
    // Удаляем старые поля
    delete backendParams.published_from
    delete backendParams.published_to
    
    const { data } = await apiClient.post('/search/advanced', backendParams)
    return data
  },

  // Прямой поиск в ЕИС (минуя БД)
  liveSearch: async (params: {
    query?: string
    exclude_keywords?: string | string[]
    region?: string
    okpd2?: string
    price_from?: number
    price_to?: number
    published_from?: string
    published_to?: string
    fz44?: boolean
    fz223?: boolean
    status?: string
    page?: number
    page_size?: number
    customer_name?: string
    platform?: string
    deadline_less_than_days?: number
    guarantee_from?: number
    guarantee_to?: number
    contract_guarantee_from?: number
    contract_guarantee_to?: number
    prepayment_type?: string
    preferences?: string[]
    procedure_types?: string[]
  }): Promise<TenderListResponse> => {
    // Преобразуем exclude_keywords в массив для exclude_words
    let excludeWords: string[] | undefined = undefined
    if (params.exclude_keywords) {
      if (Array.isArray(params.exclude_keywords)) {
        excludeWords = params.exclude_keywords.filter(k => k && k.trim())
      } else if (typeof params.exclude_keywords === 'string' && params.exclude_keywords.trim()) {
        // Разделяем строку по запятым и очищаем от пробелов
        excludeWords = params.exclude_keywords.split(',').map(k => k.trim()).filter(k => k)
      }
    }
    
    // Преобразуем параметры в формат TenderFilter (убираем undefined значения)
    const filterData: any = {
      query: params.query || undefined,
      region: params.region || undefined,
      okpd2: params.okpd2 || undefined,
      price_from: params.price_from,
      price_to: params.price_to,
      date_from: params.published_from || undefined,
      date_to: params.published_to || undefined,
      fz44: params.fz44 ?? true,
      fz223: params.fz223 ?? true,
      status: params.status || undefined,
      page: params.page ?? 1,
      page_size: params.page_size ?? 10,
      customer_name: params.customer_name || undefined,
      platform: params.platform || undefined,
      deadline_less_than_days: params.deadline_less_than_days,
      guarantee_from: params.guarantee_from,
      guarantee_to: params.guarantee_to,
      contract_guarantee_from: params.contract_guarantee_from,
      contract_guarantee_to: params.contract_guarantee_to,
      prepayment_type: params.prepayment_type || undefined,
      preferences: params.preferences && params.preferences.length > 0 ? params.preferences : undefined,
      procedure_types: params.procedure_types && params.procedure_types.length > 0 ? params.procedure_types : undefined
    }
    
    // Добавляем exclude_words только если есть значения
    if (excludeWords && excludeWords.length > 0) {
      filterData.exclude_words = excludeWords
    }
    
    // Удаляем undefined значения
    Object.keys(filterData).forEach(key => {
      if (filterData[key] === undefined) {
        delete filterData[key]
      }
    })
    // Выполняем запрос к API (кеширование отключено через React Query)
    const { data } = await apiClient.post('/search/eis-live', filterData)
    return data
  },

  getById: async (id: number | string): Promise<Tender> => {
    const { data } = await apiClient.get(`/tenders/${id}`)
    return data
  },

  getCustomerIntelligence: async (inn: string): Promise<any> => {
    const { data } = await apiClient.get(`/tenders/customer/${inn}/intelligence`)
    return data
  },

  sync: async (params?: {
    page?: number
    page_size?: number
    filters?: any
  }): Promise<Tender[]> => {
    const { data } = await apiClient.post('/tenders/sync', null, { params })
    return data
  },

  refresh: async (limit?: number): Promise<{ message: string; updated: number; total: number }> => {
    const { data } = await apiClient.post('/tenders/refresh', null, {
      params: limit ? { limit } : {}
    })
    return data
  },

  deleteAll: async (): Promise<{ message: string; deleted: number }> => {
    const { data } = await apiClient.delete('/tenders/all')
    return data
  },

  getStats: async (): Promise<{
    regions: Array<{ name: string; count: number }>
    price: { min: number; max: number; avg: number }
    statuses: Array<{ status: string; count: number }>
    total_tenders: number
  }> => {
    const { data } = await apiClient.get('/search/filters/stats')
    return data
  },

  autocomplete: async (query: string): Promise<{ data: string[] }> => {
    const { data } = await apiClient.get(`/search/autocomplete?q=${query}`)
    return data
  },
  exportExcel: async (filters: any): Promise<Blob> => {
    const { data } = await apiClient.post('/analysis/export/excel', filters, {
      responseType: 'blob'
    })
    return data
  }
}

export const authApi = {
  login: async (formData: URLSearchParams): Promise<{ access_token: string; token_type: string }> => {
    // OAuth2PasswordRequestForm требует application/x-www-form-urlencoded
    const { data } = await apiClient.post('/auth/login/access-token', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return data
  },
  register: async (userData: any): Promise<any> => {
    const { data } = await apiClient.post('/auth/register', userData)
    return data
  },
  getMe: async (): Promise<any> => {
    const { data } = await apiClient.get('/auth/me')
    return data
  },
}

export const analysisApi = {
  get: async (tenderId: number | string): Promise<Analysis | null> => {
    try {
      const { data } = await apiClient.get(`/analysis/${tenderId}`)
      return data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  },

  analyze: async (tenderId: number | string, type: AnalysisType): Promise<Analysis> => {
    const { data } = await apiClient.post(`/analysis/${type}/${tenderId}`)
    return data
  },

  calculateProfitability: async (tenderId: number, proposedPrice: number, cost?: number): Promise<{
    initial_price: number
    proposed_price: number
    estimated_cost: number
    profit: number
    margin_percent: number
    margin_vs_initial: number
    guarantee_amount: number
    contract_guarantee: number
    total_guarantees: number
    net_profit_after_guarantees: number
    break_even_price: number
    recommendation: string
  }> => {
    const { data } = await apiClient.post(`/analysis/${tenderId}/calculate`, { proposedPrice, cost })
    return data
  },

  exportPdf: async (tenderId: number | string): Promise<Blob> => {
    const { data } = await apiClient.get(`/analysis/${tenderId}/export/pdf`, {
      responseType: 'blob'
    })
    return data
  },

  getByTenderId: async (tenderId: number): Promise<Analysis | null> => analysisApi.get(tenderId),

  quickAnalyze: async (tenderId: number): Promise<Analysis> => analysisApi.analyze(tenderId, 'quick'),

  deepAnalyze: async (tenderId: number): Promise<Analysis> => analysisApi.analyze(tenderId, 'deep'),
}

export const companyProfileApi = {
  get: async (): Promise<CompanyProfile> => {
    const { data } = await apiClient.get('/profile')
    return data
  },

  createOrUpdate: async (profile: Partial<CompanyProfile>): Promise<CompanyProfile> => {
    const { data } = await apiClient.post('/profile', profile)
    return data
  },

  delete: async (): Promise<void> => {
    await apiClient.delete('/profile')
  },
}

export const crmApi = {
  toggleFavorite: async (tenderId: string | number): Promise<{ status: string; is_favorite: boolean }> => {
    const { data } = await apiClient.post('/crm/favorites/toggle', { tender_id: String(tenderId) })
    return data
  },
  getFavorites: async (): Promise<any[]> => {
    const { data } = await apiClient.get('/crm/favorites')
    return data
  },
  updateStatus: async (tenderId: string | number, status: string, notes?: string): Promise<any> => {
    const { data } = await apiClient.patch(`/crm/favorites/${tenderId}`, { status, notes })
    return data
  }
}

export const subscriptionsApi = {
  create: async (payload: { name: string; filters: any; notify_email?: boolean; notify_telegram?: boolean }): Promise<any> => {
    const { data } = await apiClient.post('/subscriptions/', payload)
    return data
  },
  list: async (): Promise<any[]> => {
    const { data } = await apiClient.get('/subscriptions/')
    return data
  },
  update: async (id: number, payload: any): Promise<any> => {
    const { data } = await apiClient.patch(`/subscriptions/${id}`, payload)
    return data
  },
  delete: async (id: number): Promise<any> => {
    const { data } = await apiClient.delete(`/subscriptions/${id}`)
    return data
  }
}
