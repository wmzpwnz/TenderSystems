import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

// Способы определения поставщика (подрядчика, исполнителя)
const PROCEDURE_TYPES = [
  {
    category: '44-ФЗ',
    methods: [
      'Электронный аукцион',
      'Конкурс с ограниченным участием',
      'Двухэтапный конкурс',
      'Открытый конкурс',
      'Запрос котировок',
      'Запрос предложений',
      'Закрытый конкурс',
      'Закрытый аукцион',
      'Закупка у единственного поставщика',
    ],
  },
  {
    category: '223-ФЗ',
    methods: [
      'Аукцион в электронной форме (223-ФЗ)',
      'Конкурс в электронной форме (223-ФЗ)',
      'Запрос котировок в электронной форме (223-ФЗ)',
      'Запрос предложений в электронной форме (223-ФЗ)',
      'Закупка у единственного поставщика (223-ФЗ)',
    ],
  },
  {
    category: 'Коммерческие закупки',
    methods: [
      'Открытый тендер',
      'Закрытый тендер',
      'Предварительный отбор',
      'Прямая закупка',
    ],
  },
]

interface ProcedureModalProps {
  isOpen: boolean
  onClose: () => void
  selectedProcedures: string[]
  onSave: (procedures: string[]) => void
}

export default function ProcedureModal({
  isOpen,
  onClose,
  selectedProcedures,
  onSave,
}: ProcedureModalProps) {
  const [tempSelected, setTempSelected] = useState<string[]>(selectedProcedures)

  useEffect(() => {
    setTempSelected(selectedProcedures)
  }, [selectedProcedures, isOpen])

  const toggleProcedure = (procedure: string) => {
    if (tempSelected.includes(procedure)) {
      setTempSelected(tempSelected.filter((p) => p !== procedure))
    } else {
      setTempSelected([...tempSelected, procedure])
    }
  }

  const toggleAllInCategory = (category: string) => {
    const categoryData = PROCEDURE_TYPES.find((c) => c.category === category)
    if (!categoryData) return

    const allSelected = categoryData.methods.every((m) => tempSelected.includes(m))

    if (allSelected) {
      setTempSelected(tempSelected.filter((p) => !categoryData.methods.includes(p)))
    } else {
      setTempSelected([...new Set([...tempSelected, ...categoryData.methods])])
    }
  }

  const toggleAll = () => {
    const allMethods = PROCEDURE_TYPES.flatMap((c) => c.methods)
    const allSelected = allMethods.every((m) => tempSelected.includes(m))

    if (allSelected) {
      setTempSelected([])
    } else {
      setTempSelected(allMethods)
    }
  }

  const handleSave = () => {
    onSave(tempSelected)
    onClose()
  }

  const handleClear = () => {
    setTempSelected([])
  }

  if (!isOpen) return null

  const allMethods = PROCEDURE_TYPES.flatMap((c) => c.methods)
  const allSelected = allMethods.every((m) => tempSelected.includes(m))

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
              <h2 className="blueprint-heading text-2xl">Способ определения поставщика</h2>
              {tempSelected.length > 0 && (
                <p className="text-sm text-[var(--color-fog)] mt-1">Выбрано: {tempSelected.length}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-2 blueprint-button-ghost transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Procedures List */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-6">
              {/* Все способы */}
              <label className="blueprint-panel flex items-center gap-3 p-3 cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={toggleAll}
                  className="h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                />
                <span className="font-semibold text-[var(--color-glacier)]">Все способы</span>
              </label>

              {/* Categories */}
              {PROCEDURE_TYPES.map(({ category, methods }) => {
                const allCategorySelected = methods.every((m) => tempSelected.includes(m))
                const someCategorySelected = methods.some((m) => tempSelected.includes(m))

                return (
                  <div key={category} className="space-y-2">
                    {/* Category Header */}
                    <label className="blueprint-panel flex items-center gap-3 p-3 cursor-pointer transition-colors">
                      <input
                        type="checkbox"
                        checked={allCategorySelected}
                        ref={(input) => {
                          if (input) input.indeterminate = someCategorySelected && !allCategorySelected
                        }}
                        onChange={() => toggleAllInCategory(category)}
                        className="h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                      />
                      <span className="font-semibold text-[var(--color-glacier)]">{category}</span>
                    </label>

                    {/* Methods */}
                    <div className="ml-8 space-y-1">
                      {methods.map((method) => (
                        <label
                          key={method}
                          className="flex items-center gap-3 p-2 hover:bg-[rgba(199,211,234,0.08)] rounded-md cursor-pointer transition-colors"
                        >
                          <input
                            type="checkbox"
                            checked={tempSelected.includes(method)}
                            onChange={() => toggleProcedure(method)}
                            className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-2 focus:ring-blue-500"
                          />
                          <span className="text-[var(--color-moonlight)]">{method}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Footer */}
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
