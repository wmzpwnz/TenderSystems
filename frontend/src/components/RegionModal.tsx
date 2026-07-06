import { useState, useEffect } from 'react'
import { X, Search, ChevronRight, ChevronDown } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// Полный список регионов РФ по федеральным округам
const REGIONS_DATA = {
  'Центральный ФО': [
    'Москва',
    'Московская область',
    'Белгородская область',
    'Брянская область',
    'Владимирская область',
    'Воронежская область',
    'Ивановская область',
    'Калужская область',
    'Костромская область',
    'Курская область',
    'Липецкая область',
    'Орловская область',
    'Рязанская область',
    'Смоленская область',
    'Тамбовская область',
    'Тверская область',
    'Тульская область',
    'Ярославская область',
  ],
  'Северо-Западный ФО': [
    'Санкт-Петербург',
    'Ленинградская область',
    'Архангельская область',
    'Вологодская область',
    'Калининградская область',
    'Республика Карелия',
    'Республика Коми',
    'Мурманская область',
    'Ненецкий АО',
    'Новгородская область',
    'Псковская область',
  ],
  'Южный ФО': [
    'Астраханская область',
    'Волгоградская область',
    'Республика Адыгея',
    'Республика Калмыкия',
    'Краснодарский край',
    'Республика Крым',
    'Ростовская область',
    'Севастополь',
  ],
  'Северо-Кавказский ФО': [
    'Республика Дагестан',
    'Республика Ингушетия',
    'Кабардино-Балкарская Республика',
    'Карачаево-Черкесская Республика',
    'Республика Северная Осетия — Алания',
    'Чеченская Республика',
    'Ставропольский край',
  ],
  'Приволжский ФО': [
    'Республика Башкортостан',
    'Республика Марий Эл',
    'Республика Мордовия',
    'Республика Татарстан',
    'Удмуртская Республика',
    'Чувашская Республика',
    'Кировская область',
    'Нижегородская область',
    'Оренбургская область',
    'Пензенская область',
    'Пермский край',
    'Самарская область',
    'Саратовская область',
    'Ульяновская область',
  ],
  'Уральский ФО': [
    'Курганская область',
    'Свердловская область',
    'Тюменская область',
    'Ханты-Мансийский АО — Югра',
    'Ямало-Ненецкий АО',
    'Челябинская область',
  ],
  'Сибирский ФО': [
    'Республика Алтай',
    'Республика Тыва',
    'Республика Хакасия',
    'Алтайский край',
    'Красноярский край',
    'Иркутская область',
    'Кемеровская область',
    'Новосибирская область',
    'Омская область',
    'Томская область',
  ],
  'Дальневосточный ФО': [
    'Республика Бурятия',
    'Республика Саха (Якутия)',
    'Забайкальский край',
    'Камчатский край',
    'Приморский край',
    'Хабаровский край',
    'Амурская область',
    'Магаданская область',
    'Сахалинская область',
    'Еврейская АО',
    'Чукотский АО',
  ],
}

interface RegionModalProps {
  isOpen: boolean
  onClose: () => void
  selectedRegions: string[]
  onSave: (regions: string[]) => void
}

