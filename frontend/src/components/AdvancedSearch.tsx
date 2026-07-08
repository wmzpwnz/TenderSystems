import { useState, useEffect, useRef } from 'react'
import { Search, SlidersHorizontal, X, ChevronDown, Calendar, DollarSign, MapPin, Building2, FileText, Bell, Check } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import RegionModal from './RegionModal'
import ProcedureModal from './ProcedureModal'
import { tendersApi, subscriptionsApi } from '../api/client'
import clsx from 'clsx'

interface SearchFilters {
  query?: string
  exclude_keywords?: string
  regions?: string[]
  okpd2_codes?: string[]
  price_from?: number
  price_to?: number
  published_from?: string
  published_to?: string
  deadline_less_than_days?: number
  statuses?: string[]
  customer_name?: string
  platform?: string  // Площадка
  guarantee_from?: number  // Обеспечение заявки от
  guarantee_to?: number    // Обеспечение заявки до
  contract_guarantee_from?: number  // Обеспечение контракта от
  contract_guarantee_to?: number    // Обеспечение контракта до
  prepayment_type?: string  // С авансом по 44-ФЗ, С авансом по 223-ФЗ, Без аванса
  preferences?: string[]  // Преимущества и ограничения
  sort_by?: string
  sort_order?: string
  procurement_types?: string[]  // 44-ФЗ, 223-ФЗ, 615 ПП РФ, Коммерческие, Закупки СНГ, Малые закупки
  procedure_types?: string[]     // Аукцион, Конкурс, Запрос котировок и др.
}

interface AdvancedSearchProps {
  onSearch: (filters: SearchFilters) => void
  initialFilters?: SearchFilters
  onForceSearch?: () => void // Опциональный callback для принудительного поиска
}

