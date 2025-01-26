export interface Message {
  type: 'question' | 'answer' | 'hint' | 'evaluation';
  content: string;
  timestamp: string;
}

export interface ExamChatProps {
  messages: Message[];
}
