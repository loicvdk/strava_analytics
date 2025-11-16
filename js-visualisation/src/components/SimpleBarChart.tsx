interface SimpleBarChartProps {
  data: Array<{ label: string; value: number; color?: string }>;
  title: string;
  className?: string;
}

export function SimpleBarChart({ data, title, className = "" }: SimpleBarChartProps) {
  const maxValue = Math.max(...data.map(d => d.value));

  const defaultColors = [
    "bg-blue-500",
    "bg-blue-400",
    "bg-blue-600",
    "bg-blue-300",
    "bg-blue-700"
  ];

  return (
    <div className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-slate-900">{title}</h3>
        <div className="h-px bg-gradient-to-r from-blue-500 to-transparent w-24"></div>
      </div>

      <div className="space-y-4">
        {data.map((item, index) => {
          const percentage = (item.value / maxValue) * 100;
          const colorClass = item.color || defaultColors[index % defaultColors.length];

          return (
            <div key={item.label} className="space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">{item.label}</span>
                <span className="text-slate-600">{item.value}</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full ${colorClass} rounded-full transition-all duration-500 ease-out`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}