export default function AdvancedSearch({ onSearch, initialFilters = {}, onForceSearch }: AdvancedSearchProps) {
  // Преобразуем exclude_keywords из массива в строку, если необходимо
  const excludeKeywordsInitial = initialFilters.exclude_keywords
    ? Array.isArray(initialFilters.exclude_keywords)
      ? initialFilters.exclude_keywords.join(', ')
      : initialFilters.exclude_keywords
    : ''
  
  const [query, setQuery] = useState(initialFilters.query || '')
  const [excludeKeywords, setExcludeKeywords] = useState(excludeKeywordsInitial)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<SearchFilters>(initialFilters)
  const [activeFiltersCount, setActiveFiltersCount] = useState(0)

  // Группы раскрытия детальных фильтров
  const [expandedGroups, setExpandedGroups] = useState({
    typeAndProcedure: false,
    customerAndConditions: false,
    fineTuning: false
  })

  // Модальные окна
  const [regionModalOpen, setRegionModalOpen] = useState(false)
  const [procedureModalOpen, setProcedureModalOpen] = useState(false)

  // Подписки
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [subName, setSubName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Статусы
  const statusOptions = [
    { value: 'active', label: 'Подача заявок', color: 'bg-[rgba(199,211,234,0.06)] text-[var(--color-cipher-mint)]' },
    { value: 'evaluation', label: 'Работа комиссии', color: 'bg-[rgba(199,211,234,0.06)] text-[var(--color-electric-iris)]' },
    { value: 'completed', label: 'Завершены', color: 'bg-[rgba(199,211,234,0.06)] text-[var(--color-fog)]' },
    { value: 'cancelled', label: 'Отменены', color: 'bg-[rgba(199,211,234,0.06)] text-[var(--color-ember-bright-soft)]' }
  ]

  // Флаг для предотвращения циклов обновлений
  const isUpdatingFromParentRef = useRef(false)
  const lastSearchParamsRef = useRef<string>('')
  const prevInitialFiltersRef = useRef<string>('')

  // Синхронизация с initialFilters из родителя (только при реальных изменениях)
  useEffect(() => {
    const currentInitialFiltersStr = JSON.stringify(initialFilters)
    
    // Пропускаем, если это не реальное изменение
    if (prevInitialFiltersRef.current === currentInitialFiltersStr) {
      return
    }
    
    // Обновляем только если initialFilters действительно изменились извне
    // И это не первая инициализация (prevInitialFiltersRef.current пуст при первом рендере)
    if (prevInitialFiltersRef.current && prevInitialFiltersRef.current !== currentInitialFiltersStr) {
      // Обновляем локальное состояние
      setFilters(initialFilters)
      setQuery(initialFilters.query || '')
      const excludeKeywordsInitial = initialFilters.exclude_keywords
        ? Array.isArray(initialFilters.exclude_keywords)
          ? initialFilters.exclude_keywords.join(', ')
          : initialFilters.exclude_keywords
        : ''
      setExcludeKeywords(excludeKeywordsInitial)
      
      // Обновляем lastSearchParamsRef для предотвращения дублирования запросов
      const searchParams = {
        ...initialFilters,
        query: initialFilters.query || '',
        exclude_keywords: excludeKeywordsInitial || undefined
      }
      lastSearchParamsRef.current = JSON.stringify(searchParams)
    }
    
    // Обновляем ref для следующей проверки
    prevInitialFiltersRef.current = currentInitialFiltersStr
  }, [initialFilters])

  // Подсчёт активных фильтров
  useEffect(() => {
    let count = 0
    if (filters.regions && filters.regions.length > 0) count++
    if (filters.okpd2_codes && filters.okpd2_codes.length > 0) count++
    if (filters.price_from || filters.price_to) count++
    if (filters.deadline_less_than_days) count++
    if (filters.statuses && filters.statuses.length > 0) count++
    if (filters.customer_name) count++
    if (filters.procurement_types && filters.procurement_types.length > 0) count++
    if (filters.procedure_types && filters.procedure_types.length > 0) count++
    if (filters.platform) count++
    if (filters.guarantee_from || filters.guarantee_to) count++
    if (filters.contract_guarantee_from || filters.contract_guarantee_to) count++
    if (filters.prepayment_type) count++
    if (filters.preferences && filters.preferences.length > 0) count++
    if (filters.published_from || filters.published_to) count++
    setActiveFiltersCount(count)
  }, [filters])

  // Инициализация: устанавливаем начальное значение lastSearchParamsRef
  useEffect(() => {
    const initialParams = {
      ...initialFilters,
      query: initialFilters.query || '',
      exclude_keywords: excludeKeywordsInitial || undefined
    }
    lastSearchParamsRef.current = JSON.stringify(initialParams)
  }, []) // Только при монтировании

  // УБРАН автоматический поиск при изменении фильтров
  // Поиск выполняется ТОЛЬКО при нажатии кнопки "Применить" (handleSearch)
  // Обновляем только lastSearchParamsRef для отслеживания изменений
  useEffect(() => {
    const normalizeForComparison = (params: any) => {
      return {
        regions: params.regions && params.regions.length > 0 ? [...params.regions].sort() : null,
        statuses: params.statuses && params.statuses.length > 0 ? [...params.statuses].sort() : null,
        procurement_types: params.procurement_types && params.procurement_types.length > 0 ? [...params.procurement_types].sort() : null,
        okpd2_codes: params.okpd2_codes && params.okpd2_codes.length > 0 ? [...params.okpd2_codes].sort() : null,
        preferences: params.preferences && params.preferences.length > 0 ? [...params.preferences].sort() : null,
        procedure_types: params.procedure_types && params.procedure_types.length > 0 ? [...params.procedure_types].sort() : null,
        query: params.query || null,
        exclude_keywords: params.exclude_keywords || null,
        price_from: params.price_from ?? null,
        price_to: params.price_to ?? null,
        published_from: params.published_from || null,
        published_to: params.published_to || null,
        deadline_less_than_days: params.deadline_less_than_days ?? null,
        customer_name: params.customer_name || null,
        platform: params.platform || null,
        guarantee_from: params.guarantee_from ?? null,
        guarantee_to: params.guarantee_to ?? null,
        contract_guarantee_from: params.contract_guarantee_from ?? null,
        contract_guarantee_to: params.contract_guarantee_to ?? null,
        prepayment_type: params.prepayment_type || null
      }
    }
    
    const baseParams = {
      ...filters,
      query,
      exclude_keywords: excludeKeywords || undefined
    }
    
    const comparisonParams = normalizeForComparison(baseParams)
    const searchParamsStr = JSON.stringify(comparisonParams)
    
    // ТОЛЬКО обновляем ref для отслеживания изменений
    // НЕ вызываем onSearch автоматически - это делается только при нажатии "Применить"
    lastSearchParamsRef.current = searchParamsStr
  }, [filters, query, excludeKeywords])

  const handleSearch = () => {
    // Принудительный поиск при нажатии "Применить"
    // Убираем debounce для немедленного выполнения
    
    // Нормализуем exclude_keywords: если это строка, преобразуем в массив для единообразия
    let normalizedExcludeKeywords: string | string[] | undefined = undefined
    if (excludeKeywords && excludeKeywords.trim()) {
      // Если это строка с запятыми, разбиваем на массив
      const keywordsArray = excludeKeywords.split(',').map(k => k.trim()).filter(k => k)
      if (keywordsArray.length > 0) {
        // Сохраняем как строку для совместимости с API клиентом
        normalizedExcludeKeywords = keywordsArray.length === 1 ? keywordsArray[0] : keywordsArray.join(', ')
      }
    }
    
    const baseParams = {
      ...filters,
      query,
      exclude_keywords: normalizedExcludeKeywords
    }
    
    // Нормализуем для сравнения (используем null для JSON)
    const normalizeForComparison = (params: any) => {
      // Нормализуем exclude_keywords для сравнения
      let excludeKeywordsForComparison: string | null = null
      if (params.exclude_keywords) {
        if (Array.isArray(params.exclude_keywords)) {
          excludeKeywordsForComparison = params.exclude_keywords.join(', ')
        } else {
          excludeKeywordsForComparison = params.exclude_keywords
        }
      }
      
      return {
        regions: params.regions && params.regions.length > 0 ? [...params.regions].sort() : null,
        statuses: params.statuses && params.statuses.length > 0 ? [...params.statuses].sort() : null,
        procurement_types: params.procurement_types && params.procurement_types.length > 0 ? [...params.procurement_types].sort() : null,
        okpd2_codes: params.okpd2_codes && params.okpd2_codes.length > 0 ? [...params.okpd2_codes].sort() : null,
        preferences: params.preferences && params.preferences.length > 0 ? [...params.preferences].sort() : null,
        procedure_types: params.procedure_types && params.procedure_types.length > 0 ? [...params.procedure_types].sort() : null,
        query: params.query || null,
        exclude_keywords: excludeKeywordsForComparison,
        price_from: params.price_from ?? null,
        price_to: params.price_to ?? null,
        published_from: params.published_from || null,
        published_to: params.published_to || null,
        deadline_less_than_days: params.deadline_less_than_days ?? null,
        customer_name: params.customer_name || null,
        platform: params.platform || null,
        guarantee_from: params.guarantee_from ?? null,
        guarantee_to: params.guarantee_to ?? null,
        contract_guarantee_from: params.contract_guarantee_from ?? null,
        contract_guarantee_to: params.contract_guarantee_to ?? null,
        prepayment_type: params.prepayment_type || null
      }
    }
    
    // Преобразуем для передачи в onSearch (undefined для типов)
    const normalizeForSearch = (params: any): SearchFilters => {
      return {
        regions: params.regions && params.regions.length > 0 ? [...params.regions].sort() : undefined,
        statuses: params.statuses && params.statuses.length > 0 ? [...params.statuses].sort() : undefined,
        procurement_types: params.procurement_types && params.procurement_types.length > 0 ? [...params.procurement_types].sort() : undefined,
        okpd2_codes: params.okpd2_codes && params.okpd2_codes.length > 0 ? [...params.okpd2_codes].sort() : undefined,
        preferences: params.preferences && params.preferences.length > 0 ? [...params.preferences].sort() : undefined,
        procedure_types: params.procedure_types && params.procedure_types.length > 0 ? [...params.procedure_types].sort() : undefined,
        query: params.query || undefined,
        exclude_keywords: params.exclude_keywords || undefined,
        price_from: params.price_from ?? undefined,
        price_to: params.price_to ?? undefined,
        published_from: params.published_from || undefined,
        published_to: params.published_to || undefined,
        deadline_less_than_days: params.deadline_less_than_days ?? undefined,
        customer_name: params.customer_name || undefined,
        platform: params.platform || undefined,
        guarantee_from: params.guarantee_from ?? undefined,
        guarantee_to: params.guarantee_to ?? undefined,
        contract_guarantee_from: params.contract_guarantee_from ?? undefined,
        contract_guarantee_to: params.contract_guarantee_to ?? undefined,
        prepayment_type: params.prepayment_type || undefined
      }
    }
    
    const comparisonParams = normalizeForComparison(baseParams)
    const searchParamsStr = JSON.stringify(comparisonParams)
    lastSearchParamsRef.current = searchParamsStr
    
    const searchParams = normalizeForSearch(baseParams)
    
    onSearch(searchParams)
    // Если есть callback для принудительного поиска, вызываем его
    if (onForceSearch) {
      onForceSearch()
    }
    setShowFilters(false)
  }

  const handleRegionsSave = (regions: string[]) => {
    const newFilters = { ...filters, regions: regions.length > 0 ? regions : undefined }
    // Помечаем, что это изменение пользователя, не извне
    isUpdatingFromParentRef.current = false
    setFilters(newFilters)
  }

  const handleProceduresSave = (procedures: string[]) => {
    const newFilters = { ...filters, procedure_types: procedures.length > 0 ? procedures : undefined }
    // Помечаем, что это изменение пользователя, не извне
    isUpdatingFromParentRef.current = false
    setFilters(newFilters)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleClearFilters = () => {
    const defaultFilters: SearchFilters = {
      procurement_types: ['44-ФЗ', '223-ФЗ']
    }
    setFilters(defaultFilters)
    setQuery('')
    setExcludeKeywords('')
    onSearch(defaultFilters)
  }

  const toggleStatus = (status: string) => {
    const current = filters.statuses || []
    let next: string[]
    if (current.includes(status)) {
      next = current.filter(s => s !== status)
    } else {
      next = [...current, status]
    }
    setFilters({ ...filters, statuses: next.length > 0 ? next : undefined })
  }

  const toggleProcurementType = (type: string) => {
    const current = filters.procurement_types || []
    if (current.includes(type)) {
      setFilters({ ...filters, procurement_types: current.filter(t => t !== type) })
    } else {
      setFilters({ ...filters, procurement_types: [...current, type] })
    }
  }

  return (
    <div className="w-full">
      <div className="relative">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[var(--color-fog)]" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Поиск..."
              className="blueprint-input pl-12 pr-4 py-3 md:py-4 text-base md:text-lg"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`relative flex-1 md:flex-none px-4 md:px-6 py-3 md:py-4 font-medium transition-all flex items-center justify-center gap-2 ${showFilters
                ? 'blueprint-button-primary'
                : 'blueprint-button-ghost'
                }`}
            >
              <SlidersHorizontal className="h-5 w-5" />
              <span className="text-sm md:text-base">Фильтры</span>
              {activeFiltersCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-[rgba(228,109,76,0.22)] text-[var(--color-ember-bright-soft)] text-xs font-bold rounded-full h-5 w-5 md:h-6 md:w-6 flex items-center justify-center">
                  {activeFiltersCount}
                </span>
              )}
            </button>

            <button
              onClick={() => setShowSaveModal(true)}
              className="px-4 py-3 md:py-4 blueprint-button-ghost font-semibold flex items-center justify-center gap-2 group"
              title="Получать уведомления о новых тендерах"
            >
              <Bell className="h-5 w-5 group-hover:rotate-12 transition-transform" />
              <span className="hidden lg:inline text-sm md:text-base">Следить</span>
            </button>

            <button
              onClick={handleSearch}
              className="px-6 md:px-8 py-3 md:py-4 blueprint-button-primary flex items-center justify-center"
            >
              <span className="md:hidden"><Search className="h-5 w-5" /></span>
              <span className="hidden md:inline">Найти</span>
            </button>
          </div>
        </div>

        {query.length >= 2 && <AutocompleteSuggestions query={query} onSelect={setQuery} />}

      </div>

      {/* Всегда видимые фильтры */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3 p-4 bg-[rgba(199,211,234,0.02)] border border-[rgba(186,215,247,0.06)] rounded-lg">
        {/* 1. Регион */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)]">
            <MapPin className="h-3.5 w-3.5 text-[var(--color-frost-link)]" />
            Регион поставки
          </label>
          <button
            type="button"
            onClick={() => setRegionModalOpen(true)}
            className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-left hover:border-blue-500 transition-colors flex items-center justify-between text-sm"
          >
            <span className={filters.regions && filters.regions.length > 0 ? 'text-[var(--color-glacier)] font-medium' : 'text-[var(--color-fog)]'}>
              {filters.regions && filters.regions.length > 0
                ? `Выбрано регионов: ${filters.regions.length}`
                : 'Все регионы'}
            </span>
            <ChevronDown className="h-4 w-4 text-[var(--color-fog)]" />
          </button>
        </div>

        {/* 2. Цена */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)]">
            <DollarSign className="h-3.5 w-3.5 text-[var(--color-frost-link)]" />
            Цена контракта (₽)
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder="От"
              value={filters.price_from || ''}
              onChange={(e) =>
                setFilters({ ...filters, price_from: e.target.value ? Number(e.target.value) : undefined })
              }
              className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-sm text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
            />
            <span className="text-[var(--color-fog)] text-xs">—</span>
            <input
              type="number"
              placeholder="До"
              value={filters.price_to || ''}
              onChange={(e) =>
                setFilters({ ...filters, price_to: e.target.value ? Number(e.target.value) : undefined })
              }
              className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-sm text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
            />
          </div>
        </div>

        {/* 3. Дедлайн */}
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)]">
            <Calendar className="h-3.5 w-3.5 text-[var(--color-frost-link)]" />
            Срок подачи заявок
          </label>
          <div className="flex gap-1.5 flex-wrap">
            {[3, 7, 14, 30].map((days) => (
              <button
                key={days}
                type="button"
                onClick={() =>
                  setFilters({
                    ...filters,
                    deadline_less_than_days: filters.deadline_less_than_days === days ? undefined : days
                  })
                }
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${filters.deadline_less_than_days === days
                  ? 'bg-[var(--color-ember)] text-white shadow-sm'
                  : 'bg-[rgba(199,211,234,0.06)] text-[var(--color-moonlight)] hover:bg-[rgba(199,211,234,0.12)]'
                  }`}
              >
                &lt; {days} дн
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Активные фильтры (Чипы) */}
      {activeFiltersCount > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 px-2">
          {filters.regions?.map(region => (
            <span key={region} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              <MapPin className="h-3 w-3 text-[var(--color-fog)]" />
              {region}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, regions: f.regions?.filter(r => r !== region) }))}
              />
            </span>
          ))}

          {filters.statuses?.map(status => (
            <span key={status} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              {statusOptions.find(o => o.value === status)?.label || status}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => toggleStatus(status)}
              />
            </span>
          ))}

          {(filters.price_from || filters.price_to) && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              <DollarSign className="h-3 w-3 text-[var(--color-fog)]" />
              Цена: {filters.price_from ? `от ${filters.price_from.toLocaleString()} ₽` : ''} {filters.price_to ? `до ${filters.price_to.toLocaleString()} ₽` : ''}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, price_from: undefined, price_to: undefined }))}
              />
            </span>
          )}

          {filters.deadline_less_than_days && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              <Calendar className="h-3 w-3 text-[var(--color-fog)]" />
              Подача &lt; {filters.deadline_less_than_days} дн
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, deadline_less_than_days: undefined }))}
              />
            </span>
          )}

          {filters.procurement_types?.map(type => (
            <span key={type} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              {type}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, procurement_types: f.procurement_types?.filter(t => t !== type) }))}
              />
            </span>
          ))}

          {filters.procedure_types?.map(type => (
            <span key={type} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              {type}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, procedure_types: f.procedure_types?.filter(t => t !== type) }))}
              />
            </span>
          ))}

          {filters.platform && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              Площадка: {filters.platform}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, platform: undefined }))}
              />
            </span>
          )}

          {filters.customer_name && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              Заказчик: {filters.customer_name}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, customer_name: undefined }))}
              />
            </span>
          )}

          {filters.prepayment_type && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              {filters.prepayment_type === 'prepayment_44fz' ? 'С авансом 44-ФЗ' : filters.prepayment_type === 'prepayment_223fz' ? 'С авансом 223-ФЗ' : 'Без аванса'}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, prepayment_type: undefined }))}
              />
            </span>
          )}

          {filters.preferences?.map(pref => (
            <span key={pref} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              {pref}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, preferences: f.preferences?.filter(p => p !== pref) }))}
              />
            </span>
          ))}

          {filters.okpd2_codes?.map(code => (
            <span key={code} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              ОКПД2: {code}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, okpd2_codes: f.okpd2_codes?.filter(c => c !== code) }))}
              />
            </span>
          ))}

          {excludeKeywords && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              Исключить: {excludeKeywords}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => {
                  setExcludeKeywords('');
                  setFilters(f => ({ ...f, exclude_keywords: undefined }));
                }}
              />
            </span>
          )}

          {(filters.published_from || filters.published_to) && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[rgba(199,211,234,0.06)] text-xs font-semibold rounded-[var(--radius-badges)] text-[var(--color-glacier)] border border-[rgba(186,215,247,0.08)]">
              Опубликовано: {filters.published_from || ''} — {filters.published_to || ''}
              <X
                className="h-3 w-3 cursor-pointer hover:text-[var(--color-ember-bright)]"
                onClick={() => setFilters(f => ({ ...f, published_from: undefined, published_to: undefined }))}
              />
            </span>
          )}
        </div>
      )}

      <AnimatePresence>
        {showSaveModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowSaveModal(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="blueprint-frame relative w-full max-w-md p-8"
            >
              <h3 className="blueprint-heading text-2xl mb-2">Создать уведомление</h3>
              <p className="text-[var(--color-fog)] mb-6 text-sm">
                Мы будем проверять ЕИС каждые 60 минут и пришлем вам уведомление, как только появится новый тендер по этим фильтрам.
              </p>

              <div className="space-y-4">
                <div>
                  <label className="blueprint-eyebrow text-[10px] mb-2 block">
                    Название фильтра
                  </label>
                  <input
                    type="text"
                    autoFocus
                    placeholder="Например: Стройка Москва 30% аванс"
                    value={subName}
                    onChange={(e) => setSubName(e.target.value)}
                    className="blueprint-input px-4 py-3 font-bold"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    onClick={() => setShowSaveModal(false)}
                    className="blueprint-button-ghost flex-1 py-3 font-bold"
                  >
                    Отмена
                  </button>
                  <button
                    disabled={!subName || isSaving}
                    onClick={async () => {
                      setIsSaving(true)
                      try {
                        // Преобразуем exclude_keywords в массив для подписки
                        const excludeKeywordsArray = excludeKeywords 
                          ? excludeKeywords.split(',').map(k => k.trim()).filter(k => k)
                          : undefined
                        const payload = {
                          name: subName,
                          filters: {
                            ...filters,
                            query,
                            exclude_keywords: excludeKeywordsArray
                          }
                        }
                        await subscriptionsApi.create(payload)
                        setSaveSuccess(true)
                        setTimeout(() => {
                          setSaveSuccess(false)
                          setShowSaveModal(false)
                          setSubName('')
                        }, 2000)
                      } catch (err) {
                        console.error('Save sub error:', err)
                      } finally {
                        setIsSaving(false)
                      }
                    }}
                    className={clsx(
                      "flex-[2] py-3 font-bold flex items-center justify-center gap-2 transition-all",
                      saveSuccess
                        ? "bg-[var(--color-cipher-mint)] text-white"
                        : "blueprint-button-primary disabled:opacity-50"
                    )}
                  >
                    {saveSuccess ? (
                      <>
                        <Check className="h-5 w-5" />
                        Готово!
                      </>
                    ) : (
                      <>
                        <Bell className="h-5 w-5" />
                        {isSaving ? 'Сохранение...' : 'Подписаться'}
                      </>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Расширенные фильтры - РАСКРЫВАЮТСЯ */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="blueprint-section mt-4 p-6 space-y-6">
              {/* Заголовок */}
              <div className="flex items-center justify-between">
                <h3 className="blueprint-heading text-lg">Детальные фильтры</h3>
                {activeFiltersCount > 0 && (
                  <button
                    onClick={handleClearFilters}
                    className="text-sm text-[var(--color-ember-bright)] hover:text-[var(--color-ember)] font-medium flex items-center gap-1"
                  >
                    <X className="h-4 w-4" />
                    Сбросить все
                  </button>
                )}
              </div>

              <div className="space-y-4">
                {/* Группа 1: Тип и процедура */}
                <div className="border border-[rgba(186,215,247,0.08)] bg-[rgba(5,6,15,0.2)] rounded-xl overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setExpandedGroups(prev => ({ ...prev, typeAndProcedure: !prev.typeAndProcedure }))}
                    className="w-full flex items-center justify-between p-4 font-bold text-sm text-[var(--color-glacier)] hover:bg-[rgba(199,211,234,0.04)] transition-all"
                  >
                    <span className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-[var(--color-electric-iris)]" />
                      Тип и процедура
                    </span>
                    <ChevronDown className={clsx("h-4 w-4 transition-transform text-[var(--color-fog)]", expandedGroups.typeAndProcedure && "rotate-180")} />
                  </button>
                  {expandedGroups.typeAndProcedure && (
                    <div className="p-4 border-t border-[rgba(186,215,247,0.08)] grid grid-cols-1 md:grid-cols-2 gap-6 bg-[rgba(5,6,15,0.1)]">
                      {/* Этап */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Этап закупки
                        </label>
                        <div className="space-y-2.5">
                          {statusOptions.map((status) => (
                            <label key={status.value} className="flex items-center gap-2 cursor-pointer group text-xs text-[var(--color-moonlight)]">
                              <input
                                type="checkbox"
                                checked={filters.statuses?.includes(status.value) || false}
                                onChange={() => toggleStatus(status.value)}
                                className="h-4 w-4 text-[var(--color-frost-link)] rounded border-[var(--color-steel-border)] bg-[rgba(5,6,15,0.3)] focus:ring-2 focus:ring-[var(--color-electric-iris)]"
                              />
                              <span className="group-hover:text-[var(--color-glacier)] transition-colors">{status.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Тип торгов */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Тип торгов
                        </label>
                        <div className="space-y-2.5">
                          {['44-ФЗ', '223-ФЗ', '615 ПП РФ', 'Коммерческие', 'Малые закупки'].map((type) => (
                            <label key={type} className="flex items-center gap-2 cursor-pointer group text-xs text-[var(--color-moonlight)]">
                              <input
                                type="checkbox"
                                checked={filters.procurement_types?.includes(type) || false}
                                onChange={() => toggleProcurementType(type)}
                                className="h-4 w-4 text-[var(--color-frost-link)] rounded border-[var(--color-steel-border)] bg-[rgba(5,6,15,0.3)] focus:ring-2 focus:ring-[var(--color-electric-iris)]"
                              />
                              <span className="group-hover:text-[var(--color-glacier)] transition-colors">{type}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Способ отбора */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Способ отбора поставщика
                        </label>
                        <button
                          type="button"
                          onClick={() => setProcedureModalOpen(true)}
                          className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-left hover:border-blue-500 transition-colors flex items-center justify-between text-xs text-[var(--color-glacier)]"
                        >
                          <span>
                            {filters.procedure_types && filters.procedure_types.length > 0
                              ? `Выбрано способов: ${filters.procedure_types.length}`
                              : 'Все способы'}
                          </span>
                          <ChevronDown className="h-4 w-4 text-[var(--color-fog)]" />
                        </button>
                      </div>

                      {/* Площадка */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Электронная площадка
                        </label>
                        <select
                          value={filters.platform || ''}
                          onChange={(e) => setFilters({ ...filters, platform: e.target.value || undefined })}
                          className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                        >
                          <option value="">Все площадки</option>
                          <option value="roseltorg">РТС-тендер (Росэлторг)</option>
                          <option value="sberbank-ast">Сбербанк-АСТ</option>
                          <option value="etp-gpb">ЭТП ГПБ</option>
                          <option value="zakazrf">Заказ.РФ</option>
                          <option value="etp-fabrikant">ЭТП Фабрикант</option>
                          <option value="b2b-center">B2B-Center</option>
                          <option value="rts-tender">РТС-тендер</option>
                          <option value="otc-tender">ОТС.тендер</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>

                {/* Группа 2: Заказчик и условия */}
                <div className="border border-[rgba(186,215,247,0.08)] bg-[rgba(5,6,15,0.2)] rounded-xl overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setExpandedGroups(prev => ({ ...prev, customerAndConditions: !prev.customerAndConditions }))}
                    className="w-full flex items-center justify-between p-4 font-bold text-sm text-[var(--color-glacier)] hover:bg-[rgba(199,211,234,0.04)] transition-all"
                  >
                    <span className="flex items-center gap-2">
                      <Building2 className="h-4 w-4 text-[var(--color-electric-iris)]" />
                      Заказчик и условия контракта
                    </span>
                    <ChevronDown className={clsx("h-4 w-4 transition-transform text-[var(--color-fog)]", expandedGroups.customerAndConditions && "rotate-180")} />
                  </button>
                  {expandedGroups.customerAndConditions && (
                    <div className="p-4 border-t border-[rgba(186,215,247,0.08)] grid grid-cols-1 md:grid-cols-2 gap-6 bg-[rgba(5,6,15,0.1)]">
                      {/* Заказчик */}
                      <div className="md:col-span-2">
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Наименование заказчика или ИНН
                        </label>
                        <input
                          type="text"
                          placeholder="Например: ГКУ УКС или ИНН..."
                          value={filters.customer_name || ''}
                          onChange={(e) => setFilters({ ...filters, customer_name: e.target.value || undefined })}
                          className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                        />
                      </div>

                      {/* Авансирование */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Аванс
                        </label>
                        <div className="space-y-2 text-xs text-[var(--color-moonlight)]">
                          {[
                            { value: 'prepayment_44fz', label: 'С авансом по 44-ФЗ' },
                            { value: 'prepayment_223fz', label: 'С авансом по 223-ФЗ' },
                            { value: 'no_prepayment', label: 'Без аванса' }
                          ].map((option) => (
                            <label key={option.value} className="flex items-center gap-2 cursor-pointer group">
                              <input
                                type="radio"
                                name="prepayment"
                                checked={filters.prepayment_type === option.value}
                                onChange={() => setFilters({ ...filters, prepayment_type: option.value })}
                                className="h-4 w-4 text-[var(--color-frost-link)] border-[var(--color-steel-border)] bg-[rgba(5,6,15,0.3)] focus:ring-2 focus:ring-[var(--color-electric-iris)]"
                              />
                              <span className="group-hover:text-[var(--color-glacier)] transition-colors">{option.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Преимущества и преференции */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Преимущества (СМП/СОНКО)
                        </label>
                        <div className="grid grid-cols-1 gap-2 text-xs text-[var(--color-moonlight)]">
                          {[
                            'СМП/СОНКО',
                            'Организации инвалидов',
                            'Импортозамещение'
                          ].map((pref) => (
                            <label key={pref} className="flex items-center gap-2 cursor-pointer group">
                              <input
                                type="checkbox"
                                checked={filters.preferences?.includes(pref) || false}
                                onChange={() => {
                                  const current = filters.preferences || []
                                  const updated = current.includes(pref)
                                    ? current.filter(p => p !== pref)
                                    : [...current, pref]
                                  setFilters({ ...filters, preferences: updated.length > 0 ? updated : undefined })
                                }}
                                className="h-4 w-4 text-[var(--color-frost-link)] rounded border-[var(--color-steel-border)] bg-[rgba(5,6,15,0.3)] focus:ring-2 focus:ring-[var(--color-electric-iris)]"
                              />
                              <span className="group-hover:text-[var(--color-glacier)] transition-colors">{pref}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Обеспечение заявки */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Обеспечение заявки (₽)
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            placeholder="От"
                            value={filters.guarantee_from || ''}
                            onChange={(e) => setFilters({ ...filters, guarantee_from: e.target.value ? Number(e.target.value) : undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                          <span className="text-[var(--color-fog)] text-xs">—</span>
                          <input
                            type="number"
                            placeholder="До"
                            value={filters.guarantee_to || ''}
                            onChange={(e) => setFilters({ ...filters, guarantee_to: e.target.value ? Number(e.target.value) : undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                        </div>
                      </div>

                      {/* Обеспечение контракта */}
                      <div>
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Обеспечение контракта (₽)
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            placeholder="От"
                            value={filters.contract_guarantee_from || ''}
                            onChange={(e) => setFilters({ ...filters, contract_guarantee_from: e.target.value ? Number(e.target.value) : undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                          <span className="text-[var(--color-fog)] text-xs">—</span>
                          <input
                            type="number"
                            placeholder="До"
                            value={filters.contract_guarantee_to || ''}
                            onChange={(e) => setFilters({ ...filters, contract_guarantee_to: e.target.value ? Number(e.target.value) : undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Группа 3: Точная настройка */}
                <div className="border border-[rgba(186,215,247,0.08)] bg-[rgba(5,6,15,0.2)] rounded-xl overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setExpandedGroups(prev => ({ ...prev, fineTuning: !prev.fineTuning }))}
                    className="w-full flex items-center justify-between p-4 font-bold text-sm text-[var(--color-glacier)] hover:bg-[rgba(199,211,234,0.04)] transition-all"
                  >
                    <span className="flex items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4 text-[var(--color-electric-iris)]" />
                      Точная настройка
                    </span>
                    <ChevronDown className={clsx("h-4 w-4 transition-transform text-[var(--color-fog)]", expandedGroups.fineTuning && "rotate-180")} />
                  </button>
                  {expandedGroups.fineTuning && (
                    <div className="p-4 border-t border-[rgba(186,215,247,0.08)] grid grid-cols-1 md:grid-cols-2 gap-6 bg-[rgba(5,6,15,0.1)]">
                      {/* Исключить слова */}
                      <div className="md:col-span-2">
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Исключить слова из поиска
                        </label>
                        <input
                          type="text"
                          placeholder="Слова через запятую, например: поставка, обслуживание"
                          value={excludeKeywords}
                          onChange={(e) => setExcludeKeywords(e.target.value)}
                          className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                        />
                      </div>

                      {/* ОКПД2 */}
                      <div className="md:col-span-2">
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Коды ОКПД2 (через запятую)
                        </label>
                        <input
                          type="text"
                          placeholder="Например: 41.2, 42.11, 43.2"
                          value={filters.okpd2_codes ? filters.okpd2_codes.join(', ') : ''}
                          onChange={(e) => {
                            const val = e.target.value
                            const codes = val ? val.split(',').map(c => c.trim()).filter(c => c) : undefined
                            setFilters({ ...filters, okpd2_codes: codes })
                          }}
                          className="w-full px-3 py-2 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                        />
                      </div>

                      {/* Дата публикации */}
                      <div className="md:col-span-2">
                        <label className="flex items-center gap-2 text-xs font-semibold text-[var(--color-moonlight)] mb-3">
                          Дата публикации закупки
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="date"
                            value={filters.published_from || ''}
                            onChange={(e) => setFilters({ ...filters, published_from: e.target.value || undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                          <span className="text-[var(--color-fog)] text-xs">—</span>
                          <input
                            type="date"
                            value={filters.published_to || ''}
                            onChange={(e) => setFilters({ ...filters, published_to: e.target.value || undefined })}
                            className="w-full px-3 py-1.5 bg-[rgba(5,6,15,0.2)] border border-[var(--color-steel-border)] rounded-lg text-xs text-[var(--color-glacier)] focus:ring-2 focus:ring-[var(--color-electric-iris)] focus:border-transparent"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Кнопки действий */}
              <div className="flex items-center justify-between pt-4 border-t border-[rgba(186,215,247,0.12)]">
                <div className="text-xs text-[var(--color-pebble)]">
                  {activeFiltersCount > 0 ? (
                    <span>
                      Активных фильтров: <strong>{activeFiltersCount}</strong>
                    </span>
                  ) : (
                    <span>Фильтры не применены</span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowFilters(false)}
                    className="px-4 py-2 text-xs text-[var(--color-moonlight)] hover:bg-[rgba(199,211,234,0.06)] rounded-lg transition-colors font-semibold"
                  >
                    Свернуть
                  </button>
                  <button
                    onClick={handleSearch}
                    className="blueprint-button-primary px-6 py-2 text-xs font-bold"
                  >
                    Применить {activeFiltersCount > 0 ? `· ${activeFiltersCount} активных` : ''}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Модальные окна */}
      <RegionModal
        isOpen={regionModalOpen}
        onClose={() => setRegionModalOpen(false)}
        selectedRegions={filters.regions || []}
        onSave={handleRegionsSave}
      />

      <ProcedureModal
        isOpen={procedureModalOpen}
        onClose={() => setProcedureModalOpen(false)}
        selectedProcedures={filters.procedure_types || []}
        onSave={handleProceduresSave}
      />
    </div>
  )
}

// Компонент автодополнения с реальным API
function AutocompleteSuggestions({ query, onSelect }: { query: string; onSelect: (value: string) => void }) {
  // Debounce для уменьшения количества запросов
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300) // 300ms debounce

    return () => clearTimeout(timer)
  }, [query])

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ['autocomplete', debouncedQuery],
    queryFn: async () => {
      // Подключаем наш apiClient вместо прямого fetch
      const { data } = await tendersApi.autocomplete(debouncedQuery)
      return data
    },
    enabled: debouncedQuery.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 минут
  })

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="blueprint-modal absolute z-10 w-full mt-2 overflow-hidden"
      >
        <div className="p-4 text-center text-[var(--color-fog)] text-sm">Загрузка...</div>
      </motion.div>
    )
  }

  if (!suggestions || suggestions.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="blueprint-modal absolute z-10 w-full mt-2 overflow-hidden"
    >
      <div className="p-2">
        <div className="text-xs text-[var(--color-fog)] px-3 py-2">Найдено {suggestions.length} подсказок</div>
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {suggestions.map((suggestion: any, idx: number) => (
            <div
              key={idx}
              className="px-3 py-2 hover:bg-[rgba(199,211,234,0.08)] rounded-md cursor-pointer transition-colors"
              onClick={() => onSelect(suggestion.title || suggestion.query || suggestion)}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Search className="h-4 w-4 text-[var(--color-fog)] flex-shrink-0" />
                  <span className="text-sm truncate">{suggestion.title || suggestion.query || suggestion}</span>
                </div>
                {suggestion.count && (
                  <span className="text-xs text-[var(--color-fog)]">{suggestion.count}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
