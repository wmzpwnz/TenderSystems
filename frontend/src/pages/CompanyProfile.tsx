import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { companyProfileApi, CompanyProfile } from '../api/client'
import { useState } from 'react'
import { Loader2, Save, Building2, FileText, Award, Briefcase, Settings, CheckCircle2 } from 'lucide-react'
import { motion } from 'framer-motion'

export default function CompanyProfilePage() {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<Partial<CompanyProfile>>({
    name: '',
    inn: '',
    region: '',
    licenses: [],
    sro_certificates: [],
    experience_contracts: 0,
    experience_sum: 0,
    okpd2_codes: [],
    equipment: [],
  })
  const [saveSuccess, setSaveSuccess] = useState(false)

  const { data: profile, isLoading, error } = useQuery({
    queryKey: ['companyProfile'],
    queryFn: () => companyProfileApi.get(),
    retry: false,
    onSuccess: (data) => {
      if (data) {
        setFormData(data)
      }
    },
  })

  const saveMutation = useMutation({
    mutationFn: () => companyProfileApi.createOrUpdate(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyProfile'] })
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    },
  })

  const handleArrayChange = (field: keyof CompanyProfile, value: string) => {
    const current = (formData[field] as string[]) || []
    const items = value.split(',').map(item => item.trim()).filter(Boolean)
    setFormData({ ...formData, [field]: items })
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--color-frost-link)]" />
      </div>
    )
  }

  const sections = [
    {
      icon: Building2,
      title: 'Основная информация',
      delay: 0.1,
      content: (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Название компании
            </label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="blueprint-input px-4 py-3"
              placeholder="ООО «Ваша компания»"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              ИНН
            </label>
            <input
              type="text"
              value={formData.inn || ''}
              onChange={(e) => setFormData({ ...formData, inn: e.target.value })}
              className="blueprint-input px-4 py-3"
              placeholder="1234567890"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Регион работы
            </label>
            <input
              type="text"
              value={formData.region || ''}
              onChange={(e) => setFormData({ ...formData, region: e.target.value })}
              className="blueprint-input px-4 py-3"
              placeholder="Например: Москва"
            />
          </div>
        </div>
      ),
    },
    {
      icon: Award,
      title: 'Лицензии и допуски',
      delay: 0.2,
      content: (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Лицензии (через запятую)
            </label>
            <input
              type="text"
              value={(formData.licenses || []).join(', ')}
              onChange={(e) => handleArrayChange('licenses', e.target.value)}
              className="blueprint-input px-4 py-3"
              placeholder="Например: ФСБ, МЧС, СРО-С-12345"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Допуски СРО (через запятую)
            </label>
            <input
              type="text"
              value={(formData.sro_certificates || []).join(', ')}
              onChange={(e) => handleArrayChange('sro_certificates', e.target.value)}
              className="blueprint-input px-4 py-3"
              placeholder="Например: СРО-С-12345, СРО-И-67890"
            />
          </div>
        </div>
      ),
    },
    {
      icon: Briefcase,
      title: 'Опыт работы',
      delay: 0.3,
      content: (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Количество выполненных контрактов
            </label>
            <input
              type="number"
              value={formData.experience_contracts || 0}
              onChange={(e) => setFormData({ ...formData, experience_contracts: parseInt(e.target.value) || 0 })}
              className="blueprint-input px-4 py-3"
              placeholder="0"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
              Сумма выполненных контрактов (₽)
            </label>
            <input
              type="number"
              value={formData.experience_sum || 0}
              onChange={(e) => setFormData({ ...formData, experience_sum: parseFloat(e.target.value) || 0 })}
              className="blueprint-input px-4 py-3"
              placeholder="0"
            />
          </div>
        </div>
      ),
    },
    {
      icon: FileText,
      title: 'Специализация',
      delay: 0.4,
      content: (
        <div>
          <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
            Коды ОКПД2 (через запятую)
          </label>
          <input
            type="text"
            value={(formData.okpd2_codes || []).join(', ')}
            onChange={(e) => handleArrayChange('okpd2_codes', e.target.value)}
            className="blueprint-input px-4 py-3"
            placeholder="Например: 41.20.10.110, 43.21.10.000"
          />
        </div>
      ),
    },
    {
      icon: Settings,
      title: 'Оборудование',
      delay: 0.5,
      content: (
        <div>
          <label className="block text-sm font-semibold text-[var(--color-moonlight)] mb-2">
            Оборудование в наличии (через запятую)
          </label>
          <input
            type="text"
            value={(formData.equipment || []).join(', ')}
            onChange={(e) => handleArrayChange('equipment', e.target.value)}
            className="blueprint-input px-4 py-3"
            placeholder="Например: Экскаватор, Кран, Бетономешалка"
          />
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-4 mb-4">
          <div className="blueprint-icon-tile h-14 w-14">
            <Building2 className="h-8 w-8" />
          </div>
          <div>
            <p className="blueprint-eyebrow mb-2">company profile</p>
            <h1 className="blueprint-heading text-4xl mb-2">Профиль компании</h1>
            <p className="text-[var(--color-pebble)]">Настройте параметры для улучшения поиска тендеров</p>
          </div>
        </div>
      </motion.div>

      {saveSuccess && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="blueprint-success mb-6 p-4 flex items-center gap-3"
        >
          <CheckCircle2 className="h-5 w-5 text-[var(--color-cipher-mint)]" />
          <span className="font-medium">Профиль успешно сохранен!</span>
        </motion.div>
      )}
      
      <div className="blueprint-section p-8">
        <form onSubmit={(e) => { e.preventDefault(); saveMutation.mutate() }}>
          <div className="space-y-8">
            {sections.map(({ icon: Icon, title, delay, content }) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay }}
                className="blueprint-panel p-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="blueprint-icon-tile h-10 w-10">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h2 className="blueprint-heading text-2xl">{title}</h2>
                </div>
                {content}
              </motion.div>
            ))}

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <button
                type="submit"
                disabled={saveMutation.isPending}
                className="blueprint-button-primary w-full px-8 py-4 text-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
              >
                {saveMutation.isPending ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Сохранение...</span>
                  </>
                ) : (
                  <>
                    <Save className="h-5 w-5" />
                    <span>Сохранить профиль</span>
                  </>
                )}
              </button>
            </motion.div>
          </div>
        </form>
      </div>
    </div>
  )
}






