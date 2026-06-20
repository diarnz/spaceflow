import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const HomeView = () => import('@/views/public/HomeView.vue')
const VenuesView = () => import('@/views/public/VenuesView.vue')
const BookingView = () => import('@/views/public/BookingView.vue')
const LoginView = () => import('@/views/auth/LoginView.vue')
const RegisterView = () => import('@/views/auth/RegisterView.vue')
const AuthCallbackView = () => import('@/views/auth/AuthCallbackView.vue')
const AccountView = () => import('@/views/account/AccountView.vue')
const MyRequestsView = () => import('@/views/account/MyRequestsView.vue')
const ClientRequestDetailView = () => import('@/views/account/ClientRequestDetailView.vue')
const AdminLayout = () => import('@/components/layout/AdminLayout.vue')
const DashboardView = () => import('@/views/admin/DashboardView.vue')
const RequestsView = () => import('@/views/admin/RequestsView.vue')
const RequestDetailView = () => import('@/views/admin/RequestDetailView.vue')
const InventoryView = () => import('@/views/admin/InventoryView.vue')
const CalendarView = () => import('@/views/admin/CalendarView.vue')
const QuotationsView = () => import('@/views/admin/QuotationsView.vue')
const TasksView = () => import('@/views/admin/TasksView.vue')
const VisualizationView = () => import('@/views/admin/VisualizationView.vue')

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { title: 'SpaceFlow - Home' },
    },
    {
      path: '/venues',
      name: 'venues',
      component: VenuesView,
      meta: { title: 'SpaceFlow - Venues' },
    },
    {
      path: '/book',
      name: 'book',
      component: BookingView,
      meta: { title: 'SpaceFlow - Book a Space' },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true, title: 'SpaceFlow - Sign In' },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { guestOnly: true, title: 'SpaceFlow - Register' },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: AuthCallbackView,
      meta: { title: 'SpaceFlow - Completing Sign In' },
    },
    {
      path: '/account',
      name: 'account',
      component: AccountView,
      meta: { requiresAuth: true, title: 'SpaceFlow - My Account' },
    },
    {
      path: '/my-requests',
      name: 'my-requests',
      component: MyRequestsView,
      meta: { requiresAuth: true, title: 'SpaceFlow - My Requests' },
    },
    {
      path: '/my-requests/:id',
      name: 'my-request-detail',
      component: ClientRequestDetailView,
      meta: { requiresAuth: true, title: 'SpaceFlow - Request Detail' },
    },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAuth: true, requiresStaff: true },
      children: [
        {
          path: '',
          redirect: '/admin/dashboard',
        },
        {
          path: 'dashboard',
          name: 'admin-dashboard',
          component: DashboardView,
          meta: { title: 'SpaceFlow - Dashboard' },
        },
        {
          path: 'requests',
          name: 'admin-requests',
          component: RequestsView,
          meta: { title: 'SpaceFlow - Requests' },
        },
        {
          path: 'requests/:id',
          name: 'admin-request-detail',
          component: RequestDetailView,
          meta: { title: 'SpaceFlow - Request Detail' },
        },
        {
          path: 'inventory',
          name: 'admin-inventory',
          component: InventoryView,
          meta: { title: 'SpaceFlow - Inventory' },
        },
        {
          path: 'calendar',
          name: 'admin-calendar',
          component: CalendarView,
          meta: { title: 'SpaceFlow - Calendar' },
        },
        {
          path: 'quotations',
          name: 'admin-quotations',
          component: QuotationsView,
          meta: { title: 'SpaceFlow - Quotations' },
        },
        {
          path: 'tasks',
          name: 'admin-tasks',
          component: TasksView,
          meta: { title: 'SpaceFlow - Tasks' },
        },
        {
          path: 'visualization',
          name: 'admin-visualization',
          component: VisualizationView,
          meta: { title: 'SpaceFlow - 3D Visualization' },
        },
      ],
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.title) {
    document.title = String(to.meta.title)
  }

  if (to.meta.guestOnly && auth.isAuthenticated) {
    return auth.isStaff ? '/admin/dashboard' : '/account'
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return `/login?redirect=${encodeURIComponent(to.fullPath)}`
  }

  if (to.meta.requiresStaff && !auth.isStaff) {
    return '/'
  }

  return true
})

export default router
