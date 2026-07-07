import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/client';
import { Sparkles, Mail, Lock, ArrowRight, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import {
    AuthDivider,
    AuthHeader,
    AuthPage,
    AuthTrustRow,
} from '../components/ui/Auth';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { Label } from '../components/ui/Label';
import { Button } from '../components/ui/Button';
import { ErrorText } from '../components/ui/ErrorText';

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
            navigate('/dashboard');
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
        <AuthPage>
            <Card variant="auth">
                <AuthHeader
                    eyebrow="access"
                    title="Вход в TenderSystems"
                    subtitle="Введите данные аккаунта"
                    icon={Sparkles}
                />

                <form className="space-y-5" onSubmit={handleSubmit}>
                    <div>
                        <Label variant="auth">Email</Label>
                        <Input
                            variant="auth"
                            icon={Mail}
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Ваш email"
                        />
                    </div>

                    <div>
                        <Label variant="auth">Пароль</Label>
                        <Input
                            variant="auth"
                            icon={Lock}
                            type={showPassword ? 'text' : 'password'}
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            rightElement={
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="auth-eye-button"
                                >
                                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                </button>
                            }
                        />
                    </div>

                    {error && (
                        <ErrorText variant="auth" size="sm">
                            {error}
                        </ErrorText>
                    )}

                    <Button variant="auth" type="submit" disabled={isLoading}>
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
                    </Button>
                </form>

                <AuthDivider />

                <AuthTrustRow icon={ShieldCheck}>Защищенный вход в систему мониторинга</AuthTrustRow>

                <div className="mt-6 text-center">
                    <p className="text-[var(--color-pebble)] text-sm">
                        Нет аккаунта?{' '}
                        <Link to="/register" className="font-semibold text-[var(--color-frost-link)] hover:text-[var(--color-glacier)] transition-colors">
                            Зарегистрироваться
                        </Link>
                    </p>
                </div>
            </Card>
        </AuthPage>
    );
};
