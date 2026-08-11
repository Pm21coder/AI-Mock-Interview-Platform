export default function QuestionDisplay({ question, index, total }) {
  return (
    <div className="rounded-lg bg-white p-6 shadow-lg">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-700">
          Question {index + 1} of {total}
        </h3>
        <span className="rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800">
          {question.category || 'Technical'}
        </span>
      </div>

      <p className="mb-6 text-xl leading-relaxed text-gray-900">{question.question}</p>

      <div className="border-t pt-4">
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>Difficulty: {question.difficulty || 'Medium'}</span>
          <span>•</span>
          <span>Time: 2–3 minutes</span>
        </div>
      </div>

      {question.expected_answer && (
        <div className="mt-4 rounded-lg bg-gray-50 p-3">
          <p className="text-sm font-medium text-gray-700">Hint:</p>
          <p className="mt-1 text-sm text-gray-600">
            {question.expected_answer.length > 150
              ? `${question.expected_answer.substring(0, 150)}...`
              : question.expected_answer}
          </p>
        </div>
      )}
    </div>
  );
}
