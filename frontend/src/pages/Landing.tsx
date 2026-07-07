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

const workflow = [
  { title: 'Поиск', text: 'Настройте фильтры под нишу, регион, бюджет и сроки.', icon: FileSearch },
  { title: 'Отбор', text: 'Сравните карточки, дедлайны, цену и признаки срочности.', icon: Target },
  { title: 'AI-анализ', text: 'Получите структурированную оценку рисков и условий.', icon: BarChart3 },
  { title: 'Контроль', text: 'Сохраните тендер, подпишитесь и вернитесь к нему в CRM.', icon: CheckCircle2 },
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
            <a href="#features">Возможности</a>
            <a href="#workflow">Сценарий</a>
            <a href="#ai">AI-анализ</a>
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
              <h1 className="landing-title">
                <DecryptedText
                  text="AI-платформа для поиска и анализа госзакупок"
                  animateOn="view"
                  revealDirection="start"
                  speed={35}
                  sequential={true}
                  useOriginalCharsOnly={false}
                />
              </h1>
              <p className="landing-lead">
                TenderSystems помогает находить релевантные тендеры, быстро разбирать документацию,
                контролировать риски и вести рабочий пайплайн закупок в одном интерфейсе.
              </p>
              <div className="landing-hero-actions">
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

          <AnimatedContent className="landing-command-panel" delay={0.12}>
            <div className="landing-panel-topline">
              <span>live search</span>
              <span>44-ФЗ / 223-ФЗ</span>
            </div>
            <div className="landing-search-row">
              <Search className="h-5 w-5" />
              <span>строительно-монтажные работы</span>
              <b>ЕИС</b>
            </div>
            <div className="landing-filter-grid">
              <span>Регион: Москва</span>
              <span>Цена: от 5M ₽</span>
              <span>Дедлайн: до 7 дней</span>
              <span>Тип: конкурс</span>
            </div>
            <SpotlightCard className="landing-tender-preview">
              <div>
                <div className="landing-card-kicker">Закупка найдена</div>
                <h2>Капитальный ремонт объекта инфраструктуры</h2>
                <p>AI выделил требования, сроки, обеспечение и потенциальные риски участия.</p>
              </div>
              <div className="landing-risk-note">AI-оценка, требует проверки</div>
            </SpotlightCard>
          </AnimatedContent>
        </div>
      </section>

        <section className="landing-container landing-stats" aria-label="Ключевые показатели">
          {stats.map((stat) => (
            <AnimatedContent key={stat.label}>
              <SpotlightCard className="landing-stat-card">
                <strong>
                  <CountUp value={stat.value} suffix={stat.suffix} />
                </strong>
                <span>{stat.label}</span>
              </SpotlightCard>
            </AnimatedContent>
          ))}
        </section>

        <section id="features" className="landing-section landing-container">
          <AnimatedContent className="landing-section-heading">
            <div className="blueprint-eyebrow landing-eyebrow">platform pages</div>
            <h2>Все ключевые рабочие страницы проекта в одном продукте</h2>
            <p>Лэндинг объясняет путь от первого поиска до контроля выбранных закупок в CRM-контуре.</p>
          </AnimatedContent>

          <div className="landing-feature-grid">
            {features.map((feature, index) => (
              <AnimatedContent key={feature.title} delay={index * 0.05}>
                <SpotlightCard className="landing-feature-card">
                  <feature.icon className="h-6 w-6 landing-feature-icon" />
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </SpotlightCard>
              </AnimatedContent>
            ))}
          </div>
        </section>

        <section id="workflow" className="landing-section landing-container">
          <AnimatedContent className="landing-section-heading">
            <div className="blueprint-eyebrow landing-eyebrow">workflow</div>
            <h2>Сценарий работы без лишних переходов</h2>
            <p>Поиск, карточка тендера, анализ, избранное и подписки связаны в один понятный поток.</p>
          </AnimatedContent>

          <div className="landing-workflow">
            {workflow.map((step, index) => (
              <AnimatedContent key={step.title} delay={index * 0.06}>
                <div className="landing-workflow-step">
                  <div className="landing-step-index">{String(index + 1).padStart(2, '0')}</div>
                  <step.icon className="h-6 w-6" />
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              </AnimatedContent>
            ))}
          </div>
        </section>

        <section id="ai" className="landing-section landing-container landing-ai-section">
          <AnimatedContent>
            <div className="landing-ai-copy">
              <div className="blueprint-eyebrow landing-eyebrow">ai analysis</div>
              <h2>AI помогает быстрее понять, стоит ли идти в закупку</h2>
              <p>
                Анализ собирает требования, финансовые ориентиры, риски, вероятные ограничения и
                практические заметки по документации. Все расчетные выводы показываются как проверяемая оценка.
              </p>
              <div className="landing-risk-note landing-risk-note-wide">AI-оценка, требует проверки</div>
            </div>
          </AnimatedContent>

          <AnimatedContent delay={0.12}>
            <SpotlightCard className="landing-analysis-card">
              <div className="landing-analysis-row">
                <span>Риск сроков</span>
                <b>Средний</b>
              </div>
              <div className="landing-analysis-row">
                <span>Обеспечение</span>
                <b>Проверить</b>
              </div>
              <div className="landing-analysis-row">
                <span>Маржинальность</span>
                <b>AI-оценка</b>
              </div>
              <div className="landing-analysis-meter">
                <span />
              </div>
            </SpotlightCard>
          </AnimatedContent>
        </section>

        <section className="landing-section landing-container">
          <div className="landing-trust-grid">
            <AnimatedContent>
              <SpotlightCard className="landing-trust-card">
                <ShieldCheck className="h-7 w-7 landing-feature-icon" />
                <h3>Безопасный рабочий контур</h3>
                <p>Авторизация, подписка и профиль компании отделены от публичной страницы.</p>
              </SpotlightCard>
            </AnimatedContent>
            <AnimatedContent delay={0.08}>
              <SpotlightCard className="landing-trust-card">
                <Database className="h-7 w-7 landing-feature-icon" />
                <h3>Интеграция с ЕИС</h3>
                <p>Поиск строится вокруг актуальных закупок и документации из рабочего источника.</p>
              </SpotlightCard>
            </AnimatedContent>
            <AnimatedContent delay={0.16}>
              <SpotlightCard className="landing-trust-card">
                <LockKeyhole className="h-7 w-7 landing-feature-icon" />
                <h3>Доступ по аккаунту</h3>
                <p>Дашборд, профиль, анализ и подписки доступны только после входа.</p>
              </SpotlightCard>
            </AnimatedContent>
          </div>
        </section>

        <section id="pricing" className="landing-section landing-container">
          <AnimatedContent>
            <div className="landing-pricing-card">
              <div>
                <div className="blueprint-eyebrow landing-eyebrow">subscription</div>
                <h2>Один рабочий тариф для команды закупок</h2>
                <p>
                  Live-поиск, AI-анализ, профиль компании, избранное и Telegram-подписки доступны
                  пользователям с активной подпиской.
                </p>
              </div>
              <Link to={primaryHref} className="blueprint-button-primary landing-hero-cta">
                {primaryLabel}
                <Zap className="h-5 w-5" />
              </Link>
            </div>
          </AnimatedContent>
        </section>

        <section className="landing-section landing-container">
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
