import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

interface User {
    id: number;
    email: string;
    full_name: string | null;
    is_active: boolean;
    subscription_status: string;
    subscription_expires_at: string | null;
    has_active_subscription: boolean;
    telegram_chat_id: string | null;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    login: (token: string) => Promise<void>;
    logout: () => void;
    updateUser: (data: Partial<User>) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (token) {
            // Токен теперь добавляется через interceptor в apiClient
            // Но для обратной совместимости оставляем и здесь
            api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            fetchUser();
        } else {
            delete api.defaults.headers.common['Authorization'];
            setUser(null);
            setIsLoading(false);
        }
    }, [token]);

    const fetchUser = async () => {
        try {
            const response = await api.get('/auth/me');
            setUser(response.data);
        } catch (error: any) {
            console.error('Error fetching user', error);
            // Only logout if unauthorized
            if (error.response && error.response.status === 401) {
                logout();
            }
        } finally {
            setIsLoading(false);
        }
    };

    const login = async (newToken: string) => {
        setIsLoading(true);
        localStorage.setItem('token', newToken);
        api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
        setToken(newToken);
        try {
            const response = await api.get('/auth/me');
            setUser(response.data);
        } finally {
            setIsLoading(false);
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        delete api.defaults.headers.common['Authorization'];
    };

    const updateUser = async (data: Partial<User>) => {
        try {
            const response = await api.patch('/auth/me', data);
            setUser(response.data);
        } catch (error) {
            console.error('Error updating user', error);
            throw error;
        }
    };

    return (
        <AuthContext.Provider value={{ user, token, isLoading, login, logout, updateUser }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
