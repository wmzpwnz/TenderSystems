import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TenderDetail from './pages/TenderDetail'
import CompanyProfile from './pages/CompanyProfile'
import Layout from './components/Layout'

import { AuthProvider } from './context/AuthContext'
import { Login } from './pages/Login'
import { Register } from './pages/Register'

function App() {
  return (
    <AuthProvider>
      <Router
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Главная страница */}
          <Route path="/" element={<Dashboard />} />

          {/* Страницы с Layout */}
          <Route path="/tender/:id" element={<Layout><TenderDetail /></Layout>} />
          <Route path="/profile" element={<Layout><CompanyProfile /></Layout>} />
        </Routes>
      </Router>
    </AuthProvider>
  )
}

export default App


