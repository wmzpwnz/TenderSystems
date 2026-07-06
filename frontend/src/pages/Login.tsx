import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/client';
import { motion } from 'framer-motion';
import { Sparkles, Mail, Lock, ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react';

export const Login: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            // OAuth2PasswordRequestForm требует application/x-www-form-urlencoded
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);

            const data = await authApi.login(formData);
            await login(data.access_token);
            navigate('/');
        } catch (err: any) {
            let errorMessage = 'Ошибка входа';
            
            // Обработка ошибок валидации (422)
            if (err.response?.status === 422) {
                const detail = err.response.data?.detail;
                if (Array.isArray(detail)) {
                    // Если это массив ошибок валидации
                    errorMessage = detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
                } else if (typeof detail === 'string') {
                    errorMessage = detail;
                } else if (detail?.msg) {
                    errorMessage = detail.msg;
                } else {
                    errorMessage = 'Неверный формат данных. Проверьте email и пароль.';
                }
            } else if (err.response?.data?.detail) {
                errorMessage = typeof err.response.data.detail === 'string' 
                    ? err.response.data.detail 
                    : 'Ошибка входа';
            } else if (err.message) {
                errorMessage = err.message;
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
                className="authkit-main-card relative z-10"
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
                        <p className="authkit-eyebrow mb-5">access</p>
                        <h2 className="authkit-title">
                            Вход в AdvaCodex
                        </h2>
                        <p className="authkit-subtitle">Введите данные аккаунта</p>
                    </div>

                    <form className="space-y-5" onSubmit={handleSubmit}>
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
                                    <span>Вход...</span>
                                </>
                            ) : (
                                <>
                                    <span>Войти</span>
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
                        <ShieldCheck className="h-4 w-4" />
                        <span>Защищенный вход в систему мониторинга</span>
                    </div>

                    <div className="mt-8 text-center">
                        <p className="text-[var(--color-pebble)] text-lg">
                            Нет аккаунта?{' '}
                            <Link to="/register" className="font-bold text-[var(--color-frost-link)] hover:text-[var(--color-glacier)] transition-colors">
                                Зарегистрироваться
                            </Link>
                        </p>
                    </div>
            </motion.div>
            </div>
        </div>
    );
};