export default function RegionModal({ isOpen, onClose, selectedRegions, onSave }: RegionModalProps) {
  const [search, setSearch] = useState('')
  const [tempSelected, setTempSelected] = useState<string[]>(selectedRegions)
  const [expandedDistricts, setExpandedDistricts] = useState<Set<string>>(new Set())

  useEffect(() => {
    setTempSelected(selectedRegions)
  }, [selectedRegions, isOpen])

  const toggleDistrict = (district: string) => {
    const newExpanded = new Set(expandedDistricts)
    if (newExpanded.has(district)) {
      newExpanded.delete(district)
    } else {
      newExpanded.add(district)
    }
    setExpandedDistricts(newExpanded)
  }

  const toggleRegion = (region: string) => {
    if (tempSelected.includes(region)) {
      setTempSelected(tempSelected.filter(r => r !== region))
    } else {
      setTempSelected([...tempSelected, region])
    }
  }

  const toggleAllInDistrict = (district: string) => {
    const regions = REGIONS_DATA[district as keyof typeof REGIONS_DATA]
    const allSelected = regions.every(r => tempSelected.includes(r))

    if (allSelected) {
      setTempSelected(tempSelected.filter(r => !regions.includes(r)))
    } else {
      setTempSelected([...new Set([...tempSelected, ...regions])])
    }
  }

  const handleSave = () => {
    onSave(tempSelected)
    onClose()
  }

  const handleClear = () => {
    setTempSelected([])
  }

  // Фильтрация по поиску
  const filteredData = Object.entries(REGIONS_DATA).reduce((acc, [district, regions]) => {
    if (search) {
      const filtered = regions.filter(r =>
        r.toLowerCase().includes(search.toLowerCase())
      )
      if (filtered.length > 0) {
        acc[district] = filtered
      }
    } else {
      acc[district] = regions
    }
    return acc
  }, {} as Record<string, string[]>)

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="blueprint-modal relative w-full max-w-2xl max-h-[80vh] flex flex-col"
        >
          <div className="flex items-center justify-between p-6 border-b border-[rgba(186,215,247,0.12)]">
            <div>
              <p className="blueprint-eyebrow mb-2">filter</p>
              <h2 className="blueprint-heading text-2xl">Регион</h2>
              {tempSelected.length > 0 && (
                <p className="text-sm text-[var(--color-fog)] mt-1">
                  Выбрано: {tempSelected.length}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 blueprint-button-ghost transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="p-4 border-b border-[rgba(186,215,247,0.12)]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--color-fog)]" />
              <input
                type="text"
                placeholder="Поиск региона..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="blueprint-input pl-10 pr-4 py-2"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {Object.entries(filteredData).map(([district, regions]) => {
                const isExpanded = expandedDistricts.has(district) || search !== ''
                const allSelected = regions.every(r => tempSelected.includes(r))
                const someSelected = regions.some(r => tempSelected.includes(r))

                return (
                  <div key={district} className="blueprint-panel overflow-hidden">
                    <div className="flex items-center gap-2 p-3 transition-colors">
                      <button
                        onClick={() => toggleDistrict(district)}
                        className="flex-1 flex items-center gap-2 text-left"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-5 w-5 text-[var(--color-fog)]" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-[var(--color-fog)]" />
                        )}
                        <span className="font-semibold text-[var(--color-glacier)]">{district}</span>
                        <span className="text-sm text-[var(--color-fog)]">({regions.length})</span>
                      </button>

                      <input
                        type="checkbox"
                        checked={allSelected}
                        ref={input => {
                          if (input) input.indeterminate = someSelected && !allSelected
                        }}
                        onChange={() => toggleAllInDistrict(district)}
                        className="h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    {isExpanded && (
                      <div className="p-2 space-y-1">
                        {regions.map((region) => (
                          <label
                            key={region}
                            className="flex items-center gap-3 p-2 hover:bg-[rgba(199,211,234,0.08)] rounded-md cursor-pointer transition-colors"
                          >
                            <input
                              type="checkbox"
                              checked={tempSelected.includes(region)}
                              onChange={() => toggleRegion(region)}
                              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                            />
                            <span className="text-[var(--color-moonlight)]">{region}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="flex items-center justify-between p-4 border-t border-[rgba(186,215,247,0.12)] bg-[rgba(5,6,15,0.18)]">
            <button
              onClick={handleClear}
              className="blueprint-button-ghost px-4 py-2 font-medium"
            >
              Очистить
            </button>

            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="blueprint-button-ghost px-6 py-2 font-medium"
              >
                Отменить
              </button>
              <button
                onClick={handleSave}
                className="blueprint-button-primary px-6 py-2 font-medium"
              >
                Сохранить
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
