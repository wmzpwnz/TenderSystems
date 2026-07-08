import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight,
  BarChart3,
  Bell,
  CheckCircle2,
  ChevronRight,
  Database,
  FileSearch,
  Heart,
  LockKeyhole,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  Zap,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import Aurora from '../components/ui/Aurora'
import Particles from '../components/ui/Particles'
import DecryptedText from '../components/ui/DecryptedText'

type AnimatedContentProps = {
  children: ReactNode
  className?: string
  delay?: number
}

function AnimatedContent({ children, className, delay = 0 }: AnimatedContentProps) {
  const shouldReduceMotion = useReducedMotion()

  return (
    <motion.div
      initial={shouldReduceMotion ? false : { opacity: 0, y: 24 }}
      whileInView={shouldReduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

function BlurText({ text }: { text: string }) {
  const shouldReduceMotion = useReducedMotion()
  const words = text.split(' ')

  if (shouldReduceMotion) {
    return <>{text}</>
  }

  return (
    <>
      {words.map((word, index) => (
        <motion.span
          key={`${word}-${index}`}
          initial={{ opacity: 0, filter: 'blur(12px)', y: 14 }}
          animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
          transition={{ duration: 0.55, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
          className="landing-blur-word"
        >
          {word}
          {index < words.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </>
  )
}

function CountUp({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0)
  const ref = useRef<HTMLSpanElement | null>(null)
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (shouldReduceMotion) {
      setCount(value)
      return
    }

    const node = ref.current
    if (!node) return

    let frame = 0
    let started = false
    const duration = 1100

    const animate = (startTime: number) => {
      const tick = (time: number) => {
        const progress = Math.min((time - startTime) / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setCount(Math.round(value * eased))

        if (progress < 1) {
          frame = requestAnimationFrame(tick)
        }
      }

      frame = requestAnimationFrame(tick)
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || started) return
        started = true
        animate(performance.now())
        observer.disconnect()
      },
      { threshold: 0.35 }
    )

    observer.observe(node)

    return () => {
      observer.disconnect()
      cancelAnimationFrame(frame)
    }
  }, [shouldReduceMotion, value])

  return (
    <span ref={ref}>
      {count.toLocaleString('ru-RU')}
      {suffix}
    </span>
  )
}

type SpotlightCardProps = {
  children: ReactNode
  className?: string
}

function SpotlightCard({ children, className = '' }: SpotlightCardProps) {
  const [spotlight, setSpotlight] = useState({ x: 50, y: 0 })

  return (
    <div
      className={`landing-spotlight-card ${className}`}
      style={
        {
          '--landing-spotlight-x': `${spotlight.x}%`,
          '--landing-spotlight-y': `${spotlight.y}%`,
        } as CSSProperties
      }
      onMouseMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect()
        setSpotlight({
          x: ((event.clientX - rect.left) / rect.width) * 100,
          y: ((event.clientY - rect.top) / rect.height) * 100,
        })
      }}
    >
      {children}
    </div>
  )
}

const stats = [
  { label: 'ФЗ в поиске', value: 2, suffix: '' },
  { label: 'Live-поиск ЕИС', value: 100, suffix: '%' },
  { label: 'Сценариев анализа', value: 6, suffix: '+' },
]

const features = [
  {
    title: 'Live-поиск закупок',
    description: 'Фильтры по 44-ФЗ и 223-ФЗ, регионам, цене, заказчику, площадке, срокам и процедурам.',
    icon: Search,
  },
  {
    title: 'AI-анализ документации',
    description: 'Быстрый разбор условий, рисков, финансовых параметров и требований к участнику.',
    icon: Sparkles,
  },
  {
    title: 'CRM-контур',
    description: 'Избранные тендеры, просмотренные закупки и подписки на новые подходящие лоты.',
    icon: Heart,
  },
  {
    title: 'Оповещения',
    description: 'Telegram-уведомления по сохраненным поискам и важным изменениям в рабочем пайплайне.',
    icon: Bell,
  },
]

const faq = [
  {
    question: 'Это публичный каталог тендеров?',
    answer: 'Нет. Лэндинг публичный, но поиск, анализ, избранное и подписки доступны после входа и активной подписки.',
  },
  {
    question: 'AI-оценка заменяет проверку специалистом?',
    answer: 'Нет. AI помогает быстро найти риски и ориентиры, но все оценки требуют проверки перед решением об участии.',
  },
  {
    question: 'Какие источники используются?',
    answer: 'Платформа работает с закупками ЕИС по 44-ФЗ и 223-ФЗ и обрабатывает документацию тендера внутри рабочего контура.',
  },
]

export default function Landing() {
  const { user, isLoading } = useAuth()
  const dashboardHref = user ? '/dashboard' : '/login'
  const primaryHref = user ? '/dashboard' : '/register'
  const primaryLabel = user ? 'Открыть дашборд' : 'Начать работу'

  return (
    <div className="blueprint-page landing-page">
      <header className="landing-header">
        <div className="landing-container landing-nav">
          <Link to="/" className="landing-brand">
            <span className="landing-brand-mark">
              <Sparkles className="h-5 w-5" />
            </span>
            <span>TenderSystems</span>
          </Link>

          <nav className="landing-nav-links" aria-label="Навигация лэндинга">
            <a href="#workflow">Сценарий</a>
            <a href="#methodology">Методология</a>
            <a href="#pricing">Тариф</a>
          </nav>

          <div className="landing-nav-actions">
            <Link to={dashboardHref} className="blueprint-button-ghost px-4 py-2">
              {user ? 'Дашборд' : 'Войти'}
            </Link>
            <Link to={primaryHref} className="blueprint-button-primary px-4 py-2">
              {isLoading ? 'Загрузка' : primaryLabel}
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-[rgba(186,215,247,0.06)]">
          {/* Background effects */}
          <div className="absolute inset-0 z-0 pointer-events-none opacity-50">
            <Aurora colorStops={['#05060f', '#0f2042', '#05060f']} speed={0.4} />
          </div>
          <div className="absolute inset-0 z-0 pointer-events-none opacity-30">
            <Particles particleCount={60} particleColors={['#d8ecf8', '#81899b', '#9fa7ba']} speed={0.3} particleBaseSize={120} />
          </div>

          <div className="landing-hero landing-container relative z-10">
            <AnimatedContent className="landing-hero-copy">
              <div className="blueprint-eyebrow landing-eyebrow">procurement intelligence</div>
              <h1 className="landing-title text-3xl md:text-5xl font-black tracking-tight leading-tight text-[var(--color-glacier)]">
                <DecryptedText
                  text="Тендерная документация на 40+ страниц."
                  animateOn="view"
                  revealDirection="start"
                  speed={25}
                  sequential={true}
                />
                <br />
                <span className="text-[var(--color-ember-bright)]">Вручную — 2-3 часа на анализ.</span>
                <br />
                <span className="text-[var(--color-cipher-mint)]">С AI — меньше двух минут.</span>
              </h1>
              <p className="landing-lead mt-6 text-[var(--color-moonlight)] text-base md:text-lg max-w-xl">
                TenderSystems автоматически сканирует файлы ЕИС, выявляет требования к опыту, 
                извлекает сметную структуру и подсвечивает скрытые риски выполнения до подачи заявки.
              </p>
              <div className="landing-hero-actions mt-8">
                <Link to={primaryHref} className="blueprint-button-primary landing-hero-cta">
                  {primaryLabel}
                  <ArrowRight className="h-5 w-5" />
                </Link>
                <a href="#workflow" className="blueprint-button-ghost landing-hero-cta">
                  Посмотреть сценарий
                  <ChevronRight className="h-5 w-5" />
                </a>
              </div>
            </AnimatedContent>

            <AnimatedContent className="landing-command-panel p-6 bg-[rgba(5,6,15,0.4)] border border-[rgba(186,215,247,0.12)] rounded-2xl relative z-10 backdrop-blur-md" delay={0.12}>
              <div className="flex items-center justify-between mb-4 border-b border-[rgba(186,215,247,0.1)] pb-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[var(--color-ember-bright)]" />
                  <span className="text-[11px] font-mono tracking-widest text-[var(--color-fog)] uppercase">AI Analysis Report</span>
                </div>
                <span className="bg-[rgba(102,58,243,0.15)] text-[var(--color-electric-iris)] text-[10px] font-mono px-2 py-0.5 rounded border border-[rgba(102,58,243,0.3)]">for_construction</span>
              </div>

              <div className="space-y-4">
                <div>
                  <span className="text-[10px] text-[var(--color-fog)] uppercase tracking-wider block">Объект закупки</span>
                  <h3 className="text-sm font-semibold text-[var(--color-glacier)] leading-snug">Строительство детского сада на 240 мест</h3>
                </div>

                <div className="grid grid-cols-2 gap-4 bg-[rgba(199,211,234,0.03)] p-3 border border-[rgba(186,215,247,0.06)] rounded-md">
                  <div>
                    <span className="text-[9px] text-[var(--color-fog)] block">Начальная цена</span>
                    <span className="text-xs font-bold text-[var(--color-cipher-mint)]">185 000 000 ₽</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-[var(--color-fog)] block">Заказчик</span>
                    <span className="text-xs font-bold text-[var(--color-moonlight)] truncate block">ГКУ УКС Администрации</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] text-[var(--color-fog)] uppercase tracking-wider block">Ключевые требования</span>
                  <div className="space-y-1.5 text-xs text-[var(--color-moonlight)]">
                    <div className="flex items-center justify-between">
                      <span>Опыт работ (Пост. №2571)</span>
                      <span className="text-[var(--color-cipher-mint)] font-bold">Обязательно</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Обеспечение контракта</span>
                      <span>9.25M ₽</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Срок выполнения</span>
                      <span>360 дней</span>
                    </div>
                  </div>
                </div>

                <div className="p-3 bg-[rgba(228,109,76,0.11)] border border-[rgba(228,109,76,0.32)] rounded-md flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-[var(--color-ember-bright)] mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-[10px] font-bold text-[var(--color-ember-bright)] block">⚠️ Флаг риска</span>
                    <span className="text-[11px] text-[var(--color-moonlight)] leading-normal block">Сроки сокращены на 20% относительно нормативов Минстроя.</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] text-[var(--color-fog)] uppercase tracking-wider block">Смета по видам работ (AI-оценка)</span>
                  <div className="border border-[rgba(186,215,247,0.08)] rounded-md overflow-hidden text-[11px]">
                    <div className="grid grid-cols-3 bg-[rgba(199,211,234,0.06)] p-2 font-mono text-[var(--color-fog)] border-b border-[rgba(186,215,247,0.08)]">
                      <span>Работа</span>
                      <span className="text-right">Объем</span>
                      <span className="text-right">Оценка м²</span>
                    </div>
                    <div className="p-2 space-y-1.5 font-mono text-[var(--color-moonlight)]">
                      <div className="grid grid-cols-3">
                        <span>Земляные работы</span>
                        <span className="text-right text-[var(--color-fog)]">4 500 м³</span>
                        <span className="text-right font-bold text-[var(--color-glacier)]">1 200 ₽</span>
                      </div>
                      <div className="grid grid-cols-3">
                        <span>Монолит каркас</span>
                        <span className="text-right text-[var(--color-fog)]">3 800 м³</span>
                        <span className="text-right font-bold text-[var(--color-glacier)]">9 500 ₽</span>
                      </div>
                      <div className="grid grid-cols-3">
                        <span>Отделка</span>
                        <span className="text-right text-[var(--color-fog)]">12 000 м²</span>
                        <span className="text-right font-bold text-[var(--color-glacier)]">3 200 ₽</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </AnimatedContent>
          </div>
        </section>

        {/* Сценарий по шагам решения */}
        <section id="workflow" className="landing-section landing-container">
          <AnimatedContent className="landing-section-heading">
            <div className="blueprint-eyebrow landing-eyebrow">what you get</div>
            <h2>Процесс отбора тендеров без рутины</h2>
            <p>Платформа автоматизирует ключевые шаги квалификации закупки и структурирует информацию.</p>
          </AnimatedContent>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <AnimatedContent delay={0.05}>
              <SpotlightCard className="landing-feature-card h-full flex flex-col justify-between p-6">
                <div>
                  <Search className="h-6 w-6 text-[var(--color-frost-link)] mb-4" />
                  <h3 className="text-lg font-semibold text-[var(--color-glacier)] mb-2">1. Умный поиск</h3>
                  <p className="text-sm text-[var(--color-pebble)] mb-4">Настраивайте регионы, сроки и лимиты бюджетов под профиль компании.</p>
                </div>
                <div className="mt-auto p-3 bg-[rgba(199,211,234,0.03)] border border-[rgba(186,215,247,0.06)] rounded-md space-y-1.5 text-[11px] font-mono text-[var(--color-moonlight)]">
                  <div className="flex items-center gap-1.5 text-[var(--color-azure)] font-bold">● Металлоконструкции</div>
                  <div className="flex items-center gap-1.5">● Москва и МО</div>
                  <div className="flex items-center gap-1.5">● от 10 000 000 ₽</div>
                </div>
              </SpotlightCard>
            </AnimatedContent>

            <AnimatedContent delay={0.1}>
              <SpotlightCard className="landing-feature-card h-full flex flex-col justify-between p-6">
                <div>
                  <Target className="h-6 w-6 text-[var(--color-frost-link)] mb-4" />
                  <h3 className="text-lg font-semibold text-[var(--color-glacier)] mb-2">2. Экспресс-отбор</h3>
                  <p className="text-sm text-[var(--color-pebble)] mb-4">Сортируйте лоты по дедлайну подачи и признакам авансирования.</p>
                </div>
                <div className="mt-auto space-y-2">
                  <div className="flex items-center justify-between p-2 bg-[rgba(228,109,76,0.1)] border border-[rgba(228,109,76,0.25)] rounded text-[11px]">
                    <span className="text-[var(--color-ember-bright)] font-bold">⚠️ Горит!</span>
                    <span className="text-[var(--color-fog)]">Дедлайн: 24 часа</span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-[rgba(0,102,204,0.1)] border border-[rgba(0,102,204,0.25)] rounded text-[11px]">
                    <span className="text-[var(--color-azure)] font-bold">С авансом</span>
                    <span className="text-[var(--color-fog)]">44-ФЗ</span>
                  </div>
                </div>
              </SpotlightCard>
            </AnimatedContent>

            <AnimatedContent delay={0.15}>
              <SpotlightCard className="landing-feature-card h-full flex flex-col justify-between p-6">
                <div>
                  <BarChart3 className="h-6 w-6 text-[var(--color-frost-link)] mb-4" />
                  <h3 className="text-lg font-semibold text-[var(--color-glacier)] mb-2">3. AI-анализ</h3>
                  <p className="text-sm text-[var(--color-pebble)] mb-4">Автоматически извлекайте объемы, себестоимость и материалы.</p>
                </div>
                <div className="mt-auto border border-[rgba(186,215,247,0.08)] rounded overflow-hidden text-[10px] font-mono text-[var(--color-moonlight)]">
                  <div className="bg-[rgba(199,211,234,0.06)] p-1.5 text-[9px] text-[var(--color-fog)] border-b border-[rgba(186,215,247,0.08)] grid grid-cols-2">
                    <span>Работа (Объем)</span>
                    <span className="text-right">Себест.</span>
                  </div>
                  <div className="p-1.5 space-y-1">
                    <div className="grid grid-cols-2">
                      <span>Бетон B25 (550 м³)</span>
                      <span className="text-right font-bold text-[var(--color-cipher-mint)]">4.8M ₽</span>
                    </div>
                    <div className="grid grid-cols-2">
                      <span>Фасад (1200 м²)</span>
                      <span className="text-right font-bold text-[var(--color-cipher-mint)]">3.1M ₽</span>
                    </div>
                  </div>
                </div>
              </SpotlightCard>
            </AnimatedContent>

            <AnimatedContent delay={0.20}>
              <SpotlightCard className="landing-feature-card h-full flex flex-col justify-between p-6">
                <div>
                  <CheckCircle2 className="h-6 w-6 text-[var(--color-frost-link)] mb-4" />
                  <h3 className="text-lg font-semibold text-[var(--color-glacier)] mb-2">4. CRM-контроль</h3>
                  <p className="text-sm text-[var(--color-pebble)] mb-4">Отслеживайте статус участия в воронке, ведите заметки команды.</p>
                </div>
                <div className="mt-auto flex items-center justify-between p-2.5 bg-[rgba(199,211,234,0.03)] border border-[rgba(186,215,247,0.06)] rounded-md text-[10px] font-bold">
                  <span className="px-1.5 py-0.5 bg-[rgba(199,211,234,0.06)] text-[var(--color-fog)] rounded">В работе</span>
                  <span className="text-[var(--color-fog)]">➔</span>
                  <span className="px-1.5 py-0.5 bg-[rgba(102,58,243,0.15)] text-[var(--color-electric-iris)] rounded">Подана</span>
                  <span className="text-[var(--color-fog)]">➔</span>
                  <span className="px-1.5 py-0.5 bg-[rgba(124,255,103,0.15)] text-[var(--color-cipher-mint)] rounded">Победа! 🎉</span>
                </div>
              </SpotlightCard>
            </AnimatedContent>
          </div>
        </section>

        {/* Сравнение производительности по времени */}
        <section className="landing-section landing-container border-t border-[rgba(186,215,247,0.06)] pt-16">
          <div className="bg-[rgba(199,211,234,0.02)] border border-[rgba(186,215,247,0.08)] rounded-2xl p-8 md:p-12 text-center relative overflow-hidden">
            <div className="absolute inset-0 pointer-events-none opacity-10 bg-[radial-gradient(circle_at_center,var(--color-electric-iris)_0%,transparent_70%)]" />
            <span className="blueprint-eyebrow text-xs tracking-widest text-[var(--color-electric-iris)] block mb-4 uppercase">Сравнение производительности</span>
            <h2 className="text-2xl md:text-4xl font-black text-[var(--color-glacier)] leading-tight mb-8">
              40 страниц документации за 90 секунд
            </h2>
            <div className="flex flex-col md:flex-row items-center justify-center gap-8 md:gap-16">
              <div className="flex-1 max-w-[280px]">
                <span className="text-4xl font-extrabold text-[var(--color-ember-bright)] block mb-2">2-3 часа</span>
                <span className="text-sm text-[var(--color-fog)]">Вручную: чтение ТЗ, выписывание сметы, поиск скрытых рисков</span>
              </div>
              <div className="text-3xl text-[var(--color-fog)] font-bold rotate-90 md:rotate-0">➔</div>
              <div className="flex-1 max-w-[280px]">
                <span className="text-4xl font-extrabold text-[var(--color-cipher-mint)] block mb-2">
                  <CountUp value={90} suffix=" секунд" />
                </span>
                <span className="text-sm text-[var(--color-fog)]">С AI-платформой: готовый структурированный отчет и оценка маржинальности</span>
              </div>
            </div>
          </div>
        </section>

        {/* Как мы считаем (Методология) */}
        <section id="methodology" className="landing-section landing-container border-t border-[rgba(186,215,247,0.06)] pt-16">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <div className="blueprint-eyebrow landing-eyebrow">методология и источники</div>
              <h2 className="text-2xl md:text-3xl font-black text-[var(--color-glacier)] leading-tight mb-4">
                Мы не верим в «черные ящики»
              </h2>
              <p className="text-[var(--color-moonlight)] leading-relaxed mb-6">
                Каждый отчет платформы строится на анализе исходных документов конкретного тендера. 
                Алгоритм сканирует файлы из ЕИС, сопоставляет информацию со справочниками и выдает результат с точными ссылками на пункты документации.
              </p>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded-full bg-[rgba(152,192,239,0.15)] flex items-center justify-center text-[var(--color-frost-link)] font-bold text-xs mt-0.5">1</div>
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--color-glacier)]">Полный разбор файлов</h4>
                    <p className="text-xs text-[var(--color-fog)] mt-1">Чтение технического задания, проектов контрактов и чертежей.</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded-full bg-[rgba(152,192,239,0.15)] flex items-center justify-center text-[var(--color-frost-link)] font-bold text-xs mt-0.5">2</div>
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--color-glacier)]">AI-оценка маржинальности</h4>
                    <p className="text-xs text-[var(--color-fog)] mt-1">Ориентировочный расчет стоимости работ (₽/м²) для первоначального отбора.</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-5 h-5 rounded-full bg-[rgba(216,161,77,0.15)] flex items-center justify-center text-[var(--color-premium-gold)] font-bold text-xs mt-0.5">3</div>
                  <div>
                    <h4 className="text-sm font-semibold text-[var(--color-glacier)]">Проверка человеком</h4>
                    <p className="text-xs text-[var(--color-fog)] mt-1">⚠️ Все расчеты являются рекомендательной AI-оценкой и требуют проверки перед решением об участии.</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="relative">
              <SpotlightCard className="p-6 bg-[rgba(5,6,15,0.28)] border border-[rgba(186,215,247,0.08)] rounded-xl relative overflow-hidden font-mono text-xs text-[var(--color-moonlight)] space-y-4">
                <div className="flex items-center justify-between border-b border-[rgba(186,215,247,0.1)] pb-2 text-[var(--color-fog)]">
                  <span>TenderSystems Engine</span>
                  <span className="text-[var(--color-cipher-mint)]">ONLINE</span>
                </div>
                <div className="space-y-2">
                  <div>
                    <span className="text-[var(--color-fog)]">&gt;_ scanning_source_files</span>
                    <p className="text-[var(--color-glacier)] mt-0.5">ТЗ_капремонт_школа.pdf: parsed 142 paragraphs</p>
                  </div>
                  <div>
                    <span className="text-[var(--color-fog)]">&gt;_ extracting_requirements</span>
                    <p className="text-[var(--color-glacier)] mt-0.5">Found: 30% prepayment (44-FZ Clause 4.2)</p>
                  </div>
                  <div>
                    <span className="text-[var(--color-fog)]">&gt;_ matching_commercial_rates</span>
                    <p className="text-[var(--color-glacier)] mt-0.5">Concrete works matching database avg: 8,400 ₽/m³</p>
                  </div>
                </div>
                <div className="p-2.5 bg-[rgba(216,161,77,0.08)] border border-[rgba(216,161,77,0.24)] rounded text-[10px] leading-relaxed text-[var(--color-premium-gold)]">
                  ℹ️ AI-оценка, требует проверки. База данных обновлена: 2026-07-08.
                </div>
              </SpotlightCard>
            </div>
          </div>
        </section>

        {/* Тариф */}
        <section id="pricing" className="landing-section landing-container border-t border-[rgba(186,215,247,0.06)] pt-16">
          <AnimatedContent className="max-w-xl mx-auto text-center">
            <div className="blueprint-eyebrow landing-eyebrow uppercase tracking-widest text-[var(--color-electric-iris)]">subscription</div>
            <h2 className="text-2xl md:text-3xl font-black text-[var(--color-glacier)] mb-4">Простой и прозрачный тариф</h2>
            <p className="text-[var(--color-pebble)] text-sm md:text-base mb-8">Все функции платформы доступны без скрытых лимитов в рамках единого плана для команд закупок.</p>
          </AnimatedContent>

          <AnimatedContent className="max-w-md mx-auto" delay={0.1}>
            <SpotlightCard className="p-8 bg-[rgba(5,6,15,0.4)] border border-[rgba(186,215,247,0.12)] rounded-2xl text-center relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-[rgba(102,58,243,0.15)] text-[var(--color-electric-iris)] text-[10px] font-bold px-3 py-1 rounded-bl-lg uppercase tracking-wider border-l border-b border-[rgba(102,58,243,0.3)]">
                Pro
              </div>
              <h3 className="text-xl font-bold text-[var(--color-glacier)] mb-2">Единый доступ</h3>
              <div className="my-6">
                <span className="text-4xl font-black text-[var(--color-cipher-mint)] tracking-tight">1 990 ₽</span>
                <span className="text-[var(--color-fog)]"> / месяц</span>
              </div>
              <ul className="text-left space-y-3.5 my-8 text-xs text-[var(--color-moonlight)] border-t border-b border-[rgba(186,215,247,0.08)] py-6">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[var(--color-cipher-mint)] flex-shrink-0" />
                  <span>Безлимитный live-поиск по всем регионам РФ</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[var(--color-cipher-mint)] flex-shrink-0" />
                  <span>AI-анализ любых тендерных документов (до 50/мес)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[var(--color-cipher-mint)] flex-shrink-0" />
                  <span>CRM-контур (избранное, воронка тендеров, заметки)</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[var(--color-cipher-mint)] flex-shrink-0" />
                  <span>Уведомления о новых закупках в Telegram</span>
                </li>
              </ul>
              <Link to={primaryHref} className="blueprint-button-primary w-full py-3 flex items-center justify-center gap-2 font-bold">
                {primaryLabel}
                <Zap className="h-4 w-4" />
              </Link>
            </SpotlightCard>
          </AnimatedContent>
        </section>

        {/* FAQ */}
        <section className="landing-section landing-container border-t border-[rgba(186,215,247,0.06)] pt-16">
          <AnimatedContent className="landing-section-heading">
            <div className="blueprint-eyebrow landing-eyebrow">faq</div>
            <h2>Частые вопросы</h2>
          </AnimatedContent>
          <div className="landing-faq-list">
            {faq.map((item, index) => (
              <AnimatedContent key={item.question} delay={index * 0.05}>
                <SpotlightCard className="landing-faq-item">
                  <h3>{item.question}</h3>
                  <p>{item.answer}</p>
                </SpotlightCard>
              </AnimatedContent>
            ))}
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-inner">
          <span>TenderSystems</span>
          <span>AI-анализ госзакупок 44-ФЗ и 223-ФЗ</span>
        </div>
      </footer>
    </div>
  )
}
