export interface SuggestionChipItem {
  id: string
  label: string
  value: string
}

export interface Question {
  id: string
  topic: string
  supervisorIntro?: string
  agentName: string
  agentRole: string
  text: string
  suggestionChips: SuggestionChipItem[]
  placeholder?: string
}

export interface UserAnswer {
  questionId: string
  topic: string
  answerText: string
  skipped: boolean
  timestamp: string
}

export type TopicStatus = 'completed' | 'current' | 'pending'

export interface TopicProgress {
  id: string
  name: string
  status: TopicStatus
}
