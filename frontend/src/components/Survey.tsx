import React, { useState } from 'react';
import { Button } from '../components/ui/button'; // Assuming a Button component exists or use plain button
import { computeStage } from '../../utils/scoring';
import type { Question } from '../../types/question';

// Placeholder questions; in real app load from JSON or API
const QUESTIONS: Question[] = [
  { id: 'Q1', text: '외출 빈도 (A7)', options: ['매일', '주 3~4일', '자주', '가끔', '보통', '인근 편의점', '방 안에만', '거의 안나감'], scores: [0,1,1,2,3,4,5,6] },
  { id: 'Q2', text: '지난 2주 교류 횟수 (A11)', options: ['0회','1회','2회','3회','4~5회','6~10회','11회 이상'], scores: [5,4,3,3,2,1,0] },
  { id: 'Q3', text: '친구와 대면 교류 (A13_3)', options: ['전혀 없다','1년에 한두 번','3개월에 한두 번','한 달에 한두 번','일주일에 한두 번','거의 매일'], scores: [5,4,3,2,1,0] },
  { id: 'Q4', text: '직장·학교·동네 사람과 대면 교류 (A13_4)', options: ['전혀 없다','1년에 한두 번','3개월에 한두 번','한 달에 한두 번','일주일에 한두 번','거의 매일'], scores: [5,4,3,2,1,0] },
  { id: 'Q5', text: '어려운 일 조언받을 사람 (A12_1)', options: ['가족/친척','친구','그 외','없음'], scores: [1,0,1,5] },
  { id: 'Q6', text: '우울할 때 털어놓을 사람 (A12_4)', options: ['가족/친척','친구','그 외','없음'], scores: [1,0,1,5] },
  { id: 'Q7', text: '외로움: 도움 청할 사람 없음 (A18_2)', options: ['전혀 아니다','별로 아니다','가끔','항상'], scores: [0,1,3,5] },
  { id: 'Q8', text: '우울감 (B12_1)', options: ['없음','2~3일 이상','7일 이상','거의 매일'], scores: [0,2,4,5] },
  { id: 'Q9', text: '자살/자해 사고 (B12_9)', options: ['없음','2~3일 이상','7일 이상','거의 매일'], scores: [0,3,5,6] },
];

interface SurveyProps {
  onComplete: (stage: string) => void;
}

const Survey: React.FC<SurveyProps> = ({ onComplete }) => {
  const [answers, setAnswers] = useState<Record<string, number>>({});

  const handleSelect = (qid: string, score: number) => {
    setAnswers(prev => ({ ...prev, [qid]: score }));
  };

  const handleSubmit = () => {
    const stage = computeStage(answers);
    onComplete(stage);
  };

  const allAnswered = QUESTIONS.every(q => answers[q.id] !== undefined);

  return (
    <div className="survey-wrapper">
      {QUESTIONS.map(q => (
        <div key={q.id} className="survey-question">
          <p className="question-text">{q.text}</p>
          <div className="options">
            {q.options.map((opt, idx) => (
              <button
                key={opt}
                className={`option-btn ${answers[q.id] === q.scores[idx] ? 'selected' : ''}`}
                onClick={() => handleSelect(q.id, q.scores[idx])}
                type="button"
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      ))}
      <div className="survey-actions">
        <button className="btn-primary" disabled={!allAnswered} onClick={handleSubmit} type="button">결과 보기</button>
      </div>
    </div>
  );
};

export default Survey;
