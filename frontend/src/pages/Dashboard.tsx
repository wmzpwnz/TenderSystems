import { useState, useMemo, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Link, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import clsx from 'clsx'
import {
  Sparkles, TrendingUp, Clock, DollarSign, Target,
  Zap, BarChart3, Bell, LogIn, LogOut, User as UserIcon, Trash2, Heart, Search
} from 'lucide-react'
import AdvancedSearch from '../components/AdvancedSearch'
import TenderCard from '../components/TenderCard'
import { SkeletonCard } from '../components/SkeletonCard'
import { tendersApi, crmApi, subscriptionsApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

export default function DashboardNew() {
  const navigate = useNavigate()
  const { user, logout, updateUser, isLoading: isAuthLoading } = useAuth()
  const queryClient = useQueryClient()
  const [searchFilters, setSearchFilters] = useState<any>({
    procurement_types: ['44-ФЗ', '223-ФЗ']
  })
  const [currentPage, setCurrentPage] = useState(1)
  const [hasSearched, setHasSearched] = useState(false) // Флаг: был ли выполнен поиск
  const [searchTimestamp, setSearchTimestamp] = useState<number>(Date.now()) // Timestamp для уникальности запросов
  const [viewedTenders, setViewedTenders] = useState<string[]>(() => {
    const saved = localStorage.getItem('viewedTenders')
    return saved ? JSON.parse(saved) : []
  })
  const [activeTab, setActiveTab] = useState<'all' | 'favorites' | 'subscriptions'>('all')
  const pageSize = 100 // Увеличиваем размер страницы для показа большего количества результатов

  const markAsViewed = (id: string) => {
    if (!viewedTenders.includes(id)) {
      const newViewed = [...viewedTenders, id]
      setViewedTenders(newViewed)
      localStorage.setItem('viewedTenders', JSON.stringify(newViewed))
    }
  }

  // Всегда используем Live Search для актуальных данных с сайта ЕИС
  // Создаем уникальный ключ кеша на основе всех фильтров
  // ВАЖНО: Используем null вместо undefined, чтобы JSON.stringify включал все поля
  const cacheKey = useMemo(() => {
    // Нормализуем фильтры для стабильного сравнения
    // Используем null вместо undefined, чтобы поля попадали в JSON
    const normalizedFilters = {
      regions: searchFilters.regions && searchFilters.regions.length > 0 ? [...searchFilters.regions].sort() : null,
      statuses: searchFilters.statuses && searchFilters.statuses.length > 0 ? [...searchFilters.statuses].sort() : null,
      query: searchFilters.query || null,
      exclude_keywords: searchFilters.exclude_keywords || null,
      procurement_types: searchFilters.procurement_types && searchFilters.procurement_types.length > 0 ? [...searchFilters.procurement_types].sort() : null,
      okpd2_codes: searchFilters.okpd2_codes && searchFilters.okpd2_codes.length > 0 ? [...searchFilters.okpd2_codes].sort() : null,
      price_from: searchFilters.price_from ?? null,
      price_to: searchFilters.price_to ?? null,
      published_from: searchFilters.published_from || null,
      published_to: searchFilters.published_to || null,
      deadline_less_than_days: searchFilters.deadline_less_than_days ?? null,
      customer_name: searchFilters.customer_name || null,
      platform: searchFilters.platform || null,
      guarantee_from: searchFilters.guarantee_from ?? null,
      guarantee_to: searchFilters.guarantee_to ?? null,
      contract_guarantee_from: searchFilters.contract_guarantee_from ?? null,
      contract_guarantee_to: searchFilters.contract_guarantee_to ?? null,
      prepayment_type: searchFilters.prepayment_type || null,
      preferences: searchFilters.preferences && searchFilters.preferences.length > 0 ? [...searchFilters.preferences].sort() : null,
      procedure_types: searchFilters.procedure_types && searchFilters.procedure_types.length > 0 ? [...searchFilters.procedure_types].sort() : null,
      page: currentPage
    }
    
    const key = JSON.stringify(normalizedFilters)
    
    // Логируем для отладки (только в development)
    if (import.meta.env.DEV) {
      console.log('[Dashboard] Search filters changed:', searchFilters)
      console.log('[Dashboard] Normalized filters:', normalizedFilters)
      console.log('[Dashboard] Cache key:', key)
    }
    
    return key
  }, [searchFilters, currentPage])

  // НЕ инвалидируем кеш автоматически - только при нажатии "Применить"
  // Это предотвращает использование старого кеша

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tenders-live-search', cacheKey, searchTimestamp], // Добавляем timestamp для предотвращения кеширования
    queryFn: async () => {
      // Для Live Search берем только первый регион и первый статус
      const region = searchFilters.regions && searchFilters.regions.length > 0 ? searchFilters.regions[0] : undefined
      const status = searchFilters.statuses && searchFilters.statuses.length > 0 ? searchFilters.statuses[0] : undefined
      
      // Логируем для отладки
      if (import.meta.env.DEV) {
        console.log('[Dashboard] Executing queryFn with cacheKey:', cacheKey)
        console.log('[Dashboard] searchFilters.regions:', searchFilters.regions)
        console.log('[Dashboard] selected region:', region)
      }

      // Маппинг типов закупок
      const fz44 = searchFilters.procurement_types
        ? searchFilters.procurement_types.includes('44-ФЗ')
        : true
      const fz223 = searchFilters.procurement_types
        ? searchFilters.procurement_types.includes('223-ФЗ')
        : true

      const searchParams = {
        page: currentPage,
        page_size: pageSize, // Увеличено до 100 для показа большего количества результатов
        query: searchFilters.query || undefined,
        exclude_keywords: searchFilters.exclude_keywords,
        region: region,
        status: status,
        okpd2: searchFilters.okpd2_codes && searchFilters.okpd2_codes.length > 0 ? searchFilters.okpd2_codes[0] : undefined,
        price_from: searchFilters.price_from,
        price_to: searchFilters.price_to,
        published_from: searchFilters.published_from,
        published_to: searchFilters.published_to,
        fz44: fz44,
        fz223: fz223,
        // Дополнительные фильтры, которые нужно передать
        customer_name: searchFilters.customer_name,
        platform: searchFilters.platform,
        deadline_less_than_days: searchFilters.deadline_less_than_days,
        guarantee_from: searchFilters.guarantee_from,
        guarantee_to: searchFilters.guarantee_to,
        contract_guarantee_from: searchFilters.contract_guarantee_from,
        contract_guarantee_to: searchFilters.contract_guarantee_to,
        prepayment_type: searchFilters.prepayment_type,
        preferences: searchFilters.preferences,
        procedure_types: searchFilters.procedure_types
      }
      
      // Логируем параметры запроса для отладки
      if (import.meta.env.DEV) {
        console.log('[Dashboard] Calling liveSearch with params:', searchParams)
      }
      
      const result = await tendersApi.liveSearch(searchParams)
      
      if (import.meta.env.DEV) {
        console.log('[Dashboard] Received result:', { total: result.total, itemsCount: result.items?.length })
      }
      
      return result
    },
    enabled: hasSearched && Boolean(user?.has_active_subscription), // Поиск выполняется ТОЛЬКО после нажатия "Применить"
    staleTime: 0, // Данные сразу считаются устаревшими - всегда делаем новый запрос
    gcTime: 0, // Не кешируем результаты вообще - каждый раз новый запрос
    refetchOnMount: true, // Обновляем при монтировании если enabled=true
    refetchOnWindowFocus: false, // Не обновляем при фокусе окна
    refetchOnReconnect: false, // Не обновляем при восстановлении соединения
  })

  // Запрос статистики
  const { data: statsData } = useQuery({
    queryKey: ['tender-stats'],
    queryFn: () => tendersApi.getStats(),
    enabled: Boolean(user?.has_active_subscription),
    refetchInterval: 60000, // Обновляем каждую минуту
  })

  // Запрос избранных для CRM вкладки
  const { data: favoritesData, isLoading: isFavLoading } = useQuery({
    queryKey: ['favorites'],
    queryFn: () => crmApi.getFavorites(),
    enabled: activeTab === 'favorites' && Boolean(user?.has_active_subscription)
  })

  // Запрос подписок
  const { data: subscriptionsData, isLoading: isSubLoading, refetch: refetchSubs } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: () => subscriptionsApi.list(),
    enabled: activeTab === 'subscriptions' && Boolean(user?.has_active_subscription)
  })

  // Рассчитываем количество тендеров с близким дедлайном
  const urgentTendersCount = data?.items?.filter(tender => {
    if (!tender.application_deadline) return false
    const deadline = new Date(tender.application_deadline)
    const now = new Date()
    const daysLeft = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return daysLeft <= 7 && daysLeft >= 0
  }).length || 0

  // Рассчитываем количество проанализированных AI
  const analyzedCount = data?.items?.filter(tender => tender.is_analyzed).length || 0

  // Генерация диапазона страниц для пагинации
  const getPageRange = () => {
    const totalPages = data?.pages || 1
    const range = []
    const start = Math.max(1, currentPage - 2)
    const end = Math.min(totalPages, start + 4)
    const actualStart = Math.max(1, end - 4)

    for (let i = actualStart; i <= end; i++) {
      range.push(i)
    }
    return range
  }

  // Статистика (реальные данные)
  const stats = [
    {
      label: 'Всего тендеров',
      value: statsData?.total_tenders || 0,
      change: data?.total ? `${data.total} в поиске` : '',
      icon: Target,
      color: 'bg-blue-500',
      trend: 'neutral'
    },
    {
      label: 'Средняя цена',
      value: statsData?.price?.avg
        ? `${(statsData.price.avg / 1_000_000).toFixed(1)}M ₽`
        : '0 ₽',
      change: statsData?.price?.max
        ? `макс: ${(statsData.price.max / 1_000_000).toFixed(1)}M ₽`
        : '',
      icon: DollarSign,
      color: 'bg-green-500',
      trend: 'neutral'
    },
    {
      label: 'Дедлайн < 7 дней',
      value: urgentTendersCount.toString(),
      change: `из ${data?.total || 0}`,
      icon: Clock,
      color: 'bg-orange-500',
      trend: 'up'
    },
    {
      label: 'AI Проанализировано',
      value: analyzedCount.toString(),
      change: data?.total ? `${Math.round((analyzedCount / data.total) * 100)}%` : '0%',
      icon: Sparkles,
      color: 'bg-purple-500',
      trend: 'up'
    }
  ]

  if (isAuthLoading) {
    return (
      <div className="blueprint-page flex items-center justify-center">
        <div className="text-[var(--color-fog)] font-medium">Загрузка...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!user.has_active_subscription) {
    return (
      <div className="blueprint-page flex items-center justify-center px-4">
        <div className="blueprint-frame w-full max-w-lg p-8 text-center">
          <Sparkles className="h-10 w-10 text-[var(--color-moonlight)] mx-auto mb-4" />
          <h1 className="blueprint-heading text-2xl mb-2">Нужна активная подписка</h1>
          <p className="text-[var(--color-pebble)] mb-6">
            Поиск закупок, live-поиск ЕИС и AI-анализ доступны только пользователям с оплаченной подпиской.
          </p>
          <button
            onClick={logout}
            className="blueprint-button-primary px-5 py-3"
          >
            Выйти
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="blueprint-page">
      <div className="relative overflow-hidden border-b border-[rgba(186,215,247,0.12)]">
        <div className="relative mx-auto max-w-[var(--page-max-width)] px-6 py-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
            <div className="text-center md:text-left">
              <div className="blueprint-eyebrow mb-4">live procurement intelligence</div>
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="blueprint-heading text-5xl mb-3 flex items-center justify-center md:justify-start gap-3"
              >
                <Sparkles className="h-10 w-10 text-[var(--color-moonlight)]" />
                Тендерный Хакер
              </motion.h1>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-[var(--color-pebble)] text-lg"
              >
                AI-ассистент для умного поиска и анализа госзакупок
              </motion.p>
            </div>

            <div className="flex items-center gap-3">
              {user ? (
                <>
                  <div className="flex items-center gap-2 mr-4 text-[var(--color-moonlight)]">
                    <UserIcon className="h-5 w-5" />
                    <span className="font-medium">{user.full_name || user.email}</span>
                  </div>
                  <button className="p-3 blueprint-button-ghost">
                    <Bell className="h-6 w-6" />
                  </button>
                  <button
                    onClick={logout}
                    className="px-4 py-2 blueprint-button-ghost flex items-center gap-2"
                  >
                    <LogOut className="h-5 w-5" />
                    <span className="font-medium">Выход</span>
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="px-4 py-2 blueprint-button-primary flex items-center gap-2"
                >
                  <LogIn className="h-5 w-5" />
                  Войти
                </Link>
              )}
            </div>
          </div>

          {/* Поисковая панель */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <AdvancedSearch
              onSearch={(f) => {
                // Этот callback НЕ должен вызываться автоматически
                // Только обновляем фильтры для отображения в UI
                if (import.meta.env.DEV) {
                  console.log('[Dashboard] onSearch called - updating filters only (no search):', f)
                }
                setSearchFilters(f)
                setActiveTab('all')
                // НЕ выполняем поиск - только обновляем состояние фильтров
              }}
              initialFilters={searchFilters}
              onForceSearch={() => {
                if (import.meta.env.DEV) {
                  console.log('[Dashboard] onForceSearch called - executing NEW search')
                }
                // При нажатии "Применить" - выполняем поиск
                setCurrentPage(1) // Сбрасываем на первую страницу
                // Полностью удаляем ВСЕ старые запросы из кеша
                queryClient.removeQueries({ queryKey: ['tenders-live-search'] })
                // Обновляем timestamp для создания нового уникального запроса (обход кеша)
                setSearchTimestamp(Date.now())
                // Включаем выполнение запроса - React Query автоматически выполнит запрос при изменении enabled
                setHasSearched(true)
              }}
            />
          </motion.div>
        </div>
      </div>

      {/* Статистические карточки */}
      <div className="mx-auto max-w-[var(--page-max-width)] px-4 md:px-6 -mt-8 relative z-10">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          {stats.map((stat, index) => {
            // Вычисляем прогресс для визуализации
            const progress = stat.label === 'Всего тендеров'
              ? Math.min(100, (statsData?.total_tenders || 0) / 1000 * 100)
              : stat.label === 'AI Проанализировано'
                ? Math.min(100, (analyzedCount / Math.max(data?.total || 1, 1)) * 100)
                : 75

            return (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                className="blueprint-card p-5 md:p-6 transition-all cursor-pointer group hover:shadow-[var(--shadow-subtle-6)]"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 md:p-4 rounded-md bg-[rgba(199,211,234,0.06)] shadow-[var(--shadow-subtle)] transition-shadow group-hover:shadow-[var(--shadow-sm)]">
                    <stat.icon className="h-6 w-6 md:h-7 md:w-7 text-[var(--color-moonlight)]" />
                  </div>
                  <div className={`flex items-center gap-1 text-xs md:text-sm font-medium ${stat.trend === 'up' ? 'text-[var(--color-cipher-mint)]' : stat.trend === 'down' ? 'text-[#ff9b83]' : 'text-[var(--color-fog)]'}`}>
                    {stat.trend !== 'neutral' && (
                      <TrendingUp className={`h-4 w-4 ${stat.trend === 'down' ? 'rotate-180' : ''}`} />
                    )}
                    {stat.change}
                  </div>
                </div>

                {/* Прогресс-бар */}
                <div className="mb-3">
                  <div className="h-1.5 md:h-2 bg-[rgba(199,211,234,0.08)] rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 1, delay: 0.5 + index * 0.1 }}
                      className="h-full bg-[var(--color-electric-iris)] rounded-full"
                    />
                  </div>
                </div>

                <div className="blueprint-heading text-3xl md:text-4xl mb-1">{stat.value}</div>
                <div className="text-xs md:text-sm text-[var(--color-fog)] font-medium">{stat.label}</div>
              </motion.div>
            )
          })}
        </div>
      </div>

      {/* Результаты поиска */}
      <main className="mx-auto max-w-[var(--page-max-width)] px-4 sm:px-6 lg:px-8 py-8">

        <div className="mt-12 flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <div className="flex items-center gap-4 mb-3">
              <button
                onClick={() => setActiveTab('all')}
                className={clsx(
                  "text-2xl font-semibold transition-all",
                  activeTab === 'all' ? "text-[var(--color-glacier)] border-b border-[var(--color-frost-link)] pb-1" : "text-[var(--color-fog)] hover:text-[var(--color-moonlight)]"
                )}
              >
                Все тендеры
              </button>
              <button
                onClick={() => setActiveTab('favorites')}
                className={clsx(
                  "text-2xl font-semibold transition-all flex items-center gap-2",
                  activeTab === 'favorites' ? "text-[var(--color-glacier)] border-b border-[var(--color-frost-link)] pb-1" : "text-[var(--color-fog)] hover:text-[var(--color-moonlight)]"
                )}
              >
                Избранное
                {favoritesData && (favoritesData as any[]).length > 0 && (
                  <span className="bg-[rgba(228,109,76,0.18)] text-[#ffb39f] text-xs font-bold rounded-full h-6 px-2 flex items-center justify-center">
                    {(favoritesData as any[]).length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('subscriptions')}
                className={clsx(
                  "text-2xl font-semibold transition-all flex items-center gap-2",
                  activeTab === 'subscriptions' ? "text-[var(--color-glacier)] border-b border-[var(--color-frost-link)] pb-1" : "text-[var(--color-fog)] hover:text-[var(--color-moonlight)]"
                )}
              >
                Подписки
                {subscriptionsData && (subscriptionsData as any[]).length > 0 && (
                  <span className="bg-[rgba(228,109,76,0.18)] text-[#ffb39f] text-xs font-bold rounded-full h-6 px-2 flex items-center justify-center">
                    {(subscriptionsData as any[]).length}
                  </span>
                )}
              </button>
            </div>
            <p className="text-[var(--color-fog)]">
              {activeTab === 'all'
                ? hasSearched 
                  ? `Найдено ${data?.total?.toLocaleString('ru-RU') || 0} актуальных закупок`
                  : 'Настройте фильтры и нажмите "Применить" для поиска'
                : activeTab === 'favorites'
                  ? `У вас ${(favoritesData as any[])?.length || 0} сохраненных тендеров`
                  : `У вас ${(subscriptionsData as any[])?.length || 0} активных подписок`
              }
            </p>
          </div>

          {/* Сортировка и экспорт */}
          <div className="flex flex-wrap items-center gap-3">
            {activeTab === 'all' && data?.items && data.items.length > 0 && (
              <button
                onClick={async () => {
                  try {
                    // Используем те же фильтры, что и для поиска
                    const region = searchFilters.regions && searchFilters.regions.length > 0 ? searchFilters.regions[0] : undefined
                    const status = searchFilters.statuses && searchFilters.statuses.length > 0 ? searchFilters.statuses[0] : undefined
                    const fz44 = searchFilters.procurement_types ? searchFilters.procurement_types.includes('44-ФЗ') : true
                    const fz223 = searchFilters.procurement_types ? searchFilters.procurement_types.includes('223-ФЗ') : true

                    const blob = await tendersApi.exportExcel({
                      query: searchFilters.query,
                      exclude_keywords: searchFilters.exclude_keywords,
                      region: region,
                      status: status,
                      okpd2: searchFilters.okpd2_codes && searchFilters.okpd2_codes.length > 0 ? searchFilters.okpd2_codes[0] : undefined,
                      price_from: searchFilters.price_from,
                      price_to: searchFilters.price_to,
                      published_from: searchFilters.published_from,
                      published_to: searchFilters.published_to,
                      fz44: fz44,
                      fz223: fz223,
                      page: currentPage,
                      page_size: pageSize
                    })

                    const url = window.URL.createObjectURL(new Blob([blob]))
                    const link = document.createElement('a')
                    link.href = url
                    link.setAttribute('download', `tenders_export_${new Date().toISOString().split('T')[0]}.xlsx`)
                    document.body.appendChild(link)
                    link.click()
                    link.remove()
                  } catch (err) {
                    console.error('Export error:', err)
                    alert('Ошибка при экспорте в Excel')
                  }
                }}
                className="px-4 py-2 blueprint-button-ghost font-bold flex items-center gap-2"
              >
                <div className="p-1 bg-white/20 rounded">
                  <BarChart3 className="h-4 w-4" />
                </div>
                Excel
              </button>
            )}

            <select className="px-4 py-2 blueprint-input max-w-[220px]">
              <option>По релевантности</option>
              <option>По цене (возр.)</option>
              <option>По цене (убыв.)</option>
              <option>По дедлайну</option>
              <option>По дате публикации</option>
            </select>
          </div>
        </div>

        {/* Skeleton Loaders */}
        {isLoading && activeTab === 'all' && (
          <div className="flex flex-col gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="border border-[rgba(228,109,76,0.38)] bg-[rgba(228,109,76,0.12)] rounded-md p-6 text-center">
            <p className="text-[#ffb39f] font-medium">Ошибка загрузки данных</p>
            <p className="text-[#ff9b83] text-sm mt-1">Проверьте подключение к API</p>
          </div>
        )}

        {/* Tender List & Tabs Content */}
        <div className="mb-10">
          {(isLoading || (activeTab === 'favorites' && isFavLoading) || (activeTab === 'subscriptions' && isSubLoading)) ? (
            <div className="grid grid-cols-1 gap-4">
              {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : activeTab === 'all' ? (
            !hasSearched ? (
              <div className="blueprint-card py-20 text-center border-dashed">
                <Search className="h-16 w-16 text-[var(--color-fog)] mx-auto mb-4" />
                <h3 className="blueprint-heading text-xl mb-2">Настройте фильтры и нажмите "Применить"</h3>
                <p className="text-[var(--color-fog)]">Список тендеров появится после выполнения поиска</p>
              </div>
            ) : data?.items && data.items.length > 0 ? (
              <div className="grid grid-cols-1 gap-4">
                {data.items.map((tender: any) => (
                  <TenderCard
                    key={tender.id || tender.eis_id}
                    tender={tender}
                    isViewed={viewedTenders.includes(String(tender.id))}
                    onClick={() => {
                      markAsViewed(String(tender.id))
                      navigate(`/tender/${tender.eis_id}`)
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className="blueprint-card py-20 text-center border-dashed">
                <Search className="h-16 w-16 text-[var(--color-fog)] mx-auto mb-4" />
                <h3 className="blueprint-heading text-xl mb-2">Ничего не найдено</h3>
                <p className="text-[var(--color-fog)]">Попробуйте изменить параметры поиска</p>
              </div>
            )
          ) : activeTab === 'favorites' ? (
            <div className="grid grid-cols-1 gap-4">
              {(favoritesData && (favoritesData as any[]).length > 0) ? (
                (favoritesData as any[]).map((fav: any) => (
                  <TenderCard
                    key={fav.id || fav.eis_id}
                    tender={fav}
                    onClick={() => navigate(`/tender/${fav.eis_id}`)}
                  />
                ))
              ) : (
                <div className="blueprint-card py-20 text-center border-dashed">
                  <Heart className="h-16 w-16 text-[var(--color-fog)] mx-auto mb-4" />
                  <h3 className="blueprint-heading text-xl mb-2">В избранном пока пусто</h3>
                  <p className="text-[var(--color-fog)]">Нажимайте на сердечко в карточках тендеров, чтобы сохранить их здесь.</p>
                </div>
              )}
            </div>
          ) : (
            /* Вкладка Подписки */
            <div className="space-y-6">
              {!user?.telegram_chat_id && (
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="blueprint-section p-8 flex flex-col md:flex-row items-center justify-between gap-6"
                >
                  <div className="flex items-center gap-6">
                    <div className="blueprint-icon-tile blueprint-pulse-glow h-16 w-16 group">
                      <Bell className="h-8 w-8 text-[var(--color-glacier)]" />
                    </div>
                    <div>
                      <h3 className="blueprint-heading text-2xl mb-1">Получайте уведомления в Telegram</h3>
                      <p className="text-[var(--color-pebble)] font-medium">Чтобы бот мог присылать вам новые тендеры, нужно привязать аккаунт.</p>
                      <div className="blueprint-eyebrow mt-3 flex items-center gap-2 text-[10px] text-[var(--color-ember)]">
                        <Zap className="h-3 w-3" />
                        Мгновенные оповещения 24/7
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={async () => {
                      const id = prompt('Введите ваш Telegram Chat ID (узнать его можно у бота @userinfobot):');
                      if (id) {
                        try {
                          await updateUser({ telegram_chat_id: id });
                          alert('Telegram успешно привязан!');
                        } catch (err) {
                          alert('Ошибка при сохранении ID');
                        }
                      }
                    }}
                    className="blueprint-button-primary px-8 py-4 active:scale-95 whitespace-nowrap"
                  >
                    Привязать бота
                  </button>
                </motion.div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {subscriptionsData && (subscriptionsData as any[]).length > 0 ? (
                  (subscriptionsData as any[]).map((sub) => (
                    <motion.div
                      key={sub.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="blueprint-card p-6 group"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div className="blueprint-icon-tile h-12 w-12 transition-transform group-hover:scale-105">
                          <Bell className="h-6 w-6" />
                        </div>
                        <button
                          onClick={async () => {
                            if (confirm('Удалить подписку?')) {
                              try {
                                await subscriptionsApi.delete(sub.id);
                                refetchSubs();
                              } catch (err) {
                                console.error('Delete error:', err);
                              }
                            }
                          }}
                          className="blueprint-button-ghost p-2 text-[var(--color-fog)] hover:text-[#ff9b83] transition-all"
                          title="Удалить подписку"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      </div>
                      <h4 className="blueprint-heading text-xl mb-2 truncate">{sub.name}</h4>
                      <div className="space-y-2 mb-6">
                        {sub.filters.query && (
                          <div className="text-sm text-[var(--color-pebble)] flex items-center gap-1 font-bold">
                            <Target className="h-4 w-4 text-[var(--color-fog)]" />
                            «{sub.filters.query}»
                          </div>
                        )}
                        <div className="flex flex-wrap gap-2 text-[10px] uppercase font-black">
                          {sub.filters.regions?.map((r: string) => (
                            <span key={r} className="blueprint-status px-2 py-1">
                              {r}
                            </span>
                          ))}
                          {sub.filters.okpd2_codes?.map((c: string) => (
                            <span key={c} className="blueprint-status px-2 py-1">
                              ОКПД: {c}
                            </span>
                          ))}
                          {sub.filters.prepayment_type && (
                            <span className="blueprint-status px-2 py-1">
                              Аванс
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center justify-between pt-4 border-t border-[rgba(186,215,247,.12)] text-[10px] text-[var(--color-fog)] font-bold uppercase tracking-widest">
                        <span>Дата: {new Date(sub.updated_at).toLocaleDateString()}</span>
                        <div className="flex items-center gap-2">
                          <div className={clsx("w-2 h-2 rounded-full", sub.is_active ? "bg-[var(--color-cipher-mint)] blueprint-pulse-glow" : "bg-[var(--color-fog)]")} />
                          {sub.is_active ? "Мониторинг" : "Пауза"}
                        </div>
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <div className="blueprint-card col-span-full py-20 text-center border-dashed">
                    <div className="blueprint-icon-tile h-24 w-24 mx-auto mb-6">
                      <Bell className="h-12 w-12 text-[var(--color-fog)]" />
                    </div>
                    <p className="blueprint-heading text-2xl">У вас пока нет активных подписок</p>
                    <p className="text-[var(--color-fog)] font-medium mt-2 max-w-sm mx-auto">
                      Настройте фильтры и нажмите <b>«Следить»</b>, чтобы мы мониторили ЕИС за вас 24/7.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {activeTab === 'all' && data && data.total > pageSize && (
          <div className="mt-10 flex justify-center items-center gap-2">
            <button
              onClick={() => {
                const newPage = Math.max(1, currentPage - 1)
                setCurrentPage(newPage)
                // Обновляем timestamp для обхода кеша при изменении страницы
                setSearchTimestamp(Date.now())
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
              disabled={currentPage === 1}
              className="blueprint-button-ghost px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Назад
            </button>
            <div className="flex items-center gap-1">
              {getPageRange().map(page => (
                <button
                  key={page}
                  onClick={() => {
                    setCurrentPage(page)
                    // Обновляем timestamp для обхода кеша при изменении страницы
                    setSearchTimestamp(Date.now())
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                  className={`px-4 py-2 font-medium transition-all ${page === currentPage
                    ? 'blueprint-button-primary'
                    : 'blueprint-button-ghost'
                    }`}
                >
                  {page}
                </button>
              ))}
            </div>
            <button
              onClick={() => {
                const newPage = Math.min(data.pages || 1, currentPage + 1)
                setCurrentPage(newPage)
                // Обновляем timestamp для обхода кеша при изменении страницы
                setSearchTimestamp(Date.now())
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
              disabled={currentPage >= (data.pages || 1)}
              className="blueprint-button-ghost px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Вперёд
            </button>
          </div>
        )}
      </main>

      {/* Floating Action Button */}
      <motion.button
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        className="blueprint-button-primary blueprint-pulse-glow fixed bottom-8 right-8 p-4 rounded-full transition-all z-50"
      >
        <Zap className="h-6 w-6" />
      </motion.button>
    </div>
  )
}
