import { createRouter, createWebHistory } from 'vue-router'
import ConnectView from '@/views/ConnectView.vue'
import ReviewSignalsView from '@/views/ReviewSignalsView.vue'
import QuestionsView from '@/views/QuestionsView.vue'
import ReportView from '@/views/ReportView.vue'
import AdvisorChatView from '@/views/AdvisorChatView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'connect',
      component: ConnectView,
      meta: { step: 1, title: 'Connect repository' }
    },
    {
      path: '/signals',
      name: 'signals',
      component: ReviewSignalsView,
      meta: { step: 2, title: 'Review signals' }
    },
    {
      path: '/questions',
      name: 'questions',
      component: QuestionsView,
      meta: { step: 3, title: 'Questions' }
    },
    {
      path: '/report',
      name: 'report',
      component: ReportView,
      meta: { step: 4, title: 'Diagnostic report' }
    },
    {
      path: '/advisor',
      name: 'advisor',
      component: AdvisorChatView,
      meta: { step: 5, title: 'Advisor chat' }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
