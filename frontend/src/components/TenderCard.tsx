import { Tender, crmApi, analysisApi } from '../api/client'
import { format } from 'date-fns'
import { Calendar, MapPin, ArrowRight, Sparkles, AlertCircle, Package, ExternalLink, Building2, X, DollarSign, Heart } from 'lucide-react'
import { motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'

interface TenderCardProps {
  tender: Tender
  onClick: () => void
  isViewed?: boolean
}

export default function TenderCard({ tender, onClick, isViewed }: TenderCardProps) {
  const queryClient = useQueryClient()

  const toggleFavoriteMutation = useMutation({
    mutationFn: (tenderId: string | number) => crmApi.toggleFavorite(tenderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] })
      queryClient.invalidateQueries({ queryKey: ['favorites'] })
    }
  })

  const quickAnalyzeMutation = useMutation({
    mutationFn: () => analysisApi.analyze(tender.id, 'quick'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenders'] })
      queryClient.invalidateQueries({ queryKey: ['favorites'] })
    }
  })

  const getAiVerdict = () => {
    if (!tender.is_analyzed) return null

    // 1. Risk level mapping
    let riskStr = ''
    const r = tender.analysis_risk_level?.toLowerCase()
    if (r === 'high') {
      riskStr = '🔴 Высокий риск'
    } else if (r === 'medium') {
      riskStr = '🟡 Средний риск'
    } else if (r === 'low') {
      riskStr = '🟢 Низкий риск'
    } else {
      riskStr = '✨ Проанализировано'
    }

    // 2. Margin formatting
    let marginStr = ''
    if (tender.analysis_margin_analysis) {
      if (typeof tender.analysis_margin_analysis === 'string') {
        marginStr = tender.analysis_margin_analysis
      } else if (typeof tender.analysis_margin_analysis === 'object') {
        const entries = Object.entries(tender.analysis_margin_analysis)
        const marginEntry = entries.find(([k]) => k.toLowerCase().includes('марж') || k.toLowerCase().includes('рентаб') || k.toLowerCase().includes('чист')) || entries[0]
        if (marginEntry) {
          marginStr = `${marginEntry[0]}: ${marginEntry[1]}`
        }
      }
    }

    // 3. Summary formatting
    let summaryStr = tender.analysis_summary || ''
    if (summaryStr.length > 80) {
      summaryStr = summaryStr.substring(0, 77) + '...'
    }

    // Build parts
    const parts = [riskStr]
    if (marginStr) parts.push(marginStr)
    if (summaryStr) parts.push(summaryStr)

    return parts.join(' · ')
  }

  const formatPrice = (price: number | null) => {
    if (!price) return 'Не указана'
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0,
    }).format(price).replace('руб.', '₽').replace('RUB', '₽')
  }

  const formatDate = (date: string | null) => {
    if (!date) return 'Не указана'
    try {
      // Support for both dd.MM.yyyy and ISO formats
      if (date.includes('.') && date.length <= 10) return date
      return format(new Date(date), 'dd.MM.yyyy')
    } catch {
      return date
    }
  }

  const formatPrepayment = (prepaymentType: string | null) => {
    if (!prepaymentType) return null
    if (prepaymentType === 'prepayment_44fz') return 'Аванс по 44-ФЗ'
    if (prepaymentType === 'prepayment_223fz') return 'Аванс по 223-ФЗ'
    if (prepaymentType === 'no_prepayment') return 'Без аванса'
    return prepaymentType
  }

  const priceVal = tender.initial_price || 0
  const tenderType = priceVal > 10000000 ? 'large' : priceVal > 1000000 ? 'medium' : 'small'

  const typeColors = {
    large: 'border-l-[var(--color-frost-link)]',
    medium: 'border-l-[var(--color-moonlight)]',
    small: 'border-l-[var(--color-fog)]'
  }

  const getStatusDisplay = (status: string | null) => {
    if (!status) return 'Активен'
    const s = status.toLowerCase()

    // mapping legacy codes to Russian if they still come through
    if (s === 'active') return 'Подача заявок'
    if (s === 'completed') return 'Завершено'
    if (s === 'evaluation') return 'Работа комиссии'
    if (s === 'cancelled') return 'Отменено'

    return status // If it's already Russian (from new parser), just return it
  }

  const getStatusColor = (status: string | null) => {
    if (!status) return 'blueprint-status'
    const s = status.toLowerCase()

    if (s.includes('подача') || s === 'active') return 'blueprint-status'
    if (s.includes('комисси') || s.includes('рассмотре') || s === 'evaluation') return 'blueprint-status'
    if (s.includes('завершено') || s.includes('заключен') || s === 'completed') return 'blueprint-status opacity-70'
    if (s.includes('отменен') || s.includes('несостоявш') || s === 'cancelled') return 'border-[rgba(228,109,76,0.38)] bg-[rgba(228,109,76,0.12)] text-[var(--color-ember-bright-soft)]'

    return 'blueprint-status'
  }

  const purchaseObject = tender.purchaseObjectInfo || tender.title || 'Наименование не указано'

  const getUrgency = () => {
    // If the status indicates it's already finished, return 'past'
    const s = tender.status?.toLowerCase() || ''
    if (s.includes('завершено') || s.includes('заключен') || s === 'completed') return 'past'
    if (s.includes('отменен') || s.includes('несостоявш') || s === 'cancelled') return 'past'

    if (!tender.application_deadline) return 'normal'
    try {
      const deadline = new Date(tender.application_deadline)
      const now = new Date()
      // If date is in dd.mm.yyyy format, convert it
      if (tender.application_deadline.includes('.')) {
        const [d, m, y] = tender.application_deadline.split('.')
        deadline.setFullYear(parseInt(y), parseInt(m) - 1, parseInt(d))
      }

      const diffDays = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))

      if (diffDays < 0) return 'past'
      if (diffDays <= 2) return 'critical'
      if (diffDays <= 5) return 'urgent'
      return 'normal'
    } catch {
      return 'normal'
    }
  }

  const urgencyLevel = getUrgency()
  const urgencyConfig = {
    critical: { text: 'Горит!', color: 'bg-[var(--color-ember)]', icon: AlertCircle },
    urgent: { text: 'Срочно', color: 'bg-[var(--color-ember)]', icon: Calendar },
    normal: { text: 'Активно', color: 'bg-[var(--color-azure)]', icon: Calendar },
    past: { text: 'Завершено', color: 'bg-[rgba(199,211,234,0.16)]', icon: X }
  }

  const UrgencyIcon = (urgencyConfig as any)[urgencyLevel]?.icon

  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.002 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
      onClick={onClick}
      className={clsx(
        "group relative blueprint-card p-0 cursor-pointer",
        "hover:shadow-[var(--shadow-subtle-6)] transition-all duration-300 w-full flex overflow-hidden",
        isViewed && "opacity-60",
        typeColors[tenderType]
      )}
    >
      <div className={clsx(
        "w-1.5 flex-shrink-0",
        tenderType === 'large' ? 'bg-[var(--color-frost-link)]' :
          tenderType === 'medium' ? 'bg-[var(--color-moonlight)]' :
            tenderType === 'small' ? 'bg-[var(--color-fog)]' : 'bg-[rgba(199,211,234,0.18)]'
      )} />

      <div className="flex flex-col md:flex-row flex-1 min-w-0">
        <div className="flex-[2.5] p-5 flex flex-col justify-between border-r border-[rgba(186,215,247,0.12)]">
          <div>
            <div className="flex items-center flex-wrap gap-2 mb-3">
              <span className="blueprint-status text-[10px] font-mono font-bold px-2 py-0.5">
                № {tender.number || tender.eis_id}
              </span>
              <span className={clsx(
                'px-2 py-0.5 text-[10px] font-bold rounded-md uppercase tracking-wider border',
                getStatusColor(tender.status)
              )}>
                {getStatusDisplay(tender.status)}
              </span>
              {tender.is_analyzed ? (
                <span className="flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-bold bg-[rgba(186,215,247,0.06)] border border-[rgba(186,215,247,0.12)] text-[var(--color-glacier)] rounded-md">
                  <Sparkles className="h-3 w-3 text-[var(--color-premium-gold)]" />
                  {getAiVerdict()}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    quickAnalyzeMutation.mutate()
                  }}
                  disabled={quickAnalyzeMutation.isPending}
                  className="flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-bold bg-[rgba(199,211,234,0.08)] hover:bg-[var(--color-electric-iris)] text-[var(--color-frost-link)] hover:text-white rounded-md border border-[rgba(186,215,247,0.12)] transition-colors active:scale-95 disabled:opacity-50"
                >
                  <Sparkles className="h-3 w-3" />
                  {quickAnalyzeMutation.isPending ? 'Анализ...' : 'Быстрый анализ'}
                </button>
              )}
              {isViewed && (
                <span className="text-[9px] font-bold text-[var(--color-fog)] uppercase tracking-widest ml-auto">
                  Просмотрено
                </span>
              )}
            </div>

            <h2 className="text-lg font-semibold text-[var(--color-glacier)] leading-tight group-hover:text-[var(--color-frost-link)] transition-colors mb-4 line-clamp-2">
              {purchaseObject}
            </h2>

            <div className="flex flex-col gap-2.5">
              {tender.customer_name ? (
                <div className="flex flex-col">
                  <div className="flex items-start gap-2 text-[13px] text-[var(--color-moonlight)]">
                    <Building2 className="h-4 w-4 mt-0.5 text-[var(--color-fog)] flex-shrink-0" />
                    <span className="line-clamp-1 font-semibold">{tender.customer_name}</span>
                  </div>
                  {tender.customer_inn && (
                    <span className="text-[11px] text-[var(--color-fog)] font-mono ml-6">ИНН: {tender.customer_inn}</span>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs text-[var(--color-fog)] italic">
                  <Building2 className="h-4 w-4 text-[var(--color-fog)]" />
                  Заказчик не указан (см. на портале)
                </div>
              )}
              {tender.customer_region && (
                <div className="flex items-center gap-2 text-[12px] text-[var(--color-fog)] font-medium">
                  <MapPin className="h-3.5 w-3.5 text-[var(--color-ember)]" />
                  {tender.customer_region}
                </div>
              )}
            </div>
          </div>

          {(() => {
            const tags = []
            if (tender.procedure_type) {
              tags.push(
                <span key="proc" className="blueprint-status text-[10px] px-2 py-1 font-medium whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px]">
                  {tender.procedure_type}
                </span>
              )
            }
            if (tender.platform) {
              tags.push(
                <span key="plat" className="blueprint-status text-[10px] px-2 py-1 font-bold flex items-center gap-1">
                  <ExternalLink className="h-3 w-3" />
                  {tender.platform}
                </span>
              )
            }
            const prep = formatPrepayment(tender.prepayment_type)
            if (prep) {
              tags.push(
                <span key="prep" className="blueprint-status text-[10px] px-2 py-1 font-medium">
                  {prep}
                </span>
              )
            }
            if (tender.preferences?.some(p => p.includes('СМП') || p.includes('СОНКО'))) {
              tags.push(
                <span key="smp" className="blueprint-status text-[10px] px-2 py-1 font-bold flex items-center gap-1">
                  <Package className="h-3 w-3" />
                  СМП / СОНКО
                </span>
              )
            }

            if (tags.length === 0) return null

            const visibleTags = tags.slice(0, 2)
            const remainingCount = tags.length - 2

            return (
              <div className="mt-5 flex items-center gap-2 flex-wrap">
                {visibleTags}
                {remainingCount > 0 && (
                  <span className="blueprint-status text-[10px] px-2 py-1 font-bold bg-[rgba(199,211,234,0.06)] text-[var(--color-fog)]">
                    +{remainingCount}
                  </span>
                )}
              </div>
            )
          })()}
        </div>

        <div className="flex-1 p-5 bg-[rgba(5,6,15,0.28)] flex flex-col justify-between items-end relative overflow-hidden min-w-[220px]">
          {urgencyLevel && urgencyLevel !== 'normal' && (
            <div className={clsx(
              "absolute -top-1 -right-1 px-4 py-1.5 rounded-bl-xl text-white text-[10px] font-black uppercase tracking-widest flex items-center gap-1 shadow-sm z-10",
              (urgencyConfig as any)[urgencyLevel].color
            )}>
              {UrgencyIcon && <UrgencyIcon className="h-3 w-3" />}
              {(urgencyConfig as any)[urgencyLevel].text}
            </div>
          )}

          <div className="text-right w-full mt-2 p-3 bg-[rgba(199,211,234,0.05)] rounded-md border border-[rgba(186,215,247,0.12)] transition-transform group-hover:scale-105">
            <p className="blueprint-eyebrow text-[10px] mb-1">Начальная цена</p>
            <p className="text-2xl font-black text-[var(--color-frost-link)] tracking-tight">
              {formatPrice(tender.initial_price)}
            </p>
          </div>

          <div className="w-full space-y-2 mt-4 px-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--color-fog)] font-medium">Дедлайн подачи:</span>
              <span className={clsx(
                "font-extrabold",
                urgencyLevel === 'critical' ? 'text-[var(--color-ember-bright)]' : 'text-[var(--color-glacier)]'
              )}>
                {formatDate(tender.application_deadline)}
              </span>
            </div>
            {tender.publication_date && (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-[var(--color-fog)]">Опубликовано:</span>
                <span className="text-[var(--color-moonlight)] font-semibold">{formatDate(tender.publication_date)}</span>
              </div>
            )}
          </div>

          <div className="mt-5 w-full flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {tender.prepayment_type && !tender.prepayment_type.includes('Без') && (
                <span className="blueprint-status flex items-center gap-1 px-2 py-1 text-[10px] font-bold" title="Есть аванс">
                  <DollarSign className="h-3.5 w-3.5" />
                  АВАНС
                </span>
              )}
              {tender.preferences && tender.preferences.some(p => p.includes('СМП') || p.includes('СОНКО')) && (
                <span className="blueprint-status flex items-center gap-1 px-2 py-1 text-[10px] font-bold" title="Только для СМП">
                  <Building2 className="h-3.5 w-3.5" />
                  СМП
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 flex-1 justify-end">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFavoriteMutation.mutate(tender.id || tender.eis_id); // Pass tender.id or eis_id
                }}
                disabled={toggleFavoriteMutation.isPending}
                className={clsx(
                  "p-2.5 blueprint-button-ghost transition-all active:scale-90",
                  tender.is_favorite
                    ? "text-[var(--color-ember-bright)]"
                    : "text-[var(--color-fog)] hover:text-[var(--color-ember-bright)]"
                )}
                title={tender.is_favorite ? "Удалить из избранного" : "Добавить в избранное"}
              >
                <Heart className={clsx("h-5 w-5", tender.is_favorite && "fill-current")} />
              </button>

              {tender.url && (
                <a
                  href={tender.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="p-2 blueprint-button-ghost transition-all"
                  title="Перейти в ЕИС"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onClick();
                }}
                className="px-6 py-2 blueprint-button-primary text-[13px] flex items-center gap-2"
              >
                Подробнее
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
