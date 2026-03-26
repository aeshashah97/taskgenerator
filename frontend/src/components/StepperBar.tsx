interface Props { activeStep: number }

const LABELS = ['Select Project', 'Provide SOW', 'Review Tasks', 'Results']

export function StepperBar({ activeStep }: Props) {
  return (
    <nav className="sticky top-0 z-10 bg-white border-b border-slate-200 px-6 py-3">
      <ol className="flex items-center w-full max-w-5xl mx-auto">
        {LABELS.map((label, i) => {
          const step = i + 1
          const completed = step < activeStep
          const active = step === activeStep
          return (
            <li key={step} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                  ${completed ? 'bg-green-500 text-white' : active ? 'bg-indigo-600 text-white' : 'border-2 border-slate-300 text-slate-400'}`}>
                  {completed ? '✓' : step}
                </div>
                <span className="text-xs font-medium mt-1 hidden sm:block text-slate-600">{label}</span>
              </div>
              {i < LABELS.length - 1 && (
                <div className={`flex-1 h-0.5 mx-2 mb-4 ${completed ? 'bg-green-500' : 'bg-slate-200'}`} />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
