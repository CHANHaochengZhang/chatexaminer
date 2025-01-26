export interface QuestionEvaluation {
  score: number;
  feedback: string;
  details: {
    accuracy: string;
    clarity: string;
    understanding: string;
  };
}

export interface EvalReportProps {
  totalScore: number;
  topicCoverage: string;
  behaviorScore: number;
  questionEvaluations: Record<string, QuestionEvaluation>;
  behaviorDetails: {
    completeness: string;
    logic: string;
    terminology: string;
    examples: string;
  };
}
