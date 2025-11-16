interface StatsCardProps {
  title: string;
  value: string;
  icon?: React.ReactNode;
  className?: string;
}

export function StatsCard({ title, value, icon, className = "" }: StatsCardProps) {
  return (
    <div className={`group relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/10 hover:border-blue-300 ${className}`}>
      <div className="relative z-10 flex items-center justify-between">
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-600 tracking-wide uppercase">{title}</p>
          <p className="text-3xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors duration-200">{value}</p>
        </div>
        {icon && (
          <div className="rounded-full bg-blue-50 p-3 text-blue-600 group-hover:bg-blue-100 transition-colors duration-200">
            {icon}
          </div>
        )}
      </div>
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
    </div>
  );
}