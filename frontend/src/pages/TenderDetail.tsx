import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
    ArrowLeft,
    ExternalLink,
    Download,
    Clock,
    MapPin,
    ShieldCheck,
    Sparkles,
    TrendingUp,
    DollarSign,
    Target,
    Zap,
    BarChart3,
    Bell,
    AlertCircle,
    CheckCircle2,
    Info,
    ChevronRight,
    Building2,
    Calendar,
    FileText,
    Shield,
    Briefcase,
    FileCheck,
    HelpCircle,
    Heart,
    Trophy,
    XCircle,
    Share2,
    Printer,
    AlertTriangle
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { tendersApi, analysisApi, crmApi } from '../api/client'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import ReactMarkdown from 'react-markdown'

const CRM_STATUSES = [
    { value: 'saved', label: 'В избранном', icon: Heart },
    { value: 'preparing', label: 'Подготовка заявки', icon: Briefcase },
    { value: 'submitted', label: 'Подано', icon: CheckCircle2 },
    { value: 'won', label: 'Победа', icon: Trophy },
    { value: 'lost', label: 'Проигрыш', icon: XCircle },
]

export default function TenderDetail() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const [activeTab, setActiveTab] = useState<'info' | 'docs' | 'analysis'>('info')
    const [showIntelligence, setShowIntelligence] = useState(true)
    const [showRequirements, setShowRequirements] = useState(true)

    // Загрузка данных тендера
    const { data: tender, isLoading, error } = useQuery({
        queryKey: ['tender', id],
        queryFn: () => tendersApi.getById(id!),
        enabled: !!id,
    })

    const queryClient = useQueryClient()

    // Мутация для запуска анализа (Краткий)
    const analyzeMutation = useMutation({
        mutationFn: () => tendersApi.analyze(id!),
        onSuccess: () => {
            setActiveTab('analysis')
            queryClient.invalidateQueries({ queryKey: ['tender', id] })
        }
    })

    // Мутация для ГЛУБОКОГО анализа
    const deepAnalyzeMutation = useMutation({
        mutationFn: () => tendersApi.deepAnalyze(id!),
        onSuccess: () => {
            setActiveTab('analysis')
            queryClient.invalidateQueries({ queryKey: ['tender', id] })
        }
    })

    // Загрузка статистики по заказчику
    const { data: intelligence, isLoading: isIntLoading } = useQuery({
        queryKey: ['intelligence', tender?.customer_inn],
        queryFn: () => tendersApi.getCustomerIntelligence(tender!.customer_inn!),
        enabled: !!tender?.customer_inn && activeTab === 'info'
    })

    // Мутация для избранного
    const toggleFavoriteMutation = useMutation({
        mutationFn: () => crmApi.toggleFavorite(id!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tender', id] })
            queryClient.invalidateQueries({ queryKey: ['favorites'] })
        }
    })

    // Мутация для статуса CRM
    const updateStatusMutation = useMutation({
        mutationFn: (newStatus: string) => crmApi.updateStatus(id!, newStatus),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tender', id] })
            queryClient.invalidateQueries({ queryKey: ['favorites'] })
        }
    })

    if (isLoading) {
        return (
            <div className="blueprint-page flex flex-col items-center justify-center min-h-[60vh]">
                <div className="relative">
                    <div className="h-16 w-16 rounded-full border-4 border-[rgba(186,215,247,.12)] border-t-[var(--color-frost-link)] animate-spin"></div>
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="absolute inset-0 flex items-center justify-center"
                    >
                        <SearchIcon className="h-6 w-6 text-[var(--color-frost-link)]" />
                    </motion.div>
                </div>
                <p className="mt-4 text-[var(--color-fog)] font-medium animate-pulse">Загружаем детали закупки...</p>
            </div>
        )
    }

    if (error || !tender) {
        return (
            <div className="text-center py-20 px-4">
                <div className="blueprint-danger inline-flex items-center justify-center w-20 h-20 rounded-full mb-6">
                    <AlertTriangle className="h-10 w-10" />
                </div>
                <h2 className="blueprint-heading text-2xl mb-2">Тендер не найден</h2>
                <p className="text-[var(--color-fog)] mb-8 max-w-md mx-auto">Не удалось загрузить данные из ЕИС. Возможно, закупка была удалена или сервер временно недоступен.</p>
                <button
                    onClick={() => navigate('/')}
                    className="blueprint-button-primary inline-flex items-center gap-2 px-6 py-3 active:scale-95"
                >
                    <ArrowLeft className="h-5 w-5" />
                    Вернуться к поиску
                </button>
            </div>
        )
    }

    const getUrgency = (deadline: string | null) => {
        if (!deadline) return 'normal';
        try {
            const diff = new Date(deadline).getTime() - new Date().getTime();
            const days = diff / (1000 * 60 * 60 * 24);
            if (diff < 0) return 'past';
            if (days < 3) return 'urgent';
            if (days < 7) return 'coming';
            return 'normal';
        } catch { return 'normal'; }
    };

    const urgency = getUrgency(tender.application_deadline);

    return (
        <div className="blueprint-page">
            <div className="max-w-7xl mx-auto px-4 py-8 pb-20">
            {/* Хлебные крошки и панель действий */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <nav className="flex items-center gap-2 text-sm text-[var(--color-fog)]">
                    <Link to="/" className="hover:text-[var(--color-glacier)] transition-colors">Поиск тендеров</Link>
                    <ChevronRight className="h-4 w-4" />
                    <span className="text-[var(--color-glacier)] font-medium truncate max-w-[200px] md:max-w-[400px]">
                        {tender.number || tender.eis_id}
                    </span>
                </nav>

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => toggleFavoriteMutation.mutate()}
                        disabled={toggleFavoriteMutation.isPending}
                        className={clsx(
                            "p-2.5 blueprint-button-ghost transition-all active:scale-90",
                            tender.is_favorite
                                ? "text-[#ff9b83]"
                                : "text-[var(--color-moonlight)] hover:text-[#ff9b83]"
                        )}
                        title={tender.is_favorite ? "Удалить из избранного" : "Добавить в избранное"}
                    >
                        <Heart className={clsx("h-5 w-5", tender.is_favorite && "fill-current")} />
                    </button>

                    <button className="p-2.5 blueprint-button-ghost transition-all">
                        <Share2 className="h-5 w-5" />
                    </button>
                    <button className="p-2.5 blueprint-button-ghost transition-all">
                        <Printer className="h-5 w-5" />
                    </button>
                    {tender.url && (
                        <a
                            href={tender.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="blueprint-button-ghost px-5 py-2.5 font-bold transition-all flex items-center gap-2"
                        >
                            Смотреть в ЕИС
                            <ExternalLink className="h-4 w-4" />
                        </a>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                {/* Левая колонка - Основная инфа */}
                <div className="lg:col-span-8 space-y-8">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="blueprint-section p-8"
                    >
                        <div className="flex flex-wrap items-center gap-3 mb-6">
                            <span className="blueprint-status px-3 py-1 text-[11px] font-bold uppercase tracking-wider">
                                {tender.status || 'Активно'}
                            </span>
                            <span className="blueprint-status px-3 py-1 text-[11px] font-bold uppercase tracking-wider">
                                {tender.procedure_type || 'Закупка'}
                            </span>
                            <span className="blueprint-status px-3 py-1 text-[11px] font-bold uppercase tracking-wider">
                                {tender.number?.startsWith('2') ? '223-ФЗ' : '44-ФЗ'}
                            </span>
                        </div>

                        <h1 className="blueprint-heading text-2xl md:text-3xl mb-8">
                            {tender.title}
                        </h1>

                        {/* Интерактивный таймлайн */}
                        <div className="mb-12 px-2">
                            <div className="relative flex items-center justify-between">
                                {/* Линия фона */}
                                <div className="absolute top-5 left-0 right-0 h-0.5 bg-[rgba(186,215,247,.12)] -z-10" />

                                {/* Линия прогресса */}
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{
                                        width: tender.status?.includes('Завершено') ? '100%' :
                                            tender.status?.includes('Заключен') ? '100%' :
                                                tender.status?.includes('Комисси') ? '66%' :
                                                    tender.status?.includes('Подача') ? '33%' : '0%'
                                    }}
                                    className="absolute top-5 left-0 h-0.5 bg-[var(--color-frost-link)] shadow-[var(--shadow-sm)] -z-10"
                                />

                                {[
                                    { label: 'Публикация', date: tender.publication_date, active: true },
                                    { label: 'Подача заявок', date: tender.application_deadline, active: tender.status?.includes('Подача') || !!tender.application_deadline },
                                    { label: 'Рассмотрение', date: null, active: tender.status?.includes('Комисси') || tender.status?.includes('Завершено') },
                                    { label: 'Контракт', date: null, active: tender.status?.includes('Завершено') || tender.status?.includes('Заключен') }
                                ].map((step, i) => (
                                    <div key={i} className="flex flex-col items-center gap-3">
                                        <motion.div
                                            initial={{ scale: 0.8 }}
                                            animate={{
                                                scale: step.active ? 1 : 0.8,
                                                backgroundColor: step.active ? '#663af3' : 'rgba(199,211,234,.08)',
                                                borderColor: step.active ? 'rgba(216,236,248,.28)' : 'rgba(186,215,247,.12)'
                                            }}
                                            className={clsx(
                                                "w-10 h-10 rounded-full border-4 flex items-center justify-center transition-colors",
                                                step.active ? "text-white shadow-[var(--shadow-sm)]" : "text-[var(--color-fog)]"
                                            )}
                                        >
                                            {step.active && !tender.status?.includes('Завершено') && i === (tender.status?.includes('Подача') ? 1 : tender.status?.includes('Комисси') ? 2 : 0) ? (
                                                <div className="w-2 h-2 bg-[var(--color-glacier)] rounded-full animate-ping" />
                                            ) : (
                                                <div className={clsx("w-2 h-2 rounded-full", step.active ? "bg-[var(--color-glacier)]" : "bg-[var(--color-fog)]")} />
                                            )}
                                        </motion.div>
                                        <div className="text-center">
                                            <p className={clsx("text-[11px] font-black uppercase tracking-wider mb-0.5", step.active ? "text-[var(--color-frost-link)]" : "text-[var(--color-fog)]")}>
                                                {step.label}
                                            </p>
                                            {step.date && (
                                                <p className="text-[10px] text-[var(--color-fog)] font-medium">
                                                    {format(new Date(step.date), 'dd.MM', { locale: ru })}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Табы */}
                        <div className="flex items-center gap-6 border-b border-[rgba(186,215,247,.12)] mb-8">
                            {[
                                { id: 'info', label: 'Описание закупки', icon: FileText },
                                { id: 'docs', label: 'Документы', icon: Download },
                                { id: 'analysis', label: 'AI Анализ', icon: Sparkles, badge: 'New' }
                            ].map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id as any)}
                                    className={clsx(
                                        "flex items-center gap-2 pb-4 text-sm font-bold transition-all relative",
                                        activeTab === tab.id ? "text-[var(--color-frost-link)]" : "text-[var(--color-fog)] hover:text-[var(--color-glacier)]"
                                    )}
                                >
                                    <tab.icon className="h-4 w-4" />
                                    {tab.label}
                                    {tab.badge && (
                                        <span className="blueprint-status px-1.5 py-0.5 text-[9px] ml-1">
                                            {tab.badge}
                                        </span>
                                    )}
                                    {activeTab === tab.id && (
                                        <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-[var(--color-frost-link)] rounded-full shadow-[var(--shadow-sm)]" />
                                    )}
                                </button>
                            ))}
                        </div>

                        {/* Контент табов */}
                        <div className="min-h-[300px]">
                            <AnimatePresence mode="wait">
                                {activeTab === 'info' && (
                                    <motion.div
                                        key="info"
                                        initial={{ opacity: 0, x: 10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -10 }}
                                        className="space-y-8"
                                    >
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <div className="space-y-1">
                                                <p className="blueprint-eyebrow text-xs">Заказчик</p>
                                                <p className="text-[var(--color-glacier)] font-bold leading-relaxed">{tender.customer_name}</p>
                                                <p className="text-xs text-[var(--color-frost-link)] font-medium">ИНН: {tender.customer_inn || 'не указан'}</p>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="blueprint-eyebrow text-xs">Место поставки</p>
                                                <div className="flex items-start gap-2 text-[var(--color-glacier)] font-bold">
                                                    <MapPin className="h-5 w-5 text-[var(--color-fog)] flex-shrink-0 mt-0.5" />
                                                    <span>{tender.customer_region || 'Вся Россия'}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="blueprint-panel overflow-hidden">
                                            <button
                                                onClick={() => setShowRequirements(!showRequirements)}
                                                className="w-full p-6 flex items-center justify-between hover:bg-[rgba(216,236,248,.04)] transition-colors"
                                            >
                                                <h3 className="font-bold text-[var(--color-glacier)] flex items-center gap-2">
                                                    <ShieldCheck className="h-5 w-5 text-[var(--color-cipher-mint)]" />
                                                    Преимущества и требования
                                                </h3>
                                                <ChevronRight className={clsx("h-5 w-5 text-[var(--color-fog)] transition-transform", showRequirements && "rotate-90")} />
                                            </button>

                                            <AnimatePresence>
                                                {showRequirements && (
                                                    <motion.div
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: 'auto', opacity: 1 }}
                                                        exit={{ height: 0, opacity: 0 }}
                                                        className="px-6 pb-6"
                                                    >
                                                        <div className="flex flex-wrap gap-2 mb-6">
                                                            {tender.preferences && tender.preferences.length > 0 ? (
                                                                tender.preferences.map((p, i) => (
                                                                    <span key={i} className="blueprint-status px-3 py-1.5 text-xs font-semibold">
                                                                        {p}
                                                                    </span>
                                                                ))
                                                            ) : (
                                                                <span className="text-[var(--color-fog)] text-sm">Требования не указаны</span>
                                                            )}
                                                            <span className={clsx(
                                                                "px-3 py-1.5 border rounded-[var(--radius-badges)] text-xs font-semibold",
                                                                tender.prepayment_type?.includes('Без') ? "border-[rgba(186,215,247,.14)] text-[var(--color-fog)]" : "border-[rgba(38,150,132,.35)] text-[var(--color-cipher-mint)]"
                                                            )}>
                                                                {tender.prepayment_type || 'Аванс не указан'}
                                                            </span>
                                                        </div>

                                                        {tender.description && (
                                                            <div className="space-y-2 pt-4 border-t border-[rgba(186,215,247,.12)]">
                                                                <p className="blueprint-eyebrow text-[10px]">Описание объекта закупки</p>
                                                                <p className="text-[var(--color-pebble)] leading-relaxed text-sm">{tender.description}</p>
                                                            </div>
                                                        )}
                                                    </motion.div>
                                                )}
                                            </AnimatePresence>
                                        </div>

                                        {/* Разведка по Заказчику */}
                                        {isIntLoading && (
                                            <div className="blueprint-section p-8 animate-pulse flex flex-col items-center justify-center min-h-[200px]">
                                                <Building2 className="h-8 w-8 text-[var(--color-frost-link)]/50 mb-4" />
                                                <p className="blueprint-eyebrow text-xs">Собираем досье на заказчика...</p>
                                            </div>
                                        )}

                                        {!isIntLoading && intelligence && (
                                            <div className="blueprint-section text-[var(--color-glacier)] relative overflow-hidden group">
                                                <button
                                                    onClick={() => setShowIntelligence(!showIntelligence)}
                                                    className="w-full p-6 md:p-8 flex items-center justify-between hover:bg-white/5 transition-colors relative z-10 text-left"
                                                >
                                                    <h4 className="blueprint-eyebrow text-xs flex items-center gap-2">
                                                        <Building2 className="h-4 w-4" />
                                                        Competitor Intelligence
                                                    </h4>
                                                    <ChevronRight className={clsx("h-5 w-5 text-[var(--color-fog)] transition-transform", showIntelligence && "rotate-90")} />
                                                </button>

                                                <AnimatePresence>
                                                    {showIntelligence && (
                                                        <motion.div
                                                            initial={{ height: 0, opacity: 0 }}
                                                            animate={{ height: 'auto', opacity: 1 }}
                                                            exit={{ height: 0, opacity: 0 }}
                                                            className="px-6 md:px-8 pb-8 relative z-10"
                                                        >
                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                                                <div className="space-y-6">
                                                                    <div className="flex flex-col gap-1">
                                                                        <div className="flex items-baseline gap-2">
                                                                            <span className="text-3xl md:text-4xl font-black">{intelligence.avg_price_reduction}</span>
                                                                            <span className="blueprint-eyebrow text-[10px]">ср. падение</span>
                                                                        </div>
                                                                        <div className="flex items-center gap-2 text-[10px] font-bold">
                                                                            <span className="text-[var(--color-fog)]">Уровень конкуренции:</span>
                                                                            <span className={clsx(
                                                                                "blueprint-status px-1.5 py-0.5",
                                                                                intelligence.competition_level === 'High' ? "text-[#ff9b83]" :
                                                                                    intelligence.competition_level === 'Medium' ? "text-[var(--color-ember)]" : "text-[var(--color-cipher-mint)]"
                                                                            )}>
                                                                                {intelligence.competition_level === 'High' ? 'Высокий' : intelligence.competition_level === 'Medium' ? 'Средний' : 'Низкий'}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                    <p className="text-sm text-[var(--color-pebble)] leading-relaxed italic">
                                                                        "{intelligence.recommendation}"
                                                                    </p>
                                                                </div>

                                                                <div className="blueprint-panel p-6">
                                                                    <p className="blueprint-eyebrow text-[10px] mb-4">Топ победителей</p>
                                                                    <div className="space-y-4">
                                                                        {intelligence.top_winners?.map((w: any, i: number) => (
                                                                            <div key={i} className="flex items-center justify-between">
                                                                                <div className="flex items-center gap-3">
                                                                                    <div className="blueprint-icon-tile h-6 w-6 text-[10px] font-black">
                                                                                        {i + 1}
                                                                                    </div>
                                                                                    <div className="flex flex-col">
                                                                                        <span className="text-xs font-bold line-clamp-1">{w.name}</span>
                                                                                        {w.avg_reduction && <span className="text-[9px] text-[var(--color-fog)]">Падение: {w.avg_reduction}</span>}
                                                                                    </div>
                                                                                </div>
                                                                                <span className="blueprint-status text-[10px] px-2 py-0.5 whitespace-nowrap">{w.count} побед</span>
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>

                                                <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:rotate-12 transition-transform pointer-events-none">
                                                    <Trophy className="h-24 w-24" />
                                                </div>
                                            </div>
                                        )}
                                    </motion.div>
                                )}

                                {activeTab === 'docs' && (
                                    <motion.div
                                        key="docs"
                                        initial={{ opacity: 0, x: 10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -10 }}
                                        className="space-y-4"
                                    >
                                        {!tender.documents_data || tender.documents_data.length === 0 ? (
                                            <div className="blueprint-panel py-12 text-center">
                                                <Download className="h-12 w-12 text-[var(--color-fog)] mx-auto mb-4" />
                                                <p className="text-[var(--color-pebble)]">Документация не загружена или отсутствует в общем доступе.</p>
                                                <p className="text-sm text-[var(--color-fog)] mt-2">Попробуйте перейти в ЕИС для ручного скачивания.</p>
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-1 gap-3">
                                                {tender.documents_data.map((doc: any, i: number) => (
                                                    <div key={i} className="blueprint-panel flex items-center justify-between p-4 transition-all group">
                                                        <div className="flex items-center gap-4">
                                                            <div className="blueprint-icon-tile h-12 w-12 group-hover:scale-105 transition-transform">
                                                                <FileText className="h-5 w-5" />
                                                            </div>
                                                            <div>
                                                                <p className="font-bold text-[var(--color-glacier)] group-hover:text-[var(--color-frost-link)] transition-colors">{doc.title || doc.fileName || 'Документ'}</p>
                                                                <p className="text-xs text-[var(--color-fog)]">{doc.pubDate || 'Дата не указана'}</p>
                                                            </div>
                                                        </div>
                                                        <a
                                                            href={doc.url || doc.href}
                                                            target="_blank"
                                                            className="blueprint-button-ghost p-3 text-[var(--color-fog)] hover:text-[var(--color-frost-link)] transition-all"
                                                        >
                                                            <Download className="h-5 w-5" />
                                                        </a>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </motion.div>
                                )}

                                {activeTab === 'analysis' && (
                                    <motion.div
                                        key="analysis"
                                        initial={{ opacity: 0, x: 10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -10 }}
                                        className="space-y-6"
                                    >
                                        {!tender.is_analyzed && !analyzeMutation.isPending && !deepAnalyzeMutation.isPending ? (
                                            <div className="blueprint-section py-12 text-center px-8">
                                                <div className="blueprint-icon-tile blueprint-pulse-glow h-20 w-20 inline-flex mb-6">
                                                    <Sparkles className="h-10 w-10" />
                                                </div>
                                                <h3 className="blueprint-heading text-xl mb-3">AI-Ассистент готов к работе</h3>
                                                <p className="text-[var(--color-pebble)] mb-8 max-w-sm mx-auto leading-relaxed text-sm">
                                                    Я могу провести краткий обзор или **глубокий аудит** документов на предмет скрытых рисков и закладок.
                                                </p>
                                                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                                                    <button
                                                        onClick={() => analyzeMutation.mutate()}
                                                        disabled={analyzeMutation.isPending || deepAnalyzeMutation.isPending}
                                                        className="blueprint-button-ghost px-6 py-3 font-bold active:scale-95 disabled:opacity-50 flex items-center gap-2"
                                                    >
                                                        <Sparkles className="h-4 w-4" /> Краткое резюме
                                                    </button>
                                                    <button
                                                        onClick={() => deepAnalyzeMutation.mutate()}
                                                        disabled={analyzeMutation.isPending || deepAnalyzeMutation.isPending}
                                                        className="blueprint-button-primary px-8 py-4 active:scale-95 disabled:opacity-50 flex items-center gap-3"
                                                    >
                                                        <ShieldCheck className="h-5 w-5" /> Профессиональный аудит
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="space-y-8">
                                                {/* Загрузка */}
                                                {(analyzeMutation.isPending || deepAnalyzeMutation.isPending) && (
                                                    <div className="blueprint-card py-20 text-center border-dashed relative overflow-hidden">
                                                        <motion.div
                                                            className="absolute inset-0 bg-gradient-to-r from-transparent via-[rgba(182,217,252,.08)] to-transparent -skew-x-12"
                                                            animate={{ x: ['-100%', '200%'] }}
                                                            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                                                        />
                                                        <div className="inline-block relative mb-4">
                                                            <div className="h-12 w-12 rounded-full border-4 border-[rgba(186,215,247,.12)] border-t-[var(--color-frost-link)] animate-spin"></div>
                                                            <div className="absolute inset-0 flex items-center justify-center">
                                                                <Sparkles className="h-4 w-4 text-[var(--color-frost-link)] animate-pulse" />
                                                            </div>
                                                        </div>
                                                        <p className="text-[var(--color-glacier)] font-bold relative z-10">
                                                            {deepAnalyzeMutation.isPending ? "Скачиваю и анализирую документацию..." : "Генерирую резюме..."}
                                                        </p>
                                                        <p className="text-sm text-[var(--color-fog)] mt-1 relative z-10">Это может занять до 30 секунд</p>
                                                    </div>
                                                )}

                                                {/* Результаты краткого анализа */}
                                                {(analyzeMutation.data || (tender.is_analyzed && !tender.deep_analysis_result)) && !deepAnalyzeMutation.isPending && (
                                                    <motion.div
                                                        initial={{ opacity: 0 }}
                                                        animate={{ opacity: 1 }}
                                                        className="blueprint-panel p-8 relative"
                                                    >
                                                        <div className="prose prose-blue max-w-none prose-sm md:prose-base">
                                                            <ReactMarkdown>{analyzeMutation.data?.summary || tender.description || "Резюме формируется..."}</ReactMarkdown>
                                                        </div>
                                                        <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
                                                            <div className="flex items-center gap-2">
                                                                <button
                                                                    onClick={() => analyzeMutation.mutate()}
                                                                    className="blueprint-eyebrow text-[10px] hover:text-[var(--color-frost-link)]"
                                                                >
                                                                    Обновить резюме
                                                                </button>
                                                            </div>
                                                            <button
                                                                onClick={() => deepAnalyzeMutation.mutate()}
                                                                className="blueprint-button-primary text-sm px-4 py-2 flex items-center gap-2"
                                                            >
                                                                <ShieldCheck className="h-4 w-4" /> Перейти к глубокому аудиту
                                                            </button>
                                                        </div>
                                                    </motion.div>
                                                )}

                                                {/* Результаты ГЛУБОКОГО анализа */}
                                                {(tender.deep_analysis_result || deepAnalyzeMutation.data) && (
                                                    <div className="space-y-8">
                                                        {/* Error handling if LLM failed to parse */}
                                                        {(tender.deep_analysis_result?.error || deepAnalyzeMutation.data?.error) && (
                                                            <div className="p-4 bg-amber-50 border border-amber-100 rounded-2xl flex items-start gap-3">
                                                                <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                                                                <div>
                                                                    <p className="text-sm font-bold text-amber-900">Неполный анализ</p>
                                                                    <p className="text-xs text-amber-700">{(tender.deep_analysis_result?.error || deepAnalyzeMutation.data?.error)}</p>
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Матрица Рисков */}
                                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                                            {Object.entries((tender.deep_analysis_result || deepAnalyzeMutation.data).risk_matrix || {}).map(([key, val]: [string, any]) => (
                                                                <div key={key} className="blueprint-panel p-6 transition-shadow">
                                                                    <p className="blueprint-eyebrow text-[10px] mb-1">
                                                                        {key === 'financial' ? 'Финансовый риск' : key === 'technical' ? 'Технический риск' : key === 'legal' ? 'Юридический риск' : key}
                                                                    </p>
                                                                    <div className="flex items-center gap-2 mb-2">
                                                                        <div className={clsx(
                                                                            "h-2 w-2 rounded-full",
                                                                            String(val).toLowerCase().includes('высокий') ? "bg-[var(--color-ember)] animate-pulse" :
                                                                                String(val).toLowerCase().includes('средний') ? "bg-[#d8a14d]" : "bg-[var(--color-cipher-mint)]"
                                                                        )} />
                                                                        <p className="font-black text-[var(--color-glacier)]">
                                                                            {String(val).split(' ')[0]}
                                                                        </p>
                                                                    </div>
                                                                    <p className="text-xs text-[var(--color-fog)] leading-relaxed">
                                                                        {String(val).split(' ').slice(1).join(' ')}
                                                                    </p>
                                                                </div>
                                                            ))}
                                                        </div>

                                                        {/* Чек-лист требований */}
                                                        <div className="blueprint-panel overflow-hidden">
                                                            <div className="px-6 py-4 border-b border-[rgba(186,215,247,.12)] flex items-center justify-between">
                                                                <h4 className="font-bold text-[var(--color-glacier)] flex items-center gap-2">
                                                                    <Target className="h-4 w-4 text-[var(--color-frost-link)]" />
                                                                    Compliance Checklist
                                                                </h4>
                                                                <span className="blueprint-status text-[10px] font-black px-2 py-1">
                                                                    AI Extracted
                                                                </span>
                                                            </div>
                                                            <div className="divide-y divide-[rgba(186,215,247,.12)] px-6">
                                                                {(tender.deep_analysis_result || deepAnalyzeMutation.data).checklist?.map((item: any, i: number) => (
                                                                    <div key={i} className="py-4 flex gap-4 items-start hover:bg-[rgba(216,236,248,.04)] transition-colors">
                                                                        <div className={clsx(
                                                                            "mt-1 p-1 rounded-[var(--radius-badges)] flex-shrink-0",
                                                                            item.critical ? "blueprint-danger" : "blueprint-success"
                                                                        )}>
                                                                            <ShieldCheck className="h-4 w-4" />
                                                                        </div>
                                                                        <div>
                                                                            <p className="font-bold text-[var(--color-glacier)] text-sm">{item.item}</p>
                                                                            <p className="text-xs text-[var(--color-fog)] mt-1">{item.description}</p>
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </div>

                                                        {/* Red Flags */}
                                                        {(tender.deep_analysis_result || deepAnalyzeMutation.data).red_flags?.length > 0 && (
                                                            <div className="blueprint-danger p-6">
                                                                <div className="flex items-center justify-between mb-4">
                                                                    <h4 className="font-black text-xs uppercase tracking-widest flex items-center gap-2">
                                                                        <AlertTriangle className="h-4 w-4" />
                                                                        Критические моменты (Red Flags)
                                                                    </h4>
                                                                    <span className="blueprint-status px-2 py-0.5 text-[9px] font-black text-[#ff9b83]">ВНИМАНИЕ</span>
                                                                </div>
                                                                <ul className="space-y-3">
                                                                    {(tender.deep_analysis_result || deepAnalyzeMutation.data).red_flags.map((flag: string, i: number) => (
                                                                        <li key={i} className="flex gap-3 text-sm font-medium">
                                                                            <span>•</span>
                                                                            {flag}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}

                                                        <div className="flex flex-wrap justify-center items-center gap-4 pt-4">
                                                            <button
                                                                onClick={async () => {
                                                                    try {
                                                                        const blob = await analysisApi.exportPdf(tender.id)
                                                                        const url = window.URL.createObjectURL(new Blob([blob]))
                                                                        const link = document.createElement('a')
                                                                        link.href = url
                                                                        link.setAttribute('download', `analysis_${tender.eis_id}.pdf`)
                                                                        document.body.appendChild(link)
                                                                        link.click()
                                                                        link.remove()
                                                                    } catch (err) {
                                                                        console.error('PDF Export error:', err)
                                                                        alert('Ошибка при экспорте в PDF')
                                                                    }
                                                                }}
                                                                className="blueprint-button-ghost px-6 py-2 flex items-center gap-2"
                                                            >
                                                                <BarChart3 className="h-4 w-4" /> Скачать в PDF
                                                            </button>

                                                            <button
                                                                onClick={() => {
                                                                    alert('Парсинг протоколов (Фаза 5): Этот функционал находится в разработке. Он позволит детально изучить причины прошлых побед и поражений конкурентов.')
                                                                }}
                                                                className="blueprint-button-primary px-6 py-2 flex items-center gap-2"
                                                            >
                                                                <Target className="h-4 w-4" /> Анализ протоколов конкурентов
                                                            </button>

                                                            <button
                                                                onClick={() => deepAnalyzeMutation.mutate()}
                                                                className="blueprint-eyebrow flex items-center gap-2 text-xs hover:text-[var(--color-frost-link)] transition-colors"
                                                            >
                                                                <Sparkles className="h-3 w-3" /> Перезапустить глубокий аудит
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )
                                        }
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                </div>

                {/* Правая колонка - Карточка цены и дат */}
                <div className="lg:col-span-4 space-y-8">
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="blueprint-section p-8 sticky top-24"
                    >
                        <div className="space-y-8">
                            {/* Цена */}
                            <div className="space-y-1">
                                <p className="blueprint-eyebrow text-xs">Начальная цена</p>
                                <div className="flex items-baseline gap-2">
                                    <span className="blueprint-heading text-4xl">
                                        {tender.initial_price?.toLocaleString('ru-RU') || '0'}
                                    </span>
                                    <span className="text-xl font-bold text-[var(--color-fog)]">{tender.currency || '₽'}</span>
                                </div>
                                {tender.guarantee_amount && (
                                    <p className="blueprint-status text-sm font-bold inline-block px-2 py-1 mt-2">
                                        Обеспечение заявки: {tender.guarantee_amount.toLocaleString('ru-RU')} ₽
                                    </p>
                                )}
                            </div>

                            {/* Таймер / Дедлайн */}
                            <div className={clsx(
                                "blueprint-panel p-6 flex items-center justify-between gap-4",
                                urgency === 'urgent' ? "text-[#ffb39f]" :
                                    urgency === 'coming' ? "text-[var(--color-ember)]" :
                                        "text-[var(--color-glacier)]"
                            )}>
                                <div>
                                    <p className="text-[10px] font-black uppercase tracking-widest mb-1">Срок подачи до</p>
                                    <p className="text-xl font-black">
                                        {tender.application_deadline ? format(new Date(tender.application_deadline), 'dd MMMM HH:mm', { locale: ru }) : 'Не указан'}
                                    </p>
                                </div>
                                <div className="blueprint-icon-tile h-12 w-12">
                                    <Clock className="h-6 w-6" />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center gap-4 text-sm">
                                    <div className="blueprint-icon-tile h-10 w-10">
                                        <Calendar className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <p className="blueprint-eyebrow text-[10px]">Опубликовано</p>
                                        <p className="text-[var(--color-glacier)] font-bold">{tender.publication_date || 'неизвестно'}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 text-sm">
                                    <div className="blueprint-icon-tile h-10 w-10">
                                        <Building2 className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <p className="blueprint-eyebrow text-[10px]">Площадка</p>
                                        <p className="text-[var(--color-glacier)] font-bold">{tender.platform || 'ЕИС Поиск'}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4 text-sm">
                                    <div className="blueprint-icon-tile h-10 w-10">
                                        <DollarSign className="h-5 w-5" />
                                    </div>
                                    <div>
                                        <p className="blueprint-eyebrow text-[10px]">Обеспечение контракта</p>
                                        <p className="text-[var(--color-glacier)] font-bold">{tender.contract_guarantee ? `${tender.contract_guarantee.toLocaleString('ru-RU')} ₽` : 'Не требуется'}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="pt-4 space-y-3">
                                {tender.is_favorite ? (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between">
                                            <p className="blueprint-eyebrow text-[10px]">Статус в CRM</p>
                                            <button
                                                onClick={() => toggleFavoriteMutation.mutate()}
                                                className="text-[10px] font-bold text-[#ff9b83] hover:text-[var(--color-glacier)] transition-colors uppercase tracking-widest"
                                            >
                                                Удалить
                                            </button>
                                        </div>
                                        <div className="grid grid-cols-1 gap-2">
                                            {CRM_STATUSES.map((status) => (
                                                <button
                                                    key={status.value}
                                                    onClick={() => updateStatusMutation.mutate(status.value)}
                                                    disabled={updateStatusMutation.isPending}
                                                    className={clsx(
                                                        "flex items-center gap-3 px-4 py-3 rounded-[var(--radius-md)] border transition-all font-bold text-sm",
                                                        tender.crm_status === status.value
                                                            ? "bg-[rgba(102,58,243,.16)] border-[rgba(216,236,248,.32)] text-[var(--color-glacier)] shadow-[var(--shadow-sm)]"
                                                            : "bg-[rgba(199,211,234,.04)] border-[rgba(186,215,247,.12)] text-[var(--color-fog)] hover:border-[rgba(216,236,248,.28)] hover:text-[var(--color-glacier)]"
                                                    )}
                                                >
                                                    <status.icon className={clsx("h-4 w-4", tender.crm_status === status.value ? "text-[var(--color-frost-link)]" : "text-[var(--color-fog)]")} />
                                                    {status.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <button
                                        onClick={() => toggleFavoriteMutation.mutate()}
                                        disabled={toggleFavoriteMutation.isPending}
                                        className="blueprint-button-primary w-full py-4 active:scale-95 flex items-center justify-center gap-2"
                                    >
                                        <Heart className="h-5 w-5" />
                                        В избранное
                                    </button>
                                )}

                                <button
                                    onClick={() => setActiveTab('analysis')}
                                    className="blueprint-button-ghost w-full py-4 font-black transition-all active:scale-95 flex items-center justify-center gap-2"
                                >
                                    <Sparkles className="h-5 w-5" />
                                    AI-Анализ ТЗ
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </div>
        </div>
        </div>
    )
}

function SearchIcon({ className }: { className?: string }) {
    return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
    )
}
