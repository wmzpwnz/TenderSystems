import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api/client';
import { motion } from 'framer-motion';
import { Sparkles, Mail, Lock, ArrowRight, Eye, EyeOff, User, CheckCircle2 } from 'lucide-react';

export const Register: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            await authApi.register({
                email,
                password,
                full_name: fullName || undefined
            });

            // Показываем сообщение об успехе перед редиректом
            setSuccess(true);
            setTimeout(() => {
                navigate('/login', { replace: true });
            }, 2000);
        } catch (err: any) {
            let errorMessage = 'Ошибка регистрации';
            if (err.response?.data?.detail) {
                errorMessage = err.response.data.detail;
            } else if (err.message) {
                errorMessage = err.message;
            } else if (err.code === 'ERR_NETWORK') {
                errorMessage = 'Не удалось подключиться к серверу. Проверьте, что backend запущен на порту 8000';
            }
            
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="blueprint-page authkit-stage px-4 py-8 sm:px-6">
            <div className="authkit-stack">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="authkit-main-card authkit-register-card relative z-10"
            >
                <div className="authkit-card-dot authkit-dot-tl" />
                <div className="authkit-card-dot authkit-dot-tr" />
                <div className="authkit-card-dot authkit-dot-bl" />
                <div className="authkit-card-dot authkit-dot-br" />

                    <div className="text-center mb-8">
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: 'spring', delay: 0.2 }}
                            className="authkit-logo-mark"
                        >
                            <Sparkles className="h-8 w-8" />
                        </motion.div>
                        <p className="authkit-eyebrow mb-5">create account</p>
                        <h2 className="authkit-title">
                            Регистрация в AdvaCodex
                        </h2>
                        <p className="authkit-subtitle">Создайте новый аккаунт</p>
                    </div>

                    {success && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="blueprint-success mb-5 p-4 flex items-center gap-3"
                        >
                            <CheckCircle2 className="h-5 w-5 text-[var(--color-cipher-mint)]" />
                            <span className="text-[var(--color-ice)] font-medium">Регистрация успешна! Перенаправление на страницу входа...</span>
                        </motion.div>
                    )}

                    <form className="space-y-5" onSubmit={handleSubmit}>
                        <div>
                            <label className="authkit-label">
                                Полное имя (необязательно)
                            </label>
                            <div className="relative">
                                <User className="authkit-input-icon" />
                                <input
                                    type="text"
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    className="authkit-input pl-14 pr-5"
                                    placeholder="Иван Иванов"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="authkit-label">
                                Email
                            </label>
                            <div className="relative">
                                <Mail className="authkit-input-icon" />
                                <input
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="authkit-input pl-14 pr-5"
                                    placeholder="Ваш email"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="authkit-label">
                                Пароль
                            </label>
                            <div className="relative">
                                <Lock className="authkit-input-icon" />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="authkit-input pl-14 pr-14"
                                    placeholder="••••••••"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="authkit-eye-button"
                                >
                                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                </button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="blueprint-danger p-4"
                            >
                                <p className="text-[#ff9b83] text-sm font-medium">{error}</p>
                            </motion.div>
                        )}

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="authkit-submit disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <>
                                    <div className="h-5 w-5 border-2 border-[var(--color-glacier)] border-t-transparent rounded-full animate-spin"></div>
                                    <span>Регистрация...</span>
                                </>
                            ) : (
                                <>
                                    <span>Зарегистрироваться</span>
                                    <ArrowRight className="h-5 w-5" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="authkit-divider">
                        <span />
                        <b>SECURE</b>
                        <span />
                    </div>

                    <div className="authkit-trust-row">
                        <CheckCircle2 className="h-4 w-4" />
                        <span>Аккаунт будет создан в защищённом контуре</span>
                    </div>

                    <div className="mt-8 text-center">
                        <p className="text-[var(--color-pebble)] text-lg">
                            Уже есть аккаунт?{' '}
                            <Link to="/login" className="font-bold text-[var(--color-frost-link)] hover:text-[var(--color-glacier)] transition-colors">
                                Войти
                            </Link>
                        </p>
                    </div>
            </motion.div>
            </div>
        </div>
    );
};
