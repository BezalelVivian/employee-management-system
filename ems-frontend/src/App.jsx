import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'

import Dashboard from './pages/employee/Dashboard'
import Profile from './pages/employee/Profile'
import Attendance from './pages/employee/Attendance'
import Tasks from './pages/employee/Tasks'
import Leave from './pages/employee/Leave'

import AdminDashboard from './pages/admin/Dashboard'
import Employees from './pages/admin/Employees'
<<<<<<< HEAD
import AdminAttendance from './pages/admin/Attendance'
import TaskReview from './pages/admin/TaskReview'
import LeaveReview from './pages/admin/LeaveReview'
import Holidays from './pages/admin/Holidays'
import { ConfirmProvider } from './components/ConfirmDialog'
import { ToastProvider } from './components/Toast'
=======
import TaskReview from './pages/admin/TaskReview'
import LeaveReview from './pages/admin/LeaveReview'
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6

function HomeRedirect() {
  const { user, isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Navigate to={user?.role === 'admin' ? '/admin/dashboard' : '/dashboard'} replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
<<<<<<< HEAD
        <ToastProvider>
        <ConfirmProvider>
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<HomeRedirect />} />

          <Route element={<ProtectedRoute role="employee"><Layout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/attendance" element={<Attendance />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/leave" element={<Leave />} />
          </Route>

          <Route element={<ProtectedRoute role="admin"><Layout /></ProtectedRoute>}>
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/employees" element={<Employees />} />
<<<<<<< HEAD
            <Route path="/admin/attendance" element={<AdminAttendance />} />
            <Route path="/admin/tasks" element={<TaskReview />} />
            <Route path="/admin/leaves" element={<LeaveReview />} />
            <Route path="/admin/holidays" element={<Holidays />} />
=======
            <Route path="/admin/tasks" element={<TaskReview />} />
            <Route path="/admin/leaves" element={<LeaveReview />} />
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
<<<<<<< HEAD
        </ConfirmProvider>
        </ToastProvider>
=======
>>>>>>> f39b002157dba8453156debd9704189418f3fdd6
      </AuthProvider>
    </BrowserRouter>
  )
}
