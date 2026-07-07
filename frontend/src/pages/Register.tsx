import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api/client';
import { Sparkles, Mail, Lock, ArrowRight, Eye, EyeOff, User, CheckCircle2 } from 'lucide-react';
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
        <AuthPage>
            <Card variant="auth-register">
                <AuthHeader
                    eyebrow="create account"
                    title="Регистрация в TenderSystems"
                    subtitle="Создайте новый аккаунт"
                    icon={Sparkles}
                />

                {success && (
                    <ErrorText variant="auth-success" className="mb-5 flex items-center gap-3">
                        <CheckCircle2 className="h-5 w-5 text-[var(--color-cipher-mint)]" />
                        <span className="text-[var(--color-ice)] font-medium">Регистрация успешна! Перенаправление на страницу входа...</span>
                    </ErrorText>
                )}

                <form className="space-y-5" onSubmit={handleSubmit}>
                    <div>
                        <Label variant="auth">Полное имя (необязательно)</Label>
                        <Input
                            variant="auth"
                            icon={User}
                            type="text"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            placeholder="Иван Иванов"
                        />
                    </div>

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
                                <span>Регистрация...</span>
                            </>
                        ) : (
                            <>
                                <span>Зарегистрироваться</span>
                                <ArrowRight className="h-5 w-5" />
                            </>
                        )}
                    </Button>
                </form>

                <AuthDivider />

                <AuthTrustRow icon={CheckCircle2}>Аккаунт будет создан в защищённом контуре</AuthTrustRow>

                <div className="mt-6 text-center">
                    <p className="text-[var(--color-pebble)] text-sm">
                        Уже есть аккаунт?{' '}
                        <Link to="/login" className="font-semibold text-[var(--color-frost-link)] hover:text-[var(--color-glacier)] transition-colors">
                            Войти
                        </Link>
                    </p>
                </div>
            </Card>
        </AuthPage>
    );
};
