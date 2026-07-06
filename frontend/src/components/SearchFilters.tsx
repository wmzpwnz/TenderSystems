import React, { useState } from 'react'
import { Search, X, ChevronDown, ChevronUp } from 'lucide-react'

interface Filters {
  query?: string
  region?: string
  okpd2?: string
  price_from?: number
  price_to?: number
  date_from?: string
  date_to?: string
  status?: string
  fz44?: boolean
  fz223?: boolean
}

interface SearchFiltersProps {
  filters: Filters
  onFiltersChange: (filters: Filters) => void
  loading?: boolean
}

export default function SearchFilters({
  filters,
  onFiltersChange,
  loading
}: SearchFiltersProps) {
  const [localFilters, setLocalFilters] = useState<Filters>({
    query: filters.query || '',
    region: filters.region || '',
    okpd2: filters.okpd2 || '',
    price_from: filters.price_from,
    price_to: filters.price_to,
    date_from: filters.date_from || '',
    date_to: filters.date_to || '',
    status: filters.status || '',
    fz44: filters.fz44 ?? true,
    fz223: filters.fz223 ?? true
  })

  const [showAdvanced, setShowAdvanced] = useState(false)

  const handleChange = (key: keyof Filters, value: any) => {
    setLocalFilters(prev => ({ ...prev, [key]: value }))
  }

  const handleApply = (e?: React.FormEvent) => {
    e?.preventDefault()
    onFiltersChange(localFilters)
  }

  const handleReset = () => {
    const defaultFilters = {
      query: '',
      region: '',
      okpd2: '',
      price_from: undefined,
      price_to: undefined,
      date_from: '',
      date_to: '',
      status: '',
      fz44: true,
      fz223: true
    }
    setLocalFilters(defaultFilters)
    onFiltersChange(defaultFilters)
  }

  return (
    <div className="blueprint-section p-5 mb-6">
      <form onSubmit={handleApply}>
        {/* Basic Search */}
        <div className="flex gap-3 mb-4">
          <div className="relative flex-grow">
            <input
              type="text"
              className="blueprint-input block w-full pl-4 pr-3 py-2.5"
              placeholder="Поиск по ключевым словам..."
              value={localFilters.query}
              onChange={(e) => handleChange('query', e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="blueprint-button-primary px-6 py-2 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <span className="animate-spin">⌛</span> : <Search className="h-4 w-4" />}
            Найти
          </button>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="blueprint-button-ghost px-4 py-2 flex items-center gap-2"
          >
            {showAdvanced ? 'Скрыть фильтры' : 'Фильтры'}
            {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>

        {/* Advanced Filters */}
        {showAdvanced && (
          <div className="blueprint-panel grid grid-cols-1 md:grid-cols-3 gap-4 p-4 animate-fadeIn">
            {/* Price */}
            <div>
              <label className="block text-sm font-medium text-[var(--color-moonlight)] mb-1">Сумма (руб)</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="От"
                  className="blueprint-input px-3 py-2"
                  value={localFilters.price_from || ''}
                  onChange={(e) => handleChange('price_from', e.target.value ? Number(e.target.value) : undefined)}
                />
                <input
                  type="number"
                  placeholder="До"
                  className="blueprint-input px-3 py-2"
                  value={localFilters.price_to || ''}
                  onChange={(e) => handleChange('price_to', e.target.value ? Number(e.target.value) : undefined)}
                />
              </div>
            </div>

            {/* Dates */}
            <div>
              <label className="block text-sm font-medium text-[var(--color-moonlight)] mb-1">Дата публикации</label>
              <div className="flex gap-2">
                <input
                  type="date"
                  className="blueprint-input px-3 py-2"
                  value={localFilters.date_from}
                  onChange={(e) => handleChange('date_from', e.target.value)}
                />
                <input
                  type="date"
                  className="blueprint-input px-3 py-2"
                  value={localFilters.date_to}
                  onChange={(e) => handleChange('date_to', e.target.value)}
                />
              </div>
            </div>

            {/* Region & OKPD2 */}
            <div>
              <label className="block text-sm font-medium text-[var(--color-moonlight)] mb-1">Регион (код)</label>
              <input
                type="text"
                placeholder="77"
                className="blueprint-input px-3 py-2 mb-2"
                value={localFilters.region}
                onChange={(e) => handleChange('region', e.target.value)}
              />
            </div>

            {/* Law Filters */}
            <div className="col-span-1 md:col-span-3 flex gap-4 mt-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={localFilters.fz44}
                  onChange={(e) => handleChange('fz44', e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span>44-ФЗ</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={localFilters.fz223}
                  onChange={(e) => handleChange('fz223', e.target.checked)}
                  className="rounded text-blue-600 focus:ring-blue-500"
                />
                <span>223-ФЗ</span>
              </label>
              <button
                type="button"
                onClick={handleReset}
                className="ml-auto text-sm text-[var(--color-fog)] hover:text-[var(--color-ember-bright)] flex items-center gap-1"
              >
                <X className="h-3 w-3" /> Сбросить все
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}







